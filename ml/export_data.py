"""Export the cleaned real-data cohort as inspectable CSV/Excel (ODbL 1.0).

This is a data export, not another training run. Raw bytes remain unchanged.
"""
import pandas as pd
from ml.download_survey import ROOT, FILES, checksum
from ml.survey import read_survey, PROFILE_FIELDS
from ml.train_survey import split_rows


def main():
    raw = ROOT / "dataset/raw/stackoverflow2024/results.csv"
    if checksum(raw) != FILES["results.csv"]:
        raise ValueError("Unverified original data")
    rows, audit, examples = read_survey(raw)
    partitions = split_rows(rows)
    split = {row["response_id"]: name for name, values in partitions.items() for row in values}
    frame = pd.DataFrame([{"response_id": r["response_id"], **{k: ";".join(r[k]) if isinstance(r[k], list) else r[k] for k in PROFILE_FIELDS}, "split": split[r["response_id"]]} for r in rows])
    destination = ROOT / "dataset/processed"
    destination.mkdir(exist_ok=True)
    frame.to_csv(destination / "survey2024_profiles.csv", index=False)
    with pd.ExcelWriter(destination / "survey2024_profiles.xlsx") as writer:
        frame.to_excel(writer, sheet_name="Cleaned real responses", index=False)
        pd.DataFrame([{"attribute": k, "missing_original": v} for k, v in audit["source_missing_counts"].items()]).to_excel(writer, sheet_name="Original missing counts", index=False)
        pd.DataFrame([{"source": "Stack Overflow Developer Survey 2024", "publisher": "Stack Exchange, Inc.", "license": "ODbL 1.0; contents DbCL 1.0", "url": "https://github.com/StackExchange/Survey", "raw_sha256": FILES["results.csv"], "notes": "Anonymous real responses. Not ConnectAI accounts. Inputs normalized; missing target responses excluded."}]).to_excel(writer, sheet_name="Attribution", index=False)
    print(f"Exported {len(frame)} verified real responses, without names or contact information.")


if __name__ == "__main__":
    main()
