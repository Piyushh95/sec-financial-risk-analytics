import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "sec_metric_facts.csv"

REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
]

COLUMNS = [
    "adsh", "cik", "name", "tag", "date", "qtrs",
    "uom", "segments", "coreg", "value",
    "form", "period", "fy", "fp", "filed"
]

print("Loading revenue records...")

df = pd.read_csv(
    DATA_FILE,
    usecols=COLUMNS,
    low_memory=False
)

df = df[df["tag"].isin(REVENUE_TAGS)].copy()

print(f"\nRevenue records loaded: {len(df):,}")

# Reproduce the core Phase 1 filters.
df = df[
    df["form"].isin(["10-Q", "10-K", "20-F", "40-F",
                     "10-Q/A", "10-K/A", "20-F/A", "40-F/A"])
    & (df["uom"] == "USD")
    & (df["segments"].isna() | (df["segments"] == ""))
    & (df["coreg"].isna() | (df["coreg"] == ""))
    & df["value"].notna()
    & (df["qtrs"] == 3)
].copy()

print(f"Records after Phase 1-style filters: {len(df):,}")

# Count facts by company, date, and tag.
group_cols = ["cik", "date", "tag"]

counts = (
    df.groupby(group_cols, dropna=False)
    .size()
    .reset_index(name="fact_count")
)

duplicates = counts[counts["fact_count"] > 1]

print("\n=== SAME TAG, COMPANY, DATE ===")
print(f"Groups with multiple facts: {len(duplicates):,}")
print(f"Companies affected: {duplicates['cik'].nunique():,}")

if not duplicates.empty:
    print("\nExamples:")
    print(duplicates.head(10).to_string(index=False))

# Check whether multiple filings contribute to these groups.
if not duplicates.empty:
    keys = duplicates[group_cols]

    merged = df.merge(keys, on=group_cols, how="inner")

    filing_check = (
        merged.groupby(group_cols, dropna=False)
        .agg(
            fact_count=("value", "size"),
            distinct_filings=("adsh", "nunique"),
            distinct_values=("value", "nunique"),
            filing_forms=("form", lambda x: ", ".join(sorted(set(x))))
        )
        .reset_index()
    )

    print("\n=== DUPLICATE GROUP DIAGNOSTICS ===")
    print(
        filing_check[filing_check["fact_count"] > 1]
        .head(20)
        .to_string(index=False)
    )

# Check multi-tag conflicts after filtering.
tag_counts = (
    df.groupby(["cik", "date"])["tag"]
    .nunique()
    .reset_index(name="distinct_tags")
)

multi_tag = tag_counts[tag_counts["distinct_tags"] > 1]

print("\n=== MULTI-TAG GROUPS AFTER FILTERING ===")
print(f"Company-date groups with multiple tags: {len(multi_tag):,}")
print(f"Companies affected: {multi_tag['cik'].nunique():,}")

print("\nDiagnostic complete. No files were modified.")