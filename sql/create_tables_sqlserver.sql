-- create_tables_sqlserver.sql
-- SQL Server (T-SQL) version of the schema in create_tables.sql.
-- Run this in SSMS or Azure Data Studio against a new database, e.g.:
--   CREATE DATABASE VaccinationAnalysis;
--   USE VaccinationAnalysis;
--   -- then run this script

CREATE TABLE Countries (
    country_code CHAR(3) PRIMARY KEY,
    country_name VARCHAR(100),
    who_region   VARCHAR(10)
);

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
    id                              INT IDENTITY(1,1) PRIMARY KEY,
    country_code                   CHAR(3),
    year                            SMALLINT,
    antigen_code                   VARCHAR(50),
    antigen_description            VARCHAR(255),
    coverage_category              VARCHAR(20),
    coverage_category_description  VARCHAR(100),
    target_number                  BIGINT,
    doses                           BIGINT,
    coverage                        DECIMAL(6,2),   -- percent, NULL = not reported
    CONSTRAINT FK_Coverage_Country FOREIGN KEY (country_code) REFERENCES Countries(country_code)
);

CREATE TABLE Disease_Incidence (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    country_code    CHAR(3),
    year            SMALLINT,
    disease_code    VARCHAR(50),
    denominator     VARCHAR(100),
    incidence_rate  DECIMAL(12,4),
    CONSTRAINT FK_Incidence_Country FOREIGN KEY (country_code) REFERENCES Countries(country_code),
    CONSTRAINT FK_Incidence_Disease FOREIGN KEY (disease_code) REFERENCES Diseases(disease_code)
);

CREATE TABLE Reported_Cases (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    country_code  CHAR(3),
    year          SMALLINT,
    disease_code  VARCHAR(50),
    cases         BIGINT,
    CONSTRAINT FK_Cases_Country FOREIGN KEY (country_code) REFERENCES Countries(country_code),
    CONSTRAINT FK_Cases_Disease FOREIGN KEY (disease_code) REFERENCES Diseases(disease_code)
);

CREATE TABLE Vaccine_Introduction (
    id                    INT IDENTITY(1,1) PRIMARY KEY,
    country_code          CHAR(3),
    year                  SMALLINT,
    vaccine_description   VARCHAR(255),
    intro                 VARCHAR(5),      -- Yes / No
    CONSTRAINT FK_Intro_Country FOREIGN KEY (country_code) REFERENCES Countries(country_code)
);

CREATE TABLE Vaccine_Schedule (
    id                     INT IDENTITY(1,1) PRIMARY KEY,
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
    CONSTRAINT FK_Schedule_Country FOREIGN KEY (country_code) REFERENCES Countries(country_code)
);

CREATE INDEX idx_coverage_country_year   ON Coverage(country_code, year);
CREATE INDEX idx_coverage_antigen        ON Coverage(antigen_code);
CREATE INDEX idx_incidence_country_year  ON Disease_Incidence(country_code, year);
CREATE INDEX idx_incidence_disease       ON Disease_Incidence(disease_code);
CREATE INDEX idx_cases_country_year      ON Reported_Cases(country_code, year);
CREATE INDEX idx_cases_disease           ON Reported_Cases(disease_code);
CREATE INDEX idx_intro_country_year      ON Vaccine_Introduction(country_code, year);
CREATE INDEX idx_schedule_country_year   ON Vaccine_Schedule(country_code, year);
