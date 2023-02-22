# Generally DEPRECIATED

from tree_sitter import Language, Tree, Node

from extractor import print_children, traverse_sub_tree
from python_extractor import PythonExtractor


class PythonAnalyzer(PythonExtractor):
    def __init__(self, src: str, lang: Language, tree: Tree, file, settings):
        """
        :param src: Source code to extract paramaeter vectors from
        :param lang: Treesitter language object
        :param tree: Treesitter tree object
        :param file: current file
        """
        super().__init__(src, lang, tree, file, settings)
        # Name of the Python logging module
        self.keyword = "logg(ing|er)"

    def analyze(self):
        """ Starts the analyses """
        print_children(self.tree.root_node, print_unnamed=self.settings.debug);

        for node in traverse_sub_tree(self.tree.root_node):
            # if node.is_named and node.type == "expression_statement":
            if node.is_named:
                print(node)
            #     print(node.text.decode("UTF-8"), "\t\t\t", node)
            #     if node.type == "function_definition":
            #         print(node.text.decode("UTF-8"))
            #         block_node = node.child_by_field_name("body")
            #         print(block_node.text.decode("UTF-8"))
            #         exit()
                # print(node.text)
                # print("#" * 80)
                # print(node.text.decode("UTF-8"))
                # exit()




    def check_for_module_import(self) -> bool:
        """
        ############
        DEPRECATED: Detecting the logging framework is out of scope.
        Also DEPRECATED: The user will have to supply the name of the logging framework.
        We now use a regex built to detect logging statements from commonly used logging frameworks
        but this functionality may prove usesful again at some point.
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
        DEPRECATED: This was the initial Tree-sitter usage

        Checks for logging in the direct children function calls of the exception nodes of the ast,
        e.g. logging inside an if-statement in the exception handling is not
        accepted as it is not guaranteed to be reached.
        """
        # self.logger.info("Tree-sitter analysis of logging in exception handling:")

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
                print(f"No direct logging in the exception handling "
                                    f"starting in line {node.start_point[0] + 1}:")
                print(node.text.decode("UTF-8"))
        print(f"Logging used in {len(exceptions_with_direct_logging)} "
                         f"out of {len(all_exceptions)} exception handling blocks.")

    def ts_example(self):
        """Example of Tree-sitter usage"""

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
