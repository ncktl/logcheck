import sys
import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier
from logcheck.config import reindex

if len(sys.argv) != 2:
    print("Please supply a .csv file to learn on")
    exit(1)

# Importing the dataset
df = pd.read_csv(sys.argv[1])
# df = df.drop(["context"], axis=1)

# Convert the compacted context from letters into strings of integers
# df.context = [list(map(lambda y: str(ascii_letters.index(y)), list(str(x)))) for x in df.context]

X = df.drop(["contains_logging", "location"], axis=1) #Todo Change back
X = pd.get_dummies(X, columns=["type", "parent"])
X = X.reindex(reindex, fill_value=0, axis="columns")
y = df.contains_logging

# Splitting the dataset into the Training set and Test set
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)

# classifier = LinearSVC(C=0.025)
# classifier = LinearSVC(C=1)
# classifier = KNeighborsClassifier(3)
# classifier = KNeighborsClassifier(8)
classifier = RandomForestClassifier(n_estimators=100, verbose= 2)
# classifier.fit(X_train, y_train)
classifier.fit(X, y)

pickle.dump(classifier, open('../models/classifier', 'wb'))