from tree_sitter import Language, Tree, Node
import logging
from pathlib import Path
from time import perf_counter
from analyzer import Analyzer, print_children
from dataclasses import dataclass



@dataclass
class ParamVec:
    def __init__(self):
        self.if_: bool = False
        self.try_: bool = False
        self.logging_: bool = False



    def __str__(self):
        return repr(self)


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

        # Method to demonstrate Tree-sitter with a special example python program
        # self.ts_example()

        # if not self.check_for_module_import():
        # self.logger.info(f"The {self.keyword} module is not used in this file.")
        # return
        # a = perf_counter()
        # self.exception_handling_manually()
        # self.logger.info("\n" * 3)
        # b = perf_counter()
        # self.exception_handling_via_treesitter()
        # c = perf_counter()
        # print(f"Manual: {b - a}, Treesitter: {c - b}")

        self.fill_param_vecs_sliding()

    # Sliding code window approach
    def fill_param_vecs_sliding(self, vert_range: int = 3) -> list:
        """
        Fill parameter vectors using a sliding code window.
        Interesting nodes are found. Their context is the lines above and below, specified by the range
        Function definitions are treated as an additional boundary of the context
        Problem: Comments in the code
        :param vert_range: Determines the size of the sliding code window in up and down directions
        """

        param_vectors = []

        interesting_node_types = ["if_statement", "except_clause", "function_definition"]
        for node_type in interesting_node_types:

            # Query to find the node type
            node_query = self.lang.query("(" + node_type + ") @a")
            nodes = node_query.captures(self.tree.root_node)
            # if_query = self.lang.query("(if_statement) @if")
            # if_nodes = if_query.captures(self.tree.root_node)

            for node, tag in nodes:

                # Parameter vector
                param_vec = {
                    "line": node.start_point[0],
                    "if_": False,
                    "try_": False,
                    "logging_": False
                }


                print(node)
                # Check the context range and check for function definitions therein
                # Context start and end are inclusive

                # First make sure context is within the file
                context_start = max(node.start_point[0] - vert_range, 0)
                context_end = min(node.start_point[0] + vert_range, len(self.lines) - 1)
                # print(context_start, context_end)

                # Check upwards for function defs
                # unless node is a function def itself
                if node_type == "function_definition":
                    context_start = node.start_point[0]
                else:
                    for i in range(node.start_point[0] - 1, context_start - 1, -1):
                        # print(i)
                        if "def " in self.lines[i]:
                            context_start = i + 1
                            break

                # Check downwards for function defs:
                for i in range(node.start_point[0] + 1, context_end + 1):
                    # print(i)
                    if "def " in self.lines[i]:
                        context_end = i - 1
                        break

                context = "\n".join(self.lines[context_start:context_end + 1])
                print(context)

                if "if " in context:
                    param_vec["if_"] = True
                if "try " in context:
                    param_vec["try_"] = True
                # Just checking for "logging" is esp. susceptible to comments
                if "logging." in context:
                    param_vec["logging_"] = True

                print(list(param_vec.values()))
                param_vectors.append(list(param_vec.values()))
                print("#" * 50)

            for vec in param_vectors:
                print(vec)
            return param_vectors




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
        self.logger.info("Treesitter analysis of logging in exception handling:")
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
