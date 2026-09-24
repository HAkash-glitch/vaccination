# Power BI Dashboard Design — Global Vaccination Coverage Analysis

Data source: `sql/vaccination.db` (SQLite) or the portable schema in
`sql/create_tables.sql` loaded into MySQL/Postgres/SQL Server. Import via
Power BI's ODBC connector (SQLite) or native connector (MySQL/Postgres/SQL
Server); alternatively import `cleaned_data/*.csv` directly with Power
Query if a live DB connection isn't available.

## 1. Data Model / Relationship Diagram

```
Countries (country_code PK) ─────┬──< Coverage (country_code FK)
                                  ├──< Disease_Incidence (country_code FK)
                                  ├──< Reported_Cases (country_code FK)
                                  ├──< Vaccine_Introduction (country_code FK)
                                  └──< Vaccine_Schedule (country_code FK)

Diseases (disease_code PK) ──────┬──< Disease_Incidence (disease_code FK)
                                  └──< Reported_Cases (disease_code FK)

Vaccines (vaccine_code, source PK) — NOT joined directly to Coverage/
Vaccine_Schedule in the model (see note below); kept as a lookup table for
antigen/vaccine descriptions only.
```

**Relationship type:** all Countries→fact and Diseases→fact relationships
are 1-to-many, single direction (filters flow from dimension to fact).

**Important modeling note:** do not build a relationship from Vaccines to
Coverage or Vaccine_Schedule on `vaccine_code` — as documented in
`python/build_database.py`, the three vaccine coding schemes (coverage's
`antigen_code`, introduction's free-text description, schedule's
`vaccine_code`) are not a verified 1:1 crosswalk. Use `antigen_code` /
`vaccine_code` directly as category axes on visuals instead of joining
through Vaccines, so the dashboard never silently implies a false vaccine
equivalence across tables.

## 2. KPI Cards (top of dashboard)

| KPI | DAX measure |
|---|---|
| Total Countries | `Total Countries = DISTINCTCOUNT(Countries[country_code])` |
| Total Vaccines Tracked | `Total Vaccines = DISTINCTCOUNT(Coverage[antigen_code])` |
| Average Coverage | `Avg Coverage % = AVERAGE(Coverage[coverage])` |
| Total Reported Cases | `Total Cases = SUM(Reported_Cases[cases])` |

## 3. DAX Measures

```DAX
Total Countries = DISTINCTCOUNT(Countries[country_code])

Total Vaccines = DISTINCTCOUNT(Coverage[antigen_code])

Avg Coverage % = AVERAGE(Coverage[coverage])

Total Cases = SUM(Reported_Cases[cases])

Avg Incidence Rate =
AVERAGE(Disease_Incidence[incidence_rate])

-- Latest-year coverage (for a KPI card that should not average across all
-- years by default)
Avg Coverage % (Latest Year) =
CALCULATE(
    [Avg Coverage %],
    Coverage[year] = MAX(Coverage[year])
)

-- WUENIC-only coverage, the standard comparable WHO series -- use this as
-- the default coverage measure on trend visuals to avoid mixing ADMIN/
-- OFFICIAL/WUENIC methodologies in one line
Avg Coverage % (WUENIC) =
CALCULATE(
    [Avg Coverage %],
    Coverage[coverage_category] = "WUENIC"
)

-- Dose 1 -> Dose 3 drop-off (DTP), in percentage points
DTP1 Coverage =
CALCULATE([Avg Coverage % (WUENIC)], Coverage[antigen_code] = "DTPCV1")

DTP3 Coverage =
CALCULATE([Avg Coverage % (WUENIC)], Coverage[antigen_code] = "DTPCV3")

DTP Drop-off (pts) = [DTP1 Coverage] - [DTP3 Coverage]

-- Year-over-year change in average coverage, for a trend KPI/sparkline
Coverage YoY Change (pts) =
VAR CurrentAvg = [Avg Coverage % (WUENIC)]
VAR PriorYearAvg =
    CALCULATE(
        [Avg Coverage % (WUENIC)],
        FILTER(ALL(Coverage[year]), Coverage[year] = MAX(Coverage[year]) - 1)
    )
RETURN CurrentAvg - PriorYearAvg

-- Countries below the 95% measles herd-immunity threshold, latest year
Countries Below 95pct MCV1 =
CALCULATE(
    DISTINCTCOUNT(Coverage[country_code]),
    Coverage[antigen_code] = "MCV1",
    Coverage[coverage_category] = "WUENIC",
    Coverage[coverage] < 95,
    Coverage[year] = MAX(Coverage[year])
)
```

## 4. Visuals

| Visual | Type | Fields |
|---|---|---|
| Coverage trend | Line chart | X: `Coverage[year]`, Y: `[Avg Coverage % (WUENIC)]`, Legend: `antigen_code` (filter to 2-3 antigens, e.g. MCV1, DTPCV3) |
| Disease trend | Line chart | X: `Disease_Incidence[year]`, Y: `[Avg Incidence Rate]`, Legend: `disease_code` |
| Country comparison | Bar chart (top N) | Axis: `Countries[country_name]`, Value: `[Avg Coverage % (WUENIC)]`, filtered to one antigen via slicer |
| Region comparison | Clustered bar | Axis: `Countries[who_region]`, Values: `[DTP1 Coverage]`, `[DTP3 Coverage]` |
| Vaccine comparison | Bar chart | Axis: `Coverage[antigen_code]`, Value: `[Avg Coverage % (Latest Year)]`, top 15 filter |
| Coverage vs Incidence | Scatter chart | X: `[Avg Coverage % (WUENIC)]`, Y: `[Avg Incidence Rate]`, Details: `country_code`, Legend: `who_region` |
| Map | Filled map / ArcGIS map | Location: `Countries[country_name]` or ISO-3 `country_code`, Color saturation: `[Avg Coverage % (WUENIC)]` |
| Heatmap (matrix) | Matrix visual w/ conditional formatting | Rows: `who_region`, Columns: `year`, Values: `[DTP3 Coverage]`, background color scale |
| Vaccine introduction timeline | Line/area chart | X: `Vaccine_Introduction[year]`, Y: distinct count of countries where `intro = "Yes"` (running total via DAX `TOTALYTD`-style cumulative measure) |

## 5. Slicers

- **Year**: slicer on `Coverage[year]` (or a shared Year dimension if you
  build one — recommended for cross-filtering all 5 fact tables
  consistently)
- **Country**: slicer on `Countries[country_name]`
- **WHO Region**: slicer on `Countries[who_region]`
- **Vaccine**: slicer on `Coverage[antigen_code]`
- **Disease**: slicer on `Diseases[disease_description]`

Sync all slicers across report pages (Format > Edit interactions / Sync
slicers pane) so filtering on the overview page carries to the drill-down
pages.

## 6. Dashboard Layout (3 pages)

**Page 1 — Overview**
- KPI cards row (4 cards above) across the top
- Coverage trend line chart (large, left)
- Map colored by average coverage (large, right)
- Year / Region slicers on the left rail

**Page 2 — Regional & Dose Analysis**
- Region comparison clustered bar (DTP1 vs DTP3)
- DTP3 heatmap matrix (region x year)
- Vaccine comparison bar chart (top 15 by coverage)

**Page 3 — Disease & Introduction**
- Disease trend line chart
- Coverage vs Incidence scatter chart
- Vaccine introduction cumulative timeline
- Reported cases bar chart (top diseases, current year)

## 7. Known data-quality flags to surface in tooltips or a notes page

- `coverage` is NULL for ~44% of Coverage rows (not reported) — Power BI
  will silently exclude NULLs from averages, which is correct behavior
  here, but a "n countries reporting" measure alongside any average is
  recommended so a thin sample (e.g. 4 countries) isn't read the same as a
  full one (e.g. 190 countries).
- `coverage` can exceed 100% for ADMIN/OFFICIAL category rows (denominator
  undercounts) — don't cap/clip in a measure; this is genuine source data.
- WHO region is not available for every Coverage/Incidence/Cases row (only
  ~214 of the world's countries have a region in the Countries table,
  sourced from the Introduction/Schedule tables) — region-level visuals
  will exclude unmapped countries.
