# Phase 1 Final Validation — 9-Month YTD YoY Comparison

> **Date**: 2026-10-17  
> **Script**: [`phase1_yoy_validation.py`](file:///f:/Big4_Project/research_phase_1/phase1_yoy_validation.py)  
> **Method**: Full scan of 991,932 rows; all filters applied; YoY pairs validated with 360–370 day tolerance  
> **No files were modified.**

---

## 1. Methodology

### Filters applied (in order)

1. **Tags**: Revenue (`RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `RevenueFromContractWithCustomerIncludingAssessedTax`), Net Income (`NetIncomeLoss`), OCF (`NetCashProvidedByUsedInOperatingActivities`)
2. **Filing forms**: 10-Q, 10-K, 20-F, 40-F and their amendments
3. **Currency**: USD only
4. **Segments**: Empty only (consolidated entity)
5. **Coreg**: Empty only (primary registrant)
6. **Value**: Non-null only
7. **Duration**: `qtrs=3` only (9-month year-to-date)

### Revenue tag hierarchy

For each company-date, if multiple revenue tags exist, select the highest-priority tag:

| Priority | Tag | Rationale |
|---:|---|---|
| 1 | `RevenueFromContractWithCustomerExcludingAssessedTax` | ASC 606 standard; most common |
| 2 | `Revenues` | Broader revenue concept |
| 3 | `RevenueFromContractWithCustomerIncludingAssessedTax` | Includes assessed taxes |

### YoY pair matching

For each company and metric, dates were sorted chronologically and paired if they are **360–370 days apart** (allowing for leap-year/calendar variation). Each date is used in at most one pair.

### Compatibility checks

Both periods in each pair were verified to share:
- Same unit of measure (USD)
- Same duration (`qtrs=3`)

---

## 2. Filter funnel

| Step | Rows |
|---|---:|
| Total dataset | 991,932 |
| Research tags only | 283,067 |
| Periodic filing forms | 266,569 |
| USD only | 265,513 |
| Segments = empty | 55,870 |
| Coreg = empty | 55,870 |
| Value non-null | 55,257 |
| **qtrs = 3 only** | **24,231** |

---

## 3. Results

### 3.1 Companies with valid YoY pairs for all three metrics

| Metric | Value |
|---|---:|
| Companies with qtrs=3 revenue data | 3,383 |
| Companies with qtrs=3 net income data | 4,229 |
| Companies with qtrs=3 OCF data | 4,462 |
| Companies with all three qtrs=3 metrics | 3,088 |
| **Companies with valid YoY pairs for ALL THREE** | **2,991** |

### 3.2 Exclusion breakdown

| Reason | Companies excluded |
|---|---:|
| Total excluded from the 3,088 with all three metrics | 97 |
| Missing a valid revenue YoY pair | 88 |
| Missing a valid net income YoY pair | 22 |
| Missing a valid OCF YoY pair | 16 |
| Incompatible units or durations between years | 0 |

> [!NOTE]
> The exclusion reasons overlap — some companies are missing pairs for multiple metrics. Revenue is the most common gap because some companies have only one date for revenue (no prior-year comparative), or their dates are not ~1 year apart (e.g., non-calendar fiscal years with unusual period boundaries).

### 3.3 Revenue tag conflicts

| Issue | Companies |
|---|---:|
| Multiple revenue tags on the same company-date | **178** |
| Duplicate facts for the same tag + date | **13** |
| Total companies with any revenue conflict | **190** |

### 3.4 Net Income and OCF duplicates

| Issue | Companies |
|---|---:|
| Net income: duplicate facts on same date | **21** |
| OCF: duplicate facts on same date | **21** |

---

## 4. Revenue tag conflict analysis

178 companies report **two different revenue tags** for the same reporting date. The hierarchy resolves these deterministically, but the values differ because the tags measure different things:

### Example conflicts

| CIK | Date | Tag 1 (selected by hierarchy) | Value 1 | Tag 2 (discarded) | Value 2 |
|---|---|---|---:|---|---:|
| 1025996 | 30-09-2024 | `RevFromContract...ExclTax` | 12,490,000 | `Revenues` | 849,250,000 |
| 1025996 | 30-09-2025 | `RevFromContract...ExclTax` | 14,256,000 | `Revenues` | 840,480,000 |
| 1051470 | 30-09-2024 | `RevFromContract...ExclTax` | 143,000,000 | `Revenues` | 3,341,000,000 |
| 1034054 | 30-09-2024 | `RevFromContract...ExclTax` | 105,504,000 | `Revenues` | 1,985,934,000 |

> [!WARNING]
> **The hierarchy can select the wrong revenue figure.** In CIK 1025996, the `RevenueFromContractWithCustomerExcludingAssessedTax` value ($12.5M) is dramatically lower than `Revenues` ($849M). This likely means the company has significant revenue streams **outside** ASC 606 contracts (e.g., interest income, investment gains). The hierarchy blindly picks the contract-revenue tag, missing 98.5% of actual revenue.
>
> **Recommendation for Phase 2**: For the 178 conflict companies, compare the values. If the priority-1 tag is <50% of the priority-2 tag, the broader `Revenues` tag is probably the appropriate total revenue measure. This requires a smarter selection rule, not a rigid hierarchy.

### Conflict pattern

Most conflicts follow one of two patterns:
1. **Contract revenue vs. total revenue**: `RevenueFromContractWithCustomerExcludingAssessedTax` captures only ASC 606 contract revenue, while `Revenues` includes all revenue sources. Common in financial services, utilities, and diversified companies.
2. **Including vs. excluding assessed tax**: `RevenueFromContractWithCustomerIncludingAssessedTax` vs. `Revenues` — typically close in value, differing only by tax pass-throughs.

---

## 5. Duplicate fact analysis

### Net Income and OCF duplicates

21 companies have **identical duplicate facts** for the same tag + date:

| CIK | Metric | Date | Value 1 | Value 2 | Identical? |
|---|---|---|---:|---:|---|
| 1005817 | NI | 30-09-2024 | 51,192,000 | 51,192,000 | Yes |
| 1005817 | OCF | 30-09-2024 | 71,717,000 | 71,717,000 | Yes |
| 1130310 | NI | 30-09-2024 | 771,000,000 | 771,000,000 | Yes |
| 1130310 | OCF | 30-09-2024 | 1,250,000,000 | 1,250,000,000 | Yes |
| 1128281 | NI | 30-09-2024 | 736,868 | 736,868 | Yes |

All examined duplicate pairs have **identical values**. These are likely caused by the extraction script matching on multiple tag/version combinations that resolve to the same fact. Taking either row is safe — the values are consistent.

> [!NOTE]
> The same 21 companies appear in both the NI and OCF duplicate lists. This suggests a structural cause (possibly dual taxonomy versions in the same filing) rather than a data error.

---

## 6. Prior-year data verification

### Confirmed: the dataset contains prior-year comparative figures

SEC 10-Q filings are required to include comparative prior-period figures. The validation confirms this structure across all 2,991 valid companies:

**Typical pattern** (CIK 1000228, HENRY SCHEIN INC):
```
Revenue:     30-09-2024 (prior) = $9,482,000,000
             30-09-2025 (curr)  = $9,747,000,000    [365 days apart]

Net Income:  30-09-2024 (prior) = $296,000,000
             30-09-2025 (curr)  = $297,000,000      [365 days apart]

OCF:         30-09-2024 (prior) = $644,000,000
             30-09-2025 (curr)  = $331,000,000      [365 days apart]
```

All three metrics have dates exactly one year apart, same units (USD), same duration (qtrs=3 / 9-month YTD).

### Date pair distribution

The overwhelming majority of YoY pairs compare:
- **30-09-2024 vs 30-09-2025** (calendar Q3 filers, FY ending December)
- Other common pairs: 31-07-2024 vs 31-07-2025, 30-06-2024 vs 30-06-2025 (non-calendar FY companies)

---

## 7. Example company-period pairs for manual verification

| CIK | Company | Prior Revenue | Current Revenue | Prior NI | Current NI | Prior OCF | Current OCF |
|---|---|---:|---:|---:|---:|---:|---:|
| 1000228 | HENRY SCHEIN | 9,482M | 9,747M | 296M | 297M | 644M | 331M |
| 1000623 | MATIV HOLDINGS | 1,523M | 1,524M | -50M | -438M | 71M | 115M |
| 1000694 | NOVAVAX | 594M | 976M | -106M | 423M | 86M | -205M |
| 1000697 | WATERS CORP | 2,086M | 2,233M | 406M | 417M | 522M | 488M |
| 1000753 | INSPERITY | 4,968M | 5,144M | 100M | 26M | -99M | -533M |
| 1001082 | DISH NETWORK | 10,723M | 10,187M | -436M | -12,930M | 874M | 155M |
| 100122 | TUCSON ELECTRIC | 1,434M | 1,317M | 262M | 260M | 531M | 454M |
| 1001233 | SANGAMO THERAPEUTICS | 50M | 25M | -75M | -86M | -64M | -73M |
| 1001316 | TG THERAPEUTICS | 221M | 424M | 0.05M | 424M | -15M | -44M |
| 1001385 | NWPX INFRASTRUCTURE | 373M | 400M | 24M | 27M | 19M | 31M |

> [!NOTE]
> Several examples already show interesting divergence patterns (e.g., NOVAVAX: revenue +64%, NI swings from loss to profit, but OCF swings from positive to negative). These patterns should be investigated in Phase 2 — they may reflect timing of cash collections, working capital changes, or one-time items.

---

## 8. Summary of exact counts

| Metric | Count |
|---|---:|
| Companies with valid 9-mo YTD YoY pairs for **all three metrics** | **2,991** |
| Companies excluded (missing one or more valid pairs) | 97 |
| Revenue tag conflicts (multi-tag on same date) | 178 |
| Revenue same-tag duplicates | 13 |
| NI duplicate-date facts | 21 |
| OCF duplicate-date facts | 21 |
| Unit/duration incompatibilities | 0 |

---

## 9. Limitations and open issues for Phase 2

1. **Revenue hierarchy is too rigid for 178 companies.** The fixed priority can select a narrow contract-revenue tag that misses most of a company's actual revenue. Phase 2 should compare values and select the tag that best represents total revenue.
2. **21 companies have exact-duplicate facts** for NI and OCF. These are safe to deduplicate (identical values), but the root cause (likely dual taxonomy versions) should be confirmed.
3. **97 companies lack valid YoY pairs** despite having all three metrics for at least one period. Most are companies with non-standard fiscal years where the prior-year date is not exactly ~365 days before the current date (e.g., fiscal year transitions, IPOs with partial-year filings).
4. **All 2,991 valid pairs passed compatibility checks.** No unit mismatches or duration inconsistencies were found.
5. **These are 9-month YTD figures**, not single-quarter. Revenue growth computed from these pairs reflects cumulative 9-month performance, which smooths out quarterly seasonality but may obscure quarter-specific divergences.
