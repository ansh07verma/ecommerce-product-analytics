# E-Commerce Search Discovery Optimization: Product Analytics & Experimentation Case Study

**Product Area**: Search Discovery & Conversion Funnel  
**Intervention**: Automated Query Relaxation / Soft-Match Fallback Engine (V1 MVP)  
**Author**: Product Management & Product Analytics Case Study  
**Artifact Status**: PORTFOLIO READY & INTERVIEW DEFENDED  
**Data Environment**: Relational DuckDB Store (119,390 events, 32,245 searches, 1,600 SKUs)  

---

## 1. Executive Summary

This case study analyzes search discovery failure across an apparel marketplace dataset of 32,245 searches, 31,328 sessions, and 16,000 customers. Exploratory funnel analysis revealed an acute failure mode: while general head queries (1–3 tokens) fail at a low 1.78% zero-result rate (ZRR), specific multi-attribute searches ($\ge 4$ tokens) suffer an **8.23% historical zero-result rate** [OBSERVED], driving a **44.39% manual reformulation rate** [OBSERVED] and depressing Search $\to$ PDP Click-Through Rate (CTR) to **3.08%** [OBSERVED]. Customers are not abandoning search because products are absent; they are failing because strict conjunctive boolean search breaks down when users over-specify attributes (color, fabric, occasion, style).

To resolve this without expensive infrastructure, we evaluated six search technologies (Query Relaxation, Autocomplete, Synonym Graphs, Fuzzy Matching, Vector Search, and Conversational LLMs). We prioritized **Automated Query Relaxation** as the V1 intervention due to direct root-cause fit, sub-millisecond execution, deterministic explainability, and zero recurring cloud inference overhead. On local benchmarks across 879 unmatchable queries, our relaxation engine achieved a **91.81% algorithmic recovery rate** [LOCAL BENCHMARK], reducing strict ZRR from 98.21% down to 8.40% (-80.70 pp reduction) within a 38.53 ms P95 latency envelope (well within the $\le 50$ ms algorithmic budget and $\le 250$ ms end-to-end SLA).

To evaluate production readiness, we built an offline A/B experiment simulator (user-level 50/50 hashing, two-proportion z-test) and a deterministic business impact model. Our model demonstrates that achieving our target +3.5 pp CTR lift yields **+$1,808.69 in gross annualized GMV** (or **+$1,356.52 net** at 25% cannibalization) [MODELED]. Crucially, our capital discipline analysis reveals that standalone return on current traffic (~15.7 searches/day) does not justify expensive dedicated infrastructure. However, because query relaxation has zero marginal query cost, an illustrative 100x traffic scenario yields **+$180.9K/year** with zero marginal development cost. 

**Final PM Recommendation**: Do not commit to costly infrastructure upfront. Validate customer purchase willingness by running a lightweight 50/50 live canary experiment. Ship if CTR lift $\ge +1.5\text{ pp}$ ($p < 0.05$); deprioritize if lift is statistically inconclusive or creates downstream quick-backs.

---

## 2. Problem: Discovery Failure on Specific Searches

In e-commerce fashion marketplaces, high-intent shoppers frequently express precise intent using natural, descriptive language:
> e.g., `"women red silk evening dress"`, `"black leather waterproof ankle boots"`

When evaluated against traditional boolean keyword engines requiring all tokens to match, these searches produce catastrophic discovery failure.

### Verified Baseline Funnel Metrics

| Metric | Empirical Value | Provenance | Significance |
| :--- | :---: | :---: | :--- |
| **Total Catalog Searches** | 32,245 | `[OBSERVED]` | Full 60-day marketplace search volume |
| **4+ Token Search Share** | 33.85% (10,914 events) | `[OBSERVED]` | High-intent, specific fashion searches |
| **Eligible Specific Searches** | **941 events** (~15.7/day) | `[OBSERVED]` | $\ge 4$ tokens AND $< 3$ strict results |
| — *Subgroup A (Zero-Result)* | 898 events | `[OBSERVED]` | Complete dead-end search screens |
| — *Subgroup B (Low-Result 1-2)*| 43 events | `[OBSERVED]` | Severe catalog constraint |
| **Historical 4+ Token ZRR** | **8.23%** (898 / 10,914) | `[OBSERVED]` | 4.6x higher failure rate than head terms |
| **Historical 1–3 Token ZRR** | **1.78%** (380 / 21,331) | `[OBSERVED]` | Baseline head & torso query health |
| **Manual Reformulation Rate** | **44.39%** (4,845 / 10,914) | `[OBSERVED]` | User re-types query in frustration |
| **Eligible Search $\to$ PDP CTR** | **3.08%** (29 clicks / 941) | `[OBSERVED]` | Immediate discovery conversion collapse |
| **Eligible Funnel Orders** | 2 completed orders | `[OBSERVED]` | $285.15 historical GMV on eligible cohort |

### Why This Is a Product Problem, Not Just a Search-Engine Problem
Search engine engineering measures precision and recall metrics. Product management measures **customer intent friction, discovery momentum, and revenue leak**:
1. **Highest-Intent Segment**: Shoppers typing 4+ words know exactly what they want. Search-engaged sessions convert at **11.92% vs. 4.75% for browse shoppers** [OBSERVED] (a 2.51x conversion advantage).
2. **Punishing Specificity**: When the search bar acts as a rigid filter rather than a discovery concierge, we punish users for expressing clear intent.
3. **Friction & Abandonment**: A 44.39% reformulation rate proves customers are actively working around the tool. When reformulation also fails, high-value shoppers churn to competing platforms.

---

## 3. User / Customer Journey

### The Discovery Friction Narrative

```text
User has a specific intent
(e.g., "women red silk evening dress")
         │
         ▼
Types detailed multi-attribute query
         │
         ▼
Strict boolean search fails (0 or 1 result)
Catalog has red evening dresses, but fabric is polyester
         │
         ▼
User faces dead-end screen: "No products found"
         │
         ▼
User forced to reformulate (44.39% rate) or abandons session
         │
         ▼
Product discovery opportunity and high-intent GMV is lost
```

### The Product Opportunity
> *"Instead of forcing users to learn the catalog's vocabulary, the search experience should preserve intent while safely relaxing overly restrictive modifiers."*

If the customer searches for `"women red silk evening dress"`, the primary purchase intent is a **red evening dress for women**. Relaxing the fabric constraint (`silk`) allows the system to present stunning red evening dresses with transparent labeling: *"Showing results for women red evening dress (relaxed: silk)"*.

---

## 4. Root-Cause Analysis

To avoid implementing generic solutions for unverified problems, we diagnosed all marketplace search failures using the Stage 5 Failure Taxonomy:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    SEARCH FAILURE TAXONOMY (STAGE 5)                         │
├────────────────────────────────┬───────────────┬─────────────────────────────┤
│ Failure Mode                   │ Share of ZRR  │ Target V1 Solution?         │
├────────────────────────────────┼───────────────┼─────────────────────────────┤
│ 1. Over-Specification          │ 65%           │ YES — Primary V1 Target     │
│ 2. Vocabulary Mismatch         │ 20%           │ NO  — Roadmap V1.2 (Synonym)│
│ 3. Typographical Errors        │ 10%           │ NO  — Roadmap V1.3 (Fuzzy)  │
│ 4. Conversational / Subjective │ 5%            │ NO  — Roadmap V3.0 (LLM)    │
└────────────────────────────────┴───────────────┴─────────────────────────────┘
```

### Diagnosed Failure Breakdown
1. **Over-Specification (Primary V1 Focus)**: Shoppers combine valid attributes (Gender + Color + Fabric + Category + Occasion) where all attributes exist in the store, but no single SKU satisfies all simultaneously.
2. **Vocabulary Mismatch**: Regional or colloquial terminology (e.g., `"frock"` vs. `"dress"`, `"jumper"` vs. `"sweater"`).
3. **Typographical Errors**: Spelling mistakes (e.g., `"denim jakcet"`).
4. **Conversational Queries**: Subjective statements (e.g., `"what should I wear to a fall wedding"`).

**Product Scoping Boundary**: The V1 Automated Query Relaxation engine **intentionally targets Over-Specification only**. It does not attempt to solve typos or conversational reasoning.

---

## 5. Solution: Automated Query Relaxation

Automated Query Relaxation runs strict boolean search first, triggering fallback logic *only* when search discovery breaks down.

```
[ Shopper Query: "women red silk evening dress" ]
                       │
                       ▼
         ┌───────────────────────────┐
         │ Strict Search Execution   │ ──( >=3 results )──► Return Direct Matches
         └─────────────┬─────────────┘
                       │ (< 3 results & >= 4 tokens)
                       ▼
         ┌───────────────────────────┐
         │ Token Classification      │ ──► Protect Category Nouns ("dress")
         └─────────────┬─────────────┘
                       ▼
         ┌───────────────────────────┐
         │ Candidate Generation      │ ──► Generate 1-drop & 2-drop subsets
         └─────────────┬─────────────┘
                       ▼
         ┌───────────────────────────┐
         │ Scoring & Ranking         │ ──► Score by token rarity (IDF) & catalog density
         └─────────────┬─────────────┘
                       ▼
         ┌───────────────────────────┐
         │ Guardrail Verification    │ ──► Category check, stock > 0, >=50% overlap
         └─────────────┬─────────────┘
                       ▼
[ Render Explainable Fallback UI: "Showing 8 results for red dress (relaxed: silk, evening)" ]
```

### Algorithmic Execution Pipeline
1. **Trigger Condition**: Query must contain $\ge 4$ meaningful tokens AND return $< 3$ strict results.
2. **Modifier Identification & Category Protection**: Catalog taxonomy categorizes tokens. Category nouns (e.g., `"dress"`, `"boots"`, `"jeans"`) are marked protected and can **never** be dropped. Modifiers (colors, fabrics, occasions) are marked eligible for relaxation.
3. **Candidate Generation**: System systematically generates 1-drop subsets (dropping 1 modifier) and 2-drop subsets.
4. **Scoring & Ranking**: Candidates are scored by Inverse Document Frequency (IDF) rarity and catalog yield, prioritizing dropping the most restrictive non-core modifier first.
5. **Relevance & Safety Guardrails**:
   - **Category Guardrail**: Fallback results must strictly match the original category.
   - **Inventory Guardrail**: Products with zero stock (`inventory_units <= 0`) are excluded.
   - **Minimum Token Overlap**: Relaxed query must retain $\ge 50\%$ of original tokens (or $\ge 2$ tokens).
6. **Explainable UI Transparency**: The UI never silently swaps results. It renders: *"Showing 8 results for 'women red dress' (relaxed: silk, evening)"*.

### Local Algorithmic Benchmark Performance
Evaluated against 1,000 historical catalog queries using `LocalSearchEngine` on the active catalog:
- **Eligible Benchmark Queries**: 879 queries returned $< 3$ results under strict search.
- **Successful Fallback Recoveries**: **807 queries recovered** (**91.81% recovery rate** [LOCAL BENCHMARK]).
- **Zero-Result Rate Reduction**: Slashed strict ZRR from **98.21% down to 8.40%** (-80.70 pp reduction) [LOCAL BENCHMARK].
- **Latency Budget Compliance**: Mean latency was **2.08 ms** strict and **38.53 ms P95** relaxed [LOCAL BENCHMARK], well within our $\le 50\text{ ms}$ algorithmic relaxation budget and $\le 250\text{ ms}$ end-to-end Gateway SLA.

---

## 6. Why This Solution?

In Stage 5, we conducted a structured multi-criteria decision analysis comparing Query Relaxation against five competing search solutions:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   STAGE 5 COMPETITIVE SOLUTION DECISION MATRIX                         │
├──────────────────────────┬───────┬────────────┬──────────┬──────────┬─────────┬────────┤
│ Solution                 │ Score │ Rank       │ Fit      │ Latency  │ Cost    │ Effort │
├──────────────────────────┼───────┼────────────┼──────────┼──────────┼─────────┼────────┤
│ Query Relaxation         │ 9.05  │ 1 (Select) │ High     │ <40 ms   │ Low     │ 1.5 mo │
│ Autocomplete Suggestions │ 8.15  │ 2 (V1.1)   │ Medium   │ <20 ms   │ Low     │ 1.0 mo │
│ Synonym Graph            │ 7.80  │ 3 (V1.2)   │ Med-High │ <10 ms   │ Low     │ 1.0 mo │
│ Fuzzy Spell-Check        │ 7.45  │ 4 (V1.3)   │ Medium   │ <25 ms   │ Low     │ 0.5 mo │
│ Vector Semantic Search   │ 6.55  │ 5 (V2.0)   │ High     │ 80-150ms │ Medium  │ 3.0 mo │
│ Conversational LLM Search│ 4.80  │ 6 (V3.0)   │ Low-Med  │ 400-1200 │ High    │ 4.0 mo │
└──────────────────────────┴───────┴────────────┴──────────┴──────────┴─────────┴────────┘
```
*(Decision weights: Root-Cause Fit 30%, Complexity 20%, Explainability 15%, Latency 15%, Experimentability 10%, Infrastructure Cost 10%. Note: Weights reflect product decision assumptions, not objective truths).*

### Why Query Relaxation Won V1
1. **Root-Cause Directness**: Directly eliminates the primary bottleneck (attribute over-specification) without altering short head queries.
2. **Sub-Millisecond Execution**: Runs inside memory in 38.53 ms P95, easily meeting our $\le 50$ ms relaxation budget and $\le 250$ ms end-to-end SLA.
3. **Full Explainability**: Deterministic rules allow exact labeling of what changed in the UI, preserving user trust.
4. **Zero Recurring Infrastructure Cost**: Runs inside application compute; no cloud model API fees or vector cluster instances.

---

## 7. Experimentation

To evaluate whether Query Relaxation produces real conversion lift, we designed an offline A/B testing framework in Stage 6.

### Experimental Design (EXP-01)
- **Control Group (A)**: Strict boolean search. Returns existing catalog matches or standard zero-result page.
- **Treatment Group (B)**: Strict search + Automated Query Relaxation fallback when eligible ($\ge 4$ tokens AND $< 3$ results).
- **Randomization Unit**: User-level deterministic allocation using `MD5(user_id) % 100` (50% Control / 50% Treatment).
- **Primary Metric**: **Search $\to$ PDP Click-Through Rate (CTR)** on eligible multi-attribute searches.
- **Secondary Metrics**: Zero-Result Rate (ZRR), Query Reformulation Rate, Search $\to$ Add-to-Cart (ATC), Search $\to$ Order.
- **Statistical Framework**: Two-proportion two-tailed z-test, $\alpha = 0.05$, statistical power $\beta = 0.80$.
- **Pre-Declared Ship Threshold**: **$\ge +1.5\text{ pp}$ Search $\to$ PDP CTR lift with $p < 0.05$** `[PRODUCT ASSUMPTION]`.

### Power Analysis & Traffic Velocity Reality
- **Historical Eligible Velocity**: 941 eligible queries across 60 days = **~15.7 searches/day** `[OBSERVED]`.
- **Target MDE (+3.5 pp lift)**: Requires 596 searches per variant (1,192 total searches). Modeled duration: **~76 days** `[MODELED]`.
- **Minimum Ship Lift (+1.5 pp lift)**: Requires 3,118 searches per variant (6,236 total searches). Modeled duration: **~398 days** `[MODELED]`.

> **Core PM Takeaway**: *"Experiment design must account for the actual eligible traffic volume; otherwise teams risk stopping too early or over-interpreting noise. Sizing sample duration up front prevents premature ship decisions on underpowered tests."*

---

## 8. Simulation — Important (Offline Evaluation)

### Stage 6 Simulated Target Scenario Results

```text
================================================================================
           OFFLINE SIMULATION — NOT A LIVE A/B TEST RESULT [SIMULATED]
================================================================================
Control Arm (Strict Search)      : 461 searches, 12 PDP clicks (CTR: 2.60%)
Treatment Arm (With Relaxation)  : 480 searches, 28 PDP clicks (CTR: 5.83%)
Absolute CTR Lift                : +3.23 percentage points
Relative CTR Lift                : +124.1%
Two-Tailed p-value               : p = 0.0141 (Statistically Significant at alpha=0.05)
95% Confidence Interval          : [+0.68 pp, +5.78 pp]
================================================================================
```

### Critical Provenance Distinction
> **IMPORTANT DATA HONESTY NOTE**:
> This result is an **offline counterfactual simulation** generated by applying our hypothesized treatment effect (+3.5 pp lift) to historical user sessions in DuckDB. 
> 
> **It is NOT a live causal result.**
> 
> Never claim *"the experiment improved CTR by 124%"*. In an interview or executive review, explain that this simulation validates our statistical test pipeline and demonstrates whether a +3.5 pp lift could be detected given the empirical traffic volume.

---

## 9. Business Impact

Propagating search recovery gains through the empirical downstream conversion funnel ($P(\text{Cart}|\text{PDP}) = 24.14\%$, $P(\text{Order}|\text{Cart}) = 28.57\%$, $\text{AOV} = \$142.58$ [OBSERVED]):

### Scenario D: Central Target Scenario (+3.5 pp CTR Lift, 91.81% Recovery)

| Metric | Modeled Value | Provenance | Note |
| :--- | :---: | :---: | :--- |
| **Incremental PDP Clicks (60d)** | +30.2 clicks | `[MODELED]` | From +3.5 pp lift on 863.9 recovered searches |
| **Incremental Cart Adds (60d)** | +7.3 items | `[MODELED]` | $30.2 \times 24.14\%$ |
| **Incremental Orders (60d)** | +2.1 orders | `[MODELED]` | $7.3 \times 28.57\%$ |
| **Gross Incremental GMV (60d)** | **+$297.32** | `[MODELED]` | $2.09 \text{ orders} \times \$142.58$ |
| **Annualized Gross GMV Run-Rate** | **+$1,808.69 / year** | `[MODELED]` | Linear annualization ($\times 365/60$) |
| **Annualized Net GMV (25% Cannibalization)** | **+$1,356.52 / year** | `[MODELED]` | Discounted for search cannibalization |
| **Illustrative 100x Scale Scenario** | **+$180,869 / year** | `[MODELED]` | Modeled at 1.5M searches/year |

### Break-Even Feasibility Analysis (Stage 7.1)
Evaluating commercial break-even against standard business targets:
- **$10,000 Annual GMV**: Requires **+19.35 pp CTR lift** (Treatment CTR: 22.43%) or **507.6% recovery rate**. Feasibility: *Not achievable under current model assumptions.*
- **$25,000 Annual GMV**: Requires **+48.38 pp CTR lift** (Treatment CTR: 51.46%) or **1269.0% recovery rate**. Feasibility: *Not achievable under current model assumptions.*
- **$50,000 Annual GMV**: Requires **+96.75 pp CTR lift** (Treatment CTR: 99.84%) or **2538.0% recovery rate**. Feasibility: *Not achievable under current model assumptions.*
- **$100,000 Annual GMV**: Requires **+193.51 pp CTR lift** (Mathematically impossible >100%). Feasibility: *Not achievable under current model assumptions.*

---

## 10. Capital Discipline & Economic Sizing

A credible product manager evaluates engineering opportunity costs rather than championing every feature:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                  CAPITAL DISCIPLINE ANALYSIS (STAGE 7.1)                     │
├───────────────────────────────────────────────┬──────────────────────────────┤
│ Current Scale Modeled Opportunity (Target)    │ +$1,808.69 / year [MODELED]  │
│ Illustrative Dedicated Cluster Cost (Year 1)  │ $28,500.00 [ASSUMPTION]      │
│ Expected First-Year Net Value Destruction     │ -$26,691.31 [MODELED]        │
└───────────────────────────────────────────────┴──────────────────────────────┘
```
*(Cost inputs: 1.5 person-months @ $15K/mo = $22.5K + $6K dedicated search cluster infrastructure = $28.5K total Year-1 cost [PRODUCT ASSUMPTION — ILLUSTRATIVE PLANNING INPUT]).*

### The Core PM Conclusion
At current traffic scale (~15.7 eligible searches/day), this is **NOT an infrastructure investment case**. Committing $28.5K in dedicated search infrastructure to chase ~$1.8K in annual GMV would destroy capital.

Instead, this is a **FEATURE VALIDATION opportunity**. Because Query Relaxation is implemented as an in-memory algorithmic fallback with **zero marginal query cost**, we can deploy it inside existing application compute.

### Recommended Action: RUN A LIGHTWEIGHT CANARY FIRST
- **SHIP / SCALE CRITERIA**:
  - Search $\to$ PDP CTR lift $\ge +1.5\text{ pp}$
  - Two-tailed significance $p < 0.05$
  - Guardrails healthy (P95 latency $\le 50\text{ ms}$, ZRR $\le 10\%$)
  - No material cannibalization on catalog browse revenue
- **DEPRIORITIZE CRITERIA**:
  - Observed CTR lift $< +1.5\text{ pp}$
  - Statistical evidence remains inconclusive after planned sample size
  - Downstream conversion quality deteriorates (high quick-backs)
  - Opportunity cost exceeds expected return

---

## 11. Trade-Offs

A hallmark of rigorous product management is articulating why popular alternatives were rejected:

### 1. Why not LLMs first?
- **Answer**: LLMs add 300–1,000 ms of latency (violating our $\le 50$ ms relaxation budget and $\le 250$ ms end-to-end SLA), introduce hallucination risks (inventing non-existent products), and incur recurring per-query API costs. Our problem was attribute over-specification, which simple set operations solve deterministically.

### 2. Why not Vector Search first?
- **Answer**: Dense embeddings require vector databases (Milvus, Pinecone), indexing pipelines, and embedding generation compute. While vector search excels at vocabulary mismatch (e.g., matching *"frock"* to *"dress"*), it struggles with strict e-commerce filters like exact colors, sizes, and stock availability. Query relaxation solved 91.8% of failures without new infrastructure.

### 3. Why not Fuzzy Matching first?
- **Answer**: Fuzzy matching (Levenshtein distance) resolves typos like `"jakcet"` $\to$ `"jacket"`. However, our root-cause analysis revealed that typographical errors represented only 10% of zero-result searches, whereas attribute over-specification represented 65%. We targeted the largest failure mode first.

### 4. Why not Autocomplete first?
- **Answer**: Autocomplete suggestions guide typing intent before submission. While highly complementary (scheduled for V1.1), autocomplete does not rescue users who have already entered a long-tail query and hit Enter. Query relaxation was necessary to provide a safety net for submitted searches.

> **Core Product Principle**: *"Use the simplest intervention that directly addresses the diagnosed failure mode."*

---

## 12. Roadmap

We sequence search intelligence based on failure share, technical risk, and infrastructure overhead:

```text
[ V1 MVP: Query Relaxation ]  <--- (COMPLETED & BENCHMARKED)
Drops non-essential modifiers on 4+ token low-result searches. $0 cloud cost.
         │
         ▼
[ V1.1: Autocomplete & Query Suggestions ] (Roadmap)
Guides users toward high-inventory head/torso terms before submit.
Justification trigger: High bounce rate on search entry.
         │
         ▼
[ V1.2: Fashion Synonym Graph ] (Roadmap)
Maps colloquial/regional terms (e.g., "jumper" <-> "sweater").
Justification trigger: Vocabulary mismatch ZRR exceeding 5% of catalog searches.
         │
         ▼
[ V1.3: Fuzzy Spell-Correction ] (Roadmap)
Corrects orthographic errors (Levenshtein distance <= 2).
Justification trigger: Typo frequency exceeding 500 searches/month.
         │
         ▼
[ V2.0: Hybrid Lexical + Dense Vector Retrieval ] (Future Vision)
Integrates embeddings for aesthetic and style searches ("boho chic").
Justification trigger: Catalog volume >50,000 SKUs AND search volume >500K/mo.
         │
         ▼
[ V3.0: Conversational AI Stylist ] (Future Vision)
Multi-turn conversational recommendation assistant.
Justification trigger: Mobile app personalization maturity & positive unit economics.
```

---

## 13. Metrics Tree

```text
                     ┌───────────────────────────────────────────────┐
                     │            NORTH STAR / PRIMARY METRIC        │
                     │  Search -> PDP Click-Through Rate (CTR)       │
                     │  on Eligible Multi-Attribute Searches         │
                     └───────────────────────┬───────────────────────┘
                                             │
             ┌───────────────────────────────┴───────────────────────────────┐
             ▼                                                               ▼
┌─────────────────────────┐                                     ┌─────────────────────────┐
│   SUPPORTING FUNNEL     │                                     │  GUARDRAIL METRICS      │
├─────────────────────────┤                                     ├─────────────────────────┤
│ • Zero-Result Rate (ZRR)│                                     │ • P95 Latency (<=50ms)  │
│ • Reformulation Rate    │                                     │ • Category Accuracy     │
│ • Search -> Add to Cart │                                     │ • Stock Availability    │
│ • Search -> Order Rate  │                                     │ • Quick-Back Rate (<5s) │
│ • Revenue / Search      │                                     │ • Browse Cannibalization│
└─────────────────────────┘                                     └─────────────────────────┘
```

### Why Search $\to$ PDP CTR Is the Primary Metric
CTR directly evaluates whether the search engine succeeded at its primary user job: **moving the shopper from query intent into product evaluation**. Downstream conversion (Cart, Order) is influenced by pricing, shipping fees, and sizing, which search cannot control. However, we track Search $\to$ Order as a supporting metric and PDP Quick-Backs as a guardrail to ensure clicks reflect genuine interest.

---

## 14. Risks & Mitigations

| # | Risk Factor | Impact | Mitigation Strategy | Monitoring Telemetry |
|---|:---|:---|:---|:---|
| **1** | **Relevance Degradation** | Low click quality, user distrust | Enforce $\ge 50\%$ token overlap; score candidates by token IDF rarity. | Search $\to$ PDP CTR; Quick-back bounce rate (<5s). |
| **2** | **Wrong-Category Fallbacks** | Showing pants for a dress search | Lock category nouns during token parsing; category terms can never be dropped. | Category mismatch audit rate in search debugger. |
| **3** | **Out-of-Stock Products** | PDP drop-off at size selection | In-stock inventory check (`inventory_units > 0`) applied before fallback rendering. | Out-of-stock PDP display rate. |
| **4** | **Query Intent Dilution** | Weakening original purchase intent | Limit relaxation to max 2 dropped tokens; prioritize 1-drop over 2-drop. | Drop-count distribution logs. |
| **5** | **Latency SLA Breach** | Increased page load time | Lightweight in-memory index; pre-calculated category lists; hard 50ms sub-budget. | Server-side P95 latency timers. |
| **6** | **Search Cannibalization** | Pulling orders from higher-margin browse | Track session-level net incremental orders across control vs. treatment. | Browse session conversion differential. |
| **7** | **Low Eligible Volume** | Prolonged A/B experiment runtimes | Power analysis conducted upfront; pre-declared 76-day duration requirement. | Daily eligible search count tracker. |
| **8** | **Seasonality Bias** | Weather/holiday catalog shifts | User-level 50/50 concurrent randomization balances seasonal shifts across arms. | Weekly control-treatment baseline tracking. |

---

## 15. Limitations & Data Honesty

To maintain rigorous professional standards, all project conclusions are contextualized by the following verified limitations:
1. **Synthetic Dataset**: Ground-truth data was generated via Python (`seed=42`) in DuckDB. While schema-validated and commercially realistic, real consumer behavior exhibits greater behavioral noise.
2. **Local Inverted Index**: Algorithmic benchmarks were executed against an in-memory inverted index, not a live distributed cluster (e.g., OpenSearch).
3. **Offline Experiment Simulator**: A/B metrics reflect simulated counterfactual draws based on hypothesized lifts, not a live causal production test.
4. **No Live Causal Claims**: We never state that this feature has *already* generated revenue or increased CTR.
5. **Static Funnel Assumptions**: Financial projections assume constant downstream conversion ($P(\text{Cart}|\text{PDP})$ and $P(\text{Order}|\text{Cart})$) and linear annualization without seasonal shocks.
6. **No Real-Time Telemetry**: Real-time event streams and distributed tracing pipelines are proposed architectural components, not running services.

---

## 16. Final PM Decision

```text
================================================================================
                    FINAL PRODUCT MANAGER DECISION
================================================================================
DECISION : Proceed with lightweight experimental validation (EXP-01 canary).
REJECTED : Do NOT commit to major search infrastructure ($28.5K dedicated cluster).
WHY      : The multi-attribute discovery failure is verified (8.23% ZRR, 44.39%
           reformulation). The Query Relaxation fallback is mathematically sound,
           fast (38.53ms P95), and recovered 91.81% of unmatchable queries in benchmarks.
           However, current eligible traffic (~15.7 searches/day) yields a modest
           standalone return (~$1.8K/year). 
           
           Therefore, the correct PM posture is capital discipline:
           VALIDATE FIRST. SCALE SECOND.
================================================================================
```
