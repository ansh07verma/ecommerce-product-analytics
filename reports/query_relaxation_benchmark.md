# Automated Query Relaxation Benchmark Report

## Executive Summary

This report documents the empirical evaluation of the deterministic Automated Query Relaxation / Soft-Match Fallback Engine implemented on top of `src/search_engine.py`. The benchmark evaluates retrieval performance, recovery efficacy, and latency across 1,000 distinct historical search queries extracted from `search_events`.

> [!IMPORTANT]
> **Distinction between Historical Behavior and Engine Benchmark**:
> - **Historical Behavioral Data (Synthetic Events)**: 4+ token ZRR was 8.23% in user event logs, with a low-result Search→PDP CTR of 3.08%.
> - **New Strict-Search Engine Benchmark**: On distinct 4+ token keyword queries against the 1,600-product catalog, strict intersection returned 0 results for 98.21% of queries due to multi-attribute over-specification.
> - **Relaxed Engine Benchmark**: The query relaxation layer successfully recovers **91.81%** of eligible failing queries, dropping remaining ZRR on the benchmark sample from 89.10% down to 8.40%.

## Primary Benchmark Results

| Metric | Baseline Strict Search | Relaxed Fallback Engine | Delta / Improvement |
| :--- | :--- | :--- | :--- |
| **Evaluated Distinct Queries** | 1000 | 1000 | - |
| **Zero-Result Rate (Overall)** | 89.10% (891) | 8.40% (84) | -80.70 pp |
| **Low-Result Rate (<3 results)** | 89.10% (891) | 9.30% (93) | -79.80 pp |
| **Eligible Queries (>=4t, <3)** | 879 | 879 | - |
| **Successfully Recovered Queries** | 0 | **807** | **+807** |
| **Eligible Recovery Rate** | 0.00% | **91.81%** | **+91.81%** |
| **Average Results per Query** | 1.53 | 11.05 | +9.51 items |
| **Avg Added Results (Eligible)** | 0.00 | **10.82** | +10.82 items |

## Stratification by Query Length

The relaxation layer enforces a safety guardrail: short queries (1–3 tokens) are **never relaxed** to prevent category drift and intent corruption.

| Strata | Query Count | Strict ZRR | Relaxed ZRR | Eligible Queries | Recovered | Recovery Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Short Queries (1–3 tokens)** | 105 | 11.43% | 11.43% | 0 | 0 | N/A (Guarded) |
| **Long Queries (4+ tokens)** | 895 | 98.21% | 8.04% | 879 | 807 | **91.81%** |

## Latency Profile (Target: p95 <= 250ms)

| Stage | Mean | p50 | p90 | p95 | p99 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Strict Search Latency** | 1.36 ms | 1.40 ms | 1.77 ms | 2.21 ms | 3.28 ms |
| **Total Relaxed Latency** | 14.48 ms | 12.41 ms | 28.85 ms | 38.79 ms | 42.35 ms |
| **Relaxation Overhead** | 13.12 ms | 11.14 ms | 27.18 ms | 36.99 ms | 40.87 ms |

> [!TIP]
> **Latency Validation**: The observed p95 total execution latency for relaxed queries is **38.79 ms**, which comfortably meets and exceeds the PRD's SLA target of <= 250 ms. Because the index is held in in-memory inverted postings structures, evaluating 10–15 candidate fallback queries adds only ~13.12 ms of average overhead.

## Representative Real Recovery Examples

| Original Query | Strict Count | Dropped Token(s) | Fallback Query | Recovered Count | Overhead |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `vintage black jeans 10` | 0 | `10, black` | `vintage jean` | **20** | 4.80 ms |
| `slim fit emerald green jeans M` | 0 | `emerald, green` | `slim fit jean m` | **12** | 22.65 ms |
| `breathable white jeans M` | 0 | `breathable, white` | `jean m` | **20** | 5.93 ms |
| `oversized beige jeans 10` | 0 | `10, beige` | `oversized jean` | **20** | 4.98 ms |
| `linen black jeans L` | 0 | `black` | `linen jean l` | **13** | 1.07 ms |
| `pure cotton beige jeans L` | 0 | `beige, pure` | `cotton jean l` | **18** | 12.32 ms |
| `linen emerald green jeans 10` | 0 | `10, emerald, green` | `linen jean` | **14** | 12.02 ms |
| `oversized beige jeans 9` | 0 | `9, beige` | `oversized jean` | **20** | 4.82 ms |
| `oversized white jeans L` | 0 | `white` | `oversized jean l` | **19** | 1.02 ms |
| `pure cotton beige jeans XL` | 0 | `beige, pure` | `cotton jean xl` | **20** | 12.04 ms |

## Limitations & Guardrails

1. **Completely Unmatchable Intent**: If all tokens in a query are absent from the catalog (e.g. unknown brand or gibberish), the system correctly returns `NO_SAFE_RELAXATION` with 0 results rather than polluting the SRP with irrelevant items.
2. **Category Drift Protection**: A severe scoring penalty (-80 pts) prevents candidates from drifting into disjoint master categories.
3. **In-Stock Filtering**: Only currently in-stock SKUs are counted toward the 3-result threshold and returned to users.
