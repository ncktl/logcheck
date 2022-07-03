from tree_sitter import Language, Tree, Node
from pathlib import Path

par_vec = {
    # "line": -1,
    "if_": False,
    "try_": False,
    "logging_": False
}


def print_children(node: Node, level=0, maxdepth=999):
    if level > maxdepth:
        return
    if level == 0:
        print(node)
    else:
        print(((level * 2) - 1) * " ", node)
    for child in node.children:
        if child.is_named:
            print_children(child, level + 1)


class Extractor:
    def __init__(self, src: str, lang: Language, tree: Tree, file_path: Path):
        """
        :param src: Source code to extract paramaeter vectors from
        :param lang: Tree-sitter language object
        :param tree: Treesitter tree object
        :param file_path: Pathlib object of the file to analyze
        """

        self.src: str = src
        self.lang: Language = lang
        self.tree: Tree = tree
        self.file_path: Path = file_path
        self.lines: list = src.splitlines()
