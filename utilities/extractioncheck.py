import pandas as pd
import sys

extractions = ["horizon", "hydra", "k8s", "pyres", "viewfinder", "web2py"]
# extractions = ["horizon", "hydra", "k8s", "pyres", "viewfinder"]
all_files = [extract + "_all_files" for extract in extractions]

for filelist, desc in zip([extractions, all_files], ["Only files that import logging", "All files"]):
    print("_" * 70)
    print("_" * 70)
    print(desc)
    total_parvec = 0
    parvec_list = []
    total_loggings = 0
    loggings_list = []

    for extraction in filelist:
        # print(extraction)
        path = "/Users/nickkeutel/logcheck/features/" + extraction + ".csv"
        dataset = pd.read_csv(path)

        parvecnum = dataset.shape[0] - 1
        total_parvec += parvecnum
        parvec_list.append(parvecnum)
        # print("Param vecs:", parvecnum)

        loggings = dataset[dataset.contains_logging == 1].shape[0]
        total_loggings += loggings
        loggings_list.append(loggings)
        # print("Loggings:", loggings)

        # percentage = loggings / parvecnum
        # print("Percentage:", percentage)

        # print(dataset.contains_logging.value_counts())
        # print(sys.argv)
        if len(sys.argv) > 1:
            df = pd.get_dummies(dataset.drop(['line'], axis=1), columns=["type", "parent"])
            # print("DTypes:", df.dtypes)
            print("Sums:")
            for col in df.columns:
                print(df[df[col] == True].shape[0], col)
            print("")
            print("Positives:")
            positives = df[df["contains_logging"] == True]
            for col in df.columns:
                print(positives[positives[col] == True].shape[0], col)
            print("-" * 70)

    precision = 4
    print("Total param vecs:", total_parvec)
    print("Total loggings:", total_loggings)
    print("Percentage:", round(total_loggings / total_parvec, precision))
    for extraction, parvecnum, loggings in zip(filelist, parvec_list, loggings_list):
        print("-" * 70)
        print(extraction)
        percentage = loggings / parvecnum
        parvec_percentage = parvecnum / total_parvec
        loggings_percentage = loggings / total_loggings

        print("Param vecs:", parvecnum, "\t Loggings:", loggings,
              "\t Percentage:", round(percentage, precision))
        print("Param vecs share:", round(parvec_percentage, precision),
              "\t Logging share:", round(loggings_percentage, precision))