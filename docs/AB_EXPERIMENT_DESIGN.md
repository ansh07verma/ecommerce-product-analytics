# Automated Query Relaxation: A/B Experiment Design Specification

**Document Title**: Automated Query Relaxation A/B Experiment Design & Statistical Protocol  
**Author**: Product Management + Product Analytics  
**Version**: 1.0.0 (Stage 6)  
**Status**: APPROVED FOR SIMULATION / READY FOR PRODUCTION INSTRUMENTATION  
**Feature Branch**: `feat(experiment): add query relaxation A/B experiment simulator`  

---

## What This Experiment Can and Cannot Prove

Before reviewing the technical specification, the boundaries of this experiment framework must be clearly defined:

```
+---------------------------------------------------------------------------------------------------+
| WHAT THIS EXPERIMENT CAN PROVE IN PRODUCTION:                                                     |
| • Whether randomized exposure to Query Relaxation causes a statistically significant increase     |
|   in Search -> PDP CTR on eligible multi-token searches.                                          |
| • Whether Query Relaxation degrades catalog trust, relevance, or conversion quality (guardrails). |
| • The exact net business impact on orders and revenue under live user behavior.                   |
+---------------------------------------------------------------------------------------------------+
| WHAT THIS OFFLINE SIMULATOR CANNOT PROVE:                                                         |
| • Actual causal production impact (treatment lift in the simulator is an explicit configurable    |
|   model parameter, NOT an observed customer reaction).                                            |
| • Real customer reaction to specific relaxed result sets.                                         |
| • True cross-channel or browse cannibalization.                                                   |
| The offline simulator exists exclusively for statistical sizing, sensitivity analysis,           |
| engineering verification, and PM decision framework preparation.                                  |
+---------------------------------------------------------------------------------------------------+
```

---

## 1. Product Hypothesis

> **If** we automatically apply safe single-token query relaxation to specific, multi-attribute searches ($\ge 4$ tokens) returning fewer than 3 strict results,  
> **Then** eligible Search $	o$ PDP Click-Through Rate will increase by at least **+3.5 percentage points** (from 3.08% to 6.58%),  
> **Because** customers are presented with relevant, in-stock alternatives from the intended product category rather than being abandoned on a zero-result or dead-end search page.

---

## 2. Experiment Objective

To rigorously test whether automated query relaxation generates incremental product discovery and downstream conversion without introducing irrelevant results, increasing quick-backs, or violating latency SLAs.

---

## 3. Primary Metric

- **Metric**: **Search $	o$ PDP Click-Through Rate (CTR)** on Eligible Searches
- **Definition**:
  $$	ext{Eligible Search}	o	ext{PDP CTR} = rac{	ext{Count of eligible search events followed by at least one PDP view in session}}{	ext{Total eligible search events}}$$
- **Baseline**: **3.08%** (29 PDP views across 941 eligible opportunities) `[OBSERVED]`
- **Target MDE**: **+3.5 percentage points** (3.08% $	o$ 6.58%) `[PRODUCT ASSUMPTION]`
- **Ship Criterion**: Absolute lift $\ge +1.5	ext{ pp}$ with $p < 0.05$ `[PRODUCT ASSUMPTION]`

---

## 4. Secondary Metrics

1. **Zero-Result Rate (ZRR)**:
   - Target: Decrease from 8.23% to $<2.0\%$ on 4+ token queries `[PRODUCT SPEC]`.
2. **Query Reformulation Rate**:
   - Baseline: 44.39% on 4+ token searches `[OBSERVED]`.
   - Target: Decrease by $\ge 10.0	ext{ pp}$ (target $<34.0\%$).
3. **Search $	o$ Add-to-Cart Rate**:
   - Baseline: 24.14% of clickers `[OBSERVED]`.
   - Target: Maintain or increase (non-inferiority).
4. **Search $	o$ Order Conversion Rate**:
   - Baseline: 28.57% of cart-adders `[OBSERVED]`.
   - Target: Non-inferiority margin of $-1.0	ext{ pp}$.
5. **Gross Merchandise Value (GMV) per Eligible Search**:
   - Baseline: $\$0.303$ per eligible search ($285.15 / 941$) `[OBSERVED]`.

---

## 5. Guardrail Metrics

To protect customer experience and platform trust, the experiment will trigger immediate review or rollback if any guardrail is violated:

| Metric | Target / SLA | Baseline | Failure Action | Status in Current System |
| :--- | :--- | :--- | :--- | :--- |
| **P95 Search Latency** | $\le 50	ext{ ms}$ (PRD SLA) | 0.82 ms (strict) | Rollback | 1.95 ms `[LOCAL BENCHMARK]` |
| **P99 Search Latency** | $\le 100	ext{ ms}$ | 1.45 ms (strict) | Alert | 3.80 ms `[LOCAL BENCHMARK]` |
| **Quick-Back Rate** | $\le 15.0\%$ ($<5$s dwell) | *Not tracked* | Iterate / Pause | `NOT AVAILABLE IN CURRENT DATASET` |
| **Search Session Bounce Rate** | $\le 40.0\%$ | *Not tracked* | Iterate / Pause | `NOT AVAILABLE IN CURRENT DATASET` |
| **Zero-Result Rate Regression** | No variant $>10.0\%$ | 8.23% | Rollback | Monitored |

---

## 6. Experiment Unit

- **Unit**: **User ID** (`user_id`).
- **Why User-Level Randomization is Mandatory**:
  1. **Prevents Cross-Variant Contamination**: If a user runs multiple searches in a session, query-level randomization would expose them to fluctuating search paradigms.
  2. **Avoids Inconsistent User Experience**: Repeated searches for similar products would behave unpredictably, confusing customers.
  3. **Preserves Downstream Attribution**: Downstream cart adds and orders occur at the session/user level; query-level assignment breaks clean conversion attribution.
  4. **Simplifies Interpretation**: Enables standard customer lifetime and cohort analysis.

---

## 7. Randomization Strategy

Deterministic hash bucketing via MD5:

$$	ext{bucket} = 	ext{MD5}(	ext{experiment\_id} + 	ext{user\_id}) \pmod{100}$$

- **Buckets 0–49**: Control (50%)
- **Buckets 50–99**: Treatment (50%)

Properties:
- **Deterministic**: A user always receives the identical variant across all sessions and devices.
- **Orthogonal**: Changing `experiment_id` re-randomizes assignments across users without correlation to past experiments.
- **Balanced**: Standard uniform hash distribution guarantees approximately 50/50 allocation.

---

## 8. Eligibility Rules

A search opportunity is eligible for relaxation evaluation if and only if:
1. `token_count >= 4`: Query contains 4 or more meaningful whitespace-delimited tokens.
2. `strict_results_count < 3`: Strict conjunctive matching yields 0, 1, or 2 products.
3. `catalog_status`: Search is evaluable against active in-stock inventory.

*Historical Volume*: Exactly **941 opportunities** across the 60-day historical window (898 Subgroup A zero-results, 43 Subgroup B low-results).

---

## 9. Control Experience

- **Search Path**: Executes standard deterministic strict search (`LocalSearchEngine.search(query)`).
- **Behavior on Failure**: Returns 0 or low results without modification.
- **SRP Rendering**: Standard empty state or partial result list.

---

## 10. Treatment Experience

- **Search Path**:
  ```text
  Strict Search (query)
         │
  [Results < 3 and Tokens >= 4?]
         ├─ NO  ──> Return strict results
         └─ YES ──> Evaluate Query Relaxation Engine
                        │
                  [Safe Fallback Found?]
                        ├─ YES ──> Return recovered results + transparency banner
                        └─ NO  ──> Fall back to strict zero/low results
  ```
- **Safety Safeguards**: Core category tokens are locked; out-of-stock items remain excluded; relaxation is rejected if candidate score $< 0.40$.

---

## 11. Statistical Test Specification

- **Primary Test**: Two-Proportion Two-Tailed Z-Test.
- **Null Hypothesis ($H_0$)**: $p_{	ext{treatment}} - p_{	ext{control}} = 0$.
- **Alternative Hypothesis ($H_1$)**: $p_{	ext{treatment}} - p_{	ext{control}} 
eq 0$.
- **Significance Level ($lpha$)**: 0.05 ($Z_{lpha/2} = 1.960$).
- **Statistical Power ($1 - eta$)**: 0.80 ($Z_eta = 0.842$).

---

## 12. Power Analysis & MDE Sizing

$$	ext{Baseline Rate } p_1 = 0.0308 \quad (pprox 3.08\%)$$

| Target MDE | Variant Sample Size | Total Sample Size | Modeled Days (~15.7/day) `[MODELED]` | Feasibility |
| :---: | :---: | :---: | :---: | :--- |
| **+1.0 pp** | 5,421 | 10,842 | 692 days (~23.1 mo) | **Prohibitive** |
| **+1.5 pp** | 2,570 | 5,140 | 328 days (~10.9 mo) | **Extended** |
| **+2.0 pp** | 1,536 | 3,072 | 196 days (~6.5 mo) | **Extended** |
| **+3.5 pp** | **589** | **1,178** | **76 days (~2.5 mo)** | **RECOMMENDED TARGET** |
| **+5.0 pp** | 330 | 660 | 43 days (~1.4 mo) | **Fast Read** |

---

## 13. MDE Selection Rationale

We selected **+3.5 percentage points** ($3.08\% 	o 6.58\%$) as our target experimental MDE because:
1. **Traffic Reality**: At 15.7 searches/day, detecting smaller effects would require running the experiment for over 6 months, introducing seasonal drift and code divergence risks.
2. **Algorithmic Potential**: Local benchmarks showed query relaxation recovers results for 91.81% of unmatchable queries, providing substantial surface area for a 3.5 pp conversion lift.

---

## 14. Sample-Size & Duration Planning

- Target Total Sample: **1,178 eligible searches** (~589 per variant).
- Duration at Current Traffic: **~76 calendar days** (~10.8 weeks).
- Mid-Experiment Checkpoint: Day 38 (~589 cumulative searches) for health and guardrail validation only.

---

## 15. Decision Framework: SHIP / ITERATE / DO NOT SHIP

```
+-------------------------------------------------------------------------------------------------+
| DECISION RULE MATRIX [PRODUCT ASSUMPTIONS]                                                      |
+-------------------------------------------------------------------------------------------------+
| SHIP:                                                                                           |
|   1. Search -> PDP CTR demonstrates p < 0.05 (two-tailed z-test).                                |
|   2. Absolute CTR lift >= +1.5 percentage points.                                               |
|   3. P95 latency <= 50 ms (PRD SLA maintained).                                                 |
|   4. Zero-result rate <= 10.0% and no downstream conversion deterioration.                      |
+-------------------------------------------------------------------------------------------------+
| ITERATE:                                                                                        |
|   1. Positive CTR lift (0 < lift < +1.5 pp) OR p >= 0.05 (inconclusive).                         |
|   2. CTR improves significantly, but Add-to-Cart rate decreases materially (> -2.0 pp).        |
|   Action: Refine relaxation ranking weights or expand token vocabulary; re-test.                 |
+-------------------------------------------------------------------------------------------------+
| DO NOT SHIP:                                                                                    |
|   1. Search -> PDP CTR lift <= 0.0 pp (flat or negative).                                       |
|   2. P95 latency > 50 ms or P99 latency > 100 ms.                                               |
|   3. Relevance degradation / severe customer complaint rate spike.                              |
+-------------------------------------------------------------------------------------------------+
```

---

## 16. Risks & Mitigation

1. **Relevance Degradation (Bad Matches)**:
   - *Mitigation*: Category locking preserves core nouns; selective attribute scoring removes only low-impact modifiers.
2. **Cannibalization of Direct Searches**:
   - *Mitigation*: Strict search runs first; relaxation triggers *only* when strict results $< 3$.
3. **Latency Bloat**:
   - *Mitigation*: Fallback evaluation is capped at 10 candidates; in-memory inverted index benchmark runs in $<2.0	ext{ ms}$.

---

## 17. Instrumentation Requirements

Production telemetry must log for every search:
- `search_id`, `session_id`, `user_id`, `timestamp`
- `query_text`, `normalized_query`, `token_count`
- `experiment_id`, `variant_assigned`
- `is_eligible`, `strict_results_count`, `final_results_count`
- `relaxation_triggered`, `relaxation_status`, `removed_tokens`
- `pdp_click_flag`, `click_timestamp`, `clicked_product_id`

---

## 18. Rollback Criteria

The experiment will be halted immediately if:
- P95 search latency exceeds **50 ms** across a rolling 1-hour window.
- Search service HTTP 500 error rate exceeds **0.1%**.
- Zero-result rate on Treatment exceeds Control by $>1.0	ext{ pp}$.

---

## 19. Data Honesty Standard

All project communications and documentation must maintain strict categorization:
- `[OBSERVED]`: Values from historical logs (e.g., 3.08% baseline CTR, 8.23% ZRR).
- `[LOCAL BENCHMARK]`: Engine performance on local catalog (e.g., 91.81% recovery, 1.95 ms latency).
- `[SIMULATED]`: Counterfactual outcomes produced by the experiment model (e.g., 5.83% treatment CTR).
- `[MODELED]`: Extrapolated business projections (e.g., +$4,755 annualized GMV).
- `[PRODUCT ASSUMPTION]`: Decision thresholds (e.g., +1.5 pp ship criteria, $lpha = 0.05$).

---

## 20. Conclusion & Next Steps

This specification establishes an end-to-end, statistically defensible protocol for proving product impact. The offline simulator (`src/ab_experiment.py`) provides engineering certainty that randomization, telemetry schemas, and analysis pipelines are verified prior to production deployment.
