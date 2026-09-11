-- ==============================================================================
-- SQL Suite: 08_category_analysis.sql
-- Business Question: Which categories represent high-traffic underperformers vs.
--                    high-converting opportunities?
-- Metrics:
--   - Traffic Share (% total views)
--   - Size Availability Rate
--   - Average Discount %
--   - View-to-Cart Conversion Rate (ATCR)
--   - Purchased Units
--   - Total Gross Revenue
-- Classification: 4-Quadrant Opportunity Matrix
--   - Q1: High Traffic + Below-Median ATCR (Underperforming Core)
--   - Q2: Low Traffic + Above-Median ATCR (High Intent / Growth Opportunity)
--   - Q3: High Traffic + Above-Median ATCR (Star Performers)
--   - Q4: Low Traffic + Below-Median ATCR (Niche / Low Focus)
-- ==============================================================================

WITH category_metrics AS (
    SELECT
        p.master_category,
        p.sub_category,
        COUNT(DISTINCT pv.view_id) AS total_views,
        COUNT(DISTINCT CASE WHEN pv.added_to_cart THEN pv.view_id END) AS cart_add_views,
        ROUND(100.0 * COUNT(DISTINCT CASE WHEN pv.added_to_cart THEN pv.view_id END) / COUNT(DISTINCT pv.view_id), 2) AS atcr_pct,
        ROUND(100.0 * SUM(CASE WHEN pv.is_size_in_stock THEN 1 ELSE 0 END) / COUNT(*), 2) AS size_availability_pct,
        ROUND(AVG(p.discount_pct), 1) AS avg_discount_pct,
        ROUND(AVG(p.effective_price), 2) AS avg_effective_price,
        COUNT(DISTINCT CASE WHEN ce.is_purchased THEN ce.cart_item_id END) AS purchased_units,
        ROUND(SUM(CASE WHEN ce.is_purchased THEN ce.item_price * ce.quantity ELSE 0 END), 2) AS total_category_revenue
    FROM products p
    JOIN product_views pv ON p.product_id = pv.product_id
    LEFT JOIN cart_events ce ON pv.view_id = ce.view_id
    GROUP BY p.master_category, p.sub_category
),
medians AS (
    SELECT
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_views) AS median_views,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY atcr_pct) AS median_atcr
    FROM category_metrics
)
SELECT
    cm.master_category,
    cm.sub_category,
    cm.total_views,
    cm.size_availability_pct,
    cm.avg_discount_pct,
    cm.atcr_pct,
    cm.purchased_units,
    cm.total_category_revenue,
    CASE 
        WHEN cm.total_views >= m.median_views AND cm.atcr_pct < m.median_atcr THEN 'Quadrant 1: High Traffic / Low ATCR (Friction)'
        WHEN cm.total_views < m.median_views AND cm.atcr_pct >= m.median_atcr THEN 'Quadrant 2: Low Traffic / High ATCR (Opportunity)'
        WHEN cm.total_views >= m.median_views AND cm.atcr_pct >= m.median_atcr THEN 'Quadrant 3: High Traffic / High ATCR (Star)'
        ELSE 'Quadrant 4: Low Traffic / Low ATCR (Niche)'
    END AS strategic_quadrant
FROM category_metrics cm
CROSS JOIN medians m
ORDER BY cm.total_views DESC;
