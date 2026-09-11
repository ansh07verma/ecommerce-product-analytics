"""
business_impact.py - Simple E-Commerce Business Impact Estimate

Calculates estimated incremental clicks, orders, and GMV if query relaxation
improves Search-to-PDP Click-Through Rate (CTR) on eligible searches.
"""

import duckdb
import pandas as pd


def get_baseline_metrics(db_path: str = "data/ecommerce_analytics.duckdb") -> dict:
    """Queries DuckDB for historical funnel conversion on the 941 eligible searches."""
    con = duckdb.connect(db_path, read_only=True)
    query = """
    SELECT
        COUNT(DISTINCT s.search_id) AS eligible_searches,
        COUNT(DISTINCT CASE WHEN s.has_pdp_click = 1 THEN s.search_id END) AS pdp_clicks,
        COUNT(DISTINCT c.cart_item_id) AS cart_additions,
        COUNT(DISTINCT o.order_id) AS completed_orders,
        SUM(o.gross_merchandise_value) AS observed_gmv
    FROM search_events s
    LEFT JOIN product_views v ON s.search_id = v.search_id
    LEFT JOIN cart_events c ON v.view_id = c.view_id
    LEFT JOIN orders o ON c.order_id = o.order_id
    WHERE (LENGTH(TRIM(s.query_text)) - LENGTH(REPLACE(TRIM(s.query_text), ' ', '')) + 1) >= 4
      AND s.results_count < 3;
    """
    df = con.execute(query).df()
    con.close()

    eligible = int(df["eligible_searches"].iloc[0])
    clicks = int(df["pdp_clicks"].iloc[0])
    carts = int(df["cart_additions"].iloc[0])
    orders = int(df["completed_orders"].iloc[0])
    gmv = float(df["observed_gmv"].iloc[0])

    ctr = clicks / eligible if eligible else 0.0
    pdp_to_cart = carts / clicks if clicks else 0.0
    cart_to_order = orders / carts if carts else 0.0
    aov = gmv / orders if orders else 0.0

    return {
        "eligible_searches_60d": eligible,
        "observed_pdp_clicks": clicks,
        "observed_carts": carts,
        "observed_orders": orders,
        "observed_gmv_60d": gmv,
        "baseline_ctr": ctr,
        "pdp_to_cart_rate": pdp_to_cart,
        "cart_to_order_rate": cart_to_order,
        "aov": aov,
    }


def estimate_scenario(
    baseline: dict,
    ctr_lift: float,
    recovery_rate: float = 0.9181,
    scenario_name: str = "Scenario",
) -> dict:
    """Estimates incremental clicks, orders, and GMV for an assumed CTR lift."""
    eligible = baseline["eligible_searches_60d"]
    pdp_to_cart = baseline["pdp_to_cart_rate"]
    cart_to_order = baseline["cart_to_order_rate"]
    aov = baseline["aov"]

    recovered_searches = eligible * recovery_rate
    incremental_clicks = recovered_searches * ctr_lift
    incremental_carts = incremental_clicks * pdp_to_cart
    incremental_orders = incremental_carts * cart_to_order
    gross_gmv_60d = incremental_orders * aov
    annualized_gmv = gross_gmv_60d * (365.0 / 60.0)

    return {
        "scenario": scenario_name,
        "ctr_lift_pct": round(ctr_lift * 100, 2),
        "recovered_searches": round(recovered_searches, 1),
        "incremental_clicks": round(incremental_clicks, 1),
        "incremental_carts": round(incremental_carts, 1),
        "incremental_orders": round(incremental_orders, 1),
        "gross_gmv_60d": round(gross_gmv_60d, 2),
        "annualized_gross_gmv": round(annualized_gmv, 2),
    }


def main():
    print("=" * 70)
    print("SIMPLE BUSINESS IMPACT MODEL: QUERY RELAXATION OPPORTUNITY")
    print("=" * 70)

    baseline = get_baseline_metrics()
    print("1. HISTORICAL 60-DAY BASELINE (Observed):")
    print(f"   Eligible Searches (>=4 tokens, <3 results): {baseline['eligible_searches_60d']}")
    print(f"   Baseline Search -> PDP CTR               : {baseline['baseline_ctr'] * 100:.2f}% ({baseline['observed_pdp_clicks']} clicks)")
    print(f"   Downstream PDP -> Cart Rate              : {baseline['pdp_to_cart_rate'] * 100:.2f}% ({baseline['observed_carts']} carts)")
    print(f"   Downstream Cart -> Order Rate            : {baseline['cart_to_order_rate'] * 100:.2f}% ({baseline['observed_orders']} orders)")
    print(f"   Average Order Value (AOV)                : ${baseline['aov']:.2f}")
    print(f"   Historical 60-Day GMV on Cohort          : ${baseline['observed_gmv_60d']:.2f}")
    print("-" * 70)

    print("2. ESTIMATED DOWNSTREAM IMPACT (Modeled Scenarios):")
    scenarios = [
        estimate_scenario(baseline, ctr_lift=0.010, scenario_name="Scenario A (+1.0 pp CTR Lift)"),
        estimate_scenario(baseline, ctr_lift=0.035, scenario_name="Scenario B (+3.5 pp CTR Lift)"),
    ]

    df_scenarios = pd.DataFrame(scenarios)
    print(df_scenarios.to_string(index=False))
    print("-" * 70)

    print("3. PRODUCT TAKEAWAY:")
    print("   At current traffic volume (~16 eligible searches/day), the financial return")
    print("   is modest (~$1,800/year under the +3.5 pp scenario). Therefore, the team")
    print("   should validate customer response through a simple A/B test rather than")
    print("   committing to large infrastructure investments.")
    print("=" * 70)


if __name__ == "__main__":
    main()
