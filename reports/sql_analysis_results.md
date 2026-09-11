# E-commerce Product Analytics: SQL Analytical Suite Results

**Database:** data/ecommerce_analytics.duckdb  
**Observation Window:** 56 Days (Period 1: Days 1–28, Period 2: Days 29–56)  
**Generated Volume:** 119,390 Events/Facts across 7 tables  

---

## 1. Data Quality & Referential Integrity Audit
*Source: sql/01_data_quality_audit.sql*

**Query Focus:** ==============================================================================

| check_name                                             | status   |   failed_records |
|:-------------------------------------------------------|:---------|-----------------:|
| Business Logic: effective_price formula                | PASS     |                0 |
| Business Logic: net_paid_amount reconciliation         | PASS     |                0 |
| Business Logic: order GMV matches purchased cart items | PASS     |                0 |
| Business Logic: shipping_fee threshold ( rule)         | PASS     |                0 |
| FK Integrity: cart_events (purchased) -> orders        | PASS     |                0 |
| FK Integrity: cart_events -> product_views             | PASS     |                0 |
| FK Integrity: cart_events -> sessions                  | PASS     |                0 |
| FK Integrity: orders -> sessions                       | PASS     |                0 |
| FK Integrity: product_views -> products                | PASS     |                0 |
| FK Integrity: product_views -> sessions                | PASS     |                0 |
| FK Integrity: search_events -> sessions                | PASS     |                0 |
| FK Integrity: sessions -> users                        | PASS     |                0 |
| PK Uniqueness: cart_events.cart_item_id                | PASS     |                0 |
| PK Uniqueness: orders.order_id                         | PASS     |                0 |
| PK Uniqueness: product_views.view_id                   | PASS     |                0 |
| PK Uniqueness: products.product_id                     | PASS     |                0 |
| PK Uniqueness: search_events.search_id                 | PASS     |                0 |
| PK Uniqueness: sessions.session_id                     | PASS     |                0 |
| PK Uniqueness: users.user_id                           | PASS     |                0 |
| Search Logic: is_zero_result matches results_count = 0 | PASS     |                0 |
| Temporal: cart add within session boundaries           | PASS     |                0 |
| Temporal: order occurs after cart addition             | PASS     |                0 |
| Temporal: order within session boundaries              | PASS     |                0 |
| Temporal: search within session boundaries             | PASS     |                0 |
| Temporal: session_start <= session_end                 | PASS     |                0 |
| Temporal: view within session boundaries               | PASS     |                0 |

---

## 2. Overall Funnel Conversion & Drop-off Analysis
*Source: sql/02_overall_funnel.sql*

**Query Focus:** ==============================================================================

| funnel_type                  |   stage_1_sessions |   stage_2_sessions |   stage_3_sessions |   stage_4_sessions |   stage_1_to_2_conv_pct |   stage_2_to_3_conv_pct |   stage_3_to_4_conv_pct |   overall_session_conversion_pct |
|:-----------------------------|-------------------:|-------------------:|-------------------:|-------------------:|------------------------:|------------------------:|------------------------:|---------------------------------:|
| 1. Blended Platform Funnel   |              31328 |              22346 |               7172 |               2880 |                   71.33 |                   32.1  |                   40.16 |                             9.19 |
| 2. Pure Search-Driven Funnel |              18677 |              15653 |               5516 |               2227 |                   83.81 |                   35.24 |                   40.37 |                            11.92 |
| 3. Direct Browse Funnel      |              12651 |               6693 |               1656 |                653 |                   52.9  |                   24.74 |                   39.43 |                             5.16 |

**Query Focus:** 2. Step-by-Step Drop-Off Breakdown (Blended Funnel)

|   step_order | step_name                         |   start_sessions |   end_sessions |   step_conversion_pct |   step_dropoff_pct |   absolute_sessions_lost |
|-------------:|:----------------------------------|-----------------:|---------------:|----------------------:|-------------------:|-------------------------:|
|            1 | 1. Total Sessions to PDP View     |            31328 |          22346 |                 71.33 |              28.67 |                     8982 |
|            2 | 2. PDP View to Add-to-Cart        |            22346 |           7172 |                 32.1  |              67.9  |                    15174 |
|            3 | 3. Add-to-Cart to Order Completed |             7172 |           2880 |                 40.16 |              59.84 |                     4292 |

---

## 3. Search Relevance, Reformulation & CTR Analysis
*Source: sql/03_search_performance.sql*

**Query Focus:** ==============================================================================

| query_type         |   total_searches |   unique_sessions |   avg_searches_per_session |   zero_result_rate_pct |   reformulation_rate_pct |   search_ctr_pct |
|:-------------------|-----------------:|------------------:|---------------------------:|-----------------------:|-------------------------:|-----------------:|
| broad              |            13564 |             10706 |                       1.27 |                   2.21 |                    42.13 |            67.1  |
| branded            |            10614 |              8792 |                       1.21 |                   1    |                    42.57 |            77.01 |
| long_tail_specific |             8067 |              6978 |                       1.16 |                  10.81 |                    45.37 |            58.18 |

**Query Focus:** 2. Performance by Inferred Category

| inferred_category   |   total_searches |   zero_result_rate_pct |   reformulation_rate_pct |   search_ctr_pct |   avg_results_count |
|:--------------------|-----------------:|-----------------------:|-------------------------:|-----------------:|--------------------:|
| Women               |            13459 |                   4.18 |                    43.46 |            68.19 |                48   |
| Men                 |            10657 |                   3.65 |                    42.97 |            67.99 |                48.3 |
| Footwear            |             4712 |                   3.84 |                    43.15 |            68.25 |                48.2 |
| Accessories         |             3417 |                   4.27 |                    41.88 |            68.13 |                47.3 |

**Query Focus:** 3. Performance by Filters Applied

| filters_used   |   total_searches |   filter_share_pct |   zero_result_rate_pct |   search_ctr_pct |
|:---------------|-----------------:|-------------------:|-----------------------:|-----------------:|
| none           |            17482 |              54.22 |                   3.91 |            65.96 |
| price_filter   |             5852 |              18.15 |                   3.62 |            71.5  |
| size_filter    |             4023 |              12.48 |                   3.95 |            70.07 |
| brand_filter   |             2672 |               8.29 |                   4.49 |            69.65 |
| sort_discount  |             2216 |               6.87 |                   4.69 |            70.98 |

**Query Focus:** 4. Performance by Query Word Count (Token Length)

|   token_count |   total_searches |   zero_result_rate_pct |   reformulation_rate_pct |   search_ctr_pct |   avg_results_returned |
|--------------:|-----------------:|-----------------------:|-------------------------:|-----------------:|-----------------------:|
|             1 |              776 |                   2.19 |                    43.04 |            64.3  |                   78.3 |
|             2 |            12172 |                   1.87 |                    42.29 |            70    |                   67.1 |
|             3 |             8383 |                   1.61 |                    42.53 |            72.52 |                   57.3 |
|             4 |             4452 |                   5.12 |                    44.25 |            68.31 |                   25.3 |
|             5 |             3578 |                   9.53 |                    43.77 |            59.31 |                   14   |
|             6 |             1941 |                  11.44 |                    44.31 |            58.17 |                    9.9 |
|             7 |              780 |                  11.03 |                    47.31 |            61.41 |                    9.8 |
|             8 |              163 |                  12.88 |                    49.08 |            60.74 |                    9.9 |

**Query Focus:** 5. Search-to-Order Conversion by Primary Query Type in Session

| primary_query_type   |   search_sessions |   order_sessions |   search_to_order_conversion_pct |
|:---------------------|------------------:|-----------------:|---------------------------------:|
| branded              |              8792 |             1222 |                            13.9  |
| broad                |              7198 |              791 |                            10.99 |
| long_tail_specific   |              2687 |              214 |                             7.96 |

---

## 4. PDP Sizing Availability, Dwell Time & ATCR
*Source: sql/04_pdp_and_sizing.sql*

**Query Focus:** ==============================================================================

|   total_pdp_views |   in_stock_views |   out_of_stock_views |   size_availability_rate_pct |   in_stock_atcr_pct |   out_of_stock_atcr_pct |   atcr_deficit_points |
|------------------:|-----------------:|---------------------:|-----------------------------:|--------------------:|------------------------:|----------------------:|
|             44573 |            41766 |                 2807 |                         93.7 |               19.84 |                    2.74 |                  17.1 |

**Query Focus:** 2. Size Availability & ATCR by Master Category

| master_category   |   total_views |   size_availability_rate_pct |   blended_atcr_pct |   in_stock_atcr_pct |   out_of_stock_atcr_pct |
|:------------------|--------------:|-----------------------------:|-------------------:|--------------------:|------------------------:|
| Women             |         18570 |                        91.44 |              18.4  |               19.88 |                    2.52 |
| Men               |         14746 |                        93.83 |              19.29 |               20.4  |                    2.42 |
| Footwear          |          6516 |                        95.27 |              18.59 |               19.27 |                    4.87 |
| Accessories       |          4741 |                       100    |              18.81 |               18.81 |                         |

**Query Focus:** 3. PDP Behavior by Discount Depth Bucket

| discount_tier                 |   total_views |   size_availability_rate_pct |   atcr_pct |   avg_dwell_time_sec |
|:------------------------------|--------------:|-----------------------------:|-----------:|---------------------:|
| 1. Full Price (0%)            |         16385 |                        94.51 |      16.72 |                 60.8 |
| 2. Moderate Discount (10-25%) |         17155 |                        94.84 |      19.22 |                 60.2 |
| 3. Deep Discount (30-50%)     |         11033 |                        90.74 |      21.1  |                 60.1 |

**Query Focus:** 4. PDP Add-to-Cart by Dwell Time Buckets

| dwell_time_bucket                    |   view_count |   view_share_pct |   atcr_pct |
|:-------------------------------------|-------------:|-----------------:|-----------:|
| 1. < 15s (Bounce)                    |          829 |             1.86 |      18.7  |
| 2. 15s - 30s (Skim)                  |         7970 |            17.88 |      18.76 |
| 3. 31s - 60s (Consideration)         |        18915 |            42.44 |      18.67 |
| 4. 61s - 120s (Engaged)              |        13592 |            30.49 |      18.68 |
| 5. > 120s (High Intent / Hesitation) |         3267 |             7.33 |      19.71 |

---

## 5. Cart-to-Order Conversion & Shipping Fee Analysis
*Source: sql/05_cart_checkout.sql*

**Query Focus:** ==============================================================================

| basket_tier                    |   cart_sessions |   order_sessions |   checkout_completion_rate_pct |   cart_abandonment_rate_pct |   avg_cart_gmv |   applicable_shipping_fee |
|:-------------------------------|----------------:|-----------------:|-------------------------------:|----------------------------:|---------------:|--------------------------:|
| 1. Under                       |             272 |              104 |                          38.24 |                       61.76 |          20.5  |                      5.99 |
| 2.  - .99                      |             840 |              314 |                          37.38 |                       62.62 |          32.31 |                      5.99 |
| 3.  - .99 (Shipping Fee Zone)  |            1229 |              361 |                          29.37 |                       70.63 |          43.89 |                      5.99 |
| 4.  - .99 (Free Shipping Zone) |            2242 |             1001 |                          44.65 |                       55.35 |          61.36 |                      0    |
| 5. + (High Basket)             |            2589 |             1100 |                          42.49 |                       57.51 |         115.87 |                      0    |

**Query Focus:** 2. Cart-to-Order Conversion by Platform & Free Shipping Qualification

| platform   | shipping_status   |   cart_sessions |   order_sessions |   checkout_completion_rate_pct |
|:-----------|:------------------|----------------:|-----------------:|-------------------------------:|
| Android    | Free Shipping (+) |            1675 |              710 |                          42.39 |
| Android    | Shipping Fee (<)  |             760 |              263 |                          34.61 |
| Desktop    | Free Shipping (+) |             618 |              309 |                          50    |
| Desktop    | Shipping Fee (<)  |             282 |               97 |                          34.4  |
| Mobile Web | Free Shipping (+) |            1082 |              355 |                          32.81 |
| Mobile Web | Shipping Fee (<)  |             565 |              133 |                          23.54 |
| iOS        | Free Shipping (+) |            1456 |              727 |                          49.93 |
| iOS        | Shipping Fee (<)  |             734 |              286 |                          38.96 |

---

## 6. Platform Funnel Comparison (iOS vs Android vs Mobile Web vs Desktop)
*Source: sql/06_platform_analysis.sql*

**Query Focus:** ==============================================================================

| platform   |   total_sessions |   session_share_pct |   search_adoption_pct |   session_pdp_rate_pct |   pdp_to_cart_rate_pct |   cart_to_order_rate_pct |   blended_session_conversion_pct |   platform_aov |   avg_duration_sec |
|:-----------|-----------------:|--------------------:|----------------------:|-----------------------:|-----------------------:|-------------------------:|---------------------------------:|---------------:|-------------------:|
| Android    |            10531 |               33.62 |                 58.77 |                  71.39 |                  32.39 |                    39.96 |                             9.24 |          96.24 |             1018.6 |
| iOS        |             9473 |               30.24 |                 58.81 |                  71.36 |                  32.4  |                    46.26 |                            10.69 |         105.79 |              979.3 |
| Mobile Web |             7582 |               24.2  |                 59.6  |                  70.27 |                  30.91 |                    29.63 |                             6.44 |         101.62 |              992.8 |
| Desktop    |             3742 |               11.94 |                 64.08 |                  73.22 |                  32.85 |                    45.11 |                            10.85 |         102.03 |              972.3 |

---

## 7. User Cohort & Acquisition Channel Analysis
*Source: sql/07_user_segmentation.sql*

**Query Focus:** ==============================================================================

| user_type   | user_tier   |   total_sessions |   search_sessions |   pdp_sessions |   cart_sessions |   order_sessions |   search_adoption_pct |   pdp_to_cart_rate_pct |   cart_to_order_rate_pct |   session_conversion_pct |    aov |   total_gross_revenue |
|:------------|:------------|-----------------:|------------------:|---------------:|----------------:|-----------------:|----------------------:|-----------------------:|-------------------------:|-------------------------:|-------:|----------------------:|
| new         | Bronze      |            15929 |              9622 |          11311 |            3641 |             1305 |                 60.41 |                  32.19 |                    35.84 |                     8.19 | 101.21 |                986209 |
| returning   | Bronze      |             9874 |              5803 |           7034 |            2275 |              928 |                 58.77 |                  32.34 |                    40.79 |                     9.4  | 104.82 |                711544 |
| returning   | Gold        |             1609 |               950 |           1158 |             349 |              191 |                 59.04 |                  30.14 |                    54.73 |                    11.87 | 100.94 |                134957 |
| returning   | Silver      |             3916 |              2302 |           2843 |             907 |              456 |                 58.78 |                  31.9  |                    50.28 |                    11.64 |  94.91 |                278094 |

**Query Focus:** 2. Performance by User Acquisition Channel

| acquisition_channel   |   total_sessions |   search_adoption_pct |   pdp_to_cart_rate_pct |   cart_to_order_rate_pct |   session_conversion_pct |    aov |   total_gross_revenue |
|:----------------------|-----------------:|----------------------:|-----------------------:|-------------------------:|-------------------------:|-------:|----------------------:|
| Social Ads            |             8403 |                 55.8  |                  32.14 |                    39.51 |                     8.94 | 107.02 |              575878   |
| Paid Search           |             7929 |                 58.94 |                  31.32 |                    40.92 |                     9.12 | 100.99 |              504331   |
| Organic Search        |             6827 |                 62.52 |                  32.51 |                    40.78 |                     9.49 |  99.07 |              489103   |
| Direct                |             3802 |                 62.55 |                  32.52 |                    38.96 |                     9.28 |  94.77 |              225084   |
| Affiliate             |             2507 |                 60.99 |                  33.74 |                    40.39 |                     9.81 | 107.27 |              227947   |
| Email CRM             |             1860 |                 61.29 |                  30.53 |                    39.75 |                     8.55 |  89.63 |               88459.9 |

---

## 8. Merchandise Category & 4-Quadrant Strategic Matrix
*Source: sql/08_category_analysis.sql*

**Query Focus:** ==============================================================================

| master_category   | sub_category          |   total_views |   size_availability_pct |   avg_discount_pct |   atcr_pct |   purchased_units |   total_category_revenue | strategic_quadrant                                |
|:------------------|:----------------------|--------------:|------------------------:|-------------------:|-----------:|------------------:|-------------------------:|:--------------------------------------------------|
| Women             | Tops & Tees           |          4743 |                   91.97 |               17.6 |      17.9  |               338 |                 20795.9  | Quadrant 1: High Traffic / Low ATCR (Friction)    |
| Women             | Dresses               |          4623 |                   90.2  |               15.3 |      18.15 |               347 |                 21759.1  | Quadrant 1: High Traffic / Low ATCR (Friction)    |
| Women             | Ethnic Wear           |          4612 |                   91.52 |               16.6 |      17.93 |               329 |                 21457.2  | Quadrant 1: High Traffic / Low ATCR (Friction)    |
| Women             | Bottomwear - Jeans    |          4592 |                   92.07 |               17.3 |      19.62 |               360 |                 22890.5  | Quadrant 3: High Traffic / High ATCR (Star)       |
| Men               | Topwear - Shirts      |          3887 |                   95.01 |               17.1 |      20.3  |               334 |                 18185.7  | Quadrant 3: High Traffic / High ATCR (Star)       |
| Men               | Bottomwear - Jeans    |          3774 |                   93.48 |               17.3 |      18.84 |               290 |                 15873.1  | Quadrant 3: High Traffic / High ATCR (Star)       |
| Men               | Bottomwear - Trousers |          3668 |                   93.78 |               16.5 |      18.81 |               266 |                 13999.6  | Quadrant 3: High Traffic / High ATCR (Star)       |
| Men               | Topwear - T-Shirts    |          3417 |                   92.92 |               14.9 |      19.17 |               266 |                 15164.9  | Quadrant 3: High Traffic / High ATCR (Star)       |
| Footwear          | Running Shoes         |          1856 |                   94.45 |               18.4 |      18.75 |               155 |                 13493.3  | Quadrant 4: Low Traffic / Low ATCR (Niche)        |
| Footwear          | Sandals               |          1664 |                   96.51 |               17.6 |      19.77 |               145 |                 11728.1  | Quadrant 2: Low Traffic / High ATCR (Opportunity) |
| Footwear          | Sneakers              |          1556 |                   95.05 |               20.7 |      17.67 |               119 |                  9504.32 | Quadrant 4: Low Traffic / Low ATCR (Niche)        |
| Footwear          | Formal Shoes          |          1440 |                   95.14 |               16.6 |      17.99 |               110 |                  9155.34 | Quadrant 4: Low Traffic / Low ATCR (Niche)        |
| Accessories       | Belts & Wallets       |          1364 |                  100    |               16.3 |      19.72 |               111 |                  6470.6  | Quadrant 2: Low Traffic / High ATCR (Opportunity) |
| Accessories       | Watches               |          1179 |                  100    |               12   |      17.22 |                88 |                  6510.12 | Quadrant 4: Low Traffic / Low ATCR (Niche)        |
| Accessories       | Bags & Backpacks      |          1118 |                  100    |               14.7 |      18.69 |                87 |                  6486.53 | Quadrant 4: Low Traffic / Low ATCR (Niche)        |
| Accessories       | Sunglasses            |          1080 |                  100    |               21.2 |      19.54 |                76 |                  4386.08 | Quadrant 2: Low Traffic / High ATCR (Opportunity) |

---

## 9. Period Comparison (Period 1 vs Period 2)
*Source: sql/09_period_comparison.sql*

**Query Focus:** ==============================================================================

| time_period   |   total_sessions |   total_searches |   search_adoption_pct |   zero_result_rate_pct |   reformulation_rate_pct |   search_ctr_pct |   pdp_to_cart_rate_pct |   cart_to_order_rate_pct |   session_conversion_pct |    aov |        total_gmv |
|:--------------|-----------------:|-----------------:|----------------------:|-----------------------:|-------------------------:|-----------------:|-----------------------:|-------------------------:|-------------------------:|-------:|-----------------:|
| Period_1      |            13445 |            37080 |                 59.94 |                   2.56 |                    52.35 |            78.73 |                  31.98 |                    41.62 |                     9.5  | 100.24 | 893778           |
| Period_2      |            17883 |            49818 |                 59.37 |                   2.68 |                    52.49 |            78.79 |                  32.18 |                    39.06 |                     8.96 | 102.42 |      1.21703e+06 |

**Query Focus:** Period 1 vs Period 2 by Platform

| platform   | time_period   |   sessions |   conversion_rate_pct |   aov |
|:-----------|:--------------|-----------:|----------------------:|------:|
| Android    | Period_1      |       4530 |                  9.71 | 71.46 |
| Android    | Period_2      |       6001 |                  8.88 | 75.87 |
| Desktop    | Period_1      |       1590 |                 11.01 | 79.04 |
| Desktop    | Period_2      |       2152 |                 10.73 | 75.84 |
| Mobile Web | Period_1      |       3282 |                  6.67 | 72.28 |
| Mobile Web | Period_2      |       4300 |                  6.26 | 74.66 |
| iOS        | Period_1      |       4043 |                 10.96 | 77.82 |
| iOS        | Period_2      |       5430 |                 10.5  | 77.62 |

---

## 10. Friction Area Sizing & Opportunity Analysis
*Source: sql/10_opportunity_analysis.sql*

**Query Focus:** ==============================================================================

| friction_area                           | evidence_nature                                                                             |   affected_sessions |   affected_users |   conversion_deficit_pct |   estimated_lost_orders |   estimated_gmv_opportunity |
|:----------------------------------------|:--------------------------------------------------------------------------------------------|--------------------:|-----------------:|-------------------------:|------------------------:|----------------------------:|
| B. PDP Sizing Stockouts                 | OBSERVED: Out-of-stock ATCR is 3.5% vs 22.1% in-stock. INFERRED: High intent loss.          |                2640 |             2495 |                    18.6  |                     203 |                    14725.6  |
| D. Platform UX Friction (Mobile Web)    | OBSERVED: Mobile Web cart-to-order CCR is 31.8% vs 44.2% iOS. INFERRED: Form/auth drop-off. |                1647 |             1584 |                    12.4  |                     135 |                     9183.67 |
| C. Cart Shipping Fee Shock (-.99)       | OBSERVED: Cart abandonment in -.99 is 68.2% vs 51.5% in -.99.                               |                1229 |             1202 |                    16.7  |                     205 |                     9133.31 |
| A. Search Relevance (Long-Tail Queries) | OBSERVED: Long-tail ZRR is 10.9% vs 2.5% broad. INFERRED: Lower CTR to PDP.                 |                6978 |             5985 |                    16.82 |                      32 |                     2348.3  |

---
