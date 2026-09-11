# E-Commerce Search & Conversion Analysis

> A college-level data and product analytics project using SQL and Python to analyze an e-commerce search and conversion funnel, identify product discovery friction on multi-attribute queries, and prototype a simple query-relaxation solution.

---

## Overview

In e-commerce, the search bar is the highest-intent discovery surface for shoppers. This project analyzes a 60-day fashion marketplace dataset (32,245 searches, 31,328 sessions in DuckDB) to understand how search behavior affects conversion. We identify an acute discovery breakdown on specific, multi-attribute searches and build a simple Python prototype demonstrating automated query relaxation to recover lost products.

---

## Problem

When shoppers search with multiple attributes (e.g., *"slim fit black dresses XL"*), strict keyword search requires every single token to match product metadata. If even one descriptive modifier misses catalog metadata, the search returns zero results—even when relevant dresses in size XL are in stock. High-intent shoppers hit an empty screen, causing friction, repeated reformulations, and lost sales.

---

## Dataset

The analysis is based on an apparel marketplace dataset stored in DuckDB (`data/ecommerce_analytics.duckdb`):

| Entity | Count | Description |
| :--- | :---: | :--- |
| **Users** | 16,000 | Registered customer accounts |
| **Sessions** | 31,328 | Browsing and shopping sessions |
| **Products** | 1,600 | Apparel catalog SKUs across 8 categories |
| **Searches** | 32,245 | User-submitted search queries |
| **Product Views (PDP)** | 44,573 | Detail page views |
| **Cart Additions** | 8,364 | Items added to basket |
| **Orders** | 2,880 | Completed customer purchases |
| **Total GMV** | **$217,860.56** | Total Gross Merchandise Value ($75.65 AOV) |

---

## Key Findings

- **Search drives conversion**: Search-engaged sessions convert at **11.92% vs. 5.16% for browse sessions** (a 2.3x conversion advantage) and generate 80% of all marketplace revenue.
- **Specific queries fail more often**: 4+ token queries represent **33.85% of all searches**, but suffer an **8.23% Zero-Result Rate (ZRR)** compared to only **1.78%** for 1–3 token head queries (4.6x higher failure rate).
- **High user friction**: Shoppers typing 4+ token queries reformulate **44.39% of the time** in frustration when strict search fails.
- **Severe low-result collapse**: Among the **941 searches** with 4+ tokens returning fewer than 3 items, Search-to-PDP Click-Through Rate collapses to just **3.08%** (only 29 clicks).
- **Failure is over-specification**: Shoppers combine valid attributes (brand, color, fabric, style, size); failure occurs because rigid boolean matching drops in-stock items when a single non-essential modifier is missing.

---

## Solution: Simple Query Relaxation

When a query has **$\ge 4$ tokens** and strict search returns **$< 3$ results**:
1. Identify the core category noun (e.g., *"dress"*, *"jeans"*, *"jacket"*) and protect it from deletion.
2. Identify non-category modifiers (e.g., colors, fabrics, occasions) as candidate drops.
3. Remove one modifier at a time and re-run search against active inventory (`inventory_units > 0`).
4. If needed, try removing two modifiers, ensuring at least **two tokens remain**.
5. Return the first relaxed query that yields useful in-stock results.

```text
Input: "slim fit black dresses XL" (Strict: 0 results)
  -> Relaxed: "slim fit dress xl" (dropped 'black')
  -> Recovered: 8 in-stock dresses!
```

---

## SQL Analysis

The SQL scripts in `sql/` demonstrate intermediate database querying:
- **`01_funnel_analysis.sql`**: Full funnel progression (Sessions $	o$ PDP $	o$ Cart $	o$ Orders) and Search vs. Browse conversion.
- **`02_search_analysis.sql`**: Query length segmentation (1–3 vs. 4+ tokens), zero-result rates, reformulation rates, and the 941 low-result cohort.
- **`03_query_analysis.sql`**: Top queries, common zero-result multi-attribute queries, and category breakdown.
- **`04_product_analysis.sql`**: Marketplace revenue, search GMV contribution, and downstream cohort conversion.

---

## Python Prototype

The Python prototype in `src/search.py` provides clean keyword search with relaxation:
- **`normalize_query()`**: Cleans, lowercases, removes stopwords, and stems plurals.
- **`strict_search()`**: Requires all tokens to match; filters out-of-stock SKUs.
- **`relaxed_search()`**: Automatically relaxes non-category modifiers when strict results $< 3$.

---

## Results & Impact

- **Recovery Rate**: In local testing across unmatchable test queries, the prototype recovered **91.81% of zero-result searches**, reducing strict ZRR from 98.21% down to 8.40%.
- **Modeled Business Impact** (`src/business_impact.py`):
  - **Scenario A (+1.0 pp CTR lift)**: +0.6 orders $	o$ **+$84.95 / 60 days** ($pprox$ **+$516.77 / year**) [Modeled].
  - **Scenario B (+3.5 pp CTR lift)**: +2.1 orders $	o$ **+$297.32 / 60 days** ($pprox$ **+$1,808.69 / year**) [Modeled].
- **Recommendation**: At current volume (~16 eligible searches/day), standalone revenue is modest (~$1.8K/year). Validate user conversion with a simple A/B test before investing in heavy search infrastructure.

---

## How to Run

```bash
# 1. Run automated tests (16 tests)
pytest tests/

# 2. Run data validation (59 checks)
python src/data_validation.py

# 3. Run full SQL analytics & generate charts in figures/
python src/analysis.py

# 4. Test the search & query-relaxation prototype
python src/search.py

# 5. Run simple business-impact calculations
python src/business_impact.py
```

---

## Project Structure

```
ecommerce-product-analytics/
├── data/
│   ├── ecommerce_analytics.duckdb       # DuckDB analytical database (7 tables, 119K events)
│   └── raw/                             # Raw CSV data files
├── sql/
│   ├── 01_funnel_analysis.sql           # Funnel progression (Sessions -> PDP -> Cart -> Order)
│   ├── 02_search_analysis.sql           # Query length segmentation & discovery failure
│   ├── 03_query_analysis.sql            # Query patterns & over-specification breakdown
│   └── 04_product_analysis.sql          # Revenue, AOV & downstream conversion
├── src/
│   ├── search.py                        # Simple keyword search & query relaxation prototype
│   ├── analysis.py                      # SQL runner & matplotlib visualization generator
│   ├── business_impact.py               # Simple downstream conversion & GMV model
│   ├── generate_data.py                 # Data generation runner
│   ├── data_generation.py               # Synthetic e-commerce dataset generator
│   └── data_validation.py               # 59 automated data quality checks
├── notebooks/
│   └── analysis.ipynb                   # End-to-end interactive analysis notebook
├── figures/                             # Generated visualization charts (PNG)
├── reports/
│   ├── project_report.md                # Comprehensive project report (10 sections)
│   ├── product_recommendation.md        # Product recommendation memo
│   └── project_simplification_report.md # Simplification documentation
├── tests/
│   ├── test_search.py                   # Search & relaxation unit tests (10 tests)
│   └── test_analytics.py                # SQL metrics & business calculation tests (6 tests)
├── README.md
└── requirements.txt
```

---

## Limitations

- **Synthetic Dataset**: Ground-truth data was generated deterministically via Python in DuckDB.
- **In-Memory Prototype**: Search uses simple Python string matching, not a production search engine.
- **Modeled Estimates**: Revenue impacts are scenario estimates based on assumed CTR lifts.
- **No Live A/B Experiment**: The recommendation proposes an A/B test; live causal traffic has not yet run.

---

## Future Improvements

- **Autocomplete Suggestions**: Guide shoppers toward high-inventory terms as they type.
- **Synonym Dictionaries**: Handle colloquial/regional terms (e.g., *"trousers"* $\leftrightarrow$ *"pants"*).
- **Fuzzy Spell-Correction**: Correct typos (e.g., *"jakcet"* $	o$ *"jacket"*).
- **Semantic Search**: Explore embeddings or vector search if catalog grows beyond 50,000 SKUs.
