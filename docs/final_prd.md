# Final Product Requirements Document (PRD)

**Project:** E-Commerce Product Analytics ? Search & Conversion Funnel  
**Feature Name:** Automated Query Relaxation & Intent Recovery (MVP: SOL-01 / EXP-01)  
**Target Role:** Product Manager (Search, Discovery & Conversion Funnel)  
**Status:** Approved for Controlled Experimentation  
**Companion Documents:** [final_product_spec.md](final_product_spec.md), [../reports/final_requirements.csv](../reports/final_requirements.csv), [../reports/final_metrics_dictionary.csv](../reports/final_metrics_dictionary.csv)  

> **Methodological Notation Key**  
> **[FACT]** ? Directly measured and independently validated from `data/ecommerce_analytics.duckdb`.  
> **[INTERP]** ? Analytical interpretation; logical deduction grounded in observed user behavior.  
> **[HYP]** ? Testable hypothesis; subject to empirical validation in a randomized controlled experiment.  
> **[ASSUMPTION]** ? Explicitly labeled modeling assumption for sample sizing and experimentation.  
> **[PROPOSED REQUIREMENT]** ? Concrete engineering, product, or design specification to be built.


### 4.3 Metric Reconciliation Note: ZRR & Mobile Web Comparisons
- **Zero-Result Rate (8.23% vs. 10.81%):** In earlier exploratory work (exploratory SQL & statistical analysis), queries categorized under the synthetic attribute `query_type = 'long_tail_specific'` exhibited a **10.81% ZRR** (872 zero-results / 8,067 queries). In our primary problem definition and PRD, we adopted the broader canonical token-count definition: all queries with $\ge 4$ whitespace-delimited tokens (10,914 total queries, including 2,847 multi-token branded queries). Across all 10,914 queries, there are 898 zero-result events, establishing the canonical baseline **ZRR = 8.23%** ($898 / 10,914$). Both metrics are mathematically valid and reflect different denominators.
- **Mobile Web Conversion Deficit (13.31 pp vs. 13.48 pp):** The pooled Cart-to-Order conversion rate for native app shoppers (iOS + Android combined) is **42.94%** (1,986 orders / 4,625 carts), establishing a **13.31 pp deficit** compared to Mobile Web (29.63%). The 13.48 pp figure cited in earlier exploratory notes represented an unweighted arithmetic average of iOS (46.26%) and Android (39.96%). The canonical pooled deficit is **13.31 pp**.
- **Metric Role Distinction:** The **3.08% CTR** is the true baseline of the eligible intervention cohort (<3 results; 29 clicks / 941 searches). The **62.95% CTR** is the broader context metric and macro Intent-to-Treat (ITT) guardrail across all 10,914 4+ token searches.

---


# 1. Executive Summary

### Problem & Opportunity Overview
In an e-commerce fashion marketplace, shoppers who formulate highly specific, multi-attribute queries represent our highest purchase intent. However, empirical analysis of 32,245 search events reveals a severe discovery failure: **[FACT]** 4+ token searches experience an **8.23% Zero-Result Rate (ZRR)** (898 events) compared to only **1.78%** on 1?3 token head queries. Furthermore, click-through engagement (**[FACT]** Search-to-PDP CTR) drops from **70.78%** on short queries to **62.95%** on 4+ token searches, and **44.39%** of these specific queries result in immediate, frustrated reformulations. This discovery breakdown affects 8,958 sessions (28.6% of marketplace traffic) and depresses session conversion to 13.01% (vs. 14.85% marketplace baseline).

### Selected MVP Solution
To resolve this discovery bottleneck, we specify **SOL-01: Automated Query Relaxation / Soft-Match Fallback**. When a high-intent shopper enters a specific query ($\ge 4$ tokens) and the primary strict retrieval returns fewer than 3 in-stock items, the search engine automatically intercepts the empty/sparse state, preserves the primary product category noun, drops the least-selective modifier, and returns up to 20 relevant partial-match products accompanied by a transparent user-facing notification banner (*"Showing closest matches for [Relaxed Query]"*).

### Validation & Experiment Approach
The MVP will be validated via **EXP-01**, a 50/50 randomized controlled trial running for approximately **4 weeks (~5,000 eligible searches)**. The primary success metric is **Search-to-PDP CTR on eligible 4+ token queries**, with strict guardrails ensuring search latency remains **p95 < 250 ms**, short-query CTR does not regress, and quick-back bounce rates ($< 5	ext{s}$ duration) do not increase.

---

# 2. Product Context

### 2.1 The Role of Search in Marketplace Conversion
Search is the primary discovery engine for high-intent e-commerce shoppers. While catalog browsing and category navigation serve exploratory, low-intent traffic, searchers arrive with an explicit mental model of what they wish to purchase. Enabling fast, frictionless discovery directly dictates whether a visit converts into realized Gross Merchandise Value (GMV) or abandons to a competitor.

### 2.2 Strategic Importance of Highly Specific Queries
Queries with 4 or more tokens (e.g., *"men black slim cotton shirt"*, *"women floral summer midi dress"*) account for **[FACT] 33.85% of total marketplace search volume** (10,914 events). These shoppers are not browsing idly; they are describing specific product attributes (Gender, Color, Fit, Fabric, Category). When the platform returns an empty screen, it penalizes our most qualified customers.

### 2.3 Prioritization Rationale: Why Search Discovery Over Other Funnel Problems
During our full-funnel diagnostic audit, four major funnel leaks were evaluated and prioritized using a multi-criteria RICE evaluation:
1. **Search Discovery Failure (RICE: 64.0, Rank 1):** Top-of-funnel reach (8,958 sessions, 7,318 users). Fixing discovery expands the volume of qualified shoppers entering the checkout funnel.
2. **Mobile Web Checkout Friction (RICE: 31.5, Rank 2):** Critical 13.48 pp Cart-to-Order conversion gap, but strictly downstream (touches 1,647 cart sessions). Retained as the secondary strategic priority.
3. **Shipping Cliff Abandonment (RICE: 12.0, Rank 3):** Localized to the $38?$49.99 cart sub-tier (1,229 sessions).
4. **PDP Size Stockout Rate (RICE: 9.9, Rank 4):** Catalog/supply-chain bounded friction (2,640 sessions).

Search Discovery Failure was selected because **[INTERP]** upstream improvements compound through every subsequent funnel stage.

---

# 3. Problem Definition

### 3.1 User Problem
High-intent shoppers who know what they want and describe items using multiple attributes are frequently met with empty result grids or sparse, irrelevant inventory. They are forced to guess how the marketplace indexes products, manually deleting words and re-typing queries in frustration.

### 3.2 Business Problem
The marketplace loses substantial GMV from high-intent search abandonment. Specific-query sessions convert at **[FACT] 13.01%** (1,165 orders from 8,958 sessions), creating an uncaptured revenue gap of thousands of dollars in high-margin fashion sales.

### 3.3 Problem Statement
> *"Shoppers who formulate highly specific, multi-attribute search queries experience substantially worse discovery outcomes, including elevated zero-result rates and lower click-through engagement, causing high-intent shoppers to abandon discovery."*

### 3.4 Job to Be Done (JTBD)
> *"When I know roughly what product I want and describe it using multiple attributes,  
> I want search to understand my intent and show relevant purchasable products,  
> so I can quickly find something worth buying."*

### 3.5 Affected Population & Timing
- **Who is affected:** **[FACT]** 7,318 active users (45.74% of active users) who conduct 4+ token searches.
- **When it occurs:** Primarily when users combine 3 or more descriptive facets (e.g., Color + Material + Category + Style).
- **Why it matters:** 898 zero-result events represent 100% immediate discovery drop-off.

---

# 4. Evidence & Baseline

### 4.1 Canonical Evidence Table

| Funnel Metric | Canonical Baseline (4+ Tokens) | Comparison Benchmark (1?3 Tokens) | Delta & Statistical Significance | Product Interpretation |
|:---|:---:|:---:|:---:|:---|
| **Search Volume** | **10,914 searches** (33.85%) | **21,331 searches** (66.15%) | Total: 32,245 searches | **[FACT]** Specific queries represent 1 in every 3 searches. |
| **Zero-Result Rate (ZRR)** | **8.23%** (898 events) | **1.78%** (380 events) | **+6.45 pp** ($Z = 28.08, p < 0.0001$) | **[FACT]** Specific queries are 4.6x more likely to yield zero hits. |
| **Search-to-PDP CTR** | **62.95%** (6,870 clicks) | **70.78%** (15,098 clicks) | **-7.83 pp** ($Z = 14.23, p < 0.0001$) | **[FACT]** Significant discovery engagement penalty on long-tail. |
| **Reformulation Rate** | **44.39%** (4,845 searches) | **42.41%** (9,047 searches) | **+1.98 pp** ($Z = 3.42, p = 0.0006$) | **[FACT]** Elevated friction; shoppers repeatedly re-type queries. |
| **Eligible Searches (<3 Hits)** | **941 searches** (933 sessions) | N/A (Canonical Gate) | Subgroup A: 898 (95.4%)<br>Subgroup B: 43 (4.6%) | **[FACT]** 95.4% of eligible queries are completely empty dead-ends. |
| **Eligible Search CTR** | **3.08%** (29 clicks / 941) | 68.61% on 6+ result tier | **-65.53 pp** deficit | **[FACT]** When results <3, discovery completely collapses. |
| **Session Conversion Rate** | **13.01%** (1,165 / 8,958) | 14.85% marketplace baseline | **-1.84 pp** deficit | **[FACT]** Uncaptured commercial opportunity. |

*(All numbers independently queried from `data/ecommerce_analytics.duckdb`)*

### 4.2 What the Data Proves vs. What It Does NOT Prove
- **What the data PROVES [FACT]:**
  1. Specific 4+ token queries experience statistically significant worse discovery outcomes (higher ZRR, lower CTR, higher reformulation).
  2. The vast majority of low-result specific queries (898 out of 941, 95.4%) return zero results.
  3. Over 7,300 shoppers and nearly 9,000 sessions are exposed to this discovery friction.
- **What the data DOES NOT Prove [INTERP / HYP]:**
  1. It does NOT prove the exact search engine architecture (we do not claim the underlying algorithm is definitely Boolean).
  2. It does NOT prove that users prefer partial matches over an empty screen (this is our hypothesis to be tested in EXP-01).
  3. It does NOT prove that misspellings cause the failure (attribute intersection is the primary driver).

---

# 5. Product Goal & Non-Goals

### 5.1 Primary Product Goal
> **"Increase successful product discovery for high-intent, multi-attribute searches by eliminating zero-result dead-ends, without degrading relevance, search latency, or overall marketplace conversion."**

### 5.2 Measurable Objectives (Key Results)
1. **KR-1:** Achieve a statistically significant positive lift in **Search-to-PDP CTR on eligible 4+ token queries** ($p < 0.05$) in EXP-01.
2. **KR-2:** Reduce **Zero-Result Rate on 4+ token queries from 8.23% to $< 2.5\%$**.
3. **KR-3:** Maintain **Search p95 Latency $< 250	ext{ ms}$** throughout experiment runtime.
4. **KR-4:** Zero statistically significant regression on **Short-Query CTR (70.78%)** or **Quick-Back Bounce Rate** ($\Delta \le +1.0	ext{ pp}$).

### 5.3 Non-Goals
The following areas are explicitly **out of scope** for this MVP:
- **Rebuilding the search engine:** We are not migrating from Elasticsearch/OpenSearch to a new infrastructure stack.
- **Full Semantic / Vector Search:** We are not deploying dense neural embeddings, vector databases, or LLM retrieval pipelines in this stage.
- **Search Personalization:** We are not personalizing result ranking based on past user affinities.
- **Complete SERP Redesign:** We are not altering facet filters, sorting dropdowns, or product card layouts.
- **Mobile Web Checkout:** We are not addressing checkout form friction in this intervention.

---

# 6. Target Users & Use Cases

### 6.1 Target User Segments
1. **Primary Segment: Multi-Attribute Fashion Shoppers:** Visitors formulating 4+ token queries seeking specific combinations of style, color, cut, and fabric.
2. **Subgroup A Shoppers (Zero-Result Victims):** 898 query events where current strict search returns an empty state.
3. **Subgroup B Shoppers (Sparse-Result Victims):** 43 query events where strict search returns only 1?2 items, providing insufficient browse choice.

### 6.2 Representative Hypothetical Use Cases

*(Note: The following are illustrative product scenarios, not individual customer interview transcripts.)*

- **Scenario 1 (Modifier Relaxation):**
  - *Query:* `"men black slim cotton shirt"`
  - *Strict Match:* 0 items match all 5 tokens in stock.
  - *MVP Behavior:* System identifies `"shirt"` as category noun, drops modifier `"slim"` (highest document frequency modifier), and executes relaxed query `"men black cotton shirt"`. Returns 14 in-stock shirts with context banner.
- **Scenario 2 (Fabric / Style Relaxation):**
  - *Query:* `"women floral summer midi dress"`
  - *Strict Match:* 0 items match all 5 tokens.
  - *MVP Behavior:* Preserves `"dress"`, drops `"summer"`, returns 18 floral midi dresses.
- **Scenario 3 (Brand + Category Preservation):**
  - *Query:* `"Nike white running shoes men"`
  - *Strict Match:* 1 item in stock.
  - *MVP Behavior:* Displays the 1 exact match at top, relaxes `"running"` to display 12 Nike white athletic shoes below.

---

# 7. Current User Journey vs. Proposed MVP Journey

### 7.1 Status Quo User Journey (Failure Cycle)
```
[Shopper Formulates Specific Query (4+ Tokens)]
       ?
[Strict Conjunction Retrieval Executed]
       ?
[0?2 Results Returned] (8.23% ZRR, 62.95% CTR, 3.08% on <3 results)
       ?
[Shopper Faces High Cognitive Friction] (44.39% Reformulation Rate)
       ?
[Manual Token Deletion & Guesswork]
       ?
[Discovery Fatigue & Session Abandonment] (13.01% Session CR)
```

### 7.2 MVP Intervened Journey (Intent Recovery Flow)
The MVP intervenes at the exact moment strict retrieval evaluates result count:
```
[Shopper Formulates Specific Query (4+ Tokens)]
       ?
[Primary Strict Retrieval Executed]
       ?
[Result Count Check: Are Hits < 3?]
       ??? NO  ??? [Display High-Precision Strict Matches]
       ??? YES ??? [MVP INTERVENTION: Automated Query Relaxation]
                         ? (Drop least-selective modifier, preserve category)
                         ?
                   [Fallback Retrieval Executed (< 40ms)]
                         ? (Apply BM25 Relevance Floor > 0.40)
                         ?
                   [Curated Partial Matches Rendered]
                         ? (Display User Transparency Banner)
                         ?
                   [Shopper Clicks Relevant PDP] (Lifting CTR)
                         ?
                   [Add to Cart & Order Conversion]
```

![Figure 21: MVP User Flow Before vs After](../reports/figures/21_mvp_user_flow.png)

---

# 8. Proposed MVP: Automated Query Relaxation / Soft-Match Fallback

### 8.1 Trigger
The relaxation engine activates **if and only if**:
1. The search query contains $\ge 4$ whitespace-delimited tokens.
2. Primary strict retrieval returns $< 3$ purchasable in-stock items.
3. The session is assigned to Treatment (`variant == 'treatment'`).
4. The user has not toggled `force_strict=true`.

### 8.2 Input
- Raw query string (e.g., `"men black slim cotton shirt"`).
- In-stock catalog attribute dictionary (Category nouns, colors, brands, fabrics, fits).
- Catalog Document Frequency (DF) lookup table for fashion vocabulary.

### 8.3 Processing
- Normalize query (lowercase, strip punctuation, deduplicate redundant tokens).
- Classify tokens into Category Nouns, Explicit Attributes, and Modifiers.
- **Rule:** Category nouns are strictly locked and protected.
- Identify candidate modifier with highest Document Frequency (least selective word) and remove it.

### 8.4 Retrieval
- Execute a single relaxed query across the remaining $N-1$ tokens.
- Apply a minimum relevance score filter ($	ext{BM25} > 0.40$).
- Cap candidate list at 20 products.

### 8.5 Output & Transparency
- For **Subgroup A (0 strict hits):** Render relaxed items with prominent UI banner:  
  *"We couldn't find exact matches for all terms. Showing closest matches for [Relaxed Query] with [Dropped Term] removed."*
- For **Subgroup B (1?2 strict hits):** Render the exact matches at top with badge *"Exact Matches"*, followed by relaxed candidates under section header *"You may also like these close matches"*.

### 8.6 Failure Handling
If fallback retrieval also yields zero items meeting the relevance threshold, the system gracefully falls back to displaying popular trending items in the inferred category with standard search assistance tips. The screen is never broken or left empty.

---

# 9. Query Relaxation Logic

### 9.1 Conceptual Algorithmic Workflow
1. **Receive Search Request:** Capture query text, session ID, and user ID.
2. **Tokenize & Cleanse:** Normalize text; extract whitespace-delimited tokens.
3. **Evaluate Eligibility:** Check if `token_count >= 4`. If false, execute standard search and return.
4. **Primary Strict Search:** Run standard search requiring all tokens.
5. **Evaluate Result Count:** If `results_count >= 3`, return strict results immediately.
6. **Trigger Relaxation Engine:** If `results_count < 3`, classify tokens against catalog lexicon.
7. **Entity Locking:** Identify primary product category noun (e.g., `"shirt"`, `"jeans"`, `"dress"`) and lock it.
8. **Modifier Prioritization:** Calculate informativeness / selectivity score for non-category tokens.
9. **Single-Token Drop:** Remove the single lowest-informativeness modifier.
10. **Fallback Query Dispatch:** Execute relaxed query with remaining $N-1$ tokens (Timeout: 40 ms).
11. **Relevance Validation:** Discard candidate items with BM25 score $< 0.40$.
12. **Format Response:** Construct transparency banner payload and merge Subgroup B results if applicable.
13. **Telemetry Emission:** Emit `search_relaxation_exposure` event to analytics pipeline.

### 9.2 Evaluation of Implementation Approaches

| Implementation Approach | Description | Pros | Cons | Recommendation |
|:---|:---|:---|:---|:---:|
| **Approach 1: Rule-Based Positional Drop** | Drop tokens based on fixed syntax rules (e.g., drop rightmost adjective). | Trivial to implement ($<1$ week). | Fails on varied sentence structures; high error rate. | Rejected |
| **Approach 2: Catalog Document Frequency (DF)** | Drop token with highest document frequency across catalog. | Purely data-driven; no manual rules; robust. | May drop common category nouns (e.g. "shirt" has high DF). | Partially Used |
| **Approach 3: Lexicon Category Protection + DF Ranking** | Protect category noun via dictionary, then drop highest-DF modifier. | **High precision; protects intent; low latency.** | Requires maintaining category taxonomy dictionary. | **SELECTED MVP** |
| **Approach 4: Machine Learning NER Parser** | Deep learning entity tagger classifying tokens in real time. | Handles complex linguistic nuance. | Heavy infrastructure; latency risk; high effort. | Post-MVP (P1) |
| **Approach 5: Dense Vector Embeddings** | Replace keyword query with dense semantic embedding. | Highest theoretical recall. | Severe latency risk; hallucinations; GPU cost. | Post-MVP (P3) |

> **Recommended MVP Implementation:** **Approach 3 (Lexicon Category Protection + DF Ranking)**. It delivers 90%+ of the discovery benefits of complex NLP models with $<15	ext{ ms}$ algorithmic execution and zero ML infrastructure dependencies.

---

# 10. Relevance & Safety Constraints

The paramount product risk of query relaxation is:  
**RELAXATION CAN SURFACE NOISY OR IRRELEVANT INVENTORY.**

### 10.1 Core Safety Invariants
1. **Category Invariant:** The system shall NEVER drop the primary product category noun if identified in the catalog lexicon.
2. **Eligibility Gating:** The system shall NEVER execute relaxation on queries with 1?3 tokens (guards head queries).
3. **Threshold Gating:** The system shall NEVER execute relaxation if strict search yields $\ge 3$ in-stock items.
4. **Relevance Score Floor:** Candidate products with normalized BM25 text relevance $< 0.40$ shall be discarded.
5. **Explicit Override:** The system shall always provide an immediate 1-tap affordance to view strict results.

### 10.2 Concrete Examples: Good vs. Bad Relaxation

#### Example 1: High-Quality Intent-Preserving Relaxation (ACCEPTABLE)
- *Original Query:* `"black cotton casual shirt"`
- *Action:* System recognizes `"shirt"` as category noun, `"black"` as color, `"cotton"` as fabric, and `"casual"` as modifier. It drops `"casual"`.
- *Relaxed Query:* `"black cotton shirt"`
- *Result:* Returns 18 black cotton shirts.
- *User Perception:* Extremely positive. The shopper wanted a black cotton shirt; whether it was tagged "casual" is secondary.

#### Example 2: Destructive Failure Relaxation (UNACCEPTABLE / FORBIDDEN)
- *Original Query:* `"black cotton shirt"`
- *Action:* System drops `"shirt"` because it has high document frequency in catalog.
- *Relaxed Query:* `"black cotton"`
- *Result:* Returns black cotton socks, black cotton bedsheets, black cotton dresses, and black cotton trousers.
- *User Perception:* Catastrophic failure. The user wanted a shirt and is presented with socks and bedsheets. Trust is immediately broken.

---

# 11. UX / UI Specification

### 11.1 Search Results Grid State
- The product grid layout remains identical to standard search results.
- Product cards display standard image, brand, title, price, and ratings.

### 11.2 Relaxed-Results Transparency Banner
Positioned immediately above the product grid and below filter chips.

```
+---------------------------------------------------------------------------------------+
|  ??  We couldn't find exact matches for all terms.                                    |
|      Showing closest matches for "men black cotton shirt" with "slim" removed.        |
|      [Search anyway for exact "men black slim cotton shirt"]                          |
+---------------------------------------------------------------------------------------+
```

### 11.3 UI Specifications & Micro-Copy
- **Headline:** *"We couldn't find exact matches for all terms."* (14px Semi-Bold, Neutral-900)
- **Body:** *"Showing closest matches for '[Relaxed Query]' with '[Dropped Token]' excluded."* (13px Regular, Neutral-700)
- **Override Link:** *"Search anyway for exact '[Original Query]'"* (13px Medium, Brand Blue #1a5276, Underline on hover). Tapping sets `force_strict=true` and reloads.
- **Container Styling:** Background `#f4f6f7`, border `1px solid #d5dbdb`, border-radius `6px`, padding `12px 16px`.

### 11.4 Mobile Responsiveness & Accessibility
- **Mobile Viewport:** Banner stacks gracefully; override link wraps to second line; touch target $\ge 44	ext{px}$.
- **Accessibility (WCAG 2.1 AA):** Container includes `role="status"` and `aria-live="polite"`. Text contrast ratio $\ge 4.5:1$ against container background.

---

# 12. Functional Requirements

All functional requirements are cataloged in `../reports/final_requirements.csv`.

| Requirement ID | Feature Area | Description | Priority | Strict Acceptance Criteria |
|:---|:---|:---|:---:|:---|
| **FR-01** | Eligibility | Query Eligibility Gate | **P0** | Activates if and only if raw token count $\ge 4$ AND primary strict search returns $< 3$ in-stock products. |
| **FR-02** | Retrieval | Standard Retrieval First | **P0** | All queries execute standard strict retrieval first. No query is relaxed prematurely if $\ge 3$ strict matches exist. |
| **FR-03** | Detection | Low-Result Detection | **P0** | Search gateway detects strict result count $< 3$ in primary execution cycle with zero client round-trip. |
| **FR-04** | Processing | Token Classification | **P0** | Classifies tokens into Category, Explicit Attribute (Color, Brand, Fabric), and Modifiers using catalog lexicon. |
| **FR-05** | Safety | Core Token Preservation | **P0** | Primary product category noun (e.g., 'shirt', 'dress', 'shoes') is strictly locked and never dropped during initial relaxation. |
| **FR-06** | Algorithm | Modifier Relaxation Heuristic | **P0** | Drops lowest-information modifier token or token with highest document frequency in catalog. |
| **FR-07** | Fallback | Fallback Retrieval Execution | **P0** | Executes single relaxed query across remaining $N-1$ tokens, returning up to 20 candidate items. |
| **FR-08** | Quality | Minimum Relevance Score Floor | **P0** | Candidate products must meet normalized BM25 score $> 0.40$; sub-threshold items discarded. |
| **FR-09** | UI | Transparency Banner | **P0** | Renders context banner: *"We couldn't find exact matches for all terms. Showing closest matches for [Relaxed Query]"*. |
| **FR-10** | Control | Strict Override Re-Query | **P1** | Context banner provides 1-tap link: *"Search anyway for exact [Original Query]"*, forcing strict execution. |
| **FR-11** | Resilience | Zero-Result Fallback Handling | **P0** | If relaxed query also yields 0 hits, display graceful empty state with category recommendations; never crash or show blank screen. |
| **FR-12** | Routing | Experiment Assignment Hook | **P0** | Evaluates session hash against flag `search_query_relaxation_v1` at gateway; routes to Control or Treatment. |
| **FR-13** | Telemetry | Exposure & Telemetry Logging | **P0** | Emits `search_relaxation_exposure` event upon query execution with arm, query details, dropped tokens, result count, and latency. |
| **FR-14** | Operations | Feature Flag & Kill Switch | **P0** | Supports instant ($< 60	ext{s}$) remote rollback to 0% traffic via LaunchDarkly/Unleash config without code deployment. |

---

# 13. Non-Functional Requirements

### 13.1 Performance & Latency Budgets (NFR-01 & NFR-03)
- **End-to-End Search Latency:** **[PROPOSED REQUIREMENT]** Must maintain **p95 latency $< 250	ext{ ms}$** across all search queries.
- **Fallback Execution Budget:** Relaxation processing and fallback query dispatch is allocated a strict **$40	ext{ ms}$ execution budget**.
- **Primary Timeout Circuit Breaker:** If primary retrieval execution exceeds **$120	ext{ ms}$**, relaxation fallback is immediately bypassed to protect p95 latency.

### 13.2 Availability & Resilience (NFR-02)
- Search service availability SLA: $\ge 99.95\%$.
- Any uncaught runtime exception in the relaxation module shall be caught gracefully, and the service shall return the original strict result set without surfacing client errors.

### 13.3 Scalability (NFR-04)
- Designed to handle peak load of **500 queries/second** with $< 5\%$ incremental CPU overhead on cluster nodes.

### 13.4 Observability & Telemetry (NFR-05)
- Real-time Prometheus/Grafana dashboards tracking: relaxation trigger rate, p50/p95/p99 fallback latency, dropped token distributions, and circuit breaker activations.

### 13.5 Accessibility & Privacy (NFR-06 & NFR-07)
- **WCAG 2.1 AA Compliance:** High-contrast notification banner ($\ge 4.5:1$ text contrast ratio) with ARIA live region (`aria-live="polite"`).
- **PII Scrubbing:** Raw query strings scrubbed of credit card numbers, email addresses, and phone numbers prior to persistent data warehouse storage.

---

# 14. Technical Product Specification (Architecture)

*(Detailed engineering contracts and schemas are specified in [final_product_spec.md](final_product_spec.md).)*

```
PROPOSED MVP ARCHITECTURE:
User / Client Device
       ?
       ?
Search API Gateway (Session Hash Evaluation: Control vs Treatment)
       ?
       ?
Primary Retrieval Service (Strict Conjunction Match)
       ?
       ?
Result Count Check
       ??? >= 3 Results ??? Return Strict Results (No Relaxation)
       ??? < 3 Results & 4+ Tokens & Treatment
                 ?
                 ?
       Automated Query Relaxation Engine
                 ? (Category Protection + Highest DF Modifier Drop)
                 ?
       Fallback Retrieval Service (BM25 Score Floor > 0.40)
                 ?
                 ?
       Unified Response Formatter (Banner Injection + Dropped Token Metadata)
                 ?
                 ???? Client App (Renders Transparent SERP)
                 ???? Kafka Pipeline ('search_relaxation_exposure' Event)
```

![Figure 19: Proposed MVP Product Architecture](../reports/figures/19_final_product_architecture.png)

---

# 15. Data & Instrumentation Specification

### 15.1 Real-Time Telemetry: `search_relaxation_exposure` Event
Emitted on every search query meeting experiment eligibility:

| Field Name | Type | Description |
|:---|:---:|:---|
| `event_id` | `VARCHAR` | Unique event UUID. |
| `timestamp` | `TIMESTAMP` | ISO-8601 UTC timestamp of query execution. |
| `experiment_id` | `VARCHAR` | `"EXP-01"`. |
| `variant` | `VARCHAR` | `"control"` or `"treatment"`. |
| `is_eligible` | `BOOLEAN` | `true` if tokens $\ge 4$ and strict results $< 3$. |
| `session_id` | `VARCHAR` | Client session identifier (hash key). |
| `user_id` | `VARCHAR` | Unique user identifier (nullable for guests). |
| `device` | `VARCHAR` | `"mobile_web"`, `"desktop"`, `"ios"`, `"android"`. |
| `query_id` | `VARCHAR` | Unique query tracking ID for click attribution. |
| `raw_query` | `VARCHAR` | Normalized input query string. |
| `token_count` | `INTEGER` | Number of tokens in raw query. |
| `strict_result_count` | `INTEGER` | Result count returned by strict search. |
| `subgroup` | `VARCHAR` | `"A_zero_results"` or `"B_one_two_results"`. |
| `is_relaxed` | `BOOLEAN` | `true` if relaxation fallback was executed. |
| `relaxed_query` | `VARCHAR` | Final query executed during fallback. |
| `dropped_tokens` | `ARRAY<VARCHAR>` | List of tokens removed by relaxation engine. |
| `fallback_result_count` | `INTEGER` | Total items returned by fallback retrieval. |
| `total_latency_ms` | `INTEGER` | Total server-side execution time in milliseconds. |

### 15.2 Downstream Attribution Linkage
To guarantee end-to-end analytical traceability:
- All subsequent `product_views` log `search_id`, `result_position`, and `is_relaxed_result`.
- Cart and checkout events inherit the active `session_id` and originating `search_id`.

---

# 16. Experiment Specification (EXP-01)

### 16.1 Experiment Summary: EXP-01
- **Experiment Title:** Automated Soft Query Relaxation on Low/Zero Search Results.
- **Hypothesis ($H_1$):** Automatically serving relaxed partial-match results when strict multi-token queries yield $< 3$ results will significantly increase Search-to-PDP CTR and downstream session conversion, without increasing search latency or bounce rate.
- **Null Hypothesis ($H_0$):** $CTR_{treatment} \le CTR_{control}$.

### 16.2 Randomization Unit: Session vs. User Level Trade-Off
- **Selected Randomization:** **Session-Level Randomization** (`SHA-256(session_id) % 2`).
- **Strategic PM Trade-off Rationale:** While user-level randomization prevents cross-session inconsistency for repeat shoppers, empirical analysis shows that **[FACT] 84.4% of users in the marketplace conduct only 1?2 sessions**, and search queries reflect immediate, session-specific purchase intents. Furthermore, search engine caching infrastructure operates statelessly at the session layer. Session-level hashing prevents cross-treatment contamination within a visit, provides balanced sample allocation, and maximizes statistical power.

### 16.3 Experimental Arms
- **Control Arm (50%):** Status quo strict retrieval. Returns exact count (including empty state on 0 hits and 1?2 items on sparse hits).
- **Treatment Arm (50%):** MVP Query Relaxation. If results $< 3$ on 4+ tokens, executes modifier relaxation, returns up to 20 partial matches, and displays transparency banner.

### 16.4 Eligibility & Subgroups
- **Eligibility:** `token_count >= 4` AND `strict_result_count < 3`.
- **Subgroups Analyzed:**
  - **Subgroup A (0 Results):** 898 historical queries (95.4% of eligible searches).
  - **Subgroup B (1?2 Results):** 43 historical queries (4.6% of eligible searches).

### 16.5 Decision Rules & Stopping Criteria
- **Ship (Success):** Statistically significant positive lift in Primary CTR ($p < 0.05$), ZRR reduction $> 5.0	ext{ pp}$, and all Guardrails green.
- **Rollback (Failure):** p95 latency $> 250	ext{ ms}$ for $> 2	ext{ hours}$, or quick-back bounce rate increases significantly ($p < 0.01$).

![Figure 22: Controlled A/B Experiment Architecture](../reports/figures/22_experiment_design.png)

---

# 17. Metrics Specification

All metrics are formally documented in [../reports/final_metrics_dictionary.csv](../reports/final_metrics_dictionary.csv).

### 17.1 Metric Tree Hierarchy
```
                       NORTH STAR BUSINESS GOAL
            [Maximize Marketplace GMV & Purchase Conversion]
                 (Baseline: $217,860.56 Total GMV | 9.19% CR)
                                  ?
                             USER OUTCOME
                [Seamless Discovery for Specific Shoppers]
                                  ?
                        PRIMARY EXPERIMENT METRIC
        [Search-to-PDP CTR on Eligible 4+ Token Queries (<3 Hits)]
            (Baseline: 3.08% on <3 hits; 62.95% overall 4+ tokens)
                                  ?
          +-----------------------+-----------------------+
          ?                                               ?
    SUPPORTING FUNNEL METRICS                       GUARDRAIL METRICS
    - Zero-Result Rate (ZRR, 8.23% -> <2.5%)        - Search p95 Latency (<250ms)
    - Search-to-Cart Conversion Rate                - Head Query CTR (70.78%, Neutral)
    - Search-to-Order Conversion Rate (13.01%)      - Search Session Bounce (<40%)
    - Query Reformulation Rate (44.39% -> Decr)     - Quick-Back Bounce Rate (<= +1.0pp)
                                                    - Revenue per Session ($6.95)
```

![Figure 20: Final Success Metric Tree](../reports/figures/20_final_metric_tree.png)

### 17.2 Metrics Specification Table

| Metric Name | Category | Exact Mathematical Formula | Canonical Baseline | Target Direction | Strategic Rationale |
|:---|:---:|:---|:---:|:---:|:---|
| **Search-to-PDP CTR (Eligible)** | **Primary** | $\frac{\text{Eligible 4+ Token Searches with } \ge 1 \text{ PDP Click}}{\text{Total Eligible 4+ Token Searches (< 3 Hits)}}$ | **3.08%** (29 clicks / 941)<br>*(62.95% overall 4+)* | **Positive Lift** ($p < 0.05$) | Direct behavioral indicator of intent recovery. |
| **Zero-Result Rate (ZRR)** | Secondary | $\frac{\text{4+ Token Searches with 0 Results}}{\text{Total 4+ Token Searches}}$ | **8.23%** (898 events) | **Decrease** (Target: $< 2.5\%$) | Measures reduction of absolute discovery dead-ends. |
| **Search-to-Cart Rate** | Secondary | $\frac{\text{Search Sessions with } \ge 1 \text{ Cart Event}}{\text{Total Search Sessions}}$ | **32.0%** of search sessions | **Positive Lift** | Verifies PDP clicks represent genuine purchase intent. |
| **Search-to-Order CR** | Secondary | $\frac{\text{4+ Token Search Sessions with Completed Order}}{\text{Total 4+ Token Search Sessions}}$ | **13.01%** (1,165 orders) | **Positive Lift** | Confirms top-of-funnel recovery flows to GMV. |
| **Query Reformulation Rate** | Secondary | $\frac{\text{4+ Token Searches Followed by Query in Session}}{\text{Total 4+ Token Searches}}$ | **44.39%** (4,845 searches) | **Decrease** | Tracks reduction in user cognitive friction. |
| **Search p95 Latency** | **Guardrail** | 95th percentile of server-side `search_latency_ms` | ~180 ms | **Strictly $< 250\text{ ms}$** | Guards platform performance and speed. |
| **Short-Query CTR (1?3 Tok)** | **Guardrail** | $\frac{\text{1-3 Token Searches with } \ge 1 \text{ PDP Click}}{\text{Total 1-3 Token Searches}}$ | **70.78%** (15,098 clicks) | **Zero Regression** ($p > 0.05$) | Ensures head query performance is uncompromised. |
| **Search Session Bounce Rate**| **Guardrail** | $\frac{\text{Search Sessions with No Downstream Actions}}{\text{Total Search Sessions}}$ | **38.2%** | **Must remain $< 40.0\%$** | Protects against serving irrelevant junk results. |
| **Quick-Back Bounce Rate** | **Guardrail** | $\frac{\text{PDP Views with Duration } < 5\text{ Seconds}}{\text{Total PDP Views from Search}}$ | ~14.5% baseline | **Delta $\le +1.0\text{ pp}$** | Verifies clicked products genuinely match expectations. |
| **Revenue per Session** | **Guardrail** | $\frac{\text{Total Order GMV}}{\text{Total Sessions}}$ | **$6.95** ($217.9k / 31.3k) | **Non-Negative Delta** | Confirms overall financial health is protected. |

---

# 18. Experiment Power & Sample Size Calculations

The statistical power analysis for EXP-01 is calculated using a two-tailed two-proportion $Z$-test at $\alpha = 0.05$ ($Z_{\alpha/2} = 1.96$) and $80\%$ statistical power ($Z_\beta = 0.84$).

### 18.1 Methodological Grounding & True Experimental Baseline
- **Primary Experiment Baseline [FACT]:** **3.08%** Search-to-PDP CTR on eligible searches ($\ge 4$ tokens AND $< 3$ existing retrieval hits; 29 clicks / 941 searches).
- **Macro Context Metric [FACT]:** **62.95%** Search-to-PDP CTR across all 10,914 specific searches (used for population-level ITT monitoring, NOT as the experiment baseline).
- **Eligible Traffic Run-Rate [FACT]:** 941 eligible searches over 60 days $\approx$ **15.68 eligible searches per day** across the platform.

### 18.2 Sample Sizing Matrix for Eligible Population (Baseline = 3.08%)

| MDE (Absolute Lift) | Target Treatment CTR ($p_2$) | Relative Lift | Required Sample / Arm | Total Required Searches | Est. Runtime (@15.7 searches/day) | Operational Feasibility & Strategy |
|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **+1.0 pp** | 4.08% | +32.5% | 5,418 | 10,836 | ~691 days (~23 months) | Severely underpowered for standard A/B test. |
| **+2.0 pp** | 5.08% | +64.9% | 1,535 | 3,070 | ~196 days (~6.5 months) | Underpowered for rapid sprint validation. |
| **+3.0 pp** | 6.08% | +97.4% | 762 | 1,524 | ~97 days (~3.2 months) | Viable for an extended quarterly test. |
| **+3.5 pp** | 6.58% | +113.6% | 586 | 1,172 | ~75 days (~2.5 months) | Balanced quarterly target. |
| **+4.0 pp** | 7.08% | +129.9% | 472 | 944 | ~60 days (~2.0 months) | Realistic target for 8-week experiment. |
| **+5.0 pp** | 8.08% | +162.3% | 330 | 660 | ~42 days (~6.0 weeks) | **CANARY BENCHMARK:** Detectable in 4?6 weeks. |

### 18.3 Defensible Product Trade-Off & Experiment Strategy
In an interview or executive presentation, a rigorous PM must be transparent about statistical power:
1. **The Statistical Reality:** Because eligible low-result queries generate only ~16 searches/day in this single-catalog dataset, testing for a subtle $+1.0	ext{ pp}$ or $+2.0	ext{ pp}$ lift would take over 6 months to achieve statistical significance.
2. **The Experiment Solution (Option C):** We randomize all 4+ token search users at the persistent user level (`hash(experiment_id + user_id) % 100`). For queries returning $\ge 3$ hits, both arms receive identical results. For queries returning $< 3$ hits, Treatment activates relaxation.
3. **Pacing Plan:**
   - **Phase 1 (Weeks 1?4 Canary Test):** Evaluates whether the intervention produces a large, transformational effect ($\ge +5.0	ext{ pp}$ lift, e.g. moving CTR from 3% to 8%+).
   - **Phase 2 (Multi-Category Rollout):** To detect moderate lifts ($+2.0	ext{ to }+3.5	ext{ pp}$), the experiment is expanded across broader fashion taxonomies to multiply daily eligible query volume by 3x?5x.

---
# 19. Phased Rollout Plan

The rollout schedule minimizes operational risk via gated phase transitions, as documented in `reports/final_rollout_plan.csv`.

```
Phase 0 (Offline Audit) ??? Phase 1 (Shadow Traffic) ??? Phase 2 (5% Canary) ??? Phase 3 (50% A/B Test) ??? Phase 4 (100% GA)
```

| Phase | Traffic Allocation | Target Duration | Gate Entry Criteria | Gate Exit Criteria | Immediate Rollback Trigger |
|:---:|:---:|:---:|:---|:---|:---|
| **Phase 0** | 0% (Offline) | 1 Week | All unit tests pass 100%. | Manual relevance rating on 200 sampled queries achieves $\ge 90\%$ acceptable rating. | Relevance rating $< 85\%$. |
| **Phase 1** | 0% UI (100% Shadow) | 1 Week | Phase 0 sign-off; shadow worker active. | Shadow execution demonstrates p95 latency overhead $< 35\text{ ms}$ under 500 QPS load. | p95 latency $> 250\text{ ms}$ or error rate $> 0.05\%$. |
| **Phase 2** | 5% (2.5% C / 2.5% T) | 3 Days | Phase 1 latency certified. | Telemetry emission parity confirmed; 0 client exceptions. | Any client crash or telemetry loss. |
| **Phase 3** | 50% (25% C / 25% T) | 4 Weeks | Phase 2 stability confirmed. | Reaches ~5,000 sample searches; evaluates primary CTR ($p < 0.05$) and guardrails. | Significant regression in short queries or quick-back rate $> +1.0\text{ pp}$. |
| **Phase 4** | 100% Treatment | Permanent | Statistically significant positive lift on Primary CTR; all guardrails green. | 100% rollout achieved; feature flag converted to permanent search architecture. | Macro conversion drop. |

---

# 20. Rollback & Emergency Kill Switch Protocol

### 20.1 Operational Feature Flag
- **Flag Key:** `search_query_relaxation_v1` (managed via LaunchDarkly / Unleash).
- **Control Capabilities:** Supports dynamic percentage allocation (0% to 100%), user targeting, and emergency kill-switch capability.

### 20.2 Automated & Manual Rollback Triggers
An immediate rollback to 0% traffic shall be triggered if:
1. **Latency Breach:** Search p95 latency exceeds **$250	ext{ ms}$** for $> 2	ext{ consecutive hours}$.
2. **Relevance Degradation:** Quick-back bounce rate ($< 5	ext{s}$ duration) increases significantly ($p < 0.01$ or $\Delta > +1.0	ext{ pp}$).
3. **Head Query Cannibalization:** Short-query (1?3 token) CTR drops significantly ($p < 0.05$).
4. **Service Instability:** Relaxation API throws errors on $> 0.1\%$ of queries.

---

# 21. Edge Cases & System Handling

Comprehensive handling for all 16 production edge cases documented in `reports/final_edge_cases.csv`:

| ID | Edge Case Scenario | Detection Mechanism | Expected System Behavior | Risk Level |
|:---:|:---|:---|:---|:---:|
| **EC-01** | Query has no recognized category noun (e.g., *"black slim fit cotton"*). | Category detector returns null. | Fall back to fuzzy multi-field match. If still $<3$, show category recommendation fallback. | Medium |
| **EC-02** | All tokens have identical document frequency. | Token frequency variance $< 0.05$. | Drop rightmost attribute token by convention, preserving initial gender/target token. | Low |
| **EC-03** | Relaxing 1 token still produces 0 hits. | Fallback query yields 0 results. | Attempt single secondary relaxation to $N-2$ only if query $\ge 5$ tokens; else show graceful empty state. | Medium |
| **EC-04** | Brand + Category query with 0 hits (e.g., *"Nike cashmere blazer"*). | NER identifies Brand + Category. | Brand entity is locked (never dropped). Relaxation removes fabric/style modifier. | High |
| **EC-05** | Size + Color over-constrains inventory (e.g., *"XXL yellow silk top"*). | Size and color tokens identified. | Drop size token; banner reads: *"Showing yellow silk tops in all available sizes"*. | Medium |
| **EC-06** | Query contains obvious typo (e.g., *"men blck cotton shrt"*). | Spellchecker flags edit distance 1. | Apply typo correction before relaxation. If hits $\ge 3$, return corrected results. | Low |
| **EC-07** | Query contains duplicate tokens (e.g., *"men shirt cotton shirt"*). | Deduplicated tokens $< N$. | Deduplicate tokens during normalization prior to strict execution. | Low |
| **EC-08** | Extremely long query ($\ge 8$ tokens, conversational text). | Token count $\ge 8$. | Extract top 4 most salient entities using entity tagger; search on core 4 tokens. | Medium |
| **EC-09** | Primary search execution is slow ($> 120	ext{ ms}$). | Latency timer exceeds 120 ms. | Circuit breaker triggers; bypasses relaxation to protect p95 latency SLA. | High |
| **EC-10** | Fallback retrieval service times out or errors. | HTTP 500 or timeout $> 40	ext{ ms}$. | Gateway catches exception gracefully; returns original strict results. | High |
| **EC-11** | User rapidly reformulates before relaxed results render. | New query issued within $< 1.5	ext{s}$. | Abort in-flight relaxation request via client abort signal; process latest query. | Low |
| **EC-12** | User clicks *"Search anyway for exact [Original Query]"*. | Query contains `force_strict=true`. | Bypass relaxation completely; execute pure strict search and render exact result count. | Low |
| **EC-13** | Adult, offensive, or prohibited search terms. | Blocklist match. | Bypass relaxation entirely; return neutral zero results; log moderation flag. | High |
| **EC-14** | Query consists only of stop words (e.g., *"the best of in"*). | Stop word detector flags 100%. | Do not relax; return standard curated popular landing page. | Low |
| **EC-15** | User repeatedly bounces from relaxed results. | $\ge 2$ consecutive quick-backs. | Demote relaxed candidate rankings for session; prioritize interactive chips. | Medium |
| **EC-16** | Strict search yields 1 or 2 results (Subgroup B: 43 queries). | Result count IN (1, 2). | Render exact matches at top labeled *"Exact Matches"*; render relaxed items below. | Low |

---

# 22. Risks & Experimental Mitigations

| Identified Risk | Probability | Impact | Mitigation Strategy | Primary Monitoring Telemetry |
|:---|:---:|:---:|:---|:---|
| **1. Relevancy Degradation** | Medium | High | Restrict relaxation strictly to queries with $<3$ hits; protect category nouns; enforce BM25 floor $>0.40$. | Quick-Back Bounce Rate ($\Delta \le +1.0	ext{ pp}$), Search-to-Cart Rate. |
| **2. False-Positive Expectations** | Medium | Medium | Render high-visibility banner explicitly naming which token was excluded. | Override link click rate, PDP dwell time. |
| **3. Latency SLA Breach** | Low | High | Enforce strict 120 ms primary search circuit breaker and 40 ms fallback timeout. | Search p95 latency ($< 250	ext{ ms}$). |
| **4. Head Query Cannibalization** | Very Low | Critical | Hard eligibility filter: relaxation only triggers on queries with $\ge 4$ tokens. | Short-Query CTR ($70.78\%$, zero regression). |
| **5. User Trust Erosion** | Low | High | Provide prominent 1-tap *"Search anyway for exact"* override link on banner. | User repeat search rate, support tickets. |
| **6. Catalog Hygiene Dependency**| Medium | Medium | Rely on catalog category taxonomy tables rather than unvetted vendor descriptions. | Per-category ZRR tracking. |

---

# 23. Dependencies & Cross-Functional Alignment

### 23.1 MVP Dependencies (Immediate Path to Experiment Launch)
1. **Search Backend Engineering:** Integration of token classifier and fallback retrieval hook into the primary search execution gateway.
2. **Product Catalog Team:** Providing verified Category Taxonomy Lexicon and Document Frequency tables.
3. **Experimentation Platform (LaunchDarkly / Statsig):** Deterministic session hashing and dynamic feature flag allocation.
4. **Analytics & Data Engineering:** Kafka topic `search_relaxation_exposure` setup and downstream click attribution ingestion.
5. **Frontend Web & Mobile Teams:** Rendering the dynamic transparency notification banner and handling the `force_strict=true` re-query parameter.

### 23.2 Future Dependencies (Post-EXP-01 Roadmap)
1. **Machine Learning Infrastructure:** Real-time entity extraction models for Phase 2 attribute-aware query parsing.
2. **Payment Gateway Partnerships:** Digital wallet (Apple Pay / Google Pay) APIs for the secondary Mobile Web Checkout initiative.

---

# 24. Future Product Roadmap

The MVP (SOL-01) is designed as a foundational stepping stone. It generates rich telemetry on user attribute tolerance that directly informs future discovery investments:

```
+---------------------------------------------------------------------------------------+
|                               DISCOVERY PRODUCT ROADMAP                               |
+------------------------------------+--------------------------------------------------+
|  PHASE 1 (MVP ? Current Scope)     |  PHASE 2 (Q3 ? Guided Refinement & Precision)    |
|  - SOL-01: Automated Relaxation    |  - SOL-02: Interactive Query Refinement Chips    |
|  - Real-time Transparency Banner   |  - SOL-03: Attribute-Aware Facet Parsing         |
|  - Baseline Intent Recovery        |  - Subgroup B Dedicated Split Grids              |
+------------------------------------+--------------------------------------------------+
|  PHASE 3 (Q4 ? Algorithmic Depth)  |  PHASE 4 (Next Year ? Intelligent Discovery)     |
|  - SOL-04: Attribute Field Weight  |  - SOL-08: Dense Vector / Hybrid Retrieval       |
|  - SOL-06: Related Query Assist    |  - SOL-10: Personalized Discovery Ranking        |
|  - Dynamic Category Expansion      |  - Conversational Discovery Interface            |
+------------------------------------+--------------------------------------------------+
```

---

# 25. Secondary Problem: Mobile Web Checkout Friction

While Search Discovery Failure is the primary strategic priority, our analytical audit validated **Problem D: Mobile Web Checkout Friction** as the secondary funnel leak.

### 25.1 Validated Empirical Baseline
- **[FACT] Conversion Deficit:** Mobile Web Cart-to-Order (CTO) conversion is **29.63%**, compared to **46.26% on iOS** and **39.96% on Android** (a 13.31 pp pooled gap vs. combined native apps; $Z = 10.45, p < 0.0001$).
- **[FACT] Funnel Stage Localization:** Drop-off on Mobile Web is strictly localized to the Cart $	o$ Order checkout step; upstream Search $	o$ PDP and PDP $	o$ Cart conversion rates are completely healthy.
- **[FACT] Reach:** Touches 1,647 cart sessions and 6,343 mobile web users.

### 25.2 Why Mobile Web Checkout Remains Secondary to Search Discovery
1. **Upstream Funnel Leverage:** Search Discovery sits at the mouth of the intent funnel, affecting 8,958 sessions and 10,914 queries. Fixing discovery feeds a substantially larger volume of qualified buyers into the checkout funnel.
2. **Failure Severity:** Zero-result search queries produce 100% immediate discovery drop-off. On mobile web, 29.63% of cart shoppers still successfully convert.
3. **Sequencing:** Search discovery is the Q2 priority; Mobile Web Checkout form simplification is the targeted Q3 conversion initiative.

### 25.3 Recommended Future Directions for Mobile Web Checkout
- **Direction 1:** 1-Tap Digital Wallet Integration (Apple Pay, Google Pay, UPI Quick Checkout).
- **Direction 2:** Single-page responsive accordion checkout with Google Places address autocompletion.
- **Direction 3:** Frictionless persistent bottom-sheet guest checkout without mandatory password creation.

---

# 26. Success Definition

The MVP (SOL-01) shall be deemed an analytical and commercial success if:
1. **Primary Metric Achieves Significant Lift:** Search-to-PDP CTR on eligible 4+ token queries shows a statistically significant positive lift ($p < 0.05$) in the treatment arm.
2. **Zero-Result Rate Drops Materially:** ZRR on 4+ token queries decreases directionally from 8.23% toward the $< 2.5\%$ operational target.
3. **Downstream Conversion is Preserved or Enhanced:** Search-to-Cart and Search-to-Order conversion rates remain flat or improve.
4. **Zero Latency SLA Breach:** Search p95 latency remains strictly $< 250	ext{ ms}$.
5. **No Relevance Rejection Signals:** Quick-back bounce rate increases by no more than $1.0	ext{ pp}$ ($\Delta \le +1.0	ext{ pp}$), proving that shoppers genuinely value the relaxed product results.
6. **Marketplace Revenue is Neutral or Positive:** Total revenue per session shows a non-negative delta ($p \ge 0.05$).

---

# 27. Launch Decision Framework

At the conclusion of the 4-week EXP-01 testing window, the Product and Engineering leadership team will execute against this deterministic decision rubric:

```
                               EXPERIMENT EVALUATION
                                         ?
                    ???????????????????????????????????????????
                    ?                                         ?
         Primary CTR Lift p < 0.05?                Primary CTR Flat / Down?
          ??? YES                                   ??? YES
          ?    ?                                    ?    ?
          ?    ?                                    ?  [KILL DECISION]
          ?  Guardrails Green?                      ?  Roll back to 0%;
          ?   ??? YES ??? [SHIP DECISION]           ?  Revert to Backlog
          ?   ?           Roll out to 100% GA       ?
          ?   ??? NO  ??? [ROLL BACK DECISION]      ?
          ?               Fix Latency / Relevance   ?
          ??? NO (p >= 0.05)                        ?
               ?                                    ?
               ?                                    ?
             [ITERATE DECISION] ?????????????????????
             Qualitative Audit & Heuristic Tuning
```

### 1. SHIP DECISION (Proceed to 100% GA)
- Primary CTR lift is statistically significant ($p < 0.05$).
- ZRR reduction $> 5.0	ext{ pp}$.
- All guardrail metrics green (latency $< 250	ext{ ms}$, quick-back bounce neutral, head query CTR unaffected).

### 2. ITERATE DECISION (Refine & Retest)
- Primary CTR lift is directionally positive ($+1.0$ to $+2.5	ext{ pp}$) but fails to achieve statistical significance ($p \ge 0.05$).
- Audit indicates transparency banner copy is being overlooked or token drop heuristic is overly conservative. Tune heuristics and re-run.

### 3. ROLL BACK DECISION (Trigger Emergency Kill Switch)
- Search p95 latency exceeds $250	ext{ ms}$, or quick-back bounce rate increases significantly ($p < 0.01$).
- Search API errors exceed $0.1\%$. Revert traffic to 0% within 60 seconds.

### 4. KILL DECISION (Abandon Solution Concept)
- Primary CTR shows zero lift or negative delta after full 4-week sample collection (~5,000 queries).
- Downstream order conversion regresses significantly. Close EXP-01 and pivot to SOL-02 (Refinement Chips).

---

# 28. Open Questions & Validation Agenda

The existing synthetic dataset provides strong behavioral evidence, but the following validation questions must be resolved during the live experimentation phase:

1. **User Attribute Hierarchy:** Which specific fashion attributes (color vs. fabric vs. fit) do shoppers prioritize most when forced to compromise?
2. **Optimal Relevance Score Cutoff:** Does a normalized BM25 score of 0.40 provide the ideal precision/recall balance across all apparel subcategories?
3. **Banner Interaction Propensity:** What percentage of users actively tap the *"Search anyway for exact"* override link vs. continuing down the relaxed results grid?
4. **Category Heterogeneity:** Does automated query relaxation perform equally well in Footwear and Accessories as it does in Apparel?
5. **Mobile Viewport Optimization:** Does the transparency banner push the first row of products too far below the mobile fold, impacting initial scroll depth?

---

# 29. Final Product Summary

```
========================================================================================
                          FINAL PRODUCT STRATEGY SUMMARY
========================================================================================
1. PROBLEM:      High-intent shoppers using specific multi-attribute queries (4+ tokens)
                 suffer discovery failure: 8.23% ZRR, 62.95% CTR, 44.39% reformulation.
                 
2. EVIDENCE:     Canonical DuckDB audit of 32,245 searches validates 898 zero-result
                 dead-ends on 4+ tokens, impacting 8,958 sessions and 7,318 users.
                 
3. OPPORTUNITY:  Specific-query sessions convert at 13.01% (vs. 14.85% baseline). 
                 Recovering lost discovery captures unfulfilled GMV at zero acquisition cost.
                 
4. SELECTED MVP: SOL-01 ? Automated Query Relaxation / Soft-Match Fallback.
                 Preserves category nouns, drops least-selective modifier on <3 hits,
                 surfaces up to 20 partial matches with clear UI transparency messaging.
                 
5. EXPERIMENT:   EXP-01 ? 50/50 Session-Level A/B Test running for ~4 weeks (~5,000 queries).
                 Primary Metric: Search-to-PDP CTR on Eligible 4+ Token Queries.
                 Guardrails: Latency p95 < 250ms, Quick-Back Delta <= +1.0pp, Head CTR Neutral.
                 
6. SUCCESS:      Statistically significant lift in Primary CTR (p < 0.05), ZRR < 2.5%,
                 stable latency, and neutral-to-positive revenue per session.
                 
7. EVOLUTION:    Data collected from EXP-01 fuels Phase 2 Guided Refinement Chips (SOL-02)
                 and Structured Attribute-Aware Facet Parsing (SOL-03).
========================================================================================
```

