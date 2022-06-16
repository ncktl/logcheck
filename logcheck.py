from tree_sitter import Language, Parser
import sys
from pathlib import Path
import importlib

supported_languages = ["java", "python", "haskell"]


def create_ts_lang_obj(language: str):
    """
    Creates a treesitter language library in the 'build' directory
    A given language library only needs to be built once across many executions.
    :param language: string containing the programming language to be analyzed
    :return: treesitter language object
    """
    Language.build_library("build/my-languages.so", list("tree-sitter-" + lang for lang in supported_languages))
    ts_lang = Language("build/my-languages.so", language)
    return ts_lang


def print_supported_languages():
    print(f"Supported languages: {supported_languages}", file=sys.stderr)


def print_usage():
    print(f"Usage: python3 {__file__} [-L <language>] <file to be analyzed>", file=sys.stderr)
    print("If no language is specified, the analyzer will attempt to infer the language.", file=sys.stderr)
    print_supported_languages()


def infer_language(file_path: Path):
    """
    Detects the programming language from the file extension
    :param file_path:
    :return: String containing programming language name
    """
    if file_path.suffix == ".py":
        return "python"
    elif file_path.suffix == ".java":
        return "java"
    # elif file_path.suffix == ".js":
    #    return "javascript"
    elif file_path.suffix == ".hs":
        return "haskell"
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
    # Import the appropriate analyzer and instantiate it
    analysis_class = getattr(importlib.import_module(prog_lang + "_analyzer"), prog_lang.capitalize() + "Analyzer")
    analyzer = analysis_class(sourcecode, tree_lang, tree, file_path)
    # Start the analysis
    analyzer.analyze()


if __name__ == "__main__":
    main(sys.argv)
