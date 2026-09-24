-- create_tables.sql
-- Normalized schema for the Vaccination Data Analysis project.
-- Written in ANSI-SQL style; tested logic lives in vaccination.db (SQLite).
-- For MySQL: change AUTOINCREMENT -> AUTO_INCREMENT and INTEGER PK -> INT.
-- For Postgres: change AUTOINCREMENT -> GENERATED ALWAYS AS IDENTITY.

CREATE TABLE Countries (
    country_code CHAR(3) PRIMARY KEY,
    country_name VARCHAR(100),
    who_region   VARCHAR(10)
);

-- Vaccine codes are NOT unified across sources (see build_database.py
-- docstring): coverage's ANTIGEN, introduction's free-text DESCRIPTION,
-- and schedule's VACCINECODE are three distinct vocabularies with no
-- supplied crosswalk. `source` disambiguates them.
CREATE TABLE Vaccines (
    vaccine_code        VARCHAR(100),
    vaccine_description VARCHAR(255),
    source               VARCHAR(20),   -- COVERAGE_ANTIGEN | INTRODUCTION | SCHEDULE
    PRIMARY KEY (vaccine_code, source)
);

CREATE TABLE Diseases (
    disease_code        VARCHAR(50) PRIMARY KEY,
    disease_description VARCHAR(255)
);

CREATE TABLE Coverage (
    id                              INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code                   CHAR(3),
    year                            SMALLINT,
    antigen_code                   VARCHAR(50),
    antigen_description            VARCHAR(255),
    coverage_category              VARCHAR(20),
    coverage_category_description  VARCHAR(100),
    target_number                  BIGINT,
    doses                           BIGINT,
    coverage                        DECIMAL(6,2),   -- percent, NULL = not reported
    FOREIGN KEY (country_code) REFERENCES Countries(country_code)
);

CREATE TABLE Disease_Incidence (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code    CHAR(3),
    year            SMALLINT,
    disease_code    VARCHAR(50),
    denominator     VARCHAR(100),
    incidence_rate  DECIMAL(12,4),
    FOREIGN KEY (country_code) REFERENCES Countries(country_code),
    FOREIGN KEY (disease_code) REFERENCES Diseases(disease_code)
);

CREATE TABLE Reported_Cases (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code  CHAR(3),
    year          SMALLINT,
    disease_code  VARCHAR(50),
    cases         BIGINT,
    FOREIGN KEY (country_code) REFERENCES Countries(country_code),
    FOREIGN KEY (disease_code) REFERENCES Diseases(disease_code)
);

CREATE TABLE Vaccine_Introduction (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code          CHAR(3),
    year                  SMALLINT,
    vaccine_description   VARCHAR(255),
    intro                 VARCHAR(5),      -- Yes / No
    FOREIGN KEY (country_code) REFERENCES Countries(country_code)
);

CREATE TABLE Vaccine_Schedule (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code           CHAR(3),
    year                   SMALLINT,
    vaccine_code           VARCHAR(100),
    vaccine_description    VARCHAR(255),
    schedule_rounds        SMALLINT,
    targetpop              VARCHAR(50),
    targetpop_description  VARCHAR(100),
    geoarea                VARCHAR(50),
    age_administered       VARCHAR(50),
    source_comment         VARCHAR(255),
    FOREIGN KEY (country_code) REFERENCES Countries(country_code)
);

CREATE INDEX idx_coverage_country_year   ON Coverage(country_code, year);
CREATE INDEX idx_coverage_antigen        ON Coverage(antigen_code);
CREATE INDEX idx_incidence_country_year  ON Disease_Incidence(country_code, year);
CREATE INDEX idx_incidence_disease       ON Disease_Incidence(disease_code);
CREATE INDEX idx_cases_country_year      ON Reported_Cases(country_code, year);
CREATE INDEX idx_cases_disease           ON Reported_Cases(disease_code);
CREATE INDEX idx_intro_country_year      ON Vaccine_Introduction(country_code, year);
CREATE INDEX idx_schedule_country_year   ON Vaccine_Schedule(country_code, year);
