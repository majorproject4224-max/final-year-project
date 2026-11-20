"""Render figures only from measured experiment outputs; no hand-entered scores."""
import json
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ml.download_survey import ROOT
from ml.survey import tags, years, clean_profile

OUT = ROOT / "docs" / "evidence" / "survey2024"
BLUE, GREEN, RED = "#4f46e5", "#15803d", "#dc2626"


def finish(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def table_figure(title, columns, rows, name, highlight=None):
    width = max(14, 100 // len(columns))
    wrapped = [[textwrap.fill(str(value), width=width, break_long_words=True) for value in row] for row in rows]
    heights = [1] + [max(value.count("\n") + 1 for value in row) for row in wrapped]
    fig, ax = plt.subplots(figsize=(13, max(3.5, sum(heights) * 0.4 + 1.8)))
    ax.axis("off")
    ax.set_title(title, fontsize=16, loc="left", pad=22, weight="bold")
    table = ax.table(cellText=wrapped, colLabels=columns, loc="center", cellLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for (r, c), cell in table.get_celld().items():
        cell.set_height(0.85 * heights[r] / sum(heights))
        cell.set_edgecolor("#e2e8f0")
        if r == 0:
            cell.set_facecolor(BLUE)
            cell.set_text_props(color="white", weight="bold")
        elif highlight is not None and r == highlight + 1:
            cell.set_facecolor("#dcfce7")
            cell.set_text_props(weight="bold")
    finish(fig, name)


def generate_report(report, examples):
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False, "font.size": 11})
    split = report["splits"]
    total = sum(part["rows"] for part in split.values())
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.axis("off")
    ax.text(0.5, 0.96, "70:30 data split — website accounts are separate", ha="center", fontsize=18, weight="bold")
    ax.text(0.5, 0.78, f"{total:,} eligible real survey responses", ha="center", fontsize=14)
    for x_pos, name, color, explanation in [(0.25, "train", BLUE, "Learn patterns and choose settings"), (0.75, "test", GREEN, "Final exam after settings are locked")]:
        count = split[name]["rows"]
        ax.text(x_pos, 0.52, f"{name.upper()}: {count:,} ({count / total:.2%})", ha="center", fontsize=15, color=color, weight="bold")
        ax.text(x_pos, 0.38, explanation, ha="center", fontsize=11)
    ax.text(0.5, 0.16, "5 website profiles + new registrations → saved models → recommendations", ha="center", fontsize=12, bbox=dict(facecolor="#eef2ff", edgecolor="none", pad=12))
    ax.text(0.5, 0.01, "No website account is used to train, tune or test. Identical survey inputs stay in the same group.", ha="center", fontsize=10)
    finish(fig, "00-data-separation")
    audit = report["audit"]
    fields = list(audit["source_missing_counts"])
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.barh(fields, [audit["source_missing_counts"][f] for f in fields], color=BLUE)
    ax.set(xlabel="Unanswered cells in the unchanged original file", title=f"Real missing data — {audit['raw_rows']:,} survey responses")
    for i, field in enumerate(fields):
        ax.text(audit["source_missing_counts"][field] + 100, i, str(audit["source_missing_counts"][field]), va="center", fontsize=9)
    finish(fig, "01-original-missing-values")

    median = report["preprocessing"]["numeric_train_median"]
    rows = []
    for e in examples[:4]:
        for column, key in [("LanguageHaveWorkedWith", "languages"), ("YearsCode", "years_code")]:
            raw, cleaned = e["raw"][column], e["cleaned"][key]
            rows.append([e["raw"]["ResponseId"], column, textwrap.shorten(str(raw), width=48), textwrap.shorten(str(cleaned), width=48)])
    table_figure("Actual original rows → normalized values (None remains unknown)", ["Response ID", "Source field", "Original", "Cleaned"], rows, "02-preprocessing-examples")
    pd.DataFrame([{"response_id": e["raw"]["ResponseId"], "raw": json.dumps(e["raw"]), "cleaned": json.dumps(e["cleaned"]), "target_observed": e["target_observed"]} for e in examples]).to_excel(OUT / "preprocessing_examples.xlsx", index=False)

    clusters = report["clustering"]
    trials = clusters["candidates"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, key, title in zip(axes, ["validation_silhouette", "train_inertia"], ["Validation silhouette (higher is better)", "Training inertia / elbow (lower is better)"]):
        ax.plot([r["k"] for r in trials], [r[key] for r in trials], "o-", color=BLUE)
        ax.axvline(clusters["selected_k"], color=GREEN, linestyle="--", label=f"Selected k={clusters['selected_k']}")
        ax.set(xlabel="Number of clusters", title=title)
        ax.legend()
    finish(fig, "03-cluster-selection")

    selected = report["selected_parameters"]
    rows, highlight = [], None
    for i, r in enumerate(report["parameter_search"]):
        p = r["parameters"]
        chosen = all(p[k] == selected[k] for k in p)
        if chosen:
            highlight = i
        rows.append([str(p["n_estimators"]), str(p["max_depth"]), str(p["min_samples_leaf"]), f"{r['validation']['f1_micro']:.4f}", f"{r['validation']['threshold']:.2f}", f"{r['fit_and_validation_seconds']:.1f}", "SELECTED" if chosen else ""])
    table_figure("Settings comparison inside the 70% training data — green row selected", ["Trees", "Max depth", "Min leaf", "Micro F1", "Threshold", "Seconds", "Decision"], rows, "04-parameter-selection", highlight)
    curve = report["learning_curve"]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot([r["train_rows"] for r in curve], [r["train_f1"] for r in curve], "o-", label="Training", color=BLUE)
    ax.plot([r["train_rows"] for r in curve], [r["validation_f1"] for r in curve], "o-", label="Validation", color=GREEN)
    ax.set(xlabel="Training respondents", ylabel="F1 balance score (higher is better)", title="Does more training data help? (internal validation only)", ylim=(0, 1))
    ax.legend()
    finish(fig, "05-learning-curve")

    test = report["test"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    matrix = np.array(test["confusion_matrix"])
    axes[0].imshow(matrix, cmap="Blues")
    for i in range(2):
        for j in range(2):
            axes[0].text(j, i, f"{matrix[i,j]:,}", ha="center", va="center", color="white" if matrix[i,j] > matrix.max() / 2 else "black", fontsize=16)
    axes[0].set(xticks=[0, 1], yticks=[0, 1], xticklabels=["Not selected", "Selected"], yticklabels=["Not selected", "Selected"], xlabel="Predicted language preference", ylabel="Actual response", title="Held-out confusion matrix (all labels)")
    axes[1].bar(["Correct", "Wrong"], [test["correct"], test["wrong"]], color=[GREEN, RED])
    axes[1].set(ylabel="Respondent × language decisions", title=f"Accuracy {test['per_label_accuracy']:.1%}; RMSE {test['probability_rmse']:.4f}")
    finish(fig, "06-test-correct-wrong")
    methods = {"Random Forest": test, "Prevalence": report["baselines"]["training_prevalence"], "Continue current": report["baselines"]["continue_current_languages"]}
    table_figure("Untouched test set — honest comparison with simple baselines", ["Method", "Accuracy", "Precision", "Recall", "Micro F1", "MSE", "RMSE"], [[name, *[f"{m[k]:.4f}" for k in ["per_label_accuracy", "precision_micro", "recall_micro", "f1_micro", "probability_mse", "probability_rmse"]]] for name, m in methods.items()], "07-baselines")

    rows = []
    for r in report["artificial_masking_stress_test"]:
        m = r["metrics_supported_only"]
        rows.append([f"{r['artificial_field_mask_rate']:.0%}", str(r["supported_rows"]), str(r["abstained_rows"]), f"{r['coverage']:.1%}", f"{m['f1_micro']:.4f}" if m else "No prediction"])
    table_figure("Artificial masking stress test — original dataset is not modified", ["Fields hidden", "Supported", "Abstained", "Coverage", "F1 on supported"], rows, "08-missing-field-stress")
    irregular = [
        {"input": '" JS ; javascript ; Python "', "output": tags(" JS ; javascript ; Python "), "reason": "Aliases, whitespace and duplicates"},
        {"input": "null technology list", "output": tags(None), "reason": "Unknown; no fabricated skills"},
        {"input": "Less than 1 year", "output": years("Less than 1 year"), "reason": "Documented boundary encoding"},
        {"input": "More than 50 years", "output": years("More than 50 years"), "reason": "Documented boundary encoding"},
        {"input": '"many" / -3 / infinity', "output": [years("many"), years(-3), years(float("inf"))], "reason": "Invalid numeric → missing"},
        {"input": "Empty profile", "output": clean_profile({}), "reason": "Serving abstains; asks for technologies"},
    ]
    (OUT / "irregular_input_checks.json").write_text(json.dumps(irregular, indent=2), encoding="utf-8")
    table_figure("Executed parser examples — deliberately constructed checks, not source records", ["Input", "Actual normalized output", "Handling"], [[r["input"], textwrap.shorten(str(r["output"]), width=65), r["reason"]] for r in irregular], "09-irregular-input-checks")
    table_figure("Original missingness — separate from artificially masked test", ["Test group", "Respondents", "Micro F1", "RMSE"], [[r["group"], str(r["rows"]), f"{r['metrics']['f1_micro']:.4f}" if r["metrics"] else "N/A", f"{r['metrics']['probability_rmse']:.4f}" if r["metrics"] else "N/A"] for r in report["natural_missingness_evaluation"]], "10-natural-missingness")

    lines = ["# Measured real-data results", "", f"Generated by the experiment at {report['metadata']['trained_at_utc']}. Run: **{report['metadata']['run_kind']}**.", "", "Task: predict stated future language preferences from current technologies and coding years. These are not friendship-success results.", ""]
    lines += [
        "## How these results relate to the website", "",
        "| Feature | Information used | How it works |",
        "|---|---|---|",
        "| People recommendations | Technologies used, coding experience and your wanted languages | K-Means + Random Forest + profile comparisons |",
        "| Activity suggestions | Community interests, city and location preference | Direct interest matching and sorting; no trained ML model |", "",
        "For people recommendations, K-Means helps find candidate profiles. Random Forest predicts language preferences from current technologies and coding years. Profile comparisons combine shared technologies, matches to your stated wanted languages and learned preferences into a discovery score. A candidate's wanted languages do not affect their score or selection in your suggestions. Your wanted languages are used in comparisons, not as Random Forest input.", "",
        "**Read the numbers this way:**", "",
        "- **Random Forest:** accuracy, precision, recall, F1, MSE and RMSE measure wanted-language predictions on held-out survey responses.",
        "- **K-Means:** silhouette and inertia describe technology groups; they do not measure successful connections.",
        "- **Website discovery score:** a ranking score from profile comparisons and learned preferences, not model accuracy or a probability of friendship success.",
        "- **Activities:** explanations show matching interests and location preferences. No trained-model result is claimed for activities.", "",
        "Project and teammate suggestions continue to use project requirement coverage. Project creation, applications, teams, connections and messaging remain separate application features. See the [people scoring formula](ML_METHODOLOGY.md#live-people-discovery-and-explanations) and [verified application checks](VERIFICATION.md).", "",
        "## Dataset used for the measured experiment", "",
        f"Original rows: **{audit['raw_rows']:,}**. Eligible: **{audit['eligible_rows']:,}**. Training median coding years: **{median:g}**.", "",
        "| Split | Respondents | Unique input groups |", "|---|---:|---:|",
    ]
    lines += [f"| {name} | {r['rows']:,} | {r['unique_groups']:,} |" for name, r in report["splits"].items()]
    lines += ["", "## 70:30 training and testing, in simple terms", "", "Training is the study material; testing is the final exam. Registered website profiles (including the five presentation accounts) are outside both datasets.", "", f"Inside the training portion, {report['validation_setup']['fit_rows']:,} rows fit candidate models and {report['validation_setup']['validation_rows']:,} rows compare settings. After selecting settings, the encoder, K-Means and Random Forest are fitted again on all {split['train']['rows']:,} training rows. The {split['test']['rows']:,} test rows are not used to choose settings.", "", "The 70:30 ratio applies to groups of identical normalized inputs. Row percentages are very close to 70:30 because group sizes differ.", ""]
    lines += ["", "Group overlap: **0**. Exact normalized input profiles stay in one partition.", "", "| Model | Accuracy per label | Precision | Recall | Micro F1 | MSE | RMSE |", "|---|---:|---:|---:|---:|---:|---:|"]
    lines += [f"| {name} | " + " | ".join(f"{m[k]:.4f}" for k in ["per_label_accuracy", "precision_micro", "recall_micro", "f1_micro", "probability_mse", "probability_rmse"]) + " |" for name, m in methods.items()]
    lines += ["", f"Correct: **{test['correct']:,}**; wrong: **{test['wrong']:,}**. One decision means one held-out respondent and one target language. Exact whole-profile accuracy: **{test['exact_profile_accuracy']:.4f}**.", "", "MSE averages (predicted probability − actual 0/1 response)². RMSE is its square root. Lower is better. Accuracy includes many negative labels; always read F1, recall and the baselines too.", "", "Selected parameters: `" + json.dumps(selected, sort_keys=True) + "`.", "", f"K-Means selected **k={clusters['selected_k']}** by validation silhouette. Held-out silhouette: **{clusters['test_silhouette']}**.", ""]
    lines += ["## How to read the figures", "", "- **Data separation:** survey training/testing and live website users are different data flows.", "- **Missing values:** longer bars mean more unanswered cells in the original survey.", "- **Before/after:** the same response ID shows what cleaning changed.", "- **Cluster selection:** higher silhouette means more separated groups; near zero means overlap. Inertia shows within-group spread.", "- **Settings:** the green row has the best internal-validation F1 among the tried settings. More trees/depth do not automatically mean a better result.", "- **Learning curve:** left-to-right means more fitting rows. Green shows performance on internal validation; blue shows the rows used for fitting. This is not training by epochs.", "- **Correct/wrong:** green bar counts correct language decisions; red counts mistakes. The matrix separates missed interests from wrongly suggested interests.", "- **Baselines:** compare against simple alternatives on the same test respondents. Higher F1 and lower MSE/RMSE are better.", "- **Hidden fields:** deliberately remove answers to check reliability. Abstained means the system requested more input instead of guessing.", "- **Parser checks:** intentionally constructed irregular inputs; they are not claimed to be original dataset rows.", "- **Natural missingness:** evaluates real incomplete source records, separately from deliberately hidden inputs.", ""]
    lines += [f"![{p.stem.replace('-', ' ')}](evidence/survey2024/{p.name})\n" for p in sorted(OUT.glob("*.png"))]
    lines += ["## What these results measure", "", *["- " + text for text in report["limitations"]], "", "Source: [Stack Overflow Developer Survey 2024](https://survey.stackoverflow.co/2024/methodology), © Stack Exchange, Inc. Data/derived tables: [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), contents DbCL 1.0."]
    (ROOT / "docs" / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
