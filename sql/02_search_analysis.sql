-- ==============================================================================
-- 02_search_analysis.sql
-- Search Behavior & Discovery Failure Analysis
-- Analyzes query length, zero-result rates (ZRR), reformulation, and CTR
-- Demonstrates: String functions, conditional aggregation, ratio calculations
-- ==============================================================================

-- 1. Query Length Segmentation: 1-3 Tokens vs 4+ Tokens
WITH query_metrics AS (
    SELECT
        search_id,
        session_id,
        query_text,
        results_count,
        is_zero_result,
        reformulated_in_session,
        has_pdp_click,
        LENGTH(TRIM(query_text)) - LENGTH(REPLACE(TRIM(query_text), ' ', '')) + 1 AS token_count,
        CASE
            WHEN LENGTH(TRIM(query_text)) - LENGTH(REPLACE(TRIM(query_text), ' ', '')) + 1 >= 4 THEN '4+ Tokens (Specific)'
            ELSE '1-3 Tokens (Head/Torso)'
        END AS query_length_segment
    FROM search_events
)
SELECT
    query_length_segment,
    COUNT(*) AS total_searches,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM search_events), 2) AS query_share_pct,
    SUM(is_zero_result) AS zero_result_searches,
    ROUND(100.0 * SUM(is_zero_result) / COUNT(*), 2) AS zero_result_rate_pct,
    SUM(reformulated_in_session) AS reformulated_searches,
    ROUND(100.0 * SUM(reformulated_in_session) / COUNT(*), 2) AS reformulation_rate_pct,
    SUM(has_pdp_click) AS searches_with_pdp_click,
    ROUND(100.0 * SUM(has_pdp_click) / COUNT(*), 2) AS search_to_pdp_ctr_pct
FROM query_metrics
GROUP BY query_length_segment
ORDER BY query_length_segment;

-- 2. The Low-Result Breakdown Cohort (< 3 Results on 4+ Token Queries)
-- Identifies the specific target cohort where search discovery breaks down
SELECT
    'Low-Result Specific Queries (<3 results, >=4 tokens)' AS cohort_name,
    COUNT(*) AS eligible_searches,
    SUM(CASE WHEN results_count = 0 THEN 1 ELSE 0 END) AS zero_result_queries,
    SUM(CASE WHEN results_count BETWEEN 1 AND 2 THEN 1 ELSE 0 END) AS low_result_queries,
    SUM(has_pdp_click) AS pdp_clicks,
    ROUND(100.0 * SUM(has_pdp_click) / COUNT(*), 2) AS search_to_pdp_ctr_pct,
    SUM(reformulated_in_session) AS reformulations,
    ROUND(100.0 * SUM(reformulated_in_session) / COUNT(*), 2) AS reformulation_rate_pct
FROM search_events
WHERE (LENGTH(TRIM(query_text)) - LENGTH(REPLACE(TRIM(query_text), ' ', '')) + 1) >= 4
  AND results_count < 3;
