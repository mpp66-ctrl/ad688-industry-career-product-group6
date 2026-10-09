"""Build data/processed/met_text_panel.csv from the course Jobs_2026 folder.

Source: the "Jobs_2026" Google Drive folder from the course assignments (20 parquet files, 815,193
postings), downloaded beside the repository with:
    gdown --folder "https://drive.google.com/drive/folders/1Tq5Uixwz5J-aG_NfUQdI6X9CIrNz9ZFS?usp=sharing" -O ../Jobs_2026
The folder is too large for the repo, so this script filters it and exports a small processed file.
Only posting fields are exported; the licensed WRDS company columns in the folder are never copied.

Filter: NAICS 518 -> role-keyword titles -> posted in 2026 -> one row per posting ID -> drop repeat
listings (same title, company, state, and posting date under different IDs).
Skill and education flags are read from the posting text (BODY), because the SKILLS_NAME field in
this folder is truncated (about 3 skills per posting, alphabetical) and EDUCATION_LEVELS_NAME is a
modeled level that the posting does not state.

Two modes:
  python build_met_text_panel.py [path/to/Jobs_2026]
      -> data/processed/met_text_panel.csv: our NAICS 5182 analysis dataset (all postings in the industry).
  python build_met_text_panel.py [path/to/Jobs_2026] --all-industries
      -> data/processed/met_salary_model_panel.csv: pathway postings from ANY industry that disclose a salary,
         with an `naics_5182` flag. Only the Salary Estimator on the Predictive Modeling page uses it, because
         the NAICS 5182 slice alone has too few salaries to train a model with this many inputs.
"""
import glob
import re
import sys

import pandas as pd

ALL_INDUSTRIES = "--all-industries" in sys.argv
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
DATA_DIR = _args[0] if _args else "../Jobs_2026"
OUT = "data/processed/met_salary_model_panel.csv" if ALL_INDUSTRIES else "data/processed/met_text_panel.csv"

KEYWORDS = [
    "data scientist", "data engineer", "machine learning engineer", "ml engineer", "data analyst",
    "business analyst", "bi analyst", "business intelligence analyst", "analytics engineer",
    "applied scientist", "data architect", "database architect",
]

COLS = [
    "ID", "TITLE_CLEAN", "COMPANY_NAME", "STATE_NAME", "REMOTE_TYPE_NAME", "EMPLOYMENT_TYPE_NAME",
    "SALARY_FROM", "SALARY_TO", "ORIGINAL_PAY_PERIOD", "NAICS_2022_3", "NAICS_2022_6", "POSTED", "BODY",
    "MIN_YEARS_EXPERIENCE", "STATE", "LOCATION",
]

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
# the state field is a mix of names, abbreviations, and city fragments; these city words resolve the rest
CITY_HINTS = {
    "francisco": "California", "los angeles": "California", "angeles": "California", "sunnyvale": "California",
    "san jose": "California", "jose": "California", "palo alto": "California", "alto": "California",
    "san diego": "California", "mountain view": "California", "york city": "New York", "new york": "New York",
    "brooklyn": "New York", "seattle": "Washington", "bellevue": "Washington", "redmond": "Washington",
    "boston": "Massachusetts", "cambridge": "Massachusetts", "chicago": "Illinois", "austin": "Texas",
    "dallas": "Texas", "houston": "Texas", "baton rouge": "Louisiana", "rouge": "Louisiana",
    "atlanta": "Georgia", "washington, dc": "District of Columbia",
}


def clean_state(abbr, name, location):
    """Resolve a US state name from the STATE code, the state-name field, or the location text."""
    abbr = str(abbr or "").strip().upper()
    if abbr in STATES:
        return STATES[abbr]
    name = str(name or "").strip()
    if name in STATES.values():
        return name
    if name.upper() in STATES:
        return STATES[name.upper()]
    text = f"{name} {location or ''}".lower()
    for hint, state in CITY_HINTS.items():
        if hint in text:
            return state
    match = re.search(r",\s*([A-Z]{2})\b", str(location or ""))
    return STATES.get(match.group(1), "") if match else ""


# employer names that are really a domain or a job board: known domains map to the employer, boards to unknown
DOMAIN_EMPLOYERS = {
    "jpmc.fa.oraclecloud.com": "JPMorgan Chase", "careers.pnc.com": "PNC", "careers.wbd.com": "WBD",
    "careers.truist.com": "Truist", "careers.usbank.com": "Usbank",
}
JOB_BOARDS = ("jobs via dice", "jobgether", "lensa", "ziprecruiter", "jooble", "jobot")


def clean_company(name):
    raw = str(name or "").strip()
    low = raw.lower()
    if low in DOMAIN_EMPLOYERS:
        return DOMAIN_EMPLOYERS[low]
    if not raw or low in JOB_BOARDS:
        return "Unknown employer"
    return raw

# "5+ years of experience", "3-5 years' experience", "minimum of 2 years of relevant experience", ...
EXPERIENCE = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:-|to|–)?\s*(?:\d{1,2}\s*)?\+?\s*years?\s*(?:of\s*)?(?:[\w'/&-]+\s+){0,4}?experience",
    re.I,
)


def experience_from_text(body):
    """Smallest number of years that a posting's text ties to 'experience' (None if not stated)."""
    found = [int(n) for n in EXPERIENCE.findall(body) if 0 < int(n) <= 20]
    return min(found) if found else None

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


frames, total_rows, in_industry = [], 0, 0
for path in sorted(glob.glob(f"{DATA_DIR}/jobs_2026_part_*.parquet")):
    part = pd.read_parquet(path, columns=COLS)
    total_rows += len(part)
    in_518 = part["NAICS_2022_3"].astype(str) == "518"
    in_industry += int(in_518.sum())
    if not ALL_INDUSTRIES:
        part = part[in_518]
    part_title = part["TITLE_CLEAN"].fillna("").str.lower()
    frames.append(part[part_title.apply(lambda t: any(k in t for k in KEYWORDS))])  # filter early to save memory
df = pd.concat(frames, ignore_index=True)
print("rows in folder:", total_rows)
if not ALL_INDUSTRIES:
    print("after NAICS 518:", in_industry)
print("after role keywords:", len(df))
df = df[df["POSTED"].astype(str).str[:4] == "2026"]
print("after keeping 2026 postings:", len(df))
df = df.drop_duplicates(subset="ID").copy()
repeat_key = (df["TITLE_CLEAN"].fillna("").str.lower().str.strip() + "|" + df["COMPANY_NAME"].fillna("").str.lower().str.strip()
              + "|" + df["STATE_NAME"].fillna("").str.lower() + "|" + df["POSTED"].astype(str))
df = df[~repeat_key.duplicated()].copy()
print("after dropping repeat listings:", len(df))

for c in ["SALARY_FROM", "SALARY_TO"]:
    df[c] = pd.to_numeric(df[c].replace("", None), errors="coerce")
# 0 means not disclosed. Most hourly postings are already stored as an annual figure (rate x 2080),
# but a few keep the raw hourly rate; values under 1,000 are treated as hourly and converted.
for c in ["SALARY_FROM", "SALARY_TO"]:
    df.loc[df[c] <= 0, c] = float("nan")
raw_hourly = df["SALARY_TO"] < 1000
for c in ["SALARY_FROM", "SALARY_TO"]:
    df.loc[raw_hourly, c] = df.loc[raw_hourly, c] * 2080
# internship stipends are not comparable to annual salaries, so they are treated as not disclosed
intern = df["TITLE_CLEAN"].fillna("").str.contains(r"\bintern(?:ship)?\b", case=False, regex=True)
for c in ["SALARY_FROM", "SALARY_TO"]:
    df.loc[intern, c] = float("nan")
df["REMOTE_TYPE_NAME"] = df["REMOTE_TYPE_NAME"].replace({"On-site": "Onsite"})
df["role"] = df["TITLE_CLEAN"].apply(classify_role)
if ALL_INDUSTRIES:
    df = df[df["SALARY_FROM"].notna() & df["SALARY_TO"].notna()].copy()
    print("after keeping postings that disclose a salary:", len(df))

body = df["BODY"].fillna("")
has_text = body.str.strip().str.len() > 0
out = pd.DataFrame({
    "job_id": df["ID"],
    "title": df["TITLE_CLEAN"],
    "role": df["role"],
    "company_name": df["COMPANY_NAME"],
    "company_name_clean": df["COMPANY_NAME"].apply(clean_company),
    "state": [clean_state(a, n, l) for a, n, l in zip(df["STATE"], df["STATE_NAME"], df["LOCATION"])],
    "remote_status": df["REMOTE_TYPE_NAME"],
    "employment_type": df["EMPLOYMENT_TYPE_NAME"],
    "salary_min_annual": df["SALARY_FROM"],
    "salary_max_annual": df["SALARY_TO"],
    "posted_at": df["POSTED"],
    "has_text": has_text,
})
if ALL_INDUSTRIES:
    out["naics_5182"] = (df["NAICS_2022_3"].astype(str) == "518").values
# minimum years of experience: the structured field when it is above zero, otherwise read from the text
field_years = pd.to_numeric(df["MIN_YEARS_EXPERIENCE"].replace("", None), errors="coerce")
field_years = field_years.where((field_years > 0) & (field_years <= 20))
text_years = pd.Series([experience_from_text(b) if t else None for b, t in zip(body, has_text)], index=df.index)
out["experience_min_years"] = field_years.combine_first(pd.to_numeric(text_years, errors="coerce")).values
out["experience_source"] = ["field" if pd.notna(f) else "text" if pd.notna(t) else "" for f, t in zip(field_years, text_years)]
for name, pat in SKILLS.items():
    out["skill_" + name] = [bool(re.search(pat, b, re.I)) if t else pd.NA for b, t in zip(body, has_text)]
for name, pat in LEVELS.items():
    out["degree_" + name] = [degree_wording(b, pat) if t else pd.NA for b, t in zip(body, has_text)]

out.to_csv(OUT, index=False)
print("saved", OUT, "| rows:", len(out), "| rows with posting text:", int(has_text.sum()))
