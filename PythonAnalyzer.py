from tree_sitter import Language, Tree
import logging
from pathlib import Path
from time import perf_counter


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
        # Name of the Python logging module, can be aliased, which is checked in the manual analysis
        self.keyword = "logging"

    def analyze(self):
        """
        Starts the analyses
        """
        a = perf_counter()
        self.exception_handling_manually()
        b = perf_counter()
        self.exception_handling_via_treesitter()
        c = perf_counter()
        print(f"Manual: {b - a}, Treesitter: {c - b}")

    def exception_handling_via_treesitter(self):
        """
        Checks for logging in the children of the exception nodes of the ast
        """
        self.logger.info("Treesitter analysis of logging in exception handling:")
        # Query to find exception handling nodes in the ast
        exception_query = self.lang.query("(except_clause) @b")
        # Query to find function call nodes in the ast
        call_query = self.lang.query("(call (attribute . (identifier) @c))")
        # Find the exception handling nodes
        exception_occurrences = exception_query.captures(self.tree.root_node)

        exception_count = len(exception_occurrences)
        exceptions_logged = 0

        for i in exception_occurrences:
            # Find function call nodes among the children of the current exception node
            possible_log_occurrences = call_query.captures(i[0])
            used_logging = False
            for j in possible_log_occurrences:
                # Check if the identifier on which a function is called matches the logging module name
                if j[0].text.decode("UTF-8") == self.keyword:
                    used_logging = True
                    break
            if used_logging:
                exceptions_logged += 1
            else:
                self.logger.warning(f"No logging in the exception handling starting in line {i[0].start_point[0]+1}:")
                # Multi-line debug message is not indented correctly
                self.logger.debug(i[0].text.decode("UTF-8"))
        self.logger.info(f"Logging used in {exceptions_logged} out of {exception_count} exception handling blocks.")

    def exception_handling_manually(self):
        """
        Searches the source code for indications of logging and checks the exception handling for logging
        """
        self.logger.info("Manual analysis of logging in exception handling:")
        if "import logging" in self.src:
            logging_count = 0
            exception_count = 0
            exceptions_logged = 0
            past_import = False
            lines = self.src.splitlines()
            # Go through the sourcecode
            for i, line in enumerate(lines):
                # Look for the logging module
                if not past_import and "import logging" in line:
                    if "import logging as" in line:
                        # Possibly find the alias
                        self.keyword = line.split(" ")[-1]
                    past_import = True
                # After the logging module import:
                if past_import:
                    if self.keyword in line:
                        logging_count += 1
                    if "except" in line:
                        except_index = line.find("except")
                        before = line[0:except_index]
                        if "#" not in before and not before.endswith("."):
                            exception_count += 1
                            # Go through the lines after the except statement in an inner loop:
                            for j, nested_line in enumerate(lines[i+1:]):
                                nested_before = nested_line[0:except_index + 1]
                                # If we find a line with one more level of indentation
                                # Assumption: Tabs used
                                if nested_before == before + "\t":
                                    # and the keyword, logging was used in this exception handling
                                    if self.keyword in nested_line:
                                        exceptions_logged += 1
                                        break
                                # If instead a line with the same indentation is found, no logging was used
                                else:
                                    self.logger.warning(
                                        f"No logging in the exception handling starting in line {i+1}:"
                                    )
                                    # Multi-line debug message is not indented correctly
                                    self.logger.debug("\n".join(lines[i:i+j+1]))
                                    break
            self.logger.info(f"The logging module has been used {logging_count} time[s].")
            self.logger.info(f"Logging used in {exceptions_logged} out of {exception_count} exception handling blocks.")
        else:
            self.logger.info("The logging module is not used in this file.")
