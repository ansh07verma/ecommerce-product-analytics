-- ==============================================================================
-- 04_product_analysis.sql
-- Business Performance & Revenue Contribution Analysis
-- Analyzes AOV, order distribution, search-driven GMV, and potential impact
-- Demonstrates: Revenue aggregations, join across funnels, simple scenario models
-- ==============================================================================

-- 1. Overall Marketplace Revenue & Average Order Value (AOV)
SELECT
    COUNT(*) AS total_orders,
    ROUND(SUM(gross_merchandise_value), 2) AS total_gmv,
    ROUND(AVG(gross_merchandise_value), 2) AS overall_aov,
    ROUND(SUM(net_paid_amount), 2) AS total_net_revenue
FROM orders;

-- 2. Revenue Contribution: Search-Engaged vs Browse Sessions
SELECT
    CASE WHEN s.has_search = 1 THEN 'Search-Engaged Sessions' ELSE 'Browse-Only Sessions' END AS session_type,
    COUNT(o.order_id) AS total_orders,
    ROUND(SUM(o.gross_merchandise_value), 2) AS gmv,
    ROUND(100.0 * SUM(o.gross_merchandise_value) / (SELECT SUM(gross_merchandise_value) FROM orders), 2) AS gmv_share_pct,
    ROUND(AVG(o.gross_merchandise_value), 2) AS aov
FROM sessions s
JOIN orders o ON s.session_id = o.session_id
GROUP BY s.has_search
ORDER BY s.has_search DESC;

-- 3. Downstream Conversion on the 941 Eligible Low-Result Search Cohort
SELECT
    COUNT(DISTINCT s.search_id) AS eligible_searches,
    COUNT(DISTINCT CASE WHEN s.has_pdp_click = 1 THEN s.search_id END) AS pdp_clicks,
    COUNT(DISTINCT c.cart_item_id) AS cart_additions,
    COUNT(DISTINCT o.order_id) AS completed_orders,
    ROUND(SUM(o.gross_merchandise_value), 2) AS observed_gmv,
    ROUND(SUM(o.gross_merchandise_value) / NULLIF(COUNT(DISTINCT o.order_id), 0), 2) AS cohort_aov,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN s.has_pdp_click = 1 THEN s.search_id END) / COUNT(DISTINCT s.search_id), 2) AS baseline_ctr_pct,
    ROUND(100.0 * COUNT(DISTINCT c.cart_item_id) / NULLIF(COUNT(DISTINCT CASE WHEN s.has_pdp_click = 1 THEN s.search_id END), 0), 2) AS pdp_to_cart_pct,
    ROUND(100.0 * COUNT(DISTINCT o.order_id) / NULLIF(COUNT(DISTINCT c.cart_item_id), 0), 2) AS cart_to_order_pct
FROM search_events s
LEFT JOIN product_views v ON s.search_id = v.search_id
LEFT JOIN cart_events c ON v.view_id = c.view_id
LEFT JOIN orders o ON c.order_id = o.order_id
WHERE (LENGTH(TRIM(s.query_text)) - LENGTH(REPLACE(TRIM(s.query_text), ' ', '')) + 1) >= 4
  AND s.results_count < 3;

-- 4. Simple Scenario-Based Impact Estimates (Modeled)
-- If query relaxation recovers 91.81% of eligible searches (863.9 recovered):
-- Scenario A: +1.0 pp CTR lift -> +8.6 clicks -> +2.1 carts -> +0.6 orders -> +.95 / 60d -> +.77 / yr [Modeled]
-- Scenario B: +3.5 pp CTR lift -> +30.2 clicks -> +7.3 carts -> +2.1 orders -> +.32 / 60d -> +,808.69 / yr [Modeled]
