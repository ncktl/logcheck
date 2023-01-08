from tree_sitter import Language, Tree, Node
from extractor import Extractor, traverse_sub_tree
from python_config import contains, most_node_types, par_vec_onehot_expanded
from python_config import compound_statements, simple_statements, extra_clauses, statements, keyword, node_dict
import python_config as cfg
import re
from copy import copy
import logging

class JavaExtractor(Extractor):
    def __init__(self, src: str, lang: Language, tree: Tree, file, settings):
        super().__init__(src, lang, tree, file, settings)
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

