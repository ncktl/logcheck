keyword = "log(g(ing|er)?)?"

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

# Too much?
simple_statements = [
    "assert_statement",
    "break_statement",
    "continue_statement",
    "delete_statement",
    "exec_statement", # Not in Viewfinder
    "expression_statement",
    "future_import_statement", # Not in Viewfinder
    "global_statement",
    "import_from_statement",
    "import_statement",
    "nonlocal_statement", # Not in Viewfinder
    "pass_statement",
    "print_statement", # Python 2 feature?
    "raise_statement",
    "return_statement"
]


extra_clauses = ["elif_clause", "else_clause", "except_clause", "finally_clause"]
# Todo: Test with if_else, try_else,... instead of else_clause and so on
# Todo: Consider the implication of except_clause=True (unambigous so try_except not needed) for child_of_try_statement

interesting_node_types = compound_statements + extra_clauses
# Should module be part of the interesting node types?
#  How to handle a module's parent parameter?
# interesting_node_types = compound_statements + extra_clauses + ["module"]


# contains_features check the node's direct children in its block
contains_types = compound_statements + simple_statements
# Todo: Test with node count for contains_features -> type(par_vec_extended["contains_features"]) == int
# Todo: contains_open? Redundant with contains_with?

# Todo: Add node length feature


def prefix(string):
    return lambda x: [string + y for y in x]


def vectorize(x):
    return list(zip(x, [False] * len(x)))


interesting_nodes = prefix("")(interesting_node_types)
children_of = prefix("child_of_")(interesting_node_types + ["module"])
contains = prefix("contains_")(contains_types + ["logging"])


def make_features(x):
    return [[("line", -1)] + x + vectorize(contains)]


features_bool = make_features(vectorize(interesting_nodes) + vectorize(children_of))
par_vec_bool = dict([x for y in features_bool for x in y])

# DEPRECATED
par_vec_extended = {
    "line": -1,

    # Type of the node
    "if_statement": False,
    # "else_clause": False,
    "try_statement": False,
    "function_definition": False,

    # Parent of the node
    "child_of_class_definition": False,
    "child_of_elif_clause": False,
    "child_of_else_clause": False,
    "child_of_except_clause": False,
    "child_of_finally_clause": False,
    "child_of_for_statement": False,
    "child_of_function_definition": False,
    "child_of_if_statement": False,
    "child_of_module": False,
    "child_of_try_statement": False,
    "child_of_while_statement": False,
    "child_of_with_statement": False,

    # Children of the node
    "contains_if": False,
    "contains_try": False,
    "contains_with": False,
    "contains_logging": False
}

features_onehot = make_features([("type", ""), ("parent", "")])
par_vec_onehot = dict([x for y in features_onehot for x in y])

# DEPRECATED
par_vec_onehot_manual = {
    "line": -1,
    "type": "",
    "parent": "",
    "contains_if": False,
    "contains_try": False,
    "contains_with": False,
    "contains_logging": False
}

reindex = ['contains_class_definition', 'contains_for_statement',
       'contains_function_definition', 'contains_if_statement',
       'contains_try_statement', 'contains_while_statement',
       'contains_with_statement', 'contains_assert_statement',
       'contains_break_statement', 'contains_continue_statement',
       'contains_delete_statement', 'contains_exec_statement',
       'contains_expression_statement', 'contains_future_import_statement',
       'contains_global_statement', 'contains_import_from_statement',
       'contains_import_statement', 'contains_nonlocal_statement',
       'contains_pass_statement', 'contains_print_statement',
       'contains_raise_statement', 'contains_return_statement',
       'type_class_definition', 'type_elif_clause',
       'type_else_clause', 'type_except_clause', 'type_finally_clause',
       'type_for_statement', 'type_function_definition', 'type_if_statement',
       'type_try_statement', 'type_while_statement', 'type_with_statement',
       'parent_class_definition', 'parent_elif_clause', 'parent_else_clause',
       'parent_except_clause', 'parent_finally_clause', 'parent_for_statement',
       'parent_function_definition', 'parent_if_statement', 'parent_module',
       'parent_try_statement', 'parent_while_statement',
       'parent_with_statement']
# print(par_vec_bool)
# print(par_vec_onehot)
