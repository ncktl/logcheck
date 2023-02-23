import argparse
import importlib
import logging
import multiprocessing as mp
import pickle
import sys
from pathlib import Path
from string import ascii_letters

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from tqdm import tqdm
from tree_sitter import Language, Parser

from config import supported_languages, suf, rev_suf
from config import parameter_vectors, rev_node_dicts, reindex
from notebooks.notebook_helper import get_X_and_y_from_csv


def overwrite():
    force = input("Output file exists. Overwrite? [y/n]: ")
    if force.lower() in ["y", "yes"]:
        pass
    elif force.lower() in ["n", "no"]:
        print("Exiting")
        sys.exit()
    else:
        overwrite()


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


def extract_file(file, settings, LangExtractor, train_mode):
    """ Extracts features from a source code file and returns them as a list of parameter vectors (also lists) """

    # Read the source code
    try:
        with open(file) as f:
            sourcecode = f.read()
            f.close()
    except UnicodeDecodeError as e:
        logger.error(f"Encountered UnicodeDecodeError in file {file}:\n{e}")
        return []
    except IsADirectoryError as e:
        logger.error(f"Encountered directory with a name ending like the language extension {file}:\n{e}")
        return []
    # Create Tree-Sitter language object and parser.
    # These could be reused for another source code file, but this is nontrivial due to parallelization.
    tree_lang = create_ts_lang_obj(settings.language)
    parser = Parser()
    parser.set_language(tree_lang)
    # Create abstract syntax tree
    tree = parser.parse(bytes(sourcecode, "utf8"))
    # Instantiate the language's extractor
    extractor = LangExtractor(sourcecode, tree_lang, tree, file, settings)
    # Start the extraction
    file_param_vecs = extractor.fill_param_vectors(training=train_mode)
    if settings.debug:
        file_param_vecs = ["/" + str(file) + "y"] + file_param_vecs
    return file_param_vecs


def extract(files, settings, LangExtractor, output, train_mode: bool = True):
    """ Starts parallelized feature extraction and writes the result to output """

    # Extract features from each file by calling extract_file() in parallel
    pool = mp.Pool(mp.cpu_count())
    # Async variant:
    # param_vectors = pool.starmap_async(extract_file, [(file, settings, train_mode) for file in files]).get()
    # Ordered parallelization:
    param_vectors = pool.starmap(extract_file, [(file, settings, LangExtractor, train_mode) for file in files])
    param_vectors = [par_vec for par_vec_list in param_vectors for par_vec in par_vec_list]
    pool.close()
    # Write output
    header = list(parameter_vectors[settings.language].keys())
    output.write(",".join(header) + "\n")
    output.write("\n".join(
        [str(x).replace(" ", "").replace("'", "")[1:-1] for x in param_vectors]))
    output.write("\n")

def train(files, settings, LangExtractor, output):
    """Train classifier"""

    # Import modules only needed for training
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import recall_score, f1_score, precision_score, balanced_accuracy_score

    model_is_rndfrst = (settings.model == "rnd")

    # Extract features from each file by calling extract_file() in parallel
    pool = mp.Pool(mp.cpu_count())
    # Ordered parallelization:
    param_vectors = pool.starmap(extract_file, [(file, settings, LangExtractor, True) for file in files])
    param_vectors = [par_vec for par_vec_list in param_vectors for par_vec in par_vec_list]
    pool.close()

    # Get X and y and drop context for random forest classifiers as they don't use it
    X, y = get_X_and_y_from_csv(param_vectors, drop_context=model_is_rndfrst)

    # Reindex
    X = X.reindex((["context"] if not model_is_rndfrst else []) + reindex[settings.language],
                  fill_value=0, axis="columns")

    # Convert the compacted context from letters into strings of integers
    if not model_is_rndfrst:
        X.context = [list(map(lambda c: str(ascii_letters.index(c)), list(str(x)))) for x in X.context]

    # Splitting the dataset into the Training set and Test set
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, stratify=y)

    # Train the chosen model and predict on test set
    if model_is_rndfrst:
        classifier = RandomForestClassifier(n_estimators=50,
                                            n_jobs=-1,
                                            min_samples_split=5,
                                            class_weight={False: 1, True: 4}
                                            )
        classifier.fit(X_train, y_train)
        y_pred = classifier.predict(X_test)
    else:
        # from notebooks.notebook_helper import MyCorpus, build_embedding_matrix, build_callbacks, build_hybrid_model
        # import numpy as np
        # import gensim.models
        # import tensorflow_addons as tfa
        from imblearn.over_sampling import RandomOverSampler
        # from tensorflow.keras.preprocessing.sequence import pad_sequences
        import tensorflow as tf

        # Limit usage to second gpu
        try:
            print("Before:\n", tf.config.get_visible_devices('GPU'))
            gpus = tf.config.list_physical_devices('GPU')
            tf.config.experimental.set_visible_devices(gpus[1], 'GPU')
            print("After:\n", tf.config.get_visible_devices('GPU'))
        except IndexError as e:
            pass

        repo_name = f"{settings.language}_{settings.path.stem}"

        # Word2vec model
        sentences = MyCorpus(list(X.context))
        gensim_model = gensim.models.Word2Vec(sentences=sentences, min_count=1, workers=mp.cpu_count())

        # Settings
        sampling_strategy = 0.05
        vocab_size = len(rev_node_dicts[settings.language])
        other_input_num_cols = len(reindex[settings.language])
        output_dims = 100
        max_length = 80
        num_epochs = 20  ### changed
        batch_size = 64
        trainable = True
        dropout = 0.2
        val_split = 0.0
        num_nodes = 128
        callback = ["cp"]
        callback_monitor = 'val_f1_score'
        cmpltn_metrics = [tfa.metrics.F1Score(num_classes=1, threshold=0.5)]
        # Cross-validation settings (k-fold splits are actually NOT used here)
        n_splits = 1

        # Build embedding matrix
        embedding_matrix = build_embedding_matrix(vocab_size, output_dims, gensim_model)
        # Save the embedding matrix
        pickle.dump(embedding_matrix, open(f"{settings.language}_{repo_name}_embedding_matrix", 'wb'))

        # Build and compile model
        model = build_hybrid_model(vocab_size, output_dims, embedding_matrix, max_length,
                                   trainable, num_nodes, dropout, other_input_num_cols)
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=cmpltn_metrics)

        # Oversample
        neg, pos = pd.value_counts(y_train)
        log_ratio = pos / (neg + pos)
        if log_ratio < sampling_strategy:
            # RandomOverSampler may still find the log ratio to be too high for some reason
            sampler = RandomOverSampler(sampling_strategy=sampling_strategy)
            X_train, y_train = sampler.fit_resample(X_train, y_train)

        # Pad the context to create the context input
        padded_inputs = pad_sequences(np.array(list(X_train.context), dtype=object), maxlen=max_length, value=0.0)
        padded_inputs_test = pad_sequences(np.array(list(X_test.context), dtype=object), maxlen=max_length, value=0.0)
        # Prepare the "other" input
        regular_inputs = X_train.drop(["context"], axis=1)
        regular_inputs_test = X_test.drop(["context"], axis=1)
        # Put both inputs into a dict
        X_train_dict = {"context": padded_inputs, "other": regular_inputs}
        X_test_dict = {"context": padded_inputs_test, "other": regular_inputs_test}

        # Build the callbacks

        callbacks, model_cp_filepath = build_callbacks(callback, callback_monitor, repo_name, "checkp")

        # Fit the model
        history = model.fit(
            X_train_dict,
            {"logging": y_train},
            epochs=num_epochs,
            batch_size=batch_size,
            validation_data=(X_test_dict, y_test),
            validation_split=val_split,
            callbacks=callbacks,
        )
        # Now load the best weights and predict on test data
        model.load_weights(model_cp_filepath)
        best_pred_test = model.predict(X_test_dict, batch_size=batch_size)
        y_pred = np.round(best_pred_test)

    # Evaluate classifier on test set
    score_names = [
        "Balanced accuracy score",
        "Precision score",
        "Recall score",
        "F1 Binary"
    ]
    scores = [
        balanced_accuracy_score(y_test, y_pred),
        precision_score(y_test, y_pred),
        recall_score(y_test, y_pred),
        f1_score(y_test, y_pred, average='binary', pos_label=True)
    ]
    score_df = pd.DataFrame([scores], columns=score_names).mean().round(3)
    print("Scores:")
    print(score_df)

    # Save classifier
    if model_is_rndfrst:
        # Default classifier save location
        if output == sys.stdout:
            output = Path(settings.language + "_" + settings.path.stem + "_classifier")
            # Non-standard output path has already been checked for overwriting
            print(f"Default classifier output path: {output}")
            if output.is_file() and not settings.force:
                overwrite()
            output = open(output, 'wb')
        # Save classifier
        pickle.dump(classifier, output)
        print(f"Created and saved classifier in {output}")
    else:
        print(f"LSTM checkpoint file path: {model_cp_filepath}")

    # if output == sys.stdout:
    #     print("output == sys.stdout")


def recommend(files, settings, LangExtractor, output):
    """ Recommend logging """

    model_is_rndfrst = (settings.model == "rnd")

    recommendations = []
    # rev_node_dict = rev_node_dicts[settings.language]
    if model_is_rndfrst:
        clf_name = f"{settings.language}_logging_classifier"
        classifier: RandomForestClassifier = pickle.load(open(clf_name, 'rb'))
    else:
        # Settings
        vocab_size = len(rev_node_dicts[settings.language])
        other_input_num_cols = len(reindex[settings.language])
        output_dims = 100
        max_length = 80
        batch_size = 64
        trainable = True
        dropout = 0.2
        num_nodes = 128
        cmpltn_metrics = [tfa.metrics.F1Score(num_classes=1, threshold=0.5)]
        # Load embedding matrix
        embedding_matrix = pickle.load(open(f"{settings.language}_embedding_matrix", 'rb'))
        # Build and compile model
        model = build_hybrid_model(vocab_size, output_dims, embedding_matrix, max_length,
                                   trainable, num_nodes, dropout, other_input_num_cols)
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=cmpltn_metrics)
        # Load weights
        model_cp_filepath = f"hybrid_models{os.sep}{settings.language}_logging{os.sep}checkp"
        model.load_weights(model_cp_filepath)

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
        # Instantiate the language's extractor
        extractor = LangExtractor(sourcecode, tree_lang, tree, file, settings)
        # Build a list of parameter vectors for all interesting nodes in the current file
        file_param_vecs = extractor.fill_param_vectors(training=False)
        # print(df.to_string())
        if file_param_vecs:
            # Build Pandas DataFrame from the list of parameter vectors
            df = pd.DataFrame.from_dict(file_param_vecs)
            # logger.debug(df); exit()

            # Drop unused features
            cols_to_drop = [
                "contains_logging", "location", "grandparent",
                "num_siblings", "depth_from_def", "depth_from_root"
            ]
            if model_is_rndfrst:
                cols_to_drop.append("context")
            X = df.drop(cols_to_drop, axis=1)

            # One-hot encode the parameters type and parent
            X = pd.get_dummies(X, columns=["type", "parent"])
            # Reindex the dataframe to ensure all possible type and parent values are present as columns
            X = X.reindex((["context"] if not model_is_rndfrst else []) + reindex[settings.language],
                          fill_value=0, axis="columns")
            if not model_is_rndfrst:
                # Convert the compacted context from letters into strings of integers
                X.context = [list(map(lambda c: str(ascii_letters.index(c)), list(str(x)))) for x in X.context]

                # Prepare test sets
                padded_inputs = pad_sequences(np.array(list(X.context), dtype=object),
                                                      maxlen=max_length, value=0.0)
                regular_inputs = X.drop(["context"], axis=1)
                X_dict = {"context": padded_inputs, "other": regular_inputs}



                # Predict
                pred = model.predict(X_dict, batch_size=batch_size)
                file_recommendations = np.round(pred)
            else:
                file_recommendations = classifier.predict(X)

            df['predictions'] = file_recommendations
            # Write the yes-instances as recommendations to the output file
            if 1 in file_recommendations:
                recommendations.append(f"File: {file}")
                for i, prediction in enumerate(file_recommendations):
                    if prediction:
                        line = file_param_vecs[i]['location'].split("-")[0].split(";")[0]
                        recommendations.append(f"We recommend logging in the "
                                               # f"{rev_node_dict[file_param_vecs[i]['type']]}"
                                               f"{file_param_vecs[i]['type']}"
                                               f" starting in line {line}")
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
    # print(settings.language)
    output = []
    for file in files:
        with open(file) as f:
            sourcecode = f.read()
            f.close()
        print(f"File: {file}")
        # Create tree-sitter parser
        tree_lang = create_ts_lang_obj(settings.language)
        parser = Parser()
        parser.set_language(tree_lang)
        # Create abstract syntax tree
        tree = parser.parse(bytes(sourcecode, "utf8"))
        # Import the appropriate analyzer and instantiate it
        analysis_class = getattr(importlib.import_module(settings.language + "_analyzer"),
                                 settings.language.capitalize() + "Analyzer")
        analyzer = analysis_class(sourcecode, tree_lang, tree, settings.path, settings)
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
    arg_parser.add_argument("path", type=Path,
                            help="The file or folder containing files to predict or train on. "
                                 "Files in subdirectories are included.")
    arg_parser.add_argument("-m", "--model", type=str, choices=["rnd", "lstm"],
                            help="Specify the classifier model, either random forest (rnd) or LSTM (lstm). "
                                 "Required for prediction and training.")
    arg_parser.add_argument("-o", "--output", type=Path,
                            help="Specify the output path. By default logcheck will print to stdout.")
    arg_parser.add_argument("-f", "--force", action="store_true",
                            help="Force overwrite of output file")
    arg_parser.add_argument("-l", "--language", type=str, choices=supported_languages,
                            help="Specify the language.")
    arg_parser.add_argument("-t", "--train", action="store_true",
                            help="Enables training mode.")
    arg_parser.add_argument("-e", "--extract", action="store_true",
                            help="Enables feature extraction mode. Logcheck will output parameter "
                                 "vectors from its analysis instead of logging recommendations.")
    arg_parser.add_argument("-d", "--debug", action="store_true",
                            help="Enable debug mode.")
    arg_parser.add_argument("-a", "--alt", action="store_true",
                            help="Also extract the context when in extraction mode.")
    arg_parser.add_argument("-x", "--all", action="store_true",
                            help="Extract features for all blocks instead of only those inside function definitions."
                                 "Can't be used together with -a context extraction.")
    arg_parser.add_argument("-c", "--encode", action="store_true",
                            help="ASCII encode type names to save space.")
    settings = arg_parser.parse_args()

    # Check arguments
    if not settings.path.exists():
        arg_parser.error("Path does not exist.")
    if settings.alt and settings.all:
        arg_parser.error("Can't build context while also extracting features for all blocks.")
    if settings.extract and settings.train:
        arg_parser.error("Can't enter extraction mode and training mode at the same time.")
    if (not settings.extract or settings.train) and not settings.model:
        arg_parser.error("Prediction and training mode require specification of model via -m")
    # Detect batch mode
    if settings.path.is_dir():
        batch = True
    elif settings.path.is_file():
        batch = False
    else:
        arg_parser.error("Path is neither file nor directory.")

    # Import modules for classifier training and recommendation
    if settings.model == "rnd":
        pass
    elif settings.model == "lstm":
        import gensim.models
        from notebooks.notebook_helper import MyCorpus, build_embedding_matrix, build_callbacks, build_hybrid_model
        import tensorflow_addons as tfa
        from tensorflow.keras.preprocessing.sequence import pad_sequences
        import numpy as np
        import os

    # Default output handling disabled in favor of printing to stdout
    # # Handle output
    # if not settings.output:
    #     # Feature extraction
    #     if settings.extract:
    #         if batch:
    #             settings.output = Path("features/demofile.csv")
    #             print(f"No output file specified. Using default: {settings.output}")
    #         else:
    #             settings.output = Path("features/" + settings.path.name + ".csv")
    #             print(f"No output file specified. Using: {settings.output}")
    #     # Analysis
    #     else:
    #         if batch:
    #             settings.output = Path("analysis/demofile.txt")
    #             print(f"No output file specified. Using default: {settings.output}")
    #         else:
    #             settings.output = Path("analysis/" + settings.path.name + ".txt")
    #             print(f"No output file specified. Using: {settings.output}")

    # File overwrite dialog
    if settings.output and settings.output.is_file() and not settings.force:
        overwrite()
    # Catch permission errors before program execution
    try:
        writing = "wb" if settings.train else "w"
        out = open(settings.output, writing) if settings.output else sys.stdout
    except PermissionError as e:
        arg_parser.error(e)
    # Ensure language is known
    if batch:
        if settings.language is None:
            arg_parser.error("Batch option requires specification of language.")
    # Without batch mode, determine language if not specified
    elif settings.language is None:
        try:
            settings.language = rev_suf[settings.path.suffix]
        except KeyError:
            arg_parser.error(f"Supported languages: {supported_languages}")
    # Determine files to work on
    if batch:
        files = list(settings.path.glob(f"**/*{suf[settings.language]}"))
    else:
        files = [settings.path]
    # Initialize logger
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("Logcheck")
    # Import the language's config and extractor
    # The extractor class has to be passed on as an argument due to parallelization
    if settings.language == "python":
        from python_extractor import PythonExtractor as LangExtractor
    elif settings.language == "java":
        from java_extractor import JavaExtractor as LangExtractor
    else:
        raise RuntimeError(f"{settings.language} is not actually supported yet.")
    # Branch into extraction or recommendation
    if settings.extract:
        extract(files, settings, LangExtractor, out)
    elif settings.train:
        train(files, settings, LangExtractor, out)
    else:
        if settings.alt:
            analyze()
        else:
            recommend(files, settings, LangExtractor, out)
