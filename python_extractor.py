from tree_sitter import Language, Tree, Node
from extractor import Extractor
from config import par_vec_bool, par_vec_onehot, interesting_node_types, contains
from config import compound_statements, simple_statements, extra_clauses, contains_types, keyword
import config as cfg
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
        # self.keyword = "logg(ing|er)"

    def debug_helper(self, node: Node):
        print(self.file)
        print(f"Parent: {node.parent}")
        print(node)
        print(f"Children: {node.children}")
        # print(node.text.decode("UTF-8"))

    def check_expression(self, exp_child: Node, param_vec: dict):
        if exp_child.type == "call":
            param_vec["contains_call"] = True
            # Check call nodes for logging
            func_call = exp_child.child_by_field_name("function")
            if re.search(keyword, func_call.text.decode("UTF-8").lower()):
                param_vec["contains_logging"] = True
        elif exp_child.type == "assignment" or exp_child.type == "augmented_assignment":
            param_vec["contains_assignment"] = True
            # Check assignment nodes for calls
            assign_rhs = exp_child.child_by_field_name("right")
            if assign_rhs and assign_rhs.type == "call":
                param_vec["contains_call"] = True
                # Check call nodes for logging
                # Overkill for now as a logging method call on the right-hand side of an assigment
                #  is usually not a logging call but rather an instantiation of a logging class
                # func_call = assign_rhs.child_by_field_name("function")
                # if re.search(keyword, func_call.text.decode("UTF-8").lower()):
                #     param_vec["contains_logging"] = True
        elif exp_child.type == "await":
            param_vec["contains_await"] = True
            assert exp_child.child_count == 2
            assert exp_child.children[0].type == "await"
            # Check await node for call
            if exp_child.children[1].type == "call":
                param_vec["contains_call"] = True
                # Eventual check for logging
        elif exp_child.type == "yield":
            param_vec["contains_yield"] = True

    def check_block(self, node: Node, param_vec: dict):
        for child in node.children:
            child: Node
            if not child.is_named or child.type == "comment":
                continue
            # Check expression statements for call, assignment, await, yield and logging(special case of call)
            if child.type == "expression_statement":
                # Block level expression statements rarely have more than one child, if so we just check them all
                # Example: web2py/gluon/contrib/login_methods/openid_auth.py line 551-556
                #           Has tuple form 'identifier.call(params), "text" * 10' for some reason
                # if len(child.children) != 1:
                if child.child_count != 1:
                    print(self.file)
                    print("Expression statement with more than one child!")
                    print(child)
                    for exp_child in child.children:
                        self.check_expression(exp_child, param_vec)
                else:
                    self.check_expression(child.children[0], param_vec)
                continue
            # Handle decorators so that they are counted as their respective class or function definition
            elif child.type == "decorated_definition":
                if child.child_by_field_name("definition").type == "class_definition":
                    param_vec["contains_class_definition"] = True
                elif child.child_by_field_name("definition").type == "function_definition":
                    param_vec["contains_function_definition"] = True
                else:
                    self.debug_helper(child)
                    raise RuntimeError("Decorated definition not handled")
                continue
            # Check if the child is a compound or simple statement
            for key, clause in zip(cfg.contains_only_statements, contains_types):
                if child.type == clause:
                    param_vec[key] = True
                    break
            else:
                if child.type != "expression_statement":
                    self.debug_helper(child)
                    raise RuntimeError("Child of block not in contains")

    def check_parent(self, node: Node, param_vec: dict):
        """Checks the node's parent. Not used for the module node."""
        if node.type in compound_statements:
            # if node.parent.type != "module":
            #     if node.parent.parent.type not in interesting_node_types:
            #         self.debug_helper(node)
            # Using the loop allows us to skip function decorators for the parent parameter
            parent = node
            while parent.parent:
                parent = parent.parent
                if self.args.mode == "bool":
                    if parent.type == "block":
                        if parent.parent.type in interesting_node_types:
                            param_vec["child_of_" + parent.parent.type] = True
                            return
                        else:
                            raise RuntimeError("Parent of block is not interesting")
                    if parent.type == "module":
                        param_vec["child_of_module"] = True
                        return
                elif self.args.mode == "onehot":
                    if parent.type == "block":
                        param_vec["parent"] = parent.parent.type
                        return
                    if parent.type == "module":
                        param_vec["parent"] = "module"
                        return
            raise RuntimeError("Could not find parent of node")
        elif node.type in extra_clauses:
            assert node.parent.type in compound_statements
            if self.args.mode == "bool":
                param_vec["child_of_" + node.parent.type] = True
            elif self.args.mode == "onehot":
                param_vec["parent"] = node.parent.type
        else:
            raise RuntimeError("Node type not handled")

    def fill_param_vecs_ast_new(self, training: bool = True) -> list:
        param_vectors = []
        visited_nodes = set()
        for node_type in interesting_node_types:
            node_query = self.lang.query("(" + node_type + ") @" + node_type)
            nodes = node_query.captures(self.tree.root_node)
            for node, tag in nodes:
                node: Node
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
                if node_type != "module":
                    self.check_parent(node, param_vec)
                # Check node
                body_block = ["class_definition",
                              "for_statement",
                              "function_definition",
                              "try_statement",
                              "while_statement",
                              "with_statement",
                              "else_clause"]
                if node_type in body_block:
                    self.check_block(node.child_by_field_name("body"), param_vec)
                elif node_type in ["if_statement", "elif_clause"]:
                    self.check_block(node.child_by_field_name("consequence"), param_vec)
                elif node_type in ["except_clause", "finally_clause"]:
                    found_block = False
                    for child in node.children:
                        if child.type == "block":
                            if found_block:
                                self.debug_helper(node)
                                raise RuntimeError("Multiple blocks in except or finally clause")
                            self.check_block(child, param_vec)
                            found_block = True

                if training:
                    # For extraction of features to a file, we need to return a list of lists of parameters
                    param_vec_list = list(param_vec.values())
                    # Check that no parameters have been accidentally added
                    if self.args.mode == "bool":
                        if len(param_vec_list) != len(par_vec_bool):
                            self.debug_helper(node)
                            print(par_vec_bool.keys())
                            print(param_vec.keys())
                            raise RuntimeError("Parameter vector length mismatch")
                    elif self.args.mode == "onehot":
                        if len(param_vec_list) != len(par_vec_onehot):
                            self.debug_helper(node)
                            print(par_vec_onehot.keys())
                            print(param_vec.keys())
                            raise RuntimeError("Parameter vector length mismatch")
                    param_vectors.append(param_vec_list)
                else:
                    # For prediction, the extracted parameters will be returned as a list of dicts for subsequent
                    # pandas.Dataframe creation
                    # Only recommend for a node that doesn't have logging already
                    if not param_vec["contains_logging"]:
                        param_vectors.append(param_vec)
        return param_vectors
