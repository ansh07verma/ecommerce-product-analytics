# Product Decision Record (PDR-001)

## Decision Title
**PDR-001: Selection of Automated Query Relaxation as the V1 Search Discovery MVP**

- **Status**: **ACCEPTED & IMPLEMENTED (MVP)**
- **Decision Date**: 2026-09-11
- **Product Area**: Search Discovery & Conversion Funnel
- **Author**: Lead Product Manager (Search & Discovery)
- **Technical Context**: Local Deterministic E-Commerce Search Engine / Future Elasticsearch Architecture

---

## 1. Decision Summary

We have decided to build, benchmark, and deploy **Automated Query Relaxation / Soft-Match Fallback** as the marketplace’s **primary (V1 MVP) search discovery intervention**. 

Competing solutions—specifically Autocomplete Suggestions, Domain Synonym Expansion, Levenshtein Fuzzy Search, Dense Vector Search, and LLM Query Rewriting—were evaluated and intentionally sequenced for subsequent roadmap releases (V1.1 through V3.0).

---

## 2. Context & Problem Framing

Product analytics on the historical fashion marketplace dataset identified search discovery failure as the primary drop-off point in the customer journey:
1. Multi-attribute queries ($\ge 4$ tokens) represent **33.85%** of all search traffic (10,914 / 32,245 searches).
2. Multi-attribute queries suffer an **8.23% Zero-Result Rate (ZRR)**, more than **$4.6\times$ higher** than 1–3 token head queries (1.78% ZRR).
3. In customer event logs, searches returning $< 3$ products suffer a catastrophic Search→PDP Click-Through Rate (CTR) of **3.08%** (29 clicks / 941 searches), compared to **62.95%** for normal searches.
4. When testing distinct 4+ token queries against the local 1,600-product catalog, strict keyword intersection returned zero results for **98.21% of queries** (879 / 895) due to multi-attribute over-specification.

The product goal is to eliminate dead-end search experiences, recover high-intent shoppers, and lift Search→PDP CTR from 3.08% toward the 6.58% target (+3.5 pp lift), unlocking an estimated $+\$382,500$ in annualized GMV.

---

## 3. Empirical Evidence Base

The decision is anchored in verified measurements across both historical session logs and the implemented local search engine:

| Metric / Dimension | Strict Keyword Search | Query Relaxation Engine | Source / Evidence |
| :--- | :---: | :---: | :--- |
| **Historical 4+ Token Search Volume** | 10,914 events | 10,914 events | DuckDB `search_events` |
| **Historical 4+ Token ZRR** | 8.23% (898 events) | - | DuckDB `search_events` |
| **Low-Result Search→PDP CTR (<3 hits)** | **3.08%** (29 clicks) | - | DuckDB `search_events` + `product_views` |
| **Catalog Strict 4+ Token ZRR** | **98.21%** (879 / 895 queries) | **8.60%** (77 queries) | Baseline Search Benchmark |
| **Eligible Query Recovery Rate** | 0.00% | **91.81%** (807 / 879 recovered) | Relaxation Engine Benchmark |
| **Average Added Products (Eligible)** | 0.00 | **+10.78 products** | Relaxation Engine Benchmark |
| **Execution Latency (Mean)** | 1.36 ms | 14.47 ms | Relaxation Engine Benchmark |
| **Execution Latency (p95)** | 2.08 ms | **38.53 ms** (Target $\le 250$ ms) | Relaxation Engine Benchmark |

---

## 4. Alternatives Considered & Comparative Trade-offs

| Alternative Solution | Target Problem Fit | Implementation Complexity | Latency Impact | Relevance Risk | Decision Verdict |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **1. Query Relaxation (Selected)** | **High (9.5/10)** | **Low-Medium** | **Low (38.5ms p95)** | **Low (Guardrails)** | **ACCEPTED (V1 MVP)** |
| **2. Autocomplete & Suggestions** | Medium (6.0/10) | Medium | Medium ($<30$ms keystroke) | Very Low | **Deferred to Roadmap V1.1** |
| **3. Fashion Synonym Graph** | Medium (5.5/10) | Medium-High (Curation) | Low ($<5$ms) | Medium (Semantic drift) | **Deferred to Roadmap V1.2** |
| **4. Levenshtein Fuzzy Search** | Low (4.0/10) | Low-Medium | Medium ($+10$ms) | High (False-friend terms) | **Deferred to Roadmap V1.3** |
| **5. Dense Semantic / Vector Search** | High (7.5/10) | High (Vector DB + GPU) | High ($+80$ms) | Medium (Loss of exact filter) | **Deferred to Roadmap V2.0** |
| **6. LLM Query Rewriting** | High (7.0/10) | Very High (LLM Serving) | Extreme ($+800$ms) | High (Hallucinations) | **Deferred to Roadmap V3.0** |

---

## 5. Decision Rationale

Automated Query Relaxation was chosen because it maximizes **expected business lift per unit of engineering complexity**:

1. **Surgical Alignment with Customer Failure Mode**:
   Over-specification is the primary reason high-intent searches return zero results. Customers type valid catalog attributes that do not co-occur in inventory. Query Relaxation directly removes this bottleneck by dropping non-core modifiers while protecting category nouns.
2. **Zero Net Infrastructure Cost**:
   Can be implemented natively inside existing inverted index search engines (Elasticsearch `minimum_should_match`, postings intersection) without procuring GPU infrastructure or vector databases.
3. **Strict Latency Compliance**:
   Total p95 execution latency of **38.53 ms** leaves over 210 ms of headroom under the PRD's 250 ms production budget.
4. **Deterministic Explainability & Merchandising Guardrails**:
   Allows merchandisers and engineers to inspect exact token weights, document frequencies, and dropped modifiers. Mathematical penalties ($-100$ pts for dropping category nouns) eliminate the risk of random category drift.
5. **Cleanest Experimental Hypothesis**:
   Provides an unambiguous causal test in an A/B trial: *Does recovering over-constrained queries into high-intent product impressions increase Search→PDP CTR?*

---

## 6. Trade-offs & Accepted Limitations

By selecting Query Relaxation as the sole V1 intervention, the product team explicitly accepts the following trade-offs:

1. **Typo Vulnerability**: Query Relaxation cannot correct misspelled words (e.g., `"runing shos"`). If the typo appears in a core noun, relaxation will either preserve the misspelled term or activate the circuit breaker (`NO_SAFE_RELAXATION`).
2. **Vocabulary Gaps**: Regional or colloquial terminology (e.g., `"frock"`, `"kicks"`) will be classified as missing catalog terms ($\text{DF}=0$) and dropped, rather than translated to `"dress"` or `"shoes"`.
3. **Conversational Queries**: Open-ended prose queries (e.g., `"what to wear to a summer beach wedding"`) will fail category consistency and return zero results.
4. **Static Ranking**: Fallback candidate selection optimizes for category consistency and item relevance score, without user-level personalization.

---

## 7. Revisit Triggers (Exit & Escalation Conditions)

This decision is governed by explicit quantitative revisit triggers. We will re-open this architectural decision if:

1. **High Residual ZRR Due to Typos**: Post-launch query log analysis reveals that $>20\%$ of remaining zero-result searches contain Levenshtein edit-distance typos $\to$ *Fast-track Levenshtein Fuzzy Matching (Roadmap V1.3)*.
2. **High Residual ZRR Due to Vocabulary Gaps**: Reformulation analysis reveals frequent substitution of colloquial terms $\to$ *Fast-track Synonym Graph Expansion (Roadmap V1.2)*.
3. **Relevance Degradation in A/B Testing**: Treatment group Search→PDP CTR drops by $>2.0$ percentage points or PDP bounce rate increases by $>10\%$ $\to$ *Halt rollout, tighten category consistency penalty from $-80$ to $-120$, and re-calibrate offline*.
4. **Offline Dense Retrieval Outperformance**: Offline evaluation demonstrates that a fine-tuned fashion bi-encoder vector model achieves $>15\%$ higher NDCG@10 than BM25 + Query Relaxation on high-intent test sets $\to$ *Initiate Stage V2.0 Vector Search Migration*.
5. **Excessive Latency Overhead**: Production p95 latency exceeds 150 ms in canary deployment $\to$ *Restrict candidate evaluation tier to single-token drops only*.
