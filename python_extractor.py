from tree_sitter import Language, Tree, Node
from extractor import Extractor, traverse_sub_tree
from config import par_vec_onehot, interesting_node_types, contains, most_node_types, par_vec_onehot_expanded
from config import compound_statements, simple_statements, extra_clauses, contains_types, keyword, node_dict
from config import par_vec_zhenhao
import config as cfg
import re
from copy import copy
import logging


class PythonExtractor(Extractor):
    def __init__(self, src: str, lang: Language, tree: Tree, file, args):
        """
        :param src: Source code to extract paramaeter vectors from
        :param lang: Treesitter language object
        :param tree: Treesitter tree object
        :param file: current file
        """

        super().__init__(src, lang, tree, file, args)
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        # Name of the Python logging module
        # self.keyword = "logg(ing|er)"

    def debug_helper(self, node: Node):
        print(self.file)
        print(f"Parent: {node.parent}")
        print(node)
        print(f"Children: {node.children}")
        # print(node.text.decode("UTF-8"))

    def check_expression(self, exp_child: Node, param_vec: dict):
        """Checks an expression node for contained features of the parent block node"""

        # Call
        if exp_child.type == "call":
            # Check call nodes for logging. Only if it's not a logging statement do we count it as a call.
            func_call = exp_child.child_by_field_name("function")
            if keyword.match(func_call.text.decode("UTF-8").lower()):
                if self.args.debug:
                    print("check_expression: ", func_call.text.decode("UTF-8"))
                    # "contains_logging" remains 0/1 as it is the target
                param_vec["contains_logging"] = 1
            else:
                param_vec["contains_call"] += 1
        # Assignment
        elif exp_child.type == "assignment" or exp_child.type == "augmented_assignment":
            param_vec["contains_assignment"] += 1
            # Check assignment nodes for calls
            assign_rhs = exp_child.child_by_field_name("right")
            if assign_rhs and assign_rhs.type == "call":
                param_vec["contains_call"] += 1
                # Check call nodes for logging?
                # No, because a logging method call on the right-hand side of an assigment
                # is usually not a logging call but rather an instantiation of a logging class
                # func_call = assign_rhs.child_by_field_name("function")
                # if re.search(keyword, func_call.text.decode("UTF-8").lower()):
                #     param_vec["contains_logging"] = 1
        # Await
        elif exp_child.type == "await":
            param_vec["contains_await"] += 1
            assert exp_child.child_count == 2
            assert exp_child.children[0].type == "await"
            # Check await node for call
            if exp_child.children[1].type == "call":
                param_vec["contains_call"] += 1
                # Eventual check for logging?
        # Yield
        elif exp_child.type == "yield":
            param_vec["contains_yield"] += 1

    def build_context_of_block_node(self, block_node: Node, param_vec: dict):
        """Build the context of the block like in Zhenhao et al."""

        # Find the containing (function) definition
        def_node = block_node.parent
        # For doing it exactly like Zhenhao et al.:
        if self.args.zhenhao:
            while def_node.type != "function_definition":
                if def_node.type == "ERROR":
                    param_vec["type"] = node_dict[def_node.type]
                    param_vec["context"] = node_dict[def_node.type]
                    return
                def_node = def_node.parent
        # For our approach of looking at interesting nodes:
        # There will be blocks that aren't inside a function/method
        # This will limit the context to a containing class in case of func def >..> class def >..> block
        else:
            while def_node.type not in ["module", "class_definition", "function_definition"]:
                if def_node.type == "ERROR":
                    param_vec["type"] = node_dict[def_node.type]
                    param_vec["parent"] = node_dict[def_node.type]
                    param_vec["context"] = node_dict[def_node.type]
                    return
                def_node = def_node.parent

        def add_relevant_node(node: Node, context: list):
            if node.is_named and node.type in most_node_types:
                if node.type == "call" \
                        and keyword.match(node.child_by_field_name("function").text.decode("UTF-8").lower()):
                    if self.args.debug:
                        print("add_relevant_node: ", node.child_by_field_name("function").text.decode("UTF-8"))
                    return
                else:
                    context.append(node_dict[node.type])

        context = []
        # Add the ast nodes that came before the block in its parent (func|class) def or module
        for node in traverse_sub_tree(def_node, block_node):
            add_relevant_node(node, context)
        # Debug
        if self.args.debug:
            context.append("%%%%")
        # /Debug
        # Add the ast nodes in the block and it's children
        for node in traverse_sub_tree(block_node):
            add_relevant_node(node, context)
        param_vec["context"] = "".join(context)

    def check_block(self, block_node: Node, param_vec: dict):
        """Checks a block node for contained features, including logging by calling check_expression().
        Optionally also build the node's context."""

        # Build the context of the block like in Zhenhao et al.
        if self.args.alt:
            self.build_context_of_block_node(block_node, param_vec)

        # Check the contents of the block, find logging
        for child in block_node.children:
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
                    # print(self.file)
                    # print("Expression statement with more than one child!")
                    # print(child)
                    for exp_child in child.children:
                        self.check_expression(exp_child, param_vec)
                else:
                    self.check_expression(child.children[0], param_vec)
                continue
            # Handle decorators so that they are counted as their respective class or function definition
            elif child.type == "decorated_definition":
                if child.child_by_field_name("definition").type == "class_definition":
                    param_vec["contains_class_definition"] += 1
                elif child.child_by_field_name("definition").type == "function_definition":
                    param_vec["contains_function_definition"] += 1
                else:
                    self.debug_helper(child)
                    raise RuntimeError("Decorated definition not handled")
                continue
            # Build the contains_features
            # Check if the child is a compound or simple statement
            for key, clause in zip(cfg.contains_only_statements, contains_types):
                if child.type == clause:
                    param_vec[key] += 1
                    break
            # else:
            #     if child.type != "ERROR":
            #         self.debug_helper(child)
            #         raise RuntimeError("Child of block not in contains")

    def check_parent(self, node: Node, param_vec: dict):
        """Checks the node's parent. Not used for the module node."""

        parent = None
        if node.type in compound_statements:
            # Using the loop allows us to skip function decorators for the parent parameter
            parent = node
            while parent.parent:
                parent = parent.parent
                if parent.type == "block":
                    parent = parent.parent
                    break
                if parent.type == "module":
                    break
                if parent.type == "ERROR":
                    param_vec["parent"] = node_dict[parent.type]
                    param_vec["type"] = node_dict[parent.type]
                    return
            else:
                self.debug_helper(node)
                raise RuntimeError("Could not find parent of node")
        elif node.type in extra_clauses:
            parent = node.parent
        else:
            raise RuntimeError("Node type not handled")
        assert parent is not None
        param_vec["parent"] = node_dict[parent.type]
        param_vec["num_siblings"] = parent.named_child_count

    def fill_param_vecs_ast_new(self, training: bool = True) -> list:
        param_vectors = []
        visited_nodes = set()
        for node_type in interesting_node_types:
            node_query = self.lang.query("(" + node_type + ") @" + node_type)
            nodes = node_query.captures(self.tree.root_node)
            for node, tag in nodes:
                node: Node
                # Uniqueness check is unnecessary? Yes!
                if (node.start_byte, node.end_byte) in visited_nodes:
                    raise RuntimeError
                else:
                    visited_nodes.add((node.start_byte, node.end_byte))
                if not node.is_named:
                    continue
                # Parameter vector for this node
                if self.args.alt:
                    param_vec_used = par_vec_onehot_expanded
                else:
                    param_vec_used = par_vec_onehot
                param_vec = copy(param_vec_used)
                param_vec["type"] = node_dict[node_type]
                param_vec["location"] = f"{node.start_point[0]};{node.start_point[1]}-" \
                                        f"{node.end_point[0]};{node.end_point[1]}"
                if self.args.alt:
                    param_vec["length"] = node.end_point[0] - node.start_point[0] + 1
                if self.args.debug:
                    param_vec = {"line": node.start_point[0] + 1, **param_vec}
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
                    if not self.args.debug and len(param_vec_list) != len(param_vec_used):
                        self.debug_helper(node)
                        print(param_vec_used.keys())
                        print(param_vec.keys())
                        raise RuntimeError("Parameter vector length mismatch")
                    # Debug
                    # if self.args.debug:
                    #     if node_type == "function_definition" and param_vec["parent"] == "function_definition":
                    #         if param_vec["context"].startswith("2|3|24|27|27|27|27|3|3|27|25|27|25|27|8|25|3|27|25|27"
                    #                                            "|25|27|8|25"):
                    #             self.debug_helper(node)
                    # /Debug
                    param_vectors.append(param_vec_list)
                else:
                    # For prediction, the extracted parameters will be returned as a list of dicts for subsequent
                    # pandas.Dataframe creation
                    # Only recommend for a node that doesn't have logging already
                    if not param_vec["contains_logging"]:
                        param_vectors.append(param_vec)
        return param_vectors

    def fill_param_vecs_zhenhao(self, training: bool = True) -> list:
        """Extracts features like Zhenhao et al., i.e. looks at all blocks that are inside functions."""
        param_vectors = []
        function_definiton_query = self.lang.query("(function_definition) @funcdef")
        function_definiton_nodes = function_definiton_query.captures(self.tree.root_node)
        block_query = self.lang.query("(block) @block")
        for funcdef_node, tag in function_definiton_nodes:
            funcdef_node: Node
            block_nodes = block_query.captures(funcdef_node)
            for block_node, tag in block_nodes:
                block_node: Node
                param_vec = copy(par_vec_zhenhao)
                try:
                    param_vec["type"] = node_dict[block_node.parent.type]
                except KeyError as e:
                    param_vec["type"] = node_dict["ERROR"]
                    self.logger.error(f"Encountered bad code in file {self.file} in line "
                                      f"{block_node.parent.start_point[0] + 1}")

                param_vec["location"] = f"{block_node.start_point[0]};{block_node.start_point[1]}-" \
                                        f"{block_node.end_point[0]};{block_node.end_point[1]}"
                if self.args.debug:
                    param_vec = {"line": block_node.start_point[0] + 1, **param_vec}
                self.build_context_of_block_node(block_node, param_vec)
                # Check for logging, slimmed version of check_block() and check_expression():
                for child in block_node.children:
                    child: Node
                    # Check expression statements for logging(special case of call)
                    if child.type == "expression_statement":

                        def check_micro_expression(exp_child, param_vec):
                            if exp_child.type == "call":
                                # Check call nodes for logging
                                func_call = exp_child.child_by_field_name("function")
                                # if re.search(keyword, func_call.text.decode("UTF-8").lower()):
                                if keyword.match(func_call.text.decode("UTF-8").lower()):
                                    if self.args.debug:
                                        print("Zhenhao: ", func_call.text.decode("UTF-8"))
                                    param_vec["contains_logging"] = 1

                        if child.child_count != 1:
                            for exp_child in child.children:
                                check_micro_expression(exp_child, param_vec)
                        else:
                            check_micro_expression(child.children[0], param_vec)

                if training:
                    param_vec_list = list(param_vec.values())
                    # # Check that no parameters have been accidentally added
                    # if len(param_vec_list) != len(par_vec_zhenhao):
                    #     self.debug_helper(block_node)
                    #     print(par_vec_zhenhao.keys())
                    #     print(param_vec.keys())
                    #     raise RuntimeError("Parameter vector length mismatch")
                    param_vectors.append(param_vec_list)
                else:
                    # Prediction
                    pass
        return param_vectors
