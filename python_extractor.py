from tree_sitter import Language, Tree, Node
from extractor import Extractor
from config import par_vec_extended, interesting_node_types
import re
from copy import copy


class PythonExtractor(Extractor):
    def __init__(self, src: str, lang: Language, tree: Tree, file, args):
        """
        :param src: Source code to extract paramaeter vectors from
        :param lang: Treesitter language object
        :param tree: Treesitter tree object
        :param file: current file
        """

        super().__init__(src, lang, tree, file, args)
        # Name of the Python logging module
        self.keyword = "logg(ing|er)"

    def check_if(self, node: Node, param_vec: dict):
        self.check_block(node.child_by_field_name("consequence"), param_vec)
        # Do we want to see what is in the elif/else clause?
        # for child in node.children:
        #     if not self.args.debug and False not in param_vec.values():
        #         return
        #     if child.type == "elif_clause":
        #         self.check_block(child.child_by_field_name("consequence"), param_vec)
        #     elif child.type == "else_clause":
        #         self.check_block(child.child_by_field_name("body"), param_vec)

    def check_block(self, node: Node, param_vec: dict):
        for child in node.children:
            if not self.args.debug and False not in param_vec.values():
                return
            if not param_vec["contains_logging"] and child.type == "expression_statement":
                if len(child.children) != 1:
                    for exp_child in child.children:
                        if exp_child.type == "call":
                            if re.search(self.keyword, exp_child.text.decode("UTF-8")):
                                param_vec["contains_logging"] = True
                elif child.children[0].type == "call":
                    if re.search(self.keyword, child.children[0].text.decode("UTF-8")):
                        param_vec["contains_logging"] = True
            elif not param_vec["contains_try"] and child.type == "try_statement":
                param_vec["contains_try"] = True
            elif not param_vec["contains_if"] and child.type == "if_statement":
                param_vec["contains_if"] = True
            elif not param_vec["contains_with"] and child.type == "with_statement":
                param_vec["contains_with"] = True
            # More checks for expanded dict

    def check_try(self, node: Node, param_vec: dict):
        self.check_block(node.child_by_field_name("body"), param_vec)
        # Do we want to see what is in the except/else clauses?
        # for child in node.children:
        #     if not self.args.debug and False not in param_vec.values():
        #         return
        #     if child.type == "block":
        #         self.check_block(child, param_vec)
        #     elif child.type == "else_clause":
        #         self.check_block(child.child_by_field_name("body"), param_vec)
        #     elif child.type == "except_clause":
        #         # Can also have some kind of expression child?
        #         for grandchild in child.children:
        #             if grandchild.type == "block":
        #                 self.check_block(grandchild, param_vec)
        #     elif child.type == "finally_clause":
        #         # Comment can also be a named child
        #         for grandchild in child.children:
        #             if grandchild.type == "block":
        #                 self.check_block(grandchild, param_vec)
        #                 break

    def check_def(self, node: Node, param_vec: dict):
        self.check_block(node.child_by_field_name("body"), param_vec)

    def check_parent(self, node: Node, param_vec: dict):
        parent = node
        while parent.parent:
            parent = parent.parent
            if parent.type == "block":
                param_vec["child_of_" + parent.parent.type] = True
                return
            if parent.type == "module":
                param_vec["child_of_module"] = True
                return
        raise RuntimeError("Could not find parent of node")

    def fill_param_vecs_ast_new(self, training: bool = True) -> list:
        param_vectors = []
        visited_nodes = set()
        for node_type in interesting_node_types:
            node_query = self.lang.query("(" + node_type + ") @" + node_type)
            nodes = node_query.captures(self.tree.root_node)
            for node, tag in nodes:
                # Uniqueness check is unnecessary?
                if (node.start_byte, node.end_byte) in visited_nodes:
                    raise RuntimeError
                else:
                    visited_nodes.add((node.start_byte, node.end_byte))
                if not node.is_named:
                    continue
                # Parameter vector for this node
                param_vec = copy(par_vec_extended)
                param_vec["line"] = node.start_point[0] + 1
                param_vec[node_type] = True
                # Check parent
                self.check_parent(node, param_vec)

                if node_type == "if_statement":
                    self.check_if(node, param_vec)
                elif node_type == "try_statement":
                    self.check_try(node, param_vec)
                elif node_type == "function_definition":
                    self.check_def(node, param_vec)
                if training:
                    param_vectors.append(list(param_vec.values()))
                else:
                    # Only recommend for a node that doesn't have logging already
                    if not param_vec["contains_logging"]:
                        param_vectors.append(param_vec)
        return param_vectors
