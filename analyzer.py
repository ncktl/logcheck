import logging

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
    # call_query = tree_lang.query("(call_expression (attribute . (identifier) @c))")  # too specific?
    call_query = tree_lang.query("(call_expression (identifier) @c)")

    block_query = tree_lang.query("(member_expression) @d")

    # Find the exception handling nodes
    exception_occurrences = exception_query.captures(tree.root_node)

    for i in exception_occurrences:
        #print(i)
        print(i[0].text.decode("UTF-8"))
        #print("Children:")
        #print(i[0].children)
        possible_log_occurences = call_query.captures(i[0])
        investigation = block_query.captures(i[0])
        used_logging = False
        for j in investigation:
            #print(j)
            #print(j[0].text.decode("UTF-8"))
            #print("Children:")
            #print(j[0].children)
            if j[0].text.decode("UTF-8") in logging_indicators:
                used_logging = True
                break
        if used_logging:
            print("Logging used in exception handling. Well done!")
        else:
            print("Log your exceptions!")
        # for j in possible_log_occurences:
        #     print(j)
        #     print(j[0].text.decode("UTF-8"))
        #     print("Children:")
        #     print(j[0].children)


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
        print("python detected")
        return "python"
    elif file_path.suffix == ".js":
        print("javascript detected")
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
    file = open(argv[-1], "r")
    sourcecode = file.read()
    file.close()
    # Treesitter Language object
    tree_lang = create_ts_lang_obj(prog_lang)
    parser = Parser()
    parser.set_language(tree_lang)
    # Create abstract syntax tree
    tree = parser.parse(bytes(sourcecode, "utf8"))
    #print(file_path.is)
    if prog_lang == "python":
        py_analyzer = PythonAnalyzer(sourcecode, tree_lang, file_path)
        py_analyzer.analyze()
    if prog_lang == "javascript":
        #js_exception_handling(tree_lang, tree)
        pass



if __name__ == "__main__":
    main(sys.argv)
