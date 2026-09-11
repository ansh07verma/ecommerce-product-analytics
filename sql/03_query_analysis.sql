-- ==============================================================================
-- 03_query_analysis.sql
-- Query Patterns, Categories & Over-Specification Analysis
-- Identifies specific query patterns causing zero-result discovery failures
-- Demonstrates: GROUP BY, ORDER BY, LIMIT, string filters, category aggregation
-- ==============================================================================

-- 1. Top 10 Most Frequent Queries Overall
SELECT
    query_text,
    inferred_category,
    COUNT(*) AS search_count,
    ROUND(AVG(results_count), 1) AS avg_results,
    ROUND(100.0 * SUM(is_zero_result) / COUNT(*), 1) AS zrr_pct,
    ROUND(100.0 * SUM(has_pdp_click) / COUNT(*), 1) AS ctr_pct
FROM search_events
GROUP BY query_text, inferred_category
ORDER BY search_count DESC
LIMIT 10;

-- 2. Common Multi-Attribute Queries Returning 0 Results
-- These illustrate the core problem: overly specific queries (color + fabric + style + category)
SELECT
    query_text,
    inferred_category,
    COUNT(*) AS search_count,
    SUM(reformulated_in_session) AS times_reformulated,
    ROUND(100.0 * SUM(reformulated_in_session) / COUNT(*), 1) AS reformulation_pct
FROM search_events
WHERE is_zero_result = 1
  AND (LENGTH(TRIM(query_text)) - LENGTH(REPLACE(TRIM(query_text), ' ', '')) + 1) >= 4
GROUP BY query_text, inferred_category
ORDER BY search_count DESC
LIMIT 15;

-- 3. Zero-Result Rate by Inferred Product Category
SELECT
    inferred_category,
    COUNT(*) AS total_searches,
    SUM(is_zero_result) AS zero_result_searches,
    ROUND(100.0 * SUM(is_zero_result) / COUNT(*), 2) AS zero_result_rate_pct,
    ROUND(100.0 * SUM(has_pdp_click) / COUNT(*), 2) AS ctr_pct
FROM search_events
GROUP BY inferred_category
ORDER BY total_searches DESC;
