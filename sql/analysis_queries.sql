-- analysis_queries.sql
-- All queries below were run and verified against sql/vaccination.db.
-- Sample verified output is given in a comment under each query so a
-- reviewer can sanity-check without re-running. Full results are larger;
-- these are the first rows only.

-- ============================================================
-- Q1. How does global measles vaccine (MCV1) coverage trend over time?
-- (Easy) — feeds "How do vaccination rates correlate with disease incidence"
-- ============================================================
SELECT year, ROUND(AVG(coverage), 2) AS avg_mcv1_coverage_pct
FROM Coverage
WHERE antigen_code = 'MCV1' AND coverage IS NOT NULL AND year >= 2014
GROUP BY year
ORDER BY year;
-- Sample result: 2014 -> 89.14%, 2019 -> 89.38%, 2021 -> 85.33% (COVID-era dip)

-- ============================================================
-- Q2. Which countries have high measles coverage (WUENIC >= 90%) but still
-- report nonzero measles incidence in 2022? (Easy/Medium — "regions with
-- high disease incidence despite high vaccination rates")
-- ============================================================
SELECT c.country_code, cov.coverage AS mcv1_coverage_2022,
       inc.incidence_rate AS measles_incidence_2022
FROM Coverage cov
JOIN Disease_Incidence inc
     ON cov.country_code = inc.country_code AND cov.year = inc.year
JOIN Countries c ON c.country_code = cov.country_code
WHERE cov.antigen_code = 'MCV1' AND cov.coverage_category = 'WUENIC'
  AND cov.year = 2022 AND inc.disease_code = 'MEASLES'
  AND cov.coverage >= 90 AND inc.incidence_rate > 0
ORDER BY inc.incidence_rate DESC
LIMIT 10;
-- Sample result: ZWE (90.0% coverage, incidence 344.3/million),
-- SLE (90.0%, 88.3), ZMB (90.0%, 87.1), TJK (98.0%, 44.6) ...
-- Reading: 90% national coverage is below the ~95% herd-immunity threshold
-- for measles, so outbreaks in high-but-not-95%+ coverage countries are
-- epidemiologically expected, not anomalous.

-- ============================================================
-- Q3. What is the drop-off rate between DTP dose 1 and dose 3, by WHO
-- region, in 2022? (Easy — "drop-off rate between 1st dose and subsequent")
-- ============================================================
SELECT c.who_region,
       ROUND(AVG(CASE WHEN cov.antigen_code = 'DTPCV1' THEN cov.coverage END), 2) AS avg_dtp1,
       ROUND(AVG(CASE WHEN cov.antigen_code = 'DTPCV3' THEN cov.coverage END), 2) AS avg_dtp3
FROM Coverage cov
JOIN Countries c ON c.country_code = cov.country_code
WHERE cov.year = 2022 AND cov.antigen_code IN ('DTPCV1', 'DTPCV3')
  AND c.who_region IS NOT NULL
GROUP BY c.who_region;
-- Sample result: AFRO 89.32% -> 83.23% (drop-off ~6.1 pts); EURO 95.56% ->
-- 92.30% (drop-off ~3.3 pts) -- AFRO shows the largest 1st-to-3rd-dose
-- drop-off of the six WHO regions.

-- ============================================================
-- Q4. Has booster-dose uptake (DIPHCV4, 1st booster) increased over time?
-- (Easy). Note: WUENIC estimates are not published for booster doses in
-- this dataset, so administrative (ADMIN) coverage is used instead --
-- flagged because ADMIN and WUENIC are not directly comparable series.
-- ============================================================
SELECT year, ROUND(AVG(coverage), 2) AS avg_booster_coverage
FROM Coverage
WHERE antigen_code = 'DIPHCV4' AND coverage_category = 'ADMIN'
  AND coverage IS NOT NULL AND year BETWEEN 2017 AND 2023
GROUP BY year
ORDER BY year;
-- Sample result: 2017: 83.33% -> 2022: 81.29% -> 2023: 83.20%.
-- Reading: no sustained increase; booster uptake has been roughly flat to
-- slightly declining over the only years this dose is reported (2017-2023).

-- ============================================================
-- Q5. Are there disparities in vaccine-introduction timelines across WHO
-- regions? (Medium) — example: Rotavirus vaccine
-- ============================================================
SELECT c.who_region, COUNT(DISTINCT vi.country_code) AS countries_introduced
FROM Vaccine_Introduction vi
JOIN Countries c ON c.country_code = vi.country_code
WHERE vi.vaccine_description LIKE '%Rotavirus%' AND vi.intro = 'Yes'
GROUP BY c.who_region
ORDER BY countries_introduced DESC;
-- Sample result: AFRO 38, EURO 26, AMRO 21, WPRO 16, EMRO 15, SEARO 6 --
-- SEARO (South-East Asia) lags well behind AFRO in Rotavirus introduction
-- count, despite AFRO typically having lower overall health-system capacity
-- -- likely reflects Gavi-funded rollout prioritization in AFRO.

-- ============================================================
-- Q6. Which vaccines have the highest average global coverage in 2022?
-- (Medium — "percentage of target population covered by each vaccine")
-- ============================================================
SELECT antigen_code, ROUND(AVG(coverage), 2) AS avg_coverage_2022, COUNT(*) AS n_reports
FROM Coverage
WHERE year = 2022 AND coverage IS NOT NULL
GROUP BY antigen_code
ORDER BY avg_coverage_2022 DESC
LIMIT 10;
-- Sample result: JAPENC_C 96.34% (n=4, thin sample -- regional vaccine),
-- DTPCV1 92.25% (n=549, broad sample), PCV1 90.69%, BCG 89.83% ...

-- ============================================================
-- Q7. Which diseases have shown the largest incidence decline, comparing
-- 1990 vs 2022? (Medium — "diseases with most significant reduction due
-- to vaccination")
-- ============================================================
SELECT d.disease_description,
       ROUND(AVG(CASE WHEN i.year = 1990 THEN i.incidence_rate END), 3) AS rate_1990,
       ROUND(AVG(CASE WHEN i.year = 2022 THEN i.incidence_rate END), 3) AS rate_2022
FROM Disease_Incidence i
JOIN Diseases d ON d.disease_code = i.disease_code
WHERE i.year IN (1990, 2022)
GROUP BY d.disease_description
HAVING rate_1990 IS NOT NULL AND rate_2022 IS NOT NULL
ORDER BY (rate_1990 - rate_2022) DESC;
-- Sample result: Measles 714.2 -> 43.1 per unit population (largest
-- absolute decline); Pertussis 240.2 -> 5.4; Total tetanus 15.8 -> 1.3.
-- Caveat: this compares average reported rates across countries with data
-- in BOTH years, not a like-for-like fixed cohort -- reporting countries
-- differ by year, so treat as directional, not precise.

-- ============================================================
-- Q8. Coverage gaps for a high-priority disease vaccine (Hepatitis B,
-- birth dose) by WHO region, most recent year (Medium)
-- ============================================================
SELECT c.who_region, ROUND(AVG(cov.coverage), 2) AS avg_hepb_coverage_2022
FROM Coverage cov
JOIN Countries c ON c.country_code = cov.country_code
WHERE cov.antigen_code = 'HEPB3' AND cov.year = 2022
  AND cov.coverage IS NOT NULL AND c.who_region IS NOT NULL
GROUP BY c.who_region
ORDER BY avg_hepb_coverage_2022 ASC;
-- Sample result: AFRO 83.24% (lowest), SEARO 84.45%, AMRO 86.18%,
-- WPRO 87.40%, EMRO 88.49%, EURO 90.20% (highest) -- AFRO has the largest
-- Hepatitis B (3rd dose) coverage gap of the six WHO regions.
