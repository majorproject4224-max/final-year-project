"""Train a connecT AI student-compatibility model from Excel data."""
from pathlib import Path
import json
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"dataset/matching_data.xlsx"
MODEL=ROOT/"ml/models/random_forest_compatibility.joblib"
METRICS=ROOT/"ml/evaluation/random_forest_metrics.json"
FEATURES=["skill_similarity","interest_similarity","domain_similarity","experience_compatibility","previous_collaboration","project_similarity"]
TARGET="compatibility_label"

def main():
    df=pd.read_excel(DATA)
    missing=set(FEATURES+[TARGET])-set(df.columns)
    if missing: raise ValueError(f"Missing required columns: {sorted(missing)}")
    user_ids = pd.unique(df[["user1_id", "user2_id"]].values.ravel())
    train_users, test_users = train_test_split(user_ids, test_size=.20, random_state=42)
    train_user_set, test_user_set = set(train_users), set(test_users)
    train_mask = df.user1_id.isin(train_user_set) & df.user2_id.isin(train_user_set)
    test_mask = df.user1_id.isin(test_user_set) & df.user2_id.isin(test_user_set)
    train_df, test_df = df[train_mask], df[test_mask]
    x_train, y_train = train_df[FEATURES].copy(), train_df[TARGET].copy()
    x_test, y_test = test_df[FEATURES].copy(), test_df[TARGET].copy()
    if len(x_train) == 0 or len(x_test) == 0 or y_train.nunique() < 2:
        raise ValueError("A user-disjoint split needs train/test pairs and both training labels.")
    model=RandomForestClassifier(n_estimators=300,max_depth=8,min_samples_leaf=3,class_weight="balanced",random_state=42)
    model.fit(x_train,y_train)
    predicted=model.predict(x_test)
    probability=model.predict_proba(x_test)[:,1]
    report = classification_report(y_test, predicted, labels=[0, 1], output_dict=True, zero_division=0)
    metrics={
        "dataset_rows":int(len(df)),
        "training_rows":int(len(x_train)),
        "test_rows":int(len(x_test)),
        "training_users":int(len(train_user_set)),
        "test_users":int(len(test_user_set)),
        "cross_partition_pairs_excluded":int(len(df) - len(x_train) - len(x_test)),
        "split_strategy":"80/20 user-disjoint holdout; each pair is retained only if both users belong to one partition",
        "test_labels":{str(int(label)):int(count) for label,count in y_test.value_counts().sort_index().items()},
        "features":FEATURES,
        "accuracy":round(float(accuracy_score(y_test,predicted)),4),
        "compatible_f1":round(float(report["1"]["f1-score"]),4),
        "confusion_matrix_labels":["Not compatible (0)","Compatible (1)"],
        "confusion_matrix":confusion_matrix(y_test,predicted,labels=[0,1]).tolist(),
        "classification_report":report,
        "feature_importance":dict(sorted(zip(FEATURES,map(float,model.feature_importances_)),key=lambda i:i[1],reverse=True)),
        "evaluation_warning":"Small synthetic held-out set; estimates reproduce rule-generated labels and are not real-student performance.",
    }
    MODEL.parent.mkdir(parents=True,exist_ok=True); METRICS.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump({"model":model,"features":FEATURES},MODEL)
    METRICS.write_text(json.dumps(metrics,indent=2),encoding="utf-8")
    sample=x_test.iloc[0]
    print("RESULTS")
    print(f"Test accuracy: {metrics['accuracy']:.2%}")
    print(f"User-disjoint compatible F1: {metrics['compatible_f1']:.2%} on {metrics['test_rows']} pairs / {metrics['test_users']} unseen users")
    print("Confusion matrix [actual rows 0,1; predicted columns 0,1]:",metrics["confusion_matrix"])
    print("Sample pair:",df.loc[sample.name,["user1_id","user2_id"]].to_dict())
    print("Predicted compatibility probability:",f"{probability[0]:.2%}")
    print("Predicted label:",int(predicted[0]),"| Actual label:",int(y_test.iloc[0]))
    print("Saved model:",MODEL)
    print("Saved metrics:",METRICS)
if __name__=="__main__": main()
