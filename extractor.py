from tree_sitter import Language, Tree, Node, TreeCursor


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

    def debug_helper(self, node: Node):
        print(self.file)
        print(f"Parent: {node.parent}")
        print(node)
        print(f"Children: {node.children}")
        # print(node.text.decode("UTF-8"))
