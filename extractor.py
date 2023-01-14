import logging
from copy import copy

from tree_sitter import Language, Tree, Node, TreeCursor

# TODO: General config
from python_config import par_vec_onehot_expanded, node_dict, node_names


def print_children(node: Node, level=0, maxdepth=999):
    if level > maxdepth:
        return
    print(f"Line {node.start_point[0] + 1}: " + (level * 2) * "  " + str(node))
    ### Debug
    # if node.type == "elif_clause":
    #     special = node.child_by_field_name("consequence")
    #     print("ELIF")
    #     print(special)
    #     print("ELIF")
    # if node.type == "else_clause":
    #     special = node.child_by_field_name("body")
    #     print("Else")
    #     print(special)
    #     print("Else")
    # if node.type == "try_statement":
    #     print("Try children:")
    #     for child in node.children:
    #         if child.is_named:
    #             print(child)
    #     print("Get body by field name:")
    #     special = node.child_by_field_name("body")
    #     print(special)
    #     print("Try handling over")
    # if node.type == "named_expression":
    #     print("Named expression", node)
    #     print("Parent", node.parent)
    #     print("Children", node.children)
    # if node.type == "block":
    #     print("Children:", node.children)
    # if node.type == "assignment":
    #     print("Parent", node.parent)
    #     print("Left: ", node.child_by_field_name("left"))
    #     print("Right: ", node.child_by_field_name("right"))
    #     print("Type: ", node.child_by_field_name("type"))
    # if node.type == "augmented_assignment":
    #     print("Parent", node.parent)
    #     print("Left: ", node.child_by_field_name("left"))
    #     print("Right: ", node.child_by_field_name("right"))
    for child in node.children:
        if child.is_named: print_children(child, level + 1)
        # print_children(child, level + 1)


def traverse_sub_tree(root_node: Node, stop_node: Node = None):
    """Traverses the sub-ast of the given root node and yields the nodes.
    If a stop node is given, traversal ends there (inclusive)"""
    cursor: TreeCursor = root_node.walk()

    reached_root = False
    while not reached_root:
        yield cursor.node

        if cursor.node == stop_node:
            reached_root = True
            continue

        if cursor.goto_first_child():
            continue
        if cursor.goto_next_sibling():
            continue

        retracing = True
        while retracing:
            if not cursor.goto_parent():
                retracing = False
                reached_root = True
            elif cursor.goto_next_sibling():
                retracing = False





class Extractor:
    def __init__(self, src: str, lang: Language, tree: Tree, file, settings):
        """
        :param src: Source code to extract paramaeter vectors from
        :param lang: Tree-sitter language object
        :param tree: Treesitter tree object
        :param file_path: Pathlib object of the file to analyze
        """

        self.src: str = src
        self.lang: Language = lang
        self.tree: Tree = tree
        self.file = file
        self.lines: list = src.splitlines()
        self.settings = settings
        self.names = node_names[self.settings.language]
        self.logger = logging.getLogger(self.settings.language.capitalize() + "Extractor")
        self.logger.setLevel(logging.DEBUG)

    def debug_helper(self, node: Node):
        print(self.file)
        print(f"Parent: {node.parent}")
        print(node)
        print(f"Children: {node.children}")
        # print(node.text.decode("UTF-8"))

    def get_node_type(self, node: Node):
        """Returns the node type of the given node. If the -a/--alt flag is set, the type is returned ascii encoded."""
        if self.settings.alt:
            return node_dict[node.type]
        else:
            return node.type

    def fill_param_vectors(self, training: bool = True) -> list:
        """Extracts features like Zhenhao et al., i.e. looks at all blocks that are inside functions."""
        param_vectors = []
        visited_nodes = set()
        func_def_query = self.lang.query(f"({self.names.func_def}) @funcdef")
        func_def_nodes = func_def_query.captures(self.tree.root_node)
        block_query = self.lang.query("(block) @block")
        for funcdef_node, tag in func_def_nodes:
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
                    param_vec["type"] = self.get_node_type(block_node.parent)
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
                self.check_parent(block_node, param_vec)
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
