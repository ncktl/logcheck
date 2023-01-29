from tree_sitter import Language, Tree, Node
from extractor import Extractor, traverse_sub_tree
from java_config import keyword

class JavaExtractor(Extractor):
    def __init__(self, src: str, lang: Language, tree: Tree, file, settings):
        super().__init__(src, lang, tree, file, settings)

    def check_expression(self, exp_child: Node, param_vec: dict):
        if exp_child.type == self.names.func_call:
            method_name = exp_child.child_by_field_name("name").text.decode("UTF-8")
            calling_object = exp_child.child_by_field_name("object").text.decode("UTF-8")
            object_and_method_str = (calling_object + ("." if calling_object else "") + method_name).lower()
            if keyword.match(object_and_method_str):
                param_vec["contains_logging"] = 1
            else:
                param_vec["contains_call"] += 1

    def check_block(self, block_node: Node, param_vec: dict):
        # Check the contents of the block, find logging
        for child in block_node.children:
            child: Node
            if not child.is_named or child.type == "line_comment" or child.type == "block_comment":
                continue
            if child.type == "expression_statement":
                for exp_child in child.children:
                    self.check_expression(exp_child, param_vec)

    def handle_block_parent(self, node):
        # TODO: Needs handling of all block types
        assert node.parent.type == self.names.block
        block_parent = node.parent
        logical_parent = node.parent.parent
        if block_parent.prev_sibling.type == "else":
            parent_type = "else"
        elif logical_parent.prev_sibling.type == "else":
            parent_type = "elif"
        else:
            parent_type = logical_parent.type
        return parent_type

    def check_parent(self, block_node: Node, param_vec: dict):
        """Find the block node's and parent's types.
        Collect information pertaining to the block node's ancestors and siblings"""

        # The block node's direct parent
        node: Node = block_node.parent
        node_type = node.type
        # The containing block
        containing_block = self.find_containing_block(node)
        if self.error_detected:
            return

        if node.parent == containing_block:
            # Special treatments for different kind of Java blocks
            if node.parent.type == self.names.block:
                parent_type = self.handle_block_parent(node)
            elif node.parent.type in ["enum_body_declarations", "switch_block_statement_group"]:
                parent_type = node.parent.parent.type
            else:
                parent_type = node.parent.type
                # Debug
                # print(node)
        else:
            parent_type = node.parent.type

        # Handle else-blocks
        if block_node.prev_sibling.type == "else":
            assert node.type == self.names.if_stmt
            parent_type = node.type  # Comment this out to consider the parent of the if-stmt as parent of the else
            node_type = "else"
        # Handle if-statements
        elif node.type == self.names.if_stmt:
            # else if
            if node.parent.type == self.names.if_stmt:
                assert node.parent.named_child_count == 3
                assert node.prev_sibling.type == "else"
                node_type = "elif"
            # regular if
            elif node.parent == containing_block:
                pass
            else:
                self.debug_helper(node)
                raise RuntimeError(f"if_stmt, child of <{str(node.parent.type)}> not handled")
        # Handle method declarations
        elif node.type == self.names.func_def:
            pass
        elif node.type in ["for_statement",
                           "do_statement",
                           "try_statement",
                           "catch_clause",
                           "constructor_declaration",
                           "switch_block",
                           ]:
            pass
        else:
            self.debug_helper(node)
            raise RuntimeError(f"Node type <{str(node.type)}> not handled")

        param_vec["type"] = self.get_node_type(node_type)
        assert parent_type not in ["class_declaration", "constructor_declaration"]
        param_vec["parent"] = self.get_node_type(parent_type)
        param_vec["num_siblings"] = containing_block.named_child_count
