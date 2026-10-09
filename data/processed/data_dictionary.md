# Data Dictionary: met_text_panel.csv

Built by `build_met_text_panel.py` from the course's `Jobs_2026` Google Drive folder (20 parquet files, 815,193
postings): https://drive.google.com/drive/folders/1Tq5Uixwz5J-aG_NfUQdI6X9CIrNz9ZFS (the folder confirmed by our instructor)
One row per distinct posting; 765 rows (NAICS 518, pathway job titles, repeat listings removed; all postings are from 2026).
Posting text is not stored in the file; the flags below were computed from it when the file was built, and the
licensed company-industry columns of the source folder are not copied.

| Column | Description |
|---|---|
| `job_id` | Posting ID from the source files |
| `title` | Cleaned job title |
| `role` | Role family from the title: Data Analyst, Data Scientist, ML Engineer, or Data / Analytics Engineer |
| `company_name`, `state`, `remote_status`, `employment_type` | As in the source (empty when not given); `remote_status` is Remote, Hybrid, Onsite, or Unknown |
| `salary_min_annual`, `salary_max_annual` | Annual salary range in USD; empty when not disclosed or an internship (303 rows have one) |
| `posted_at` | Posting date |
| `has_text` | True when the source has posting text (570 rows); the flags below are empty otherwise |
| `skill_<name>` | True when the posting text matches the skill's name pattern (Python, SQL, Machine Learning, Cloud/AWS, Data Visualization, Statistics, and 11 more; patterns are in the build script) |
| `degree_Associate`, `degree_Bachelor`, `degree_Master`, `degree_PhD` | `required` (a sentence naming the degree says require, minimum, must, or mandatory, with no preference word), `preferred`, `mentioned` (named without requirement wording), or `none` |

Known limits: the source `SKILLS_NAME` field is truncated and `EDUCATION_LEVELS_NAME` is a modeled level, so
neither is used. Text-based flags undercount when a posting words a skill or requirement differently.
