-- ==============================================================================
-- 01_funnel_analysis.sql
-- E-Commerce Conversion Funnel Analysis
-- Analyzes session progression: Sessions -> Search -> PDP Views -> Carts -> Orders
-- Demonstrates: CTEs, LEFT JOINs, COUNT(DISTINCT), CASE statements, aggregations
-- ==============================================================================

-- 1. Overall Marketplace Funnel
WITH session_steps AS (
    SELECT
        s.session_id,
        s.has_search,
        MAX(CASE WHEN pv.view_id IS NOT NULL THEN 1 ELSE 0 END) AS has_pdp_view,
        MAX(CASE WHEN ce.cart_item_id IS NOT NULL THEN 1 ELSE 0 END) AS has_cart_add,
        MAX(CASE WHEN o.order_id IS NOT NULL THEN 1 ELSE 0 END) AS has_order
    FROM sessions s
    LEFT JOIN product_views pv ON s.session_id = pv.session_id
    LEFT JOIN cart_events ce ON s.session_id = ce.session_id
    LEFT JOIN orders o ON s.session_id = o.session_id
    GROUP BY s.session_id, s.has_search
)
SELECT
    'All Sessions' AS funnel_segment,
    COUNT(session_id) AS total_sessions,
    SUM(has_search) AS search_sessions,
    SUM(has_pdp_view) AS pdp_sessions,
    SUM(has_cart_add) AS cart_sessions,
    SUM(has_order) AS order_sessions,
    ROUND(100.0 * SUM(has_pdp_view) / COUNT(session_id), 2) AS session_to_pdp_pct,
    ROUND(100.0 * SUM(has_cart_add) / NULLIF(SUM(has_pdp_view), 0), 2) AS pdp_to_cart_pct,
    ROUND(100.0 * SUM(has_order) / NULLIF(SUM(has_cart_add), 0), 2) AS cart_to_order_pct,
    ROUND(100.0 * SUM(has_order) / COUNT(session_id), 2) AS overall_conversion_pct
FROM session_steps;

-- 2. Funnel Comparison: Search-Engaged vs Browse-Only Sessions
WITH session_steps AS (
    SELECT
        s.session_id,
        s.has_search,
        MAX(CASE WHEN pv.view_id IS NOT NULL THEN 1 ELSE 0 END) AS has_pdp_view,
        MAX(CASE WHEN ce.cart_item_id IS NOT NULL THEN 1 ELSE 0 END) AS has_cart_add,
        MAX(CASE WHEN o.order_id IS NOT NULL THEN 1 ELSE 0 END) AS has_order
    FROM sessions s
    LEFT JOIN product_views pv ON s.session_id = pv.session_id
    LEFT JOIN cart_events ce ON s.session_id = ce.session_id
    LEFT JOIN orders o ON s.session_id = o.session_id
    GROUP BY s.session_id, s.has_search
)
SELECT
    CASE WHEN has_search = 1 THEN 'Search-Engaged' ELSE 'Browse-Only' END AS cohort,
    COUNT(session_id) AS total_sessions,
    SUM(has_pdp_view) AS pdp_sessions,
    SUM(has_cart_add) AS cart_sessions,
    SUM(has_order) AS order_sessions,
    ROUND(100.0 * SUM(has_pdp_view) / COUNT(session_id), 2) AS session_to_pdp_pct,
    ROUND(100.0 * SUM(has_cart_add) / NULLIF(SUM(has_pdp_view), 0), 2) AS pdp_to_cart_pct,
    ROUND(100.0 * SUM(has_order) / NULLIF(SUM(has_cart_add), 0), 2) AS cart_to_order_pct,
    ROUND(100.0 * SUM(has_order) / COUNT(session_id), 2) AS overall_conversion_pct
FROM session_steps
GROUP BY has_search
ORDER BY has_search DESC;
