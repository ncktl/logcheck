from tree_sitter import Language, Parser
import sys
from pathlib import Path
import importlib
import argparse
from config import par_vec_bool, par_vec_onehot, reindex
from sklearn.svm import LinearSVC
import pandas as pd
import pickle

supported_languages = ["java", "python"]
suf = {
    "java": ".java",
    "python": ".py"
}
rev_suf = dict(zip(suf.values(), suf.keys()))


def create_ts_lang_obj(language: str) -> Language:
    """
    Creates a tree-sitter language library in the 'build' directory
    A given language library only needs to be built once across many executions.
    :param language: string containing the programming language to be analyzed
    :return: tree-sitter language object
    """
    Language.build_library("build/my-languages.so", list("tree-sitter-" + lang for lang in supported_languages))
    ts_lang = Language("build/my-languages.so", language)
    return ts_lang


def extract(training: bool = True):
    """ Extracts parameter vectors from the file(s) """
    param_vectors = []
    for file in files:
        with open(file) as f:
            sourcecode = f.read()
            f.close()
        # Check if logging is imported. Python specific placeholder!
        if training:
            if "import logging" not in sourcecode:
                continue
        # print(f"File: {file}")
        # Create abstract syntax tree
        tree = parser.parse(bytes(sourcecode, "utf8"))
        # Import the appropriate extractor and instantiate it
        extractor_class = getattr(importlib.import_module(args.language + "_extractor"),
                                  args.language.capitalize() + "Extractor")
        extractor = extractor_class(sourcecode, tree_lang, tree, file, args)
        # Start the extraction
        file_param_vecs = extractor.fill_param_vecs_ast_new(training)
        if args.debug:
            param_vectors += [f" {file} "]
        param_vectors += file_param_vecs
    with open(args.output, "w") as out:
        if args.mode == "bool":
            out.write(",".join(key for key in par_vec_bool.keys()))
        elif args.mode == "onehot":
            out.write(",".join(key for key in par_vec_onehot.keys()))
        out.write("\n")
        out.write("\n".join([str(x).replace(" ", "").replace("'", "")[1:-1] for x in param_vectors]))
        out.write("\n")
        out.close()


def analyze_newer():
    """ Recommend logging"""
    output = []
    classifier: LinearSVC = pickle.load(open('classifier', 'rb'))
    for file in files:
        with open(file) as f:
            sourcecode = f.read()
            f.close()
        #print(f"File: {file}")
        # Create abstract syntax tree
        tree = parser.parse(bytes(sourcecode, "utf8"))
        # Import the appropriate extractor and instantiate it
        extractor_class = getattr(importlib.import_module(args.language + "_extractor"),
                                  args.language.capitalize() + "Extractor")
        extractor = extractor_class(sourcecode, tree_lang, tree, args.path, args)
        # Build a list of parameter vectors for all interesting nodes in the current file
        file_param_vecs = extractor.fill_param_vecs_ast_new(training=False)
        # print(df.to_string())
        if file_param_vecs:
            # Build Pandas DataFrame from the list of parameter vectors
            df = pd.DataFrame.from_dict(file_param_vecs).drop(["line", "contains_logging"], axis=1)
            # One-hot encode the parameters type and parent
            df = pd.get_dummies(df, columns=["type", "parent"])
            # Reindex the dataframe to ensure all possible type and parent values are present as columns
            df = df.reindex(reindex, fill_value=False, axis="columns")
            # print(classifier.predict(df))
            # Predict logging for the parameters vectors, creating a list of booleans for the parameter vectors
            recs = classifier.predict(df)
            # Write the yes-instances as recommendations to the output file
            if True in recs:
                output.append(f"File: {file}")
                for i, prediction in enumerate(recs):
                    if prediction:
                        # Assumption: onehot
                        output.append(f"We recommend logging in the {file_param_vecs[i]['type']} "
                                      f"starting in line {file_param_vecs[i]['line']}")
    with open(args.output, "w") as out:
        if output:
            out.write("\n".join(output))
        else:
            out.write("No recommendations")
        out.write("\n")
        out.close()


# DEPRECATED
def analyze():
    """ Analyses the code in the file(s) """
    output = []
    for file in files:
        with open(file) as f:
            sourcecode = f.read()
            f.close()
        print(f"File: {file}")
        # Create abstract syntax tree
        tree = parser.parse(bytes(sourcecode, "utf8"))
        # Import the appropriate analyzer and instantiate it
        analysis_class = getattr(importlib.import_module(args.language + "_analyzer"),
                                 args.language.capitalize() + "Analyzer")
        analyzer = analysis_class(sourcecode, tree_lang, tree, args.path, args)
        # Start the analysis
        file_analysis = analyzer.analyze()
        # output.append(f"{file}")
        # print(output)
        if file_analysis:
            output.append(f"File: {file}")
            output.extend(file_analysis)
    print("\n".join(output))
    # with open(args.output, "w") as out:
    #     if output:
    #         out.write("\n".join(output))
    #     else:
    #         out.write("No recommendations")
    #     out.write("\n")
    #     out.close()


if __name__ == "__main__":
    # Handle arguments
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("path", type=Path)
    arg_parser.add_argument("-b", "--batch", action="store_true",
                            help="Enable batch mode. Logcheck will be run on all source code files of"
                                 " the given programming language found in the specified directory and "
                                 "subdirectories. Requires the -l / --language argument.")
    arg_parser.add_argument("-e", "--extract", action="store_true",
                            help="Enables feature extraction mode. Logcheck will output parameter "
                                 "vectors from its analysis instead of logging recommendations.")
    arg_parser.add_argument("-o", "--output", type=Path,
                            help="Specify the output file.")
    arg_parser.add_argument("-f", "--force", action="store_true",
                            help="Force overwrite of output file")
    arg_parser.add_argument("-l", "--language", type=str, choices=supported_languages, default="python",
                            help="Specify the language. Default: python")
    arg_parser.add_argument("-m", "--mode", type=str, choices=["bool", "onehot"], default="onehot",
                            help="Mode of encoding. Default: onehot")
    arg_parser.add_argument("-d", "--debug", action="store_true",
                            help="Enable debug mode")
    arg_parser.add_argument("-a", "--alt", action="store_true",
                            help="Use alternative / old functions")
    arg_parser.add_argument("-s", "--suffix", action="store_true",
                            help="Add mode of encoding to file name")
    args = arg_parser.parse_args()
    # Check arguments
    if not args.path.exists():
        arg_parser.error("Path does not exist.")
    if not args.batch and args.path.is_dir():
        arg_parser.error("Use batch mode when specifying directories.")
    # Handle output
    if not args.output:
        # Analysis
        if not args.extract:
            if args.batch:
                args.output = Path("analysis/demofile.txt")
                print(f"No output file specified. Using default: {args.output}")
            else:
                args.output = Path("analysis/" + args.path.name + ".txt")
                print(f"No output file specified. Using: {args.output}")
        # Feature extraction
        else:
            if args.batch:
                args.output = Path("features/demofile.csv")
                print(f"No output file specified. Using default: {args.output}")
            else:
                args.output = Path("features/" + args.path.name + ".csv")
                print(f"No output file specified. Using: {args.output}")
    if args.suffix:
        args.output = args.output.with_suffix(f".{args.mode}.csv")
    if args.output.is_file() and not args.force:
        # arg_parser.error("Output file exists. Use the -f argument to overwrite.")
        def overwrite():
            force = input("Output file exists. Overwrite? [y/n]: ")
            if force.lower() in ["y", "yes"]:
                pass
            elif force.lower() in ["n", "no"]:
                print("Exiting")
                sys.exit()
            else:
                overwrite()
        overwrite()
    print(f"Output file: {args.output}")
    # Catch permission errors before program execution
    try:
        args.output.touch()
    except PermissionError as e:
        arg_parser.error(e)
    # Ensure language is known
    # DEPRECATED because python is the default
    if args.batch:
        if args.language is None:
            arg_parser.error("Batch option requires specification of language.")
    # Without batch mode, determine language if not specified
    elif args.language is None:
        try:
            args.language = rev_suf[args.path.suffix]
        except KeyError:
            arg_parser.error(f"Supported languages: {supported_languages}")
    # Create tree-sitter parser
    tree_lang = create_ts_lang_obj(args.language)
    parser = Parser()
    parser.set_language(tree_lang)
    # Determine files to work on
    if args.batch:
        files = args.path.glob(f"**/*{suf[args.language]}")
    else:
        files = [args.path]
    # Branch into extraction or analysis
    if args.extract:
        extract()
    else:
        if args.alt:
            analyze()
        else:
            analyze_newer()
