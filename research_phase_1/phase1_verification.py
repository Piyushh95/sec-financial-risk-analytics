#!/usr/bin/env python3
"""
Phase 1 Verification — Coverage & Comparability Check
======================================================
Reads sec_metric_facts.csv in chunks. Applies proposed filters and measures
exact company coverage for the three key metrics and YoY comparability.

Does NOT modify the original dataset or Phase 1 outputs.
"""
import pandas as pd
import numpy as np
from collections import defaultdict
import os

DATA_FILE = r"F:\Big4_Project\sec_metric_facts.csv"
OUT_DIR = r"F:\Big4_Project\research_phase_1"
CHUNKSIZE = 200_000

# --- Tag mappings ---
REVENUE_TAGS = {
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
}
NET_INCOME_TAGS = {"NetIncomeLoss"}
OCF_TAGS = {"NetCashProvidedByUsedInOperatingActivities"}
ALL_RESEARCH_TAGS = REVENUE_TAGS | NET_INCOME_TAGS | OCF_TAGS

# --- Accumulators ---
# Track per-company, per-metric: set of (date, qtrs) tuples found
# BEFORE filtering (raw)
raw_companies_revenue = set()
raw_companies_ni = set()
raw_companies_ocf = set()

# AFTER filtering (consolidated, USD, 10-Q/10-K, value non-null)
filtered_companies_revenue = set()
filtered_companies_ni = set()
filtered_companies_ocf = set()

# For YoY comparability: track (cik, qtrs, fiscal_context) -> set of dates
# This lets us see which companies have the same metric for multiple years
revenue_periods = defaultdict(set)   # key: (cik, qtrs) -> set of dates
ni_periods = defaultdict(set)
ocf_periods = defaultdict(set)

# For understanding what "prior year" data looks like
# Track (cik, tag) -> set of (date, qtrs, fy, fp)
detail_tracker = defaultdict(set)

# Counters for filter funnel
total_rows = 0
after_tag_filter = 0
after_form_filter = 0
after_usd_filter = 0
after_segment_filter = 0
after_coreg_filter = 0
after_value_filter = 0

# Track segment/coreg impact per metric
segment_impact = defaultdict(lambda: {"before": 0, "after": 0})

VALID_FORMS = {"10-Q", "10-K", "10-Q/A", "10-K/A", "20-F", "40-F", "20-F/A"}

print("=" * 70)
print("PHASE 1 VERIFICATION: Coverage & Comparability")
print("=" * 70)
print(f"\nReading: {DATA_FILE}")
print(f"Revenue tags: {sorted(REVENUE_TAGS)}")
print(f"Net income tags: {sorted(NET_INCOME_TAGS)}")
print(f"OCF tags: {sorted(OCF_TAGS)}")
print()

for i, chunk in enumerate(pd.read_csv(DATA_FILE, chunksize=CHUNKSIZE, low_memory=False)):
    total_rows += len(chunk)

    # Step 1: Filter to research tags only
    mask_tag = chunk["tag"].isin(ALL_RESEARCH_TAGS)
    research = chunk[mask_tag].copy()
    after_tag_filter += len(research)

    if research.empty:
        continue

    # Classify each row by metric category
    research["metric"] = "other"
    research.loc[research["tag"].isin(REVENUE_TAGS), "metric"] = "revenue"
    research.loc[research["tag"].isin(NET_INCOME_TAGS), "metric"] = "net_income"
    research.loc[research["tag"].isin(OCF_TAGS), "metric"] = "ocf"

    # Raw company counts (before any filtering)
    cik_col = research["cik"].astype(str)
    for _, row in research.iterrows():
        cik = str(row["cik"])
        m = row["metric"]
        if m == "revenue":
            raw_companies_revenue.add(cik)
        elif m == "net_income":
            raw_companies_ni.add(cik)
        elif m == "ocf":
            raw_companies_ocf.add(cik)

    # Step 2: Filter to valid forms
    mask_form = research["form"].isin(VALID_FORMS)
    research = research[mask_form]
    after_form_filter += len(research)

    if research.empty:
        continue

    # Step 3: Filter to USD
    mask_usd = research["uom"] == "USD"
    research = research[mask_usd]
    after_usd_filter += len(research)

    if research.empty:
        continue

    # Count before segment filter (per metric)
    for m in ["revenue", "net_income", "ocf"]:
        segment_impact[m]["before"] += len(research[research["metric"] == m])

    # Step 4: Filter segments to empty
    mask_seg = research["segments"].fillna("").str.strip() == ""
    research = research[mask_seg]
    after_segment_filter += len(research)

    if research.empty:
        continue

    # Step 5: Filter coreg to empty
    mask_coreg = research["coreg"].fillna("").str.strip() == ""
    research = research[mask_coreg]
    after_coreg_filter += len(research)

    if research.empty:
        continue

    # Count after segment+coreg filter (per metric)
    for m in ["revenue", "net_income", "ocf"]:
        segment_impact[m]["after"] += len(research[research["metric"] == m])

    # Step 6: Filter to non-null values
    mask_val = research["value"].notna()
    research = research[mask_val]
    after_value_filter += len(research)

    if research.empty:
        continue

    # Filtered company counts & period tracking
    for _, row in research.iterrows():
        cik = str(row["cik"])
        m = row["metric"]
        date_val = str(row["date"])
        qtrs_val = str(row.get("qtrs", ""))
        fy_val = str(row.get("fy", ""))
        fp_val = str(row.get("fp", ""))

        if m == "revenue":
            filtered_companies_revenue.add(cik)
            revenue_periods[(cik, qtrs_val)].add(date_val)
            detail_tracker[(cik, "revenue")].add((date_val, qtrs_val, fy_val, fp_val))
        elif m == "net_income":
            filtered_companies_ni.add(cik)
            ni_periods[(cik, qtrs_val)].add(date_val)
            detail_tracker[(cik, "net_income")].add((date_val, qtrs_val, fy_val, fp_val))
        elif m == "ocf":
            filtered_companies_ocf.add(cik)
            ocf_periods[(cik, qtrs_val)].add(date_val)
            detail_tracker[(cik, "ocf")].add((date_val, qtrs_val, fy_val, fp_val))

    if (i + 1) % 3 == 0:
        print(f"  Processed {total_rows:,} rows...")

print(f"  Finished scanning {total_rows:,} rows.\n")

# =====================================================================
# QUESTION 1: Unique companies with usable facts after filters
# =====================================================================
print("=" * 70)
print("Q1: UNIQUE COMPANIES WITH USABLE FACTS (after all filters)")
print("=" * 70)
print(f"\n  Filters applied:")
print(f"    - Tags: research tags only")
print(f"    - Forms: {sorted(VALID_FORMS)}")
print(f"    - UOM: USD only")
print(f"    - Segments: empty only (consolidated)")
print(f"    - Coreg: empty only (primary entity)")
print(f"    - Value: non-null only")

print(f"\n  Filter funnel (row counts):")
print(f"    Total dataset rows:           {total_rows:>10,}")
print(f"    After tag filter:             {after_tag_filter:>10,}")
print(f"    After form filter:            {after_form_filter:>10,}")
print(f"    After USD filter:             {after_usd_filter:>10,}")
print(f"    After segment=empty filter:   {after_segment_filter:>10,}")
print(f"    After coreg=empty filter:     {after_coreg_filter:>10,}")
print(f"    After value non-null filter:  {after_value_filter:>10,}")

print(f"\n  Unique companies (RAW, no filters):")
print(f"    Revenue (any tag):          {len(raw_companies_revenue):>6,}")
print(f"    NetIncomeLoss:              {len(raw_companies_ni):>6,}")
print(f"    Operating Cash Flow:        {len(raw_companies_ocf):>6,}")

print(f"\n  Unique companies (FILTERED, consolidated USD with values):")
print(f"    Revenue (any tag):          {len(filtered_companies_revenue):>6,}")
print(f"    NetIncomeLoss:              {len(filtered_companies_ni):>6,}")
print(f"    Operating Cash Flow:        {len(filtered_companies_ocf):>6,}")

all_three = filtered_companies_revenue & filtered_companies_ni & filtered_companies_ocf
rev_ni = filtered_companies_revenue & filtered_companies_ni
rev_ocf = filtered_companies_revenue & filtered_companies_ocf
ni_ocf = filtered_companies_ni & filtered_companies_ocf

print(f"\n  Company overlap:")
print(f"    Revenue AND Net Income:           {len(rev_ni):>6,}")
print(f"    Revenue AND OCF:                  {len(rev_ocf):>6,}")
print(f"    Net Income AND OCF:               {len(ni_ocf):>6,}")
print(f"    ALL THREE (Revenue+NI+OCF):       {len(all_three):>6,}")

# =====================================================================
# QUESTION 3: Segment/coreg filter impact
# =====================================================================
print(f"\n{'=' * 70}")
print("Q3: SEGMENT/COREG FILTER IMPACT ON THREE METRICS")
print("=" * 70)
for m_name in ["revenue", "net_income", "ocf"]:
    before = segment_impact[m_name]["before"]
    after = segment_impact[m_name]["after"]
    pct = (after / before * 100) if before > 0 else 0
    print(f"  {m_name:15s}: {before:>8,} rows before -> {after:>8,} after segment+coreg filter ({pct:.1f}% retained)")

# =====================================================================
# QUESTION 2 & 4: YoY comparability — do we have prior-year figures?
# =====================================================================
print(f"\n{'=' * 70}")
print("Q2 & Q4: YEAR-OVER-YEAR COMPARABILITY")
print("=" * 70)

# For each company with all three metrics, check if they have >= 2 dates
# for the same qtrs value (which would indicate prior-year data exists)
def count_multi_period_companies(periods_dict, companies_set):
    """Count companies that have >= 2 distinct dates for any single qtrs value."""
    multi_period = set()
    for (cik, qtrs), dates in periods_dict.items():
        if cik in companies_set and len(dates) >= 2:
            multi_period.add(cik)
    return multi_period

rev_multi = count_multi_period_companies(revenue_periods, filtered_companies_revenue)
ni_multi = count_multi_period_companies(ni_periods, filtered_companies_ni)
ocf_multi = count_multi_period_companies(ocf_periods, filtered_companies_ocf)

print(f"\n  Companies with >= 2 distinct dates for same qtrs value (potential YoY pairs):")
print(f"    Revenue:       {len(rev_multi):>6,} of {len(filtered_companies_revenue):,}")
print(f"    Net Income:    {len(ni_multi):>6,} of {len(filtered_companies_ni):,}")
print(f"    OCF:           {len(ocf_multi):>6,} of {len(filtered_companies_ocf):,}")

all_three_multi = rev_multi & ni_multi & ocf_multi
print(f"    ALL THREE:     {len(all_three_multi):>6,} companies have multi-period data for all three metrics")

# Detailed analysis: what qtrs values have multi-period coverage?
print(f"\n  Multi-period coverage by qtrs value:")
for qtrs_val in ["0", "1", "2", "3", "4"]:
    label = {"0": "instant", "1": "Q-only", "2": "H1-YTD", "3": "9mo-YTD", "4": "annual"}[qtrs_val]
    rev_q = {cik for (cik, q), dates in revenue_periods.items() if q == qtrs_val and cik in filtered_companies_revenue and len(dates) >= 2}
    ni_q = {cik for (cik, q), dates in ni_periods.items() if q == qtrs_val and cik in filtered_companies_ni and len(dates) >= 2}
    ocf_q = {cik for (cik, q), dates in ocf_periods.items() if q == qtrs_val and cik in filtered_companies_ocf and len(dates) >= 2}
    all_q = rev_q & ni_q & ocf_q
    print(f"    qtrs={qtrs_val} ({label:10s}):  Revenue={len(rev_q):>5,}  NI={len(ni_q):>5,}  OCF={len(ocf_q):>5,}  ALL THREE={len(all_q):>5,}")

# Sample: Show date distributions for a few companies to understand the structure
print(f"\n  Sample: date values found for first 5 'all-three-multi-period' companies:")
sample_ciks = sorted(all_three_multi)[:5]
for cik in sample_ciks:
    rev_dates = sorted(detail_tracker.get((cik, "revenue"), set()))
    ni_dates = sorted(detail_tracker.get((cik, "net_income"), set()))
    ocf_dates = sorted(detail_tracker.get((cik, "ocf"), set()))
    print(f"\n    CIK {cik}:")
    print(f"      Revenue:    {rev_dates}")
    print(f"      Net Income: {ni_dates}")
    print(f"      OCF:        {ocf_dates}")

# Detailed date distribution across ALL filtered research facts
print(f"\n{'=' * 70}")
print("DATE DISTRIBUTION OF FILTERED RESEARCH FACTS")
print("=" * 70)

all_dates_rev = set()
all_dates_ni = set()
all_dates_ocf = set()
for (cik, qtrs), dates in revenue_periods.items():
    if cik in filtered_companies_revenue:
        all_dates_rev.update(dates)
for (cik, qtrs), dates in ni_periods.items():
    if cik in filtered_companies_ni:
        all_dates_ni.update(dates)
for (cik, qtrs), dates in ocf_periods.items():
    if cik in filtered_companies_ocf:
        all_dates_ocf.update(dates)

print(f"\n  Distinct reporting dates in filtered data:")
print(f"    Revenue dates:    {sorted(all_dates_rev)}")
print(f"    Net Income dates: {sorted(all_dates_ni)}")
print(f"    OCF dates:        {sorted(all_dates_ocf)}")

# Annual (qtrs=4) specific analysis for Q4
print(f"\n{'=' * 70}")
print("ANNUAL (qtrs=4) SPECIFIC ANALYSIS")
print("=" * 70)
rev_annual = {cik for (cik, q), dates in revenue_periods.items() if q in ("4", "4.0") and cik in filtered_companies_revenue}
ni_annual = {cik for (cik, q), dates in ni_periods.items() if q in ("4", "4.0") and cik in filtered_companies_ni}
ocf_annual = {cik for (cik, q), dates in ocf_periods.items() if q in ("4", "4.0") and cik in filtered_companies_ocf}
all_annual = rev_annual & ni_annual & ocf_annual
print(f"  Companies with annual (qtrs=4) data:")
print(f"    Revenue:    {len(rev_annual):>5,}")
print(f"    Net Income: {len(ni_annual):>5,}")
print(f"    OCF:        {len(ocf_annual):>5,}")
print(f"    ALL THREE:  {len(all_annual):>5,}")

# How many of those have >= 2 annual dates?
rev_annual_multi = {cik for (cik, q), dates in revenue_periods.items() if q in ("4", "4.0") and cik in filtered_companies_revenue and len(dates) >= 2}
ni_annual_multi = {cik for (cik, q), dates in ni_periods.items() if q in ("4", "4.0") and cik in filtered_companies_ni and len(dates) >= 2}
ocf_annual_multi = {cik for (cik, q), dates in ocf_periods.items() if q in ("4", "4.0") and cik in filtered_companies_ocf and len(dates) >= 2}
all_annual_multi = rev_annual_multi & ni_annual_multi & ocf_annual_multi
print(f"\n  Companies with >= 2 annual dates (YoY annual comparison):")
print(f"    Revenue:    {len(rev_annual_multi):>5,}")
print(f"    Net Income: {len(ni_annual_multi):>5,}")
print(f"    OCF:        {len(ocf_annual_multi):>5,}")
print(f"    ALL THREE:  {len(all_annual_multi):>5,}")

print(f"\n{'=' * 70}")
print("VERIFICATION COMPLETE")
print("=" * 70)
