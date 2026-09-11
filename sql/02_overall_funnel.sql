-- ==============================================================================
-- SQL Suite: 02_overall_funnel.sql
-- Business Question: Where does the customer journey lose the most sessions across
--                    the overall platform, and how does search-driven conversion
--                    compare to direct browsing?
-- Metrics:
--   - Funnel A: Blended Platform Funnel (Total -> PDP -> Cart -> Order)
--   - Funnel B: Pure Search-Driven Funnel (Search -> Search-PDP -> Search-Cart -> Search-Order)
--   - Funnel C: Direct Browse Funnel (Non-Search -> Browse-PDP -> Browse-Cart -> Browse-Order)
-- Notes:
--   - DISTINCT session_id used across all stages.
--   - Avoids false denominator distortion between multi-path stages.
-- ==============================================================================

-- 1. Master Funnel Ratios & Stage Breakdown
WITH session_flags AS (
    SELECT
        s.session_id,
        MAX(CASE WHEN se.session_id IS NOT NULL THEN 1 ELSE 0 END) AS is_search_session,
        MAX(CASE WHEN pv.session_id IS NOT NULL THEN 1 ELSE 0 END) AS is_pdp_session,
        MAX(CASE WHEN pv.search_id IS NOT NULL THEN 1 ELSE 0 END) AS is_search_pdp_session,
        MAX(CASE WHEN ce.session_id IS NOT NULL THEN 1 ELSE 0 END) AS is_cart_session,
        MAX(CASE WHEN o.session_id IS NOT NULL THEN 1 ELSE 0 END) AS is_order_session
    FROM sessions s
    LEFT JOIN search_events se ON s.session_id = se.session_id
    LEFT JOIN product_views pv ON s.session_id = pv.session_id
    LEFT JOIN cart_events ce ON s.session_id = ce.session_id
    LEFT JOIN orders o ON s.session_id = o.session_id
    GROUP BY s.session_id
),
overall_funnel AS (
    SELECT
        COUNT(*) AS total_sessions,
        SUM(is_search_session) AS search_sessions,
        SUM(is_pdp_session) AS pdp_sessions,
        SUM(is_cart_session) AS cart_sessions,
        SUM(is_order_session) AS order_sessions,
        SUM(CASE WHEN is_search_session = 1 AND is_pdp_session = 1 THEN 1 ELSE 0 END) AS search_with_pdp,
        SUM(CASE WHEN is_search_session = 1 AND is_cart_session = 1 THEN 1 ELSE 0 END) AS search_with_cart,
        SUM(CASE WHEN is_search_session = 1 AND is_order_session = 1 THEN 1 ELSE 0 END) AS search_with_order,
        SUM(CASE WHEN is_search_session = 0 AND is_pdp_session = 1 THEN 1 ELSE 0 END) AS browse_with_pdp,
        SUM(CASE WHEN is_search_session = 0 AND is_cart_session = 1 THEN 1 ELSE 0 END) AS browse_with_cart,
        SUM(CASE WHEN is_search_session = 0 AND is_order_session = 1 THEN 1 ELSE 0 END) AS browse_with_order
    FROM session_flags
)
SELECT
    '1. Blended Platform Funnel' AS funnel_type,
    total_sessions AS stage_1_sessions,
    pdp_sessions AS stage_2_sessions,
    cart_sessions AS stage_3_sessions,
    order_sessions AS stage_4_sessions,
    ROUND(100.0 * pdp_sessions / total_sessions, 2) AS stage_1_to_2_conv_pct,
    ROUND(100.0 * cart_sessions / pdp_sessions, 2) AS stage_2_to_3_conv_pct,
    ROUND(100.0 * order_sessions / cart_sessions, 2) AS stage_3_to_4_conv_pct,
    ROUND(100.0 * order_sessions / total_sessions, 2) AS overall_session_conversion_pct
FROM overall_funnel

UNION ALL

SELECT
    '2. Pure Search-Driven Funnel' AS funnel_type,
    search_sessions AS stage_1_sessions,
    search_with_pdp AS stage_2_sessions,
    search_with_cart AS stage_3_sessions,
    search_with_order AS stage_4_sessions,
    ROUND(100.0 * search_with_pdp / search_sessions, 2) AS stage_1_to_2_conv_pct,
    ROUND(100.0 * search_with_cart / search_with_pdp, 2) AS stage_2_to_3_conv_pct,
    ROUND(100.0 * search_with_order / search_with_cart, 2) AS stage_3_to_4_conv_pct,
    ROUND(100.0 * search_with_order / search_sessions, 2) AS overall_session_conversion_pct
FROM overall_funnel

UNION ALL

SELECT
    '3. Direct Browse Funnel' AS funnel_type,
    (total_sessions - search_sessions) AS stage_1_sessions,
    browse_with_pdp AS stage_2_sessions,
    browse_with_cart AS stage_3_sessions,
    browse_with_order AS stage_4_sessions,
    ROUND(100.0 * browse_with_pdp / (total_sessions - search_sessions), 2) AS stage_1_to_2_conv_pct,
    ROUND(100.0 * browse_with_cart / browse_with_pdp, 2) AS stage_2_to_3_conv_pct,
    ROUND(100.0 * browse_with_order / browse_with_cart, 2) AS stage_3_to_4_conv_pct,
    ROUND(100.0 * browse_with_order / (total_sessions - search_sessions), 2) AS overall_session_conversion_pct
FROM overall_funnel;

-- 2. Step-by-Step Drop-Off Breakdown (Blended Funnel)
WITH step_metrics AS (
    SELECT
        1 AS step_order, '1. Total Sessions to PDP View' AS step_name,
        COUNT(DISTINCT s.session_id) AS start_sessions,
        COUNT(DISTINCT pv.session_id) AS end_sessions
    FROM sessions s
    LEFT JOIN product_views pv ON s.session_id = pv.session_id
    UNION ALL
    SELECT
        2, '2. PDP View to Add-to-Cart',
        COUNT(DISTINCT pv.session_id),
        COUNT(DISTINCT ce.session_id)
    FROM product_views pv
    LEFT JOIN cart_events ce ON pv.session_id = ce.session_id
    UNION ALL
    SELECT
        3, '3. Add-to-Cart to Order Completed',
        COUNT(DISTINCT ce.session_id),
        COUNT(DISTINCT o.session_id)
    FROM cart_events ce
    LEFT JOIN orders o ON ce.session_id = o.session_id
)
SELECT
    step_order,
    step_name,
    start_sessions,
    end_sessions,
    ROUND(100.0 * end_sessions / start_sessions, 2) AS step_conversion_pct,
    ROUND(100.0 * (1.0 - (end_sessions * 1.0 / start_sessions)), 2) AS step_dropoff_pct,
    (start_sessions - end_sessions) AS absolute_sessions_lost
FROM step_metrics
ORDER BY step_order;
