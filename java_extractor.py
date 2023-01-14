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

    def check_parent(self, block_node: Node, param_vec: dict):
        # Get the block node's parent node which we consider to be the given node
        node: Node = block_node.parent
        parent = node.parent
        param_vec["parent"] = self.get_node_type(parent)
        param_vec["num_siblings"] = parent.named_child_count