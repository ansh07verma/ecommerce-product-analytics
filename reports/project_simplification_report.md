# Project Simplification Report

**Project**: E-Commerce Search Discovery & Conversion Funnel Analysis  
**Repository**: `ansh07verma/ecommerce-product-analytics`  
**Purpose**: Documentation of the strategic simplification from an over-engineered production-style search platform into an authentic, college-level SQL and Python Product Analytics project.  

---

## 1. Before

In previous stages, the repository evolved into an advanced, enterprise-scale search and experimentation framework containing:
- In-memory inverted indexes with custom field token scoring and tie-breaking algorithms
- Elaborate search debugging UI with local HTTP servers, trace logs, and web endpoints
- Full-scale A/B experiment simulator with deterministic MD5 user-level hashing, two-proportion z-tests, and power curves
- Extensive financial and capital discipline modeling with sensitivity matrices, elasticity ranks, break-even targets, and illustrative corporate engineering cost calculations ($28.5K Year-1 cost)
- Standalone single-file HTML/CSS/JS analytics dashboard with live background HTTP servers
- Over 20 specialized reports, PRD documentation files, and 71 unit/integration tests

While technically thorough, this implementation was significantly more complex than appropriate for a student data analytics portfolio and resembled an enterprise search engineering system.

---

## 2. After

The project has been intentionally refactored into a clear, credible, student-level Product Analytics project:
- **Core Focus**: Funnel analytics using intermediate SQL and a clean Python prototype.
- **Search Logic**: Replaced complex inverted index logic with a readable, straightforward Python search prototype (`src/search.py`, ~150 lines) that handles tokenization, strict search, and query relaxation.
- **SQL Analytics**: Organized into four modular, readable `.sql` files (`01_funnel_analysis.sql`, `02_search_analysis.sql`, `03_query_analysis.sql`, `04_product_analysis.sql`) demonstrating intermediate SQL.
- **Business Sizing**: Replaced the complex financial modeling suite with a simple, direct calculation script (`src/business_impact.py`, ~90 lines) evaluating two realistic CTR lift scenarios (+1.0 pp and +3.5 pp).
- **Visualization**: Replaced the web dashboard with five clean, standalone matplotlib charts in `figures/`.
- **Notebook**: Consolidated multiple complex notebooks into a single, clean narrative notebook (`notebooks/analysis.ipynb`).
- **Tests**: Replaced 71 advanced tests with 16 clean, focused pytest tests covering search mechanics and data integrity.

---

## 3. Removed Components

| Category | Removed Files / Features | Rationale for Removal |
| :--- | :--- | :--- |
| **Search Dashboard** | `src/search_dashboard.py`, `reports/search_dashboard.html`, `test_search_dashboard.py` | Over-engineered; dashboard is not part of a core analytics portfolio |
| **Search Debugger** | `src/search_debugger.py`, `src/search_debugger_ui.py`, `test_search_debugger.py` | Unnecessary UI and server infrastructure |
| **A/B Simulation Engine** | `src/ab_experiment.py`, `src/plot_ab_experiment.py`, `test_ab_experiment.py`, simulation reports | Simulated A/B testing is over-complicated; replaced with clean experiment design in report |
| **Advanced Search Engine** | `src/search_engine.py`, `benchmark_search.py`, `benchmark_query_relaxation.py` | Complex inverted index and benchmarking replaced by simple Python prototype |
| **Advanced PM Frameworks** | RICE prioritization scripts, $28.5K engineering cost models, break-even solver, PRD validator | Corporate planning overhead replaced by authentic student analysis |
| **Old Complex Reports** | 16-section case study, interview cheat sheet, credibility QA, evaluation reports | Consolidated into a single readable 5-8 page `reports/project_report.md` |

---

## 4. Retained Analytics & Ground Truth Findings

All validated empirical metrics and core analytical conclusions from the original dataset are strictly preserved:
- **32,245** total marketplace searches across 31,328 customer sessions `[Observed]`
- **11.92% vs. 5.16%**: Conversion advantage of search-engaged shoppers over browse-only shoppers `[Observed]`
- **33.85%** of all searches contain 4+ words (10,914 queries) `[Observed]`
- **8.23%** historical Zero-Result Rate on 4+ token queries (vs. 1.78% on 1-3 token head queries) `[Observed]`
- **44.39%** manual reformulation rate on 4+ token queries `[Observed]`
- **941 searches** in the eligible low-result discovery failure cohort (< 3 results on 4+ tokens) `[Observed]`
- **3.08%** baseline Search-to-PDP Click-Through Rate on the eligible cohort (29 clicks) `[Observed]`
- **91.81%** query recovery rate achieved by the simple Python relaxation prototype on unmatchable test queries `[Local Evaluation]`
- **+$1,808.69 / year**: Modeled annualized gross GMV under the target +3.5 pp CTR lift scenario `[Modeled]`

---

## 5. SQL Concepts Demonstrated

The SQL suite (`sql/`) demonstrates intermediate data analytics skills appropriate for an entry-level analyst:
1. **Common Table Expressions (`WITH ... AS`)**: Multi-step funnel aggregation and query segmentation without deeply nested subqueries.
2. **Aggregations & Grouping (`COUNT`, `COUNT(DISTINCT)`, `SUM`, `AVG`, `GROUP BY`)**: Calculating session counts, revenue, and averages.
3. **Conditional Logic (`CASE WHEN ... THEN ... ELSE ... END`)**: Funnel step flags (`has_pdp_view`, `has_cart_add`, `has_order`) and cohort segmentation.
4. **Relational Joins (`LEFT JOIN`, `INNER JOIN`)**: Linking sessions, searches, views, carts, and orders on foreign keys.
5. **Ratio & Percentage Calculations**: Safe division using `NULLIF()` to compute stage-by-stage drop-offs and CTRs.
6. **String Manipulation (`LENGTH`, `REPLACE`, `TRIM`)**: Calculating query token lengths directly in SQL.

---

## 6. Python Concepts Demonstrated

The Python codebase (`src/`) demonstrates clean, readable programming:
1. **Data Ingestion & SQL Querying**: Connecting to DuckDB and loading tables into pandas DataFrames.
2. **String Processing & Tokenization**: Regular expressions for query cleaning, stopword filtering, and rule-based stemming.
3. **Combinatorics & Search**: Using `itertools.combinations` to generate candidate dropped-token subsets.
4. **Data Structures**: Lists of dictionaries and sets for fast, in-memory document matching.
5. **Mathematical Modeling**: Simple conversion propagation formulas calculating incremental clicks, orders, and GMV.
6. **Data Visualization**: Matplotlib bar charts with formatted labels and clean styling.
7. **Automated Testing**: Writing modular pytest fixtures and test functions to verify logic.

---

## 7. Product Story

The refined project narrative is concise, believable, and compelling:

> *"I analyzed an e-commerce fashion dataset using SQL and Python to understand how search behavior impacts customer conversion.
> 
> I discovered that while search-engaged shoppers convert 2.3x better than browse shoppers, high-intent users typing longer queries (4+ words) suffer an 8.23% zero-result rate and a 44.39% reformulation rate because strict keyword search breaks down when shoppers over-specify attributes.
> 
> To address this discovery failure, I built a simple Python query-relaxation prototype that safely removes restrictive non-category modifiers when strict search returns fewer than 3 items. In testing, this recovered 91.81% of unmatchable queries while protecting core category intent.
> 
> Finally, I modeled downstream conversion to estimate that a +3.5 pp CTR lift could yield ~$1,800 in annual GMV, leading to my product recommendation to run a lightweight A/B test before making any larger infrastructure investments."*

---

## 8. Verification & Test Results

- **Unit & Functional Tests**: `pytest tests/` passed **16/16 tests** in 0.50 seconds.
- **Data Quality Integrity**: `python src/data_validation.py` passed **59/59 checks**.
- **Analysis Execution**: `python src/analysis.py` successfully ran all 4 SQL scripts and generated 5 clean charts in `figures/`.
- **Search Prototype**: `python src/search.py` tested across 5 sample queries, demonstrating strict search and relaxation.
- **Business Impact**: `python src/business_impact.py` executed cleanly with Scenario A and Scenario B estimates.

---

## 9. Final Positioning

> **"College-level Product Analytics / Data Analytics project using intermediate SQL and Python."**
