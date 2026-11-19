"""Collect successful cloud verification output; never copy credentials/traces."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "test-results"


def main():
    logs = {name: (RESULTS / f"{name}.log").read_text() for name in ["unit", "backend", "build", "browser", "presentation-browser", "survey-browser"]}
    counts = {}
    for name in ["unit", "backend"]:
        match = re.search(r"Ran (\d+) tests in ([\d.]+)s\s+OK", logs[name])
        if not match:
            raise RuntimeError(f"No successful {name} result; evidence not published")
        counts[name] = {"tests": int(match[1]), "seconds": float(match[2]), "status": "passed"}
    if "built in" not in logs["build"]:
        raise RuntimeError("No successful production build")
    markers = {"browser": "Browser journey passed:", "presentation-browser": "Presentation checks passed:", "survey-browser": "Survey UI, reciprocal explanations"}
    summaries = {}
    for name, marker in markers.items():
        summaries[name] = next((line for line in logs[name].splitlines() if line.startswith(marker)), None)
        if summaries[name] is None:
            raise RuntimeError(f"No successful {name} result")
    destination = ROOT / "docs/screenshots"
    copies = {
        "survey-ui/dashboard-reciprocal.png": "survey-dashboard.png",
        "survey-ui/survey-profile.png": "survey-profile.png",
        "survey-ui/measured-method.png": "survey-method.png",
        "survey-ui/empty-profile-behavior.png": "survey-empty-profile.png",
        "survey-ui/method-mobile.png": "survey-method-mobile.png",
        **{name: name for name in ["dashboard-desktop.png", "dashboard-mobile.png", "project-team.png", "chat-desktop.png"]},
    }
    for source, target in copies.items():
        shutil.copyfile(RESULTS / source, destination / target)
    report = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "environment": "GitHub Codespaces; isolated disposable MongoDB database and Redis database 15",
        "checks": counts, "production_build": "passed", "browser_journeys": summaries,
        "model_sha256": hashlib.sha256((ROOT / "ml/models/survey-recommender.joblib").read_bytes()).hexdigest(),
        "screenshot_accounts": "Fictional UI fixtures; never training data",
    }
    path = ROOT / "docs/evidence/survey2024/verification.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    lines = ["# Verified application checks", "", f"Executed in GitHub Codespaces at {report['verified_at_utc']}.", "", f"Source revision at collection: `{report['source_commit']}`. Model SHA-256: `{report['model_sha256']}`.", "", "| Check | Outcome |", "|---|---|", *[f"| {name.title()} tests | {value['tests']} passed in {value['seconds']:.2f}s |" for name, value in counts.items()], "| React production build | Passed |", "| Full browser journeys | All three passed |", "", *[f"- {summary}" for summary in summaries.values()], "", "Checks use a separate disposable MongoDB database, Redis database 15 and ports 8001/5174. The existing presentation database is not reset. Browser screenshots use fictional fixtures; statistical evaluation uses the verified real survey. Passing application tests does not establish social-outcome prediction quality.", "", "Reproduce with `bash scripts/cloud-verify.sh`, then `.venv/bin/python scripts/collect-evidence.py`. See [testing instructions](TESTING.md)."]
    (ROOT / "docs/VERIFICATION.md").write_text("\n".join(lines) + "\n")
    print("Collected successful cloud checks and nine real browser screenshots.")


if __name__ == "__main__":
    main()
