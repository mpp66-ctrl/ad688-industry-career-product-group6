# AD688 Career Evaluation Product - Group 6

A career evaluation product helping analytics/data-science job seekers understand the Data Processing, Hosting, and Related Services industry (NAICS 5182), built for AD688 - Big Data and Cloud Analytics for Business.

## Project Scope

- **Career pathway:** Data Analyst -> Data Scientist / Analytics Engineer
- **Industry code:** NAICS 5182 - Computing Infrastructure Providers, Data Processing, Web Hosting, and Related Services

## Site Structure

- `index.qmd` - project overview and roadmap
- `introduction.qmd` - product rationale, literature review, and industry scoping
- `data_preparation.qmd` - how both datasets were filtered and cleaned
- `eda.qmd` - Exploratory Analysis (interactive Plotly charts)
- `skill_gap_analysis.qmd` - team skills vs. Data Analyst and Data Scientist / ML postings
- `build_met_text_panel.py` - builds `data/processed/met_text_panel.csv` from the course `Jobs_2026` job files
- `predictive_modeling.qmd` - salary regression, role opportunity scorecard, and salary estimator
- `data/` - raw, interim, and processed datasets (see `data/processed/data_dictionary.md`)
- `outputs/` - exported tables, CSVs, and other analysis outputs
- `references.bib` - bibliography

## Data Sources

- **MET Career Compass 2026 job files** (the `Jobs_2026` Google Drive folder confirmed by our instructor,
  https://drive.google.com/drive/folders/1Tq5Uixwz5J-aG_NfUQdI6X9CIrNz9ZFS?usp=sharing, not stored in the repo):
  `data/processed/met_text_panel.csv`, 765 postings, used for every analysis page.
- `data/processed/met_salary_model_panel.csv`: pathway postings from any industry that disclose a salary
  (2,607), built from the same folder with `--all-industries`; used only by the Salary Estimator.

## Team

Group 6 - AD688

