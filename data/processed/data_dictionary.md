# Data Dictionary: career_market_panel.csv

Source: MET Employability Career Match API (`/api/v1/student/jobs/`), filtered to NAICS 518
(Data Processing, Hosting, and Related Services — our Step 1 industry, NAICS 5182), US-only
locations, and title-keyword-matched to the Data Analyst -> Data Scientist career pathway.
Pulled 2026-09-16. 258 rows after deduplication.

| Column | Type | Description |
|---|---|---|
| `job_id` | integer | Unique posting ID from the MET API |
| `title` | string | Raw job title as posted |
| `company_name_raw` | string | Employer name as returned by the API (may be an ATS domain artifact) |
| `company_name_clean` | string | Cleaned employer name; ATS-hosted postings with unreadable tenant codes (e.g. Oracle Cloud subdomains) are labeled `"Unknown employer (ATS-hosted posting)"` rather than guessed |
| `state_clean` | string | Full US state name, standardized from inconsistent raw values (mix of full names, abbreviations, and city names that leaked into the state field). `"Unknown"` where no reliable US state could be determined |
| `state_abbr` | string | 2-letter US state abbreviation (or `US-UNK` if unresolved) |
| `city_raw` | string | Raw city value as returned by the API (unstandardized) |
| `remote_status` | string | One of `remote`, `hybrid`, `onsite`, `unknown` (as tagged by the source) |
| `employment_type` | string | Employment type as posted (e.g. Full-time, Internship); blank if not provided |
| `salary_min_annual` / `salary_max_annual` | float | Annualized salary range in USD. Hourly rates were converted (`hourly x 2080`). Two rows had salary values mislabeled between the annual and hourly fields in the source data (an hourly-scale number filed as "annual" and vice versa) -- corrected using a $1,000 sanity threshold and documented via `salary_source`. Where the structured salary fields were blank, the posting's free-text description was also searched for an explicit dollar figure (e.g. "Salary: $97,510 - $133,100 per year") as a fallback. Blank if no salary data was available anywhere |
| `salary_source` | string | `annual_reported` (native annual value), `hourly_converted` (derived from an hourly rate), `parsed_from_description_text` (recovered from free text when the structured field was blank), or `missing` |
| `experience_min_years` | integer | Minimum years of experience, parsed via regex from the posting's requirements/description text (no structured experience field exists in this API). Blank if no pattern was found |
| `experience_source` | string | `parsed_from_text` or `not_found` |
| `education_level` | string | One of `PhD`, `Master's`, `Bachelor's`, `Associate's`, `Not specified` -- parsed via keyword match against the posting's requirements/description text (no structured education field exists) |
| `education_source` | string | `parsed_from_text` or `missing` |
| `soc_code` / `soc_name` | string | Standard Occupational Classification code/name assigned by the source. **Known reliability issue**: a small number of rows (14/258) carry implausible SOC tags (e.g. "Actors", "Models") that are source-classifier errors, not real job functions -- these rows are kept because the *title itself* matched our career-pathway keywords, but the SOC field should not be trusted at face value for those rows |
| `soc_quality_flag` | string | `ok` or `likely_misclassified` (flags the 14 rows above) |
| `onet_code` / `onet_name` | string | O*NET occupation code/name assigned by the source. Same reliability caveat as `soc_code`/`soc_name` above -- carries the identical classifier noise (e.g. "Models," "Actors") since both are produced by the same underlying occupation classifier |
| `naics_code` / `naics_name` | string | Industry classification. All rows fall under NAICS 518 / "Computing Infrastructure Providers, Data Processing, Web Hosting, and Related Services" (our Step 1 NAICS 5182 pick, captured under both `518000` and `518200` source tags) |
| `skills` | string | Semicolon-separated list of skill names extracted from the posting by the source classifier |
| `posted_at` | date (YYYY-MM-DD) | Date the posting was listed |
| `apply_url` | string | Original posting URL |

## Cleaning decisions summary

- **Industry filter**: NAICS `518` (not `5182` alone) — the source data tags the same industry
  under two different granularities (`518000`: 4,299 rows, `518200`: 10 rows); querying only
  `5182` silently missed the larger bucket.
- **Geographic filter**: US-only. Classified using state field where possible; for blank/`Remote`/
  ambiguous state values, cross-checked the city field for a country signal. Rows with no
  resolvable US signal were excluded rather than assumed. Starting pool: 4,309 -> US: 2,469.
- **Role filter**: title-keyword matching (not SOC-code-based), using: data analyst, data
  scientist, data engineer, business analyst, BI analyst, business intelligence analyst,
  analytics engineer, ML engineer, machine learning engineer, applied scientist, data/database
  architect. Chosen over SOC-based filtering because SOC tags in this dataset are demonstrably
  unreliable (see `soc_quality_flag`), while title text is the most direct evidence of actual
  job function. Result: 259 rows before dedup.
- **Duplicates**: 1 exact duplicate (same title + company + state) removed -> 258 final rows.
- **Salary**: annual and hourly fields cross-validated against each other; hourly rates were
  annualized (x2080); two rows with values swapped between the annual/hourly fields in the
  source data were corrected using a $1,000 sanity threshold. Where both structured fields
  were blank, the free-text job description was also searched for an explicit dollar figure
  as a fallback, recovering 16 additional rows. Final coverage: 89/258 (34%) -- the remaining
  169 rows genuinely state no salary information anywhere in the posting (structured field or
  text), which is itself a documented market finding (most postings in this pool don't disclose
  pay), not a parsing gap.
- **Experience**: no structured field exists in this API tier; parsed from free text using both
  digit patterns ("5+ years") and word-form patterns ("minimum of three years"). Final coverage:
  131/258 (51%) -- the remaining rows were manually spot-checked and genuinely do not state an
  experience requirement anywhere in the text, not a missed extraction.
- **Education**: no structured field exists; keyword-parsed from free text. Only 45/258 (17%)
  yielded a value -- most postings simply don't state a degree requirement.
- **Company names**: ATS-hosted postings where the "company" field was actually a login-portal
  subdomain (e.g. `careers.snowflake.com`, or opaque Oracle Cloud tenant codes) were cleaned
  where the real employer was recoverable from the domain, and explicitly labeled "Unknown
  employer" (not guessed) where it was not. Separately, 19 rows had `"Jobs via Dice"` as the
  company name -- a job-board aggregator placeholder, not a real employer -- and were relabeled
  "Unknown employer (job board aggregator listing)". In total, 35/258 (14%) rows have no
  attributable real employer name; these are excluded from "top employers" rankings but kept
  in the dataset since the role/salary/location data is still valid.
