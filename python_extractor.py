from tree_sitter import Language, Tree, Node
from extractor import Extractor
from config import par_vec_extended, par_vec_bool, par_vec_onehot, interesting_node_types, contains
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
            # Useless?
            if False not in param_vec.values():
                raise RuntimeError
            # Todo: Adapt to new contains_features

            if not param_vec["contains_logging"] and child.type == "expression_statement":
                if len(child.children) != 1:
                    for exp_child in child.children:
                        if exp_child.type == "call":
                            if re.search(self.keyword, exp_child.text.decode("UTF-8")):
                                param_vec["contains_logging"] = True
                elif child.children[0].type == "call":
                    if re.search(self.keyword, child.children[0].text.decode("UTF-8")):
                        param_vec["contains_logging"] = True
            elif not param_vec["contains_try_statement"] and child.type == "try_statement":
                param_vec["contains_try_statement"] = True
            elif not param_vec["contains_if_statement"] and child.type == "if_statement":
                param_vec["contains_if_statement"] = True
            elif not param_vec["contains_with_statement"] and child.type == "with_statement":
                param_vec["contains_with_statement"] = True
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
            if self.args.mode == "bool":
                if parent.type == "block":
                    # Temporary solution while interesting nodes not handled fully
                    if parent.parent.type in interesting_node_types:
                        param_vec["child_of_" + parent.parent.type] = True
                        return
                # Temp disabled
                # if parent.type == "module":
                #     param_vec["child_of_module"] = True
                #     return
            elif self.args.mode == "onehot":
                if parent.type == "block":
                    param_vec["parent"] = parent.parent.type
                    return
                if parent.type == "module":
                    param_vec["parent"] = "module"
                    return
        # Temp disabled
        # raise RuntimeError("Could not find parent of node")

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
                if self.args.mode == "bool":
                    param_vec = copy(par_vec_bool)
                    param_vec[node_type] = True
                elif self.args.mode == "onehot":
                    param_vec = copy(par_vec_onehot)
                    param_vec["type"] = node_type
                param_vec["line"] = node.start_point[0] + 1
                # Check parent
                self.check_parent(node, param_vec)
                # Todo: Turn this into a function
                if node_type == "if_statement":
                    self.check_if(node, param_vec)
                elif node_type == "try_statement":
                    self.check_try(node, param_vec)
                elif node_type == "function_definition":
                    self.check_def(node, param_vec)
                if training:
                    hmm = list(param_vec.values())
                    if self.args.mode == "bool":
                        if len(hmm) != len(par_vec_bool):
                            print(self.file)
                            print(copy(par_vec_bool))
                            print(node)
                            print(param_vec)
                            print()
                    elif self.args.mode == "onehot":
                        if len(hmm) != len(par_vec_onehot):
                            print(self.file)
                            print(copy(par_vec_onehot))
                            print(node)
                            print(param_vec)
                            print()
                    param_vectors.append(hmm)
                else:
                    # Only recommend for a node that doesn't have logging already
                    # TODO check if this is a good idea
                    if not param_vec["contains_logging"]:
                        param_vectors.append(param_vec)
        return param_vectors
