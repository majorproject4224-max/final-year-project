"""Load the saved model and predict one compatible student pair."""
from pathlib import Path
import joblib
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
bundle=joblib.load(ROOT/"ml/models/random_forest_compatibility.joblib")
df=pd.read_excel(ROOT/"dataset/matching_data.xlsx")
features=bundle["features"]
pair=df[df.compatibility_label==1].iloc[0]
probability=bundle["model"].predict_proba(pd.DataFrame([pair[features].to_dict()]))[0,1]
label=int(probability>=0.5)
print("MODEL RELOAD: PASS")
print("Student pair:",pair.user1_id,"and",pair.user2_id)
print("Matched feature values:",pair[features].to_dict())
print(f"Compatibility probability: {probability:.2%}")
print("Recommendation:", "Compatible" if label else "Not compatible")
