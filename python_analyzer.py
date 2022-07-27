from tree_sitter import Language, Tree, Node
import logging
from pathlib import Path
from time import perf_counter
from analyzer import Analyzer, print_children
import pickle
from sklearn.svm import LinearSVC


class PythonAnalyzer(Analyzer):
    def __init__(self, src: str, lang: Language, tree: Tree, file_path: Path):
        """
        :param src: Source code to analyze
        :param lang: Treesitter language object
        :param tree: Treesitter tree object
        :param file_path: Pathlib object of the file to analyze
        """

        super().__init__(src, lang, tree, file_path)
        # Name of the Python logging module
        self.keyword = "logging"

    def analyze(self):
        """ Starts the analyses """
        classifier: LinearSVC = pickle.load(open('classifier', 'rb'))
        print(classifier.predict([[False,False,False,False,False,False,False,False,False,False]]))

    def get_all_named_children_with_parent_of_type(self, node_type: str):
        query = self.lang.query("(" + node_type + " (_) @inner)")
        nodes = query.captures(self.tree.root_node)
        for node in nodes:
            print(node)

    def check_for_module_import(self) -> bool:
        """
        DEPRECATED: Detecting the logging framework is out of scope.
        The user will have to supply the name of the logging framework.
        ############
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
        self.logger.info("Tree-sitter analysis of logging in exception handling:")
        # Query to find logging calls inside exception handling of the form of
        # keyword.function(), e.g. logging.info("Text")
        # The first identifier of the method call, "logging", is selected via the dot (".") as the first child of
        # the attribute node (which is "logging.info", i.e. without the parentheses and parameters)
        # The identifier node is captured with the "@identifier" tag (name is arbitrary)
        call_in_exc_query = self.lang.query("(except_clause"
                                            "(block"
                                            "(expression_statement"
                                            "(call"
                                            "(attribute ."
                                            "(identifier) @identifier)))))")
        # Execute query. Creates a list of (node, tag) tuples of the captured nodes
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

    def ts_example(self):
        # Recursively print the whole ast in stdout
        print("Abstract syntax tree of ts_py_example.py. Start and end points of nodes are 0-indexed.")
        print("Below the ast are the non-import logging occurrences and their logical parent's ast subtree.")
        print_children(self.tree.root_node)

        # Query to find logging calls of the form of
        # keyword.function(), e.g. logging.info("Text")
        # The first identifier of the method call, "logging", is selected via the dot (".") as the first child of
        # the attribute node (which is "logging.info", i.e. without the parentheses and parameters)
        # The identifier node is captured with the "@a" tag (name is arbitrary)
        call_in_exc_query = self.lang.query("(call"
                                            "(attribute ."
                                            "(identifier) @identifier))")

        # Execute query. Creates a list of (node, tag) tuples of the captured nodes
        call_identifiers = call_in_exc_query.captures(self.tree.root_node)

        for node, tag in call_identifiers:
            if node.text.decode("UTF-8") == "logging":
                # Parent of the great-grandparent expression node
                # Usually a block node, can also be the whole module if logging statement is top level
                # First parent is attribute, second is call, third is expression, fourth is block
                block_parent: Node = node.parent.parent.parent.parent
                # Avoid top level occurrences of the logging module, including import
                if block_parent.type != "module":
                    # If the logging statement isn't a top level statement (i.e. is a child of the whole module)
                    # its parent expression statement's parent should be a block node,
                    # of which the parent is what we normally consider the parent of the logging statement,
                    # like a function declaration or an if-statement.
                    assert block_parent.type == "block"
                    # Text of the logging statement
                    code_line = node.parent.parent.parent.text.decode("UTF-8")
                    print("#" * 80)
                    print(f"Line {node.start_point[0] + 1}: {code_line}")
                    # Recursively print the subtree of the logging statement's logical parent
                    # Note that the result depends on the logical parent's type because
                    # if the logical parent is an except clause, its father is a try statement,
                    # but if the logical parent is an if-statement, its father is a block (or the module)
                    print_children(block_parent.parent)
