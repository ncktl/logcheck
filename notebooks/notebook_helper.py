# Helper functions for the notebooks

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.metrics import roc_auc_score, balanced_accuracy_score
from sklearn.metrics import confusion_matrix
from sklearn.metrics import precision_score, recall_score, f1_score

import pandas as pd
# Tensorflow + Keras
from keras.layers import CuDNNLSTM
import tensorflow as tf
import tensorflow.keras as keras
from tensorflow.keras.layers import Dense, LSTM, Embedding, Bidirectional
from tensorflow.keras.models import Sequential
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

from numpy import zeros
import numpy as np

iteration_features = "Name, Timestamp, sampling_strategy, max_length, vocab_size, batch_size, trainable," \
                     " dropout, val_split, callback, callback_monitor, num_nodes, num_epochs, class_weight," \
                     " cmpltn_metrics, run_folder, execution_time"

tex_fonts = {
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 11,
}


def set_size(width_pt=443.863, fraction=1, subplots=(1, 1)):
    """Set figure dimensions to sit nicely in our document.

    Parameters
    ----------
    width_pt: float
            Document width in points
    fraction: float, optional
            Fraction of the width which you wish the figure to occupy
    subplots: array-like, optional
            The number of rows and columns of subplots.
    Returns
    -------
    fig_dim: tuple
            Dimensions of figure in inches
    """
    # Width of figure (in pts)
    fig_width_pt = width_pt * fraction
    # Convert from pt to inches
    inches_per_pt = 1 / 72.27

    # Golden ratio to set aesthetic figure height
    golden_ratio = (5**.5 - 1) / 2

    # Figure width in inches
    fig_width_in = fig_width_pt * inches_per_pt
    # Figure height in inches
    fig_height_in = fig_width_in * golden_ratio * (subplots[0] / subplots[1])

    return fig_width_in, fig_height_in


class MyCorpus:
    """An iterator that yields sentences (lists of str)."""

    def __init__(self, text_list: list):
        self.text_list = text_list

    def __iter__(self):
        for line in self.text_list:
            yield line


def get_X_and_y_from_csv(
        filepath,
        drop_num_children=False,
        drop_num_siblings=True,
        drop_depth_from_def=True,
        drop_depth_from_root=True,
):
    df = pd.read_csv(filepath)
    # remove errors
    df = df[df.parent != "b"]
    df = df[df.type != "b"]
    df = df[df.parent != "ERROR"]
    df = df[df.type != "ERROR"]
    columns_to_onehot_encode = [
        "type",
        "parent"
    ]
    df = pd.get_dummies(df, columns=columns_to_onehot_encode)
    columns_to_drop = [
        "location",
        "contains_logging",
        "grandparent",
        "context",
        # "num_children",
        # "num_siblings",
        "num_cousins",
        # "depth_from_def",
        # "depth_from_root"
    ]
    if drop_num_children:
        columns_to_drop.append("num_children")
    if drop_num_siblings:
        columns_to_drop.append("num_siblings")
    if drop_depth_from_def:
        columns_to_drop.append("depth_from_def")
    if drop_depth_from_root:
        columns_to_drop.append("depth_from_root")

    X = df.drop(columns_to_drop, axis=1)
    y = df.contains_logging
    return X, y


def compute_scores_and_cm(
        X,
        y,
        score_names: list,
        verbose=True,
        n_splits=10,
        n_estimators=50,
        min_samples_split=5,
        min_samples_leaf=1,
        max_depth=None,
        pos_class_weight=4
):
    class_weight = {False: 1, True: pos_class_weight}
    # class_weight = "balanced"

    if verbose:
        print(f"Running {n_splits} folds: ", end="")

    all_scores = []
    conf_matrices = []
    skf = StratifiedShuffleSplit(n_splits=n_splits, test_size=0.25)
    for k_fold, (train_index, test_index) in enumerate(skf.split(X, y)):
        if verbose:
            print(f"{k_fold + 1} ", end="")
        classifier = RandomForestClassifier(
            n_estimators=n_estimators,
            n_jobs=-1,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            max_depth=max_depth,
            class_weight=class_weight
        )
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]
        classifier.fit(X_train, y_train)

        y_pred = classifier.predict(X_test)
        y_proba = classifier.predict_proba(X_test)

        scores = [
            balanced_accuracy_score(y_test, y_pred),
            precision_score(y_test, y_pred),
            recall_score(y_test, y_pred),
            f1_score(y_test, y_pred, average='binary', pos_label=True),
        ]
        if "AUROC" in score_names:
            scores.append(roc_auc_score(y_test, y_proba[:, 1]))

        all_scores.append(scores)
        cm = confusion_matrix(y_test, y_pred, labels=classifier.classes_)
        conf_matrices.append(cm)

    if verbose:
        print("Done")
    score_df = pd.DataFrame(all_scores, columns=score_names).mean().round(3)
    avg_cm = np.mean(conf_matrices, axis=0).astype(int)
    return score_df, avg_cm


def show_stats(df: pd.DataFrame):
    no_log_cnt, log_cnt = df['contains_logging'].value_counts()
    par_vec_cnt = no_log_cnt + log_cnt
    log_ratio = log_cnt / par_vec_cnt
    print("Shape:", str(df.shape))
    print(f"Number of parameter vecs:\t{par_vec_cnt}")
    print(f"without logging (negatives):\t{no_log_cnt}")
    print(f"with logging (positives):\t{log_cnt}")
    print(f"Log ratio:\t\t\t{log_ratio * 100:.2f}%")
    # Compute the logging ratio by node type
    positives = df[df["contains_logging"] == True]
    cols = ["type", "count", "positives", "ratio"]
    results = []
    for type_feature in df.columns:
        type_feature = str(type_feature)
        if not type_feature.startswith("type"):
            continue
        type_name = type_feature[5:]
        cnt = df[df[type_feature] == 1].shape[0]
        pos_cnt = positives[positives[type_feature] == 1].shape[0]
        ratio = pos_cnt / cnt
        results.append([type_name, cnt, pos_cnt, ratio])
    log_ratios_by_type_df = pd.DataFrame(results, columns=cols).sort_values(by="ratio", ascending=False)
    print(log_ratios_by_type_df)


def build_others_model(vocab_size, output_dims, embedding_matrix, max_length,
                       trainable, num_nodes, dropout, other_input_num_cols):
    """Build a tensorflow model using only the other features as input"""

    model = Sequential()
    model.add(keras.Input(shape=(other_input_num_cols,)))
    model.add(Dense(300, activation='relu'))
    model.add(Dense(1, activation='sigmoid'))

    return model


def build_hybrid_model(vocab_size, output_dims, embedding_matrix, max_length,
                       trainable, num_nodes, dropout, other_input_num_cols):
    """Build a tensorflow model using both the context and the other features as inputs"""

    context_input = keras.Input(shape=(max_length,), name="context")
    other_input = keras.Input(shape=(other_input_num_cols,), name="other")

    context_features = keras.layers.Embedding(vocab_size, output_dims, weights=[embedding_matrix], trainable=trainable)(
        context_input)  # input_length?
    context_features = keras.layers.LSTM(num_nodes, dropout=dropout)(context_features)

    # context_features = keras.layers.LSTM(128, return_sequences=True)(context_features) # dropout?
    # context_features = keras.layers.LSTM(128)(context_features)

    # context_features = keras.layers.CuDNNLSTM(128, return_sequences=True)(context_features) # dropout?
    # context_features = keras.layers.CuDNNLSTM(128)(context_features)
    # context_features = keras.layers.Dense(32)(context_features)

    other_features = keras.layers.Dense(300, activation='relu')(other_input)

    # other_features = keras.layers.Dense(300, activation='relu')(other_input)
    # other_features = keras.layers.Dense(100, activation='relu')(other_features)
    # other_features = keras.layers.Dense(32, activation='relu')(other_features)

    x = keras.layers.concatenate([context_features, other_features])

    logging_pred = keras.layers.Dense(1, name="logging", activation='sigmoid')(x)  # Sigmoid?

    model = keras.Model(
        inputs=[context_input, other_input],
        outputs=[logging_pred],
    )
    return model


def build_model(name, vocab_size, output_dims, embedding_matrix, max_length, trainable, num_nodes, dropout,
                return_sequences=True):
    model = Sequential()
    model.add(
        Embedding(vocab_size, output_dims, weights=[embedding_matrix], input_length=max_length, trainable=trainable))

    if name.startswith("A"):
        model.add(tf.keras.layers.LSTM(num_nodes, dropout=dropout, return_sequences=return_sequences))
        model.add(tf.keras.layers.LSTM(num_nodes, dropout=dropout))
    elif name.startswith("B"):
        model.add(tf.keras.layers.LSTM(num_nodes, dropout=dropout, return_sequences=return_sequences))
        model.add(tf.keras.layers.LSTM(num_nodes, dropout=dropout))
        model.add(Dense(int(num_nodes / 4), activation='relu'))
    elif name.startswith("C"):
        model.add(CuDNNLSTM(128, return_sequences=return_sequences))
        model.add(CuDNNLSTM(128))
    elif name.startswith("D"):
        model.add(CuDNNLSTM(num_nodes, return_sequences=return_sequences))
        model.add(CuDNNLSTM(num_nodes))
        model.add(Dense(32, activation='relu'))
    elif name.startswith("E"):
        model.add(Bidirectional(CuDNNLSTM(128, return_sequences=return_sequences)))
        model.add(Bidirectional(CuDNNLSTM(128)))
        model.add(Dense(32, activation='relu'))
    elif name.startswith("Y"):
        model.add(tf.keras.layers.LSTM(num_nodes, dropout=dropout))
        model.add(Dense(int(num_nodes / 4), activation='relu'))
    elif name.startswith("Z"):
        model.add(tf.keras.layers.LSTM(num_nodes, dropout=dropout))
        # Add a Dropout layer instead?
    else:
        raise RuntimeError

    model.add(Dense(1, activation='sigmoid'))

    return model


def build_callbacks(callback, callback_monitor, repo_name, run_folder, kfold, zhenhao=True, old=False):
    callbacks = []
    if "es" in callback:
        es = EarlyStopping(monitor=callback_monitor,
                           mode='max',
                           verbose=1,
                           patience=10,
                           restore_best_weights=True)
        callbacks.append(es)
    model_cp_filepath = ""
    if "cp" in callback:
        if zhenhao:
            # No more epoch in filepath for loading the model weights after fit
            # filepath = f"zhenhao_models/{repo_name}/{run_folder}/" + "epoch{epoch}"
            if old:
                model_cp_filepath = f"zhenhao_models/{repo_name}/{run_folder}/fold{kfold}"
            else:
                model_cp_filepath = f"my_zhenhao_models/{repo_name}/{run_folder}/fold{kfold}"
        else:
            model_cp_filepath = f"hybrid_models/{repo_name}/{run_folder}/fold{kfold}"
        cp = ModelCheckpoint(filepath=model_cp_filepath,
                             monitor=callback_monitor,
                             mode="max",
                             save_best_only=True,
                             save_weights_only=True,
                             save_freq="epoch")
        callbacks.append(cp)

    if callbacks == []:
        callbacks = None

    return callbacks, model_cp_filepath


def build_embedding_matrix(vocab_size, output_dims, gensim_model):
    embedding_matrix = zeros((vocab_size, output_dims))

    for i in range(vocab_size):
        embedding_vector = None
        try:
            embedding_vector = gensim_model.wv[str(i)]
        except KeyError:
            pass
        if embedding_vector is not None:
            embedding_matrix[i] = embedding_vector

    return embedding_matrix


if __name__ == '__main__':
    print("Hello World!")
