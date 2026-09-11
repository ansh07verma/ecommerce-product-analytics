-- ==============================================================================
-- SQL Suite: 05_cart_checkout.sql
-- Business Question: How does cart-to-order checkout completion vary by basket value,
--                    delivery fee threshold ( cutoff), and platform?
-- Metrics:
--   - Cart Sessions (DISTINCT sessions with >=1 item added to cart)
--   - Order Sessions (DISTINCT sessions with completed order)
--   - Checkout Completion Rate (CCR): Order Sessions / Cart Sessions
--   - Cart Abandonment Rate: 1.0 - CCR
--   - Average Cart GMV
--   - Average Shipping Fee Charged
-- ==============================================================================

-- 1. Checkout Completion by Basket Value Buckets (Testing the  Shipping Cliff)
WITH cart_basket_values AS (
    SELECT
        ce.session_id,
        s.platform,
        u.user_type,
        u.user_tier,
        ROUND(SUM(ce.item_price * ce.quantity), 2) AS cart_gmv,
        MAX(CASE WHEN ce.is_purchased THEN 1 ELSE 0 END) AS has_purchased
    FROM cart_events ce
    JOIN sessions s ON ce.session_id = s.session_id
    JOIN users u ON ce.user_id = u.user_id
    GROUP BY ce.session_id, s.platform, u.user_type, u.user_tier
),
bucketed_carts AS (
    SELECT
        *,
        CASE 
            WHEN cart_gmv < 25.0 THEN '1. Under '
            WHEN cart_gmv BETWEEN 25.0 AND 37.99 THEN '2.  - .99'
            WHEN cart_gmv BETWEEN 38.0 AND 49.99 THEN '3.  - .99 (Shipping Fee Zone)'
            WHEN cart_gmv BETWEEN 50.0 AND 74.99 THEN '4.  - .99 (Free Shipping Zone)'
            ELSE '5. + (High Basket)'
        END AS basket_tier
    FROM cart_basket_values
)
SELECT
    basket_tier,
    COUNT(*) AS cart_sessions,
    SUM(has_purchased) AS order_sessions,
    ROUND(100.0 * SUM(has_purchased) / COUNT(*), 2) AS checkout_completion_rate_pct,
    ROUND(100.0 * (1.0 - (SUM(has_purchased) * 1.0 / COUNT(*))), 2) AS cart_abandonment_rate_pct,
    ROUND(AVG(cart_gmv), 2) AS avg_cart_gmv,
    CASE 
        WHEN basket_tier IN ('1. Under ', '2.  - .99', '3.  - .99 (Shipping Fee Zone)') THEN 5.99
        ELSE 0.00
    END AS applicable_shipping_fee
FROM bucketed_carts
GROUP BY basket_tier
ORDER BY basket_tier;

-- 2. Cart-to-Order Conversion by Platform & Free Shipping Qualification
WITH cart_shipping_summary AS (
    SELECT
        ce.session_id,
        s.platform,
        SUM(ce.item_price * ce.quantity) AS cart_gmv,
        CASE WHEN SUM(ce.item_price * ce.quantity) >= 50.0 THEN 'Free Shipping (+)' ELSE 'Shipping Fee (<)' END AS shipping_status,
        MAX(CASE WHEN ce.is_purchased THEN 1 ELSE 0 END) AS has_purchased
    FROM cart_events ce
    JOIN sessions s ON ce.session_id = s.session_id
    GROUP BY ce.session_id, s.platform
)
SELECT
    platform,
    shipping_status,
    COUNT(*) AS cart_sessions,
    SUM(has_purchased) AS order_sessions,
    ROUND(100.0 * SUM(has_purchased) / COUNT(*), 2) AS checkout_completion_rate_pct
FROM cart_shipping_summary
GROUP BY platform, shipping_status
ORDER BY platform, shipping_status;
