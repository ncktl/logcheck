import logging
from copy import copy

from tree_sitter import Language, Tree, Node

import config as cfg
from config import compound_statements, extra_clauses, statements, keyword, node_dict
from config import most_node_types, par_vec_onehot_expanded
from extractor import Extractor, traverse_sub_tree

extra_debugging = False


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
                if self.args.debug and extra_debugging:
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
                # is usually not a logging call but rather an instantiation of a logging class?
                # func_call = assign_rhs.child_by_field_name("function")
                # if keyword.match(func_call.text.decode("UTF-8").lower()):
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
        """Build the context of the block and computes depth from def"""

        # Find the containing (function) definition
        def_node = block_node.parent
        # Measure the depth of nesting from the node's containing func/class def or module
        depth_from_def = 0
        while def_node.type != "function_definition":
            if def_node.type == "ERROR":
                param_vec["type"] = node_dict[def_node.type]
                param_vec["context"] = node_dict[def_node.type]
                return
            def_node = def_node.parent
            depth_from_def += 1
        param_vec["depth_from_def"] = depth_from_def

        def add_relevant_node(node: Node, context: list):
            if node.is_named and node.type in most_node_types:
                if node.type == "call" \
                        and keyword.match(node.child_by_field_name("function").text.decode("UTF-8").lower()):
                    if self.args.debug and extra_debugging:
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
            for key, clause in zip(cfg.contains_only_statements, statements):
                if child.type == clause:
                    param_vec[key] += 1
                    break
            # else:
            #     if child.type != "ERROR":
            #         self.debug_helper(child)
            #         raise RuntimeError("Child of block not in contains")

    def check_parent(self, node: Node, param_vec: dict):
        """Checks the node's parent. Not used for the module node."""

        # We try to find the node's logical parent,
        # and the position of the highest ancestor of the node among the logical parent's children (sibling_index)
        # This allows us e.g. to find the sibling_index of a function definition that is decorated among its enclosing
        # block. Otherwise, the decorator would be considered the parent and the sibling_index would always be 0
        parent = None
        considered_node = node
        # For compound statements (like function definition, if-statement, for-statement, etc.)
        # we consider the enclosing block's parent as logical parent,
        # or the module, if there is no block between the compound statement and the module node
        # (module, the root, is essentially a block)
        if node.type in compound_statements:
            # Using the loop allows us to skip function decorators for the parent parameter
            parent = considered_node.parent
            while parent is not None:
                if parent.type == "block":
                    # parent = parent.parent
                    param_vec["parent"] = node_dict[parent.parent.type]
                    break
                if parent.type == "module":
                    param_vec["parent"] = node_dict[parent.type]
                    break
                if parent.type == "ERROR":
                    param_vec["parent"] = node_dict[parent.type]
                    param_vec["type"] = node_dict[parent.type]
                    return
                considered_node = parent
                parent = parent.parent
            else:
                self.debug_helper(node)
                raise RuntimeError("Could not find parent of node")
        # For the extra clauses (like else, elif, except, finally,etc.)
        # we consider the parent compound statement as logical parent
        elif node.type in extra_clauses:
            parent = node.parent
            param_vec["parent"] = node_dict[parent.type]
        else:
            err_str = f"Node type {node.type} not handled"
            raise RuntimeError(err_str)
        assert parent is not None
        # param_vec["parent"] = node_dict[parent.type]
        param_vec["num_siblings"] = parent.named_child_count
        # The position of the node among its siblings, (e.g. node is the 2nd child of its parent)
        # Actually makes the performance WORSE with rnd_forest classifier
        # TODO: Check if +1 is best
        # param_vec["sibling_index"] = node.parent.children.index(node) + 1
        param_vec["sibling_index"] = parent.children.index(considered_node) + 1

    def fill_param_vectors(self, training: bool = True) -> list:
        """Extracts features like Zhenhao et al., i.e. looks at all blocks that are inside functions."""
        param_vectors = []
        visited_nodes = set()
        function_definiton_query = self.lang.query("(function_definition) @funcdef")
        function_definiton_nodes = function_definiton_query.captures(self.tree.root_node)
        block_query = self.lang.query("(block) @block")
        for funcdef_node, tag in function_definiton_nodes:
            funcdef_node: Node
            block_nodes = block_query.captures(funcdef_node)
            for block_node, tag in block_nodes:
                block_node: Node
                # Uniqueness check using start and end byte tuple
                check_value = (block_node.start_byte, block_node.end_byte)
                if check_value in visited_nodes:
                    continue
                else:
                    visited_nodes.add(check_value)
                param_vec = copy(par_vec_onehot_expanded)
                try:
                    param_vec["type"] = node_dict[block_node.parent.type]
                except KeyError as e:
                    self.logger.error(f"Node type <{str(block_node.parent.type)}> key error in file {self.file} "
                                      f"in line {block_node.parent.start_point[0] + 1}")
                    continue
                param_vec["location"] = f"{block_node.start_point[0]};{block_node.start_point[1]}-" \
                                        f"{block_node.end_point[0]};{block_node.end_point[1]}"
                # Add +2 instead because the block lacks the parent's line?
                param_vec["length"] = block_node.end_point[0] - block_node.start_point[0] + 1
                param_vec["num_children"] = block_node.named_child_count
                # Check parent
                self.check_parent(block_node.parent, param_vec)
                # Check node
                self.check_block(block_node, param_vec)

                if training:
                    param_vec_list = list(param_vec.values())
                    # Check that no parameters have been accidentally added
                    if len(param_vec_list) != len(par_vec_onehot_expanded):
                        self.debug_helper(block_node)
                        print(par_vec_onehot_expanded.keys())
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
