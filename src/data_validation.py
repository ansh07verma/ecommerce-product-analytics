"""
Data Quality Validation Module for E-commerce Product Analytics.
Performs 18 strict integrity and business-logic assertions across all tables.
"""

import sys
import pandas as pd
import numpy as np


class DataValidationError(Exception):
    pass


def validate_all(
    users_df: pd.DataFrame,
    sessions_df: pd.DataFrame,
    products_df: pd.DataFrame,
    searches_df: pd.DataFrame,
    views_df: pd.DataFrame,
    carts_df: pd.DataFrame,
    orders_df: pd.DataFrame,
) -> bool:
    print("\n" + "=" * 60)
    print("RUNNING AUTOMATED DATA QUALITY VALIDATION SUITE")
    print("=" * 60)

    results = []

    def check(condition: bool, check_name: str, details: str = ""):
        if condition:
            print(f"PASS — {check_name}")
            results.append((True, check_name))
        else:
            msg = f"FAIL — {check_name}: {details}"
            print(msg)
            results.append((False, check_name))
            raise DataValidationError(msg)

    # 1. Primary-key uniqueness
    check(users_df["user_id"].is_unique, "users PK uniqueness")
    check(products_df["product_id"].is_unique, "products PK uniqueness")
    check(sessions_df["session_id"].is_unique, "sessions PK uniqueness")
    check(searches_df["search_id"].is_unique, "searches PK uniqueness")
    check(views_df["view_id"].is_unique, "product_views PK uniqueness")
    check(carts_df["cart_item_id"].is_unique, "cart_events PK uniqueness")
    check(orders_df["order_id"].is_unique, "orders PK uniqueness")

    # 2. Foreign-key integrity (Zero orphans)
    check(sessions_df["user_id"].isin(users_df["user_id"]).all(), "sessions -> users FK")
    check(searches_df["session_id"].isin(sessions_df["session_id"]).all(), "searches -> sessions FK")
    check(searches_df["user_id"].isin(users_df["user_id"]).all(), "searches -> users FK")
    check(views_df["session_id"].isin(sessions_df["session_id"]).all(), "views -> sessions FK")
    check(views_df["user_id"].isin(users_df["user_id"]).all(), "views -> users FK")
    check(views_df["product_id"].isin(products_df["product_id"]).all(), "views -> products FK")
    
    # search_id in views can be null (non-search views), but if not null must exist in searches
    valid_searches = views_df["search_id"].dropna()
    check(valid_searches.isin(searches_df["search_id"]).all(), "views -> searches FK (nullable)")

    check(carts_df["session_id"].isin(sessions_df["session_id"]).all(), "carts -> sessions FK")
    check(carts_df["user_id"].isin(users_df["user_id"]).all(), "carts -> users FK")
    check(carts_df["product_id"].isin(products_df["product_id"]).all(), "carts -> products FK")
    check(carts_df["view_id"].isin(views_df["view_id"]).all(), "carts -> views FK")

    # order_id in carts
    valid_cart_orders = carts_df["order_id"].dropna()
    check(valid_cart_orders.isin(orders_df["order_id"]).all(), "carts -> orders FK (nullable)")

    check(orders_df["session_id"].isin(sessions_df["session_id"]).all(), "orders -> sessions FK")
    check(orders_df["user_id"].isin(users_df["user_id"]).all(), "orders -> users FK")

    # 3. No nulls in required fields
    check(users_df[["user_id", "signup_date", "user_type", "user_tier", "acquisition_channel", "gender_preference", "created_at"]].notna().all().all(), "users required non-nulls")
    check(sessions_df[["session_id", "user_id", "platform", "device_category", "traffic_source", "session_start", "session_end", "session_duration_sec", "has_search", "time_period"]].notna().all().all(), "sessions required non-nulls")
    check(products_df[["product_id", "title", "brand", "master_category", "sub_category", "retail_price", "discount_pct", "effective_price", "available_sizes", "inventory_units", "avg_rating", "review_count"]].notna().all().all(), "products required non-nulls")
    check(searches_df[["search_id", "session_id", "user_id", "query_text", "query_type", "inferred_category", "results_count", "is_zero_result", "filters_used", "search_timestamp", "reformulated_in_session", "has_pdp_click"]].notna().all().all(), "searches required non-nulls")
    check(views_df[["view_id", "session_id", "user_id", "product_id", "referrer_channel", "view_timestamp", "dwell_time_sec", "is_size_in_stock", "added_to_cart"]].notna().all().all(), "views required non-nulls")
    check(carts_df[["cart_item_id", "session_id", "user_id", "product_id", "view_id", "selected_size", "quantity", "item_price", "added_at", "is_purchased"]].notna().all().all(), "carts required non-nulls")
    check(orders_df[["order_id", "session_id", "user_id", "total_items", "gross_merchandise_value", "discount_amount", "shipping_fee", "net_paid_amount", "payment_method", "checkout_step_reached", "order_timestamp"]].notna().all().all(), "orders required non-nulls")

    # 4. Valid categorical values
    check(set(users_df["user_type"].unique()).issubset({"new", "returning"}), "users.user_type values")
    check(set(users_df["user_tier"].unique()).issubset({"Bronze", "Silver", "Gold"}), "users.user_tier values")
    check(set(sessions_df["platform"].unique()).issubset({"iOS", "Android", "Mobile Web", "Desktop"}), "sessions.platform values")
    check(set(sessions_df["time_period"].unique()).issubset({"Period_1", "Period_2"}), "sessions.time_period values")
    check(set(products_df["master_category"].unique()).issubset({"Men", "Women", "Footwear", "Accessories"}), "products.master_category values")
    check(set(searches_df["query_type"].unique()).issubset({"broad", "branded", "long_tail_specific"}), "searches.query_type values")
    check(set(orders_df["payment_method"].unique()).issubset({"Credit Card", "Debit Card", "Digital Wallet", "Buy Now Pay Later"}), "orders.payment_method values")

    # 5. Valid timestamps & chronological ordering within user lifecycle
    # signup <= session_start <= session_end
    u_sess = sessions_df.merge(users_df[["user_id", "signup_date"]], on="user_id", how="left")
    u_sess["signup_ts"] = pd.to_datetime(u_sess["signup_date"])
    check((u_sess["session_start"] >= u_sess["signup_ts"]).all(), "chronological signup <= session_start")
    check((sessions_df["session_end"] >= sessions_df["session_start"]).all(), "chronological session_start <= session_end")
    check((sessions_df["session_duration_sec"] >= 0).all(), "non-negative session_duration_sec")

    # searches within session
    s_merged = searches_df.merge(sessions_df[["session_id", "session_start", "session_end"]], on="session_id")
    check(((s_merged["search_timestamp"] >= s_merged["session_start"]) & 
           (s_merged["search_timestamp"] <= s_merged["session_end"])).all(), 
          "searches occur strictly within session boundaries")

    # views within session and after search if search-linked
    v_merged = views_df.merge(sessions_df[["session_id", "session_start", "session_end"]], on="session_id")
    check(((v_merged["view_timestamp"] >= v_merged["session_start"]) & 
           (v_merged["view_timestamp"] <= v_merged["session_end"])).all(), 
          "views occur strictly within session boundaries")

    v_search = views_df[views_df["search_id"].notna()].merge(
        searches_df[["search_id", "search_timestamp"]], on="search_id"
    )
    check((v_search["view_timestamp"] >= v_search["search_timestamp"]).all(), 
          "search-linked views occur after search timestamp")

    # carts within session and after view
    c_merged = carts_df.merge(sessions_df[["session_id", "session_start", "session_end"]], on="session_id")
    check(((c_merged["added_at"] >= c_merged["session_start"]) & 
           (c_merged["added_at"] <= c_merged["session_end"])).all(), 
          "cart adds occur strictly within session boundaries")

    c_view = carts_df.merge(views_df[["view_id", "view_timestamp"]], on="view_id")
    check((c_view["added_at"] >= c_view["view_timestamp"]).all(), 
          "cart adds occur after product view timestamp")

    # orders within session and after cart adds
    o_merged = orders_df.merge(sessions_df[["session_id", "session_start", "session_end"]], on="session_id")
    check(((o_merged["order_timestamp"] >= o_merged["session_start"]) & 
           (o_merged["order_timestamp"] <= o_merged["session_end"])).all(), 
          "orders occur strictly within session boundaries")

    o_carts = carts_df[carts_df["order_id"].notna()].merge(
        orders_df[["order_id", "order_timestamp"]], on="order_id"
    )
    check((o_carts["order_timestamp"] >= o_carts["added_at"]).all(), 
          "orders occur after cart addition timestamp")

    # 7. No negative prices & valid discount ranges
    check((products_df["retail_price"] > 0).all(), "products retail_price > 0")
    check((products_df["discount_pct"] >= 0).all() and (products_df["discount_pct"] <= 50.0).all(), "discount_pct in [0, 50]")
    
    # 9. effective_price calculation
    calc_eff_price = (products_df["retail_price"] * (1 - products_df["discount_pct"] / 100)).round(2)
    diff = (products_df["effective_price"] - calc_eff_price).abs()
    check((diff <= 0.02).all(), "effective_price matches retail_price * (1 - discount_pct/100)")

    # 10. shipping fee calculation: $0 if GMV >= $50, else $5.99
    expected_shipping = np.where(orders_df["gross_merchandise_value"] >= 50.0, 0.00, 5.99)
    check((orders_df["shipping_fee"].round(2) == expected_shipping).all(), "shipping fee: $0 if GMV >= $50, else $5.99")

    # 11. net-paid calculation: GMV - discount + shipping
    expected_net = (orders_df["gross_merchandise_value"] - orders_df["discount_amount"] + orders_df["shipping_fee"]).round(2)
    net_diff = (orders_df["net_paid_amount"].round(2) - expected_net).abs()
    check((net_diff <= 0.02).all(), "net_paid_amount matches GMV - discount + shipping")

    # 12. Order / cart reconciliation: Sum of purchased cart items equals order GMV
    cart_totals = carts_df[carts_df["is_purchased"]].groupby("order_id").apply(
        lambda g: (g["item_price"] * g["quantity"]).sum()
    ).round(2).reset_index(name="calc_gmv")
    order_recon = orders_df.merge(cart_totals, on="order_id", how="left")
    check((order_recon["gross_merchandise_value"].round(2) == order_recon["calc_gmv"].round(2)).all(), 
          "order GMV matches exact sum of purchased cart item prices")

    # 13. Purchased cart events have order_id
    purchased_carts = carts_df[carts_df["is_purchased"]]
    check(purchased_carts["order_id"].notna().all(), "purchased cart events have valid order_id")

    # 14. Abandoned cart events have NULL order_id
    abandoned_carts = carts_df[~carts_df["is_purchased"]]
    check(abandoned_carts["order_id"].isna().all(), "abandoned cart events have NULL order_id")

    # 15. Search zero-result flag correctness
    check(((searches_df["results_count"] == 0) == searches_df["is_zero_result"]).all(), 
          "is_zero_result flag strictly matches results_count == 0")

    # 16. Search-linked PDP views belong to the exact same session
    v_s_session = views_df[views_df["search_id"].notna()].merge(
        searches_df[["search_id", "session_id"]], on="search_id", suffixes=("_view", "_search")
    )
    check((v_s_session["session_id_view"] == v_s_session["session_id_search"]).all(), 
          "search-linked PDP views belong to identical session_id")

    # 17. SRP positions are valid (1 to 40 for search views, null for browse)
    search_views = views_df[views_df["referrer_channel"] == "search_srp"]
    check(search_views["srp_position"].notna().all(), "search views have non-null srp_position")
    check((search_views["srp_position"] >= 1).all() and (search_views["srp_position"] <= 40).all(), 
          "srp_position in range [1, 40]")

    # 18. Funnel cardinality
    n_sessions = sessions_df["session_id"].nunique()
    n_search_sess = searches_df["session_id"].nunique()
    n_view_sess = views_df["session_id"].nunique()
    n_cart_sess = carts_df["session_id"].nunique()
    n_order_sess = orders_df["session_id"].nunique()

    check(n_order_sess <= n_cart_sess <= n_view_sess <= n_sessions, 
          "funnel session cardinality: Orders <= Carts <= Views <= Total Sessions")
    check(n_search_sess <= n_sessions, "search sessions <= total sessions")

    print("=" * 60)
    print(f"ALL {len(results)} DATA QUALITY CHECKS PASSED PERFECTLY!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    import os
    raw_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
    try:
        users = pd.read_csv(os.path.join(raw_dir, "users.csv"))
        sessions = pd.read_csv(os.path.join(raw_dir, "sessions.csv"), parse_dates=["session_start", "session_end"])
        products = pd.read_csv(os.path.join(raw_dir, "products.csv"))
        searches = pd.read_csv(os.path.join(raw_dir, "search_events.csv"), parse_dates=["search_timestamp"])
        views = pd.read_csv(os.path.join(raw_dir, "product_views.csv"), parse_dates=["view_timestamp"])
        carts = pd.read_csv(os.path.join(raw_dir, "cart_events.csv"), parse_dates=["added_at"])
        orders = pd.read_csv(os.path.join(raw_dir, "orders.csv"), parse_dates=["order_timestamp"])
        validate_all(users, sessions, products, searches, views, carts, orders)
    except Exception as e:
        print(f"Validation failed: {e}")
        sys.exit(1)
