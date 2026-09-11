-- ==============================================================================
-- SQL Suite: 01_data_quality_audit.sql
-- Business Question: Does the DuckDB analytical database meet 100% data integrity,
--                    referential consistency, and business logic constraints?
-- Metric: Audit assertion status (PASS/FAIL) and failure count
-- Definition: Comprehensive validation across PKs, FKs, domain values, calculations,
--             and temporal sequence.
-- SQL Approach: Multi-test CTE with UNION ALL evaluating zero-defect assertions.
-- ==============================================================================

WITH audit_checks AS (
    -- 1. Primary Key Uniqueness
    SELECT 'PK Uniqueness: users.user_id' AS check_name,
           CASE WHEN COUNT(*) = COUNT(DISTINCT user_id) THEN 'PASS' ELSE 'FAIL' END AS status,
           COUNT(*) - COUNT(DISTINCT user_id) AS failed_records
    FROM users

    UNION ALL
    SELECT 'PK Uniqueness: products.product_id',
           CASE WHEN COUNT(*) = COUNT(DISTINCT product_id) THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*) - COUNT(DISTINCT product_id)
    FROM products

    UNION ALL
    SELECT 'PK Uniqueness: sessions.session_id',
           CASE WHEN COUNT(*) = COUNT(DISTINCT session_id) THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*) - COUNT(DISTINCT session_id)
    FROM sessions

    UNION ALL
    SELECT 'PK Uniqueness: search_events.search_id',
           CASE WHEN COUNT(*) = COUNT(DISTINCT search_id) THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*) - COUNT(DISTINCT search_id)
    FROM search_events

    UNION ALL
    SELECT 'PK Uniqueness: product_views.view_id',
           CASE WHEN COUNT(*) = COUNT(DISTINCT view_id) THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*) - COUNT(DISTINCT view_id)
    FROM product_views

    UNION ALL
    SELECT 'PK Uniqueness: cart_events.cart_item_id',
           CASE WHEN COUNT(*) = COUNT(DISTINCT cart_item_id) THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*) - COUNT(DISTINCT cart_item_id)
    FROM cart_events

    UNION ALL
    SELECT 'PK Uniqueness: orders.order_id',
           CASE WHEN COUNT(*) = COUNT(DISTINCT order_id) THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*) - COUNT(DISTINCT order_id)
    FROM orders

    -- 2. Foreign Key Integrity (Zero Orphans)
    UNION ALL
    SELECT 'FK Integrity: sessions -> users',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM sessions s
    LEFT JOIN users u ON s.user_id = u.user_id
    WHERE u.user_id IS NULL

    UNION ALL
    SELECT 'FK Integrity: search_events -> sessions',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM search_events se
    LEFT JOIN sessions s ON se.session_id = s.session_id
    WHERE s.session_id IS NULL

    UNION ALL
    SELECT 'FK Integrity: product_views -> sessions',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM product_views pv
    LEFT JOIN sessions s ON pv.session_id = s.session_id
    WHERE s.session_id IS NULL

    UNION ALL
    SELECT 'FK Integrity: product_views -> products',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM product_views pv
    LEFT JOIN products p ON pv.product_id = p.product_id
    WHERE p.product_id IS NULL

    UNION ALL
    SELECT 'FK Integrity: cart_events -> sessions',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM cart_events ce
    LEFT JOIN sessions s ON ce.session_id = s.session_id
    WHERE s.session_id IS NULL

    UNION ALL
    SELECT 'FK Integrity: cart_events -> product_views',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM cart_events ce
    LEFT JOIN product_views pv ON ce.view_id = pv.view_id
    WHERE pv.view_id IS NULL

    UNION ALL
    SELECT 'FK Integrity: orders -> sessions',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM orders o
    LEFT JOIN sessions s ON o.session_id = s.session_id
    WHERE s.session_id IS NULL

    UNION ALL
    SELECT 'FK Integrity: cart_events (purchased) -> orders',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM cart_events ce
    LEFT JOIN orders o ON ce.order_id = o.order_id
    WHERE ce.is_purchased = TRUE AND o.order_id IS NULL

    -- 3. Business Logic & Pricing Integrity
    UNION ALL
    SELECT 'Business Logic: effective_price formula',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM products
    WHERE ABS(effective_price - ROUND(retail_price * (1.0 - discount_pct / 100.0), 2)) > 0.02

    UNION ALL
    SELECT 'Business Logic: shipping_fee threshold ( rule)',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM orders
    WHERE (gross_merchandise_value >= 50.0 AND shipping_fee != 0.0)
       OR (gross_merchandise_value < 50.0 AND shipping_fee != 5.99)

    UNION ALL
    SELECT 'Business Logic: net_paid_amount reconciliation',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM orders
    WHERE ABS(net_paid_amount - (gross_merchandise_value - discount_amount + shipping_fee)) > 0.02

    UNION ALL
    SELECT 'Business Logic: order GMV matches purchased cart items',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM (
        SELECT o.order_id, o.gross_merchandise_value,
               ROUND(SUM(ce.item_price * ce.quantity), 2) AS cart_gmv
        FROM orders o
        JOIN cart_events ce ON o.order_id = ce.order_id
        WHERE ce.is_purchased = TRUE
        GROUP BY o.order_id, o.gross_merchandise_value
        HAVING ABS(o.gross_merchandise_value - ROUND(SUM(ce.item_price * ce.quantity), 2)) > 0.02
    ) mismatch

    -- 4. Temporal Integrity
    UNION ALL
    SELECT 'Temporal: session_start <= session_end',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM sessions
    WHERE session_start > session_end

    UNION ALL
    SELECT 'Temporal: search within session boundaries',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM search_events se
    JOIN sessions s ON se.session_id = s.session_id
    WHERE se.search_timestamp < s.session_start OR se.search_timestamp > s.session_end

    UNION ALL
    SELECT 'Temporal: view within session boundaries',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM product_views pv
    JOIN sessions s ON pv.session_id = s.session_id
    WHERE pv.view_timestamp < s.session_start OR pv.view_timestamp > s.session_end

    UNION ALL
    SELECT 'Temporal: cart add within session boundaries',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM cart_events ce
    JOIN sessions s ON ce.session_id = s.session_id
    WHERE ce.added_at < s.session_start OR ce.added_at > s.session_end

    UNION ALL
    SELECT 'Temporal: order within session boundaries',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM orders o
    JOIN sessions s ON o.session_id = s.session_id
    WHERE o.order_timestamp < s.session_start OR o.order_timestamp > s.session_end

    UNION ALL
    SELECT 'Temporal: order occurs after cart addition',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM cart_events ce
    JOIN orders o ON ce.order_id = o.order_id
    WHERE o.order_timestamp < ce.added_at

    -- 5. Search Zero-Result Flag Consistency
    UNION ALL
    SELECT 'Search Logic: is_zero_result matches results_count = 0',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*)
    FROM search_events
    WHERE (results_count = 0 AND is_zero_result = FALSE)
       OR (results_count > 0 AND is_zero_result = TRUE)
)
SELECT check_name, status, failed_records
FROM audit_checks
ORDER BY status DESC, check_name;
