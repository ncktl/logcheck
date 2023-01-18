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

    def get_java_type(self, node: Node):
        if node.type == self.names.if_stmt:
            pass



    def check_parent(self, block_node: Node, param_vec: dict):
        """Find the block node's and parent's types.
        Collect information pertaining to the block node's ancestors and siblings"""

        # Naive
        param_vec["type"] = self.get_node_type(block_node.parent)
        # The block node's direct parent
        node: Node = block_node.parent
        if block_node.prev_sibling.type == "else":
            parent = block_node.parent
            param_vec["type"] = self.get_node_type("else")
        # Block of if_statement
        elif node.type == self.names.if_stmt:
            # else if
            if node.parent.type == self.names.if_stmt:
                assert node.parent.named_child_count == 3
                param_vec["parent"] = self.get_node_type(self.names.if_stmt)
                if block_node.prev_sibling.type == "else":
                    param_vec["type"] = self.get_node_type("else")
                else:
                    param_vec["type"] = self.get_node_type("elif")
            # else
            elif block_node.prev_sibling.type == "else":
                param_vec["parent"] = self.get_node_type(self.names.if_stmt)
                param_vec["type"] = self.get_node_type("else")

            # if
            elif node.parent.type == self.names.block: # TODO: Needs handling of all block types
                param_vec["parent"] = self.get_node_type(node.parent.parent)
                param_vec["type"] = self.get_node_type(self.names.if_stmt)
        else:
            pass
            # raise RuntimeError(f"Node type <{str(node.type)}> not handled during node type check in file {self.file} "
            #                    f"at line {block_node.start_point[0] + 1}")

        # parent = node.parent
        # param_vec["parent"] = self.get_node_type(parent)
        # param_vec["num_siblings"] = parent.named_child_count