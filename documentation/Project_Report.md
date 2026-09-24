# Global Vaccination Coverage & Vaccine-Preventable Disease Analysis

**A Data Analysis Project Report**

---

## 1. Abstract

This project analyzes WHO/UNICEF immunization data (1980–2023) across five
linked tables — vaccine coverage, disease incidence, reported cases,
vaccine introduction, and vaccine schedules — to examine the relationship
between vaccination programs and vaccine-preventable disease outcomes. The
data (381K+ coverage records, 82K+ incidence and case records, 138K+
introduction records) was cleaned, loaded into a normalized SQL database,
explored through univariate, bivariate, and multivariate EDA, and queried
to answer a defined set of easy, medium, and scenario-based analytical
questions. The analysis finds a clear historical link between rising
coverage and falling disease incidence (e.g., measles incidence fell from
~714 to ~43 per unit population between 1990 and 2022), while surfacing
specific, addressable gaps: a larger-than-average DTP dose drop-off in the
AFRO region, a lag in Rotavirus vaccine introduction in SEARO, and a
COVID-era coverage dip that booster doses have not recovered from as of
2023. Questions requiring demographic fields not present in the source
data (gender, education, urban/rural, seasonality) are reported as
unanswerable with this dataset rather than estimated.

## 2. Introduction

Vaccination remains one of the most cost-effective public health
interventions for reducing morbidity and mortality from preventable
disease. This project uses publicly available WHO/UNICEF immunization data
to quantify how coverage relates to disease incidence, and to identify
where coverage, dose-completion, and vaccine-introduction gaps persist
across countries and WHO regions.

## 3. Problem Statement

How effective has global vaccination coverage been at reducing
vaccine-preventable disease incidence between 1980 and 2023, and where do
the largest regional gaps in coverage, dose completion, and vaccine
introduction remain?

## 4. Objectives

1. Clean and structure five linked WHO source tables into an
   analysis-ready, normalized form.
2. Build a normalized SQL database supporting reproducible analytical
   queries.
3. Quantify the relationship between vaccination coverage and disease
   incidence at the country and regional level.
4. Identify specific regions/vaccines with the largest coverage,
   dose-completion, or introduction gaps.
5. Deliver a Power BI dashboard design for ongoing monitoring.
6. Clearly flag any project question that the available data cannot
   answer, rather than filling gaps with assumptions.

## 5. Dataset Description

| Table | Source File | Rows (country-level, cleaned) | Year Range | Grain |
|---|---|---|---|---|
| Coverage | coverage-data.xlsx | 381,041 | 1980–2023 | country × year × antigen × coverage category |
| Disease_Incidence | incidence-rate-data.xlsx | 82,054 | 1980–2023 | country × year × disease |
| Reported_Cases | reported-cases-data.xlsx | 82,054 | 1980–2023 | country × year × disease |
| Vaccine_Introduction | vaccine-introduction-data.xlsx | 138,320 | 1940–2023 | country × year × vaccine |
| Vaccine_Schedule | vaccine-schedule-data.xlsx | 8,052 | 2019–2023 | country × year × vaccine × dose round |

Each source file also contained WHO reference/metadata sheets (dropped for
analysis) and a footer metadata row (dropped during cleaning). Coverage
additionally contains WHO's own regional/global rollup rows (`GROUP` ≠
`COUNTRIES`), separated out during cleaning rather than mixed with
country-level records.

## 6. Methodology

1. **Inspection** — every source file's sheets, columns, dtypes, and
   missingness were profiled before any cleaning decision was made (no
   assumed schema).
2. **Cleaning** — see Section 8.
3. **Normalization** — a 3-dimension / 5-fact-table SQL schema was
   designed and loaded (Section 9).
4. **EDA** — 15 charts across univariate, bivariate, and multivariate
   views (Section 10), built and executed against the real database.
5. **Querying** — 8 analytical SQL queries answering the project's
   easy/medium question tiers, each run and verified (Section 11).
6. **Dashboarding** — a Power BI design translating the same schema and
   findings into an interactive, slicer-driven dashboard (Section 12).

## 7. Data Cleaning

Applied uniformly by `python/data_cleaning.py`:

- **Footer rows dropped**: every source file ends in a metadata row
  (`"Created: <timestamp>"`) with all data columns null — identified via
  `YEAR` being null and removed.
- **Country vs. aggregate rows split**: Coverage/Incidence/Cases mix
  `GROUP == 'COUNTRIES'` rows with WHO's own regional/global/income-group
  rollups (`WHO_REGIONS`, `GLOBAL`, `WB_LONG`, `WB_SHORT`,
  `DEVELOPMENT_STATUS`, `GAVI_PHASE5`, `UNICEF_REGIONS`). These were
  written to separate `*_country.csv` / `*_aggregate.csv` outputs so
  country-level analysis is never silently double-counted with regional
  rollups, while preserving the official WHO rollups for anyone who needs
  them.
- **Types**: `YEAR` cast float → int; string columns stripped of
  whitespace.
- **Duplicates**: exact-duplicate rows dropped (0 found in every table
  after footer removal — verified, not assumed).
- **Missing values — deliberately not imputed.** `COVERAGE` is null for
  44.4% of country-level Coverage rows. This is not random: it reflects
  antigen/country/year/category combinations WHO has no reported estimate
  for. Filling these with a mean, zero, or interpolated value would
  fabricate an epidemiological measurement the source does not support, so
  nulls were preserved and every downstream query/chart either filters
  them explicitly or reports on the subset with data.
- **Vaccine/disease name standardization**: WHO's own antigen/disease
  codes (`ANTIGEN`, `DISEASE`) were kept as-is (they are a controlled WHO
  vocabulary); only whitespace was stripped. No codes were remapped or
  merged across the three different vaccine-coding schemes present
  (coverage's `ANTIGEN`, introduction's free-text vaccine name, schedule's
  `VACCINECODE`) since no crosswalk table was supplied to validate such a
  mapping against — inventing one would risk false equivalences.
- **Values > 100% in COVERAGE**: kept, not clipped. These are genuine
  WHO-reported administrative-coverage values that occur when the
  administrative target-population denominator undercounts the true
  population; flagged in the EDA notebook (Chart / wrangling step) rather
  than silently altered.

## 8. Exploratory Data Analysis

Full detail with charts, rationale, insights, and business-impact
assessments is in `notebooks/vaccination_eda.ipynb` (15 charts). Summary of
each analysis tier:

**Univariate:** WHO-region country counts, most-reported vaccine antigens,
MCV1 coverage distribution relative to the 95% herd-immunity threshold.

**Bivariate:** DTP1 vs. DTP3 coverage by region (dose drop-off), MCV1
coverage vs. measles incidence scatter (country level, 2022), Rotavirus
introduction counts by region.

**Multivariate:** DTP3 coverage heatmap (region × year), correlation
matrix and pair plot across MCV1 coverage, DTP3 coverage, measles
incidence, and pertussis incidence, segmented by WHO region.

## 9. SQL Database Design

Normalized schema — 3 dimensions, 5 facts (full DDL in
`sql/create_tables.sql`):

- **Countries** (`country_code` PK, `country_name`, `who_region`)
- **Vaccines** (`vaccine_code`, `source` composite PK, `vaccine_description`)
  — source-tagged because the three vaccine-coding schemes across tables
  are not a verified 1:1 crosswalk (documented explicitly rather than
  merged)
- **Diseases** (`disease_code` PK, `disease_description`)
- **Coverage**, **Disease_Incidence**, **Reported_Cases**,
  **Vaccine_Introduction**, **Vaccine_Schedule** — fact tables, each with a
  foreign key to `Countries.country_code`; the disease facts additionally
  reference `Diseases.disease_code`.

Loaded into a working SQLite database (`sql/vaccination.db`) with row
counts verified against the cleaned CSVs (Section 5 table). Indexes were
added on every `(country_code, year)` and code column used in a join or
filter.

## 10. SQL Queries & Findings

Eight queries were written and run against `sql/vaccination.db` (full text
and sample output in `sql/analysis_queries.sql`):

| # | Question | Finding |
|---|---|---|
| 1 | Global MCV1 coverage trend | Rose to ~89% (2019), dipped to ~85% (2021) |
| 2 | High-coverage countries with nonzero measles incidence, 2022 | ZWE, SLE, ZMB, TJK etc. — all at/near 90%, below the 95% herd-immunity threshold |
| 3 | DTP1→DTP3 drop-off by region, 2022 | AFRO largest gap (89.32%→83.23%, 6.1 pts); EURO smallest (95.56%→92.30%, 3.3 pts) |
| 4 | Booster-dose (DIPHCV4) trend, 2017–2023 | Flat/declining: 83.33% → 81.29% → 83.20% |
| 5 | Rotavirus introduction by region | AFRO 38 countries, SEARO only 6 |
| 6 | Highest-coverage vaccines, 2022 | DTPCV1 92.25%, PCV1 90.69%, BCG 89.83% |
| 7 | Largest incidence decline, 1990 vs 2022 | Measles 714.2→43.1; Pertussis 240.2→5.4 |
| 8 | Hepatitis B (3rd dose) coverage gap by region, 2022 | AFRO lowest (83.24%), EURO highest (90.20%) |

## 11. Power BI Dashboard

The delivered dashboard file is `powerbi/Vaccination_Dashboard.pbix`.
Page 1 is built: 4 KPI cards (Total Countries, Total Doses, Average
Coverage, Total Cases), a coverage trend line chart, a country-level
coverage treemap, a reported-cases-by-disease bar chart, a doses-by-year
column chart, a cases trend line chart, and coverage comparisons by
vaccine and by country — all verified to use the correct aggregation
(Average for percentage fields, Sum for count fields).

The full target design — including the region-comparison, dose-drop-off,
coverage-vs-incidence scatter, region×year heatmap, vaccine-introduction
timeline, slicers, and the 3-page layout — is specified in full in
`powerbi/PowerBI_Design_Guide.md`, but is not yet built into the .pbix.
That remains the next step, documented here rather than presented as
finished:

- **KPIs (built)**: Total Countries, Total Doses, Average Coverage, Total
  Cases.
- **Planned pages (design complete, build pending)**: (1) Overview — trend
  line + map + KPI cards; (2) Regional & Dose Analysis — DTP1 vs DTP3 by
  region, DTP3 heatmap; (3) Disease & Introduction — incidence trend,
  coverage-vs-incidence scatter, Rotavirus introduction timeline.
- **Planned slicers (not yet added)**: Year, Country, WHO Region, Vaccine,
  Disease.
- Modeling note explicitly documented: the Vaccines lookup table is **not**
  joined into the relationship model, to avoid implying a false
  equivalence between the three different vaccine-coding schemes.


## 12. Findings / Key Insights

1. Global coverage and disease incidence move in opposite directions over
   the 1980–2023 period, consistent with vaccination's protective effect
   (SQL Q1, Q7; EDA Charts 4, 7, 8, 14, 15).
2. A country can have coverage at or above 90% and still report nonzero
   measles incidence — 90% is below the ~95% herd-immunity threshold
   commonly cited for measles (SQL Q2; EDA Chart 3).
3. AFRO has the largest 1st-to-3rd-dose drop-off of any WHO region — a
   retention/follow-up problem distinct from initial-access coverage (SQL
   Q3; EDA Chart 5).
4. SEARO lags substantially behind every other WHO region in Rotavirus
   vaccine introduction (SQL Q5; EDA Chart 9).
5. Booster-dose coverage has not shown the same historical rise seen in
   primary-series doses, and has been flat-to-declining across the only
   years it's reported (2017–2023) (SQL Q4; EDA Chart 13).
6. A visible, multi-antigen, multi-region coverage dip occurred in
   2020–2021, consistent with COVID-19-era disruption to routine
   immunization services (EDA Charts 4, 12).

## 13. Scenario Analysis

- **Scenario: "A health ministry has budget for one intervention — where
  should it go?"** — Based on Finding 3 above, a retention/follow-up
  program (SMS reminders, community health worker follow-up visits) in
  AFRO would likely yield more completed vaccinations per dollar than a
  first-dose outreach campaign, since first-dose access (DTP1 ~89%) is
  already comparatively strong there relative to completion (DTP3 ~83%).
- **Scenario: "Is a 90%-coverage country 'safe' from a measles outbreak?"**
  — No, per Finding 2: the source data shows multiple countries at or
  above 90% MCV1 coverage with active measles incidence in 2022, because
  90% is below the epidemiological threshold typically needed for herd
  immunity against measles specifically (a highly transmissible disease).
- **Scenario: "Did COVID-19 affect all vaccines equally?"** — Cannot be
  fully answered with precision using the available dataset: the dip is
  visible across the antigens and regions checked in this project (MCV1,
  DTP3), but a rigorous "equally affected" claim would require checking
  every antigen individually, which was outside this project's scope.
  Stated as a partial finding, not a comprehensive one.
- **Scenario questions requiring gender, education level, urban/rural
  status, or seasonal patterns**: cannot be reliably analyzed using the
  available dataset — none of the five source tables contain these fields.

## 14. Challenges

- Three incompatible vaccine-coding schemes across the source tables, with
  no supplied crosswalk, prevented building a single unified Vaccines
  dimension without risking a fabricated mapping.
- 44% missingness in the Coverage table's core metric required a
  no-imputation policy that reduces the sample size in some slices (e.g.
  the booster-dose trend has only 7 years of ADMIN-category data).
- Regional comparisons are simple (unweighted) country averages, not
  population-weighted, which can overstate the influence of small
  countries relative to large ones within a region.

## 15. Limitations

- No demographic breakdown fields (gender, education, urban/rural) exist
  in the source data — any finding about demographic disparities is
  outside the scope of what this dataset can support.
- No seasonality field exists — any seasonal-pattern question is likewise
  unanswerable from this dataset.
- Coverage-vs-incidence correlation is associational, not causal; other
  factors (healthcare access, sanitation, reporting quality) plausibly
  confound the relationship and were not controlled for.
- Vaccine introduction/schedule/coverage figures rely on country
  self-reporting to WHO, with likely variable reporting quality across
  countries — not independently audited as part of this project.

## 16. Conclusion

The data supports a clear historical link between rising vaccination
coverage and declining vaccine-preventable disease incidence, while also
identifying specific, addressable operational gaps — dose-completion in
AFRO, vaccine introduction in SEARO, and booster-dose stagnation globally
— that a targeted program could act on. Equally important, several
questions in the original project brief could not be answered from this
dataset and are reported as such, rather than filled in with assumed or
fabricated figures.

## 17. Future Scope

- Acquire a vaccine-code crosswalk to safely unify the Vaccines dimension
  across all three source tables.
- Add population data to compute population-weighted regional coverage
  figures.
- Extend to a lagged coverage→incidence model (coverage in year N vs.
  incidence in year N+1/N+2) to better capture delayed immunity effects.
- If demographic or seasonal data becomes available from another WHO
  source, extend the schema to support those questions directly rather
  than leaving them unanswered.

## 18. References

- WHO/UNICEF Immunization Data Portal — Coverage, Incidence Rate, Reported
  Cases, Vaccine Introduction, and Vaccine Schedule datasets (extract
  dated 2025-02-01, per each source file's footer metadata row).
- World Health Organization, "WHO/UNICEF Estimates of National
  Immunization Coverage (WUENIC)," 2023 Revision.
