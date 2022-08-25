import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from matplotlib.pyplot import figure
from sklearn.svm import LinearSVC
from sklearn import svm

sort_features = False

def f_importances(coef, names, title, sort_features=True, supertitle=""):
    imp = coef
    # print(dict(zip(imp, names)))
    if sort_features:
        imp, names = zip(*sorted(zip(imp, names)))
    fig, ax = plt.subplots()
    ax.barh(range(len(names)), imp, align='center')
    ax.set_title(title)
    plt.yticks(range(len(names)), names)
    fig.set_size_inches(18.5, 18.5)
    fig.suptitle(supertitle)
    fig.show()

features = [
    "combination",
    # "combination_full_all_files",
    "combination_without_web2py",
    # "combination_without_web2py_all_files"
]
for feature in features:
    print("-" * 30)
    print(feature)
    # Importing the dataset
    # Assumption: Onehot encoding
    df = pd.read_csv("~/logcheck/features/" + feature + ".csv")
    # X = df.drop(["line", "contains_logging"], axis=1)
    X = df.drop(["line", "contains_logging", "contains_call"], axis=1)
    X = pd.get_dummies(X, columns=["type", "parent"])
    y = df.contains_logging
    # Splitting the dataset into the Training set and Test set
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.25, random_state = 0)

    for clf, rndfor in zip(
            [LinearSVC(C=0.025, random_state=0), RandomForestClassifier(n_estimators=9, random_state=0)],
            [False, True]):
        clf.fit(X_train, y_train)
        if rndfor:
            print("Random Forest")
            f_importances(clf.feature_importances_, list(X.columns), "Random Forest", sort_features, feature)
        else:
            print("Linear SVC")
            f_importances(abs(clf.coef_[0]), list(X.columns), "Linear SVC", sort_features, feature)
        print(accuracy_score(clf.predict(X_test), y_test))