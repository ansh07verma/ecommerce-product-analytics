-- ==============================================================================
-- SQL Suite: 03_search_performance.sql
-- Business Question: How do search volume, zero-result rates, reformulations,
--                    and CTR vary across query types, categories, and lengths?
-- Metrics:
--   - Search Volume (Total searches & unique search sessions)
--   - Zero Result Rate (ZRR): Searches with results_count = 0 / Total searches
--   - Query Reformulation Rate: Searches reformulated in session / Total searches
--   - Search Event CTR: Searches with >=1 PDP click / Total searches
--   - Search Session CTR: Search sessions with >=1 PDP click / Total search sessions
--   - Search-to-Order Conversion: Search sessions ending in order / Total search sessions
-- ==============================================================================

-- 1. Performance by Query Type
SELECT
    query_type,
    COUNT(*) AS total_searches,
    COUNT(DISTINCT session_id) AS unique_sessions,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT session_id), 2) AS avg_searches_per_session,
    ROUND(100.0 * SUM(CASE WHEN is_zero_result THEN 1 ELSE 0 END) / COUNT(*), 2) AS zero_result_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN reformulated_in_session THEN 1 ELSE 0 END) / COUNT(*), 2) AS reformulation_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN has_pdp_click THEN 1 ELSE 0 END) / COUNT(*), 2) AS search_ctr_pct
FROM search_events
GROUP BY query_type
ORDER BY total_searches DESC;

-- 2. Performance by Inferred Category
SELECT
    inferred_category,
    COUNT(*) AS total_searches,
    ROUND(100.0 * SUM(CASE WHEN is_zero_result THEN 1 ELSE 0 END) / COUNT(*), 2) AS zero_result_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN reformulated_in_session THEN 1 ELSE 0 END) / COUNT(*), 2) AS reformulation_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN has_pdp_click THEN 1 ELSE 0 END) / COUNT(*), 2) AS search_ctr_pct,
    ROUND(AVG(results_count), 1) AS avg_results_count
FROM search_events
GROUP BY inferred_category
ORDER BY total_searches DESC;

-- 3. Performance by Filters Applied
SELECT
    filters_used,
    COUNT(*) AS total_searches,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM search_events), 2) AS filter_share_pct,
    ROUND(100.0 * SUM(CASE WHEN is_zero_result THEN 1 ELSE 0 END) / COUNT(*), 2) AS zero_result_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN has_pdp_click THEN 1 ELSE 0 END) / COUNT(*), 2) AS search_ctr_pct
FROM search_events
GROUP BY filters_used
ORDER BY total_searches DESC;

-- 4. Performance by Query Word Count (Token Length)
SELECT
    ARRAY_LENGTH(STRING_SPLIT(TRIM(query_text), ' ')) AS token_count,
    COUNT(*) AS total_searches,
    ROUND(100.0 * SUM(CASE WHEN is_zero_result THEN 1 ELSE 0 END) / COUNT(*), 2) AS zero_result_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN reformulated_in_session THEN 1 ELSE 0 END) / COUNT(*), 2) AS reformulation_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN has_pdp_click THEN 1 ELSE 0 END) / COUNT(*), 2) AS search_ctr_pct,
    ROUND(AVG(results_count), 1) AS avg_results_returned
FROM search_events
GROUP BY ARRAY_LENGTH(STRING_SPLIT(TRIM(query_text), ' '))
ORDER BY token_count ASC;

-- 5. Search-to-Order Conversion by Primary Query Type in Session
WITH session_query_summary AS (
    SELECT
        se.session_id,
        MIN(se.query_type) AS primary_query_type,
        MAX(CASE WHEN o.order_id IS NOT NULL THEN 1 ELSE 0 END) AS has_order
    FROM search_events se
    LEFT JOIN orders o ON se.session_id = o.session_id
    GROUP BY se.session_id
)
SELECT
    primary_query_type,
    COUNT(*) AS search_sessions,
    SUM(has_order) AS order_sessions,
    ROUND(100.0 * SUM(has_order) / COUNT(*), 2) AS search_to_order_conversion_pct
FROM session_query_summary
GROUP BY primary_query_type
ORDER BY search_sessions DESC;
