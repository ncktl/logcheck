from tree_sitter import Language, Tree
import logging
from pathlib import Path
from time import perf_counter
from analyzer import Analyzer, print_children


class JavaAnalyzer:
    def __init__(self, src: str, lang: Language, tree: Tree, file_path: Path):
        """
        :param src: Source code to analyze
        :param lang: Treesitter language object
        :param file_path: Pathlib object of the file to analyze
        """
        super().__init__(src, lang, tree, file_path)
        # Name of the log4j object in the example, hardcoded for now
        self.keyword = "logger"

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
