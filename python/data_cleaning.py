import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent.parent / "cleaned_data"
OUT_DIR.mkdir(exist_ok=True)

AGGREGATE_GROUPS = {
    "WHO_REGIONS", "GLOBAL", "WB_LONG", "WB_SHORT",
    "DEVELOPMENT_STATUS", "GAVI_PHASE5", "UNICEF_REGIONS",
}


def _load(fname: str) -> pd.DataFrame:
    df = pd.read_excel(RAW_DIR / fname, sheet_name="Data")
    # Drop the footer row: it's the row where every column except GROUP-like
    # metadata is null. Simplest robust rule: drop rows where the YEAR
    # column (present in all 5 files) is null.
    df = df[df["YEAR"].notna()].copy()
    df["YEAR"] = df["YEAR"].astype(int)
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip().replace({"nan": pd.NA})
    before = len(df)
    df = df.drop_duplicates()
    dropped = before - len(df)
    if dropped:
        print(f"  {fname}: dropped {dropped} exact-duplicate rows")
    return df


def clean_group_split(fname: str, group_col: str = "GROUP"):
    df = _load(fname)
    country = df[df[group_col] == "COUNTRIES"].copy()
    aggregate = df[df[group_col].isin(AGGREGATE_GROUPS)].copy()
    unexpected = set(df[group_col].unique()) - {"COUNTRIES"} - AGGREGATE_GROUPS
    if unexpected:
        print(f"  {fname}: unexpected GROUP values not classified: {unexpected}")
    return country, aggregate


def main():
    print("Cleaning coverage-data.xlsx ...")
    coverage_country, coverage_agg = clean_group_split("coverage-data.xlsx")
    coverage_country.to_csv(OUT_DIR / "coverage_country.csv", index=False)
    coverage_agg.to_csv(OUT_DIR / "coverage_aggregate.csv", index=False)
    print(f"  country rows: {len(coverage_country):,} | aggregate rows: {len(coverage_agg):,}")
    print(f"  COVERAGE missing: {coverage_country['COVERAGE'].isna().sum():,} "
          f"({coverage_country['COVERAGE'].isna().mean():.1%}) -- left as NULL, not imputed")

    print("\nCleaning incidence-rate-data.xlsx ...")
    incidence_country, incidence_agg = clean_group_split("incidence-rate-data.xlsx")
    incidence_country.to_csv(OUT_DIR / "incidence_country.csv", index=False)
    incidence_agg.to_csv(OUT_DIR / "incidence_aggregate.csv", index=False)
    print(f"  country rows: {len(incidence_country):,} | aggregate rows: {len(incidence_agg):,}")

    print("\nCleaning reported-cases-data.xlsx ...")
    cases_country, cases_agg = clean_group_split("reported-cases-data.xlsx")
    cases_country.to_csv(OUT_DIR / "cases_country.csv", index=False)
    cases_agg.to_csv(OUT_DIR / "cases_aggregate.csv", index=False)
    print(f"  country rows: {len(cases_country):,} | aggregate rows: {len(cases_agg):,}")

    print("\nCleaning vaccine-introduction-data.xlsx ...")
    intro = _load("vaccine-introduction-data.xlsx")
    intro.to_csv(OUT_DIR / "vaccine_introduction.csv", index=False)
    print(f"  rows: {len(intro):,}")

    print("\nCleaning vaccine-schedule-data.xlsx ...")
    schedule = _load("vaccine-schedule-data.xlsx")
    schedule.to_csv(OUT_DIR / "vaccine_schedule.csv", index=False)
    print(f"  rows: {len(schedule):,}")

    print("\nDone. Cleaned CSVs written to:", OUT_DIR)


if __name__ == "__main__":
    main()
