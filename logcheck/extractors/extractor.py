from tree_sitter import Language, Tree, Node, TreeCursor

from ..dtos import Settings


class Extractor:
    def __init__(self, src: str, lang: Language, tree: Tree, settings: Settings):
        self.src: str = src
        self.lang: Language = lang
        self.tree: Tree = tree
        self.lines: list = src.splitlines()
        self.settings = settings

    def debug_helper(self, node: Node):
        pass

    @staticmethod
    def traverse_sub_tree(root_node: Node, stop_node: Node = None):
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
            if child.is_named:
                Extractor.print_children(child, level + 1)
