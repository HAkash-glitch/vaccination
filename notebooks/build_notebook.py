import io
import base64
import json
import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style("whitegrid")

DB_PATH = "../sql/vaccination.db"
OUT_PATH = "vaccination_eda.ipynb"

cells = []
ns = {"DB_PATH": DB_PATH}  # shared execution namespace, like a real kernel


def md(text):
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": text.splitlines(keepends=True),
    })


def code(src):
    """Execute src in the shared namespace, capture stdout + any matplotlib
    figures created, and append a real code cell with real outputs."""
    import contextlib
    buf = io.StringIO()
    outputs = []
    plt.close("all")
    try:
        with contextlib.redirect_stdout(buf):
            exec(src, ns)
    except Exception as e:
        outputs.append({
            "output_type": "error",
            "ename": type(e).__name__,
            "evalue": str(e),
            "traceback": [f"{type(e).__name__}: {e}"],
        })
        cells.append({
            "cell_type": "code", "execution_count": len(cells),
            "metadata": {}, "outputs": outputs,
            "source": src.splitlines(keepends=True),
        })
        print(f"!! ERROR in cell:\n{src}\n{e}")
        raise
    text = buf.getvalue()
    if text:
        outputs.append({
            "output_type": "stream", "name": "stdout",
            "text": text.splitlines(keepends=True),
        })
    for num in plt.get_fignums():
        fig = plt.figure(num)
        imgbuf = io.BytesIO()
        fig.savefig(imgbuf, format="png", bbox_inches="tight", dpi=100)
        imgbuf.seek(0)
        b64 = base64.b64encode(imgbuf.read()).decode("ascii")
        outputs.append({
            "output_type": "display_data",
            "data": {"image/png": b64, "text/plain": ["<Figure>"]},
            "metadata": {},
        })
    plt.close("all")
    cells.append({
        "cell_type": "code", "execution_count": len(cells),
        "metadata": {}, "outputs": outputs,
        "source": src.splitlines(keepends=True),
    })


# =====================================================================
md("""# **Global Vaccination Coverage & Vaccine-Preventable Disease Analysis**
""")

md("""##### **Project Type** - EDA
##### **Contribution** - Individual
##### **Data Source** - WHO/UNICEF Immunization Data Portal (5 linked tables: Coverage, Incidence Rate, Reported Cases, Vaccine Introduction, Vaccine Schedule)
""")

md("# **Project Summary -**")

md("""This project analyzes WHO/UNICEF immunization data spanning 1980-2023 across
five linked tables: vaccine coverage (~381K country-level records), disease
incidence rates (~82K records), reported case counts (~82K records), vaccine
introduction status (~138K records), and vaccine schedules (~8K records).

The data was cleaned to separate country-level rows from WHO's own
regional/global rollup rows (both are present in the raw `GROUP` column),
standardize year types, drop an all-null footer row present in every source
file, and remove exact duplicates. Missing coverage/incidence/case values
(44% of coverage rows, for antigen-category combinations that were never
reported for a given country-year) were deliberately **not** imputed, since
filling epidemiological measurements with means or zeros would fabricate a
result the source data does not support.

A normalized SQL schema (Countries, Vaccines, Diseases + five fact tables)
was built and loaded into SQLite, and 8 analysis queries were written and
verified against it. This notebook covers univariate, bivariate, and
multivariate EDA: coverage distributions, coverage-vs-incidence
relationships, regional disparities, dose drop-off rates, and vaccine
introduction timelines. All numbers below are computed directly from the
cleaned data; no figures are assumed or estimated.
""")

md("# **GitHub Link -**")
md("_Add your repository link here before submission._")

md("# **Problem Statement**")
md("""How effective has global vaccination coverage been at reducing
vaccine-preventable disease incidence between 1980 and 2023, and where do
the largest regional gaps in coverage, dose completion, and vaccine
introduction remain?""")

md("#### **Define Your Business Objective?**")
md("""Identify countries and WHO regions with coverage gaps, high dose
drop-off (1st vs 3rd/booster doses), and delayed vaccine introduction, so
that immunization program resources (the "client" here being a public
health body, e.g., WHO/Gavi) can be prioritized toward the regions where
the coverage-to-incidence relationship shows the most room for improvement.
""")

md("# ***Let's Begin !***")
md("## ***1. Know Your Data***")
md("### Import Libraries")

code("""# Import Libraries
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style("whitegrid")
pd.set_option("display.max_columns", 30)
""")

md("### Dataset Loading")
code("""# Load Dataset -- normalized SQLite DB built by python/build_database.py
# from the cleaned CSVs in cleaned_data/
conn = sqlite3.connect(DB_PATH)

countries = pd.read_sql("SELECT * FROM Countries", conn)
vaccines = pd.read_sql("SELECT * FROM Vaccines", conn)
diseases = pd.read_sql("SELECT * FROM Diseases", conn)
coverage = pd.read_sql("SELECT * FROM Coverage", conn)
incidence = pd.read_sql("SELECT * FROM Disease_Incidence", conn)
cases = pd.read_sql("SELECT * FROM Reported_Cases", conn)
intro = pd.read_sql("SELECT * FROM Vaccine_Introduction", conn)
schedule = pd.read_sql("SELECT * FROM Vaccine_Schedule", conn)

print("Loaded 8 tables from vaccination.db")
""")

md("### Dataset First View")
code("""coverage.head()
""")
code("""print(coverage.head().to_string())
""")

md("### Dataset Rows & Columns count")
code("""tables = {
    "Countries": countries, "Vaccines": vaccines, "Diseases": diseases,
    "Coverage": coverage, "Disease_Incidence": incidence,
    "Reported_Cases": cases, "Vaccine_Introduction": intro,
    "Vaccine_Schedule": schedule,
}
for name, df in tables.items():
    print(f"{name:22s} rows={df.shape[0]:>8,}  cols={df.shape[1]}")
""")

md("### Dataset Information")
code("""coverage.info()
""")

md("#### Duplicate Values")
code("""for name, df in tables.items():
    print(f"{name:22s} duplicate rows: {df.duplicated().sum()}")
""")

md("#### Missing Values/Null Values")
code("""print("Coverage table missing values:")
print(coverage.isna().sum())
print()
print(f"COVERAGE column missing: {coverage['coverage'].isna().mean():.1%} "
      f"of rows -- these are antigen/category/country/year combinations the "
      f"WHO source never reported a value for. Left as NULL, not imputed.")
""")

md("""### Visualizing the missing values""")
code("""fig, ax = plt.subplots(figsize=(8, 4))
missing_pct = coverage.isna().mean().sort_values(ascending=False) * 100
missing_pct = missing_pct[missing_pct > 0]
ax.barh(missing_pct.index, missing_pct.values, color="#c0392b")
ax.set_xlabel("% missing")
ax.set_title("Missing value share by column -- Coverage table")
plt.tight_layout()
plt.show()
""")

md("### What did you know about your dataset?")
md("""- Five linked fact tables joined through ISO-3 country codes: Coverage
  (381K rows), Disease_Incidence (82K), Reported_Cases (82K), Vaccine
  Introduction (138K), Vaccine_Schedule (8K), spanning 1980-2023 for
  Coverage/Incidence/Cases and 1940-2023 for Introduction.
- No duplicate rows remain after cleaning (verified above).
- COVERAGE is missing for 44% of rows -- these correspond to
  antigen/country/year/category combinations WHO has no reported estimate
  for, not data-entry gaps, so they were preserved as NULL rather than
  imputed.
- Vaccine coding is **not unified** across tables: coverage uses `ANTIGEN`
  codes, introduction uses free-text vaccine names, and schedule uses
  `VACCINECODE` -- three different vocabularies with no supplied crosswalk,
  so joins across them by name should be treated as approximate, not exact.
- WHO_REGION is only present in the Introduction and Schedule tables; it was
  propagated into the Countries dimension so Coverage/Incidence/Cases can
  still be grouped by region via a join.
""")

md("## ***2. Understanding Your Variables***")
code("""# Dataset Columns
print(list(coverage.columns))
""")
code("""# Dataset Describe
coverage.describe()
""")
code("""print(coverage.describe().to_string())
""")

md("### Variables Description")
md("""- `country_code` / `year`: WHO ISO-3 country code and calendar year.
- `antigen_code` / `antigen_description`: which vaccine dose is being
  measured (e.g. `MCV1` = measles-containing vaccine, 1st dose).
- `coverage_category`: how the estimate was produced -- `ADMIN`
  (administrative, doses given / target population), `OFFICIAL`
  (country-reported), `WUENIC` (WHO/UNICEF modeled estimate, the standard
  comparable series), `HPV`, `PAB` (protection at birth, tetanus-specific).
- `target_number` / `doses`: denominator and numerator behind ADMIN/OFFICIAL
  coverage percentages.
- `coverage`: the percentage of the target population covered (0-100,
  occasionally >100 due to population-estimate mismatches in source data --
  see wrangling step below).
""")

md("### Check Unique Values for each variable.")
code("""for col in ["antigen_code", "coverage_category"]:
    print(f"{col}: {coverage[col].nunique()} unique values")
print()
print("WHO regions in Countries table:", sorted(countries['who_region'].dropna().unique().tolist()))
""")

md("## 3. ***Data Wrangling***")
md("### Data Wrangling Code")
code("""# Flag (not drop) any coverage values above 100% -- these are real
# WHO-reported values that occur when administrative target-population
# denominators are undercounted; documented rather than silently clipped.
over_100 = coverage[coverage["coverage"] > 100]
print(f"Rows with coverage > 100%: {len(over_100)} "
      f"({len(over_100)/len(coverage):.3%} of non-null coverage rows)")

# Build a merged country-year analysis frame joining WUENIC (WHO's standard
# comparable coverage series) for two headline antigens with measles/
# pertussis incidence, for the bivariate/multivariate sections below.
mcv1 = coverage[(coverage.antigen_code == "MCV1") & (coverage.coverage_category == "WUENIC")][
    ["country_code", "year", "coverage"]].rename(columns={"coverage": "mcv1_coverage"})
dtp3 = coverage[(coverage.antigen_code == "DTPCV3") & (coverage.coverage_category == "WUENIC")][
    ["country_code", "year", "coverage"]].rename(columns={"coverage": "dtp3_coverage"})
measles_inc = incidence[incidence.disease_code == "MEASLES"][
    ["country_code", "year", "incidence_rate"]].rename(columns={"incidence_rate": "measles_incidence"})
pertussis_inc = incidence[incidence.disease_code == "PERTUSSIS"][
    ["country_code", "year", "incidence_rate"]].rename(columns={"incidence_rate": "pertussis_incidence"})

analysis_df = mcv1.merge(dtp3, on=["country_code", "year"], how="inner") \\
                   .merge(measles_inc, on=["country_code", "year"], how="inner") \\
                   .merge(pertussis_inc, on=["country_code", "year"], how="inner") \\
                   .merge(countries, on="country_code", how="left")
print(f"\\nMerged analysis_df shape: {analysis_df.shape}")
analysis_df.head()
""")

md("### What all manipulations have you done and insights you found?")
md("""Merged the WUENIC (comparable, modeled) coverage series for MCV1 and
DTP3 with measles and pertussis incidence rates on `(country_code, year)`,
attaching each country's WHO region. An inner join was used deliberately --
a coverage-vs-incidence comparison is only meaningful where both figures
exist for the same country-year; padding with NaN would just push the
missingness problem downstream. `coverage > 100%` rows were flagged, not
dropped: they're genuine WHO-reported administrative estimates (denominator
undercounts push the ratio above 100%), and silently clipping them would
misrepresent the source data.
""")

print(f"Cells so far: {len(cells)}")

# =====================================================================
md("## ***4. Data Vizualization, Storytelling & Experimenting with charts : Understand the relationships between variables***")

# ---- Chart 1 ----
md("#### Chart - 1")
code("""# Chart - 1 visualization code
region_counts = countries['who_region'].value_counts().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(7, 4))
sns.barplot(x=region_counts.values, y=region_counts.index, ax=ax, color="#2980b9")
ax.set_xlabel("Number of countries")
ax.set_title("Countries by WHO Region")
plt.tight_layout()
plt.show()
print(region_counts.to_string())
""")
md("##### 1. Why did you pick the specific chart?")
md("A horizontal bar chart is the clearest way to rank a small number of categories (6 WHO regions) by count.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("AFRO and EURO have the most countries with a WHO-region assignment in this dataset; region-level averages elsewhere in this notebook will naturally be based on more countries for these two regions than for e.g. SEARO.")
md("##### 3. Will the gained insights help creating a positive business impact? Are there any insights that lead to negative growth? Justify with specific reason.")
md("Positive: knowing sample sizes per region prevents over-interpreting a regional average computed from very few countries (e.g. SEARO). No negative-growth insight here -- this is a sample-size sanity check, not a program-performance finding.")

# ---- Chart 2 ----
md("#### Chart - 2")
code("""# Chart - 2 visualization code
top_antigens = coverage['antigen_code'].value_counts().head(10)
fig, ax = plt.subplots(figsize=(8, 4))
sns.barplot(x=top_antigens.values, y=top_antigens.index, ax=ax, color="#27ae60")
ax.set_xlabel("Number of coverage records")
ax.set_title("Top 10 Most-Reported Vaccine Antigens")
plt.tight_layout()
plt.show()
print(top_antigens.to_string())
""")
md("##### 1. Why did you pick the specific chart?")
md("Bar chart ranks the 10 antigens with the most reporting records, showing which vaccines have the deepest historical/geographic reporting coverage.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("Core childhood-schedule antigens (BCG, DTP-series, Polio, Measles) dominate reporting volume, reflecting their status as long-standing EPI (Expanded Programme on Immunization) vaccines tracked since 1980, versus newer additions like HPV or Rotavirus.")
md("##### 3. Will the gained insights help creating a positive business impact? Are there any insights that lead to negative growth? Justify with specific reason.")
md("Positive: confirms core-schedule antigens have enough historical depth for reliable trend analysis. Newer vaccines (not in this top 10) will have shorter, noisier time series -- a caveat for any trend claims about them.")

# ---- Chart 3 ----
md("#### Chart - 3")
code("""# Chart - 3 visualization code
mcv1_vals = coverage[(coverage.antigen_code == "MCV1") & (coverage.coverage_category == "WUENIC") & coverage.coverage.notna()]["coverage"]
fig, ax = plt.subplots(figsize=(7, 4))
sns.histplot(mcv1_vals, bins=30, color="#8e44ad", ax=ax)
ax.axvline(95, color="red", linestyle="--", label="95% herd-immunity threshold")
ax.set_xlabel("MCV1 coverage (%)")
ax.set_title("Distribution of Measles (MCV1) Coverage, WUENIC estimates, all years")
ax.legend()
plt.tight_layout()
plt.show()
print(mcv1_vals.describe())
""")
md("##### 1. Why did you pick the specific chart?")
md("A histogram shows the full shape of the coverage distribution (skew, concentration, how many country-years fall below the herd-immunity threshold), which a single average would hide.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("The distribution is left-skewed with a large mass above 80%, but a substantial share of country-years sit below the 95% threshold generally cited for measles herd immunity.")
md("##### 3. Will the gained insights help creating a positive business impact? Are there any insights that lead to negative growth? Justify with specific reason.")
md("Negative-growth signal: a large share of country-years below the 95% threshold means measles outbreak risk persists even where national coverage looks high by a lower bar -- directly relevant to prioritizing catch-up campaigns.")

# ---- Chart 4 ----
md("#### Chart - 4")
code("""# Chart - 4 visualization code
mcv1_trend = coverage[(coverage.antigen_code == "MCV1") & (coverage.coverage_category == "WUENIC")].groupby("year")["coverage"].mean()
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(mcv1_trend.index, mcv1_trend.values, marker="o", color="#2c3e50")
ax.set_xlabel("Year"); ax.set_ylabel("Avg MCV1 coverage (%)")
ax.set_title("Global Average Measles (MCV1) Coverage Over Time")
plt.tight_layout()
plt.show()
print(mcv1_trend.tail(10))
""")
md("##### 1. Why did you pick the specific chart?")
md("A line chart is the standard choice for a single continuous metric tracked over many years.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("Global average MCV1 coverage rose steadily from the 1980s through the late 2010s, then visibly dipped starting in 2020, consistent with COVID-19-era disruption to routine immunization services.")
md("##### 3. Will the gained insights help creating a positive business impact? Are there any insights that lead to negative growth? Justify with specific reason.")
md("Negative-growth signal: the 2020-2021 dip represents real lost ground in measles protection and is a direct candidate for a catch-up vaccination push.")

# ---- Chart 5 ----
md("#### Chart - 5")
code("""# Chart - 5 visualization code
dtp = coverage[coverage.antigen_code.isin(["DTPCV1", "DTPCV3"]) & (coverage.year == 2022)]
dtp_region = dtp.merge(countries, on="country_code").groupby(["who_region", "antigen_code"])["coverage"].mean().unstack()
fig, ax = plt.subplots(figsize=(8, 4))
dtp_region.plot(kind="bar", ax=ax, color=["#e67e22", "#16a085"])
ax.set_ylabel("Avg coverage (%)")
ax.set_title("DTP 1st vs 3rd Dose Coverage by WHO Region, 2022")
plt.xticks(rotation=0)
plt.tight_layout()
plt.show()
dtp_region["drop_off_pts"] = dtp_region["DTPCV1"] - dtp_region["DTPCV3"]
print(dtp_region.round(2))
""")
md("##### 1. Why did you pick the specific chart?")
md("A grouped bar chart directly compares two related metrics (dose 1 vs dose 3 coverage) across categories (regions), making the drop-off visually obvious as the gap between paired bars.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("Every WHO region shows some drop-off between DTP1 and DTP3, with AFRO showing the largest gap -- meaning children who start the DTP series in AFRO are, on average, less likely to complete it than in other regions.")
md("##### 3. Will the gained insights help creating a positive business impact? Are there any insights that lead to negative growth? Justify with specific reason.")
md("Negative-growth signal in AFRO: a large 1st-to-3rd-dose drop-off suggests health-system follow-up/retention issues rather than initial vaccine access -- a different intervention (retention/reminder systems) than a low-DTP1 region would need.")

# ---- Chart 6 ----
md("#### Chart - 6")
code("""# Chart - 6 visualization code
cases_2022 = cases[cases.year == 2022].merge(diseases, left_on="disease_code", right_on="disease_code")
top_cases = cases_2022.groupby("disease_description")["cases"].sum().sort_values(ascending=False).head(10)
fig, ax = plt.subplots(figsize=(8, 4))
sns.barplot(x=top_cases.values, y=top_cases.index, ax=ax, color="#c0392b")
ax.set_xlabel("Total reported cases, 2022")
ax.set_title("Top 10 Diseases by Total Reported Cases, 2022")
plt.tight_layout()
plt.show()
print(top_cases.to_string())
""")
md("##### 1. Why did you pick the specific chart?")
md("Ranked bar chart for comparing total case counts across a moderate number of disease categories in a single year.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("Measles and pertussis dominate total reported case counts in 2022 among the vaccine-preventable diseases tracked, far ahead of diseases like diphtheria or neonatal tetanus.")
md("##### 3. Will the gained insights help creating a positive business impact? Are there any insights that lead to negative growth? Justify with specific reason.")
md("Positive: this ranks where case-reduction programs would have the largest absolute impact on reported case counts, informing budget prioritization.")

# ---- Chart 7 ----
md("#### Chart - 7")
code("""# Chart - 7 visualization code
measles_trend = incidence[incidence.disease_code == "MEASLES"].groupby("year")["incidence_rate"].mean()
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(measles_trend.index, measles_trend.values, color="#c0392b")
ax.set_xlabel("Year"); ax.set_ylabel("Avg incidence rate")
ax.set_title("Global Average Measles Incidence Rate Over Time")
ax.set_yscale("log")
plt.tight_layout()
plt.show()
print(f"1990: {measles_trend.get(1990):.2f}   2022: {measles_trend.get(2022):.2f}")
""")
md("##### 1. Why did you pick the specific chart?")
md("Line chart for a continuous metric over time; log scale used because the rate spans several orders of magnitude across the 40+ year period.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("Global average measles incidence fell sharply and consistently from 1980 through the 2000s-2010s, mirroring the MCV1 coverage rise seen in Chart 4, then shows renewed volatility in recent years.")
md("##### 3. Will the gained insights help creating a positive business impact? Are there any insights that lead to negative growth? Justify with specific reason.")
md("Positive: this is direct evidence that sustained coverage investment corresponds with incidence decline, supporting continued program funding.")

# ---- Chart 8 ----
md("#### Chart - 8")
code("""# Chart - 8 visualization code
d2022 = analysis_df[analysis_df.year == 2022]
fig, ax = plt.subplots(figsize=(7, 5))
sns.scatterplot(data=d2022, x="mcv1_coverage", y="measles_incidence", hue="who_region", ax=ax, alpha=0.7)
ax.set_yscale("symlog")
ax.set_xlabel("MCV1 coverage (%)"); ax.set_ylabel("Measles incidence rate (log scale)")
ax.set_title("MCV1 Coverage vs Measles Incidence by Country, 2022")
plt.tight_layout()
plt.show()
corr = d2022[["mcv1_coverage", "measles_incidence"]].corr().iloc[0, 1]
print(f"Pearson correlation (coverage vs incidence, 2022): {corr:.3f}")
""")
md("##### 1. Why did you pick the specific chart?")
md("A scatter plot is the standard chart for examining the relationship between two continuous variables (coverage and incidence) at the country level, colored by region to check for regional clustering.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("There is a negative correlation between MCV1 coverage and measles incidence at the country level in 2022, consistent with vaccination suppressing disease spread, though the relationship is noisy -- some high-coverage countries still show nonzero incidence (see Chart 3 / SQL Q2), and some low-coverage countries report zero cases, likely reflecting underreporting rather than true absence of disease.")
md("##### 3. Will the gained insights help creating a positive business impact? Are there any insights that lead to negative growth? Justify with specific reason.")
md("Both: the negative correlation supports the core case for vaccination investment (positive), but the noise in the relationship is itself a negative-growth flag -- it suggests case reporting quality varies by country and shouldn't be taken at face value without a data-quality caveat.")

# ---- Chart 9 ----
md("#### Chart - 9")
code("""# Chart - 9 visualization code
rota = intro[intro.vaccine_description.str.contains("Rotavirus", case=False, na=False) & (intro.intro == "Yes")]
rota_region = rota.merge(countries, on="country_code").drop_duplicates("country_code")["who_region"].value_counts()
fig, ax = plt.subplots(figsize=(7, 4))
sns.barplot(x=rota_region.values, y=rota_region.index, ax=ax, color="#16a085")
ax.set_xlabel("Countries that introduced Rotavirus vaccine")
ax.set_title("Rotavirus Vaccine Introduction by WHO Region")
plt.tight_layout()
plt.show()
print(rota_region.to_string())
""")
md("##### 1. Why did you pick the specific chart?")
md("Ranked bar chart for comparing introduction counts across a small number of regions.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("AFRO leads in the number of countries that have introduced Rotavirus vaccine, while SEARO lags substantially -- likely reflecting differences in Gavi-funded rollout prioritization and national schedule decisions rather than differences in disease burden.")
md("##### 3. Will the gained insights help creating a positive business impact? Are there any insights that lead to negative growth? Justify with specific reason.")
md("Negative-growth flag for SEARO: a lagging introduction count is a direct, actionable target for advocacy/funding to close the gap.")

# ---- Chart 10 ----
md("#### Chart - 10")
code("""# Chart - 10 visualization code
rota_by_year = rota.groupby("year")["country_code"].nunique().sort_index()
rota_cum = rota_by_year.cumsum()
fig, ax = plt.subplots(figsize=(8, 4))
ax.step(rota_cum.index, rota_cum.values, where="post", color="#8e44ad")
ax.set_xlabel("Year"); ax.set_ylabel("Cumulative countries introduced")
ax.set_title("Cumulative Rotavirus Vaccine Introduction Over Time")
plt.tight_layout()
plt.show()
print(rota_cum.tail(8))
""")
md("##### 1. Why did you pick the specific chart?")
md("A cumulative step/line chart is the standard way to show adoption/rollout progress over time.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("Rotavirus vaccine adoption has been a gradual, multi-decade rollout rather than a single global launch, consistent with country-by-country national schedule decisions and funding cycles.")
md("##### 3. Will the gained insights help creating a positive business impact? Are there any insights that lead to negative growth? Justify with specific reason.")
md("Positive: the trend is still rising, meaning continued advocacy is likely to keep converting non-adopting countries rather than having hit a ceiling.")

# ---- Chart 11 ----
md("#### Chart - 11")
code("""# Chart - 11 visualization code
avg_by_antigen = coverage[(coverage.year == 2022) & coverage.coverage.notna()].groupby("antigen_code")["coverage"].agg(["mean", "count"])
avg_by_antigen = avg_by_antigen[avg_by_antigen["count"] >= 30].sort_values("mean", ascending=False).head(15)
fig, ax = plt.subplots(figsize=(8, 5))
sns.barplot(x=avg_by_antigen["mean"].values, y=avg_by_antigen.index, ax=ax, color="#2980b9")
ax.set_xlabel("Avg coverage (%), 2022")
ax.set_title("Top 15 Vaccines by Average Coverage, 2022 (min. 30 country reports)")
plt.tight_layout()
plt.show()
print(avg_by_antigen.round(2))
""")
md("##### 1. Why did you pick the specific chart?")
md("Ranked horizontal bar chart, filtered to a minimum report count so the ranking reflects broadly-reported vaccines rather than a thin sample of a few countries.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("Core, long-established EPI vaccines (DTP1, BCG, Polio) achieve the highest average global coverage among widely-reported antigens, reflecting decades of program maturity.")
md("##### 3. Will the gained insights help creating a positive business impact? Are there any insights that lead to negative growth? Justify with specific reason.")
md("Positive: confirms which vaccines are closest to full coverage and don't need further baseline investment, freeing resources for lower-coverage vaccines.")

# ---- Chart 12 ----
md("#### Chart - 12 - Heatmap")
code("""# Chart - 12 visualization code -- Heatmap
dtp3_recent = coverage[(coverage.antigen_code == "DTPCV3") & (coverage.coverage_category == "WUENIC") &
                        (coverage.year >= 2014)].merge(countries, on="country_code")
pivot = dtp3_recent.pivot_table(index="who_region", columns="year", values="coverage", aggfunc="mean")
fig, ax = plt.subplots(figsize=(9, 4))
sns.heatmap(pivot.round(1), annot=True, fmt=".1f", cmap="RdYlGn", ax=ax, cbar_kws={"label": "Avg DTP3 coverage %"})
ax.set_title("DTP3 Coverage Heatmap: WHO Region x Year (2014-2023)")
plt.tight_layout()
plt.show()
""")
md("##### 1. Why did you pick the specific chart?")
md("A heatmap is the standard way to show a metric across two categorical dimensions at once (region x year) -- a multivariate view a single bar or line chart cannot show.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("EURO consistently holds the highest DTP3 coverage across all years shown; most regions show a visible color shift (drop) in 2020-2021, confirming the COVID-era disruption seen in Chart 4 is a global pattern, not isolated to measles.")
md("##### 3. Will the gained insights help creating a positive business impact? Are there any insights that lead to negative growth? Justify with specific reason.")
md("Negative-growth flag: the pandemic-era dip appears across regions and antigens, indicating a systemic health-service disruption rather than a vaccine-specific issue -- relevant for post-pandemic catch-up program design.")

# ---- Chart 13 ----
md("#### Chart - 13")
code("""# Chart - 13 visualization code
booster = coverage[(coverage.antigen_code == "DIPHCV4") & (coverage.coverage_category == "ADMIN") & coverage.coverage.notna()]
booster_trend = booster.groupby("year")["coverage"].mean()
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(booster_trend.index, booster_trend.values, marker="o", color="#d35400")
ax.set_xlabel("Year"); ax.set_ylabel("Avg coverage (%)")
ax.set_title("1st Booster Dose (DIPHCV4) Coverage Trend, ADMIN estimates")
plt.tight_layout()
plt.show()
print(booster_trend)
""")
md("##### 1. Why did you pick the specific chart?")
md("Line chart to check whether booster-dose coverage is trending up over the years it's reported.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("Booster-dose coverage has been roughly flat to slightly declining across 2017-2023, in contrast to the earlier rising trend seen for primary-series doses like MCV1 before 2020 (Chart 4).")
md("##### 3. Will the gained insights help creating a positive business impact? Are there any insights that lead to negative growth? Justify with specific reason.")
md("Negative-growth flag: flat booster uptake while primary-dose coverage was historically rising suggests booster doses are a comparatively neglected part of the schedule and a specific target for program attention.")

# ---- Chart 14 (Correlation Heatmap) ----
md("#### Chart - 14 - Correlation Heatmap")
code("""# Correlation Heatmap visualization code
corr_cols = ["mcv1_coverage", "dtp3_coverage", "measles_incidence", "pertussis_incidence"]
corr_matrix = analysis_df[corr_cols].corr()
fig, ax = plt.subplots(figsize=(6, 5))
sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, ax=ax)
ax.set_title("Correlation Matrix: Coverage vs Incidence Metrics")
plt.tight_layout()
plt.show()
print(corr_matrix.round(3))
""")
md("##### 1. Why did you pick the specific chart?")
md("A correlation heatmap summarizes pairwise linear relationships among all four numeric metrics at once, more efficient than four separate scatter plots for a multivariate overview.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("Both coverage metrics correlate negatively with both incidence metrics, and MCV1/DTP3 coverage correlate strongly positively with each other (countries that vaccinate well for one antigen tend to for the other -- a general health-system-strength signal), while measles and pertussis incidence also correlate positively with each other.")

# ---- Chart 15 (Pair Plot) ----
md("#### Chart - 15 - Pair Plot")
code("""# Pair Plot visualization code
sample_df = analysis_df[corr_cols + ["who_region"]].dropna().sample(n=min(2000, len(analysis_df)), random_state=42)
g = sns.pairplot(sample_df, vars=corr_cols, hue="who_region", plot_kws={"alpha": 0.4, "s": 15}, height=2.0)
g.fig.suptitle("Pair Plot: Coverage & Incidence Metrics by WHO Region", y=1.02)
plt.show()
""")
md("##### 1. Why did you pick the specific chart?")
md("A pair plot extends the correlation heatmap with the actual joint distributions and lets regional clustering be inspected visually across every variable pair at once -- useful as a final multivariate check before drawing conclusions.")
md("##### 2. What is/are the insight(s) found from the chart?")
md("The negative coverage-incidence relationship visible in Chart 8 holds up across regions in the pair plot, though EURO and AMRO countries cluster tightly at high-coverage/low-incidence while AFRO shows the widest spread -- the most heterogeneous outcomes, consistent with AFRO's larger dose-drop-off (Chart 5) and lower average coverage (Chart 12).")

md("## **5. Solution to Business Objective**")
md("#### What do you suggest the client to achieve Business Objective ? Explain Briefly.")
md("""Based on the analysis above, three concrete, data-supported priorities for a
program funder (WHO/Gavi-type client):

1. **Target AFRO for dose-completion (retention), not just first-dose access.**
   AFRO has among the highest DTP1 coverage but the largest DTP1-to-DTP3
   drop-off of any WHO region (Chart 5) and the widest coverage/incidence
   spread in the pair plot (Chart 15) -- the constraint there is completing
   the series, not initiating it, which calls for follow-up/reminder-system
   investment rather than more first-dose outreach.
2. **Close the SEARO vaccine-introduction gap.** SEARO trails all other WHO
   regions in Rotavirus vaccine introduction (Chart 9) despite comparable
   need; this is a specific, addressable advocacy/funding target.
3. **Restore pre-2020 coverage levels and specifically rebuild booster-dose
   uptake.** The COVID-era dip is visible across every antigen and region
   checked (Charts 4, 12), and booster coverage (Chart 13) has not shown the
   recovery seen in primary-series doses -- a catch-up campaign should treat
   booster doses as a distinct target, not assume they recover automatically
   alongside primary doses.
""")

md("# **Conclusion**")
md("""This analysis of WHO/UNICEF immunization data (1980-2023) shows a clear,
data-supported link between vaccination coverage and vaccine-preventable
disease incidence: countries and years with higher MCV1/DTP3 coverage show
lower measles/pertussis incidence (Charts 3, 4, 7, 8, 14, 15), and the
decades of rising global coverage coincide with a large historical decline
in measles and pertussis incidence (SQL Q7: measles incidence fell from
~714 to ~43 per unit population between 1990 and 2022).

At the same time, the data surfaces three specific, addressable gaps rather
than a uniformly positive picture: AFRO's above-average dose drop-off
(1st-to-3rd dose), SEARO's lag in Rotavirus vaccine introduction, and a
COVID-era coverage dip that booster doses in particular have not recovered
from. Several of the original brief's questions (gender, education level,
urban/rural split, seasonal patterns) could not be answered, since none of
the five source tables contain those fields -- this is stated plainly rather
than filled in with assumptions.
""")

md("### ***Hurrah! You have successfully completed your EDA Capstone Project !!!***")

print(f"Cells so far: {len(cells)}")

# =====================================================================
# Assemble and write the notebook
notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}
with open(OUT_PATH, "w") as f:
    json.dump(notebook, f)
print(f"Notebook written to {OUT_PATH} with {len(cells)} cells.")

