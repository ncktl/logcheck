import logging
from copy import copy

from tree_sitter import Language, Tree, Node

import python_config as cfg
from python_config import compound_statements, extra_clauses, statements, keyword, node_dict
from python_config import most_node_types, par_vec_onehot_expanded
from extractor import Extractor, traverse_sub_tree

extra_debugging = False


class PythonExtractor(Extractor):
    def __init__(self, src: str, lang: Language, tree: Tree, file, settings):
        """
        :param src: Source code to extract paramaeter vectors from
        :param lang: Treesitter language object
        :param tree: Treesitter tree object
        :param file: current file
        """
        super().__init__(src, lang, tree, file, settings)

    def check_expression(self, exp_child: Node, param_vec: dict):
        """Checks an expression node for contained features of the parent block node"""

        # Call
        if exp_child.type == self.names.func_call:
            # Check call nodes for logging. Only if it's not a logging statement do we count it as a call.
            func_call = exp_child.child_by_field_name("function")
            if keyword.match(func_call.text.decode("UTF-8").lower()):
                if self.settings.debug and extra_debugging:
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
        # Remains 0 if the given block node is the child of a function definition
        depth_from_def = 0
        while def_node.type != self.names.func_def:
            # Stop when encountering an error
            if def_node.type == self.names.error:
                self.error_detected = True
                return
            def_node = def_node.parent
            depth_from_def += 1
        param_vec["depth_from_def"] = depth_from_def

        def add_relevant_node(node: Node, context: list):
            if node.is_named and node.type in most_node_types:
                if node.type == "call" \
                        and keyword.match(node.child_by_field_name("function").text.decode("UTF-8").lower()):
                    if self.settings.debug and extra_debugging:
                        print("add_relevant_node: ", node.child_by_field_name("function").text.decode("UTF-8"))
                    return
                else:
                    context.append(self.get_node_type(node, encode=True))

        context = []
        # Add the ast nodes that came before the block in its parent (func|class) def or module
        for node in traverse_sub_tree(def_node, block_node):
            add_relevant_node(node, context)
        # Debug
        if self.settings.debug:
            context.append("%%%%")
        # /Debug
        # Add the ast nodes in the block and it's children
        for node in traverse_sub_tree(block_node):
            add_relevant_node(node, context)
        param_vec["context"] = "".join(context)

    def check_block(self, block_node: Node, param_vec: dict):
        """Checks a block node for contained features, including logging by calling check_expression().
        Optionally also build the node's context."""

        if self.settings.alt:
            # Build the context of the block like in Zhenhao et al.
            self.build_context_of_block_node(block_node, param_vec)
            if self.error_detected:
                return

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
                for exp_child in child.children:
                    self.check_expression(exp_child, param_vec)
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

    def check_parent(self, block_node: Node, param_vec: dict):
        """Find the block node's and parent's types.
        Collect information pertaining to the block node's ancestors and siblings"""

        # Find the block node's "type". For Python, this is always simply its parent's type.
        try:
            param_vec["type"] = self.get_node_type(block_node.parent)
        except KeyError as e:
            self.error_detected = True
            self.logger.error(f"Node type <{str(block_node.parent.type)}> key error in file {self.file} "
                              f"in line {block_node.parent.start_point[0] + 1}")
            return

        # Get the block node's parent node
        node: Node = block_node.parent
        # Get the containing block
        parent = self.find_containing_block(node)
        # Special treatment for "else" as Python has if..else, for..else, while..else and try..else
        # and they all use the same node type for the else clause (in Tree-Sitter at least).
        # Therefore we consider the parent of else as its parent (i.e. "if" in an if..else situation),
        # but for other "extra clauses" (case_clause, elif_clause, except_clause, except_group_clause, finally_clause)
        # we consider the grandparent as its parent (i.e. "if" for "except" in an if..try..except situation)
        # However, for the number of siblings we still consider the else's grandparent
        if node.type == "else_clause":
            param_vec["parent"] = self.get_node_type(node.parent)
        elif node.type in compound_statements + extra_clauses:
            if parent.type == self.names.block:
                param_vec["parent"] = self.get_node_type(parent.parent)
            elif parent.type == self.names.root:
                param_vec["parent"] = self.get_node_type(parent)
        else:
            err_str = f"Node type {node.type} not handled"
            raise RuntimeError(err_str)
        assert parent is not None
        param_vec["num_siblings"] = parent.named_child_count
