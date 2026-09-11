# E-Commerce Product Analytics SQL Suite

A clean collection of intermediate analytical SQL scripts executed against DuckDB (`data/ecommerce_analytics.duckdb`).

---

## SQL Suite Structure

| File | Focus Area | Core Concepts Demonstrated | Key Output Metrics |
| :--- | :--- | :--- | :--- |
| **`01_funnel_analysis.sql`** | Conversion Funnel | CTEs, LEFT JOINs, conditional aggregation | Session-to-PDP, PDP-to-Cart, Cart-to-Order conversion; Search vs Browse comparison |
| **`02_search_analysis.sql`** | Query Segmentation | String functions (`LENGTH`, `REPLACE`), conditional counting | 1–3 vs 4+ token query shares, Zero-Result Rates (ZRR), reformulation rates, 941 eligible low-result cohort |
| **`03_query_analysis.sql`** | Query Patterns & Categories | GROUP BY, ORDER BY, LIMIT, string filters | Top search queries, frequent zero-result queries, category-level ZRR and over-specification patterns |
| **`04_product_analysis.sql`** | Revenue & Impact | Revenue aggregations, multi-table joins | Overall GMV ($217.8K), Search GMV ($174.3K), eligible cohort downstream baseline (29 clicks, 7 carts, 2 orders, $285.15 GMV) |

---

## How to Run

```bash
# Execute all SQL scripts and print results via Python
python src/analysis.py
```
