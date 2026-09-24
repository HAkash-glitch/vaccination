import sqlite3
import pandas as pd
from pathlib import Path

CLEAN_DIR = Path(__file__).resolve().parent.parent / "cleaned_data"
DB_PATH = Path(__file__).resolve().parent.parent / "sql" / "vaccination.db"

SCHEMA = """
DROP TABLE IF EXISTS Coverage;
DROP TABLE IF EXISTS Disease_Incidence;
DROP TABLE IF EXISTS Reported_Cases;
DROP TABLE IF EXISTS Vaccine_Introduction;
DROP TABLE IF EXISTS Vaccine_Schedule;
DROP TABLE IF EXISTS Vaccines;
DROP TABLE IF EXISTS Diseases;
DROP TABLE IF EXISTS Countries;

CREATE TABLE Countries (
    country_code TEXT PRIMARY KEY,
    country_name TEXT,
    who_region   TEXT
);

CREATE TABLE Vaccines (
    vaccine_code TEXT,
    vaccine_description TEXT,
    source TEXT,               -- 'COVERAGE_ANTIGEN' | 'INTRODUCTION' | 'SCHEDULE'
    PRIMARY KEY (vaccine_code, source)
);

CREATE TABLE Diseases (
    disease_code TEXT PRIMARY KEY,
    disease_description TEXT
);

CREATE TABLE Coverage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT,
    year INTEGER,
    antigen_code TEXT,
    antigen_description TEXT,
    coverage_category TEXT,
    coverage_category_description TEXT,
    target_number REAL,
    doses REAL,
    coverage REAL,
    FOREIGN KEY (country_code) REFERENCES Countries(country_code)
);

CREATE TABLE Disease_Incidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT,
    year INTEGER,
    disease_code TEXT,
    denominator TEXT,
    incidence_rate REAL,
    FOREIGN KEY (country_code) REFERENCES Countries(country_code),
    FOREIGN KEY (disease_code) REFERENCES Diseases(disease_code)
);

CREATE TABLE Reported_Cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT,
    year INTEGER,
    disease_code TEXT,
    cases REAL,
    FOREIGN KEY (country_code) REFERENCES Countries(country_code),
    FOREIGN KEY (disease_code) REFERENCES Diseases(disease_code)
);

CREATE TABLE Vaccine_Introduction (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT,
    year INTEGER,
    vaccine_description TEXT,
    intro TEXT,
    FOREIGN KEY (country_code) REFERENCES Countries(country_code)
);

CREATE TABLE Vaccine_Schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT,
    year INTEGER,
    vaccine_code TEXT,
    vaccine_description TEXT,
    schedule_rounds REAL,
    targetpop TEXT,
    targetpop_description TEXT,
    geoarea TEXT,
    age_administered TEXT,
    source_comment TEXT,
    FOREIGN KEY (country_code) REFERENCES Countries(country_code)
);

CREATE INDEX idx_coverage_country_year ON Coverage(country_code, year);
CREATE INDEX idx_coverage_antigen ON Coverage(antigen_code);
CREATE INDEX idx_incidence_country_year ON Disease_Incidence(country_code, year);
CREATE INDEX idx_incidence_disease ON Disease_Incidence(disease_code);
CREATE INDEX idx_cases_country_year ON Reported_Cases(country_code, year);
CREATE INDEX idx_cases_disease ON Reported_Cases(disease_code);
CREATE INDEX idx_intro_country_year ON Vaccine_Introduction(country_code, year);
CREATE INDEX idx_schedule_country_year ON Vaccine_Schedule(country_code, year);
"""


def main():
    coverage = pd.read_csv(CLEAN_DIR / "coverage_country.csv")
    incidence = pd.read_csv(CLEAN_DIR / "incidence_country.csv")
    cases = pd.read_csv(CLEAN_DIR / "cases_country.csv")
    intro = pd.read_csv(CLEAN_DIR / "vaccine_introduction.csv")
    schedule = pd.read_csv(CLEAN_DIR / "vaccine_schedule.csv")

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    # --- Countries dimension: union of country_code/name across all 5 tables,
    # WHO region filled in from intro/schedule where available (coverage/
    # incidence/cases do not carry a WHO region column) ---
    c1 = coverage[["CODE", "NAME"]].rename(columns={"CODE": "country_code", "NAME": "country_name"})
    c2 = incidence[["CODE", "NAME"]].rename(columns={"CODE": "country_code", "NAME": "country_name"})
    c3 = cases[["CODE", "NAME"]].rename(columns={"CODE": "country_code", "NAME": "country_name"})
    c4 = intro[["ISO_3_CODE", "COUNTRYNAME", "WHO_REGION"]].rename(
        columns={"ISO_3_CODE": "country_code", "COUNTRYNAME": "country_name", "WHO_REGION": "who_region"})
    c5 = schedule[["ISO_3_CODE", "COUNTRYNAME", "WHO_REGION"]].rename(
        columns={"ISO_3_CODE": "country_code", "COUNTRYNAME": "country_name", "WHO_REGION": "who_region"})

    countries = pd.concat([c1, c2, c3, c4, c5], ignore_index=True)
    who_region_map = pd.concat([c4, c5])[["country_code", "who_region"]].dropna().drop_duplicates("country_code")
    countries = countries[["country_code", "country_name"]].dropna().drop_duplicates("country_code")
    countries = countries.merge(who_region_map, on="country_code", how="left")
    countries.to_sql("Countries", conn, if_exists="append", index=False)

    # --- Vaccines dimension (source-tagged, see module docstring) ---
    v1 = coverage[["ANTIGEN", "ANTIGEN_DESCRIPTION"]].drop_duplicates().dropna()
    v1.columns = ["vaccine_code", "vaccine_description"]
    v1["source"] = "COVERAGE_ANTIGEN"
    v2 = intro[["DESCRIPTION"]].drop_duplicates().dropna()
    v2["vaccine_code"] = v2["DESCRIPTION"]
    v2["vaccine_description"] = v2["DESCRIPTION"]
    v2 = v2[["vaccine_code", "vaccine_description"]]
    v2["source"] = "INTRODUCTION"
    v3 = schedule[["VACCINECODE", "VACCINE_DESCRIPTION"]].drop_duplicates().dropna()
    v3.columns = ["vaccine_code", "vaccine_description"]
    v3["source"] = "SCHEDULE"
    vaccines = pd.concat([v1, v2, v3], ignore_index=True).drop_duplicates(["vaccine_code", "source"])
    vaccines.to_sql("Vaccines", conn, if_exists="append", index=False)

    # --- Diseases dimension (DISEASE code is shared between incidence & cases) ---
    d1 = incidence[["DISEASE", "DISEASE_DESCRIPTION"]].drop_duplicates().dropna()
    d2 = cases[["DISEASE", "DISEASE_DESCRIPTION"]].drop_duplicates().dropna()
    diseases = pd.concat([d1, d2], ignore_index=True).drop_duplicates("DISEASE")
    diseases.columns = ["disease_code", "disease_description"]
    diseases.to_sql("Diseases", conn, if_exists="append", index=False)

    # --- Fact tables ---
    cov_fact = coverage.rename(columns={
        "CODE": "country_code", "YEAR": "year", "ANTIGEN": "antigen_code",
        "ANTIGEN_DESCRIPTION": "antigen_description", "COVERAGE_CATEGORY": "coverage_category",
        "COVERAGE_CATEGORY_DESCRIPTION": "coverage_category_description",
        "TARGET_NUMBER": "target_number", "DOSES": "doses", "COVERAGE": "coverage",
    })[["country_code", "year", "antigen_code", "antigen_description", "coverage_category",
        "coverage_category_description", "target_number", "doses", "coverage"]]
    cov_fact.to_sql("Coverage", conn, if_exists="append", index=False)

    inc_fact = incidence.rename(columns={
        "CODE": "country_code", "YEAR": "year", "DISEASE": "disease_code",
        "DENOMINATOR": "denominator", "INCIDENCE_RATE": "incidence_rate",
    })[["country_code", "year", "disease_code", "denominator", "incidence_rate"]]
    inc_fact.to_sql("Disease_Incidence", conn, if_exists="append", index=False)

    cases_fact = cases.rename(columns={
        "CODE": "country_code", "YEAR": "year", "DISEASE": "disease_code", "CASES": "cases",
    })[["country_code", "year", "disease_code", "cases"]]
    cases_fact.to_sql("Reported_Cases", conn, if_exists="append", index=False)

    intro_fact = intro.rename(columns={
        "ISO_3_CODE": "country_code", "YEAR": "year",
        "DESCRIPTION": "vaccine_description", "INTRO": "intro",
    })[["country_code", "year", "vaccine_description", "intro"]]
    intro_fact.to_sql("Vaccine_Introduction", conn, if_exists="append", index=False)

    sched_fact = schedule.rename(columns={
        "ISO_3_CODE": "country_code", "YEAR": "year", "VACCINECODE": "vaccine_code",
        "VACCINE_DESCRIPTION": "vaccine_description", "SCHEDULEROUNDS": "schedule_rounds",
        "TARGETPOP": "targetpop", "TARGETPOP_DESCRIPTION": "targetpop_description",
        "GEOAREA": "geoarea", "AGEADMINISTERED": "age_administered", "SOURCECOMMENT": "source_comment",
    })[["country_code", "year", "vaccine_code", "vaccine_description", "schedule_rounds",
        "targetpop", "targetpop_description", "geoarea", "age_administered", "source_comment"]]
    sched_fact.to_sql("Vaccine_Schedule", conn, if_exists="append", index=False)

    conn.commit()

    # --- Validation ---
    print("Row counts:")
    for tbl in ["Countries", "Vaccines", "Diseases", "Coverage", "Disease_Incidence",
                "Reported_Cases", "Vaccine_Introduction", "Vaccine_Schedule"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl}: {n:,}")

    conn.close()
    print(f"\nDatabase written to {DB_PATH}")


if __name__ == "__main__":
    main()
