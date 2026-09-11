# Baseline Search Engine Benchmark Report

**Benchmark Execution Date:** September 2026  
**Implementation:** `src/search_engine.py` (`LocalSearchEngine`)  
**Catalog Size:** 1,600 products (DuckDB `products` table)  
**Evaluated Query Sample:** 1,000 distinct queries from `search_events`  
**Historical Search Events Represented:** 30,012 events  

---

## Executive Summary

This benchmark measures the empirical baseline performance of the newly implemented strict keyword search engine (`LocalSearchEngine`) against historical customer queries from the e-commerce marketplace dataset.

The measured benchmark confirms the core product hypothesis:
- **Short queries (1-3 tokens)** achieve high match density (average 14.21 matches) with low zero-result rates (11.43%).
- **Specific queries (4+ tokens)** experience acute retrieval failure under strict boolean matching: **98.21% Zero-Result Rate** and **98.21% Low-Result (< 3 hits) Rate**, with average matches dropping to 0.32.
- **Retrieval Latency** is sub-millisecond to low single-digit milliseconds (mean: **0.9 ms**, p95: **1.09 ms**), well within the proposed production budget (p95 <= 250 ms).

---

## Key Performance Indicators

| Metric Category | Metric Name | Measured Baseline | Context / Historical Benchmark |
|---|---|---|---|
| **Retrieval Volume** | Evaluated Queries | **1,000** distinct | Sampled across all historical query types |
| **Catalog Matches** | Average Matches / Query | **1.77** products | 1,600 total catalog size |
| **Discovery Failure** | Distinct Zero-Result Queries | **891** (89.1%) | Strict boolean AND condition |
| **Discovery Failure** | Volume-Weighted ZRR | **51.36%** | Weighted by historical event frequency |
| **Specific Queries (4+)** | 4+ Token Zero-Result Rate | **98.21%** | Proves vulnerability of multi-attribute searches |
| **Specific Queries (4+)** | 4+ Token Low-Result (<3) Rate | **98.21%** | Candidate pool for Stage 3 Query Relaxation |
| **Short Queries (1-3)** | 1-3 Token Zero-Result Rate | **11.43%** | High precision on head & branded queries |
| **System Latency** | Mean Latency | **0.9 ms** | In-memory tokenized inverted index |
| **System Latency** | p95 Latency | **1.09 ms** | Proposed SLA: p95 <= 250 ms (PASS) |
| **System Latency** | p99 Latency | **2.48 ms** | Peak execution time |

---

## Metric Labeling & Integrity Disclosures

- **[IMPLEMENTED]:** All latency numbers, engine match counts, zero-result rates, and low-result rates in the table above were directly executed and measured using `src/search_engine.py` on the 1,600 product catalog.
- **[OBSERVED DATA]:** The historical search events, CTRs (62.95% on 4+ tokens, 3.08% on <3 results), and session conversion rates (13.01%) are observational facts from `data/ecommerce_analytics.duckdb`.
- **[MODELED / PROPOSED]:** Online A/B lift, query relaxation candidate recovery, and post-relaxation CTR improvements are proposed models to be evaluated in Stage 3.

---

## Failure Case Analysis (The Baseline for Stage 3)

The benchmark highlights representative failure cases where strict search returns 0 results on valid customer intent:

1. **Specific Attribute Stacking:** Queries like `"women floral midi dress red"` fail because while the catalog contains 165 Women's Dresses and 16 Floral Dresses, no single product contains all 5 attributes (`midi` is absent, `red` is on footwear/accessories).
2. **Size Stockouts in Query:** Specific sizing queries where the product exists but the size is stocked out.
3. **Compound Modifiers:** Queries combining multiple fabric, fit, and color adjectives where strict boolean intersection is empty.

These exact failure cases will serve as the testbed for **Stage 3: Automated Query Relaxation / Soft-Match Fallback**.
