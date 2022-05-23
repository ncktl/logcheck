from tree_sitter import Language, Parser, Tree
import logging
from pathlib import Path


class PythonAnalyzer:
    def __init__(self, src, lang: Language, tree: Tree, file_path: Path):
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
        self.logger
        self.analyze_exception_handling()
        self.simple_text_analysis()

    def analyze_exception_handling(self):
        """
        Checks for logging in the children of the exception nodes of the ast
        """

        # Query to find exception handling nodes in the ast
        exception_query = self.lang.query("(except_clause) @b")
        # Query to find function call nodes in the ast
        call_query = self.lang.query("(call (attribute . (identifier) @c))")
        # Find the exception handling nodes
        exception_occurrences = exception_query.captures(self.tree.root_node)

        for i in exception_occurrences:
            # print(i)
            print(i[0].text.decode("UTF-8"))
            # Find function call nodes among the children of the current exception node
            possible_log_occurrences = call_query.captures(i[0])
            used_logging = False
            for j in possible_log_occurrences:
                # print(j)
                # print(j[0].text.decode("UTF-8"))
                # print(j[0].children)
                if j[0].text.decode("UTF-8") == "logging":
                    used_logging = True
                    break
            if used_logging:
                print("Logging used in exception handling. Well done!")
                self.logger.info("Logging used in exception handling. Well done!")
            else:
                print("Log your exceptions!")
                self.logger.warning("Log your exceptions!")

    def simple_text_analysis(self):
        """

        :return:
        """
        pass
