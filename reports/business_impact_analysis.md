# Automated Query Relaxation: Business Impact & GMV Opportunity Analysis

**Project**: E-Commerce Product Analytics — Search & Conversion Funnel  
**Intervention**: V1 Automated Query Relaxation / Soft-Match Fallback Engine  
**Stage**: Stage 7 / 7.1 — Business Impact Model QA & Credibility Cleanup  
**Document Status**: COMPLETED & VERIFIED  
**Observation Window**: 60 Calendar Days (Oct 1, 2026 – Nov 25, 2026)  
**Annualization Factor**: $\times (365 / 60) = 6.0833$  

---

## Executive Summary

Following the experiment design and statistical sizing established in Stage 6, Stage 7 presents an end-to-end, deterministic business impact model for Automated Query Relaxation. By propagating search recovery improvements through the empirical e-commerce conversion funnel, this analysis estimates the incremental order volume, gross merchandise value (GMV), cannibalization discount, and return on engineering investment (ROI).

```
+---------------------------------------------------------------------------------------------------+
|                                    DATA HONESTY FRAMEWORK                                         |
+---------------------------------------------------------------------------------------------------+
| [OBSERVED]          | Historical baseline performance extracted directly from DuckDB.             |
| [LOCAL BENCHMARK]   | Algorithmic recovery rate (91.81%) on local catalog search engine.         |
| [SIMULATED]         | Counterfactual treatment outcome from Stage 6 offline experiment.          |
| [MODELED]           | Projected downstream business outcomes (Orders, GMV run-rate).            |
| [PRODUCT ASSUMPTION — ILLUSTRATIVE PLANNING INPUT] | Configurable planning assumptions & costs.  |
+---------------------------------------------------------------------------------------------------+
```

### Key Business Conclusions:
1. **Target Opportunity (Scenario D: +3.5 pp CTR Lift, 91.81% Recovery)**:
   - **+30.2 Incremental PDP Views** per 60 days `[MODELED]`.
   - **+7.3 Incremental Cart Additions** per 60 days `[MODELED]`.
   - **+2.1 Incremental Orders** per 60 days `[MODELED]`.
   - **+$297.32 Incremental 60-Day GMV** $	o$ **+$1,808.69 Annualized GMV Run-Rate** `[MODELED]`.
2. **Current Scale vs Illustrative 100x Traffic Scenario**:
   - On current baseline traffic (1,600 SKUs, 941 eligible searches / 60 days), the direct annualized GMV opportunity is **+$1,809 / year** `[MODELED]` (or **+$1,357 / year** at 25% cannibalization).
   - In an **illustrative 100x traffic sensitivity scenario** (~1,570 searches/day), the same algorithmic capability delivers **+$180,869 / year** in incremental GMV with zero marginal engineering development cost.
3. **Executive Recommendation**:
   - Validate the intervention through a low-cost, live A/B canary experiment (Stage 6 protocol) to confirm live customer willingness-to-buy before making major dedicated infrastructure commitments.

---

## 1. Executive Opportunity Tree

```text
SEARCH DISCOVERY FAILURE ON MULTI-ATTRIBUTE QUERIES
│
├── Eligible Search Volume: 941 searches / 60 days (15.7 / day) [OBSERVED]
│     ├── Subgroup A (Zero-Result): 898 searches (8.23% of 4+ token)
│     └── Subgroup B (Low-Result 1-2): 43 searches
│
├── Algorithmic Recovery Rate: 91.81% (864 recovered queries) [LOCAL BENCHMARK]
│
├── Search -> PDP CTR Lift: +3.5 percentage points (3.08% -> 6.58%) [PRODUCT ASSUMPTION]
│     └── Incremental PDP Discovery: +30.2 unique views / 60 days [MODELED]
│
├── PDP -> Cart Conversion Rate: 24.14% (7 carts / 29 views) [OBSERVED]
│     └── Incremental Cart Additions: +7.3 carts / 60 days [MODELED]
│
├── Cart -> Order Conversion Rate: 28.57% (2 orders / 7 carts) [OBSERVED]
│     └── Incremental Customer Orders: +2.1 orders / 60 days [MODELED]
│
└── Average Order Value (AOV): $142.58 / order ($285.15 / 2 orders) [OBSERVED]
      │
      ▼
INCREMENTAL BUSINESS VALUE
├── 60-Day Gross Incremental GMV: +$297.32 [MODELED]
├── Net GMV after Cannibalization (25%): +$222.99 [MODELED]
└── Annualized Gross GMV Run-Rate: +$1,808.69 / year [MODELED]
```

---

## 2. Source of Truth & Observed Baseline Funnel

All conversion baselines are extracted directly from the DuckDB relational schema (`search_events`, `product_views`, `cart_events`, `orders`).

### Exact Observed Funnel on Eligible Searches (60 Days)

| Funnel Stage | Absolute Metric `[OBSERVED]` | Transition Rate `[OBSERVED]` | Benchmark / Context |
| :--- | :---: | :---: | :--- |
| **Total Marketplace Searches** | 32,245 events | — | Entire 60-day catalog search traffic |
| **4+ Token Searches** | 10,914 events | 33.85% of total | Multi-attribute, specific queries |
| **Eligible Search Opportunities** | **941 events** | 8.62% of 4+ token | High-intent failure tail (15.7 searches/day) |
| — *Subgroup A (Zero-Results)* | 898 events | 95.43% of eligible | Strict zero-result dead ends |
| — *Subgroup B (Low-Results 1-2)*| 43 events | 4.57% of eligible | Constrained discovery experiences |
| **Searches with PDP Click** | **29 events** | **3.08%** (Search $	o$ PDP CTR) | Depressed baseline CTR |
| **Total PDP Views Generated** | 42 views | 1.45 views / clicker | Multi-product exploration |
| **Cart Items Added** | **7 items** | **24.14%** (PDP $	o$ Cart Rate) | 7 unique cart journeys from 29 clickers |
| **Completed Customer Orders** | **2 orders** | **28.57%** (Cart $	o$ Order Rate) | 2 converted purchases from 7 cart journeys |
| **Total Captured GMV** | **$285.15** | — | Order 1: $207.47, Order 2: $77.68 |
| **Average Order Value (AOV)** | **$142.58** | — | $285.15 / 2 completed orders |
| **GMV per Eligible Search** | **$0.303** | — | $285.15 / 941 eligible opportunities |

---

## 3. Mathematical Attribution Framework

The model is deterministic and follows standard e-commerce funnel attribution:

$$	ext{Recovered Searches } S_{	ext{rec}} = S_{	ext{elig}} 	imes R_{	ext{recovery}}$$

$$	ext{Incremental PDP Views } \Delta 	ext{PDP} = S_{	ext{rec}} 	imes \Delta 	ext{CTR}$$

$$	ext{Incremental Carts } \Delta 	ext{Cart} = \Delta 	ext{PDP} 	imes P(	ext{Cart} \mid 	ext{PDP})$$

$$	ext{Incremental Orders } \Delta 	ext{Order} = \Delta 	ext{Cart} 	imes P(	ext{Order} \mid 	ext{Cart})$$

$$	ext{Gross Incremental GMV } 	ext{GMV}_{	ext{gross}} = \Delta 	ext{Order} 	imes 	ext{AOV}$$

$$	ext{Net Incremental GMV } 	ext{GMV}_{	ext{net}} = 	ext{GMV}_{	ext{gross}} 	imes (1 - C_{	ext{cannibalization}})$$

$$	ext{Annualized Incremental GMV} = 	ext{GMV}_{	ext{gross/net}} 	imes \left( rac{365}{60} ight)$$

---

## 4. CTR Scenario Modeling (91.81% Benchmark Recovery)

| Metric | Conservative (+1.0 pp) | Moderate (+1.5 pp) | Target MDE (+3.5 pp) | Optimistic (+5.0 pp) |
| :--- | :---: | :---: | :---: | :---: |
| **Search $	o$ PDP CTR** | 4.08% | 4.58% | **6.58%** | 8.08% |
| **Eligible Searches (60d)** | 941 | 941 | **941** | 941 |
| **Recovered Searches (60d)** | 863.9 | 863.9 | **863.9** | 863.9 |
| **Incremental PDP Views** | +8.6 | +13.0 | **+30.2** | +43.2 |
| **Incremental Cart Adds** | +2.1 | +3.1 | **+7.3** | +10.4 |
| **Incremental Orders** | +0.6 | +0.9 | **+2.1** | +3.0 |
| **60-Day Gross GMV `[MODELED]`** | +$84.95 | +$127.42 | **+$297.32** | +$424.74 |
| **Annualized Gross GMV `[MODELED]`** | **+$516.77** | **+$775.15** | **+$1,808.69** | **+$2,583.85** |
| **Annualized Orders `[MODELED]`** | +3.6 orders | +5.4 orders | **+12.7 orders** | +18.1 orders |

---

## 5. Recovery Rate $	imes$ CTR Lift Sensitivity Matrix

### Annualized Net GMV ($) Matrix (0% Cannibalization) `[MODELED]`

| Recovery Rate / CTR Lift | +1.0 pp (Conservative) | +1.5 pp (Moderate) | +3.5 pp (Target MDE) | +5.0 pp (Optimistic) |
| :--- | :---: | :---: | :---: | :---: |
| **50.0%** (Poor Fallback) | $281.43 | $422.15 | $985.02 | $1,407.17 |
| **70.0%** (Acceptable) | $394.01 | $591.01 | $1,379.03 | $1,970.04 |
| **90.0%** (Strong) | $506.58 | $759.87 | $1,773.03 | $2,532.91 |
| **91.81% (Local Benchmark)** | **$516.77** | **$775.15** | **$1,808.69** | **$2,583.85** |

---

## 6. Cannibalization Sensitivity Analysis

| Cannibalization Rate `[PRODUCT ASSUMPTION]` | 60-Day Net GMV | Annualized Net GMV `[MODELED]` | Annual GMV Eroded | Net Incremental Orders / Year |
| :---: | :---: | :---: | :---: | :---: |
| **0%** (Pure Incrementality) | $297.32 | **$1,808.69** | $0.00 | +12.7 orders |
| **10%** (Low Cannibalization) | $267.59 | **$1,627.82** | $180.87 | +11.4 orders |
| **25%** (Realistic Base Case) | $222.99 | **$1,356.52** | $452.17 | +9.5 orders |
| **40%** (Severe Substitution) | $178.39 | **$1,085.21** | $723.48 | +7.6 orders |

---

## 7. Engineering Economics & ROI Modeling

> **Note**: ROI is illustrative and should be recalculated using the target company's fully-loaded engineering and infrastructure costs.

### Illustrative Cost Inputs `[PRODUCT ASSUMPTION — ILLUSTRATIVE PLANNING INPUT]`
- **Engineering Effort Input**: 1.5 person-months (Senior Search Engineer).
- **Loaded Engineering Cost Rate**: $15,000 / month $	o$ **$22,500 one-time implementation**.
- **Cloud Infrastructure (Inverted Index / Memory)**: $200 / month $	o$ **$2,400 / year**.
- **Maintenance & Monitoring**: **$3,600 / year**.
- **Total Illustrative Year-1 Cost**: **$28,500.00**.

### Economic Assessment across Traffic Scenarios

| Scenario | Year 1 Net GMV `[MODELED]` | Total Year 1 Cost `[ASSUMPTION]` | Net Benefit / Loss | Payback Period |
| :--- | :---: | :---: | :---: | :---: |
| **Current Scale (1x Traffic)** | $1,808.69 | $28,500.00 | -$26,691.31 | 189.1 months |
| **Illustrative 10x Traffic Scenario** | $18,086.90 | $28,500.00 | -$10,413.10 | 18.9 months |
| **Illustrative 100x Traffic Scenario**| $180,869.00 | $28,500.00 | **+$152,369.00** | **1.9 months** |

---

## 8. Break-Even Analysis ($10k, $25k, $50k, $100k Targets)

Evaluating the four canonical corporate annual GMV hurdles under current baseline traffic:

| Target Annual GMV | Required CTR Lift (at 91.81% Recovery) | Required Treatment CTR | Required Recovery (at +3.5 pp lift) | Feasibility Assessment |
| :---: | :---: | :---: | :---: | :--- |
| **$10,000** | **+19.35 pp** | 22.43% | 507.6% (Exceeds 100%) | **Not achievable under current model assumptions** |
| **$25,000** | **+48.38 pp** | 51.46% | 1,269.0% (Exceeds 100%) | **Not achievable under current model assumptions** |
| **$50,000** | **+96.75 pp** | 99.84% | 2,538.0% (Exceeds 100%) | **Not achievable under current model assumptions** |
| **$100,000** | **+193.51 pp** (Exceeds 100% CTR) | 196.59% (Impossible >100%) | 5,076.0% (Exceeds 100%) | **Not achievable under current model assumptions** |

> **Key PM Insight**: Generating five-figure or six-figure GMV gains strictly from this narrow long-tail cohort (941 searches / 60 days) is mathematically impossible at current traffic volume. Achieving such milestones requires overall marketplace traffic expansion or expanding query relaxation to broader head/torso query categories.

---

## 9. Sensitivity Ranking & Tornado Analysis

Perturbing each parameter by $\pm 20\%$ reveals the following elasticity ranking:

```text
SENSITIVITY RANKING (ANNUALIZED GMV SWING FOR +/- 20% SHOCKS):
Rank 1: CTR Lift (+3.5 pp)           ───► $723.48 swing (Elasticity = 1.00)
Rank 2: Eligible Traffic (941 events) ──► $723.48 swing (Elasticity = 1.00)
Rank 3: Average Order Value ($142.58) ──► $723.48 swing (Elasticity = 1.00)
Rank 4: PDP -> Cart Rate (24.14%)     ──► $723.48 swing (Elasticity = 1.00)
Rank 5: Cart -> Order Rate (28.57%)   ──► $723.48 swing (Elasticity = 1.00)
Rank 6: Recovery Rate (91.81%)        ──► $523.09 swing (Elasticity = 0.72, capped at 100%)
Rank 7: Cannibalization (0% to 20%)   ──► $361.74 swing (Elasticity = 0.50)
```

---

## 10. Executive Recommendation: Connecting Stage 7 to Stage 6

```text
+-------------------------------------------------------------------------------------------------+
| EXECUTIVE RECOMMENDATION: VALIDATE VIA EXPERIMENT BEFORE DEDICATED INFRASTRUCTURE INVESTMENT   |
+-------------------------------------------------------------------------------------------------+
| 1. CURRENT SCALE IS MODEST:                                                                     |
|    Direct modeled GMV opportunity is relatively small (~$1.8K/year). Capital discipline         |
|    dictates that we do NOT build expensive dedicated infrastructure (Elasticsearch clusters,    |
|    vector databases) based solely on this standalone long-tail return.                         |
|                                                                                                 |
| 2. CAPABILITY IS SCALABLE:                                                                      |
|    Query Relaxation is an algorithmic platform capability with zero marginal cost per query.    |
|    In an illustrative 100x traffic scenario, annual incremental GMV reaches +$180.9K.           |
|                                                                                                 |
| 3. LOW-COST VALIDATION PATHWAY:                                                                 |
|    Proceed with the Stage 6 A/B experiment protocol (exp_query_relaxation_v1) as a lightweight   |
|    canary test. Validate whether the +1.5 pp ship threshold is achieved in live traffic.        |
|    If live lift fails or cannibalization is severe, deprioritize before incurring major costs.  |
+-------------------------------------------------------------------------------------------------+
```
