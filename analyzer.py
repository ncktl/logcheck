from tree_sitter import Language, Tree, Node
import logging
from pathlib import Path


def print_children(node: Node, indent=0):
    print(indent * 2 * " ", node)
    for child in node.children:
        if child.is_named:
            print_children(child, indent + 1)


class Analyzer:
    def __init__(self, src: str, lang: Language, tree: Tree, file_path: Path):
        """
        :param src: Source code to analyze
        :param lang: Treesitter language object
        :param file_path: Pathlib object of the file to analyze
        """

        self.src = src
        self.lang = lang
        self.tree = tree
        self.file_path = file_path
        logging.basicConfig(
            filename=file_path.with_name("analysis-of-" + file_path.name + ".log"),
            filemode="w",
            level=logging.DEBUG,
            format="%(levelname)s:%(message)s"
        )
        self.logger: Logger = logging.getLogger(__name__)
