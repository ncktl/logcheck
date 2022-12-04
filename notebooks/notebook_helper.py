# Helper functions for the notebooks

import pandas as pd
# Tensorflow + Keras
from keras.layers import CuDNNLSTM
import tensorflow as tf
import tensorflow.keras as keras
from tensorflow.keras.layers import Dense, LSTM, Embedding, Bidirectional
from tensorflow.keras.models import Sequential
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

from numpy import zeros

iteration_features = "Name, Timestamp, sampling_strategy, max_length, vocab_size, batch_size, trainable," \
                     " dropout, val_split, callback, callback_monitor, num_nodes, num_epochs, class_weight," \
                     " cmpltn_metrics, run_folder, execution_time"


class MyCorpus:
    """An iterator that yields sentences (lists of str)."""

    def __init__(self, text_list: list):
        self.text_list = text_list

    def __iter__(self):
        for line in self.text_list:
            yield line


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
