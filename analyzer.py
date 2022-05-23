# import logging
from tree_sitter import Language, Parser
import sys
from pathlib import Path
from PythonAnalyzer import PythonAnalyzer

supported_languages = ["javascript", "python"]


def js_exception_handling(tree_lang, tree):

    logging_indicators = ["console.error", "console.log"]

    # Query to find exception handling nodes in the ast
    exception_query = tree_lang.query("(catch_clause) @b")
    # Query to find function calls in the ast
    # call_query = tree_lang.query("(call_expression (identifier) @c)")
    # Query to find blocks
    block_query = tree_lang.query("(member_expression) @d")

    # Find the exception handling nodes
    exception_occurrences = exception_query.captures(tree.root_node)

    for i in exception_occurrences:
        print(i[0].text.decode("UTF-8"))
        # possible_log_occurrences = call_query.captures(i[0])
        investigation = block_query.captures(i[0])
        used_logging = False
        for j in investigation:
            if j[0].text.decode("UTF-8") in logging_indicators:
                used_logging = True
                break
        if used_logging:
            print("Logging used in exception handling. Well done!")
        else:
            print("Log your exceptions!")


def create_ts_lang_obj(language):
    """
    Creates a treesitter language library in the 'build' directory
    A given language library only needs to be built once across many executions.
    :param language: string containing the programming language to be analyzed
    :return: treesitter language object
    """
    Language.build_library("build/my-languages.so", ["tree-sitter-" + language])
    ts_lang = Language("build/my-languages.so", language)
    return ts_lang


def print_supported_languages():
    print(f"Supported languages: {supported_languages}", file=sys.stderr)


def print_usage():
    print(f"Usage: python3 {__file__} [-L <language>] <file to be analyzed>", file=sys.stderr)
    print("If no language is specified, the analyzer will attempt to infer the language.", file=sys.stderr)
    print_supported_languages()


def infer_language(file_path):
    """
    Detects the programming language from the file extension
    :param file_path:
    :return: String containing programming language name
    """
    if file_path.suffix == ".py":
        return "python"
    elif file_path.suffix == ".js":
        return "javascript"
    else:
        print_supported_languages()
        sys.exit()


def main(argv):
    """
    main program execution
    """
    arglen = len(argv)
    if not (arglen == 2 or arglen == 4):
        print_usage()
        sys.exit()
    file_path = Path(argv[-1])
    if not file_path.exists():
        print("File doesn't exist.", file=sys.stderr)
        print_usage()
        sys.exit()
    if arglen == 2:
        prog_lang = infer_language(file_path)
    else:  # -> arglen == 4
        prog_lang = argv[2].lower()
        # print(language)
    if prog_lang not in supported_languages:
        print_supported_languages()
        sys.exit()
    with open(argv[-1]) as file:
        sourcecode = file.read()
        file.close()
    # Treesitter Language object
    tree_lang = create_ts_lang_obj(prog_lang)
    parser = Parser()
    parser.set_language(tree_lang)
    # Create abstract syntax tree
    tree = parser.parse(bytes(sourcecode, "utf8"))
    analyzer = []
    if prog_lang == "python":
        analyzer = PythonAnalyzer(sourcecode, tree_lang, tree, file_path)
    if prog_lang == "javascript":
        analyzer = []
        pass
    analyzer.analyze()


if __name__ == "__main__":
    main(sys.argv)
