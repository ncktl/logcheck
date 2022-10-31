from tree_sitter import Language, Tree, Node, TreeCursor


class Extractor:
    def __init__(self, src: str, lang: Language, tree: Tree, file, args):
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
        self.args = args

    @staticmethod
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

    @staticmethod
    def print_children(node: Node, level=0, max_depth=999):
        if level > max_depth:
            return
        print(f"Line {node.start_point[0] + 1}: " + (level * 2) * "  " + str(node))
        for child in node.children:
            if child.is_named: print_children(child, level + 1)
            # print_children(child, level + 1)
