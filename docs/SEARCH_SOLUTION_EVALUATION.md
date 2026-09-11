# Search Solution Evaluation & Product Decision Analysis

## Executive Decision

**Product Recommendation**: Deploy **Automated Query Relaxation / Soft-Match Fallback** as the marketplace's **first (V1 MVP) search discovery intervention**.

This decision is not rooted in novelty or personal preference, but in a disciplined comparative evaluation across **six candidate search interventions**:
1. **Automated Query Relaxation / Soft-Match Fallback** *(Selected V1 MVP)*
2. **Query Suggestions & Autocomplete** *(Roadmap V1.1)*
3. **Synonym Graph & Vocabulary Expansion** *(Roadmap V1.2)*
4. **Levenshtein Fuzzy Matching** *(Roadmap V1.3)*
5. **Dense Semantic / Vector Search** *(Roadmap V2)*
6. **LLM-Powered Query Rewriting** *(Roadmap V3)*

The analysis demonstrates that **Query Relaxation uniquely addresses the highest-ROI discovery bottleneck** identified in user behavior—over-constrained multi-attribute queries returning zero or fewer than three items—with zero new infrastructure overhead, deterministic guardrails, sub-40ms p95 latency, and an empirical recovery rate of **91.81%** on failing queries.

---

## The User Problem

### Problem Statement
In fashion e-commerce, high-intent shoppers formulationally combine gender, silhouette, pattern, fabric, color, and size (e.g., `"women floral midi dress red"`, `"slim fit emerald green jeans M"`). Under strict keyword intersection search, if even a single modifier is unrepresented in catalog titles or if an exact attribute combination is absent from inventory, the search engine returns **zero products** (`results_count = 0`).

Showing an empty "No products found" state destroys discovery momentum, resulting in immediate customer abandonment.

### Evidence Separation
To maintain strict analytical rigor, the problem is defined across three distinct epistemological boundaries:

- **OBSERVED (Empirical Behavioral Data)**:
  - Total historical searches analyzed: **32,245**.
  - Multi-attribute queries ($\ge 4$ tokens) represent **33.85%** of search volume (10,914 searches).
  - In customer event logs, 4+ token queries suffered an **8.23% Zero-Result Rate (ZRR)** (898 events) compared to 1.78% for short queries (1–3 tokens).
  - Low-result searches ($< 3$ products) exhibited a catastrophic Search→PDP Click-Through Rate (CTR) of **3.08%** (29 clicks / 941 eligible searches), compared to **62.95%** overall.
  - On the local 1,600-product catalog, strict keyword intersection resulted in a **98.21% ZRR** on distinct 4+ token queries due to multi-attribute over-specification.

- **INFERENCE (Root-Cause Attribution)**:
  - Over-specification is the primary driver of high-intent search abandonment. Customers know what they want, but finite catalog inventory cannot satisfy the full conjunction of 4–6 strict keyword constraints.

- **HYPOTHESIS (Product Intervention Model)**:
  - Selectively dropping non-essential, highly selective modifiers while strictly protecting core product category nouns will transform zero-result searches into high-intent product impressions, increasing Search→PDP CTR from **3.08% toward the 6.58% target** (+3.5 pp lift) and recovering an estimated **+$382,500 in annualized GMV**.

---

## Candidate Solutions Deep Dive

Each of the six candidate interventions was profiled across 12 product and engineering dimensions:

### 1. Automated Query Relaxation / Soft-Match Fallback (Selected MVP)
- **User Value**: Directly salvages dead-end searches by presenting relevant catalog items matching core shopping intent.
- **Expected Impact**: Recovers $>90\%$ of over-constrained zero-result searches (empirically measured at **91.81%**).
- **Implementation Complexity**: **Low-Medium**. Implemented locally in Python inverted indexes; natively supported in Elasticsearch via `minimum_should_match` and multi-match cross-fields disjunction.
- **Engineering Effort**: **2 / 5** (Simple rule engine + deterministic scoring).
- **Latency Risk**: **1 / 5** (Empirically measured at **38.53 ms p95**, well within the 250 ms SLA ceiling).
- **Relevance Risk**: **2 / 5** (Low risk due to category consistency guardrails and $-100$ penalty for dropping category terms).
- **Explainability**: **5 / 5** (100% deterministic; exact dropped tokens and score weights are completely visible to PMs).
- **Data Requirements**: Inverted product catalog + catalog-wide token document frequencies (DF). Zero user telemetry required.
- **Personalization Potential**: Medium (can later re-rank candidate fallbacks based on user brand affinity).
- **Failure Mode**: Does not fix typos; cannot resolve vocabulary gaps (synonyms).
- **Experimentability**: **5 / 5** (Clean randomized control trial at persistent user level; clear treatment vs control).
- **Time-to-Value**: **1–2 sprints**.

### 2. Query Suggestions & Autocomplete
- **User Value**: Guides the customer toward known inventory *before* the query is submitted.
- **Expected Impact**: Prevents query over-specification on popular head and torso terms; ineffective for customers who type quickly and hit Enter.
- **Implementation Complexity**: **Medium**. Requires a Trie / FST prefix index, real-time keystroke endpoint ($<30$ ms SLA), and query log popularity ranking.
- **Engineering Effort**: **3 / 5**.
- **Latency Risk**: **3 / 5** (High frontend API query volume: 5–10 requests per search session).
- **Relevance Risk**: **1 / 5** (Suggestions are pre-validated against inventory).
- **Explainability**: **4 / 5**.
- **Data Requirements**: Aggregated historical search volume logs + catalog inventory presence.
- **Personalization Potential**: High (past search history, trending terms).
- **Failure Mode**: Cannot recover a user once a zero-result page has already been rendered.
- **Experimentability**: **4 / 5**.
- **Time-to-Value**: **3–4 sprints**.

### 3. Synonym Expansion
- **User Value**: Bridges colloquial and regional vocabulary differences (e.g., `"frock"` $\to$ `"dress"`, `"kicks"` $\to$ `"shoes"`).
- **Expected Impact**: High for vocabulary mismatches; zero impact for queries using valid catalog terms that lack mutual inventory overlap.
- **Implementation Complexity**: **Medium-High**. Requires building, validating, and maintaining a domain-specific fashion taxonomy/graph to prevent semantic drift (e.g., `"apple"` phone vs `"apple"` green).
- **Engineering Effort**: **3 / 5**.
- **Latency Risk**: **2 / 5** (Token expansion adds negligible overhead).
- **Relevance Risk**: **3 / 5** (Uncalibrated synonyms cause catastrophic precision loss and customer confusion).
- **Explainability**: **4 / 5**.
- **Data Requirements**: Curated domain synonym dictionaries or search reformulation mining pipelines.
- **Personalization Potential**: Low.
- **Failure Mode**: Synonym explosion inflating result noise; false equivalences across categories.
- **Experimentability**: **4 / 5**.
- **Time-to-Value**: **4–6 sprints** (significant domain curation required).

### 4. Levenshtein Fuzzy Matching
- **User Value**: Recovers queries containing spelling mistakes and typos (e.g., `"runing shos"` $\to$ `"running shoes"`).
- **Expected Impact**: Solves typos; zero impact on correctly spelled over-specified queries (`"women floral midi dress red"`).
- **Implementation Complexity**: **Low-Medium**. Built-in to Lucene/Elasticsearch (`fuzziness: AUTO`).
- **Engineering Effort**: **2 / 5**.
- **Latency Risk**: **3 / 5** (N-gram expansions and Levenshtein automatas increase CPU and latency on long tokens).
- **Relevance Risk**: **4 / 5** (High risk of false-friend matching on short fashion words: `"red"` matching `"bed"`, `"cap"` matching `"cup"`).
- **Explainability**: **4 / 5**.
- **Data Requirements**: Catalog vocabulary dictionary.
- **Personalization Potential**: None.
- **Failure Mode**: Inadvertently corrupting short, valid search terms into unrelated words.
- **Experimentability**: **5 / 5**.
- **Time-to-Value**: **2 sprints**.

### 5. Dense Semantic / Vector Search (Embeddings + kNN)
- **User Value**: Understands conceptual semantic similarity and thematic styling (e.g., `"cozy autumn outfit"`).
- **Expected Impact**: Extremely high for broad thematic queries; moderate-to-low for specific SKU/attribute searches that demand exact size/brand filtering.
- **Implementation Complexity**: **High**. Requires embedding generation pipeline (CLIP / fashion fine-tuned BERT), vector database (HNSW index), vector dimension storage, and hybrid BM25+dense ranking.
- **Engineering Effort**: **5 / 5**.
- **Latency Risk**: **4 / 5** (kNN vector indexing and embedding inference typically add 60–150 ms latency).
- **Relevance Risk**: **3 / 5** (Semantic drift: returning a green dress for a red dress query because the embedding distance is close).
- **Explainability**: **1 / 5** (High-dimensional vector dot-products cannot explain *why* an item was returned to an angry user).
- **Data Requirements**: High-quality multimodal product image+text embeddings, GPU inference service, offline vector evaluation set.
- **Personalization Potential**: **Very High** (vector user embeddings).
- **Failure Mode**: Loss of keyword precision; returning aesthetically similar items of the wrong gender or size.
- **Experimentability**: **3 / 5** (Complex offline calibration required before online deployment).
- **Time-to-Value**: **2–3 quarters**.

### 6. LLM-Powered Query Rewriting
- **User Value**: Converts complex natural language queries (e.g., `"what should I wear to an outdoor summer garden wedding"`) into structured catalog filters.
- **Expected Impact**: Transformational for complex conversational queries; massive overkill for 4-token attribute queries.
- **Implementation Complexity**: **Very High**. Requires prompt engineering, LLM serving infrastructure, schema validation, guardrail classifiers, and caching.
- **Engineering Effort**: **5 / 5**.
- **Latency Risk**: **5 / 5** (LLM generation adds 400–1,200 ms latency, severely violating the 250 ms production SLA).
- **Relevance Risk**: **4 / 5** (Hallucinations: inventing non-existent brands, categories, or attributes).
- **Explainability**: **2 / 5** (Prompt dependent, stochastic responses).
- **Data Requirements**: LLM API or dedicated GPU cluster, structured catalog metadata schemas, few-shot prompt sets.
- **Personalization Potential**: **Very High**.
- **Failure Mode**: Latency timeouts, API cost spikes ($0.005–$0.02 per search), and catastrophic hallucinated queries.
- **Experimentability**: **2 / 5**.
- **Time-to-Value**: **3–4 quarters**.

---

## Evaluation Framework & Weighted Decision Matrix

To ensure objective comparison, the solutions were evaluated using a weighted multi-criteria decision model.

### Scoring Weights & Strategic Rationale
| Criteria | Weight | Direction | Strategic Rationale |
| :--- | :---: | :---: | :--- |
| **User Impact on Target Bottleneck** | **20%** | Higher is better | *[PRODUCT ASSUMPTION]* Primary priority is resolving the 8.23% ZRR and 3.08% CTR discovery failure. |
| **Reach in Historical Traffic** | **15%** | Higher is better | *[PRODUCT ASSUMPTION]* Must address a substantial portion of customer sessions (33.85% of volume). |
| **Implementation Complexity & Effort** | **15%** | Lower is better | *[PRODUCT ASSUMPTION]* Fast time-to-market and low architectural debt are required for MVP validation. |
| **Latency Budget Compliance** | **10%** | Lower is better | *[PRODUCT ASSUMPTION]* Must strictly adhere to the PRD latency SLA ($p95 \le 250$ ms). |
| **Relevance & Category Safety** | **10%** | Lower risk is better | *[PRODUCT ASSUMPTION]* Must avoid polluting search results with cross-category noise. |
| **Explainability & Observability** | **10%** | Higher is better | *[PRODUCT ASSUMPTION]* PMs and engineers must understand *why* search failed and what changed. |
| **Experimentability & Clean Attribution** | **10%** | Higher is better | *[PRODUCT ASSUMPTION]* Must be cleanly testable in a randomized A/B trial with isolated attribution. |
| **Time-to-Value (Velocity)** | **10%** | Shorter is better | *[PRODUCT ASSUMPTION]* Rapid feedback loop required to de-risk investment before major architectural commitments. |

### Decision Matrix (Scale 1–10, Higher is Better)
*Note: Negative dimensions (Effort, Latency Risk, Relevance Risk) are scored inversely where 10 = Lowest Risk / Lowest Effort, and 1 = Severe Risk / Extreme Effort.*

| Evaluation Dimension | Weight | Query Relaxation | Autocomplete | Synonyms | Fuzzy Match | Vector Search | LLM Rewriting |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Target Problem Fit** | 20% | **9.5** | 6.0 | 5.5 | 4.0 | 7.5 | 7.0 |
| **Traffic Reach** | 15% | **8.5** | 7.5 | 6.0 | 5.0 | 8.0 | 4.0 |
| **Low Engineering Effort** | 15% | **8.5** | 6.0 | 5.0 | 8.0 | 2.5 | 2.0 |
| **Latency Compliance** | 10% | **9.5** | 7.5 | 9.0 | 7.0 | 4.5 | 1.5 |
| **Relevance Safety** | 10% | **8.5** | 9.0 | 6.0 | 5.0 | 6.5 | 4.0 |
| **Explainability** | 10% | **10.0** | 8.0 | 7.5 | 8.0 | 2.0 | 3.0 |
| **Experimentability** | 10% | **9.5** | 7.5 | 7.0 | 8.5 | 5.0 | 3.5 |
| **Fast Time-to-Value** | 10% | **9.5** | 6.5 | 5.5 | 8.0 | 3.0 | 2.0 |
| **WEIGHTED TOTAL SCORE** | **100%** | **9.05** | **7.00** | **6.10** | **6.40** | **5.25** | **3.68** |
| **RANK** | - | **#1 (Selected)** | **#2** | **#4** | **#3** | **#5** | **#6** |

---

## Solution-Level RICE Prioritization

To connect the technical comparison to portfolio-standard product management methodology, each solution was evaluated using the RICE framework:

$$\text{RICE Score} = \frac{\text{Reach} \times \text{Impact} \times \text{Confidence}}{\text{Effort}}$$

### Parameter Definitions & Calibrations
- **Reach**: Estimated annual user search sessions impacted *(Modeled on 32,245 base sessions)*.
- **Impact**: Multiplier on customer discovery and conversion:
  - $3.0 = \text{Massive}$ (recovers complete zero-result failure)
  - $2.0 = \text{High}$
  - $1.0 = \text{Medium}$
  - $0.5 = \text{Low}$
- **Confidence**: Empirical backing and risk level:
  - $100\% = \text{High}$ (validated by empirical local benchmark and actual event logs)
  - $80\% = \text{Medium}$
  - $50\% = \text{Low}$ (high technical or relevance risk)
- **Effort**: Person-months of engineering, analytics, and QA required for production release.

### RICE Comparison Table
| Solution Option | Reach (Searches/yr) [MODELED] | Impact Factor [MODELED] | Confidence [MODELED] | Effort (Person-Mo) [MODELED] | RICE Score [MODELED] | Prioritization Tier |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Query Relaxation (MVP)** | **10,914** | **2.5** (High-Massive) | **90%** (Local proof) | **1.5** (Inverted logic) | **16,371** | **P0 (Immediate MVP)** |
| **2. Autocomplete & Suggestions** | 18,000 | 1.0 (Medium) | 80% (Industry std) | 3.0 (Prefix infrastructure) | **4,800** | **P1 (Roadmap V1.1)** |
| **3. Fuzzy Typo Matching** | 3,500 | 1.5 (Targeted) | 80% (Lucene native) | 1.5 (Threshold tuning) | **2,800** | **P1 (Roadmap V1.3)** |
| **4. Synonym Expansion** | 4,200 | 1.5 (Targeted) | 60% (Taxonomy risk) | 3.5 (Domain curation) | **1,080** | **P2 (Roadmap V1.2)** |
| **5. Vector / Semantic Search** | 12,000 | 2.0 (High) | 50% (Precision risk) | 8.0 (Embeddings + Vector DB) | **1,500** | **P2 (Roadmap V2.0)** |
| **6. LLM Query Rewriting** | 2,500 | 2.0 (High) | 30% (Latency/Cost risk) | 6.0 (Serving + Guardrails) | **250** | **P3 (Exploratory V3)** |

**Strategic Takeaway**: Query Relaxation achieves more than **$3.4\times$ the RICE score** of its closest alternative due to its massive impact on the specific 8.23% ZRR discovery failure mode paired with minimal engineering effort.

---

## Why Query Relaxation First?

The decision to build Query Relaxation as the first intervention is supported by five concrete product arguments:

1. **Surgical Alignment with the Empirical Failure Mode**:
   The primary discovery failure is not that customers cannot spell or do not know fashion terms; it is that they provide **too much valid detail** for the finite catalog inventory. Query Relaxation is the *only* solution designed specifically to solve over-constrained retrieval.
2. **Zero Infrastructure Overhead**:
   Query Relaxation operates directly within existing inverted keyword index data structures (document frequencies and postings lists). It does not require deploying new vector databases, caching layers, or GPU inference clusters.
3. **Strict Latency Compliance**:
   With a measured mean overhead of **13.12 ms** and a total p95 latency of **38.53 ms**, Query Relaxation comfortably operates within the 250 ms production budget, leaving 210+ ms of headroom.
4. **Deterministic Explainability & Debuggability**:
   In e-commerce, merchandisers and category managers must know *why* an item appeared. Query Relaxation provides 100% explainability: dropped modifiers, document frequencies, and score deltas are completely visible.
5. **Fastest Time-to-Value & Cleanest Experimentation**:
   Query Relaxation isolates a single, clean independent variable: *relaxing selective modifiers on failing multi-token searches*. This provides an unpolluted baseline for A/B testing before layering complex semantic algorithms.

---

## Why Not AI First?

A frequent temptation in modern product design is jumping immediately to Generative AI, LLMs, or dense vector search: *"Why not just use an embedding model or an LLM to rewrite queries?"*

Starting with AI first was explicitly rejected for seven defensible reasons:

1. **The Target Problem is Narrow & Well-Defined**:
   The failure mode is over-specification on structured product attributes (color, size, style, silhouette). It does not require open-ended natural language reasoning; it requires relaxing Boolean intersection constraints.
2. **Deterministic Relevance Guardrails**:
   LLMs and vector embeddings are inherently non-deterministic and susceptible to semantic drift (e.g., returning a blue blazer when the user explicitly asked for a red dress because both share "formal cocktail apparel" embedding space). Query Relaxation strictly guarantees category consistency through mathematical penalties.
3. **Severe Production Latency Violations**:
   The production SLA target is $p95 \le 250$ ms. An LLM API call typically incurs **400–1,200 ms**, directly violating customer latency expectations and reducing conversion. Query Relaxation executes in **14.47 ms mean latency**.
4. **Disproportionate Infrastructure & Operating Costs**:
   Query Relaxation adds negligible compute cost (~0.01 ms CPU time per candidate). LLM inference costs $0.005–$0.02 per search, totaling tens of thousands of dollars annually in operational expenditure before proving product-market fit.
5. **The Need for a Calibrated Baseline**:
   Without a high-performing deterministic baseline, it is impossible to determine whether an expensive AI search system is actually generating incremental lift or simply masking basic keyword indexing failures.
6. **Lack of Domain-Specific Training Data**:
   Off-the-shelf vector embedding models (e.g., standard text-embedding-ada) perform poorly on specialized fashion taxonomies without extensive contrastive fine-tuning on millions of click pairs.
7. **Principled Product Management Philosophy**:
   A great product manager solves problems with the **simplest, most reliable, most cost-effective intervention** that delivers the required business outcome. AI is a powerful technology to be deployed when simpler heuristics fail, not a default starting point.

> [!NOTE]
> **Product Position**: AI and semantic vector search are **not rejected outright**—they are phased into **Roadmap V2 / V3** after the deterministic baseline is online and its residual failure modes are measured.

---

## Where Query Relaxation Fails (Failure Mode Taxonomy)

A robust product evaluation must openly document where the selected solution **fails**. Query Relaxation is not a panacea. 

Below is the failure mode taxonomy verified by the empirical test harness ([`src/evaluate_competing_solutions.py`](file:///C:/Projects/ecommerce-product-analytics/src/evaluate_competing_solutions.py)):

| Failure Mode | Query Example | Root Cause | Query Relaxation Behavior | Recovery Outcome | Optimal Future Solution |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Over-Constrained Query** | `women floral midi dress red` | Modifiers unrepresented together in inventory | Drops selective non-core modifiers (`midi`, `red`), preserves `women floral dress` | **SUCCESS (+16 hits, 8.2 ms)** | **Query Relaxation (V1 MVP)** |
| **Typo / Misspelling** | `runing shos` | Edit distance mismatch against catalog vocabulary | Guardrail prevents dropping core words; stems do not match catalog tokens | **FAIL (0 hits, No recovery)** | **Levenshtein Fuzzy Matching (V1.3)** |
| **Vocabulary Gap / Synonyms** | `ladies frock` | Regional/colloquial terms absent from catalog | Tokens are absent from index ($\text{DF}=0$); cannot recover without category noun | **FAIL (0 hits, No recovery)** | **Synonym Graph Expansion (V1.2)** |
| **Conversational Natural Language** | `what to wear to a summer beach wedding` | Non-attribute prose not indexed by inverted lists | Evaluates candidate subsets but fails category consistency and keyword overlap | **FAIL (0 hits, Circuit Breaker)** | **Semantic / Vector Search (V2.0)** |
| **Ambiguous Single Term** | `linen` | Underspecified customer intent across multiple departments | Guardrail blocks relaxation on queries with $< 4$ tokens | **FAIL (Guarded broad results)** | **Query Suggestions / Autocomplete (V1.1)** |
| **Attribute Substitution** | `nike shoes size 11` | Specific size out of stock; user might accept size 10.5 | Relaxation drops size token entirely instead of suggesting adjacent available size | **PARTIAL (Drops size constraint)** | **Attribute Substitution Engine (V2.2)** |

---

## Staged Search Discovery Roadmap

The search evolution roadmap is structured incrementally based on addressing discovered failure modes:

```
V1 (MVP) ───► V1.1 ───────► V1.2 ────────► V1.3 ────────► V2.0 ────────► V3.0
Query         Autocomplete  Synonym      Levenshtein     Dense Semantic   Conversational
Relaxation    & Suggestions Graph        Fuzzy Search    Vector Search    AI Assistant
(Over-        (Pre-query    (Vocabulary  (Spelling       (Thematic        (Complex
specification) guidance)    mismatches)  errors)         discovery)       prose intent)
```

### Stage V1: Automated Query Relaxation (Current MVP)
- **Problem**: Over-constrained 4+ token queries returning zero results.
- **Business Value**: Eliminates dead-end searches for 941 high-intent customer sessions.
- **Expected Lift**: $+3.5\text{ pp}$ Search→PDP CTR; $+\$382\text{K}$ annualized GMV.
- **Dependencies**: Existing local catalog and inverted document frequencies.

### Stage V1.1: Query Suggestions & In-Search Autocomplete
- **Problem**: High friction during mobile typing; users formulating queries blind to inventory.
- **Business Value**: Steers users into successful search paths before submitting dead queries.
- **Expected Lift**: $-15\%$ search reformulation rate; $+1.2\text{ pp}$ CTR.
- **Dependencies**: Query event aggregation pipeline + prefix trie index.

### Stage V1.2: Fashion Synonym Graph Expansion
- **Problem**: Colloquial and regional vocabulary gaps (`"frock"` $\to$ `"dress"`, `"kicks"` $\to$ `"sneakers"`).
- **Business Value**: Expands discovery reach for non-standard fashion terminology.
- **Expected Lift**: $-25\%$ of remaining zero-result queries on 1–3 token head terms.
- **Dependencies**: Curated fashion taxonomy dictionary.

### Stage V1.3: Levenshtein Fuzzy Typo Correction
- **Problem**: Mobile keyboard typos on brand and category terms (`"adidass"`, `"runing"`).
- **Business Value**: Captures fat-finger typing errors without dropping words.
- **Expected Lift**: $-10\%$ of remaining zero-result queries.
- **Dependencies**: Spellcheck lexicon derived from catalog vocabulary.

### Stage V2.0: Dense Semantic / Hybrid Vector Search
- **Problem**: Inability to handle thematic, occasion-based, or aesthetic searches (`"cozy aesthetic autumn outfit"`).
- **Business Value**: Unlocks high-margin lifestyle and trend-driven apparel shopping.
- **Expected Lift**: $+5.0\text{ pp}$ broad search CTR; $+8\%$ search session depth.
- **Dependencies**: Multimodal embedding model (CLIP/BERT) + Vector Index (HNSW) + BM25/Dense Reciprocal Rank Fusion.

### Stage V3.0: Conversational AI Shopping Assistant
- **Problem**: Complex open-ended styling consultations (`"I'm attending a semi-formal destination wedding in Greece"`).
- **Business Value**: Premium white-glove discovery experience for high-LTV tiers.
- **Expected Lift**: $+12\%$ basket size for assisted sessions.
- **Dependencies**: Low-latency LLM agent runtime + real-time inventory retrieval tools.

---

## Open Questions & Risks

1. **Merchandising Threshold Calibration**:
   - *Question*: Is a strict result count of $< 3$ the optimal universal trigger, or should premium luxury categories have a higher threshold ($< 5$)?
   - *Mitigation*: Run offline sensitivity analysis across catalog categories prior to canary rollout.
2. **Margin & Brand Cannibalization Risk**:
   - *Question*: Could relaxing brand modifiers substitute high-margin branded items with lower-margin alternatives?
   - *Mitigation*: Brand terms receive protected scoring priority, ensuring private-label substitution only occurs when the requested brand has zero available inventory.
3. **User Perceived Precision**:
   - *Question*: Will users notice and appreciate relaxed queries, or will they perceive the system as "ignoring" parts of their request?
   - *Mitigation*: Display transparent UI messaging: *"Showing 16 results for 'women floral dress' (relaxed from your search)"*.

---

## Assumptions & Boundaries

- **[PRODUCT ASSUMPTION]**: High-intent multi-attribute searchers prefer viewing closely related category products over encountering an empty zero-result screen.
- **[MODELED]**: The Search→PDP CTR on recovered searches is projected to rise from $3.08\%$ to at least $6.58\%$, generating $+\$382,500$ annualized GMV.
- **[ENGINEERING BOUNDARY]**: This document evaluates product architecture. It does not claim that distributed Elasticsearch clusters, vector databases, or LLMs are currently running in this repository.
