import logging
from copy import copy

from tree_sitter import Language, Tree, Node, TreeCursor

# TODO: General config
from config import parameter_vectors, node_dicts, node_names, keywords


def print_children(node: Node, level=0, print_unnamed=False, maxdepth=999):
    if level > maxdepth:
        return
    if node.is_named or print_unnamed:
        print(f"Line {node.start_point[0] + 1}: " + (level * 2) * "  " + str(node))
    for child in node.children:
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
        # A compiled Regex to identify logging statements
        self.keyword = keywords[self.settings.language]
        # A dict for encoding node types to ASCII chars to reduce size
        self.node_dict = node_dicts[self.settings.language]
        # Parameter vector dict for feature extraction
        self.parameter_vector = parameter_vectors[self.settings.language]
        # The parsed source code files can contain syntax errors. If a syntax error is discovered during processing of
        # a block, this flag will be raised resulting in the block being discarded.
        self.error_detected = False
        self.visited_nodes = set()
        self.logger = logging.getLogger(self.settings.language.capitalize() + "Extractor")
        # self.logger.setLevel(logging.DEBUG)
        # Debugging unhandled nodes
        self.unhandled_node_types = set()

    def debug_helper(self, node: Node):
        debug_str = f"{self.file}\nParent: {node.parent}\n{str(node)}\nChildren: {node.children}"
        # self.logger.error(debug_str)
        # self.logger.error(node.text.decode("UTF-8"))
        return debug_str

    def get_node_type(self, node_or_str, encode=False):
        """Returns the node type of the given node or type string.
        If the -c/--encode flag is set, the type is returned ascii encoded."""
        if type(node_or_str) == str:
            key = node_or_str
        elif type(node_or_str) == Node:
            key = node_or_str.type
        else:
            raise RuntimeError("Bad input type given to get_node_type()")
        if self.settings.encode or encode:
            return self.node_dict[key]
        else:
            return key

    def find_containing_block(self, node: Node):
        """Returns the lowest block node containing the node."""
        parent = node.parent
        while parent is not None:
            if parent.type in self.names.containing_block_types:
                return parent
            if parent.type == self.names.error:
                self.error_detected = True
                return parent
            parent = parent.parent
        else:
            debug_str = self.debug_helper(node)
            raise RuntimeError(f"Could not find containing block\n{debug_str}")

    def build_context_of_block_node(self, block_node: Node, param_vec: dict):
        """Build the context of the block and computes depth features"""

        # Find the containing (function) definition
        def_node = None
        depth_from_def = -1
        looking_for_def = True
        climbing_node = block_node.parent
        # Measure the depth of nesting from the node's containing func/class def or module
        # Remains 0 if the given block node is the child of a function definition
        depth_from_root = 0
        while climbing_node.type != self.names.root:
            # Stop when encountering an error
            if climbing_node.type == self.names.error:
                self.error_detected = True
                return
            # Note the height until enclosing function definition
            if looking_for_def and climbing_node.type == self.names.func_def:
                looking_for_def = False
                def_node = climbing_node
                depth_from_def = depth_from_root
            climbing_node = climbing_node.parent
            depth_from_root += 1
        assert def_node is not None
        assert depth_from_def != -1
        param_vec["depth_from_def"] = depth_from_def
        param_vec["depth_from_root"] = depth_from_root

        # Only build the context if argument is given
        if not self.settings.alt:
            return

        def add_relevant_node(node: Node, context: list):
            """Adds the node to the context unless it is a logging statement"""
            if node.is_named:
                if node.type in self.names.most_node_types:
                    if node.type == self.names.func_call:
                        func_call_str = self.get_func_call_str(node)
                        if self.keyword.match(func_call_str):
                            return
                    context.append(self.get_node_type(node, encode=True))
                else:
                    pass
                    # Finds obscure node types
                    # self.unhandled_node_types.add(node.type)

        context = []
        # Add the ast nodes that came before the block in its parent (func|class) def or module
        for node in traverse_sub_tree(def_node, block_node):
            add_relevant_node(node, context)
        # Debug
        if self.settings.debug:
            context.append("%%%%")
        # Add the ast nodes in the block and it's children
        for node in traverse_sub_tree(block_node):
            add_relevant_node(node, context)
        param_vec["context"] = "".join(context)

    def process_block_node(self, block_node: Node, training: bool, param_vectors: list):
        """Gathers information about the block in a parameter vector and enters it into the list of parameter vectors"""

        # Uniqueness check using start and end byte tuple
        check_value = (block_node.start_byte, block_node.end_byte)
        if check_value in self.visited_nodes:
            return
        else:
            self.visited_nodes.add(check_value)
        # Create a parameter vector for the block node and enter some information
        param_vec = copy(self.parameter_vector)
        param_vec["location"] = f"{block_node.start_point[0]};{block_node.start_point[1]}-" \
                                f"{block_node.end_point[0]};{block_node.end_point[1]}"
        # Add +2 instead because the block lacks the parent's line?
        param_vec["length"] = block_node.end_point[0] - block_node.start_point[0] + 1
        param_vec["num_children"] = block_node.named_child_count
        # Collect information from the block node's content
        self.check_block(block_node, param_vec)
        if self.error_detected:
            return
        # Collect information from the block node's ancestors and siblings
        self.check_parent(block_node, param_vec)
        # Discard blocks for which syntax errors have been discovered
        if self.error_detected:
            return


        # Debug grandparent feature
        # if param_vec["contains_logging"] and param_vec["grandparent"] == "rootception":
        #     self.logger.error("Found logging in a block whose containing block is already root:")
        #     self.debug_helper(block_node.parent)

        if training:
            param_vec_list = list(param_vec.values())
            # Check that no parameters have been accidentally added
            if len(param_vec_list) != len(self.parameter_vector):
                self.debug_helper(block_node)
                print(self.parameter_vector.keys())
                print(param_vec.keys())
                raise RuntimeError("Parameter vector length mismatch")
            param_vectors.append(param_vec_list)
        else:
            # For prediction, the extracted parameters will be returned as a list of dicts for subsequent
            # pandas.Dataframe creation
            # Only recommend for a node that doesn't have logging already
            if not param_vec["contains_logging"]:
                param_vectors.append(param_vec)

    def fill_param_vectors(self, training: bool = True) -> list:
        """Extracts features like Zhenhao et al., i.e. looks at all blocks that are inside functions."""
        self.error_detected = False
        param_vectors = []
        # visited_nodes = set()
        func_def_query = self.lang.query(f"({self.names.func_def}) @funcdef")
        func_def_nodes = func_def_query.captures(self.tree.root_node)
        for funcdef_node, func_tag in func_def_nodes:
            funcdef_node: Node
            for block_name in self.names.block_types:
                block_query = self.lang.query(f"({block_name}) @block")
                block_nodes = block_query.captures(funcdef_node)
                for block_node, block_tag in block_nodes:
                    block_node: Node
                    self.process_block_node(block_node, training, param_vectors)
        if self.unhandled_node_types != set():
            self.logger.error(self.unhandled_node_types)
            # self.logger.error(str(self.unhandled_node_types))
        return param_vectors
