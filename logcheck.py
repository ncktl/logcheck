import argparse
import importlib
import logging
import multiprocessing as mp
import pickle
import sys
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from tqdm import tqdm
from tree_sitter import Language, Parser

from config import reindex, par_vec_onehot_expanded, rev_node_dict

supported_languages = ["java", "javascript", "python"]
suf = {
    "java": ".java",
    "javascript": ".js",
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
    lib_path = str(Path(Path(__file__).parent / "build/my-languages.so").resolve())
    lang_paths = [str(Path(Path(__file__).parent / ("tree-sitter-" + lang)).resolve()) for lang in supported_languages]
    Language.build_library(lib_path, lang_paths)
    ts_lang = Language(lib_path, language)
    return ts_lang


def extract_file(file, settings, train_mode):
    """ Extracts features from a source code file and returns them as a list of parameter vectors (also lists) """

    # Read the source code
    try:
        with open(file) as f:
            sourcecode = f.read()
            f.close()
    except UnicodeDecodeError as e:
        logger.error(f"Encountered UnicodeDecodeError in file {file}:\n{e}")
        return []
    # Create Tree-Sitter language object and parser.
    # These could be reused for another source code file, but this is nontrivial due to parallelization.
    tree_lang = create_ts_lang_obj(settings.language)
    parser = Parser()
    parser.set_language(tree_lang)
    # Create abstract syntax tree
    tree = parser.parse(bytes(sourcecode, "utf8"))
    # Import the language's extractor and instantiate it
    extractor_class = getattr(importlib.import_module(settings.language + "_extractor"),
                              settings.language.capitalize() + "Extractor")
    extractor = extractor_class(sourcecode, tree_lang, tree, file, settings)
    # Start the extraction
    file_param_vecs = extractor.fill_param_vectors(training=train_mode)
    if settings.debug:
        file_param_vecs = ["/" + str(file) + "y"] + file_param_vecs
    return file_param_vecs


def extract(files, settings, output, train_mode: bool = True):
    """ Starts parallelized feature extraction and writes the result to output """

    # Extract features from each file by calling extract_file() in parallel
    pool = mp.Pool(mp.cpu_count())
    # Async variant:
    # param_vectors = pool.starmap_async(extract_file, [(file, settings, train_mode) for file in files]).get()
    # Ordered parallelization:
    param_vectors = pool.starmap(extract_file, [(file, settings, train_mode) for file in files])
    param_vectors = [par_vec for par_vec_list in param_vectors for par_vec in par_vec_list]
    pool.close()
    # Write output
    header = list(par_vec_onehot_expanded.keys())
    output.write(",".join(header) + "\n")
    output.write("\n".join(
        [str(x).replace(" ", "").replace("'", "")[1:-1] for x in param_vectors]))
    output.write("\n")


def recommend(files, settings, output):
    """ Recommend logging """
    recommendations = []
    classifier: RandomForestClassifier = pickle.load(open('classifier', 'rb'))
    for file in tqdm(files):
        with open(file) as f:
            sourcecode = f.read()
            f.close()
        # print(f"File: {file}")
        # Create tree-sitter parser
        tree_lang = create_ts_lang_obj(settings.language)
        parser = Parser()
        parser.set_language(tree_lang)
        # Create abstract syntax tree
        tree = parser.parse(bytes(sourcecode, "utf8"))
        # Import the appropriate extractor and instantiate it
        extractor_class = getattr(importlib.import_module(settings.language + "_extractor"),
                                  settings.language.capitalize() + "Extractor")
        extractor = extractor_class(sourcecode, tree_lang, tree, file, settings)
        # Build a list of parameter vectors for all interesting nodes in the current file
        file_param_vecs = extractor.fill_param_vectors(training=False)
        # print(df.to_string())
        if file_param_vecs:
            # Build Pandas DataFrame from the list of parameter vectors
            df = pd.DataFrame.from_dict(file_param_vecs)
            # logger.debug(df); exit()
            X = df.drop(["contains_logging", "location", "context", "sibling_index"], axis=1)
            # X = df.drop(["contains_logging"], axis=1)
            # One-hot encode the parameters type and parent
            X = pd.get_dummies(X, columns=["type", "parent"])
            # Reindex the dataframe to ensure all possible type and parent values are present as columns
            X = X.reindex(reindex, fill_value=0, axis="columns")
            # print(classifier.predict(df))
            # Predict logging for the parameter vectors, creating a list of booleans for the parameter vectors
            file_recommendations = classifier.predict(X)
            df['predictions'] = file_recommendations
            # Write the yes-instances as recommendations to the output file
            if 1 in file_recommendations:
                recommendations.append(f"File: {file}")
                for i, prediction in enumerate(file_recommendations):
                    if prediction:
                        line = file_param_vecs[i]['location'].split("-")[0].split(";")[0]
                        recommendations.append(f"We recommend logging in the {rev_node_dict[file_param_vecs[i]['type']]} "
                                      f"starting in line {line}")
    if recommendations:
        output.write("\n".join(recommendations))
    else:
        output.write("No recommendations")
    output.write("\n")
    output.close()


# DEPRECATED
def analyze():
    """ Calls analysis functions for development and debugging """
    # print("analyze")
    # print(args.language)
    output = []
    for file in files:
        with open(file) as f:
            sourcecode = f.read()
            f.close()
        print(f"File: {file}")
        # Create tree-sitter parser
        tree_lang = create_ts_lang_obj(args.language)
        parser = Parser()
        parser.set_language(tree_lang)
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


if __name__ == "__main__":
    # Handle arguments
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("path", type=Path)
    arg_parser.add_argument("-e", "--extract", action="store_true",
                            help="Enables feature extraction mode. Logcheck will output parameter "
                                 "vectors from its analysis instead of logging recommendations.")
    arg_parser.add_argument("-o", "--output", type=Path,
                            help="Specify the output file.")
    arg_parser.add_argument("-f", "--force", action="store_true",
                            help="Force overwrite of output file")
    arg_parser.add_argument("-l", "--language", type=str, choices=supported_languages,
                            help="Specify the language.")
    arg_parser.add_argument("-d", "--debug", action="store_true",
                            help="Enable debug mode.")
    arg_parser.add_argument("-a", "--alt", action="store_true",
                            help="Also extract the context when in extraction mode")
    args = arg_parser.parse_args()

    # Check arguments
    if not args.path.exists():
        arg_parser.error("Path does not exist.")
    # Detect batch mode
    if args.path.is_dir():
        batch = True
    elif args.path.is_file():
        batch = False
    else:
        arg_parser.error("Path is neither file nor directory.")

    # Default output handling disabled in favor of printing to stdout
    # # Handle output
    # if not args.output:
    #     # Feature extraction
    #     if args.extract:
    #         if batch:
    #             args.output = Path("features/demofile.csv")
    #             print(f"No output file specified. Using default: {args.output}")
    #         else:
    #             args.output = Path("features/" + args.path.name + ".csv")
    #             print(f"No output file specified. Using: {args.output}")
    #     # Analysis
    #     else:
    #         if batch:
    #             args.output = Path("analysis/demofile.txt")
    #             print(f"No output file specified. Using default: {args.output}")
    #         else:
    #             args.output = Path("analysis/" + args.path.name + ".txt")
    #             print(f"No output file specified. Using: {args.output}")

    # File overwrite dialog
    if args.output and args.output.is_file() and not args.force:
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
    # Catch permission errors before program execution
    try:
        out = open(args.output, "w") if args.output else sys.stdout
    except PermissionError as e:
        arg_parser.error(e)
    # Ensure language is known
    if batch:
        if args.language is None:
            arg_parser.error("Batch option requires specification of language.")
    # Without batch mode, determine language if not specified
    elif args.language is None:
        try:
            args.language = rev_suf[args.path.suffix]
        except KeyError:
            arg_parser.error(f"Supported languages: {supported_languages}")
    # Determine files to work on
    if batch:
        files = list(args.path.glob(f"**/*{suf[args.language]}"))
    else:
        files = [args.path]
    # Initialize logger
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("Logcheck")
    # Branch into extraction or analysis
    if args.extract:
        extract(files, args, out)
    else:
        if args.alt:
            analyze()
        else:
            recommend(files, args, out)
