# Product Problem Definition & Opportunity Prioritization

**Project:** E-Commerce Product Analytics — Search & Conversion Funnel  
**Source of Truth:** data/ecommerce_analytics.duckdb (all numbers independently re-queried)  
**Status:** Completed Analysis & Opportunity Prioritization

> **Notation key**  
> **[FACT]** — directly measured from the database.  
> **[INTERP]** — interpretation of measured data; plausible but not uniquely provable.  
> **[HYP]** — hypothesis requiring further testing to validate.

---

## 1. Context & Scope

The exploratory data analysis produced five statistically validated root-cause hypotheses. This document converts those hypotheses into four structured product problems, quantifies business impact using database-derived numbers, and prioritises them using a transparent RICE-variant scoring framework.

**Key dataset parameters (re-queried):**

| Metric | Value |
|:---|:---:|
| Total sessions | 31,328 |
| Sessions with PDP view | 22,346 |
| Sessions with cart addition | 7,172 |
| Completed orders | 2,880 |
| Total users | 16,000 |
| Total GMV | USD 217,860.56 |
| Average order GMV | USD 75.65 |
| Blended session-to-order CR | 9.19% |

---

## 2. The Four Product Problems

---

### Problem A — Search Discovery Failure on Specific Queries

**Problem Statement [FACT]:** Shoppers using 4+ word search queries encounter an **8.23% zero-result rate** (ZRR) — a **4.6x higher failure rate** than short queries — causing them to exit discovery before seeing a relevant product.

**Target User:** Fashion-aware shopper with specific intent who uses a precise multi-attribute query.

**Key Facts [FACT]:**
- 10,914 of 32,245 search events (33.9%) are 4+ token queries
- 8,958 unique sessions contain a long-tail search (28.6% of all sessions)
- ZRR: 8.23% (long-tail) vs 1.78% (short) — Z=28.08, p<0.0001
- CTR: 62.97% (long-tail) vs 70.77% (short) — -7.80 pp gap — Z=14.23, p<0.0001
- 7,318 unique users affected
- ZRR rises monotonically: 1 token=0.91%, 2=2.11%, 3=2.74%, 4+=8.23%

**Root-Cause Hypothesis [HYP]:** Strict term matching across query tokens. Multi-attribute queries produce zero results when any single token fails to match. Synonym layer/attribute tokenizer likely absent.

**Business Impact [FACT-DERIVED]:**
- ZRR-recoverable click opportunities (if LT ZRR matched short-query ZRR): ~703 search events
- Analytical scenario: ~91 incremental orders (~USD 6,883 GMV)
- IMPORTANT: Scenario estimate only; not guaranteed.

**Statistical Confidence:** Z=28.08 (ZRR), Z=14.23 (CTR). Consistent across all platforms and user types.

**What remains uncertain [HYP/UNKNOWN]:**
- Post-zero-result user behaviour (retry, browse, or exit)
- Whether ZRR is catalogue coverage gap or algorithmic matching failure
- Whether long-tail session CR (13.01%) reflects intent self-selection

---

### Problem B — PDP Size-Stockout Dead-End

**Problem Statement [FACT]:** Shoppers on a PDP with their preferred size OOS experience an **86.2% collapse in add-to-cart rate** (19.84% to 2.74%), creating a near-total dead-end.

**Target User:** Apparel shopper in high-stockout categories: Dresses (9.80%), Ethnic Wear (8.48%), Tops & Tees (8.03%), Jeans (7.29%).

**Key Facts [FACT]:**
- 2,807 of 44,573 product views (6.30%) have selected size OOS
- In-stock ATCR: 19.84% (N=41,766). OOS ATCR: 2.74% (N=2,807)
- Odds Ratio = 8.87 (95% CI: 7.05-11.16). Z=22.46, p<0.0001
- 2,640 sessions and 2,495 unique users affected
- Accessories (Bags, Watches, Belts) have 0% stockout

**Root-Cause Hypothesis [HYP]:** PDP fails to surface recovery paths (alt sizes, alt products, notify-me).

**Business Impact [FACT-DERIVED]:**
- 10% partial-recovery scenario: ~280 additional carts
- At blended CTO (40.16%): ~112 incremental orders (~USD 8,473 GMV)

**Statistical Confidence:** Z=22.46, p<0.0001. Largest odds ratio in dataset.

---

### Problem C — Near-Threshold Shipping Fee Abandonment

**Problem Statement [FACT]:** Shoppers with USD 38-49.99 carts convert at **29.37%** — **15.27 pp lower** than shoppers above the USD 50 free-shipping threshold (44.65%). Cliff is universal.

**Key Facts [FACT]:**
- 1,229 cart sessions in USD 38-49.99 range (avg = USD 43.89)
- Cliff CTO: 29.37%. Free-ship CTO: 44.65%. Gap: -15.27 pp. Z=8.81, p<0.0001
- All platforms affected: Android 33.84%->44.04%; Desktop 25.00%->50.18%; Mobile Web 18.15%->33.83%; iOS 34.85%->52.13%
- 1,202 unique users in cliff zone
- Sub-USD 38 sessions convert at 37.38% — higher than cliff zone

**Root-Cause Hypothesis [HYP]:** No visible cart progress indicator. Users unaware they could cheaply cross threshold.

**Business Impact [FACT-DERIVED]:**
- 30% gap-closure estimate: ~56 orders (~USD 3,347 GMV)

**Statistical Confidence:** Z=8.81, p<0.0001. No confounding from platform or user type.

---

### Problem D — Mobile Web Checkout Friction

**Problem Statement [FACT]:** Mobile Web CTO is **29.63%** vs **46.26% iOS** and **39.96% Android** — a **13.48 pp gap vs native-app average** — with no underperformance at earlier funnel stages.

**Key Facts [FACT]:**
- 7,582 Mobile Web sessions (24.2%). 1,647 cart sessions. 488 orders. CTO=29.63%
- Session-to-PDP gap vs iOS: -1.09 pp (near parity)
- PDP-to-cart gap vs iOS: -1.49 pp (near parity)
- Cart-to-order gap vs iOS: -16.63 pp (Z=10.45, p<0.0001) — stage-localised
- New user CTO: 26.56% (MW) vs 42.69% (iOS). Returning: 32.80% vs 50.05%
- 6,343 unique Mobile Web users (39.6% of total)

**Root-Cause Hypothesis [HYP]:** Mobile browsers lack stored payment credentials and biometric auth. Manual entry + absence of Web Payments API creates abandonment friction.

**Business Impact [FACT-DERIVED]:**
- 50% gap-closure scenario: ~110 orders (~USD 8,095 GMV)

**Statistical Confidence:** Z=10.45, p<0.0001. Gap in both user-type segments.
---

## 3. Impact Quantification Summary

### Table 3.1: Affected Population

| Problem | Affected Events | Sessions | Users |
|:---|:---:|:---:|:---:|
| **A** | 10,914 searches (898 ZRR) | 8,958 | 7,318 |
| **B** | 2,807 PDP views | 2,640 | 2,495 |
| **C** | 1,229 cart sessions | 1,229 | 1,202 |
| **D** | 1,647 cart sessions | 1,647 | 6,343 |

### Table 3.2: Conversion Gap Summary

| Problem | Baseline | Contrast | Gap | Z | p |
|:---|:---:|:---:|:---:|:---:|:---:|
| A: ZRR | 8.23% | 1.78% | +6.45 pp | 28.08 | <0.0001 |
| A: CTR | 62.97% | 70.77% | -7.80 pp | 14.23 | <0.0001 |
| B: ATCR | 19.84% | 2.74% | -17.10 pp | 22.46 | <0.0001 |
| C: CTO | 29.37% | 44.65% | -15.27 pp | 8.81 | <0.0001 |
| D: CTO | 29.63% | 43.11% | -13.48 pp | 10.45 | <0.0001 |

### Table 3.3: Scenario Estimates (NOT guaranteed)

| Problem | Assumption | Est. Orders | Est. GMV |
|:---|:---|:---:|:---:|
| A | ZRR drops to 1.78%; recovered clicks at 13.01% session CR | ~91 | ~USD 6,883 |
| B | 10% OOS views recover; at blended CTO 40.16% | ~112 | ~USD 8,473 |
| C | 30% of 15.27 pp gap closes via nudge | ~56 | ~USD 3,347 |
| D | 50% of 13.48 pp gap vs native avg closed | ~110 | ~USD 8,095 |

> Critical caveat: These are scenario calculations for relative sizing only.

---

## 4. Prioritisation Framework

**Priority Score** = (Impact x Reach x Confidence) / Effort  
**Evidence Score** = Impact x Reach x Confidence (effort-agnostic)

### Score Rubric

**IMPACT (1-5):** 5=Very High (>=10 pp primary KPI). 4=High (5-9 pp). 3=Moderate. 2=Small. 1=Negligible.

**REACH (1-5):** 5=>25% of sessions (>8,000). 4=15-25%. 3=8-15%. 2=3-8%. 1=<3%.

**CONFIDENCE (1-5):** 5=Strong stats + all segments. 4=Strong + most segments. 3=Significant. 2=Suggestive. 1=Anecdotal.

**EFFORT (1-5) [PM judgment]:** 5=Infra rewrite/ML pipeline. 4=Multi-team backend. 3=Backend+frontend. 2=Frontend+config. 1=Config change.

---

## 5. Prioritisation Scores

| Problem | Reach | Impact | Conf | Effort | Priority Score | Evidence Score | Rank |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **A — Search Discovery** | 4 | 4 | 5 | 5 | **16.0** | 80 | **1st** |
| **D — Mobile Web Checkout** | 3 | 4 | 5 | 4 | **15.0** | 60 | **2nd** |
| **C — Shipping Cliff** | 2 | 3 | 5 | 2 | **15.0** | 30 | **3rd** |
| **B — PDP Stockout** | 2 | 4 | 5 | 3 | **13.3** | 40 | **4th** |

### Score Justifications

**Problem A:** Reach=4 (8,958 sessions, 28.6%). Impact=4 (ZRR+CTR degradation on 33.9% of searches). Confidence=5 (Z=28.08). Effort=5 (NLP/ML search infra, multi-team multi-quarter).

**Problem B:** Reach=2 (2,807 views, 6.30%). Impact=4 (OR=8.87, strongest effect). Confidence=5 (Z=22.46). Effort=3 (inventory API + PDP component).

**Problem C:** Reach=2 (1,229 sessions, 3.92%). Impact=3 (15.27 pp relative cliff). Confidence=5 (Z=8.81). Effort=2 (frontend progress indicator).

**Problem D:** Reach=3 (1,647 cart sessions, 22.97% of carts; 6,343 users). Impact=4 (13.48 pp stage-localised gap). Confidence=5 (Z=10.45). Effort=4 (checkout redesign, payment gateway, PCI).

**Tie-breaking (C vs D):** Both score 15.0. D ranks higher on Evidence Score (60 vs 30) and broader strategic relevance.

---

## 6. Selected Primary and Secondary Problems

**Primary Problem: A — Search Discovery Failure on Specific Queries**  
**Secondary Problem: D — Mobile Web Checkout Friction**

---

## 7. Selection Rationale

### Why A Wins as Primary

1. **Widest reach in discovery** (8,958 sessions, 28.6%). Failures cascade through every downstream stage.
2. **Highest Evidence Score** (80). Largest population + strongest confirmed conversion signal.
3. **Strategic leverage.** Search-engaged sessions convert at 2.51x browse-only. Improvements amplify at scale.
4. **Compounding capability.** Every future high-intent user benefits.
5. **Explainability.** Monotonic ZRR escalation (0.91% to 8.23%) is an unambiguous structural signal.

### Why D is Secondary

1. **Stage-localised** (Cart-to-Order only). Precise problem framing.
2. **22.97% of cart sessions** on Mobile Web.
3. **Evidence Score 60** (second-highest), Z=10.45.
4. **Faster execution** than search infrastructure.
5. **Compounds with C** — solving MW checkout reduces cliff-zone severity on that platform.

### Why C is Third (Quick Win)

Effort=2 makes it fastest to ship. Cart progress indicator deploys by a frontend team. Parallel near-term initiative.

### Why B is Fourth (Highest Effect, Smallest Population)

Strongest OR (8.87) but smallest absolute reach. Cross-functional inventory dependencies. Best as parallel track.

---

## 8. Problem Statements (Primary: A)

**PM version:** High-intent shoppers who enter specific, multi-attribute search queries encounter a near-total search failure (8.23% ZRR), causing them to exit discovery before the platform can surface relevant products.

**User-centred:** When I know exactly what I want — specific style, size, colour, occasion — I struggle to find it through search, because my detailed query returns no results or irrelevant ones, making me feel the platform does not carry what I need even if it does.

**Executive:** One in three searches is a specific-intent query. Of these, 8.23% return zero results (4.6x higher than simple queries) and CTR falls by 7.80 pp. This prevents converting 28.6% of sessions at the highest-intent moment.

---

## 9. Job To Be Done (Primary)

> **When** I search for a specific product matching my precise style, size, and occasion,  
> **I want to** instantly see products that match my full intent — or understand what adjustments would surface results,  
> **so I can** make a confident purchase decision without simplifying my requirements.

---

## 10. Success Metrics (Primary)

**North Star:** ZRR on 4+ token queries. Baseline: 8.23%. Direction: Decrease.

**Secondary Metrics:**
1. Search CTR on long-tail — Baseline: 62.97%. Direction: Increase.
2. Reformulation rate on long-tail — Baseline: 44.39%. Direction: Decrease.
3. Long-tail session-to-order CR — Baseline: 13.01%. Direction: Increase (control for self-selection).
4. PDP view rate from search sessions — Baseline: 78.43%. Direction: Increase.

**Guardrail Metrics:**
1. Short-query ZRR (<4 tokens) — Must not increase from 1.78%.
2. Search latency (p95) — Must not exceed SLA.
3. Sessions reaching PDP — Must not decrease.
4. Blended session-to-order CR — Must not decrease.

---

## 11. Validation Gaps (Top 5)

1. **Post-ZRR user journey.** Do users retry, browse, or exit after zero results?
2. **Mobile Web checkout micro-step.** Where exactly does MW abandonment occur (address, payment, OTP, redirect)?
3. **Threshold awareness.** Are cliff-zone abandoners aware of the USD 50 free-shipping threshold?
4. **OOS PDP cross-navigation.** Do stockout PDP visitors navigate to alternatives or exit?
5. **ZRR root cause.** Catalogue coverage gap or algorithmic matching failure?

---

## 12. Executive Summary

| Problem | Core Friction | Key Metric | Baseline |
|:---|:---|:---|:---:|
| A | 8.23% ZRR on 4+ token queries | ZRR (long-tail) | 8.23% |
| B | 86.2% ATCR collapse on OOS size | ATCR (OOS) | 2.74% |
| C | 15.27 pp CTO drop at USD 38-49.99 | CTO (cliff) | 29.37% |
| D | 13.48 pp CTO gap vs native apps | CTO (MW) | 29.63% |

| Rank | Problem | Priority Score | Evidence Score |
|:---:|:---|:---:|:---:|
| 1 | A — Search Discovery | 16.0 | 80 |
| 2 | D — Mobile Web Checkout | 15.0 | 60 |
| 3 | C — Shipping Cliff | 15.0 | 30 |
| 4 | B — PDP Stockout | 13.3 | 40 |

**Primary:** A — Search Discovery Failure on Specific Queries  
**Secondary:** D — Mobile Web Checkout Friction  
**North Star:** ZRR on 4+ token queries. Baseline: 8.23%. Direction: Decrease.

**Next Steps:** Explore solution hypotheses for A and D, define A/B experiment designs, specify instrumentation to close validation gaps, and produce go-to-market framing.

---
*Problem Prioritization complete. Next: Product Solution Design & Experiment Framework.*