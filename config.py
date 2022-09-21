import re

keyword = re.compile("log(g(ing|er))?(\.|$)")

compound_statements = [
    "class_definition",
    # "decorated_definition", # Not needed: It's just the @decorator_name line
    "for_statement",
    "function_definition",
    "if_statement",
    # "match_statement", # Python 3.10 feature
    "try_statement",
    "while_statement",
    "with_statement"
]

extra_clauses = ["elif_clause", "else_clause", "except_clause", "finally_clause"]
# Todo: Test with if_else, try_else,... instead of else_clause and so on
# Todo: Consider the implication of except_clause=True (unambigous so try_except not needed) for parent_try_statement

# Too much?
simple_statements = [
    "assert_statement",
    "break_statement",
    "continue_statement",
    "delete_statement",
    "exec_statement",  # Not in Viewfinder
    # "expression_statement", # TODO Highest importance, disabled for testing, split up into finer
    "future_import_statement",  # Not in Viewfinder
    "global_statement",
    "import_from_statement",
    "import_statement",
    "nonlocal_statement",  # Not in Viewfinder
    "pass_statement",
    "print_statement",  # Python 2 feature?
    "raise_statement",
    "return_statement"
]

expressions = [
    "assignment",
    "await",
    "call",
    "yield"
]

interesting_node_types = compound_statements + extra_clauses
# Should module be part of the interesting node types?
#  How to handle a module's parent parameter?
# interesting_node_types = compound_statements + extra_clauses + ["module"]


# contains_features check the node's direct children in its block
contains_types = compound_statements + simple_statements

# A list of all python syntax node types that are visible and non-literals and also not identifiers
# Excludes e.g. block and expression_statement nodes
visible_node_types = compound_statements + extra_clauses + simple_statements + expressions

# Todo: Test with node count for contains_features -> type(par_vec_extended["contains_features"]) == int
# Todo: contains_open? Redundant with contains_with?

# Todo: Add node length feature


def prefix(string):
    return lambda x: [string + y for y in x]


def vectorize(x):
    return list(zip(x, [False] * len(x)))


interesting_nodes = prefix("")(interesting_node_types)
contains_only_statements = prefix("contains_")(contains_types)
contains = prefix("contains_")(contains_types + expressions + ["logging"])


def make_features(x):
    return [[("line", -1)] + x + vectorize(contains)]


features_onehot = make_features([("type", ""), ("parent", "")])
par_vec_onehot = dict([x for y in features_onehot for x in y])

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
