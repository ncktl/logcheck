keyword = "logg(ing|er)"

# Todo: Onehot: encode with OdrdinalEncoder
# Todo: Test with X = pd.get_dummies(X) and X = pd.get_dummies(X, drop_first=True)

compound_statements = [
    "class_definition",
    "decorated_definition",
    "for_statement",
    "function_definition",
    "if_statement",
    "match_statement",
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
    "exec_statement",
    "expression_statement",
    "future_import_statement",
    "global_statement",
    "import_from_statement",
    "import_statement",
    "nonlocal_statement",
    "pass_statement",
    "print_statement",
    "raise_statement",
    "return_statement"
]

# Todo: Make module's value an int? Perhaps check if there is executing code on the top level and increase accordingly?
extra_clauses = ["elif_clause", "else_clause", "except_clause", "finally_clause", "module"]
# Todo: Test with if_else, try_else,... instead of else_clause and so on

interesting_node_types = ["if_statement", "try_statement", "function_definition"]
# Todo: Fix this breaking change:
# interesting_node_types = compound_statements + extra_clauses


# contains_features check the node's direct children in its block
contains_types = compound_statements + simple_statements + ["logging"]


# Todo: Test with node count for contains_features -> type(par_vec_extended["contains_features"]) == int


def prefix(string):
    return lambda x: [string + y for y in x]


def vectorize(x):
    return zip(x, [False] * len(x))


interesting_nodes = prefix("")(interesting_node_types)
children_of = prefix("child_of_")(interesting_node_types)
contains = prefix("contains_")(contains_types)


def make_features(x):
    return [[("line", -1)] + x + list(vectorize(contains))]


# features = [
#     [("line", -1)],
#     list(vectorize(interesting_nodes)),
#     list(vectorize(children_of)),
#     list(vectorize(contains))
# ]
#
# par_vec_bool = dict([x for y in features for x in y])
features_bool = make_features(list(vectorize(interesting_nodes)) + list(vectorize(children_of)))
par_vec_bool = dict([x for y in features_bool for x in y])

# Bool manual
par_vec_extended = {
    "line": -1,

    # Type of the node
    "if_statement": False,
    # Todo: Test Bool:  splitting else_clause (and child_of_else_clause) feature into
    # Todo:         if_else, try_else, for_else, while_else (..?)
    # Todo:         Likewise for try_statement: try_except, try_finally
    # Todo:         I.e. only have the compound_statements as "first-class" type-features
    # Todo:         Consider the implication of except_clause=True (unambigous so try_except not needed)
    # Todo:         for child_of_try_statement
    # "else_clause": False,
    "try_statement": False,
    "function_definition": False,

    # Parent of the node
    "child_of_class_definition": False,
    # Todo: Test decorated_definition extraction
    "child_of_decorated_definition": False,
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

features_onehot = make_features([("line", -1), ("type", ""), ("parent", "")])
par_vec_onehot = dict([x for y in features_onehot for x in y])

par_vec_onehot_manual = {
    "line": -1,
    # Todo: Test Onehot: type = if_else, try_else, for_else,... instead of else_clause
    "type": "",
    "parent": "",
    "contains_if": False,
    "contains_try": False,
    "contains_with": False,
    "contains_logging": False
}
