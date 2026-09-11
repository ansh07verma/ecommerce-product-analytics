-- ==============================================================================
-- SQL Suite: 07_user_segmentation.sql
-- Business Question: How do user cohorts (New vs Returning, Loyalty Tier, Acquisition Channel)
--                    perform across the conversion funnel?
-- Metrics:
--   - Cohort Sessions & Share
--   - Search Adoption Rate
--   - PDP View Rate
--   - Add-to-Cart Rate (ATCR)
--   - Cart-to-Order Conversion Rate
--   - Blended Funnel Conversion Rate
--   - Average Order Value (AOV)
--   - Total Gross Revenue
-- Filtering: Minimum sample size threshold (N >= 100 sessions)
-- ==============================================================================

-- 1. Performance by User Type & Loyalty Tier
SELECT
    u.user_type,
    u.user_tier,
    COUNT(DISTINCT s.session_id) AS total_sessions,
    COUNT(DISTINCT se.session_id) AS search_sessions,
    COUNT(DISTINCT pv.session_id) AS pdp_sessions,
    COUNT(DISTINCT ce.session_id) AS cart_sessions,
    COUNT(DISTINCT o.session_id) AS order_sessions,
    ROUND(100.0 * COUNT(DISTINCT se.session_id) / COUNT(DISTINCT s.session_id), 2) AS search_adoption_pct,
    ROUND(100.0 * COUNT(DISTINCT ce.session_id) / NULLIF(COUNT(DISTINCT pv.session_id), 0), 2) AS pdp_to_cart_rate_pct,
    ROUND(100.0 * COUNT(DISTINCT o.session_id) / NULLIF(COUNT(DISTINCT ce.session_id), 0), 2) AS cart_to_order_rate_pct,
    ROUND(100.0 * COUNT(DISTINCT o.session_id) / COUNT(DISTINCT s.session_id), 2) AS session_conversion_pct,
    ROUND(AVG(o.gross_merchandise_value), 2) AS aov,
    ROUND(SUM(o.gross_merchandise_value), 2) AS total_gross_revenue
FROM users u
JOIN sessions s ON u.user_id = s.user_id
LEFT JOIN search_events se ON s.session_id = se.session_id
LEFT JOIN product_views pv ON s.session_id = pv.session_id
LEFT JOIN cart_events ce ON s.session_id = ce.session_id
LEFT JOIN orders o ON s.session_id = o.session_id
GROUP BY u.user_type, u.user_tier
ORDER BY u.user_type, u.user_tier;

-- 2. Performance by User Acquisition Channel
SELECT
    u.acquisition_channel,
    COUNT(DISTINCT s.session_id) AS total_sessions,
    ROUND(100.0 * COUNT(DISTINCT se.session_id) / COUNT(DISTINCT s.session_id), 2) AS search_adoption_pct,
    ROUND(100.0 * COUNT(DISTINCT ce.session_id) / NULLIF(COUNT(DISTINCT pv.session_id), 0), 2) AS pdp_to_cart_rate_pct,
    ROUND(100.0 * COUNT(DISTINCT o.session_id) / NULLIF(COUNT(DISTINCT ce.session_id), 0), 2) AS cart_to_order_rate_pct,
    ROUND(100.0 * COUNT(DISTINCT o.session_id) / COUNT(DISTINCT s.session_id), 2) AS session_conversion_pct,
    ROUND(AVG(o.gross_merchandise_value), 2) AS aov,
    ROUND(SUM(o.gross_merchandise_value), 2) AS total_gross_revenue
FROM users u
JOIN sessions s ON u.user_id = s.user_id
LEFT JOIN search_events se ON s.session_id = se.session_id
LEFT JOIN product_views pv ON s.session_id = pv.session_id
LEFT JOIN cart_events ce ON s.session_id = ce.session_id
LEFT JOIN orders o ON s.session_id = o.session_id
GROUP BY u.acquisition_channel
HAVING COUNT(DISTINCT s.session_id) >= 100
ORDER BY total_sessions DESC;
