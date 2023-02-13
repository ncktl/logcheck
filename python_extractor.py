from tree_sitter import Language, Tree, Node

from extractor import Extractor

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

    def get_func_call_str(self, func_call_node: Node):
        assert func_call_node.type == self.names.func_call
        func_call_str = func_call_node.child_by_field_name("function").text.decode("UTF-8").lower()
        return func_call_str

    def check_expression(self, exp_child: Node, param_vec: dict):
        """Checks an expression node for contained features of the parent block node"""

        # Call
        if exp_child.type == self.names.func_call:
            # Check call nodes for logging. Only if it's not a logging statement do we count it as a call.
            func_call_str = self.get_func_call_str(exp_child)
            if self.keyword.match(func_call_str):
                param_vec["contains_logging"] = 1
            else:
                param_vec[f"contains_{self.names.func_call}"] += 1
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
                # if self.keyword.match(func_call.text.decode("UTF-8").lower()):
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

    def check_block(self, block_node: Node, param_vec: dict):
        """Checks a block node for contained features, including logging by calling check_expression().
        Optionally also build the node's context."""

        # Calculate the depth and optionally build the context of the block
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
                    debug_str = self.debug_helper(child)
                    raise RuntimeError(f"Decorated definition not handled\n{debug_str}")
                continue
            # Build the contains_features
            # Check if the child is a compound or simple statement
            for key, clause in zip(self.names.contains_statements, self.names.statements):
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

        # Get the block node's parent node
        node: Node = block_node.parent
        if not node.is_named:
            self.error_detected = True
            return
        param_vec["type"] = self.get_node_type(node)
        # Get the containing block
        containing_block = self.find_containing_block(node)
        if self.error_detected:
            return
        param_vec["num_siblings"] = containing_block.named_child_count
        # Detect grandparent
        if containing_block.type == self.names.root:
            param_vec["grandparent"] = "rootception"
        else:
            parent = containing_block.parent
            second_containing_block = self.find_containing_block(parent)
            if self.error_detected:
                return
            # TODO: This is wrong, it calculates the number of uncles!
            param_vec["num_cousins"] = second_containing_block.named_child_count
            if parent.type == "else_clause":
                param_vec["grandparent"] = self.get_node_type(parent.parent)
            elif parent.type in self.names.compound_statements + self.names.extra_clauses:
                if second_containing_block.type == self.names.block:
                    param_vec["grandparent"] = self.get_node_type(second_containing_block.parent)
                elif second_containing_block.type == self.names.root:
                    param_vec["grandparent"] = self.get_node_type(second_containing_block)
                else:
                    debug_str = self.debug_helper(second_containing_block)
                    raise RuntimeError(f"Second containing block is neither block nor root\n{debug_str}")
            else:
                raise RuntimeError(f"Parent node type {parent.type} not handled")
        # Detect parent
        # Special treatment for "else" as Python has if..else, for..else, while..else and try..else
        # and they all use the same node type for the else clause (in Tree-Sitter at least).
        # Therefore we consider the parent of else as its parent (i.e. "if" in an if..else situation),
        # but for other "extra clauses" (case_clause, elif_clause, except_clause, except_group_clause, finally_clause)
        # we consider the grandparent as its parent (i.e. "if" for "except" in an if..try..except situation)
        # However, for the number of siblings we still consider the else's grandparent
        if node.type == "else_clause":
            param_vec["parent"] = self.get_node_type(node.parent)
        elif node.type in self.names.compound_statements + self.names.extra_clauses:
            if containing_block.type == self.names.block:
                param_vec["parent"] = self.get_node_type(containing_block.parent)
            elif containing_block.type == self.names.root:
                param_vec["parent"] = self.get_node_type(containing_block)
            else:
                debug_str = self.debug_helper(containing_block)
                raise RuntimeError(f"Containing block is neither block nor root\n{debug_str}")
        else:
            raise RuntimeError(f"Node type {node.type} not handled")
