import pandas as pd

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "sec_metric_facts.csv"
OUTPUT_FILE = ROOT / "research_phase_1" / "phase2_duplicate_full_audit.csv"

REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
]

COLUMNS = [
    "adsh", "cik", "name", "tag", "version", "date",
    "qtrs", "uom", "segments", "coreg", "value",
    "form", "period", "fy", "fp", "filed", "prevrpt"
]

print("Loading SEC revenue records...")

df = pd.read_csv(
    DATA_FILE,
    usecols=COLUMNS,
    low_memory=False
)

# Apply the Phase 1-style filters.
df = df[
    df["tag"].isin(REVENUE_TAGS)
    & df["form"].isin([
        "10-Q", "10-K", "20-F", "40-F",
        "10-Q/A", "10-K/A", "20-F/A", "40-F/A"
    ])
    & (df["uom"] == "USD")
    & (df["segments"].isna() | (df["segments"] == ""))
    & (df["coreg"].isna() | (df["coreg"] == ""))
    & df["value"].notna()
    & (df["qtrs"] == 3)
].copy()

# Identify duplicate groups with the same company, date, and tag.
keys = ["cik", "date", "tag"]

group_sizes = df.groupby(keys, dropna=False).size()
duplicate_keys = group_sizes[group_sizes > 1].reset_index()[keys]

duplicates = df.merge(
    duplicate_keys,
    on=keys,
    how="inner"
)

rows = []

for (cik, date, tag), group in duplicates.groupby(
    keys, dropna=False, sort=True
):
    group = group.sort_values(["filed", "adsh"])

    distinct_values = group["value"].nunique()
    distinct_filings = group["adsh"].nunique()

    original_rows = group[~group["form"].str.endswith("/A")]
    amended_rows = group[group["form"].str.endswith("/A")]

    original_value = (
        original_rows.iloc[-1]["value"]
        if not original_rows.empty else None
    )

    amended_value = (
        amended_rows.iloc[-1]["value"]
        if not amended_rows.empty else None
    )

    if distinct_values == 1 and len(amended_rows) > 0:
        classification = "amended_same_value"
    elif distinct_values == 1:
        classification = "identical_duplicate"
    elif not original_rows.empty and not amended_rows.empty:
        classification = "amended_changed_value"
    else:
        classification = "unresolved_conflict"

    rows.append({
        "cik": cik,
        "company": group["name"].iloc[0],
        "date": date,
        "tag": tag,
        "fact_count": len(group),
        "distinct_filings": distinct_filings,
        "distinct_values": distinct_values,
        "original_adsh": (
            "; ".join(original_rows["adsh"].astype(str).unique())
            if not original_rows.empty else None
        ),
        "amended_adsh": (
            "; ".join(amended_rows["adsh"].astype(str).unique())
            if not amended_rows.empty else None
        ),
        "original_value": original_value,
        "amended_value": amended_value,
        "value_difference": (
            amended_value - original_value
            if original_value is not None
            and amended_value is not None
            else None
        ),
        "original_filed": (
            "; ".join(original_rows["filed"].astype(str).unique())
            if not original_rows.empty else None
        ),
        "amended_filed": (
            "; ".join(amended_rows["filed"].astype(str).unique())
            if not amended_rows.empty else None
        ),
        "classification": classification,
        "review_required": classification in [
            "amended_changed_value",
            "unresolved_conflict"
        ],
        "selected_record": "PENDING_REVIEW",
        "selection_reason": "No automatic selection until policy validation",
    })

audit = pd.DataFrame(rows)

audit.to_csv(OUTPUT_FILE, index=False)

print("\n=== DUPLICATE AUDIT SUMMARY ===")
print(f"Duplicate groups: {len(audit)}")
print(f"Companies affected: {audit['cik'].nunique()}")
print("\nClassification counts:")
print(audit["classification"].value_counts().to_string())

print("\nGroups requiring review:")
print(
    audit.loc[
        audit["review_required"],
        [
            "cik", "company", "date", "tag",
            "original_value", "amended_value",
            "classification"
        ]
    ].to_string(index=False)
)

print(f"\nAudit saved to: {OUTPUT_FILE}")
print("Original dataset was not modified.")
