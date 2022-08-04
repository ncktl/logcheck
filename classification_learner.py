import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC
import pickle

# Importing the dataset
df = pd.read_csv('features/viewfinder.bool2.csv')
# Assumption: Bool encoding
X = df.drop(["line", "contains_logging"], axis=1)
y = df.contains_logging

# Splitting the dataset into the Training set and Test set
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)

classifier = LinearSVC(C=1)
# classifier.fit(X_train, y_train)
classifier.fit(X, y)

pickle.dump(classifier, open('classifier', 'wb'))