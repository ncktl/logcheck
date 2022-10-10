import re
from string import ascii_letters

keyword = re.compile("log(g(ing|er))?(\.|$)")

compound_statements = [
    "class_definition",
    # "decorated_definition", # Not needed: It's just the @decorator_name line
    "function_definition",
    "if_statement",
    "for_statement",
    # "match_statement", # Python 3.10 feature
    "while_statement",
    "try_statement",
    "with_statement"
]

extra_clauses = ["elif_clause", "else_clause", "except_clause", "finally_clause"]
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

interesting_node_types = compound_statements + extra_clauses
# Should module be part of the interesting node types?
#  How to handle a module's parent parameter?
# interesting_node_types = compound_statements + extra_clauses + ["module"]


# contains_features check the node's direct children in its block
contains_types = compound_statements + simple_statements

# A list of all python syntax node types that are visible and non-literals and also not identifiers, plus module
# Excludes e.g. block and expression_statement nodes
most_node_types = ["module"] + compound_statements + extra_clauses + expressions + simple_statements

# ASCII Encoding of visible node types
node_dict = dict()
for i, node_type in enumerate(most_node_types):
    node_dict[node_type] = ascii_letters[i]

# Todo: Test with node count for contains_features -> type(par_vec_extended["contains_features"]) == int
# Todo: contains_open? Redundant with contains_with?

# Todo: Add node length feature


def prefix(string):
    return lambda x: [string + y for y in x]


def vectorize(x):
    return list(zip(x, [0] * len(x)))


interesting_nodes = prefix("")(interesting_node_types)
contains_only_statements = prefix("contains_")(contains_types)
contains = prefix("contains_")(contains_types + expressions + ["logging"])


def make_features(x):
    return [[("line", -1)] + x + vectorize(contains)]


features_onehot = make_features([("type", ""), ("parent", "")])
par_vec_onehot = dict([x for y in features_onehot for x in y])

features_onehot_expanded = make_features([("type", ""), ("parent", ""), ("context", "")])
par_vec_onehot_expanded = dict([x for y in features_onehot_expanded for x in y])

par_vec_zhenhao = {
    "line": -1,
    "type": "",
    "context": "",
    "contains_logging": 0
}

# List of par_vec_onehot keys with onehot values expanded for reindexing the parameter vector during prediction
reindex = ["contains_class_definition", "contains_for_statement",
           "contains_function_definition", "contains_if_statement",
           "contains_try_statement", "contains_while_statement",
           "contains_with_statement", "contains_assert_statement",
           "contains_break_statement", "contains_continue_statement",
           "contains_delete_statement", "contains_exec_statement",
           # "contains_expression_statement",
           "contains_future_import_statement",
           "contains_global_statement", "contains_import_from_statement",
           "contains_import_statement", "contains_nonlocal_statement",
           "contains_pass_statement", "contains_print_statement",
           "contains_raise_statement", "contains_return_statement",
           "contains_assignment",
           "contains_await",
           "contains_call",
           "contains_yield",
           "type_class_definition", "type_elif_clause",
           "type_else_clause", "type_except_clause", "type_finally_clause",
           "type_for_statement", "type_function_definition", "type_if_statement",
           "type_try_statement", "type_while_statement", "type_with_statement",
           "parent_class_definition", "parent_elif_clause", "parent_else_clause",
           "parent_except_clause", "parent_finally_clause", "parent_for_statement",
           "parent_function_definition", "parent_if_statement", "parent_module",
           "parent_try_statement", "parent_while_statement",
           "parent_with_statement"]

if __name__ == "__main__":
    print(par_vec_onehot)
    print(contains_only_statements)
    print(contains)
    print(node_dict)
    print(len(most_node_types))

"""
{'module': 'a',
 'class_definition': 'b',
 'function_definition': 'c',
 'if_statement': 'd',
 'for_statement': 'e',
 'while_statement': 'f',
 'try_statement': 'g',
 'with_statement': 'h',
 'elif_clause': 'i',
 'else_clause': 'j',
 'except_clause': 'k',
 'finally_clause': 'l',
 'assignment': 'm',
 'call': 'n',
 'await': 'o',
 'yield': 'p',
 'return_statement': 'q',
 'assert_statement': 'r',
 'break_statement': 's',
 'continue_statement': 't',
 'raise_statement': 'u',
 'import_statement': 'v',
 'import_from_statement': 'w',
 'pass_statement': 'x',
 'delete_statement': 'y',
 'exec_statement': 'z',
 'future_import_statement': 'A',
 'global_statement': 'B',
 'nonlocal_statement': 'C',
 'print_statement': 'D'}


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
