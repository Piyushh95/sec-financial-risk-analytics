# Phase 1 Dataset Audit — SEC Financial Facts

> **Project**: Big4 Financial Reporting Risk Monitor  
> **Dataset**: `sec_metric_facts.csv`  
> **Audit date**: 2026-10-17  
> **Auditor**: Automated Phase 1 audit (phase1_audit.py)

---

## 1. Dataset Overview

| Metric | Value |
|---|---|
| **Total rows** | 991,932 |
| **Unique companies (CIK)** | 5,785 |
| **Unique filings (adsh)** | 6,295 |
| **Unique XBRL tags** | 7,808 |
| **Reporting date range** | 2015-02-28 to 2029-12-31 |
| **Filing period range** | 2022-03-31 to 2025-12-31 |
| **Filing date range** | 2025-10-01 to 2025-12-31 |
| **Source files** | `num.txt` (541 MB), `sub.txt` (1.8 MB), `tag.txt` (17 MB), `pre.txt` (84 MB) |

### Key observation

The **filing dates** span only Oct–Dec 2025, indicating this dataset was extracted from a **single quarterly release** of the SEC Financial Statement Data Sets (likely 2025-Q4). The reporting dates (`date` / `ddate`) go further back because filings include comparative-period figures from prior years.

---

## 2. Schema & Column Dictionary

The dataset has **24 columns**, merging data from three SEC source files:

### From NUM.txt (numeric facts)
| Column | Type | Missingness | SEC Definition |
|---|---|---|---|
| `adsh` | str | 0 | Accession number — unique 20-char identifier for each EDGAR submission |
| `tag` | str | 0 | XBRL tag name (e.g., `Revenues`, `NetIncomeLoss`) |
| `version` | str | 0 | Taxonomy version (e.g., `us-gaap/2025`) |
| `date` | str | 0 | Period end date for this fact (DD-MM-YYYY format); renamed from `ddate` during extraction |
| `qtrs` | int | 0 | Duration in quarters: 0 = instant/balance-sheet, 1 = single quarter, 4 = full year |
| `uom` | str | 0 | Unit of measure (USD, shares, pure, etc.) |
| `segments` | str | 458,449 (46%) | Dimensional breakdown tags; empty = consolidated entity |
| `coreg` | str | 979,724 (99%) | Co-registrant identifier; empty = primary filing entity |
| `value` | float | **40,035 (4%)** | Numeric value of the financial fact |
| `footnote` | str | 990,073 (99.8%) | XBRL footnote text; rarely populated |

### From TAG.txt (taxonomy metadata)
| Column | Type | Missingness | SEC Definition |
|---|---|---|---|
| `tlabel` | str | 0 | Human-readable label for the tag |
| `datatype` | str | 0 | XBRL data type (monetary, perShare, percent, etc.) |
| `iord` | str | 0 | Instant (I) or Duration (D) — matches balance sheet vs income statement |
| `crdr` | str | 142,730 (14%) | Credit (C) or Debit (D) natural balance; missing for non-monetary types |
| `custom` | str | 0 | 0 = standard US-GAAP tag; 1 = company-specific custom tag |

### From SUB.txt (submission metadata)
| Column | Type | Missingness | SEC Definition |
|---|---|---|---|
| `cik` | int | 0 | Central Index Key — SEC company identifier |
| `name` | str | 0 | Company name |
| `sic` | float | 77,803 (8%) | Standard Industrial Classification code |
| `form` | str | 0 | Filing type (10-Q, 10-K, etc.) |
| `period` | str | 0 | Filing period end date (YYYYMMDD format) |
| `fy` | float | 51,134 (5%) | Fiscal year |
| `fp` | str | 51,134 (5%) | Fiscal period (Q1, Q2, Q3, FY) |
| `filed` | str | 0 | Date the filing was submitted to SEC |
| `prevrpt` | int | 0 | 0 = current filing; 1 = superseded by a later amendment |

---

## 3. Filing Type Distribution

| Form | Rows | % | Description |
|---|---|---|---|
| **10-Q** | 821,337 | **82.8%** | Quarterly reports (primary) |
| **10-K** | 60,325 | 6.1% | Annual reports |
| **6-K** | 25,980 | 2.6% | Foreign private issuer reports |
| **S-1** | 18,471 | 1.9% | Registration statements |
| **20-F** | 15,117 | 1.5% | Foreign annual reports |
| **S-1/A** | 11,520 | 1.2% | Amended registration statements |
| **10-Q/A** | 7,094 | 0.7% | Amended quarterly reports |
| Other (18 types) | 32,088 | 3.2% | Various registration, transition, and specialty forms |

### Fiscal Period Distribution

| Period | Rows | Notes |
|---|---|---|
| Q3 | 759,846 | Dominant — confirms Q3 2025 filings |
| FY | 88,350 | Full-year filings (annual reports, non-calendar FY companies) |
| Q2 | 59,697 | Prior-quarter comparatives |
| Q1 | 32,905 | Prior-quarter comparatives |

---

## 4. Duration/Period Type Analysis (qtrs)

The `qtrs` column critically distinguishes **what time period a fact covers**:

| qtrs | Meaning | Row Count | % |
|---|---|---|---|
| **0** | Instant (balance sheet point-in-time) | 258,771 | 26.1% |
| **1** | Single quarter | 315,046 | 31.8% |
| **2** | Two quarters (H1 cumulative) | 36,268 | 3.7% |
| **3** | Three quarters (9-month YTD) | 313,625 | 31.6% |
| **4** | Full year (annual) | 68,117 | 6.9% |
| **5–101** | Non-standard durations | 101 | <0.01% |

> [!IMPORTANT]
> **Year-to-date vs. quarterly**: The SEC data provides **cumulative** (YTD) figures, not isolated quarterly values. A `qtrs=3` revenue figure is 9-month YTD, not Q3 alone. To get Q3-only revenue, you must subtract the `qtrs=2` (H1) figure from the `qtrs=3` figure. This is essential for our research question.

> [!WARNING]
> 101 rows have non-standard `qtrs` values (5–101). These are likely transition periods, unusual fiscal years, or data anomalies. They should be excluded or investigated individually.

---

## 5. Data Quality Issues

### 5.1 Missing Values

| Column | Missing | % | Severity | Notes |
|---|---|---|---|---|
| `value` | **40,035** | 4.04% | **MEDIUM** | Facts without numeric values — may be text-only disclosures or reporting errors |
| `segments` | 458,449 | 46.2% | LOW | Empty = consolidated entity (expected) |
| `coreg` | 979,724 | 98.8% | LOW | Empty = primary registrant (expected) |
| `footnote` | 990,073 | 99.8% | LOW | Rarely populated (normal) |
| `crdr` | 142,730 | 14.4% | LOW | Missing for non-monetary types (expected) |
| `sic` | 77,803 | 7.8% | LOW | Some filers lack SIC codes |
| `fy` / `fp` | 51,134 | 5.2% | LOW | Missing for non-standard filing types (S-1, F-1, etc.) |

### 5.2 Corrupted Data

- **1 row** has a corrupted `date` value (a long string of `#` characters)
  - Filing: `0001213900-25-108212` (KAYNE ANDERSON BDC, INC.)
  - Tag: `InvestmentOwnedPercentOfNetAssets`
  - **Impact**: Negligible — single row, investment fund metric

### 5.3 Duplicate Key Analysis

Using the key `(adsh, tag, version, date, qtrs, uom)`:

| Metric | Value |
|---|---|
| Total unique keys | 475,438 |
| Keys appearing >1 time | 112,178 |
| Total rows in duplicate groups | 628,672 (63.4%) |

> [!IMPORTANT]
> **Most "duplicates" are legitimate** — they represent the same fact reported with different **segments** (business units, geographic regions) or different **co-registrants**. The 533,483 rows with non-empty `segments` (54%) explain the bulk of these duplicate keys.

**Top repeated keys** are all `InvestmentOwnedPercentOfNetAssets` from investment funds — these funds report hundreds of individual investment positions, each as a separate segmented fact sharing the same key.

**To get unduplicated consolidated facts**, filter to `segments = empty AND coreg = empty`. This is essential before constructing company-level financial metrics.

### 5.4 Amended Filings (prevrpt)

All 991,932 rows have `prevrpt = 0`, meaning **no amended/superseded filing data** is present. This is clean — we don't need to deduplicate original vs. amended filings.

### 5.5 Value Statistics

| Metric | Value |
|---|---|
| Non-null values | 951,897 |
| Negative values | 166,359 (17.5%) |
| Zero values | 72,727 (7.6%) |
| Min value | -7,993,750,000,000 |
| Max value | 405,940,211,000,000 |

Negative values are expected (net losses, expense offsets, etc.). The extreme values (trillions) may be legitimate (sovereign/fund entities) or warrant individual review.

### 5.6 Units of Measure

| UOM | Rows | Notes |
|---|---|---|
| USD | 895,883 (90.3%) | US Dollars — primary unit |
| pure | 71,595 (7.2%) | Ratios/percentages |
| CAD, CNY, JPY, EUR, etc. | 24,454 (2.5%) | Foreign currency filers |

> [!NOTE]
> For cross-company comparison, we should filter to `uom = USD` or handle currency conversion. The 2.5% foreign-currency rows are from 20-F and 6-K filers.

---

## 6. Financial Metric Availability

### 6.1 Revenue Tags

| Tag | Facts | Companies | Notes |
|---|---|---|---|
| `RevenueFromContractWithCustomerExcludingAssessedTax` | 115,709 | 2,442 | **Primary revenue tag** (ASC 606 standard) |
| `Revenues` | 51,688 | 1,853 | Broader revenue concept |
| `RevenueFromContractWithCustomerIncludingAssessedTax` | 16,904 | 495 | Includes taxes assessed on customers |
| `SalesRevenueNet` | — | — | Not found (deprecated tag from older GAAP) |
| `SalesRevenueGoodsNet` | — | — | Not found |
| `SalesRevenueServicesNet` | — | — | Not found |

### 6.2 Profitability Tags

| Tag | Facts | Companies | Notes |
|---|---|---|---|
| `NetIncomeLoss` | 84,644 | 5,351 | **Primary net income tag** — attributable to parent |
| `ProfitLoss` | 39,315 | 2,821 | Including noncontrolling interest |
| `OperatingIncomeLoss` | 33,926 | 4,347 | Operating income |
| `NetIncomeLossAvailableToCommonStockholdersBasic` | 5,080 | 876 | After preferred dividends |
| `GrossProfit` | 15,976 | 2,167 | Revenue minus COGS |

### 6.3 Cash Flow Tags

| Tag | Facts | Companies | Notes |
|---|---|---|---|
| `NetCashProvidedByUsedInOperatingActivities` | 14,122 | 5,545 | **Primary OCF tag** |
| `NetCashProvidedByUsedInOperatingActivitiesContinuingOperations` | 646 | 235 | Continuing operations only |

### 6.4 Balance Sheet Tags

| Tag | Facts | Companies | Notes |
|---|---|---|---|
| `Assets` | 28,200 | 5,763 | **Total assets** |
| `AssetsCurrent` | 11,377 | 4,416 | Current assets |
| `AccountsReceivableNetCurrent` | 8,450 | 2,842 | A/R current |
| `AccountsPayableCurrent` | 9,164 | 3,209 | A/P current |

### 6.5 Other Tags

| Tag | Facts | Companies | Notes |
|---|---|---|---|
| `DepreciationDepletionAndAmortization` | 13,890 | 2,237 | D&A |
| `EarningsPerShareBasic` | 24,716 | 5,124 | Basic EPS |
| `EarningsPerShareDiluted` | 24,458 | 5,044 | Diluted EPS |
| `CostOfGoodsAndServicesSold` | 22,398 | 1,697 | COGS |

---

## 7. Critical Findings & Limitations

### 7.1 Confirmed Facts

1. The dataset contains **991,932 rows** covering **5,785 companies** and **6,295 filings**.
2. All key financial metrics needed for the research question (revenue, net income, operating cash flow) **are present** with substantial coverage.
3. The `qtrs` column reliably distinguishes instant vs. duration facts and quarterly vs. YTD vs. annual figures.
4. No amended filing overlap exists (`prevrpt` = 0 for all rows).
5. The data is from a **single SEC quarterly release** (filing dates Oct–Dec 2025).
6. **54% of rows** contain segment-level breakdowns, not consolidated totals.

### 7.2 Limitations

1. **Single-quarter coverage**: Only ~3 months of new filings. Comparative periods go back to 2015, but coverage is sparse before 2022.
2. **YTD figures require subtraction**: Revenue/income for Q3 alone must be computed as `qtrs=3` minus `qtrs=2`. This requires both figures to exist for the same company/period.
3. **Multiple revenue tags**: Companies use different revenue tags depending on their GAAP version and industry. No single tag covers all companies.
4. **Segment proliferation**: Investment funds report hundreds of per-position facts, inflating row counts.
5. **Missing SIC codes**: 7.8% of rows lack industry classification.
6. **4% missing values**: ~40K facts have no numeric value. These must be excluded from calculations.

### 7.3 Hypotheses to Verify in Phase 2

- Revenue-to-net-income divergence analysis is feasible for companies reporting both tags in the same period, but coverage overlap needs to be measured.
- Operating cash flow coverage (5,545 companies) is strong and nearly matches net income coverage (5,351), suggesting good overlap for income-vs-OCF analysis.
- Segment filtering (`segments = empty`) is critical before any company-level aggregation.

---

## 8. Methods & Reproducibility

All analysis was performed using:
- **Script**: [`phase1_audit.py`](file:///f:/Big4_Project/research_phase_1/phase1_audit.py) (chunked pandas, 200K rows/chunk)
- **Completion**: [`phase1_completion.py`](file:///f:/Big4_Project/research_phase_1/phase1_completion.py) (metrics summary)
- **Environment**: Python 3.14, pandas, Windows
- **No modifications** were made to the original dataset or existing scripts.
