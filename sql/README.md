# E-commerce Funnel SQL Analytical Suite

A production-grade collection of analytical SQL scripts executed against DuckDB (data/ecommerce_analytics.duckdb).

---

## Suite Structure & Execution Index

| File | Primary Analytical Question | Core Metrics Calculated |
| :--- | :--- | :--- |
| 01_data_quality_audit.sql | Does the database meet 100% data integrity & business rules? | PK uniqueness, FK zero-orphans, price/net-paid logic, temporal chronology |
| 02_overall_funnel.sql | Where does the customer journey lose the most sessions? | Step conversions, drop-off rates, absolute sessions lost, funnel retention |
| 03_search_performance.sql | How do queries perform by type, length, category & filter? | Zero-result rate (ZRR), reformulation rate, search CTR, token length |
| 04_pdp_and_sizing.sql | How does size availability & dwell time affect Add-to-Cart? | In-stock vs out-of-stock ATCR, sizing deficit, dwell time buckets |
| 05_cart_checkout.sql | How does the  shipping fee threshold affect checkout? | Cart abandonment, checkout completion (CCR), GMV basket tiers |
| 06_platform_analysis.sql | At which exact funnel stage do platforms diverge? | iOS vs Android vs Mobile Web vs Desktop stage conversion & AOV |
| 07_user_segmentation.sql | How do cohorts (loyalty tiers, acquisition) behave? | New vs Returning, Bronze/Silver/Gold, acquisition channel conversion |
| 08_category_analysis.sql | Which categories represent friction vs expansion opportunity?| 4-quadrant opportunity classification (traffic vs ATCR), revenue |
| 09_period_comparison.sql | How did performance evolve between Period 1 and Period 2? | Baseline (Days 1-28) vs Recent (Days 29-56) KPI delta analysis |
| 10_opportunity_analysis.sql | What is the quantified upside across competing friction areas?| Sizing, search, shipping, and platform opportunity sizing (GMV) |

---

## How to Execute the Suite

### Via Python:
```python
import duckdb

con = duckdb.connect('data/ecommerce_analytics.duckdb')
with open('sql/02_overall_funnel.sql', 'r') as f:
    df = con.execute(f.read()).df()
print(df)
con.close()
```
