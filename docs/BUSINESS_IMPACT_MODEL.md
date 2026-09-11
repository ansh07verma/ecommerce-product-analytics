# Business Impact Model & GMV Opportunity Specification

**Document Title**: Automated Query Relaxation Business Impact Model & Financial Specification  
**Author**: Product Management + Product Analytics  
**Version**: 1.1.0 (Stage 7 / 7.1)  
**Status**: APPROVED FOR BUSINESS CASE EVALUATION  
**Component Reference**: `src/business_impact.py`  

---

## What This Model Does NOT Prove

Before reviewing the financial projections, executive leadership and product stakeholders must understand the explicit boundaries of this offline business model:

```
+---------------------------------------------------------------------------------------------------+
| WHAT THIS BUSINESS MODEL PROVES:                                                                  |
| • The exact mathematical connection between search recovery, CTR lifts, and downstream GMV.      |
| • That incremental revenue is bounded by eligible traffic volume (941 searches / 60 days).        |
| • Sensitivity to cannibalization, recovery degradation, and conversion leakage.                   |
| • Sizing requirements for engineering ROI and corporate break-even targets.                       |
+---------------------------------------------------------------------------------------------------+
| WHAT THIS BUSINESS MODEL DOES NOT PROVE:                                                          |
| • Actual realized corporate revenue (treatment lift is an explicit model parameter, NOT revenue).|
| • True live customer willingness-to-buy on relaxed fallback items.                               |
| • Audited cannibalization rates (requires production randomized holdouts).                       |
| • Long-term customer lifetime value (LTV) or retention effects.                                   |
| Only a production A/B experiment can measure actual customer purchasing behavior.                |
+---------------------------------------------------------------------------------------------------+
```

---

## 1. Product Context & Strategic Problem

In multi-attribute e-commerce fashion queries ($\ge 4$ tokens), customers frequently over-constrain searches with multiple specific attributes (e.g., `"women red silk evening dress"`), causing strict boolean conjunctive search to return 0 results even when relevant catalog items exist.

- **Eligible Search Volume**: **941 opportunities** across the 60-day historical window (15.7 searches/day) `[OBSERVED]`.
- **Baseline Conversion**: Only **3.08%** of eligible searches result in a PDP view, generating just 2 orders and $285.15 in GMV over 60 days `[OBSERVED]`.
- **Selected Intervention**: Automated Query Relaxation / Soft-Match Fallback (Stage 5 Decision).

---

## 2. Metric Dictionary & Definitions

```
+-----------------------------------------------------------------------------------------------+
| METRIC DICTIONARY                                                                             |
+-----------------------------------------------------------------------------------------------+
| Eligible Search Opportunity: A search event satisfying: token_count >= 4 AND                   |
|                              strict_result_count < 3.                                          |
| Recovered Search:            An eligible search where query relaxation returns >=1 safe,      |
|                              in-stock, category-consistent product alternatives.               |
| Incremental PDP View:        A product detail page view caused by the presence of relaxed     |
|                              results that would have been a zero/low result dead end.         |
| Incremental Cart Addition:   A cart add event originating from an incremental PDP discovery.   |
| Incremental Order:           A completed purchase attributable to an incremental search.      |
| Gross Incremental GMV:       Incremental Orders multiplied by empirical Average Order Value.   |
| Cannibalization Rate:        The fraction of modeled orders that would have occurred anyway    |
|                              through alternative site discovery (e.g., browse/reformulation).  |
| Net Incremental GMV:         Gross Incremental GMV discounted by (1 - Cannibalization Rate).   |
| Annualized GMV Run-Rate:     60-day GMV scaled to an annual basis: GMV * (365 / 60).           |
+-----------------------------------------------------------------------------------------------+
```

---

## 3. Mathematical Attribution Framework

The model enforces strict sequential funnel propagation to avoid double-counting or unrealistic attribution jumps:

```text
Eligible Searches (941)
       │
       ▼ [× Recovery Rate (91.81%)]
Recovered Searches (863.9)
       │
       ▼ [× Incremental CTR Lift (+3.5 pp)]
Incremental PDP Views (+30.2)
       │
       ▼ [× PDP -> Cart Rate (24.14%)]
Incremental Carts (+7.3)
       │
       ▼ [× Cart -> Order Rate (28.57%)]
Incremental Orders (+2.1)
       │
       ▼ [× Average Order Value ($142.58)]
Gross Incremental GMV (+$297.32 / 60 days)
       │
       ▼ [× (1 - Cannibalization Rate)]
Net Incremental GMV (+$222.99 at 25% Cannibalization)
       │
       ▼ [× (365 / 60 Days)]
Annualized Net GMV Run-Rate (+$1,356.52 / year)
```

---

## 4. Empirical Baseline Ground Truth

All baseline rates are extracted from the DuckDB relational store (`ecommerce_analytics.duckdb`):

- **Total Historical Searches**: 32,245 events `[OBSERVED]`
- **Eligible Searches**: 941 events (15.68 / day) `[OBSERVED]`
  - *Subgroup A (Zero-Result)*: 898 events (8.23% of 4+ token volume) `[OBSERVED]`
  - *Subgroup B (Low-Result 1-2)*: 43 events `[OBSERVED]`
- **Searches with PDP Click**: 29 events $	o$ **Search $	o$ PDP CTR = 3.08%** `[OBSERVED]`
- **PDP Views Generated**: 42 views (1.45 views / clicker) `[OBSERVED]`
- **Cart Items Added**: 7 items $	o$ **PDP $	o$ Cart Rate = 24.14%** (7 / 29) `[OBSERVED]`
- **Orders Placed**: 2 orders $	o$ **Cart $	o$ Order Rate = 28.57%** (2 / 7) `[OBSERVED]`
- **Historical GMV**: $285.15 ($207.47 + $77.68) `[OBSERVED]`
- **Average Order Value (AOV)**: **$142.58** ($285.15 / 2) `[OBSERVED]`
- **GMV per Eligible Search**: **$0.303** ($285.15 / 941) `[OBSERVED]`

---

## 5. Recovery Rate Benchmarking

The recovery rate is not an assumed parameter; it is grounded directly in the Stage 3 local benchmark:
- **Eligible Unmatchable Queries Tested**: 879 queries `[LOCAL BENCHMARK]`
- **Successfully Recovered Queries**: 807 queries `[LOCAL BENCHMARK]`
- **Observed Recovery Rate**: **91.81%** `[LOCAL BENCHMARK]`

*Distinction*: The 91.81% rate represents algorithmic catalog coverage under deterministic local execution. In production, real-time inventory fluctuations may alter this rate; hence, we evaluate sensitivity across 50%, 70%, 90%, and 91.81%.

---

## 6. Sensitivity Analysis: Recovery Rate $	imes$ CTR Lift

| Recovery Rate | +1.0 pp (Conservative) | +1.5 pp (Moderate) | +3.5 pp (Target MDE) | +5.0 pp (Optimistic) |
| :---: | :---: | :---: | :---: | :---: |
| **50.0%** | $281.43 | $422.15 | $985.02 | $1,407.17 |
| **70.0%** | $394.01 | $591.01 | $1,379.03 | $1,970.04 |
| **90.0%** | $506.58 | $759.87 | $1,773.03 | $2,532.91 |
| **91.81% (Benchmark)** | **$516.77** | **$775.15** | **$1,808.69** | **$2,583.85** |

*All cell values represent Annualized Gross Incremental GMV ($) `[MODELED]`.*

---

## 7. Cannibalization & Net Revenue Attribution

In e-commerce search, cannibalization occurs when:
1. A customer would have reformulated their query and purchased anyway.
2. A customer would have navigated through category taxonomy.
3. A customer substitutes a planned high-margin purchase with a cheaper relaxed alternative.

To prevent revenue overstatement:
$$	ext{Net Incremental GMV} = 	ext{Gross Incremental GMV} 	imes (1 - 	ext{Cannibalization Rate})$$

- At **0% Cannibalization**: $1,808.69 / year `[MODELED]`
- At **10% Cannibalization**: $1,627.82 / year `[MODELED]`
- At **25% Cannibalization (Base Planning Case)**: **$1,356.52 / year** `[MODELED]`
- At **40% Cannibalization**: $1,085.21 / year `[MODELED]`

---

## 8. Engineering Economics & ROI Framework

> **Important Notice**: ROI is illustrative and should be recalculated using the target company's fully-loaded engineering and infrastructure costs.

Engineering effort is treated as a configurable planning parameter:
- **Effort Input**: 1.5 person-months (Senior Search Engineer) `[PRODUCT ASSUMPTION — ILLUSTRATIVE PLANNING INPUT]`
- **Loaded Monthly Rate Input**: $15,000 / month `[PRODUCT ASSUMPTION — ILLUSTRATIVE PLANNING INPUT]`
- **Development Cost**: $22,500 one-time `[PRODUCT ASSUMPTION — ILLUSTRATIVE PLANNING INPUT]`
- **Annual Cloud & Maintenance**: $6,000 / year ($200/mo infra + $300/mo maintenance) `[PRODUCT ASSUMPTION — ILLUSTRATIVE PLANNING INPUT]`
- **Total Illustrative Year-1 Cost**: **$28,500.00** `[PRODUCT ASSUMPTION — ILLUSTRATIVE PLANNING INPUT]`

### Scaling Economics across Traffic Scenarios
- **At 1x Current Traffic (15.7 searches/day)**: Annualized net GMV is $1,809. Standalone Year-1 ROI is negative (-93.7%).
- **Illustrative 10x Traffic Scenario (157 searches/day)**: Annualized net GMV is $18,087.
- **Illustrative 100x Traffic Scenario (1,570 searches/day)**: Annualized net GMV reaches **$180,869**, delivering an illustrative ROI of **+534%** and a payback period of **1.9 months**.

---

## 9. Break-Even Analysis ($10k, $25k, $50k, $100k Targets)

Evaluating the four canonical corporate annual GMV hurdles under current baseline traffic:

$$	ext{Required CTR Lift} = rac{	ext{Target Annual GMV}}{	ext{Recovered Searches} 	imes 	ext{Funnel Value / View}}$$

| Target Annual GMV | Required CTR Lift (at 91.81% Recovery) | Required Treatment CTR | Required Recovery (at +3.5 pp lift) | Feasibility Assessment |
| :---: | :---: | :---: | :---: | :--- |
| **$10,000** | **+19.35 pp** | 22.43% | 507.6% (Exceeds 100%) | **Not achievable under current model assumptions** |
| **$25,000** | **+48.38 pp** | 51.46% | 1,269.0% (Exceeds 100%) | **Not achievable under current model assumptions** |
| **$50,000** | **+96.75 pp** | 99.84% | 2,538.0% (Exceeds 100%) | **Not achievable under current model assumptions** |
| **$100,000** | **+193.51 pp** (Exceeds 100% CTR) | 196.59% (Impossible >100%) | 5,076.0% (Exceeds 100%) | **Not achievable under current model assumptions** |

---

## 10. Data Honesty & Provenance Tags

Every metric in this model carries mandatory provenance:
- `[OBSERVED]`: Baseline funnel extracted directly from DuckDB historical data.
- `[LOCAL BENCHMARK]`: Algorithmic recovery (91.81%) measured on the local search engine.
- `[SIMULATED]`: Counterfactual treatment outcomes generated by the Stage 6 A/B experiment simulator.
- `[MODELED]`: Projected downstream business impact (incremental carts, orders, annualized GMV).
- `[PRODUCT ASSUMPTION — ILLUSTRATIVE PLANNING INPUT]`: Explicit scenario parameters (target lift +3.5 pp, cannibalization 25%, illustrative engineering cost $28.5K).
