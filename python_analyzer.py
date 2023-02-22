# Generally DEPRECIATED
import re

from tree_sitter import Language, Tree, Node

from extractor import print_children, traverse_sub_tree
from config import keywords, PythonNodeNames
from python_extractor import PythonExtractor


# Copied from Python Extractor
def check_parent(node: Node, param_vec: dict):
    parent = node
    while parent.parent:
        parent = parent.parent
        if parent.type == "block":
            break
    if parent.type != "module":
        assert parent.type == "block"
        if parent.parent.type == "if_statement":
            param_vec["inside_if"] = True
        elif parent.parent.type == "elif_clause":
            param_vec["inside_elif"] = True
        elif parent.parent.type == "else_clause":
            if parent.parent.parent.type == "if_statement":
                param_vec["inside_if_else"] = True
            elif parent.parent.parent.type == "try_statement":
                param_vec["inside_try_else"] = True
            # For..else, While..else,..
        elif parent.parent.type == "try_statement":
            param_vec["inside_try"] = True
        elif parent.parent.type == "except_clause":
            param_vec["inside_except"] = True
        elif parent.parent.type == "finally_clause":
            param_vec["inside_finally"] = True


def check_block(node: Node, param_vec: dict, args, keyword: str):
    for child in node.children:
        if not args.debug and False not in param_vec.values():
            return
        if not param_vec["contains_logging"] and child.type == "expression_statement":
            # assert len(child.children) == 1 # NOT ALWAYS TRUE
            if len(child.children) != 1:
                # print("Expression statement with more than one child found:")
                # print(f"Line {child.start_point[0] + 1}")
                # print(child.text.decode("UTF-8"))
                # print(child.children)
                for exp_child in child.children:
                    if exp_child.type == "call":
                        if re.search(keyword, exp_child.text.decode("UTF-8")):
                            param_vec["contains_logging"] = True
            elif child.children[0].type == "call":
                if re.search(keyword, child.children[0].text.decode("UTF-8")):
                    param_vec["contains_logging"] = True
        elif not param_vec["contains_try"] and child.type == "try_statement":
            param_vec["contains_try"] = True
        elif not param_vec["contains_if"] and child.type == "if_statement":
            param_vec["contains_if"] = True
        elif not param_vec["contains_with"] and child.type == "with_statement":
            param_vec["contains_with"] = True
        # More checks for expanded dict


def check_if(node: Node, param_vec: dict, args, keyword: str):
    check_block(node.child_by_field_name("consequence"), param_vec, args, keyword)


def check_try(node: Node, param_vec: dict, args, keyword: str):
    check_block(node.child_by_field_name("body"), param_vec, args, keyword)


def check_def(node: Node, param_vec: dict, args, keyword: str):
    check_block(node.child_by_field_name("body"), param_vec, args, keyword)


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

    def analyze(self) -> list:
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
            # return []
        # recommendations = []
        # return recommendations

    def proto_context(self):
        # print_children(self.tree.root_node)
        function_definiton_query = self.lang.query("(function_definition) @funcdef")
        function_definiton_nodes = function_definiton_query.captures(self.tree.root_node)
        block_query = self.lang.query("(block) @block")
        # block_nodes = block_query.captures(self.tree.root_node)
        # prev = None
        for funcdef_node, tag in function_definiton_nodes:
            funcdef_node: Node
            block_nodes = block_query.captures(funcdef_node)
            print("#" * 80)
            print(funcdef_node)
            print(funcdef_node.text.decode("UTF-8"))
            print("+" * 80)
            for block_node, tag in block_nodes:
                print(block_node)
                print(block_node.text.decode("UTF-8"))
                print("-" * 80)
                print("Ast path from function definition to block:")
                pathlist = []
                wandering_node = block_node
                while wandering_node != funcdef_node:
                    pathlist.append(wandering_node)
                    wandering_node = wandering_node.parent
                pathlist.reverse()
                for node in pathlist:
                    if node.is_named and node.type in PythonNodeNames.most_node_types:
                        print(node.type)
                print("-" * 80)
                print("Previous nodes in function definition:")

                # last_node = None
                def check_and_print(node: Node):
                    if node.is_named and node.type in PythonNodeNames.most_node_types:
                        if node.type == "call" and keyword.match(node.text.decode("UTF-8").lower()):
                            # print("Logging call found")
                            return
                        print(node.type)

                for node in traverse_sub_tree(funcdef_node, block_node):
                    if node.type != "function_definition":
                        check_and_print(node)
                        # print(node)
                        # print(node.type)
                        # last_node = node
                        # print("-" * 80)
                # if last_node:
                #     for node2 in traverse_sub_tree(last_node):
                #         if node2.is_named and node2.type in visible_node_types:
                #             print(node2.type)
                for node in traverse_sub_tree(block_node):
                    check_and_print(node)
                print("=" * 80)

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
