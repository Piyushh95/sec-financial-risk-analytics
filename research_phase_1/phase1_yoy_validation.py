#!/usr/bin/env python3
"""
Phase 1 Final Validation — 9-Month YTD YoY Pair Verification
==============================================================
Applies all approved filters, isolates qtrs=3 facts for the three key
metrics, validates that current/prior-year dates are ~1 year apart,
enforces the revenue tag hierarchy, and identifies conflicts/duplicates.

Does NOT modify the source dataset or existing Phase 1 outputs.
"""
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta
import os, json

DATA_FILE = r"F:\Big4_Project\sec_metric_facts.csv"
OUT_DIR = r"F:\Big4_Project\research_phase_1"
CHUNKSIZE = 200_000

# --- Tags ---
REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",  # Priority 1
    "Revenues",                                              # Priority 2
    "RevenueFromContractWithCustomerIncludingAssessedTax",  # Priority 3
]
REVENUE_TAG_SET = set(REVENUE_TAGS)
REVENUE_PRIORITY = {t: i for i, t in enumerate(REVENUE_TAGS)}

NET_INCOME_TAGS = {"NetIncomeLoss"}
OCF_TAGS = {"NetCashProvidedByUsedInOperatingActivities"}
ALL_TAGS = REVENUE_TAG_SET | NET_INCOME_TAGS | OCF_TAGS

VALID_FORMS = {"10-Q", "10-K", "10-Q/A", "10-K/A", "20-F", "40-F", "20-F/A"}

# --- Collect all filtered qtrs=3 facts ---
# Store as list of dicts per (cik, metric)
# Each fact: {cik, tag, date, date_parsed, qtrs, uom, value, adsh, form, fy, fp, name}
facts_by_company = defaultdict(list)  # key: (cik_str, metric_str) -> list of fact dicts

print("=" * 70)
print("PHASE 1 FINAL VALIDATION: 9-Month YTD YoY Pairs")
print("=" * 70)

def parse_date(d):
    """Parse DD-MM-YYYY date string."""
    try:
        return datetime.strptime(str(d).strip(), "%d-%m-%Y")
    except (ValueError, TypeError):
        return None

total_rows = 0
qtrs3_research_rows = 0

for i, chunk in enumerate(pd.read_csv(DATA_FILE, chunksize=CHUNKSIZE, low_memory=False)):
    total_rows += len(chunk)

    # Filter: research tags
    mask = chunk["tag"].isin(ALL_TAGS)
    sub = chunk[mask].copy()
    if sub.empty:
        continue

    # Filter: valid forms
    sub = sub[sub["form"].isin(VALID_FORMS)]
    if sub.empty:
        continue

    # Filter: USD
    sub = sub[sub["uom"] == "USD"]
    if sub.empty:
        continue

    # Filter: segments empty
    sub = sub[sub["segments"].fillna("").str.strip() == ""]
    if sub.empty:
        continue

    # Filter: coreg empty
    sub = sub[sub["coreg"].fillna("").str.strip() == ""]
    if sub.empty:
        continue

    # Filter: value non-null
    sub = sub[sub["value"].notna()]
    if sub.empty:
        continue

    # Filter: qtrs=3 only
    sub["qtrs_int"] = pd.to_numeric(sub["qtrs"], errors="coerce")
    sub = sub[sub["qtrs_int"] == 3]
    if sub.empty:
        continue

    qtrs3_research_rows += len(sub)

    # Classify and store
    for _, row in sub.iterrows():
        cik = str(row["cik"])
        tag = row["tag"]
        if tag in REVENUE_TAG_SET:
            metric = "revenue"
        elif tag in NET_INCOME_TAGS:
            metric = "net_income"
        elif tag in OCF_TAGS:
            metric = "ocf"
        else:
            continue

        facts_by_company[(cik, metric)].append({
            "cik": cik,
            "tag": tag,
            "date": str(row["date"]),
            "date_parsed": parse_date(row["date"]),
            "qtrs": 3,
            "uom": row["uom"],
            "value": float(row["value"]),
            "adsh": str(row["adsh"]),
            "form": str(row["form"]),
            "fy": str(row.get("fy", "")),
            "fp": str(row.get("fp", "")),
            "name": str(row.get("name", "")),
        })

    if (i + 1) % 3 == 0:
        print(f"  Processed {total_rows:,} rows...")

print(f"  Finished scanning {total_rows:,} rows.")
print(f"  Collected {qtrs3_research_rows:,} filtered qtrs=3 research facts.\n")

# --- Gather all unique companies that have any qtrs=3 data ---
all_ciks_with_data = set()
for (cik, metric) in facts_by_company:
    all_ciks_with_data.add(cik)

ciks_with_revenue = {cik for (cik, m) in facts_by_company if m == "revenue"}
ciks_with_ni = {cik for (cik, m) in facts_by_company if m == "net_income"}
ciks_with_ocf = {cik for (cik, m) in facts_by_company if m == "ocf"}
ciks_all_three = ciks_with_revenue & ciks_with_ni & ciks_with_ocf

print(f"Companies with qtrs=3 data: Revenue={len(ciks_with_revenue):,}  NI={len(ciks_with_ni):,}  OCF={len(ciks_with_ocf):,}")
print(f"Companies with all three qtrs=3 metrics: {len(ciks_all_three):,}")

# =====================================================================
# REVENUE TAG HIERARCHY & CONFLICT DETECTION
# =====================================================================
print(f"\n{'=' * 70}")
print("REVENUE TAG HIERARCHY & CONFLICT DETECTION")
print("=" * 70)

# For each company, check what revenue tags exist per reporting date
# Hierarchy: pick highest-priority tag. Flag conflicts.
revenue_conflicts = {}  # cik -> list of conflict details
revenue_resolved = {}   # cik -> dict of {date_str: chosen_fact}

for cik in sorted(ciks_with_revenue):
    facts = facts_by_company[(cik, "revenue")]

    # Group by date
    by_date = defaultdict(list)
    for f in facts:
        by_date[f["date"]].append(f)

    resolved_dates = {}
    conflicts_for_cik = []

    for date_str, date_facts in by_date.items():
        tags_present = set(f["tag"] for f in date_facts)

        if len(tags_present) > 1:
            # Multiple revenue tags for same company-date — CONFLICT
            conflicts_for_cik.append({
                "date": date_str,
                "tags": sorted(tags_present),
                "values": {f["tag"]: f["value"] for f in date_facts},
                "count": len(date_facts),
            })

        # Also check for duplicate facts with SAME tag on same date
        tag_groups = defaultdict(list)
        for f in date_facts:
            tag_groups[f["tag"]].append(f)

        # Apply hierarchy: pick highest-priority tag
        chosen_tag = min(tags_present, key=lambda t: REVENUE_PRIORITY.get(t, 99))
        chosen_facts = tag_groups[chosen_tag]

        if len(chosen_facts) > 1:
            # Duplicate facts for same tag+date — pick by value (flag it)
            conflicts_for_cik.append({
                "date": date_str,
                "issue": "duplicate_same_tag",
                "tag": chosen_tag,
                "values": [f["value"] for f in chosen_facts],
                "count": len(chosen_facts),
            })
            # Take first (they should be identical if truly duplicate)
            resolved_dates[date_str] = chosen_facts[0]
        else:
            resolved_dates[date_str] = chosen_facts[0]

    revenue_resolved[cik] = resolved_dates
    if conflicts_for_cik:
        revenue_conflicts[cik] = conflicts_for_cik

# Classify conflict types
multi_tag_conflicts = {}
dup_same_tag_conflicts = {}
for cik, conflicts in revenue_conflicts.items():
    multi = [c for c in conflicts if "tags" in c]
    dups = [c for c in conflicts if c.get("issue") == "duplicate_same_tag"]
    if multi:
        multi_tag_conflicts[cik] = multi
    if dups:
        dup_same_tag_conflicts[cik] = dups

print(f"\n  Companies with multiple revenue tags on same date: {len(multi_tag_conflicts):,}")
print(f"  Companies with duplicate facts for same tag+date:  {len(dup_same_tag_conflicts):,}")
print(f"  Total companies with any revenue conflict:         {len(revenue_conflicts):,}")

if multi_tag_conflicts:
    print(f"\n  Examples of multi-tag conflicts (first 5):")
    for cik in sorted(multi_tag_conflicts.keys())[:5]:
        for c in multi_tag_conflicts[cik][:2]:
            print(f"    CIK {cik}: date={c['date']}, tags={c['tags']}, values={c['values']}")

# =====================================================================
# RESOLVE NET INCOME AND OCF (simpler — single tag each)
# =====================================================================
ni_resolved = {}   # cik -> {date_str: fact}
ni_duplicates = {}
ocf_resolved = {}
ocf_duplicates = {}

for metric, resolved_dict, dup_dict in [
    ("net_income", ni_resolved, ni_duplicates),
    ("ocf", ocf_resolved, ocf_duplicates),
]:
    for cik in sorted(all_ciks_with_data):
        facts = facts_by_company.get((cik, metric), [])
        if not facts:
            continue
        by_date = defaultdict(list)
        for f in facts:
            by_date[f["date"]].append(f)

        dates_resolved = {}
        dups_for_cik = []
        for date_str, date_facts in by_date.items():
            if len(date_facts) > 1:
                dups_for_cik.append({
                    "date": date_str,
                    "tag": date_facts[0]["tag"],
                    "values": [f["value"] for f in date_facts],
                    "count": len(date_facts),
                })
            dates_resolved[date_str] = date_facts[0]

        resolved_dict[cik] = dates_resolved
        if dups_for_cik:
            dup_dict[cik] = dups_for_cik

print(f"\n  Net Income duplicate-date companies: {len(ni_duplicates):,}")
print(f"  OCF duplicate-date companies:        {len(ocf_duplicates):,}")

# =====================================================================
# YOY PAIR VALIDATION
# =====================================================================
print(f"\n{'=' * 70}")
print("YOY PAIR VALIDATION (qtrs=3, dates ~1 year apart)")
print("=" * 70)

def find_yoy_pairs(resolved_dates):
    """
    Given {date_str: fact}, find pairs where dates are approximately 1 year
    apart (364-367 days, to allow leap year variation).
    Returns list of (prior_fact, current_fact) tuples.
    """
    items = []
    for date_str, fact in resolved_dates.items():
        dp = fact["date_parsed"]
        if dp is not None:
            items.append((dp, date_str, fact))

    items.sort(key=lambda x: x[0])
    pairs = []
    used = set()

    # For each pair of dates, check if they are ~1 year apart
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            d_prior, ds_prior, f_prior = items[i]
            d_current, ds_current, f_current = items[j]
            delta = (d_current - d_prior).days
            if 360 <= delta <= 370:  # ~1 year, allowing calendar variation
                if ds_prior not in used and ds_current not in used:
                    pairs.append((f_prior, f_current))
                    used.add(ds_prior)
                    used.add(ds_current)
                    break  # Move to next prior date

    return pairs

# Validate for each company that has all three metrics
valid_companies = []
excluded_no_pair = {"revenue": 0, "net_income": 0, "ocf": 0}
excluded_reasons = defaultdict(list)

company_details = {}  # for examples

for cik in sorted(ciks_all_three):
    rev_dates = revenue_resolved.get(cik, {})
    ni_dates = ni_resolved.get(cik, {})
    ocf_dates = ocf_resolved.get(cik, {})

    rev_pairs = find_yoy_pairs(rev_dates)
    ni_pairs = find_yoy_pairs(ni_dates)
    ocf_pairs = find_yoy_pairs(ocf_dates)

    if not rev_pairs:
        excluded_no_pair["revenue"] += 1
    if not ni_pairs:
        excluded_no_pair["net_income"] += 1
    if not ocf_pairs:
        excluded_no_pair["ocf"] += 1

    if rev_pairs and ni_pairs and ocf_pairs:
        # Additional check: verify units and duration compatibility
        # All should be USD and qtrs=3 (already filtered, but verify)
        compatible = True
        for pairs, name in [(rev_pairs, "revenue"), (ni_pairs, "net_income"), (ocf_pairs, "ocf")]:
            for prior, current in pairs:
                if prior["uom"] != current["uom"]:
                    compatible = False
                    excluded_reasons[cik].append(f"{name}: unit mismatch {prior['uom']} vs {current['uom']}")
                if prior["qtrs"] != current["qtrs"]:
                    compatible = False
                    excluded_reasons[cik].append(f"{name}: qtrs mismatch {prior['qtrs']} vs {current['qtrs']}")

        if compatible:
            valid_companies.append(cik)
            company_details[cik] = {
                "name": rev_pairs[0][0].get("name", ""),
                "revenue_pairs": [(p["date"], p["value"], c["date"], c["value"], p["tag"]) for p, c in rev_pairs],
                "ni_pairs": [(p["date"], p["value"], c["date"], c["value"]) for p, c in ni_pairs],
                "ocf_pairs": [(p["date"], p["value"], c["date"], c["value"]) for p, c in ocf_pairs],
            }
        else:
            excluded_no_pair["revenue"] += 0  # already counted above if applicable
    else:
        if cik not in excluded_reasons:
            missing = []
            if not rev_pairs:
                missing.append("revenue")
            if not ni_pairs:
                missing.append("net_income")
            if not ocf_pairs:
                missing.append("ocf")
            excluded_reasons[cik].append(f"missing YoY pair for: {', '.join(missing)}")

# --- Final counts ---
print(f"\n  Companies with all three qtrs=3 metrics:         {len(ciks_all_three):,}")
print(f"  Companies with valid YoY pairs for ALL THREE:     {len(valid_companies):,}")
print(f"  Companies excluded (missing >= 1 valid pair):     {len(ciks_all_three) - len(valid_companies):,}")
print(f"\n  Exclusion breakdown (companies missing YoY pair):")
print(f"    Missing revenue pair:      {excluded_no_pair['revenue']:,}")
print(f"    Missing net income pair:   {excluded_no_pair['net_income']:,}")
print(f"    Missing OCF pair:          {excluded_no_pair['ocf']:,}")
print(f"    Incompatible units/qtrs:   {len(excluded_reasons) - sum(1 for v in excluded_reasons.values() if any('missing' in r for r in v)):,}")

print(f"\n  Revenue tag conflicts:       {len(multi_tag_conflicts):,}")
print(f"  Revenue same-tag duplicates: {len(dup_same_tag_conflicts):,}")
print(f"  NI duplicate-date facts:     {len(ni_duplicates):,}")
print(f"  OCF duplicate-date facts:    {len(ocf_duplicates):,}")

# --- Examples ---
print(f"\n{'=' * 70}")
print("EXAMPLE COMPANY-PERIOD PAIRS (first 10 valid companies)")
print("=" * 70)
for cik in valid_companies[:10]:
    d = company_details[cik]
    print(f"\n  CIK {cik} — {d['name']}")
    for prior_date, prior_val, curr_date, curr_val, tag in d["revenue_pairs"][:1]:
        print(f"    Revenue ({tag}):")
        print(f"      Prior: {prior_date} = {prior_val:>20,.0f}")
        print(f"      Curr:  {curr_date} = {curr_val:>20,.0f}")
    for prior_date, prior_val, curr_date, curr_val in d["ni_pairs"][:1]:
        print(f"    Net Income:")
        print(f"      Prior: {prior_date} = {prior_val:>20,.0f}")
        print(f"      Curr:  {curr_date} = {curr_val:>20,.0f}")
    for prior_date, prior_val, curr_date, curr_val in d["ocf_pairs"][:1]:
        print(f"    OCF:")
        print(f"      Prior: {prior_date} = {prior_val:>20,.0f}")
        print(f"      Curr:  {curr_date} = {curr_val:>20,.0f}")

# --- Save detailed results as JSON for the markdown report ---
results = {
    "total_rows_scanned": total_rows,
    "qtrs3_research_rows": qtrs3_research_rows,
    "companies_with_all_three_qtrs3": len(ciks_all_three),
    "valid_yoy_companies": len(valid_companies),
    "excluded_companies": len(ciks_all_three) - len(valid_companies),
    "excluded_missing_revenue_pair": excluded_no_pair["revenue"],
    "excluded_missing_ni_pair": excluded_no_pair["net_income"],
    "excluded_missing_ocf_pair": excluded_no_pair["ocf"],
    "revenue_multi_tag_conflicts": len(multi_tag_conflicts),
    "revenue_same_tag_duplicates": len(dup_same_tag_conflicts),
    "ni_duplicate_dates": len(ni_duplicates),
    "ocf_duplicate_dates": len(ocf_duplicates),
    "valid_company_ciks": valid_companies[:50],  # first 50 for reference
    "example_conflicts": {cik: conflicts[:2] for cik, conflicts in list(multi_tag_conflicts.items())[:10]},
    "example_ni_dups": {cik: dups[:2] for cik, dups in list(ni_duplicates.items())[:5]},
    "example_ocf_dups": {cik: dups[:2] for cik, dups in list(ocf_duplicates.items())[:5]},
}

results_path = os.path.join(OUT_DIR, "yoy_validation_results.json")
with open(results_path, "w") as f:
    json.dump(results, f, indent=2, default=str)
print(f"\n\nSaved detailed results: {results_path}")

print(f"\n{'=' * 70}")
print("VALIDATION COMPLETE")
print("=" * 70)
