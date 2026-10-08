"""Build data/processed/met_text_panel.csv from the MET Career Compass 2026 folder.

Source: the "jobs 2026" Google Drive folder shared for the course assignments (17 parquet files,
downloaded with gdown into data/MET_CareerCompass_2026/). The folder is too large for the repo,
so this script filters it with the same rules as our API panel and exports a small processed file.

Filter: NAICS 518 -> role-keyword titles -> one row per posting ID.
Skill and education flags are read from the posting text (BODY), because the SKILLS_NAME field in
this folder is truncated (about 3 skills per posting, alphabetical) and EDUCATION_LEVELS_NAME is a
modeled level that the posting does not state.

Usage: python build_met_text_panel.py [path/to/MET_CareerCompass_2026]
"""
import glob
import re
import sys

import pandas as pd

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else "data/MET_CareerCompass_2026"
OUT = "data/processed/met_text_panel.csv"

KEYWORDS = [
    "data scientist", "data engineer", "machine learning engineer", "ml engineer", "data analyst",
    "business analyst", "bi analyst", "business intelligence analyst", "analytics engineer",
    "applied scientist", "data architect", "database architect",
]

COLS = [
    "ID", "TITLE_CLEAN", "COMPANY_NAME", "STATE_NAME", "REMOTE_TYPE_NAME", "EMPLOYMENT_TYPE_NAME",
    "SALARY_FROM", "SALARY_TO", "ORIGINAL_PAY_PERIOD", "NAICS_2022_3", "NAICS_2022_6", "POSTED", "BODY",
]

# skill name -> regex searched in the posting text (case-insensitive)
SKILLS = {
    "Python": r"\bpython\b",
    "SQL": r"\bsql\b|structured query",
    "Machine Learning": r"machine learning|\bml\b",
    "Cloud/AWS": r"\baws\b|amazon web services|azure|google cloud|\bgcp\b|cloud computing",
    "Data Visualization": r"data visuali|tableau|power ?bi|looker|qlik",
    "Statistics": r"statistic",
    "Tableau": r"tableau",
    "Power BI": r"power ?bi",
    "Excel": r"\bexcel\b",
    "Spark": r"\bspark\b|pyspark",
    "Snowflake": r"snowflake",
    "ETL": r"\betl\b|\belt\b|data pipeline",
    "Communication": r"communicat",
    "Dashboards": r"dashboard",
    "Java": r"\bjava\b",
    "Data Modeling": r"data model",
    "Deep Learning": r"deep learning|neural network|\bllm\b|generative ai",
}

# degree level -> regex
LEVELS = {
    "Associate": r"associate.?s? degree|associate of",
    "Bachelor": r"bachelor|\bb\.?[sa]\.?(?= (?:or|and|/|degree|in)\b)|undergraduate degree",
    "Master": r"master.?s|\bm\.?s\.?(?= (?:or|and|/|degree|in)\b)|\bmba\b|graduate degree",
    "PhD": r"ph\.? ?d|doctorate|doctoral",
}
PREFERRED = r"prefer|a plus|nice to have|desired|desirable|bonus|ideal"
REQUIRED = r"require|minimum|must|mandatory|necessary"


def classify_role(title):
    t = str(title).lower()
    if re.search(r"machine learning engineer|ml engineer", t):
        return "ML Engineer"
    if re.search(r"data scientist|applied scientist", t):
        return "Data Scientist"
    if re.search(r"data engineer|analytics engineer|data architect|database architect", t):
        return "Data / Analytics Engineer"
    if re.search(r"data analyst|business analyst|bi analyst|business intelligence analyst", t):
        return "Data Analyst"
    return "Other"


def degree_wording(body, pattern):
    """Strict wording, best across the sentences that name the level:
    'required' only if the sentence says require/minimum/must/mandatory and has no preference word;
    'preferred' if it says prefer/a plus/etc.; 'mentioned' if the level is named with neither; else 'none'."""
    sentences = re.split(r"(?<=[.;!?])\s+|\n+|\s[-•*]\s", body)
    found = "none"
    for s in sentences:
        if not re.search(pattern, s, re.I):
            continue
        if re.search(PREFERRED, s, re.I):
            wording = "preferred"
        elif re.search(REQUIRED, s, re.I):
            wording = "required"
        else:
            wording = "mentioned"
        rank = {"none": 0, "mentioned": 1, "preferred": 2, "required": 3}
        if rank[wording] > rank[found]:
            found = wording
    return found


frames = [pd.read_parquet(f, columns=COLS) for f in sorted(glob.glob(f"{DATA_DIR}/*.parquet"))]
df = pd.concat(frames, ignore_index=True)
print("rows in folder:", len(df))

df = df[df["NAICS_2022_3"].astype(str) == "518"]
print("after NAICS 518:", len(df))
title = df["TITLE_CLEAN"].fillna("").str.lower()
df = df[title.apply(lambda t: any(k in t for k in KEYWORDS))]
print("after role keywords:", len(df))
df = df.drop_duplicates(subset="ID").copy()
print("after dedupe:", len(df))

for c in ["SALARY_FROM", "SALARY_TO"]:
    df[c] = pd.to_numeric(df[c].replace("", None), errors="coerce")
# 0 means not disclosed. Most hourly postings are already stored as an annual figure (rate x 2080),
# but a few keep the raw hourly rate; values under 1,000 are treated as hourly and converted.
for c in ["SALARY_FROM", "SALARY_TO"]:
    df.loc[df[c] <= 0, c] = float("nan")
raw_hourly = df["SALARY_TO"] < 1000
for c in ["SALARY_FROM", "SALARY_TO"]:
    df.loc[raw_hourly, c] = df.loc[raw_hourly, c] * 2080
df["role"] = df["TITLE_CLEAN"].apply(classify_role)

body = df["BODY"].fillna("")
has_text = body.str.strip().str.len() > 0
out = pd.DataFrame({
    "job_id": df["ID"],
    "title": df["TITLE_CLEAN"],
    "role": df["role"],
    "company_name": df["COMPANY_NAME"],
    "state": df["STATE_NAME"],
    "remote_status": df["REMOTE_TYPE_NAME"],
    "employment_type": df["EMPLOYMENT_TYPE_NAME"],
    "salary_min_annual": df["SALARY_FROM"],
    "salary_max_annual": df["SALARY_TO"],
    "posted_at": df["POSTED"],
    "has_text": has_text,
})
for name, pat in SKILLS.items():
    out["skill_" + name] = [bool(re.search(pat, b, re.I)) if t else pd.NA for b, t in zip(body, has_text)]
for name, pat in LEVELS.items():
    out["degree_" + name] = [degree_wording(b, pat) if t else pd.NA for b, t in zip(body, has_text)]

out.to_csv(OUT, index=False)
print("saved", OUT, "| rows:", len(out), "| rows with posting text:", int(has_text.sum()))
