# Working Search MVP: Deterministic Strict Keyword Engine

**Implementation:** `src/search_engine.py` (`LocalSearchEngine`)  
**Status:** Implemented, Tested, and Benchmarked  
**Date:** September 2026  

---

## 1. Why the Baseline Search Engine Was Needed

Prior to this stage, the repository operated exclusively as an offline product analytics case study based on synthetic event logs in DuckDB. While those logs demonstrated an **8.23% Zero-Result Rate (ZRR)** on 4+ token queries and a depressed **3.08% CTR** on low-result searches, the product itself had no working retrieval mechanism.

To validate the behavioral hypotheses and prepare for **Automated Query Relaxation (Stage 3)**, an actual, executable search engine was required. In product management and search engineering:
- **You cannot improve retrieval without establishing an unrelaxed baseline.**
- **You cannot evaluate query relaxation without a strict search engine that actually produces zero/sparse results on over-specified queries.**
- The strict search engine serves as the **Control ($A$)** in the proposed A/B experimentation framework (EXP-01).

---

## 2. How Query Processing Works

Query preprocessing in `normalize_query_text()` executes deterministically in sub-millisecond time without external APIs or heavy NLP dependencies:

```
User Query: "   Women Floral Dresses, in Cotton!   "
       │
       ▼
1. Lowercase Normalization: "   women floral dresses, in cotton!   "
       │
       ▼
2. Punctuation Handling: "   women floral dresses in cotton   " (replaces non-alphanumeric with spaces)
       │
       ▼
3. Whitespace Collapsing: "women floral dresses in cotton"
       │
       ▼
4. Functional Stopword Filtering: drops "in" (preserves domain terms: "men", "women")
       │
       ▼
5. Deterministic Fashion Stemming: "dresses" ──► "dress"
       │
       ▼
Processed Tokens: ["women", "floral", "dress", "cotton"]
Normalized String: "women floral dress cotton"
```

---

## 3. How Retrieval Works

The engine indexes the 1,600 product catalog directly from `data/ecommerce_analytics.duckdb` (with fallback to `data/raw/products.csv`).

### Strict Boolean Matching (AND Condition)
For any query with tokens $T = \{t_1, t_2, \dots, t_k\}$:
A product $P$ is considered a candidate match **if and only if all query tokens appear in the product document representation**:
$$orall t_i \in T: \quad t_i \in 	ext{Tokens}(P_{	ext{title}} \cup P_{	ext{brand}} \cup P_{	ext{category}} \cup P_{	ext{subcategory}} \cup P_{	ext{sizes}})$$

This strictness models existing production e-commerce search engines before query reformulation or semantic expansion, correctly exposing the vulnerability of specific multi-attribute queries.

---

## 4. How Ranking Works

Candidate products that satisfy the strict boolean match are scored using a deterministic, multi-factor relevance formula:

| Match Factor | Weight / Bonus | Rationale |
|---|:---:|---|
| **Exact Phrase Match in Title** | **+50.0** | Huge precision boost when query matches title exactly |
| **Title Token Match** | **+10.0 per token** | Product title is the highest-signal content attribute |
| **Brand Token Match** | **+8.0 per token** | Explicit brand affinity (e.g. "Nike", "Zara") |
| **Sub-Category Token Match** | **+6.0 per token** | Product type specificity (e.g. "Dresses", "Sneakers") |
| **Master Category Token Match** | **+4.0 per token** | High-level department filter (e.g. "Women", "Men") |
| **Size Token Match** | **+3.0 per token** | Specific size match (e.g. "S", "M", "9", "10") |
| **Product Rating Tie-Breaker** | **+ `avg_rating * 0.1`** | Subtle commercial preference for higher-rated items |
| **Review Volume Tie-Breaker** | **+ `min(review_count, 100) * 0.001`** | Subtle boost for social proof |
| **Deterministic Tie-Breaker** | **`product_id` ASC** | Guarantees 100% deterministic, repeatable ordering |

---

## 5. How Stock Filtering Works

Search supports strict in-stock filtering via `in_stock_only=True` (enabled by default):

1. **Product-Level Inventory:** Products with `inventory_units <= 0` are suppressed from purchasable search results.
2. **Size-Level Stockout Awareness:** If a query explicitly mentions a size (e.g., `"Zara dresses S"`), the engine inspects `stockout_sizes`. If size `S` is out of stock, the product is filtered out to prevent customer disappointment and dead-end PDP clicks.
3. **Explicit Metadata:** Every returned item contains `is_in_stock: bool`, making inventory status explicit in API contracts.

---

## 6. What the Current Limitations Are

1. **Keyword Brittleness:** If a customer searches for `"women midi dress"` or `"sneakers red"`, and `"midi"` is absent from the title or `"red"` is on accessories rather than footwear, strict search returns 0 results.
2. **Zero Typo Tolerance:** A typo like `"drss"` or `"nikke"` returns 0 results because strict token matching fails.
3. **Attribute Over-Specification Collapse:** When shoppers combine 4+ modifiers (fit, fabric, color, category, size), strict boolean intersection drops catalog matches to zero (98.21% ZRR on distinct 4+ token queries).
4. **No Semantic Understanding:** The engine cannot recognize that "formal footwear" includes "oxford shoes" without exact keyword overlap.

---

## 7. Why Query Relaxation Is Intentionally NOT Included Yet

In disciplined product management, **you must never build a solution before you have measured the exact baseline defect rate of the control state**.

Including query relaxation in Stage 2 would blur the line between:
1. The **Control state** (what happens today under strict retrieval).
2. The **Treatment state** (what happens when relaxation intervenes).

By preserving `src/search_engine.py` as pure strict search, **Stage 3 can build on top of it cleanly as an interception layer**:
- When `result_count >= 3`, serve standard strict results.
- When `result_count < 3` AND tokens $\ge 4$, trigger **Query Relaxation**.

---

## 8. Baseline Search Metrics

The search engine was benchmarked across 1,000 distinct queries from `search_events` representing 30,012 customer sessions:

| Metric Category | Metric Name | Measured Value | Metric Status |
|---|---|:---:|:---:|
| **Sample Size** | Evaluated Queries | **1,000 distinct** | **[IMPLEMENTED]** |
| **Catalog Scale** | Indexed Products | **1,600 items** | **[IMPLEMENTED]** |
| **Throughput Latency** | Mean Latency | **0.89 ms** | **[IMPLEMENTED]** |
| **Throughput Latency** | p95 Latency | **1.08 ms** | **[IMPLEMENTED]** |
| **Match Density** | Average Results / Query | **1.77 items** | **[IMPLEMENTED]** |
| **Head Queries (1-3 tokens)** | 1-3 Token Zero-Result Rate | **11.43%** | **[IMPLEMENTED]** |
| **Head Queries (1-3 tokens)** | 1-3 Token Avg Results | **14.21 items** | **[IMPLEMENTED]** |
| **Specific Queries (4+ tokens)**| 4+ Token Zero-Result Rate | **98.21%** | **[IMPLEMENTED]** |
| **Specific Queries (4+ tokens)**| 4+ Token Low-Result (<3) Rate | **98.21%** | **[IMPLEMENTED]** |
| **Historical Log Context** | 4+ Token Observed ZRR | **8.23%** | **[OBSERVED DATA]** |
| **Historical Log Context** | Low-Result (<3) Search CTR | **3.08%** | **[OBSERVED DATA]** |
| **Historical Log Context** | Specific Query Session CR | **13.01%** | **[OBSERVED DATA]** |
| **Future Lift Target** | Expected CTR Lift on Recovery | **+3.5 to +5.0 pp** | **[PROPOSED / MODELED]** |

---

## 9. CLI Usage & Manual Demonstration

The search engine can be executed directly from the command line:

```bash
# Example 1: Specific query that returns 0 results under strict search (Stage 3 target)
python src/search_engine.py "women floral midi dress red"

# Example 2: Strong category query that returns multiple ranked products
python src/search_engine.py "women dress"

# Example 3: Branded multi-token query
python src/search_engine.py "nike running shoes"

# Example 4: Run the automated benchmark suite
python src/benchmark_search.py

# Example 5: Run the search unit tests
pytest tests/test_search_engine.py
```
