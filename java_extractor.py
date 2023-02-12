from tree_sitter import Language, Tree, Node

from extractor import Extractor


class JavaExtractor(Extractor):
    def __init__(self, src: str, lang: Language, tree: Tree, file, settings):
        super().__init__(src, lang, tree, file, settings)

    def get_func_call_str(self, func_call_node: Node):
        assert func_call_node.type == self.names.func_call
        method_name = func_call_node.child_by_field_name("name").text.decode("UTF-8")
        calling_object = func_call_node.child_by_field_name("object")
        calling_object_str = calling_object.text.decode("UTF-8") if calling_object else ""
        func_call_str = (calling_object_str + ("." if calling_object else "") + method_name).lower()
        return func_call_str

    def check_expression(self, exp_child: Node, param_vec: dict):
        if exp_child.type == self.names.func_call:
            func_call_str = self.get_func_call_str(exp_child)
            if self.keyword.match(func_call_str):
                param_vec["contains_logging"] = 1
            else:
                param_vec[f"contains_{self.names.func_call}"] += 1
        elif exp_child.type in self.names.expressions:
            param_vec[f"contains_{exp_child.type}"] += 1
        elif exp_child.is_named and exp_child.type not in ["line_comment", "block_comment"]:
            # self.unhandled_node_types.add(exp_child.type)
            self.logger.error(f"check_expression: Unhandled node type: {exp_child.type}")

    def check_block(self, block_node: Node, param_vec: dict, recursion_level=0):

        if recursion_level == 0:
            self.build_context_of_block_node(block_node, param_vec)
            if self.error_detected:
                return
        # elif recursion_level > 2:
        #     debug_str = self.debug_helper(block_node)
        #     self.logger.error(f"Check_block recursion {recursion_level}\n{debug_str}")

        #  We check for block nodes directly inside this block node,
        #  include their content in this block's features and put them into the visited nodes set?
        #  The inner block has its own scope, but logging statements inside the inner block can essentially
        #  be considered as if they were in the outer block. Also, there are Instance initialization blocks
        # Check the contents of the block, find logging
        for child in block_node.children:
            child: Node
            if not child.is_named or child.type == "line_comment" or child.type == "block_comment":
                continue
            if child.type == "expression_statement":
                for exp_child in child.children:
                    self.check_expression(exp_child, param_vec)
            elif child.type == self.names.block:
                # We consider the block child to be part of the parent block
                self.check_block(child, param_vec, recursion_level + 1)
                # Add the block child to visited nodes so it will be skipped
                check_value = (child.start_byte, child.end_byte)
                self.visited_nodes.add(check_value)
            # elif child.type == "local_variable_declaration":
            #     param_vec["contains_local_variable_declaration"] += 1
            elif child.type in self.names.statements:
                # TODO: Is this more elegant than the approach for Python?
                param_vec[f"contains_{child.type}"] += 1
            elif child.type == self.names.error:
                self.error_detected = True
                return
            else:
                # self.unhandled_node_types.add(child.type)
                self.logger.error(f"check_block: Unhandled node type: {child.type}")

    def handle_block_parent(self, node):
        assert node.parent.type == self.names.block
        block_parent = node.parent
        logical_parent = node.parent.parent
        if block_parent.prev_sibling and block_parent.prev_sibling.type == "else":
            parent_type = "else"
        elif logical_parent.prev_sibling and logical_parent.prev_sibling.type == "else":
            parent_type = "elif"
        else:
            parent_type = logical_parent.type
        return parent_type

    def check_parent(self, block_node: Node, param_vec: dict):
        """Find the block node's and parent's types.
        Collect information pertaining to the block node's ancestors and siblings"""

        # The block node's direct parent
        node: Node = block_node.parent
        # The containing block
        containing_block = self.find_containing_block(node)

        # Find the node's type
        # Handle regular blocks
        if block_node.type == self.names.block:
            node_type = node.type
            # TODO: There shouldn't be any regular block types with block parents being processed due to check_block()!
            if node.type == self.names.block:
                debug_str = self.debug_helper(block_node)
                self.logger.error(f"Block, child of block\n{debug_str}")
            # Rarely a block is the child of a non-regular block type,
            # e.g. as a child of a switch_block_statement_group like in
            # Ghidra/Framework/SoftwareModeling/src/main/java/ghidra/pcodeCPort/slghsymbol/SymbolTable.java line 337
            # In that case add the parent block to the visited nodes set (the regular block nodes are visited first)
            elif node.type in self.names.block_types:
                debug_str = self.debug_helper(block_node)
                self.logger.error(f"Block, child of non reg block\n{debug_str}")
                # Assumption: This doesn't happen twice in a row
                assert node.parent.type not in self.names.block_types
                # Add the block type parent to visited nodes so it will be skipped
                check_value = (node.start_byte, node.end_byte)
                self.visited_nodes.add(check_value)
                # Use the parent's containing block instead
                containing_block = self.find_containing_block(node.parent)
        # Handle block nodes that aren't of type "block", like constructor_body
        elif block_node.type in self.names.block_types:
            node_type = block_node.type
        else:
            raise NotImplementedError("Block type not handled")

        if self.error_detected:
            return

        # Handle else-blocks
        if block_node.prev_sibling.type == "else":
            assert node.type == self.names.if_stmt
            # parent_type = node.type  # Comment this out to consider the parent of the if-stmt as parent of the else
            node_type = "else"
        # Handle if-statements
        elif node.type == self.names.if_stmt:
            # else if
            if node.parent.type == self.names.if_stmt:
                if node.prev_sibling.type == "else":
                    node_type = "elif"
                # else -> regular if

            # # regular if
            # elif node.parent == containing_block:
            #     pass
            # # Loops without curly brackets and exactly one statement
            # elif node.parent.type in self.names.loops:
            #     pass
            # else:
            #     debug_str = self.debug_helper(node)
            #     raise RuntimeError(f"if_stmt, child of <{str(node.parent.type)}> not handled\n{debug_str}")

        # Handle method declarations
        elif node_type == self.names.func_def:
            pass
        elif node_type in [
            "for_statement",
            "enhanced_for_statement",
            "while_statement",
            "do_statement",
            "try_statement",
            "try_with_resources_statement",
            "catch_clause",
            "constructor_declaration",
            "switch_block",
            "synchronized_statement",
            "finally_clause",
            "lambda_expression",
            "switch_block_statement_group",
            "block",  # TODO Included for debug
            "constructor_body",
            "class_body",
            "switch_rule",
            "compact_constructor_declaration",
            "labeled_statement",
            "interface_declaration",
            "static_initializer",
        ]:
            pass
        else:
            # self.unhandled_node_types.add(node.type)
            self.logger.error(f"check_parent: Unhandled node type: {node.type}")
            # debug_str = self.debug_helper(node)
            # raise RuntimeError(f"Node type <{str(node_type)}> not handled:\n{debug_str}")

        # Find the parent's type
        # Most cases: The node is inside another block
        if node.parent == containing_block:
            # Special treatments for different kind of Java blocks
            if node.parent.type == self.names.block:
                parent_type = self.handle_block_parent(node)
            elif node.parent.type in [
                "enum_body_declarations",
                "switch_block_statement_group",
            ]:
                parent_type = node.parent.parent.type
            else:
                parent_type = node.parent.type
                # Debug
                # print(node)
        # Extra clauses and lambda
        elif node_type in [
            "lambda_expression",
            "switch_block_statement_group",
            "catch_clause",
            "finally_clause",
            "elif",
            "else",
        ]:
            parent_type = containing_block.parent.type
            # Debug
            # if block_node.type == "switch_block_statement_group":
            #     print(containing_block.parent.type)
        else:
            parent_type = node.parent.type

        param_vec["type"] = self.get_node_type(node_type)
        # assert parent_type not in ["class_declaration", "constructor_declaration"]
        # TODO Look at those cases
        param_vec["parent"] = self.get_node_type(parent_type)
        param_vec["num_siblings"] = containing_block.named_child_count
