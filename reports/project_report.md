# E-Commerce Search & Conversion Analysis

**Project**: E-Commerce Search Discovery & Conversion Funnel Analysis  
**Author**: Data & Product Analytics Project (College Level)  
**Tools**: SQL (DuckDB), Python (Pandas, Matplotlib)  
**Repository**: `ansh07verma/ecommerce-product-analytics`  

---

## 1. Introduction

In modern online retail, the search bar is the primary discovery engine for high-intent shoppers. When customers type a query into an e-commerce search bar, they are actively looking to buy rather than passively browsing. If the search engine fails to return relevant products, the customer is stopped before reaching a Product Detail Page (PDP), stalling the conversion funnel.

This project analyzes customer search and funnel progression across an e-commerce fashion marketplace dataset. Using intermediate SQL and Python, we investigate where shoppers lose momentum, discover an acute failure mode on specific multi-attribute searches, prototype a simple query-relaxation fallback solution, and model its potential business impact.

---

## 2. Dataset

The analysis is conducted on an e-commerce relational dataset stored in DuckDB (`data/ecommerce_analytics.duckdb`), spanning 60 days of fashion marketplace activity.

### Core Data Model (7 Relational Tables)

| Table | Row Count | Primary Description | Key Columns |
| :--- | :---: | :--- | :--- |
| **`users`** | 16,000 | Registered customer accounts | `user_id`, `user_tier`, `acquisition_channel` |
| **`sessions`** | 31,328 | Browsing and shopping sessions | `session_id`, `user_id`, `platform`, `has_search` |
| **`products`** | 1,600 | Apparel catalog SKUs across 8 categories | `product_id`, `title`, `brand`, `effective_price`, `inventory_units` |
| **`search_events`** | 32,245 | Search queries submitted by users | `search_id`, `session_id`, `query_text`, `results_count`, `is_zero_result` |
| **`product_views`** | 44,573 | Detail page (PDP) visits | `view_id`, `session_id`, `product_id`, `search_id`, `is_size_in_stock` |
| **`cart_events`** | 8,364 | Items added to shopping basket | `cart_item_id`, `session_id`, `product_id`, `quantity`, `is_purchased` |
| **`orders`** | 2,880 | Completed customer purchases | `order_id`, `session_id`, `gross_merchandise_value`, `net_paid_amount` |

Across the entire marketplace, completed orders represent **$217,860.56 in Gross Merchandise Value (GMV)** with an overall Average Order Value (AOV) of **$75.65**.

---

## 3. Business Problem

Our objective was to diagnose where shoppers lose momentum across the six primary customer journey stages:

$$	ext{Sessions} \longrightarrow 	ext{Search} \longrightarrow 	ext{Product Detail (PDP)} \longrightarrow 	ext{Cart Add} \longrightarrow 	ext{Checkout} \longrightarrow 	ext{Order}$$

Through initial exploratory data analysis, we confirmed two fundamental baseline facts:
1. **Searchers are high intent**: Sessions with search activity convert at **11.92%**, compared to only **5.16%** for browse-only sessions (a 2.3x conversion advantage). Search drives **$174,251.23 (79.98%)** of all marketplace revenue.
2. **Specific queries break strict search**: When shoppers type detailed multi-attribute queries (e.g., *"slim fit black dresses XL"*), keyword search requiring all words to match fails frequently, returning 0 or very few items even though relevant inventory exists.

When high-intent shoppers receive zero results, they are forced to either manually reformulate their query or abandon the session entirely, resulting in lost discovery opportunities and forgone sales.

---

## 4. SQL Analysis

The analytical core of the project is organized into four modular SQL scripts located in the `sql/` directory:

### 1. Funnel Analysis (`sql/01_funnel_analysis.sql`)
Analyzes overall marketplace funnel progression and compares search-engaged vs. browse-only sessions:
- **Total Sessions**: 31,328 sessions $	o$ 22,346 PDP sessions (71.3%) $	o$ 7,172 cart sessions (32.1%) $	o$ 2,880 order sessions (40.2%).
- **Search-Engaged Sessions (18,677)**: 83.8% view a PDP, 35.2% add to cart, and **11.92% complete an order**.
- **Browse-Only Sessions (12,651)**: 52.9% view a PDP, 24.7% add to cart, and **5.16% complete an order**.

### 2. Search Behavior & Query Length (`sql/02_search_analysis.sql`)
Segments the 32,245 search events by word count into **Head/Torso terms (1–3 tokens)** and **Specific queries (4+ tokens)**:
- **1–3 Token Queries**: 21,331 searches (66.15% share), 1.78% Zero-Result Rate, 70.78% Search $	o$ PDP CTR, 42.41% reformulation.
- **4+ Token Queries**: 10,914 searches (33.85% share), **8.23% Zero-Result Rate** (4.6x higher failure), 62.95% CTR, 44.39% reformulation.
- **Eligible Low-Result Cohort (< 3 results on 4+ tokens)**: **941 searches** (~15.7 searches/day) with a collapsed **3.08% Search $	o$ PDP CTR** (only 29 clicks).

### 3. Query Patterns & Over-Specification (`sql/03_query_analysis.sql`)
Identifies top queries and isolates the specific attributes that cause zero-result dead ends:
- Popular queries like *"leather jacket"* (360 searches, 77.9 avg results, 1.9% ZRR) succeed reliably.
- Unsuccessful queries combine valid individual attributes that do not co-occur on a single product: e.g., *"slim fit black dresses XL"* (5 searches, 0 results), *"vintage black jeans L"* (4 searches, 0 results).
- The failure is **attribute over-specification**, not a missing category.

### 4. Revenue & Downstream Funnel (`sql/04_product_analysis.sql`)
Traces downstream behavior for the 941 eligible low-result searches:
- **Searches**: 941
- **PDP Clicks**: 29 (3.08% CTR)
- **Cart Additions**: 7 ($P(	ext{Cart}|	ext{PDP}) = 24.14\%$)
- **Completed Orders**: 2 ($P(	ext{Order}|	ext{Cart}) = 28.57\%$)
- **Historical GMV**: $285.15 (Cohort AOV: $142.58)

---

## 5. Key Findings

1. **Search Drives Marketplace Conversion**: Search-engaged shoppers convert at **11.92% vs 5.16% for browse shoppers** ($p < 0.0001$), generating 80% of completed order revenue.
2. **Specific Queries Suffer a 4.6x Higher Failure Rate**: Queries with 4+ tokens have an **8.23% Zero-Result Rate** compared to only **1.78%** for 1–3 token head terms.
3. **Severe Discovery Collapse on Low-Result Cohort**: For the 941 searches with 4+ tokens that returned fewer than 3 results, Search-to-PDP CTR collapsed to **3.08%** (29 clicks out of 941 searches).
4. **Users Experience High Friction**: Customers typing 4+ token queries reformulate **44.39% of the time**, re-typing words in frustration when strict matching fails.
5. **Over-Specification Is the Primary Culprit**: Shoppers combine valid attributes (brand + color + fabric + style + size). When strict boolean matching requires every single modifier to match metadata, items in stock are excluded simply because one modifier is missing from the title.

---

## 6. Proposed Solution: Simple Query Relaxation

To resolve over-specification without building complex distributed infrastructure, we propose a lightweight **Automated Query Relaxation** fallback rule:

```
[ User Query: "slim fit black dresses XL" ]
                     │
                     ▼
          Strict Search Execution
                     │
   Does query have >= 4 tokens AND < 3 results?
                     │
       ┌─────────────┴─────────────┐
       ▼                           ▼
    [ NO ]                      [ YES ]
Return strict results        Identify candidate modifiers:
                             - Protect category nouns ("dress")
                             - Identify droppable modifiers ("black", "slim", "fit", "xl")
                                   │
                                   ▼
                             Iterative Modifier Drops:
                             1. Try dropping 1 modifier (e.g. test "slim fit dress xl")
                             2. If results < 3, try dropping combinations of 2 modifiers
                             3. If tokens >= 5 and results < 3, try dropping 3 modifiers
                                   │
                                   ▼
                     Ensure at least 2 tokens remain & category preserved.
```

### Core Guardrails
1. **Category Protection**: Core merchandise nouns (e.g., *"dress"*, *"jeans"*, *"jacket"*, *"shirt"*) can **never** be dropped. A search for a dress will never return jeans or shoes.
2. **Minimum Token Overlap**: At least 2 tokens must remain in any relaxed query to preserve search context.
3. **In-Stock Filtering**: Only products with active inventory (`inventory_units > 0`) are returned.
4. **Head Query Safety**: Queries with fewer than 4 tokens never trigger relaxation, preventing query drift on high-performing short terms.

---

## 7. Python Prototype

We implemented the proposed solution in a lightweight, readable Python script: [`src/search.py`](file:///C:/Projects/ecommerce-product-analytics/src/search.py).

### Prototype Demonstration on Test Queries

```text
Query: "slim fit black dresses XL"
  Strict Results : 0 matches
  Relaxed Query  : "slim fit dress xl" (dropped 'black')
  Relaxed Results: 8 in-stock dresses recovered!
  Example Match  : Urban Chic Slim Fit Dresses ($30.46)

Query: "vintage black jeans L"
  Strict Results : 0 matches
  Relaxed Query  : "vintage jean l" (dropped 'black')
  Relaxed Results: 24 in-stock jeans recovered!
  Example Match  : Allen Solly Vintage Wash Jeans ($33.57)

Query: "breathable black jeans M"
  Strict Results : 0 matches
  Relaxed Query  : "jean m" (dropped 'breathable', 'black')
  Relaxed Results: 303 in-stock jeans recovered!
  Example Match  : Marks & Spencer Slim Fit Jeans ($42.09)

Query: "pure cotton white jeans 10"
  Strict Results : 0 matches
  Relaxed Query  : "cotton jean" (dropped ['pure', 'white', '10'])
  Relaxed Results: 23 in-stock jeans recovered!
  Example Match  : Vero Moda Cotton Jeans ($54.30)

Query: "shoes"
  Strict Results : 121 matches
  Relaxation     : Not triggered (short query with adequate results)
```

In a broader evaluation over historical test queries, query relaxation recovered **91.81% of unmatchable queries** [Local Prototype Evaluation], reducing strict Zero-Result Rate from 98.21% down to 8.40%.

---

## 8. Expected Impact

We modeled potential downstream business impact using the empirical funnel conversion rates from DuckDB (`src/business_impact.py`):
- Eligible searches over 60 days: **941** (~15.7/day)
- Prototype recovery rate: **91.81%** (863.9 recovered searches)
- Observed PDP $	o$ Cart rate: **24.14%**
- Observed Cart $	o$ Order rate: **28.57%**
- Average Order Value (AOV): **$142.58**

### Scenario Estimates

| Scenario | Modeled CTR Lift | Incremental Clicks | Incremental Orders | 60-Day Gross GMV | Annualized Gross GMV |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Scenario A (Conservative)** | +1.0 pp | +8.6 | +0.6 | +$84.95 | **+$516.77 / year** [Modeled] |
| **Scenario B (Target)** | +3.5 pp | +30.2 | +2.1 | +$297.32 | **+$1,808.69 / year** [Modeled] |

### Product & Business Recommendation
At current boutique volume (~16 eligible searches/day), the annual revenue opportunity is modest (**~$1,800/year**). 
- **Recommendation**: Do **not** spend budget or time building dedicated search cluster infrastructure.
- **Action**: Deploy the simple Python in-memory relaxation prototype into the existing application layer. Validate whether live users actually purchase recovered products through a standard 50/50 A/B test before making any larger engineering investments.

---

## 9. Limitations

1. **Synthetic Dataset**: Ground-truth data was generated using a controlled random seed in DuckDB. Real shoppers exhibit greater variance in search intent and spelling.
2. **Simple In-Memory Search**: The prototype uses basic Python string and token matching. It does not replace a production search engine like Elasticsearch or OpenSearch.
3. **Modeled Revenue Estimates**: Revenue figures are mathematical projections based on assumed CTR lifts, not audited receipts from a live production experiment.
4. **No Live A/B Experiment**: An actual A/B test has not yet been executed in production; the recommendation represents the next proposed step.

---

## 10. Future Improvements

If a live A/B test confirms positive customer conversion, future iterations could include:
1. **Autocomplete Suggestions**: Guide users toward high-inventory queries before they hit Enter.
2. **Synonym Dictionary**: Map regional fashion terms (e.g., *"trousers"* $\leftrightarrow$ *"pants"*).
3. **Fuzzy Spell-Correction**: Handle typos (e.g., *"denim jakcet"*) using simple edit-distance matching.
4. **Semantic Search**: Explore embeddings or vector search if catalog size expands beyond tens of thousands of SKUs.
