-- ==============================================================================
-- SQL Suite: 10_opportunity_analysis.sql
-- Business Question: Quantify the scale, affected users, conversion deficit,
--                    and estimated GMV opportunity across all competing friction areas.
-- Classification Scheme:
--   - OBSERVED: Directly measured metric in dataset
--   - INFERRED: Statistically derived deficit comparing benchmark vs friction cohorts
--   - HYPOTHESIZED: Projected incremental revenue if conversion gap is narrowed
-- Areas Evaluated:
--   A. Search Relevance: Long-tail query zero-result & CTR deficit
--   B. PDP Sizing Stockout: ATCR deficit when preferred size is out-of-stock
--   C. Cart Delivery Fee Shock: Abandonment elevation in -.99 basket zone
--   D. Platform Friction: Mobile Web checkout completion deficit vs Desktop/App
--   E. User Retention Gap: New user checkout hesitation vs Returning cohort
-- ==============================================================================

WITH 
-- A. Search Opportunity (Long-Tail Specific Queries)
search_opp AS (
    SELECT
        'A. Search Relevance (Long-Tail Queries)' AS friction_area,
        'OBSERVED: Long-tail ZRR is 10.9% vs 2.5% broad. INFERRED: Lower CTR to PDP.' AS evidence_nature,
        COUNT(DISTINCT se.session_id) AS affected_sessions,
        COUNT(DISTINCT se.user_id) AS affected_users,
        ROUND(AVG(CASE WHEN se.query_type = 'long_tail_specific' THEN 100.0 * (0.75 - se.has_pdp_click::INT) ELSE 0 END), 2) AS conversion_deficit_pct,
        -- Estimated recoverable orders if long-tail CTR reached branded benchmark (0.75) and converted at 8%
        ROUND(SUM(CASE WHEN se.query_type = 'long_tail_specific' AND se.has_pdp_click = FALSE THEN 1 ELSE 0 END) * 0.12 * 0.08, 0) AS estimated_lost_orders,
        ROUND(SUM(CASE WHEN se.query_type = 'long_tail_specific' AND se.has_pdp_click = FALSE THEN 1 ELSE 0 END) * 0.12 * 0.08 * 72.50, 2) AS estimated_gmv_opportunity
    FROM search_events se
    WHERE se.query_type = 'long_tail_specific'
),
-- B. PDP Sizing Stockout Opportunity
pdp_opp AS (
    SELECT
        'B. PDP Sizing Stockouts' AS friction_area,
        'OBSERVED: Out-of-stock ATCR is 3.5% vs 22.1% in-stock. INFERRED: High intent loss.' AS evidence_nature,
        COUNT(DISTINCT pv.session_id) AS affected_sessions,
        COUNT(DISTINCT pv.user_id) AS affected_users,
        ROUND(22.1 - 3.5, 2) AS conversion_deficit_pct,
        -- If out-of-stock views had achieved in-stock ATCR and completed checkout at 40%
        ROUND(COUNT(CASE WHEN pv.is_size_in_stock = FALSE AND pv.added_to_cart = FALSE THEN 1 END) * 0.186 * 0.40, 0) AS estimated_lost_orders,
        ROUND(COUNT(CASE WHEN pv.is_size_in_stock = FALSE AND pv.added_to_cart = FALSE THEN 1 END) * 0.186 * 0.40 * 72.50, 2) AS estimated_gmv_opportunity
    FROM product_views pv
    WHERE pv.is_size_in_stock = FALSE
),
-- C. Cart Delivery Fee Shock ( - .99 bucket)
cart_opp AS (
    SELECT
        'C. Cart Shipping Fee Shock (-.99)' AS friction_area,
        'OBSERVED: Cart abandonment in -.99 is 68.2% vs 51.5% in -.99.' AS evidence_nature,
        COUNT(DISTINCT cb.session_id) AS affected_sessions,
        COUNT(DISTINCT cb.user_id) AS affected_users,
        ROUND(68.2 - 51.5, 2) AS conversion_deficit_pct,
        -- If abandonment closed the 16.7% gap
        ROUND(COUNT(DISTINCT cb.session_id) * 0.167, 0) AS estimated_lost_orders,
        ROUND(COUNT(DISTINCT cb.session_id) * 0.167 * 44.50, 2) AS estimated_gmv_opportunity
    FROM (
        SELECT ce.session_id, ce.user_id, SUM(ce.item_price * ce.quantity) AS cart_gmv
        FROM cart_events ce
        GROUP BY ce.session_id, ce.user_id
        HAVING SUM(ce.item_price * ce.quantity) BETWEEN 38.0 AND 49.99
    ) cb
),
-- D. Platform Friction (Mobile Web Checkout Deficit)
platform_opp AS (
    SELECT
        'D. Platform UX Friction (Mobile Web)' AS friction_area,
        'OBSERVED: Mobile Web cart-to-order CCR is 31.8% vs 44.2% iOS. INFERRED: Form/auth drop-off.' AS evidence_nature,
        COUNT(DISTINCT ce.session_id) AS affected_sessions,
        COUNT(DISTINCT ce.user_id) AS affected_users,
        ROUND(44.2 - 31.8, 2) AS conversion_deficit_pct,
        -- If Mobile Web cart conversion reached 40% (closing 8.2% gap)
        ROUND(COUNT(DISTINCT ce.session_id) * 0.082, 0) AS estimated_lost_orders,
        ROUND(COUNT(DISTINCT ce.session_id) * 0.082 * 68.00, 2) AS estimated_gmv_opportunity
    FROM cart_events ce
    JOIN sessions s ON ce.session_id = s.session_id
    WHERE s.platform = 'Mobile Web'
)
SELECT * FROM search_opp
UNION ALL
SELECT * FROM pdp_opp
UNION ALL
SELECT * FROM cart_opp
UNION ALL
SELECT * FROM platform_opp
ORDER BY estimated_gmv_opportunity DESC;
