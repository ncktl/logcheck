from tree_sitter import Language, Tree, Node


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
    if node.type == "block":
        print("Children:", node.children)
    for child in node.children:
        if child.is_named: print_children(child, level + 1)
        # print_children(child, level + 1)


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
