# Product Recommendation: E-Commerce Search Query Relaxation

**To**: Product & Engineering Leadership  
**From**: Product Analytics Team  
**Subject**: Recommendation to Test Automated Query Relaxation for Multi-Attribute Searches  
**Date**: September 2026  

---

## 1. Executive Summary

Our funnel analysis of 32,245 search events across 31,328 customer sessions revealed that search-engaged shoppers are our most valuable segment, converting at **11.92% vs. 5.16% for browse shoppers**.

However, high-intent shoppers entering specific multi-attribute queries ($\ge 4$ words) face severe discovery breakdown:
- **8.23% Zero-Result Rate (ZRR)**, 4.6x higher than short head queries (1.78%).
- **44.39% manual reformulation rate**, showing high customer struggle.
- **3.08% Search-to-PDP Click-Through Rate (CTR)** on the 941 low-result searches.

To resolve this friction, we prototyped **Automated Query Relaxation**, an algorithmic fallback that safely removes overly restrictive modifiers while protecting core category nouns and active inventory. In local testing, it recovered **91.81% of unmatchable queries**.

**Recommendation**: Deploy query relaxation as a lightweight in-memory fallback within our existing application layer and run a 50/50 A/B canary test to validate live customer conversion before committing to larger search infrastructure investments.

---

## 2. Problem Diagnosis: Over-Specification Friction

When shoppers type detailed queries like *"slim fit black dresses XL"* or *"vintage black jeans L"*, our current search requires every single word to match catalog metadata. Even though we carry dresses in size XL and vintage jeans in size L, the presence of non-essential modifiers (e.g., specific colors or stylistic adjectives) causes strict boolean search to return zero items.

This friction directly damages commercial performance:
- Over 60 days, **941 searches** returned fewer than 3 items.
- Only **29 searches (3.08%)** progressed to a Product Detail Page (PDP).
- High-intent shoppers re-typed their queries **44.39% of the time** or abandoned their sessions.

---

## 3. Recommended Intervention: Automated Query Relaxation

Rather than forcing users to learn our internal catalog vocabulary, the search service should preserve user intent while relaxing non-essential modifiers:

1. **Trigger Condition**: Executes only when a query has $\ge 4$ tokens AND strict search returns $< 3$ in-stock results.
2. **Category Protection**: Core merchandise nouns (*"dress"*, *"jeans"*, *"jacket"*, *"shoes"*) are permanently protected and cannot be dropped.
3. **Safe Modifier Relaxation**: Non-category modifiers (colors, fabrics, occasions) are relaxed one at a time, ensuring at least 2 tokens remain.
4. **Transparent Presentation**: The UI clearly explains the fallback: *"Showing results for 'slim fit dress xl' (relaxed: black)"*.

---

## 4. Proposed A/B Experiment Design

We propose validating this feature through a controlled production experiment:

- **Target Audience**: Users submitting queries with $\ge 4$ tokens where strict search returns $< 3$ results.
- **Variant A (Control)**: Current strict keyword search (shows existing results or standard zero-result page).
- **Variant B (Treatment)**: Strict search + Automated Query Relaxation fallback.
- **Primary Metric**: **Search $	o$ PDP Click-Through Rate (CTR)** on eligible queries.
- **Secondary Metrics**: Zero-Result Rate (ZRR) and Query Reformulation Rate.
- **Guardrail Metrics**: Category consistency audit, PDP bounce rate (quick-backs < 5s), and out-of-stock display rate.
- **Hypothesis**: Treatment will improve Search $	o$ PDP CTR by at least **+1.5 percentage points** ($p < 0.05$).

---

## 5. Financial Sizing & Capital Discipline

Using our empirical downstream conversion rates ($P(	ext{Cart}|	ext{PDP}) = 24.14\%$, $P(	ext{Order}|	ext{Cart}) = 28.57\%$, $	ext{AOV} = \$142.58$):

| Scenario | Modeled CTR Lift | 60-Day Incremental GMV | Annualized Incremental GMV |
| :--- | :---: | :---: | :---: |
| **Scenario A (Conservative)** | +1.0 pp | +$84.95 | **+$516.77 / year** [Modeled] |
| **Scenario B (Target)** | +3.5 pp | +$297.32 | **+$1,808.69 / year** [Modeled] |

### The Capital Discipline Principle
At our current boutique search volume (~16 eligible searches/day), the standalone revenue return is modest (~$1,800/year). 
- **What NOT to do**: We should **not** invest in expensive third-party search platforms or dedicated cloud search clusters.
- **What TO do**: Our prototype is lightweight Python logic that runs within existing application compute with no external API fees. We should deploy it as a low-risk experiment. If the A/B test proves customer conversion, we can scale the solution as marketplace traffic grows.

---

## 6. Action Plan & Next Steps

1. **Sprint 1**: Integrate Python query-relaxation fallback function into search backend.
2. **Sprint 2**: Add frontend explainability banner (*"Showing results for..."*).
3. **Sprint 3**: Launch 50/50 randomized A/B canary experiment.
4. **Evaluation Milestone**: Review Search $	o$ PDP CTR lift and guardrail metrics after target sample size is reached.
