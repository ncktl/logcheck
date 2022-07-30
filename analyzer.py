from tree_sitter import Language, Tree, Node
import logging
from pathlib import Path


def print_children(node: Node, level=0, maxdepth=999):
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
    ###
    if level > maxdepth:
        return
    if level == 0:
        print(node, node.start_byte)
    else:
        print(((level * 2) - 1) * " ", node, hash)
    for child in node.children:
        if child.is_named:
            print_children(child, level + 1)


class Analyzer:
    def __init__(self, src: str, lang: Language, tree: Tree, file_path: Path, args):
        """
        :param src: Source code to analyze
        :param lang: Tree-sitter language object
        :param tree: Treesitter tree object
        :param file_path: Pathlib object of the file to analyze
        """

        self.src: str = src
        self.lang: Language = lang
        self.tree: Tree = tree
        self.file_path: Path = file_path
        # logging.basicConfig(
        #     filename=file_path.with_name("analysis-of-" + file_path.name + ".log"),
        #     filemode="w",
        #     level=logging.DEBUG,
        #     format="%(message)s"
        # )
        # self.logger: None
        self.lines: list = src.splitlines()
        self.args = args
