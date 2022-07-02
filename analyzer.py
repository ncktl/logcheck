from tree_sitter import Language, Tree, Node
import logging
from pathlib import Path


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


class Analyzer:
    def __init__(self, src: str, lang: Language, tree: Tree, file_path: Path):
        """
        :param src: Source code to analyze
        :param lang: Tree-sitter language object
        :param file_path: Pathlib object of the file to analyze
        """

        self.src: str = src
        self.lang: Language = lang
        self.tree: Tree = tree
        self.file_path: Path = file_path
        '''
        logging.basicConfig(
            filename=file_path.with_name("analysis-of-" + file_path.name + ".log"),
            filemode="w",
            level=logging.DEBUG,
            # format="%(levelname)s:%(message)s"
            format="%(message)s"
        )
        self.logger: Logger = logging.getLogger(__name__)
        '''
        self.lines: list = src.splitlines()
