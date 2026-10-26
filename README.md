# SEC Financial Risk Analytics

An end-to-end financial analytics project using SEC company filings to validate financial data, analyze revenue and profitability trends, assess operating cash flow, and identify financial patterns that warrant further investigation.

## Business Objective

Detect companies where **revenue growth materially diverges from net income or operating cash flow growth** using publicly available SEC XBRL filings. Divergence patterns can indicate timing differences, working capital shifts, accounting policy changes, or other factors worth investigating — they are treated as signals for further review, not conclusions.

## Data Source

- **SEC Financial Statement Data Sets** (public): [https://www.sec.gov/dera/data/financial-statement-data-sets](https://www.sec.gov/dera/data/financial-statement-data-sets)
- Source files: `num.txt` (numeric facts), `sub.txt` (submission metadata), `tag.txt` (XBRL taxonomy), `pre.txt` (presentation data)
- The raw dataset is **not included** in this repository due to its size (~700 MB combined). Download directly from the SEC link above.

## Project Status

### Phase 1: Data Validation (complete)

- Extracted ~992K financial facts across 5,785 companies from the SEC quarterly release
- Applied multi-stage filters: consolidated entities only, USD, standard filing forms (10-Q, 10-K), non-null values
- Validated year-over-year comparability for 9-month YTD figures (`qtrs=3`)
- Confirmed **2,991 companies** with valid YoY pairs across all three key metrics (revenue, net income, operating cash flow)
- Documented revenue tag hierarchy, duplicate facts, and tag conflict patterns

### Phase 2: Duplicate Investigation (in progress)

- Identified and classified revenue duplicate groups (amended filings, identical duplicates, value changes)
- Full audit of all duplicate groups with original vs. amended filing comparison
- Two companies flagged with amended revenue value changes requiring manual review

### Phase 3: Divergence Analysis (planned)

- Compute YoY growth rates for revenue, net income, and OCF
- Flag companies with material divergences between metrics
- Contextualize findings with industry (SIC) codes and plausible explanations

## Repository Structure

```
research_phase_1/
├── phase1_verification.py            # Coverage and comparability checks
├── phase1_yoy_validation.py          # YoY pair validation with tag hierarchy
├── phase1_yoy_validation.md          # Detailed validation findings
├── dataset_audit.md                  # Full dataset schema and quality audit
├── phase2_duplicate_full_audit.py    # Duplicate classification and audit
├── phase2_duplicate_full_audit.csv   # Audit results (21 duplicate groups)
└── phase2_revenue_diagnostics.py     # Revenue tag conflict diagnostics
```

## How to Run

### Prerequisites

- Python 3.10+
- pandas

### Data Setup

1. Download the SEC Financial Statement Data Sets from the SEC website
2. Place `num.txt`, `sub.txt`, `tag.txt`, and `pre.txt` in the project root
3. Run the extraction script to produce `sec_metric_facts.csv`:
   ```bash
   python extract_sec_metrics.py --num num.txt --tag tag.txt --sub sub.txt --out sec_metric_facts.csv
   ```

### Running the Analysis Scripts

```bash
# Phase 1: verify coverage and comparability
python research_phase_1/phase1_verification.py

# Phase 1: validate YoY pairs
python research_phase_1/phase1_yoy_validation.py

# Phase 2: audit revenue duplicates
python research_phase_1/phase2_duplicate_full_audit.py

# Phase 2: revenue tag conflict diagnostics
python research_phase_1/phase2_revenue_diagnostics.py
```

> **Note**: The Phase 1 verification and YoY validation scripts reference hardcoded local paths for the dataset. Update the `DATA_FILE` and `OUT_DIR` variables in those scripts to match your local directory structure before running.

## Data Limitations and Caveats

1. **Single-quarter SEC release**: The dataset covers filings from one quarterly release (Oct–Dec 2025). Multi-year trend analysis requires additional releases.
2. **YTD figures, not quarterly**: The 9-month (`qtrs=3`) values are year-to-date cumulative, not single-quarter. Growth rates reflect cumulative performance.
3. **Revenue tag inconsistency**: Companies use different XBRL tags for revenue. A hierarchical mapping resolves most cases, but 178 companies have multi-tag conflicts where the hierarchy may select a narrower figure.
4. **Divergence is not misconduct**: Revenue/income/OCF divergence has many legitimate causes (acquisitions, one-time charges, working capital timing, accounting changes). Findings require contextual investigation.
5. **No proprietary data**: All data used is publicly available from SEC EDGAR. No confidential or non-public information is included.

## License

This project uses publicly available SEC EDGAR data. The SEC data is in the public domain.
