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

    def get_java_type_and_parent(self, node: Node):

        def handle_block_parent(node):
            # TODO: Needs handling of all block types
            assert node.parent.type == self.names.block
            parent = node.parent.parent
            java_type = node.type
            if node.parent.prev_sibling.type == "else":
                parent_type = "else"
            elif parent.prev_sibling.type == "else":
                parent_type = "elif"
            else:
                parent_type = parent.type
            return java_type, parent_type, parent

        if node.type == self.names.if_stmt:
            # else if
            if node.parent.type == self.names.if_stmt:
                assert node.parent.named_child_count == 3
                parent = node.parent
                parent_type = parent.type
                java_type = "elif"
            # if
            elif node.parent.type == self.names.block:
                java_type, parent_type, parent = handle_block_parent(node)
            else:
                raise RuntimeError(f"if_stmt, child of <{str(node.parent.type)}> not handled")
        elif node.type == self.names.func_def:
            java_type = node.type
            if node.parent.type == self.names.block:
                java_type, parent_type, parent = handle_block_parent(node)
            else:
                parent = node.parent
                parent_type = parent.type
        else:
            raise RuntimeError(f"Node type <{str(node.type)}> not handled")
        return self.get_node_type(java_type), self.get_node_type(parent_type), parent.named_child_count



    def check_parent(self, block_node: Node, param_vec: dict):
        """Find the block node's and parent's types.
        Collect information pertaining to the block node's ancestors and siblings"""

        # Naive
        param_vec["type"] = self.get_node_type(block_node.parent)
        # The block node's direct parent
        node: Node = block_node.parent
        if block_node.prev_sibling.type == "else":
            parent = block_node.parent
            num_siblings = parent.named_child_count
            param_vec["type"] = self.get_node_type("else")
        else:
            param_vec["type"], parent, num_siblings = self.get_java_type_and_parent(node)

        param_vec["parent"] = self.get_node_type(parent)
        param_vec["num_siblings"] = num_siblings
