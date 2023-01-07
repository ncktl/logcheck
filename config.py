import re
from string import ascii_letters

# keyword = re.compile("log(g(ing|er))?(\.|$)")
keyword = re.compile("(\w|\.)+\.(debug|info|warning|error|critical|log|exception)$")

compound_statements_part_one = [
    "class_definition",
    # "decorated_definition", # Not needed: It's just the @decorator_name line
    "function_definition",
    "if_statement",
    "for_statement",
]
compound_statements_part_two = [
    "while_statement",
    "try_statement",
    "with_statement",
]
# Match doesn't have a block
# Awkward because need to preserve order for now
compound_statements = compound_statements_part_one +\
                        ["match_statement"] +\
                        compound_statements_part_two

extra_clauses = ["elif_clause", "else_clause", "except_clause", "except_group_clause", "finally_clause", "case_clause"]
# Todo: Test with if_else, try_else,... instead of else_clause and so on
# Todo: Consider the implication of except_clause=True (unambigous so try_except not needed) for parent_try_statement

# Too much?
simple_statements = [
    "return_statement",
    "assert_statement",
    "break_statement",
    "continue_statement",
    "raise_statement",
    "import_statement",
    "import_from_statement",
    "pass_statement",
    "delete_statement",
    "exec_statement",  # Not in Viewfinder
    # "expression_statement", #  Highest importance, disabled for testing, split up into finer
    "future_import_statement",  # Not in Viewfinder
    "global_statement",
    "nonlocal_statement",  # Not in Viewfinder
    "print_statement",  # Python 2 feature?
]

expressions = [
    "assignment",
    "call",
    "await",
    "yield"
]

interesting_node_types = compound_statements_part_one + compound_statements_part_two + extra_clauses
# Should module be part of the interesting node types?
#  How to handle a module's parent parameter?
# interesting_node_types = compound_statements + extra_clauses + ["module"]


# contains_features check the node's direct children in its block
contains_types = compound_statements + simple_statements

# A list of most python syntax node types that are visible and non-literals and also not identifiers,
# plus module and error
# Excludes e.g. block and expression_statement nodes
most_node_types = ["module", "ERROR"] + compound_statements + extra_clauses + expressions + simple_statements

# ASCII Encoding of visible node types
node_dict = dict()
for i, node_type in enumerate(most_node_types):
    node_dict[node_type] = ascii_letters[i]
rev_node_dict = dict(zip(node_dict.values(), node_dict.keys()))

# Todo: Test with node count for contains_features -> type(par_vec_extended["contains_features"]) == int
# Todo: contains_open? Redundant with contains_with?

# Todo: Add node length feature


def prefix(string):
    return lambda x: [string + y for y in x]


def vectorize(x):
    return list(zip(x, [0] * len(x)))


# interesting_nodes = prefix("")(interesting_node_types)
contains_only_statements = prefix("contains_")(contains_types)
contains = prefix("contains_")(contains_types + expressions + ["logging"])


def make_features(x):
    # return [[("line", -1)] + x + vectorize(contains)]
    return [x + vectorize(contains)]


features_onehot_expanded = make_features([
    ("type", ""),
    ("location", ""),
    ("length", 0),
    ("num_siblings", 0),
    ("sibling_index", 0),
    ("num_children", 0),
    ("depth_from_def", 0),
    ("parent", ""),
    ("context", "")
])
par_vec_onehot_expanded = dict([x for y in features_onehot_expanded for x in y])

# List of par_vec_onehot keys with onehot values expanded for reindexing the parameter vector during prediction
reindex = ['contains_class_definition',
       'contains_function_definition', 'contains_if_statement',
       'contains_for_statement', 'contains_match_statement',
       'contains_while_statement', 'contains_try_statement',
       'contains_with_statement', 'contains_return_statement',
       'contains_assert_statement', 'contains_break_statement',
       'contains_continue_statement', 'contains_raise_statement',
       'contains_import_statement', 'contains_import_from_statement',
       'contains_pass_statement', 'contains_delete_statement',
       'contains_exec_statement', 'contains_future_import_statement',
       'contains_global_statement', 'contains_nonlocal_statement',
       'contains_print_statement', 'contains_assignment', 'contains_call',
       'contains_await', 'contains_yield', 'type_c',
       'type_d', 'type_e', 'type_f', 'type_g', 'type_h', 'type_i', 'type_j',
       'type_k', 'type_l', 'type_m', 'type_n', 'type_o', 'type_p', 'parent_a',
       'parent_b', 'parent_c', 'parent_d', 'parent_e', 'parent_f', 'parent_g',
       'parent_h', 'parent_i', 'parent_j', 'parent_k', 'parent_l', 'parent_m',
       'parent_n', 'parent_o', 'parent_p']

if __name__ == "__main__":
    print(contains_only_statements)
    print(contains)
    print(node_dict)
    print(len(most_node_types))
    print(compound_statements)

"""
{'module': 'a',
 'ERROR': 'b',
 'class_definition': 'c',
 'function_definition': 'd',
 'if_statement': 'e',
 'for_statement': 'f',
 'match_statement': 'g',
 'while_statement': 'h',
 'try_statement': 'i',
 'with_statement': 'j',
 'elif_clause': 'k',
 'else_clause': 'l',
 'except_clause': 'm',
 'except_group_clause': 'n',
 'finally_clause': 'o',
 'case_clause': 'p',
 'assignment': 'q',
 'call': 'r',
 'await': 's',
 'yield': 't',
 'return_statement': 'u',
 'assert_statement': 'v',
 'break_statement': 'w',
 'continue_statement': 'x',
 'raise_statement': 'y',
 'import_statement': 'z',
 'import_from_statement': 'A',
 'pass_statement': 'B',
 'delete_statement': 'C',
 'exec_statement': 'D',
 'future_import_statement': 'E',
 'global_statement': 'F',
 'nonlocal_statement': 'G',
 'print_statement': 'H'}




## Old:
{'class_definition': '0',
 'for_statement': '1',
 'function_definition': '2',
 'if_statement': '3',
 'try_statement': '4',
 'while_statement': '5',
 'with_statement': '6',
 'elif_clause': '7',
 'else_clause': '8',
 'except_clause': '9',
 'finally_clause': '10',
 'assert_statement': '11',
 'break_statement': '12',
 'continue_statement': '13',
 'delete_statement': '14',
 'exec_statement': '15',
 'future_import_statement': '16',
 'global_statement': '17',
 'import_from_statement': '18',
 'import_statement': '19',
 'nonlocal_statement': '20',
 'pass_statement': '21',
 'print_statement': '22',
 'raise_statement': '23',
 'return_statement': '24',
 'assignment': '25',
 'await': '26',
 'call': '27',
 'yield': '28'}
"""
