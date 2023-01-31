import pickle
import sys

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import recall_score, f1_score, precision_score, balanced_accuracy_score

from config import reindex

if len(sys.argv) != 2:
    print("Please supply a .csv file to learn on")
    exit(1)

# Importing the dataset
df = pd.read_csv(sys.argv[1])
# df = df.drop(["context"], axis=1)

# Convert the compacted context from letters into strings of integers
# Only required for neural net classifier
# df.context = [list(map(lambda y: str(ascii_letters.index(y)), list(str(x)))) for x in df.context]

X = df.drop(["contains_logging", "location", "context", "sibling_index"], axis=1)
X = pd.get_dummies(X, columns=["type", "parent"])
X = X.reindex(reindex, fill_value=0, axis="columns")
y = df.contains_logging

# Splitting the dataset into the Training set and Test set
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, stratify=y)

# Create random forest classifier and evaluate
classifier = RandomForestClassifier(n_estimators=50,
                                    n_jobs=-1,
                                    min_samples_split=5,
                                    class_weight={False: 1, True: 4}
)
classifier.fit(X_train, y_train)
y_pred = classifier.predict(X_test)
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
print(score_df)

# Save the classifier
pickle.dump(classifier, open('classifier', 'wb'))