# Generally DEPRECIATED

from tree_sitter import Language, Tree, Node
from pathlib import Path
from analyzer import Analyzer, print_children
from config import interesting_node_types, par_vec_extended
import pickle
from sklearn.svm import LinearSVC
from copy import copy
import re
import pandas as pd


# Copied from Python Extractor
def check_parent(node: Node, param_vec: dict):
    parent = node
    while parent.parent:
        parent = parent.parent
        if parent.type == "block":
            break
    if parent.type != "module":
        assert parent.type == "block"
        # TODO: Decide: Always check if entry is true already like in check_block()?
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


class PythonAnalyzer(Analyzer):
    def __init__(self, src: str, lang: Language, tree: Tree, file_path: Path, args):
        """
        :param src: Source code to analyze
        :param lang: Treesitter language object
        :param tree: Treesitter tree object
        :param file_path: Pathlib object of the file to analyze
        """

        super().__init__(src, lang, tree, file_path, args)
        # Name of the Python logging module
        self.keyword = "logg(ing|er)"

    def analyze(self) -> list:
        """ Starts the analyses """
        print_children(self.tree.root_node)
        return []
        recommendations = []
        classifier: LinearSVC = pickle.load(open('classifier', 'rb'))
        # print(classifier.predict([[False,False,False,False,False,False,False,False,False,False]]))

        for node_type in interesting_node_types:
            node_query = self.lang.query("(" + node_type + ") @" + node_type)
            nodes = node_query.captures(self.tree.root_node)
            for node, tag in nodes:

                print(f"{node_type} line {node.start_point[0] + 1}")
                print(node.end_point[0] - node.start_point[0] + 1)

                param_vec = copy(par_vec_extended)
                param_vec["type"] = node_type
                if node_type == "if_statement":
                    check_if(node, param_vec, self.args, self.keyword)
                elif node_type == "try_statement":
                    check_try(node, param_vec, self.args, self.keyword)
                elif node_type == "function_definition":
                    check_def(node, param_vec, self.args, self.keyword)
                # Only recommend for a node that doesn't have logging already
                if param_vec["contains_logging"]:
                    continue
                # Check the parent
                check_parent(node, param_vec)

                # print(list(param_vec.items()))
                # print(param_vec)
                # print(classifier.predict([list(param_vec.values())]))

                df = pd.DataFrame.from_dict([param_vec]).iloc[:, 2:-1]
                # print(df)

                # DEBUG
                # test_vec = copy(par_vec_extended_no_type_all_true)
                # df = pd.DataFrame.from_dict([test_vec])
                # print(classifier.predict(df)[0])
                # DEBUG END

                if classifier.predict(df)[0]:
                    recommendations.append(f"We recommend logging in the {node_type} "
                                           f"starting in line {node.start_point[0] + 1}")
        return recommendations

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
