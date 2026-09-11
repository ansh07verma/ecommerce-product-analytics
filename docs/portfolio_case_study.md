# Portfolio Case Study: E-Commerce Search & Conversion Funnel Analytics

**Project:** E-Commerce Product Analytics ? Search Discovery & Funnel Optimization  
**Role:** Product Manager (Search, Discovery & Conversion)  
**Read Time:** ~3 minutes  

---

## 1. The Business Problem
In a fashion e-commerce marketplace with 31,328 user sessions, searchers convert at **11.92%** compared to only **4.75%** for non-search browse sessions (a **2.51x conversion advantage**). Search is clearly the highest-intent channel on the platform. However, top-line conversion stalled below 10% (9.19% overall), with noticeable drop-offs across the funnel. Rather than assuming where the problem lay, I conducted a full-funnel diagnostic audit across 32,245 search events, 22,346 product views, 7,172 cart additions, and 2,880 completed orders to locate the highest-leverage breakdown.

---

## 2. The Data & Methodology
- **Dataset:** Event-level transactional database (`data/ecommerce_analytics.duckdb`) comprising 16,000 users, 1,600 catalog products, 31,328 sessions, and 7 core entity tables.
- **Methodology:** SQL segmentation, parametric hypothesis testing (two-proportion $Z$-tests, odds ratios), funnel drop-off analysis, and RICE-variant feature scoring.
- **Rigor Rule:** Strictly separated empirical facts (`[FACT]`), analytical interpretations (`[INTERP]`), and behavioral hypotheses (`[HYP]`).

---

## 3. What I Found: Four Funnel Leaks
Across the customer journey, four distinct failure points emerged:
1. **Search Discovery Collapse:** While 1-3 token head queries had a low **1.78% Zero-Result Rate (ZRR)** and **70.78% Click-Through Rate (CTR)**, specific queries ($\ge 4$ tokens, e.g., *"men black slim cotton shirt"*) suffered an alarming **8.23% ZRR** (898 events) and CTR fell to **62.95%** ($p < 0.0001$).
2. **Mobile Web Checkout Friction:** Cart-to-Order conversion was only **29.63% on Mobile Web**, compared to **42.94% on combined native apps** (a **13.31 pp deficit**, $p < 0.0001$).
3. **Shipping Fee Cliff:** Carts in the $38-$49.99 tier converted at **29.37%** vs. **44.65%** for carts reaching the $50 free-shipping threshold (a **15.28 pp drop**, $p < 0.0001$).
4. **Out-of-Stock Size Rejection:** PDP Add-to-Cart rate collapsed from **19.84%** for in-stock sizes to **2.74%** when a shopper encountered a stockout ($p < 0.0001$).

---

## 4. Root-Cause Hypotheses
Focusing on the search breakdown, I analyzed query structures and behavioral patterns:
- **Observation:** 44.39% of 4+ token searches resulted in an immediate within-session query reformulation (vs. 42.41% on short queries).
- **Hypothesis:** Evidence supports the hypothesis that the existing retrieval system has insufficient relevancy for multi-attribute queries. When shoppers combine multiple descriptive attributes (e.g., gender, color, fabric, category), the system over-constrains the query, returning an empty state or sparse results despite relevant partial inventory existing in the catalog.

---

## 5. Prioritization Framework
Using an objective RICE scoring matrix (Reach $	imes$ Impact $	imes$ Confidence / Effort):
- **Search Discovery Failure scored 64.0 (Rank 1):** Highest reach (touches 8,958 sessions, 7,318 users) at the mouth of the intent funnel.
- **Mobile Web Checkout scored 31.5 (Rank 2):** High impact, but sits downstream (touches 1,647 cart sessions).
- **Shipping Cliff scored 12.0 (Rank 3) & Stockouts scored 9.9 (Rank 4):** Smaller localized cohorts.

*Decision:* Prioritize Search Discovery first because upstream gains compound through every subsequent funnel step. Mobile Web checkout was slated as the immediate Q3 follow-up.

---

## 6. The Product Decision & Non-Goals
- **Primary Job to Be Done (JTBD):** *"When I know roughly what product I want and describe it using multiple attributes, I want search to understand my intent and show relevant purchasable products, so I can quickly find something worth buying."*
- **Non-Goals:** Do NOT rebuild the search engine from scratch; do NOT deploy complex, uncalibrated vector/semantic models immediately; do NOT redesign the entire UI.

---

## 7. The MVP: Automated Query Relaxation / Soft-Match Fallback
- **Mechanism:** When a query contains $\ge 4$ tokens AND the existing retrieval returns $< 3$ in-stock products:
  1. Identify and strictly preserve the primary product category noun (e.g., "shirt", "dress").
  2. Identify the least-selective modifier (highest document frequency in catalog) and relax it.
  3. Execute a fallback query across the remaining $N-1$ tokens.
  4. Enforce a minimum relevance score floor to prevent surfacing low-quality junk.
  5. Present up to 20 partial matches accompanied by an informative UI transparency banner: *"We couldn't find exact matches for all terms. Showing closest matches for [Relaxed Query] with [Dropped Term] removed."*
  6. Provide an immediate 1-tap override link: *"Search anyway for exact [Original Query]"*.

---

## 8. Defensible Experiment Design (EXP-01)
- **Architecture (Option C):** Randomize all 4+ token searchers at the persistent user level (`hash(experiment_id + user_id) % 100`, with cookie fallback for guests), while activating the relaxation intervention dynamically only when existing results $< 3$.
- **Primary Analysis Subgroup:** The eligible low-result cohort (941 baseline searches; 898 zero-result + 43 sparse-result).
- **Experiment Baseline:** **3.08% Search-to-PDP CTR** on eligible searches (29 clicks / 941 searches).
- **Context Metric:** **62.95% Search-to-PDP CTR** across all 10,914 specific searches.
- **Statistical Power Reality:** With ~15.7 eligible searches/day, detecting a $+3.5	ext{ pp}$ lift (from 3.08% to 6.58%) requires ~1,000 eligible searches (~64 days). An initial 4-week canary experiment is powered to detect transformational lifts ($\ge +5.0	ext{ pp}$), followed by a phased multi-category rollout for long-term validation.
- **Guardrails:** Search latency SLA (proposed p95 $< 250	ext{ ms}$), short-query head CTR (neutral), search session bounce rate ($< 40\%$), and quick-back bounce rate ($< 5	ext{s}$ duration delta $\le +1.0	ext{ pp}$).

---

## 9. Expected Business Impact
- Recovers high-intent drop-offs across the 898 observed zero-result queries and 43 sparse queries.
- Narrows the conversion deficit between specific-query sessions (13.01%) and baseline marketplace sessions (14.85%).
- Lifts top-of-funnel discovery throughput, feeding more qualified shoppers into the checkout funnel.

---

## 10. What I Would Do Next
1. **Calibrate Relevance Thresholds Offline:** Benchmark the proposed relevance score floor against historical click logs before production traffic ramp.
2. **Phase 2 (Q3): Interactive Refinement Chips:** Expose dismissible token chips (`[Black x] [Cotton x]`) to empower user-guided query editing.
3. **Execute Mobile Web Checkout Overhaul:** Launch 1-tap digital wallets (Apple Pay / Google Pay) to attack the 13.31 pp Cart-to-Order mobile web deficit.
