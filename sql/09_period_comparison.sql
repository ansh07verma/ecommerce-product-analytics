-- ==============================================================================
-- SQL Suite: 09_period_comparison.sql
-- Business Question: How did funnel performance evolve between Period 1 (Baseline: Days 1-28)
--                    and Period 2 (Recent: Days 29-56)?
-- Metrics:
--   - Period Session Volume
--   - Search Adoption Rate
--   - Zero Result Rate (ZRR)
--   - Query Reformulation Rate
--   - Search CTR
--   - PDP -> Cart Conversion Rate
--   - Cart -> Order Conversion Rate
--   - Blended Session Conversion Rate
--   - Average Order Value (AOV)
--   - Total Gross Merchandise Value (GMV)
-- Objective: Determine empirical changes without pre-assuming performance degradation.
-- ==============================================================================

WITH period_funnel AS (
    SELECT
        s.time_period,
        COUNT(DISTINCT s.session_id) AS total_sessions,
        COUNT(DISTINCT se.session_id) AS search_sessions,
        COUNT(DISTINCT pv.session_id) AS pdp_sessions,
        COUNT(DISTINCT ce.session_id) AS cart_sessions,
        COUNT(DISTINCT o.session_id) AS order_sessions,
        COUNT(se.search_id) AS total_searches,
        SUM(CASE WHEN se.is_zero_result THEN 1 ELSE 0 END) AS zero_result_searches,
        SUM(CASE WHEN se.reformulated_in_session THEN 1 ELSE 0 END) AS reformulated_searches,
        SUM(CASE WHEN se.has_pdp_click THEN 1 ELSE 0 END) AS clicked_searches,
        ROUND(AVG(o.gross_merchandise_value), 2) AS aov,
        ROUND(SUM(o.gross_merchandise_value), 2) AS total_gmv
    FROM sessions s
    LEFT JOIN search_events se ON s.session_id = se.session_id
    LEFT JOIN product_views pv ON s.session_id = pv.session_id
    LEFT JOIN cart_events ce ON s.session_id = ce.session_id
    LEFT JOIN orders o ON s.session_id = o.session_id
    GROUP BY s.time_period
)
SELECT
    time_period,
    total_sessions,
    total_searches,
    ROUND(100.0 * search_sessions / total_sessions, 2) AS search_adoption_pct,
    ROUND(100.0 * zero_result_searches / NULLIF(total_searches, 0), 2) AS zero_result_rate_pct,
    ROUND(100.0 * reformulated_searches / NULLIF(total_searches, 0), 2) AS reformulation_rate_pct,
    ROUND(100.0 * clicked_searches / NULLIF(total_searches, 0), 2) AS search_ctr_pct,
    ROUND(100.0 * cart_sessions / NULLIF(pdp_sessions, 0), 2) AS pdp_to_cart_rate_pct,
    ROUND(100.0 * order_sessions / NULLIF(cart_sessions, 0), 2) AS cart_to_order_rate_pct,
    ROUND(100.0 * order_sessions / total_sessions, 2) AS session_conversion_pct,
    aov,
    total_gmv
FROM period_funnel
ORDER BY time_period;

-- Period 1 vs Period 2 by Platform
SELECT
    s.platform,
    s.time_period,
    COUNT(DISTINCT s.session_id) AS sessions,
    ROUND(100.0 * COUNT(DISTINCT o.session_id) / COUNT(DISTINCT s.session_id), 2) AS conversion_rate_pct,
    ROUND(AVG(o.gross_merchandise_value), 2) AS aov
FROM sessions s
LEFT JOIN orders o ON s.session_id = o.session_id
GROUP BY s.platform, s.time_period
ORDER BY s.platform, s.time_period;
