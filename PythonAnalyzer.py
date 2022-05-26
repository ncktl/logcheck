from tree_sitter import Language, Tree, Node
import logging
from pathlib import Path
from time import perf_counter


def print_children(node: Node, indent=0):
    print(indent * 2 * " ", node)
    for child in node.children:
        if child.is_named:
            print_children(child, indent + 1)


class PythonAnalyzer:
    def __init__(self, src: str, lang: Language, tree: Tree, file_path: Path):
        """
        :param src: Source code to analyze
        :param lang: Treesitter language object
        :param file_path: Pathlib object of the file to analyze
        """
        self.src = src
        self.lang = lang
        self.tree = tree
        self.file_path = file_path
        logging.basicConfig(
            filename=file_path.with_name("analysis-of-" + file_path.name + ".log"),
            filemode="w",
            level=logging.DEBUG,
            encoding="utf-8",
            format="%(levelname)s:%(message)s"
        )
        self.logger = logging.getLogger(__name__)
        # Name of the Python logging module
        self.keyword = "logging"

    def analyze(self):
        """ Starts the analyses """
        if not self.check_for_module_import():
            self.logger.info(f"The {self.keyword} module is not used in this file.")
            return
        # a = perf_counter()
        self.exception_handling_manually()
        # b = perf_counter()
        self.exception_handling_via_treesitter()
        # c = perf_counter()
        # print(f"Manual: {b - a}, Treesitter: {c - b}")

    def check_for_module_import(self) -> bool:
        """
        Checks if the logging module is imported.
        Also finds alias of logging module if used and updates self.keyword accordingly
        Currently only full (aliased) module imports are supported,
        but not "from x import y [as z]" imports.
        """
        # Query to find import statements
        import_query = self.lang.query("(import_statement) @a1")
        # Find import statements
        import_statements = import_query.captures(self.tree.root_node)

        for node, tag in import_statements:
            # Simple import: Last child is the module name
            if node.children[-1].type == "dotted_name":
                if node.children[-1].text.decode("UTF-8") == self.keyword:
                    pass
                    return True
            # Aliased import: Last child is aliased import statement node,
            else:
                # Last child's first child is module, last child is alias
                if node.children[-1].children[0].text.decode("UTF-8") == self.keyword:
                    self.keyword = node.children[-1].children[-1].text.decode("UTF-8")
                    return True
        return False

    def exception_handling_via_treesitter(self):
        """
        Checks for logging in the direct children function calls of the exception nodes of the ast,
        e.g. logging inside an if-statement in the exception handling is not
        accepted as it is not guaranteed to be reached.
        """
        self.logger.info("Treesitter analysis of logging in exception handling:")
        # Query to find logging calls inside exception handling of the form keyword.function(), e.g. logging.info()
        call_in_exc_query = self.lang.query("(except_clause"
                                            "(block"
                                            "(expression_statement"
                                            "(call"
                                            "(attribute ."
                                            "(identifier) @identifier)))))")
        # Execute query
        call_identifiers = call_in_exc_query.captures(self.tree.root_node)
        exceptions_with_direct_logging = set()
        for node, tag in call_identifiers:
            if node.text.decode("UTF-8") == self.keyword:
                # The except clause is the identifier's fifth-level ancestor (see query above)
                # Add these exceptions to a set because multiple logging calls can have the same exception ancestor
                # Identified by their start_byte
                exceptions_with_direct_logging.add(node.parent.parent.parent.parent.parent.start_byte)
        # Query to find all exception handling nodes in the ast
        exception_query = self.lang.query("(except_clause) @b")
        all_exceptions = exception_query.captures(self.tree.root_node)
        for node, tag in all_exceptions:
            if node.start_byte not in exceptions_with_direct_logging:
                # Find the exceptions not in the set of exceptions with direct logging
                self.logger.warning(f"No direct logging in the exception handling "
                                    f"starting in line {node.start_point[0] + 1}:")
                self.logger.debug(node.text.decode("UTF-8"))
        self.logger.info(f"Logging used in {len(exceptions_with_direct_logging)} "
                         f"out of {len(all_exceptions)} exception handling blocks.")

    def exception_handling_manually(self):
        """ Searches the source code for indications of logging and checks the exception handling for logging """
        self.logger.info("Manual analysis of logging in exception handling:")
        logging_count = 0
        exception_count = 0
        exceptions_logged = 0
        lines = self.src.splitlines()
        past_import = False
        # Go through the sourcecode
        for i, line in enumerate(lines):
            # Look for the logging module
            if not past_import:
                if "import" not in line:
                    past_import = True
            # After the logging module import:
            else:
                if self.keyword in line:
                    logging_count += 1
                # Search for exception statements
                if "except" in line:
                    except_index = line.find("except")
                    # Substring of the line before the "except" keyword
                    exc_line_prefix = line[0:except_index]
                    # Avoid comments and "logging.exception()"
                    if "#" not in exc_line_prefix and not exc_line_prefix.endswith("."):
                        exception_count += 1
                        # Go through the lines after the except statement in an inner loop:
                        for j, nested_line in enumerate(lines[i + 1:]):
                            # Assumption: 4 spaces used for indentation
                            nested_line_prefix = nested_line[0:except_index + 4]
                            # If we find a line with one more level of indentation
                            if nested_line_prefix == exc_line_prefix + 4 * " ":
                                # but also not more than one additional level
                                if nested_line[except_index + 5] != " ":
                                    # and the keyword (default: "logging") was used in this exception handling,
                                    # this exception has been logged.
                                    if self.keyword in nested_line:
                                        exceptions_logged += 1
                                        break
                            # If instead a line with the same indentation is found, the exception block is
                            # over and no logging was used.
                            else:
                                self.logger.warning(
                                    f"No logging in the exception handling starting in line {i + 1}:"
                                )
                                # Multi-line debug message is not indented correctly
                                self.logger.debug("\n".join(lines[i:i + j + 1]))
                                break
        self.logger.info(f"The logging module has been mentioned {logging_count} time[s].")
        self.logger.info(f"Logging used in {exceptions_logged} out of {exception_count} exception handling blocks.")
