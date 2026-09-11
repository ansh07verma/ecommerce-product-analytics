# Automated Query Relaxation MVP

## Problem

In e-commerce search, high-intent shoppers frequently formulate multi-attribute queries combining gender, style, silhouette, fabric, color, and size (e.g., `"women floral midi dress red"`, `"slim fit emerald green jeans M"`).

Under strict keyword intersection search:
- If even **one** modifier is unrepresented in product titles or catalog tags (e.g., `"midi"` with catalog document frequency = 0), the search engine returns **zero products** (`results_count = 0`).
- If an attribute combination has zero catalog inventory (e.g., red floral dresses), strict search returns 0 products despite abundant related floral dresses in other colors.

On the local catalog of 1,600 fashion products, strict keyword search resulted in a **98.21% zero-result rate (ZRR)** across distinct 4+ token queries. In historical customer session logs, multi-token searches suffered an 8.23% ZRR and low-result searches (<3 results) suffered an abysmal **3.08% Search→PDP CTR** (compared to 62.95% overall).

Showing an empty "No products found" page destroys user trust and causes immediate session bounce.

---

## Product Hypothesis

> If the search engine automatically identifies and relaxes non-essential, highly selective modifiers when strict retrieval yields fewer than 3 in-stock items—while strictly protecting core product and category nouns—then the marketplace can recover over 85% of failing searches, delivering highly relevant in-stock products and increasing product discovery without introducing category drift.

---

## Trigger Condition

To prevent query drift on head queries while targeting specific long-tail failures, the relaxation engine enforces an explicit, strict trigger rule:

```
Trigger Relaxation IF:
    len(meaningful_tokens) >= 4
    AND
    strict_in_stock_results < 3
```

- **Short Queries (1–3 tokens)**: Never relaxed. If `"dress"` or `"nike shoes"` returns 0 results, query relaxation does NOT trigger (`status = LOW_RESULTS_NO_RELAXATION`). Modifying short queries risks severe intent drift.
- **Successful Queries (>=4 tokens, >= 3 results)**: Never relaxed (`status = NORMAL`). If `"women floral print dresses"` returns 16 in-stock products, strict results are returned directly.
- **Eligible Queries (>=4 tokens, < 3 results)**: Relaxation triggers (`status = RELAXED_RECOVERED` or `NO_SAFE_RELAXATION`).

---

## Candidate Generation

Candidate generation is fully deterministic and avoids combinatorial explosion by prioritizing candidate token subsets into tiers:

1. **Tier 1 (Single Token Removal)**: Evaluates subsets dropping exactly 1 token ($N$ candidates for an $N$-token query).
2. **Tier 2 (Double Token Removal)**: If Tier 1 candidates do not recover adequate results ($\ge 3$ items), evaluates subsets dropping 2 tokens ($\binom{N}{2}$ candidates).
3. **Tier 3 (Triple Token Removal)**: For very long queries ($N \ge 5$), evaluates dropping 3 tokens if at least 2 tokens remain.

Every candidate query retains at least **2 meaningful tokens** to prevent over-relaxation into single-word generic queries.

---

## Modifier Selection

The engine classifies each token in the query using catalog-wide document frequency (DF) and semantic catalog presence:

1. **Token Catalog Frequency**:
   - $\text{DF} = 0$: Token does not appear anywhere in catalog products (e.g., `"midi"`, misspelled terms, unindexed sizing codes). These are prioritized for immediate removal.
   - Low $\text{DF} \in [1, 50]$: Highly selective attributes (e.g., specific colors like `"emerald"`, fabric textures). Strong candidates for relaxation.
   - High $\text{DF} > 150$: Broad terms (e.g., `"jeans"`, `"shirt"`, `"women"`).

2. **Semantic Category Protection**:
   - Tokens corresponding to **Master Categories** (`men`, `women`, `footwear`, `accessories`) and **Subcategories** (`dress`, `shirt`, `jean`, `trouser`, `shoe`, `sneaker`, `sandal`) are classified as **Core Category Terms**.
   - **Hard Rule**: Core category tokens receive a severe scoring penalty ($-100$ pts) if removed while modifier tokens are available. For example, in `"women floral midi dress red"`, the engine will never drop `"dress"` in favor of keeping `"midi"` or `"red"`.

---

## Fallback Ranking

Candidate fallback queries are evaluated against the strict search engine and ranked using an explainable, deterministic multi-factor objective function:

$$\text{Score}(c) = S_{\text{recovery}} + S_{\text{intent}} + S_{\text{category}} + S_{\text{relevance}}$$

Where:
- **$S_{\text{recovery}}$ (Result Recovery Quality)**:
  - $+50.0$ if candidate returns $\ge 3$ in-stock products.
  - $+20.0$ if candidate returns $1–2$ in-stock products.
  - $+\min(15.0, 1.5 \times \text{result\_count})$ (marginal utility for deeper result sets).
- **$S_{\text{intent}}$ (Intent Preservation)**:
  - $+25.0 \times \frac{|\text{remaining\_tokens}|}{|\text{original\_tokens}|}$ (rewards retaining more original information).
  - $-8.0 \times |\text{dropped\_tokens}|$ (penalty per dropped modifier).
  - $-100.0$ if any core category token was dropped when modifiers existed.
- **$S_{\text{category}}$ (Category Consistency)**:
  - $+25.0$ if candidate results match the query's inferred master category.
  - $-80.0$ if candidate results cause cross-category drift.
- **$S_{\text{relevance}}$ (Item Relevance Score)**:
  - $+0.15 \times \text{avg\_relevance\_score}$ of the top-ranking items.

The candidate achieving the highest deterministic score is selected as the fallback.

---

## Relevance Guardrails

1. **In-Stock Filtering**: Only in-stock inventory is returned. Out-of-stock items are strictly excluded from the 3-result threshold and SRP results.
2. **Category Consistency**: Prevents cross-department contamination (e.g., query for women's apparel will not return men's footwear).
3. **Minimum Token Overlap**: At least 2 original query tokens must be matched.
4. **Safety Circuit Breaker (`NO_SAFE_RELAXATION`)**: If no candidate query can produce in-stock catalog matches without violating guardrails, the engine returns `status = NO_SAFE_RELAXATION` with 0 results rather than returning irrelevant products.

---

## Real Catalog Example

### Query: `"women floral midi dress red"`

```json
{
  "original_query": "women floral midi dress red",
  "normalized_query": "women floral midi dress red",
  "strict_result_count": 0,
  "relaxation_triggered": true,
  "relaxation_reason": "Strict search returned fewer than 3 results (0 returned) for a specific 5-token query.",
  "recovery_status": "RELAXED_RECOVERED",
  "selected_removed_tokens": ["midi", "red"],
  "selected_removed_token": "midi",
  "fallback_query": "women floral dress",
  "fallback_result_count": 16,
  "total_execution_time_ms": 7.82,
  "relaxation_overhead_ms": 6.66,
  "explanation": "Strict search returned 0 results for 'women floral midi dress red'. The modifier(s) 'midi' (catalog DF=0), 'red' (catalog DF=47) were identified as non-core attributes causing strict retrieval failure. Relaxing them preserved core category intent 'women floral dress', successfully recovering 16 relevant in-stock products in 6.66 ms.",
  "results": [
    {
      "product_id": "p-a25f16dde589",
      "title": "Biba Floral Print Dresses",
      "brand": "Biba",
      "master_category": "Women",
      "sub_category": "Dresses",
      "effective_price": 78.46,
      "is_in_stock": true,
      "relevance_score": 30.582
    },
    {
      "product_id": "p-7559726b91cb",
      "title": "Mango Floral Print Dresses",
      "brand": "Mango",
      "master_category": "Women",
      "sub_category": "Dresses",
      "effective_price": 68.75,
      "is_in_stock": true,
      "relevance_score": 30.546
    }
  ]
}
```

---

## Benchmark Results

Evaluated over 1,000 distinct historical queries extracted from `search_events` against the 1,600-product catalog:

| Metric | Baseline Strict Search | Relaxed Fallback Engine | Delta / Improvement |
| :--- | :--- | :--- | :--- |
| **Evaluated Queries** | 1,000 | 1,000 | - |
| **Overall Zero-Result Rate** | 89.10% (891) | **8.40%** (84) | **-80.70 pp** |
| **Overall Low-Result Rate (<3)** | 89.10% (891) | **9.80%** (98) | **-79.30 pp** |
| **Eligible Queries (>=4t, <3)** | 879 | 879 | - |
| **Recovered Queries** | 0 | **807** | **+807** |
| **Eligible Recovery Rate** | 0.00% | **91.81%** | **+91.81%** |
| **Average Results per Query** | 1.53 | **11.01** | **+9.48 items** |
| **Avg Added Results (Eligible)** | 0.00 | **10.78** | **+10.78 items** |

### Stratification by Query Length

| Strata | Query Count | Strict ZRR | Relaxed ZRR | Eligible | Recovered | Recovery Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Short (1–3 tokens)** | 105 | 11.43% | 11.43% | 0 | 0 | *Guarded (0%)* |
| **Long (4+ tokens)** | 895 | 98.21% | **8.60%** | 879 | **807** | **91.81%** |

---

## Latency Profile

Execution latency measured on a standard developer workstation (target SLA from PRD: p95 $\le 250$ ms):

| Stage | Mean | p50 | p90 | p95 | p99 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Strict Search Baseline** | 1.36 ms | 1.40 ms | 1.75 ms | 2.08 ms | 3.17 ms |
| **Total Relaxed Latency** | 14.47 ms | 12.30 ms | 27.39 ms | **38.53 ms** | **44.04 ms** |
| **Relaxation Overhead** | 13.12 ms | 11.21 ms | 26.24 ms | 36.99 ms | 42.16 ms |

**SLA Verification**: At **38.53 ms p95**, the query relaxation engine operates well within the proposed 250 ms production ceiling.

---

## Limitations

1. **In-Memory Local Implementation**: Built in Python on top of inverted dictionary postings; not a distributed multi-node cluster.
2. **Deterministic Keyword-Only Matching**: Relies on document frequency and Porter-style stemming; does not utilize vector embeddings or semantic synonym graphs (e.g., mapping `"sneakers"` to `"trainers"`).
3. **No Dynamic User Personalization**: Fallback ranking optimizes for catalog relevance and intent preservation, without factoring in user-specific affinity or historical click patterns.

---

## Future Improvements

1. **Distributed BM25 Integration**: Porting candidate selection and fallback scoring to Elasticsearch / OpenSearch `minimum_should_match` and multi-match disjunction max queries.
2. **Synonym Graph & Typo Correction**: Augmenting modifier relaxation with Levenshtein-distance fuzzy matching for brand misspellings.
3. **Live A/B Testing**: Validating whether the 91.81% search recovery translates to the modeled +3.93 pp Search→PDP CTR lift in a live customer experiment.
