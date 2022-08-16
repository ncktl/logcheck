from tree_sitter import Language, Tree
import logging
from pathlib import Path
from time import perf_counter
from extractor import Extractor, print_children


class JavaAnalyzer(Extractor):
    def __init__(self, src: str, lang: Language, tree: Tree, file, args):
        """
        :param src: Source code to extract paramaeter vectors from
        :param lang: Treesitter language object
        :param tree: Treesitter tree object
        :param file: current file
        """

        super().__init__(src, lang, tree, file, args)
        # Name of the log4j object in the example, hardcoded for now
        self.keyword = "logger"

    def analyze(self):
        """
        Starts the analyses
        """

        self.exception_handling_via_treesitter()

    def exception_handling_via_treesitter(self):
        """
        Checks for logging in the children of the catch nodes of the ast
        """

        self.logger.info("Treesitter analysis of logging in exception handling:")
        # Query to find logging invocations inside catch clauses of the form "logger.method()"
        invoc_in_catch_query = self.lang.query("(catch_clause"
                                               "(block"
                                               "(expression_statement"
                                               "(method_invocation ."
                                               "(identifier) @identifier))))")
        # Execute query
        invoc_identifiers = invoc_in_catch_query.captures(self.tree.root_node)
        catches_with_direct_logging = set()
        for node, tag in invoc_identifiers:
            if node.text.decode("UTF-8") == self.keyword:
                # The catch clause is the identifier's fourth-level ancestor (see query above)
                # Add these catches to a set because multiple logging invocations can have the same catch ancestor
                # Identified by their start_byte
                catches_with_direct_logging.add(node.parent.parent.parent.parent.start_byte)
        # Query to find all catch nodes in the ast
        catch_query = self.lang.query("(catch_clause) @b")
        all_catches = catch_query.captures(self.tree.root_node)
        for node, tag in all_catches:
            if node.start_byte not in catches_with_direct_logging:
                # Find the catches not in the set of exceptions with direct logging
                self.logger.warning(f"No direct logging in the exception handling "
                                    f"starting in line {node.start_point[0] + 1}:")
                self.logger.debug(node.text.decode("UTF-8"))
        self.logger.info(f"Logging used in {len(catches_with_direct_logging)} "
                         f"out of {len(all_catches)} exception handling blocks.")