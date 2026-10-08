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
- `build_met_text_panel.py` - builds `data/processed/met_text_panel.csv` from the MET Career Compass 2026 job files
- `data/` - raw, interim, and processed datasets (see `data/processed/data_dictionary.md`)
- `figures/` - earlier exported chart images
- `outputs/` - exported tables, CSVs, and other analysis outputs
- `references.bib` - bibliography

## Data Sources

- **MET Employability Career Match API (2026):** `data/processed/career_market_panel.csv`, 258 postings.
- **MET Career Compass 2026 job files** (course Google Drive folder, not stored in the repo):
  `data/processed/met_text_panel.csv`, 350 postings, used for skills and degree wording.

## Team

Group 6 - AD688
