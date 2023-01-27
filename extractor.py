import logging
from copy import copy

from tree_sitter import Language, Tree, Node, TreeCursor

# TODO: General config
from python_config import par_vec_onehot_expanded, node_dict, node_names


def print_children(node: Node, level=0, print_unnamed=False, maxdepth=999):
    if level > maxdepth:
        return
    if node.is_named or print_unnamed:
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
        # if child.is_named: print_children(child, level + 1)
        print_children(child, level + 1, print_unnamed)


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
        # names is a dataclass containing Tree-Sitter's node type names for the current programming language
        # E.g. if self.settings.language == "python" then self.names.func_def == "function_definition"
        self.names = node_names[self.settings.language]
        # The parsed source code files can contain syntax errors. If a syntax error is discovered during processing of
        # a block, this flag will be raised and the block discarded.
        self.error_detected = False
        self.logger = logging.getLogger(self.settings.language.capitalize() + "Extractor")
        self.logger.setLevel(logging.DEBUG)

    def debug_helper(self, node: Node):
        print(self.file)
        print(f"Parent: {node.parent}")
        print(node)
        print(f"Children: {node.children}")
        # print(node.text.decode("UTF-8"))

    def get_node_type(self, node_or_str, encode=False):
        """Returns the node type of the given node or type string.
        If the -a/--alt flag is set, the type is returned ascii encoded."""
        if type(node_or_str) == str:
            key = node_or_str
        elif type(node_or_str) == Node:
            key = node_or_str.type
        else:
            raise RuntimeError("Bad input type given to get_node_type()")
        if self.settings.encode or encode:
            return node_dict[key]
        else:
            return key

    def find_containing_block(self, node: Node):
        """Returns the lowest block node containing the node."""
        parent = node.parent
        while parent is not None:
            # TODO: Handle other block types
            if parent.type in [self.names.block, self.names.root]:
                return parent
            if parent.type == self.names.error:
                self.error_detected = True
                return parent
            parent = parent.parent
        else:
            self.debug_helper(node)
            raise RuntimeError("Could not find containing block")

    def fill_param_vectors(self, training: bool = True) -> list:
        """Extracts features like Zhenhao et al., i.e. looks at all blocks that are inside functions."""
        self.error_detected = False
        param_vectors = []
        visited_nodes = set()
        func_def_query = self.lang.query(f"({self.names.func_def}) @funcdef")
        func_def_nodes = func_def_query.captures(self.tree.root_node)
        block_query = self.lang.query("(block) @block")
        for funcdef_node, func_tag in func_def_nodes:
            funcdef_node: Node
            block_nodes = block_query.captures(funcdef_node)
            for block_node, block_tag in block_nodes:
                block_node: Node
                # Uniqueness check using start and end byte tuple
                check_value = (block_node.start_byte, block_node.end_byte)
                if check_value in visited_nodes:
                    continue
                else:
                    visited_nodes.add(check_value)
                # Create a parameter vector for the block node and enter some information
                param_vec = copy(par_vec_onehot_expanded)
                param_vec["location"] = f"{block_node.start_point[0]};{block_node.start_point[1]}-" \
                                        f"{block_node.end_point[0]};{block_node.end_point[1]}"
                # Add +2 instead because the block lacks the parent's line?
                param_vec["length"] = block_node.end_point[0] - block_node.start_point[0] + 1
                param_vec["num_children"] = block_node.named_child_count
                # Collect information from the block node's ancestors and siblings
                self.check_parent(block_node, param_vec)
                # Discard blocks for which syntax errors have been discovered
                if self.error_detected:
                    continue
                # Collect information from the block node's content
                self.check_block(block_node, param_vec)
                if self.error_detected:
                    continue

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
