from tree_sitter import Language, Tree

from extractor import Extractor, print_children


class JavaAnalyzer(Extractor):
    def __init__(self, src: str, lang: Language, tree: Tree, file, settings):
        """
        :param src: Source code to extract paramaeter vectors from
        :param lang: Treesitter language object
        :param tree: Treesitter tree object
        :param file: current file
        """

        super().__init__(src, lang, tree, file, settings)
        # Name of the log4j object in the example, hardcoded for now
        self.keyword = "logger"

    def analyze(self):
        """
        Starts the analyses
        """

        print_children(self.tree.root_node, print_unnamed=self.settings.debug); exit()
