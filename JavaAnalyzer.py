from tree_sitter import Language, Tree
import logging
from pathlib import Path
from time import perf_counter


class JavaAnalyzer:
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
            encoding="utf-8",
            format="%(levelname)s:%(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def analyze(self):
        """
        Starts the analyses
        """
        pass

    def exception_handling_via_treesitter(self):
        """
        Checks for logging in the children of the exception nodes of the ast
        """
        pass
