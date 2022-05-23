from tree_sitter import Language, Parser, Tree
import logging
from pathlib import Path


class PythonAnalyzer:
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

        exception_count = len(exception_occurrences)
        exceptions_logged = 0

        for i in exception_occurrences:
            #print(i)
            #print(i[0].text.decode("UTF-8"))
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
                #print("Logging used in exception handling. Well done!")
                #self.logger.info("Logging used in exception handling. Well done!")
                exceptions_logged += 1
            else:
                #print("Log your exceptions!")
                self.logger.warning(f"No logging in the exception handling starting in line {i[0].start_point[0]+1}:")
                # Multi-line debug message is not indented correctly
                self.logger.debug(i[0].text.decode("UTF-8"))
        self.logger.info(f"Logging used in {exceptions_logged} out of {exception_count} exception handling blocks.")

    def simple_text_analysis(self):
        """
        Searches the source code for indications of logging
        """
        if "import logging" in self.src:
            keyword = "logging"
            logging_count = 0
            past_import = False
            lines = self.src.splitlines()
            for i, line in enumerate(lines):
                if not past_import and "import logging" in line:
                    if "import logging as" in line:
                        keyword = line.split(" ")[-1]
                    past_import = True
                if past_import:
                    if keyword in line:
                        logging_count += 1
                    if "except" in line:
                        except_index = line.find("except")
                        before = line[0:except_index]
                        if "#" not in before and not before.endswith("."):
                            indentation = len(before)
                            print(f"line {i+1}:")
                            print(line)
                            print(f"before: {indentation} tabs")
                            print("a" + before + "b")
                            #print(before == "\t")
                            print("except_index: " + str(except_index))
                            for j, nested_line in enumerate(lines[i+1:]):
                                print(f"nested_line {i + j + 2}:")
                                print(nested_line)
                                nested_before = nested_line[0:except_index + 1]
                                print("nested_before: a" + nested_before + "b")
                                if nested_before == before + "\t":
                                    if keyword in nested_line:
                                        break
                                else:
                                    self.logger.warning(
                                        f"No logging in the exception handling starting in line {i+1}:"
                                    )
                                    break


            self.logger.info(f"The logging module has been used {logging_count} time[s].")
        else:
            self.logger.info("The logging module is not used in this file.")

