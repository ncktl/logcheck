from tree_sitter import Language, Tree, Node
from pathlib import Path
from extractor import Extractor, par_vec
import re
from copy import copy


class PythonExtractor(Extractor):
    def __init__(self, src: str, lang: Language, tree: Tree, file_path: Path):
        """
        :param src: Source code to extract paramaeter vectors from
        :param lang: Treesitter language object
        :param tree: Treesitter tree object
        :param file_path: Pathlib object of the file to analyze
        """

        super().__init__(src, lang, tree, file_path)
        # Name of the Python logging module
        self.keyword = "logging"

    # Sliding code window approach
    def fill_param_vecs_sliding(self, vert_range: int = 3) -> list:
        """
        Fill parameter vectors using a sliding code window.
        Interesting nodes are found. Their context is the lines above and below, specified by the range
        Function definitions are treated as an additional boundary of the context
        Problem: Comments in the code
        :param vert_range: Determines the size of the sliding code window in up and down directions
        :return: parameter vectors
        """
        param_vectors = []
        interesting_node_types = ["if_statement", "except_clause", "function_definition"]
        for node_type in interesting_node_types:
            # Query to find the node type
            node_query = self.lang.query("(" + node_type + ") @" + node_type)
            nodes = node_query.captures(self.tree.root_node)
            for node, tag in nodes:
                # print(node)
                # Parameter vector
                param_vec = copy(par_vec)
                # param_vec["line"] = node.start_point[0]

                # Check the context range and check for function definitions therein
                # Context start and end are inclusive
                # First make sure context is within the file
                context_start = max(node.start_point[0] - vert_range, 0)
                context_end = min(node.start_point[0] + vert_range, len(self.lines) - 1)
                # print(context_start, context_end)

                # Check upwards for function defs
                # unless node is a function def itself
                if node_type == "function_definition":
                    context_start = node.start_point[0]
                else:
                    for i in range(node.start_point[0] - 1, context_start - 1, -1):
                        # print(i)
                        # Assumption: def not in comment at end of line
                        if "def " in self.lines[i]:
                            context_start = i + 1
                            break
                # Check downwards for function defs:
                for i in range(node.start_point[0] + 1, context_end + 1):
                    # print(i)
                    # Assumption: def not in comment at end of line
                    if "def " in self.lines[i]:
                        context_end = i - 1
                        break

                context = "\n".join(self.lines[context_start:context_end + 1])
                # print(context)

                if "if " in context:
                    param_vec["if_"] = True
                if "try:" in context:
                    param_vec["try_"] = True
                # Just checking for "logging" is esp. susceptible to comments
                ############################
                # CHANGED ##################
                # if "logger" in context:
                if re.search("logg(ing|er)", context):
                    ############################
                    param_vec["logging_"] = True

                # print(list(param_vec.values()))
                param_vectors.append(list(param_vec.values()))
                # print("#" * 50)
        # for vec in param_vectors:
        # print(vec)
        return param_vectors

    def fill_param_vecs_ast(self) -> list:
        """
        Fill parameter vectors using the ast but not sliding code window
        For the interesting nodes, their context is considered,
        which for now is their siblings (i.e. the parent's children)

        Should we consider the node's children as well?
        Due to different grammatical structures of the nodes,
        special handling of the different node types will be required
        Are function def nodes suited for this approach? Can only work with children
        :return: parameter vectors
        """
        param_vectors = []
        # The seniority in the tuple indicates which level parent is the parent
        # of similarly nested siblings (motivation: parent of except is try)
        interesting_node_types = [("if_statement", 1), ("except_clause", 2)]
        for node_type, seniority in interesting_node_types:
            # Query to find the node type
            node_query = self.lang.query("(" + node_type + ") @a")
            nodes = node_query.captures(self.tree.root_node)
            for node, tag in nodes:
                # Parameter vector
                param_vec = copy(par_vec)
                # param_vec["line"] = node.start_point[0]

                # print(node)
                # Find the parent node we care about, using the given seniority
                parent = node
                for _ in range(seniority):
                    parent = parent.parent
                # Parent might be module, i.e. all top level statements are the context.
                # Is this a problem?
                # How would ignoring these nodes affect our results?
                # print(parent.children)
                for sibling in parent.children:
                    # If all param vector entries are True, we are done with the node
                    if param_vec["if_"] and param_vec["try_"] and param_vec["logging_"]:
                        break
                    # Unlike the code window approach, we can easily filter out comments
                    if sibling.type == "comment":
                        continue
                    # internally use something like a code window approach, however
                    code_line = self.lines[sibling.start_point[0]]

                    if "if " in code_line:
                        param_vec["if_"] = True
                        continue
                    if "try:" in code_line:
                        param_vec["try_"] = True
                        continue
                    # Assumption: logging statement not in condition of if-statement
                    if re.search("logg(ing|er)", code_line):
                        param_vec["logging_"] = True
                        continue

                    # Alternative: internal ast approach. TODO: Test which is faster
                    '''
                    if sibling.type == "if_statement":
                        param_vec["if_"] = True
                        continue
                    if sibling.type == "try_statement":
                        param_vec["try_"] = True
                        continue
                    '''
                param_vectors.append(list(param_vec.values()))
                # print("#" * 50)
        # for vec in param_vectors:
        #     print(vec)
        return param_vectors
