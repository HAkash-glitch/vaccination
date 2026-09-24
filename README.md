# Global Vaccination Coverage & Vaccine-Preventable Disease Analysis

An end-to-end data analysis project on WHO/UNICEF immunization data
(1980–2023): data cleaning, a normalized SQL database, exploratory data
analysis, and a Power BI dashboard design, examining how vaccination
coverage relates to vaccine-preventable disease incidence across countries
and WHO regions.

## Project Overview

Five linked WHO/UNICEF source tables — Coverage, Disease Incidence,
Reported Cases, Vaccine Introduction, and Vaccine Schedule — are cleaned,
loaded into a normalized SQL schema, explored, and visualized to answer:
how has global vaccination coverage trended, where do dose-completion and
introduction gaps remain by region, and how does coverage relate to
disease incidence?

## Features

- Reproducible cleaning pipeline (`python/data_cleaning.py`) that splits
  country-level data from WHO's own regional/global rollups, documents
  every decision (e.g. missing coverage values are never imputed), and
  writes tidy CSVs.
- Normalized SQL schema (`sql/create_tables.sql`) with 3 dimension tables
  and 5 fact tables, loaded into a working SQLite database
  (`sql/vaccination.db`) via `python/build_database.py`.
- 8 verified analysis queries (`sql/analysis_queries.sql`) with real,
  tested sample output in comments.
- A full EDA notebook (`notebooks/vaccination_eda.ipynb`) — 15 charts
  covering univariate, bivariate, and multivariate analysis, each with a
  chart-choice rationale, insight, and business-impact note, all run
  against real data (no placeholder outputs).
- A Power BI dashboard design (`powerbi/PowerBI_Design_Guide.md`) with
  KPIs, DAX measures, slicers, and a 3-page layout.

## Dataset Description

| File | Rows (cleaned, country-level) | Years | Key columns |
|---|---|---|---|
| Coverage | 381,041 | 1980–2023 | country, year, antigen, coverage % |
| Disease Incidence | 82,054 | 1980–2023 | country, year, disease, incidence rate |
| Reported Cases | 82,054 | 1980–2023 | country, year, disease, case count |
| Vaccine Introduction | 138,320 | 1940–2023 | country, year, vaccine, introduced (Y/N) |
| Vaccine Schedule | 8,052 | 2019–2023 | country, year, vaccine, dose schedule |

Source: WHO/UNICEF Immunization Data Portal (data extracts dated
2025-02-01, as recorded in each file's footer row).

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# 1. Clean the raw Excel files into tidy CSVs
cd python
python data_cleaning.py

# 2. Build the normalized SQLite database from the cleaned CSVs
python build_database.py

# 3. (Re)build the EDA notebook (optional — a built copy is already at
#    notebooks/vaccination_eda.ipynb)
cd ../notebooks
python build_notebook.py
```

## SQL Setup

```bash
sqlite3 sql/vaccination.db < sql/analysis_queries.sql   # run the analysis queries
```

For MySQL/Postgres/SQL Server, use `sql/create_tables.sql` for the schema
and see the bulk-load notes at the top of `sql/insert_data.sql` for loading
the cleaned CSVs (`cleaned_data/*.csv`).

## Power BI Setup

The built dashboard file is `powerbi/Vaccination_Dashboard.pbix` — open it
directly in Power BI Desktop. Current state, honestly:

- **Page 1 (built)**: 4 KPI cards (Total Countries, Total Doses, Average
  Coverage, Total Cases), a coverage trend line chart, a country-level
  treemap, a reported-cases-by-disease bar chart, a doses-by-year column
  chart, a cases trend line chart, and two coverage comparison bar charts
  (by vaccine, by country) — all using correct aggregations (Average for
  the % coverage fields, Sum for count fields like doses/cases).
- **Not yet built**: slicers (Year, Country, WHO Region, Vaccine,
  Disease), the DTP1-vs-DTP3 drop-off visual, the coverage-vs-incidence
  scatter, the region × year heatmap, the vaccine-introduction timeline,
  and pages 2–3 (Regional & Dose Analysis / Disease & Introduction).

To extend it, follow `powerbi/PowerBI_Design_Guide.md` from where Page 1
leaves off. If starting from scratch instead:

1. Connect Power BI to `sql/vaccination.db` (ODBC) or import
   `cleaned_data/*.csv` directly.
2. Build the relationships described in the guide (Countries/Diseases as
   dimensions; do **not** join the Vaccines lookup table into the model —
   see the note in the guide on why).
3. Paste in the DAX measures from the guide.
4. Build the 3-page layout (Overview / Regional & Dose Analysis /
   Disease & Introduction) described in the guide.

## Results

Headline findings (see `notebooks/vaccination_eda.ipynb` and
`documentation/Project_Report.md` for full detail and every chart):

- Global measles (MCV1) coverage rose from the 1980s through the late
  2010s, then dipped in 2020–2021 (COVID-era disruption), a pattern that
  repeats across DTP3 and other antigens.
- Measles incidence fell from ~714 to ~43 (per the dataset's rate unit)
  between 1990 and 2022, alongside rising coverage.
- AFRO shows the largest DTP1→DTP3 dose drop-off of any WHO region (~6.1
  points in 2022) — a retention gap, not an access gap.
- SEARO lags every other WHO region in Rotavirus vaccine introduction.
- Booster-dose (1st booster) coverage has been flat-to-declining
  2017–2023, unlike the earlier rising trend in primary-series doses.
- Several original brief questions (gender, education, urban/rural,
  seasonality) could not be answered — those fields do not exist in any
  of the five source tables, and are reported as such rather than guessed.

## Screenshots

See `images/` for exported chart PNGs (extract from the notebook, or embed
Power BI screenshots here once the dashboard is built in Desktop).

## Future Improvements

- Obtain a vaccine-code crosswalk to safely join the Coverage antigen
  codes, Introduction vaccine names, and Schedule vaccine codes into one
  unified Vaccines dimension.
- Add population-weighted (not simple country-average) regional coverage
  figures for a more epidemiologically accurate regional comparison.
- Extend the incidence/coverage correlation analysis with a lagged model
  (coverage in year N vs incidence in year N+1/N+2), since immunity
  effects are not always same-year.
