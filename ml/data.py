"""Excel/CSV loading with explicit schema and relationship validation."""

from pathlib import Path
import pandas as pd
from .features import normalize_items, normalize_text

STUDENT_COLUMNS = {
    "user_id",
    "academic_year",
    "branch",
    "skills",
    "interests",
    "domain",
    "experience",
    "preferred_project_type",
    "availability_hours",
}
PROJECT_COLUMNS = {
    "project_id",
    "domain",
    "required_skills",
    "required_interests",
    "required_experience",
    "project_type",
    "expected_hours",
    "team_size",
}


def load_table(path, required):
    path = Path(path)
    if path.suffix == ".xlsx":
        frame = pd.read_excel(path, engine="openpyxl")
    elif path.suffix == ".csv":
        frame = pd.read_csv(path)
    else:
        raise ValueError("Use an .xlsx or .csv dataset.")
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
    if frame.empty:
        raise ValueError(f"{path.name}: dataset is empty")
    return frame


def require_unique(frame, column):
    if (
        frame[column].isna().any()
        or frame[column].astype(str).str.strip().eq("").any()
        or frame[column].duplicated().any()
    ):
        raise ValueError(f"{column} must be present and unique.")


def numeric(frame, column, lower, upper, default=None):
    values = pd.to_numeric(frame[column], errors="coerce")
    if default is not None:
        values = values.fillna(default)
    if values.isna().any() or ((values < lower) | (values > upper)).any():
        raise ValueError(f"{column} must be numeric between {lower} and {upper}.")
    frame[column] = values


def clean_profiles(frame, project=False):
    frame = frame.copy()
    identifier = "project_id" if project else "user_id"
    require_unique(frame, identifier)
    for column in ["required_skills", "required_interests"] if project else ["skills", "interests"]:
        frame[column] = frame[column].map(normalize_items)
    skill_column = "required_skills" if project else "skills"
    if frame[skill_column].map(len).eq(0).any():
        raise ValueError(f"Every row needs at least one {skill_column} item.")
    experience_column = "required_experience" if project else "experience"
    if not frame[experience_column].isin(["Beginner", "Intermediate", "Advanced"]).all():
        raise ValueError(f"Invalid {experience_column} value.")
    for column in (
        ["domain", "project_type"] if project else ["domain", "preferred_project_type", "branch"]
    ):
        if frame[column].map(normalize_text).eq("").any():
            raise ValueError(f"{column} cannot be blank.")
    numeric(frame, "expected_hours" if project else "availability_hours", 1, 40)
    if project:
        numeric(frame, "team_size", 2, 10)
    else:
        numeric(frame, "academic_year", 1, 4)
    return frame.where(pd.notna(frame), None).to_dict("records")


def validate_pairs(frame, students, projects=None):
    frame = frame.copy()
    left, right = ("user_id", "project_id") if projects is not None else ("user1_id", "user2_id")
    if (
        not frame[left].isin(students).all()
        or not frame[right].isin(projects if projects is not None else students).all()
    ):
        raise ValueError("Pair references an unknown student or project.")
    keys = frame.apply(
        lambda row: (
            (str(row[left]), str(row[right]))
            if projects is not None
            else tuple(sorted([str(row[left]), str(row[right])]))
        ),
        axis=1,
    )
    if keys.duplicated().any():
        raise ValueError("Duplicate pairs, including reversed student pairs, are not allowed.")
    if projects is None and frame[left].eq(frame[right]).any():
        raise ValueError("A student cannot be matched with themself.")
    if not frame.compatibility_label.isin([0, 1]).all():
        raise ValueError("Compatibility labels must be 0 or 1.")
    if frame.label_source.isna().any() or frame.label_source.astype(str).str.strip().eq("").any():
        raise ValueError("Every label needs a source.")
    return frame
