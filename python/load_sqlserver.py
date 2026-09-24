import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path

# ---- EDIT THESE ----
SERVER = "localhost"                 # or "YOUR_SERVER\\SQLEXPRESS"
DATABASE = "VaccinationAnalysis"
DRIVER = "ODBC Driver 17 for SQL Server"
# Windows auth (recommended for local SQL Server Express):
CONN_STR = f"mssql+pyodbc://@{SERVER}/{DATABASE}?driver={DRIVER.replace(' ', '+')}&trusted_connection=yes"
# If you use SQL auth instead, use this form:
# USERNAME, PASSWORD = "sa", "your_password"
# CONN_STR = f"mssql+pyodbc://{USERNAME}:{PASSWORD}@{SERVER}/{DATABASE}?driver={DRIVER.replace(' ', '+')}"
# ---------------------

CLEAN_DIR = Path(__file__).resolve().parent.parent / "cleaned_data"

engine = create_engine(CONN_STR, fast_executemany=True)

coverage = pd.read_csv(CLEAN_DIR / "coverage_country.csv")
incidence = pd.read_csv(CLEAN_DIR / "incidence_country.csv")
cases = pd.read_csv(CLEAN_DIR / "cases_country.csv")
intro = pd.read_csv(CLEAN_DIR / "vaccine_introduction.csv")
schedule = pd.read_csv(CLEAN_DIR / "vaccine_schedule.csv")

# --- Countries dimension ---
c1 = coverage[["CODE", "NAME"]].rename(columns={"CODE": "country_code", "NAME": "country_name"})
c2 = intro[["ISO_3_CODE", "COUNTRYNAME", "WHO_REGION"]].rename(
    columns={"ISO_3_CODE": "country_code", "COUNTRYNAME": "country_name", "WHO_REGION": "who_region"})
who_region_map = c2[["country_code", "who_region"]].dropna().drop_duplicates("country_code")
countries = c1.dropna().drop_duplicates("country_code").merge(who_region_map, on="country_code", how="left")
countries.to_sql("Countries", engine, if_exists="append", index=False)
print(f"Loaded {len(countries)} Countries")

# --- Diseases dimension ---
diseases = incidence[["DISEASE", "DISEASE_DESCRIPTION"]].drop_duplicates().dropna()
diseases.columns = ["disease_code", "disease_description"]
diseases.to_sql("Diseases", engine, if_exists="append", index=False)
print(f"Loaded {len(diseases)} Diseases")

# --- Vaccines dimension (source-tagged, see build_database.py for why) ---
v1 = coverage[["ANTIGEN", "ANTIGEN_DESCRIPTION"]].drop_duplicates().dropna()
v1.columns = ["vaccine_code", "vaccine_description"]; v1["source"] = "COVERAGE_ANTIGEN"
v2 = schedule[["VACCINECODE", "VACCINE_DESCRIPTION"]].drop_duplicates().dropna()
v2.columns = ["vaccine_code", "vaccine_description"]; v2["source"] = "SCHEDULE"
vaccines = pd.concat([v1, v2], ignore_index=True)
vaccines.to_sql("Vaccines", engine, if_exists="append", index=False)
print(f"Loaded {len(vaccines)} Vaccines")

# --- Fact tables ---
cov_fact = coverage.rename(columns={
    "CODE": "country_code", "YEAR": "year", "ANTIGEN": "antigen_code",
    "ANTIGEN_DESCRIPTION": "antigen_description", "COVERAGE_CATEGORY": "coverage_category",
    "COVERAGE_CATEGORY_DESCRIPTION": "coverage_category_description",
    "TARGET_NUMBER": "target_number", "DOSES": "doses", "COVERAGE": "coverage",
})[["country_code", "year", "antigen_code", "antigen_description", "coverage_category",
    "coverage_category_description", "target_number", "doses", "coverage"]]
cov_fact.to_sql("Coverage", engine, if_exists="append", index=False, chunksize=5000)
print(f"Loaded {len(cov_fact)} Coverage rows")

inc_fact = incidence.rename(columns={
    "CODE": "country_code", "YEAR": "year", "DISEASE": "disease_code",
    "DENOMINATOR": "denominator", "INCIDENCE_RATE": "incidence_rate",
})[["country_code", "year", "disease_code", "denominator", "incidence_rate"]]
inc_fact.to_sql("Disease_Incidence", engine, if_exists="append", index=False, chunksize=5000)
print(f"Loaded {len(inc_fact)} Disease_Incidence rows")

cases_fact = cases.rename(columns={
    "CODE": "country_code", "YEAR": "year", "DISEASE": "disease_code", "CASES": "cases",
})[["country_code", "year", "disease_code", "cases"]]
cases_fact.to_sql("Reported_Cases", engine, if_exists="append", index=False, chunksize=5000)
print(f"Loaded {len(cases_fact)} Reported_Cases rows")

intro_fact = intro.rename(columns={
    "ISO_3_CODE": "country_code", "YEAR": "year",
    "DESCRIPTION": "vaccine_description", "INTRO": "intro",
})[["country_code", "year", "vaccine_description", "intro"]]
intro_fact.to_sql("Vaccine_Introduction", engine, if_exists="append", index=False, chunksize=5000)
print(f"Loaded {len(intro_fact)} Vaccine_Introduction rows")

sched_fact = schedule.rename(columns={
    "ISO_3_CODE": "country_code", "YEAR": "year", "VACCINECODE": "vaccine_code",
    "VACCINE_DESCRIPTION": "vaccine_description", "SCHEDULEROUNDS": "schedule_rounds",
    "TARGETPOP": "targetpop", "TARGETPOP_DESCRIPTION": "targetpop_description",
    "GEOAREA": "geoarea", "AGEADMINISTERED": "age_administered", "SOURCECOMMENT": "source_comment",
})[["country_code", "year", "vaccine_code", "vaccine_description", "schedule_rounds",
    "targetpop", "targetpop_description", "geoarea", "age_administered", "source_comment"]]
sched_fact.to_sql("Vaccine_Schedule", engine, if_exists="append", index=False, chunksize=5000)
print(f"Loaded {len(sched_fact)} Vaccine_Schedule rows")

print("\nDone. All tables loaded into SQL Server.")
