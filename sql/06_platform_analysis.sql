-- ==============================================================================
-- SQL Suite: 06_platform_analysis.sql
-- Business Question: At which exact stage of the funnel do iOS, Android, Mobile Web,
--                    and Desktop diverge?
-- Metrics:
--   - Platform Session Share
--   - Search Adoption Rate (% sessions searching)
--   - Search Session CTR (% search sessions viewing PDP)
--   - PDP -> Cart Conversion Rate (% viewing sessions adding to cart)
--   - Cart -> Order Conversion Rate (% cart sessions ordering)
--   - End-to-End Session Conversion Rate (% all sessions ordering)
--   - Average Order Value (AOV)
--   - Average Session Duration (seconds)
-- ==============================================================================

WITH platform_funnel AS (
    SELECT
        s.platform,
        COUNT(DISTINCT s.session_id) AS total_sessions,
        COUNT(DISTINCT se.session_id) AS search_sessions,
        COUNT(DISTINCT pv.session_id) AS pdp_sessions,
        COUNT(DISTINCT ce.session_id) AS cart_sessions,
        COUNT(DISTINCT o.session_id) AS order_sessions,
        ROUND(AVG(s.session_duration_sec), 1) AS avg_duration_sec,
        ROUND(AVG(o.gross_merchandise_value), 2) AS platform_aov
    FROM sessions s
    LEFT JOIN search_events se ON s.session_id = se.session_id
    LEFT JOIN product_views pv ON s.session_id = pv.session_id
    LEFT JOIN cart_events ce ON s.session_id = ce.session_id
    LEFT JOIN orders o ON s.session_id = o.session_id
    GROUP BY s.platform
)
SELECT
    platform,
    total_sessions,
    ROUND(100.0 * total_sessions / (SELECT COUNT(*) FROM sessions), 2) AS session_share_pct,
    ROUND(100.0 * search_sessions / total_sessions, 2) AS search_adoption_pct,
    ROUND(100.0 * pdp_sessions / total_sessions, 2) AS session_pdp_rate_pct,
    ROUND(100.0 * cart_sessions / NULLIF(pdp_sessions, 0), 2) AS pdp_to_cart_rate_pct,
    ROUND(100.0 * order_sessions / NULLIF(cart_sessions, 0), 2) AS cart_to_order_rate_pct,
    ROUND(100.0 * order_sessions / total_sessions, 2) AS blended_session_conversion_pct,
    platform_aov,
    avg_duration_sec
FROM platform_funnel
ORDER BY total_sessions DESC;
