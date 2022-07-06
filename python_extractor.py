from tree_sitter import Language, Tree, Node
from pathlib import Path
from extractor import Extractor, par_vec, par_vec_debug
import re
from copy import copy


class PythonExtractor(Extractor):
    def __init__(self, src: str, lang: Language, tree: Tree, file_path: Path, args):
        """
        :param src: Source code to extract paramaeter vectors from
        :param lang: Treesitter language object
        :param tree: Treesitter tree object
        :param file_path: Pathlib object of the file to analyze
        """

        super().__init__(src, lang, tree, file_path, args)
        # Name of the Python logging module
        self.keyword = "logg(ing|er)"

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
        visited_nodes = set()
        # Changed from except_clause to try_statement
        interesting_node_types = ["if_statement", "try_statement", "function_definition"]
        # interesting_node_types = ["function_definition"]
        for node_type in interesting_node_types:
            # Query to find the node type OLD
            if self.args.alt:
                node_query = self.lang.query("(" + node_type + ") @" + node_type)
            else:
                # Query to find all nodes inside NEW
                if node_type == "if_statement":
                    node_query = self.lang.query("(if_statement " # Capture if itself as well?
                                                 "["
                                                 "(block (_) @block)"
                                                 "(elif_clause"
                                                 "(block (_) @elif) )"
                                                 "(else_clause"
                                                 "(block (_) @else) )"
                                                 "] )")
                elif node_type == "try_statement":
                    node_query = self.lang.query("(try_statement" # Capture try itself?
                                                 "["
                                                 "(block (_) @block)"
                                                 "(else_clause"
                                                 "(block (_) @else) )"
                                                 "(except_clause"
                                                 "(block (_) @except) )"
                                                 "(finally_clause"
                                                 "(block (_) @finally) )"
                                                 "] )")
                elif node_type == "function_definition":
                    node_query = self.lang.query("(function_definition" # and def?
                                                 "(block (_) @block)"
                                                 ")")
            nodes = node_query.captures(self.tree.root_node)
            for node, tag in nodes:
                # Uniqueness check is unnecessary?
                if (node.start_byte, node.end_byte) in visited_nodes:
                    continue
                else:
                    visited_nodes.add((node.start_byte, node.end_byte))
                if not node.is_named:
                    continue
                # print(node, tag)
                # Parameter vector
                if self.args.debug:
                    param_vec = copy(par_vec_debug)
                    param_vec["line"] = node.start_point[0] + 1
                else:
                    param_vec = copy(par_vec)

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
                if re.search(self.keyword, context):
                    ############################
                    param_vec["logging_"] = True

                # print(list(param_vec.values()))
                param_vectors.append(list(param_vec.values()))
                # print("#" * 50)
        # for vec in param_vectors:
        # print(vec)
        return param_vectors

######## New ast Approach: Children of nodes, only depth of "one" level

    def check_if_node(self, node: Node, param_vec: dict):
        for child in node.children:
            if not self.args.debug and False not in param_vec.values():
                return
            if child.type == "block":
                self.check_block(child, param_vec)
            elif child.type == "elif_clause":
                self.check_block(child.child_by_field_name("consequence"), param_vec)
            elif child.type == "else_clause":
                self.check_block(child.child_by_field_name("body"), param_vec)

    def check_block(self, node: Node, param_vec: dict):
        for child in node.children:
            if not self.args.debug and False not in param_vec.values():
                return
            if not param_vec["logging_"] and child.type == "expression_statement":
                assert len(child.children) == 1
                if child.children[0].type == "call":
                    if re.search(self.keyword, child.children[0].text.decode("UTF-8")):
                        param_vec["logging_"] = True
            elif not param_vec["try_"] and child.type == "try_statement":
                param_vec["try_"] = True
            elif not param_vec["if_"] and child.type == "if_statement":
                param_vec["if_"] = True
            # More checks for expanded dict

    def check_try(self, node: Node, param_vec: dict):
        for child in node.children:
            if not self.args.debug and False not in param_vec.values():
                return
            if child.type == "block":
                self.check_block(child, param_vec)
            elif child.type == "else_clause":
                self.check_block(child.child_by_field_name("body"), param_vec)
            elif child.type == "except_clause":
                # Can also have some kind of expression child?
                for grandchild in child.children:
                    if grandchild.type == "block":
                        self.check_block(grandchild.child_by_field_name("body"), param_vec)
            elif child.type == "finally_clause":
                assert len(child.children) == 1
                assert child.children[0].type == "block"
                self.check_block(child.children[0], param_vec)

    def check_def(self, node: Node, param_vec: dict):
        self.check_block(node.child_by_field_name("body"), param_vec)

    def fill_param_vecs_ast_new(self) -> list:
        param_vectors = []

        if_query = self.lang.query("(if_statement) @a")
        if_nodes = if_query.captures(self.tree.root_node)
        for node, tag in if_nodes:
            if self.args.debug:
                param_vec = copy(par_vec_debug)
                param_vec["line"] = node.start_point[0] + 1
            else:
                param_vec = copy(par_vec)
            param_vec["if_"] = True
            self.check_if_node(node, param_vec)
            param_vectors.append(list(param_vec.values()))

        try_query = self.lang.query("(try_statement) @a")
        try_nodes = try_query.captures(self.tree.root_node)
        for node, tag in if_nodes:
            if self.args.debug:
                param_vec = copy(par_vec_debug)
                param_vec["line"] = node.start_point[0] + 1
            else:
                param_vec = copy(par_vec)
            param_vec["try_"] = True
            self.check_try(node, param_vec)
            param_vectors.append(list(param_vec.values()))

        def_query = self.lang.query("(function_definition) @a")
        def_nodes = def_query.captures(self.tree.root_node)
        for node, tag in def_nodes:
            if self.args.debug:
                param_vec = copy(par_vec_debug)
                param_vec["line"] = node.start_point[0] + 1
            else:
                param_vec = copy(par_vec)
            self.check_def(node, param_vec)
            param_vectors.append(list(param_vec.values()))

        return param_vectors


######## Old ast approach: siblings


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
                if self.args.debug:
                    param_vec = copy(par_vec_debug)
                    param_vec["line"] = node.start_point[0] + 1
                else:
                    param_vec = copy(par_vec)
                # print(node)
                # Find the parent node we care about, using the given seniority
                parent = node
                # parent_list = [parent]
                for _ in range(seniority):
                    parent = parent.parent
                    # parent_list.append(parent)
                # Parent might be module, i.e. all top level statements are the context.
                # Is this a problem?
                # How would ignoring these nodes affect our results?
                # print(parent.children)
                # try:
                #     for parent in parent_list:
                for sibling in parent.children:
                    # If all param vector entries are True, we are done with the node
                    # Doesn't work with debug param vec
                    if not self.args.debug and False not in param_vec.values():
                        # raise StopIteration
                        continue
                    # Unlike the code window approach, we can easily filter out comments
                    if sibling.type == "comment":
                        continue
                    # internally use something like a code window approach, however
                    code_line = self.lines[sibling.start_point[0]]
                    '''
                    if "if " in code_line:
                        param_vec["if_"] = True
                        # continue
                    if "try:" in code_line:
                        param_vec["try_"] = True
                        # continue
                    '''
                    # Assumption: logging statement not in condition of if-statement
                    # Bad example: 	/Users/nickkeutel/code/python/marepos/web2py/gluon/widget.py line 714
                    # -> No continue
                    if re.search(self.keyword, code_line):
                        param_vec["logging_"] = True
                        # continue

                    # Alternative: internal ast approach.
                    # '''
                    if sibling.type == "if_statement":
                        param_vec["if_"] = True
                        continue
                    if sibling.type == "try_statement":
                        param_vec["try_"] = True
                        continue
                    # '''
                # except StopIteration:
                #     pass
                param_vectors.append(list(param_vec.values()))
                # print("#" * 50)
        # for vec in param_vectors:
        #     print(vec)
        return param_vectors
