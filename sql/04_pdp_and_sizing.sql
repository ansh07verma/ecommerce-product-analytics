-- ==============================================================================
-- SQL Suite: 04_pdp_and_sizing.sql
-- Business Question: How does size availability, dwell time, and merchandise pricing
--                    associate with Add-to-Cart behavior on Product Display Pages (PDP)?
-- Metrics:
--   - PDP View Count
--   - Size Availability Rate: Views where is_size_in_stock = TRUE / Total views
--   - In-Stock Add-to-Cart Rate (ATCR): Cart adds on in-stock views / In-stock views
--   - Out-of-Stock ATCR: Cart adds on out-of-stock views / Out-of-stock views
--   - Conversion Delta: In-stock ATCR - Out-of-stock ATCR
--   - Dwell Time Buckets vs ATCR
-- Framing Note:
--   - Observational analysis reflects statistical association, not confirmed causation.
-- ==============================================================================

-- 1. Overall Sizing Stockout Association with Add-to-Cart
SELECT
    COUNT(*) AS total_pdp_views,
    SUM(CASE WHEN is_size_in_stock THEN 1 ELSE 0 END) AS in_stock_views,
    SUM(CASE WHEN NOT is_size_in_stock THEN 1 ELSE 0 END) AS out_of_stock_views,
    ROUND(100.0 * SUM(CASE WHEN is_size_in_stock THEN 1 ELSE 0 END) / COUNT(*), 2) AS size_availability_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN is_size_in_stock AND added_to_cart THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN is_size_in_stock THEN 1 ELSE 0 END), 0), 2) AS in_stock_atcr_pct,
    ROUND(100.0 * SUM(CASE WHEN NOT is_size_in_stock AND added_to_cart THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN NOT is_size_in_stock THEN 1 ELSE 0 END), 0), 2) AS out_of_stock_atcr_pct,
    ROUND(
        (100.0 * SUM(CASE WHEN is_size_in_stock AND added_to_cart THEN 1 ELSE 0 END) / 
         NULLIF(SUM(CASE WHEN is_size_in_stock THEN 1 ELSE 0 END), 0)) -
        (100.0 * SUM(CASE WHEN NOT is_size_in_stock AND added_to_cart THEN 1 ELSE 0 END) / 
         NULLIF(SUM(CASE WHEN NOT is_size_in_stock THEN 1 ELSE 0 END), 0)), 
        2
    ) AS atcr_deficit_points
FROM product_views;

-- 2. Size Availability & ATCR by Master Category
SELECT
    p.master_category,
    COUNT(*) AS total_views,
    ROUND(100.0 * SUM(CASE WHEN pv.is_size_in_stock THEN 1 ELSE 0 END) / COUNT(*), 2) AS size_availability_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN pv.added_to_cart THEN 1 ELSE 0 END) / COUNT(*), 2) AS blended_atcr_pct,
    ROUND(100.0 * SUM(CASE WHEN pv.is_size_in_stock AND pv.added_to_cart THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN pv.is_size_in_stock THEN 1 ELSE 0 END), 0), 2) AS in_stock_atcr_pct,
    ROUND(100.0 * SUM(CASE WHEN NOT pv.is_size_in_stock AND pv.added_to_cart THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN NOT pv.is_size_in_stock THEN 1 ELSE 0 END), 0), 2) AS out_of_stock_atcr_pct
FROM product_views pv
JOIN products p ON pv.product_id = p.product_id
GROUP BY p.master_category
ORDER BY total_views DESC;

-- 3. PDP Behavior by Discount Depth Bucket
SELECT
    CASE 
        WHEN p.discount_pct = 0 THEN '1. Full Price (0%)'
        WHEN p.discount_pct <= 25 THEN '2. Moderate Discount (10-25%)'
        ELSE '3. Deep Discount (30-50%)'
    END AS discount_tier,
    COUNT(*) AS total_views,
    ROUND(100.0 * SUM(CASE WHEN pv.is_size_in_stock THEN 1 ELSE 0 END) / COUNT(*), 2) AS size_availability_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN pv.added_to_cart THEN 1 ELSE 0 END) / COUNT(*), 2) AS atcr_pct,
    ROUND(AVG(pv.dwell_time_sec), 1) AS avg_dwell_time_sec
FROM product_views pv
JOIN products p ON pv.product_id = p.product_id
GROUP BY 1
ORDER BY 1;

-- 4. PDP Add-to-Cart by Dwell Time Buckets
SELECT
    CASE 
        WHEN dwell_time_sec < 15 THEN '1. < 15s (Bounce)'
        WHEN dwell_time_sec BETWEEN 15 AND 30 THEN '2. 15s - 30s (Skim)'
        WHEN dwell_time_sec BETWEEN 31 AND 60 THEN '3. 31s - 60s (Consideration)'
        WHEN dwell_time_sec BETWEEN 61 AND 120 THEN '4. 61s - 120s (Engaged)'
        ELSE '5. > 120s (High Intent / Hesitation)'
    END AS dwell_time_bucket,
    COUNT(*) AS view_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM product_views), 2) AS view_share_pct,
    ROUND(100.0 * SUM(CASE WHEN added_to_cart THEN 1 ELSE 0 END) / COUNT(*), 2) AS atcr_pct
FROM product_views
GROUP BY 1
ORDER BY 1;
