# Final Technical Product Specification: Automated Query Relaxation (EXP-01)

**Document Version:** 1.0.0  
**Status:** Approved for Engineering Implementation  
**Product Reference:** `docs/final_prd.md` (MVP: SOL-01 / EXP-01)  
**Target Systems:** Search API Gateway, Primary Retrieval Service, Query Relaxation Worker, Analytics Pipeline  

---

## 1. System Context & Overview

This specification details the technical architecture, component contracts, algorithmic pseudocode, latency budgets, and telemetry pipelines for **SOL-01: Automated Query Relaxation / Soft-Match Fallback**. 

### 1.1 Objective
Provide an automated, server-side intent-recovery mechanism for search queries meeting the canonical eligibility criteria:
$$\text{Eligible Query} \iff (\text{Token Count} \ge 4) \land (\text{Strict Result Count} < 3)$$

The system attempts a controlled relaxation by dropping the least-selective modifier while strictly preserving core product category nouns, executing a fallback retrieval, and returning relevant partial matches accompanied by an informative UI context banner.

```
+---------------------------------------------------------------------------------------+
|                               SYSTEM CONTEXT TOPOLOGY                                 |
+---------------------------------------------------------------------------------------+
|  [Client App: Web / iOS / Android]                                                    |
|         ? (HTTPS POST /api/v1/search)                                                 |
|         ?                                                                             |
|  [Search API Gateway & Experiment Allocator]                                          |
|         ??? SHA-256 Session Hash Evaluation                                           |
|         ??? Feature Flag: 'search_query_relaxation_v1'                                |
|         ?                                                                             |
|         ?                                                                             |
|  [Primary Retrieval Engine (Elasticsearch / OpenSearch)]                              |
|         ??? Strict Conjunction Match across Title, Description, Tags                  |
|         ??? Result Count Evaluation: Is Result Count < 3?                             |
|               ??? YES & 4+ Tokens & Treatment ??? [Automated Relaxation Engine]       |
|               ?                                          ?                            |
|               ?                                          ?                            |
|               ?                                   [Fallback Retrieval Service]        |
|               ?                                          ? (Merge & Format)           |
|               ?                                          ?                            |
|               ??? NO (or Control Arm) ??????????? [Response Formatter]                |
|                                                          ?                            |
|                                                          ?                            |
|                                             [Client UI + Kafka Telemetry]             |
+---------------------------------------------------------------------------------------+
```

---

## 2. Architectural Components & Responsibilities

### 2.1 API Gateway & Experiment Router
- **Input:** Incoming client search request (`query_text`, `session_id`, `user_id`, `filters`, `device`).
- **Function:** Evaluates experiment assignment using deterministic hashing:
  $$\text{Bucket} = \text{SHA-256}(\text{session\_id}) \pmod{100}$$
  Allocates 50% to Control (`control`) and 50% to Treatment (`treatment`).
- **Circuit Breaker:** Tracks upstream response times. If average search latency exceeds 200 ms over a rolling 5-minute window, sets `relaxation_disabled = true`.

### 2.2 Primary Retrieval Engine
- **Function:** Executes standard BM25 multi-field search requiring all query tokens (Boolean conjunction).
- **Timeout Budget:** 120 ms hard ceiling.
- **Output:** Exact match count (`strict_result_count`) and initial product IDs.

### 2.3 Automated Query Relaxation Engine
- **Trigger:** Activates if `variant == 'treatment'`, `token_count >= 4`, and `strict_result_count < 3`.
- **Function:** Tokenizes query, looks up catalog lexicon metadata, preserves product category nouns, ranks modifiers by Document Frequency (DF), and removes the lowest-value token.
- **Latency Budget:** Maximum 15 ms CPU execution.

### 2.4 Fallback Retrieval Service
- **Function:** Dispatches a secondary search query containing the remaining $N-1$ tokens.
- **Relevance Gate:** Validates candidate items against a minimum BM25 score threshold ($> 0.40$). Discards poor-quality matches.
- **Timeout Budget:** Maximum 40 ms execution.

### 2.5 Response Formatter & Banner Generator
- **Function:** Combines candidate products, populates the `relaxation_context` payload, injects the user-facing transparency copy, and formats the unified JSON response.

---

## 3. Data Contracts & API Schemas

### 3.1 Search Request Payload (`POST /api/v1/search`)
```json
{
  "query_text": "men black slim cotton shirt",
  "session_id": "sess_89f02c4b119a",
  "user_id": "usr_990142fa",
  "device": "mobile_web",
  "filters": {},
  "force_strict": false
}
```

### 3.2 Search Response Payload (`200 OK`)
```json
{
  "search_id": "sch_01HXYZ789BCA",
  "query_metadata": {
    "original_query": "men black slim cotton shirt",
    "token_count": 5,
    "strict_result_count": 0,
    "is_relaxed": true,
    "relaxed_query": "men black cotton shirt",
    "dropped_tokens": ["slim"],
    "relaxation_strategy": "drop_least_selective_modifier"
  },
  "experiment_metadata": {
    "experiment_id": "EXP-01",
    "variant": "treatment",
    "is_eligible": true
  },
  "transparency_banner": {
    "show_banner": true,
    "banner_type": "relaxed_results",
    "headline": "We couldn't find exact matches for all terms.",
    "body_text": "Showing closest matches for 'men black cotton shirt' with 'slim' removed.",
    "override_action": {
      "text": "Search anyway for exact 'men black slim cotton shirt'",
      "target_url": "/search?q=men+black+slim+cotton+shirt&force_strict=true"
    }
  },
  "performance": {
    "primary_latency_ms": 78,
    "relaxation_latency_ms": 32,
    "total_latency_ms": 110
  },
  "results_count": 14,
  "products": [
    {
      "product_id": "prod_882190",
      "title": "Men's Black 100% Cotton Formal Shirt",
      "brand": "Arrow",
      "category": "Shirts",
      "price": 49.99,
      "in_stock": true,
      "relevance_score": 0.88,
      "match_tier": "relaxed_match"
    }
  ]
}
```

---

## 4. Algorithmic Pseudocode: Query Relaxation Engine

```python
def process_search_query(request, catalog_lexicon, search_index):
    start_time = current_timestamp_ms()
    tokens = normalize_and_tokenize(request.query_text)
    token_count = len(tokens)
    
    # 1. Determine Experiment Assignment
    variant = evaluate_experiment_variant(request.session_id, flag="search_query_relaxation_v1")
    
    # 2. Execute Primary Strict Retrieval
    strict_results = search_index.execute_strict_conjunction(tokens, timeout_ms=120)
    primary_latency = current_timestamp_ms() - start_time
    strict_count = len(strict_results)
    
    # 3. Check Eligibility Gate
    is_eligible = (token_count >= 4) and (strict_count < 3)
    
    if not is_eligible or variant == "control" or request.force_strict:
        # Standard return path (Control Arm or >=3 hits or Forced Strict)
        emit_telemetry(request, variant, is_eligible, is_relaxed=False, 
                       strict_count=strict_count, primary_latency=primary_latency)
        return format_standard_response(strict_results, strict_count)
        
    # 4. Automated Relaxation Engine (Treatment Arm)
    relaxation_start = current_timestamp_ms()
    
    # Classify tokens into Category, Explicit Attribute, and Modifiers
    classified_tokens = []
    for token in tokens:
        entity_type = catalog_lexicon.get_entity_type(token) # CATEGORY, COLOR, BRAND, MODIFIER, UNKNOWN
        doc_frequency = catalog_lexicon.get_document_frequency(token)
        classified_tokens.append({
            "token": token,
            "type": entity_type,
            "df": doc_frequency
        })
        
    # Heuristic Token Protection & Selection
    # Rule A: NEVER drop the primary CATEGORY token if identifiable
    candidate_tokens_to_drop = [t for t in classified_tokens if t["type"] != "CATEGORY"]
    
    if not candidate_tokens_to_drop:
        # Edge Case: All tokens appear to be category nouns; drop rightmost token
        candidate_tokens_to_drop = classified_tokens[1:]
        
    # Rule B: Drop token with HIGHEST document frequency (least selective modifier)
    # Prefer dropping MODIFIER or UNKNOWN over explicit BRAND or COLOR
    candidate_tokens_to_drop.sort(key=lambda x: (x["type"] in ["BRAND", "COLOR"], -x["df"]))
    token_to_drop = candidate_tokens_to_drop[0]["token"]
    
    relaxed_tokens = [t["token"] for t in classified_tokens if t["token"] != token_to_drop]
    relaxed_query_text = " ".join(relaxed_tokens)
    
    # 5. Execute Fallback Retrieval
    fallback_candidates = search_index.execute_relaxed_query(relaxed_tokens, timeout_ms=40)
    
    # 6. Apply Minimum Relevance Floor Filter (relevance score > 0.40 (proposed threshold to be calibrated offline))
    filtered_results = [p for p in fallback_candidates if p.bm25_score >= 0.40]
    
    relaxation_latency = current_timestamp_ms() - relaxation_start
    total_latency = current_timestamp_ms() - start_time
    
    # 7. Format Hybrid Presentation based on Subgroup
    if strict_count > 0:
        # Subgroup B (1-2 strict hits): Merge exact hits at top, relaxed below
        final_products = merge_strict_and_relaxed(strict_results, filtered_results)
    else:
        # Subgroup A (0 strict hits): Pure relaxed hit set
        final_products = filtered_results
        
    emit_telemetry(request, variant, is_eligible, is_relaxed=True,
                   original_query=request.query_text, relaxed_query=relaxed_query_text,
                   dropped_tokens=[token_to_drop], strict_count=strict_count,
                   fallback_count=len(filtered_results), total_latency=total_latency)
                   
    return format_relaxed_response(
        products=final_products,
        original_query=request.query_text,
        relaxed_query=relaxed_query_text,
        dropped_token=token_to_drop,
        strict_count=strict_count,
        total_latency=total_latency
    )
```

---

## 5. Low-Result Subgroup Handling

The 941 historical eligible queries in DuckDB decompose into two distinct behavioral subgroups:

| Subgroup | Criteria | Canonical Volume | % of Eligible | Target Presentation Behavior |
|:---|:---|:---:|:---:|:---|
| **Subgroup A: Zero Results** | `results_count == 0` | **898 searches** | **95.4%** | Full relaxation. Replaces empty screen with up to 20 curated relaxed items and prominent header: *"We couldn't find exact matches for all terms. Showing closest matches for [Relaxed Query]"*. |
| **Subgroup B: 1?2 Results** | `results_count IN (1, 2)` | **43 searches** | **4.6%** | Hybrid presentation. Pins the 1?2 exact matches at top with "Exact Matches" badge; renders relaxed items below under divider: *"You may also like these close matches (with [term] excluded)"*. |

---

## 6. Latency Budget & Circuit Breaker Architecture

```
Search API Latency SLA Budget: p95 < 250 ms
+-----------------------------------------------------------------------------------------+
| [Gateway & Auth]  | [Primary Search] | [Relaxation Engine] | [Fallback] | [Serialization] |
|     15 ms         |      120 ms      |        15 ms        |   40 ms    |      10 ms      |
+-----------------------------------------------------------------------------------------+
Total Worst-Case Execution Budget: 200 ms (Well below 250 ms p95 SLA)
```

### Circuit Breaker Rules:
1. **Primary Timeout Circuit Breaker:** If primary retrieval execution exceeds **120 ms**, the system aborts relaxation fallback immediately and returns strict results.
2. **Search Gateway Circuit Breaker:** If search gateway rolling average latency exceeds **200 ms** or search cluster CPU exceeds **85%**, dynamic config automatically disables relaxation globally (`force_bypass_relaxation = true`).
3. **Fail-Safe Fallback:** Any unhandled exception thrown in the relaxation worker is swallowed, logged to Sentry, and the standard strict response is returned seamlessly.

---

## 7. Telemetry & Analytics Event Schema

All eligible search events emit an enriched telemetry payload to Kafka topic `search_relaxation_exposure`:

```json
{
  "$schema": "https://schemas.ecommerce.internal/events/search_relaxation_exposure.v1.json",
  "event_id": "evt_01HXYZ99AA",
  "timestamp": "2026-09-11T15:20:00.123Z",
  "experiment_id": "EXP-01",
  "variant": "treatment",
  "is_eligible": true,
  "session_id": "sess_89f02c4b119a",
  "user_id": "usr_990142fa",
  "device": "mobile_web",
  "query_metadata": {
    "query_id": "sch_01HXYZ789BCA",
    "raw_query": "men black slim cotton shirt",
    "normalized_tokens": ["men", "black", "slim", "cotton", "shirt"],
    "token_count": 5,
    "strict_result_count": 0,
    "subgroup": "A_zero_results"
  },
  "relaxation_metadata": {
    "is_relaxed": true,
    "relaxed_query": "men black cotton shirt",
    "dropped_tokens": ["slim"],
    "token_heuristic": "highest_df_modifier",
    "fallback_candidate_count": 18,
    "filtered_candidate_count": 14,
    "min_relevance_score": 0.54,
    "max_relevance_score": 0.88
  },
  "performance_telemetry": {
    "primary_latency_ms": 78,
    "relaxation_latency_ms": 32,
    "total_latency_ms": 110,
    "circuit_breaker_triggered": false
  }
}
```

### Downstream Attribution Linkage
When a user clicks a product on the search page, the resulting `product_views` event must include:
- `search_id`: Direct foreign key to `search_relaxation_exposure.query_metadata.query_id`.
- `result_position`: Ordinal rank on search grid (1 to 20).
- `is_relaxed_result`: Boolean (`true` if item originated from fallback retrieval).
- `view_duration_seconds`: Active time spent on PDP (for quick-back bounce calculation).

---

## 8. Feature Flagging & Emergency Rollback Protocol

The feature flag `search_query_relaxation_v1` is hosted on LaunchDarkly / Unleash and evaluated in-process:

```json
{
  "key": "search_query_relaxation_v1",
  "enabled": true,
  "default_variant": "control",
  "rules": [
    {
      "comment": "EXP-01 A/B Experiment Allocation",
      "percentage_split": {
        "control": 50,
        "treatment": 50
      },
      "hash_key": "session_id"
    }
  ],
  "parameters": {
    "min_token_count": 4,
    "max_strict_results_threshold": 3,
    "primary_timeout_ms": 120,
    "fallback_timeout_ms": 40,
    "min_relevance_floor": 0.40
  }
}
```

### Emergency Kill-Switch Protocol:
In the event that p95 latency exceeds 250 ms, client crash rate spikes, or quick-back rate increases by $> 1.5	ext{ pp}$, the On-Call Engineering Lead shall execute:
1. Open Feature Flag Console $	o$ Set `enabled = false`.
2. Propagation SLA: In-memory cache invalidated across all cluster nodes within **$< 30	ext{ seconds}$**.
3. Fallback state: System immediately reverts 100% of traffic to status quo strict search. No deployment required.

---

