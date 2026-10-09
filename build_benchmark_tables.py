"""Build the small summary tables behind the Benchmark Analysis page from the course Jobs_2026 folder.

Source: the same approved folder as the rest of the project (20 parquet files, 815,193 postings):
    gdown --folder "https://drive.google.com/drive/folders/1Tq5Uixwz5J-aG_NfUQdI6X9CIrNz9ZFS?usp=sharing" -O ../Jobs_2026
Unlike the NAICS 5182 analysis, the benchmark looks at ALL postings in the folder, in every industry. The folder is
too large for the repository, so this script writes only aggregated tables (no posting text or rows):
    data/processed/benchmark_quantiles.csv  salary spread for AI-related vs non-AI postings
    data/processed/benchmark_fields.csv     pay, demand, and AI share for each occupation field

Rules
- Valid posting: not flagged as a duplicate, not a possible ghost listing, not an internship.
- Salary: the folder's normalized annual salary (midpoint of the range), kept only when it was converted from an
  annual, hourly (x2,080), weekly (x52), or biweekly (x26) figure, and only between $25,000 and $600,000.
- Occupation field: assigned from the job title with the keyword rules in FIELDS (first match wins; no match means
  "All other occupations").
- AI-related: the title names AI or machine learning, or the posting text names at least one core AI term.

Usage: python build_benchmark_tables.py [path/to/Jobs_2026]
"""
import glob
import re
import sys

import numpy as np
import pandas as pd

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else "../Jobs_2026"
OUT = "data/processed/"

COLS = ["TITLE_CLEAN", "BODY", "NORMALIZED_SALARY_FROM", "NORMALIZED_SALARY_TO", "SALARY_NORMALIZATION_STATUS",
        "IS_DUPLICATE", "IS_INTERNSHIP", "POTENTIAL_GHOST", "PARSED_STATE_NAME", "STATE", "REMOTE_TYPE_NAME"]
ANNUALIZED = {"annual_unchanged", "hourly_x2080", "weekly_x52", "biweekly_x26"}

# first match wins; titles are lower-cased before matching
FIELDS = [
    ("Data Science & ML", r"data scientist|applied scientist|research scientist|machine learning|\bml\b|\bai\b|artificial intelligence|\bnlp\b|computer vision|deep learning|\bllm\b|prompt engineer"),
    ("Data Engineering", r"data engineer|analytics engineer|data architect|database|\betl\b|data warehouse|big data|\bdba\b"),
    ("Data Analytics & BI", r"data analyst|business intelligence|\bbi (?:analyst|developer|engineer)|analytics|reporting analyst|insights analyst"),
    ("Software Engineering", r"software|developer|full[ -]?stack|front[ -]?end|back[ -]?end|\bmobile\b|\bios\b|android|programmer|application engineer"),
    ("IT & Cloud Infrastructure", r"devops|site reliability|\bsre\b|cloud|systems? (?:admin|engineer)|network (?:engineer|admin|architect)|infrastructure|it support|help ?desk|technical support|solutions? architect|platform engineer"),
    ("Cybersecurity", r"cyber|infosec|information security|(?:security|soc) (?:analyst|engineer|architect|specialist|administrator|consultant)|penetration|devsecops"),
    ("Product & Project Management", r"product manager|project manager|program manager|scrum|product owner|technical program"),
    ("Business Analysis & Consulting", r"business analyst|management analyst|consultant|strategy|operations analyst|systems analyst"),
    ("Finance & Accounting", r"financ|accountant|accounting|auditor|controller|treasury|actuar"),
    ("Marketing & Sales", r"marketing|\bsales\b|account executive|business development"),
]
OTHER = "All other occupations"
NAMED = [f for f, _ in FIELDS]
AI_TITLE = re.compile(r"\bai\b|artificial intelligence|machine learning|\bml\b|deep learning|\bnlp\b|natural language|\bllm\b|generative|gen ?ai|computer vision|neural|prompt engineer|mlops")
AI_TEXT = re.compile(r"machine learning|artificial intelligence|deep learning|neural network|natural language processing|\bnlp\b|\bllm\b|large language model|generative ai|computer vision|\bpytorch\b|\btensorflow\b")
FIELD_RES = [(name, re.compile(pat)) for name, pat in FIELDS]

STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}
ABBR_BY_NAME = {v: k for k, v in STATES.items()}


def field_of(title):
    for name, pattern in FIELD_RES:
        if pattern.search(title):
            return name
    return OTHER


frames = []
total_rows = 0
for path in sorted(glob.glob(f"{DATA_DIR}/jobs_2026_part_*.parquet")):
    d = pd.read_parquet(path, columns=COLS)
    total_rows += len(d)
    valid = ~d["IS_DUPLICATE"].fillna(False).astype(bool) & ~d["POTENTIAL_GHOST"].fillna(False).astype(bool)
    valid &= ~d["IS_INTERNSHIP"].fillna(0).astype(bool)
    d = d[valid].copy()
    title = d["TITLE_CLEAN"].fillna("").str.lower()
    d["field"] = [field_of(t) for t in title]
    body = d["BODY"].fillna("").str.lower()
    d["ai"] = title.apply(lambda t: bool(AI_TITLE.search(t))).values | body.apply(lambda b: bool(AI_TEXT.search(b))).values
    lo = pd.to_numeric(d["NORMALIZED_SALARY_FROM"], errors="coerce")
    hi = pd.to_numeric(d["NORMALIZED_SALARY_TO"], errors="coerce")
    d["sal"] = (lo + hi) / 2
    d.loc[~d["SALARY_NORMALIZATION_STATUS"].isin(ANNUALIZED) | ~d["sal"].between(25000, 600000), "sal"] = np.nan
    state = d["PARSED_STATE_NAME"].fillna("")
    abbr = d["STATE"].fillna("").str.upper()
    d["state"] = np.where(state.isin(ABBR_BY_NAME), state, abbr.map(STATES).fillna(""))
    d["remote"] = d["REMOTE_TYPE_NAME"].fillna("Unknown").replace({"On-site": "Onsite"})
    frames.append(d[["field", "ai", "sal", "state", "remote"]])
df = pd.concat(frames, ignore_index=True)
print("rows in folder:", total_rows, "| valid postings:", len(df), "| with usable annual salary:", int(df["sal"].notna().sum()))
sal = df.dropna(subset=["sal"]).copy()


def spread(g):
    return pd.Series({
        "n": len(g), "p05": g["sal"].quantile(0.05), "p25": g["sal"].quantile(0.25), "median": g["sal"].median(),
        "p75": g["sal"].quantile(0.75), "p95": g["sal"].quantile(0.95), "mean": g["sal"].mean(),
    })


# 1) salary spread, AI-related vs non-AI, for all jobs and for the computer and business fields only
rows = []
for scope, frame in (("All jobs", sal), ("Computer and business fields", sal[sal["field"].isin(NAMED)])):
    for ai, g in frame.groupby("ai"):
        rows.append({"scope": scope, "ai_related": bool(ai), **spread(g).round(0).to_dict()})
pd.DataFrame(rows).to_csv(OUT + "benchmark_quantiles.csv", index=False)

# 2) one row per occupation field
field_median = sal.groupby("field")["sal"].median()
rows = []
for field_name in NAMED + [OTHER]:
    allp, sp = df[df["field"] == field_name], sal[sal["field"] == field_name]
    ai_s, non_s = sp[sp["ai"]], sp[~sp["ai"]]
    stated = allp[allp["remote"] != "Unknown"]
    rows.append({
        "field": field_name, "postings": len(allp), "ai_share_postings": round(float(allp["ai"].mean()), 4),
        "salary_postings": len(sp), "median": round(float(sp["sal"].median())), "p25": round(float(sp["sal"].quantile(0.25))),
        "p75": round(float(sp["sal"].quantile(0.75))), "n_ai": len(ai_s),
        "median_ai": round(float(ai_s["sal"].median())) if len(ai_s) else np.nan,
        "n_nonai": len(non_s), "median_nonai": round(float(non_s["sal"].median())) if len(non_s) else np.nan,
        "remote_share_stated": round(float((stated["remote"] == "Remote").mean()), 4) if len(stated) else np.nan,
        "remote_or_hybrid_share_stated": round(float(stated["remote"].isin(["Remote", "Hybrid"]).mean()), 4) if len(stated) else np.nan,
    })
pd.DataFrame(rows).to_csv(OUT + "benchmark_fields.csv", index=False)

print("saved benchmark_quantiles.csv and benchmark_fields.csv")
