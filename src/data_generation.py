"""
Synthetic Data Generation Engine for E-commerce Product Analytics.
Simulates a multi-platform fashion marketplace with realistic behavioural patterns,
competing friction signals, and strict temporal and referential integrity.
"""

import os
import sys
import uuid
import math
import random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import duckdb
from faker import Faker

# Import validation suite
from data_validation import validate_all

# Configuration & Constants
SEED = 42
OBSERVATION_DAYS = 56
START_DATE = datetime(2026, 10, 1, 0, 0, 0)
END_DATE = START_DATE + timedelta(days=OBSERVATION_DAYS)
PERIOD_1_END = START_DATE + timedelta(days=28)

# Target Cardinalities
TARGET_USERS = 16000
TARGET_PRODUCTS = 1600
TARGET_SESSIONS = 32000

# Set deterministic seeds
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


# ==============================================================================
# 1. GENERATE PRODUCTS
# ==============================================================================
def generate_products(n_products=TARGET_PRODUCTS) -> pd.DataFrame:
    print(f"Generating {n_products} catalogue products...")
    
    categories = {
        "Men": {
            "sub_categories": ["Topwear - Shirts", "Topwear - T-Shirts", "Bottomwear - Jeans", "Bottomwear - Trousers"],
            "brands": ["Levi's", "Zara Men", "H&M Men", "Tommy Hilfiger", "Roadster", "Allen Solly", "Marks & Spencer"],
            "price_range": (18.0, 110.0),
            "sizes": ["S", "M", "L", "XL", "XXL"],
            "popular_sizes": ["M", "L"]
        },
        "Women": {
            "sub_categories": ["Dresses", "Tops & Tees", "Bottomwear - Jeans", "Ethnic Wear"],
            "brands": ["Zara", "H&M", "Mango", "Vero Moda", "Forever 21", "Biba", "Urban Chic"],
            "price_range": (22.0, 135.0),
            "sizes": ["XS", "S", "M", "L", "XL"],
            "popular_sizes": ["S", "M"]
        },
        "Footwear": {
            "sub_categories": ["Sneakers", "Formal Shoes", "Sandals", "Running Shoes"],
            "brands": ["Nike", "Adidas", "Puma", "Reebok", "Clarks", "Red Tape"],
            "price_range": (45.0, 160.0),
            "sizes": ["6", "7", "8", "9", "10", "11"],
            "popular_sizes": ["8", "9"]
        },
        "Accessories": {
            "sub_categories": ["Bags & Backpacks", "Watches", "Belts & Wallets", "Sunglasses"],
            "brands": ["Fossil", "Fastrack", "Ray-Ban", "Tommy Hilfiger", "Titan", "Lavie"],
            "price_range": (15.0, 140.0),
            "sizes": ["One Size"],
            "popular_sizes": ["One Size"]
        }
    }

    item_adjectives = ["Slim Fit", "Regular Fit", "Oversized", "Floral Print", "Cotton", "Linen", 
                       "Vintage Wash", "Casual", "Formal", "Classic", "Textured", "Solid", "Athletic"]

    records = []
    cat_keys = list(categories.keys())
    cat_weights = [0.35, 0.40, 0.15, 0.10]

    for i in range(n_products):
        p_id = f"p-{uuid.uuid4().hex[:12]}"
        master_cat = np.random.choice(cat_keys, p=cat_weights)
        cat_info = categories[master_cat]
        sub_cat = random.choice(cat_info["sub_categories"])
        brand = random.choice(cat_info["brands"])
        adj = random.choice(item_adjectives)
        
        # Construct realistic fashion title
        clean_sub = sub_cat.split(" - ")[-1] if " - " in sub_cat else sub_cat
        title = f"{brand} {adj} {clean_sub}"
        
        # Price & discount
        min_p, max_p = cat_info["price_range"]
        retail_price = round(float(np.random.triangular(min_p, (min_p + max_p) * 0.4, max_p)), 2)
        
        # Discount distribution (40% no discount, 35% moderate 10-25%, 25% deep 30-50%)
        disc_tier = np.random.choice(["none", "moderate", "deep"], p=[0.38, 0.37, 0.25])
        if disc_tier == "none":
            discount_pct = 0.0
        elif disc_tier == "moderate":
            discount_pct = float(np.random.choice([10.0, 15.0, 20.0, 25.0]))
        else:
            discount_pct = float(np.random.choice([30.0, 40.0, 50.0]))
            
        effective_price = round(retail_price * (1.0 - discount_pct / 100.0), 2)
        
        # Sizes & Stockouts
        all_sizes = cat_info["sizes"]
        avail_str = ",".join(all_sizes)
        
        # Stockout frequency: Higher for high-discount items and specific categories
        base_stockout_prob = 0.18
        if discount_pct >= 30.0:
            base_stockout_prob += 0.15
        if sub_cat in ["Dresses", "Ethnic Wear", "Sneakers"]:
            base_stockout_prob += 0.10
            
        if master_cat == "Accessories":
            stockout_sizes = ""
        else:
            if random.random() < base_stockout_prob:
                stock_out_count = random.choice([1, 2])
                out_sample = random.sample(cat_info["popular_sizes"], min(stock_out_count, len(cat_info["popular_sizes"])))
                stockout_sizes = ",".join(out_sample)
            else:
                stockout_sizes = ""
                
        inventory_units = int(np.random.gamma(shape=3.0, scale=15.0)) + 5
        avg_rating = round(float(np.clip(np.random.normal(4.15, 0.35), 2.5, 5.0)), 2)
        review_count = int(np.random.exponential(scale=45.0)) + 3

        records.append({
            "product_id": p_id,
            "title": title,
            "brand": brand,
            "master_category": master_cat,
            "sub_category": sub_cat,
            "retail_price": retail_price,
            "discount_pct": discount_pct,
            "effective_price": effective_price,
            "available_sizes": avail_str,
            "stockout_sizes": stockout_sizes,
            "inventory_units": inventory_units,
            "avg_rating": avg_rating,
            "review_count": review_count
        })

    df = pd.DataFrame(records)
    print(f"Products generated: {len(df)} rows.")
    return df


# ==============================================================================
# 2. GENERATE USERS
# ==============================================================================
def generate_users(n_users=TARGET_USERS) -> pd.DataFrame:
    print(f"Generating {n_users} users...")
    records = []
    
    channels = ["Organic Search", "Paid Search", "Social Ads", "Direct", "Affiliate", "Email CRM"]
    ch_weights = [0.22, 0.25, 0.27, 0.12, 0.08, 0.06]
    
    tiers = ["Bronze", "Silver", "Gold"]
    tier_weights = [0.65, 0.25, 0.10]
    
    gender_prefs = ["Women", "Men", "Unisex", "Kids"]
    g_weights = [0.48, 0.42, 0.07, 0.03]

    for i in range(n_users):
        u_id = f"u-{uuid.uuid4().hex[:12]}"
        user_type = np.random.choice(["new", "returning"], p=[0.62, 0.38])
        user_tier = np.random.choice(tiers, p=tier_weights) if user_type == "returning" else "Bronze"
        acquisition_channel = np.random.choice(channels, p=ch_weights)
        gender_pref = np.random.choice(gender_prefs, p=g_weights)
        
        if user_type == "returning":
            days_ago = random.randint(45, 365)
            signup_dt = START_DATE - timedelta(days=days_ago, seconds=random.randint(0, 86399))
        else:
            days_offset = random.randint(-20, 30)
            signup_dt = START_DATE + timedelta(days=days_offset, seconds=random.randint(0, 86399))

        records.append({
            "user_id": u_id,
            "signup_date": signup_dt.strftime("%Y-%m-%d"),
            "user_type": user_type,
            "user_tier": user_tier,
            "acquisition_channel": acquisition_channel,
            "gender_preference": gender_pref,
            "created_at": signup_dt.strftime("%Y-%m-%d %H:%M:%S")
        })

    df = pd.DataFrame(records)
    print(f"Users generated: {len(df)} rows.")
    return df


# ==============================================================================
# 3. GENERATE SESSIONS
# ==============================================================================
def generate_sessions(users_df: pd.DataFrame, target_sessions=TARGET_SESSIONS) -> pd.DataFrame:
    print(f"Generating approximately {target_sessions} sessions...")
    
    platforms = ["iOS", "Android", "Mobile Web", "Desktop"]
    plat_weights = [0.30, 0.34, 0.24, 0.12]
    
    traffic_sources = {
        "Social Ads": ["Meta Ads", "TikTok Ads", "Instagram Influencer"],
        "Paid Search": ["Google CPC", "Bing CPC"],
        "Organic Search": ["Google Organic", "Yahoo Organic"],
        "Direct": ["Direct"],
        "Affiliate": ["Affiliate Partner"],
        "Email CRM": ["CRM Email", "Push Notification"]
    }

    records = []
    users_list = users_df.to_dict(orient="records")
    
    # Calculate session count distribution per user
    user_session_counts = []
    for u in users_list:
        if u["user_type"] == "returning":
            cnt = int(np.random.choice([1, 2, 3, 4, 5], p=[0.20, 0.34, 0.26, 0.13, 0.07]))
        else:
            cnt = int(np.random.choice([1, 2, 3], p=[0.52, 0.35, 0.13]))
        user_session_counts.append(cnt)

    total_prelim = sum(user_session_counts)
    scale_factor = target_sessions / total_prelim

    for idx, u in enumerate(users_list):
        n_user_sess = max(1, int(round(user_session_counts[idx] * scale_factor)))
        u_signup = datetime.strptime(u["created_at"], "%Y-%m-%d %H:%M:%S")
        
        effective_start = max(u_signup, START_DATE)
        if effective_start >= END_DATE - timedelta(hours=3):
            effective_start = END_DATE - timedelta(days=2)

        window_seconds = int((END_DATE - effective_start).total_seconds())
        if window_seconds <= 300:
            window_seconds = 3600

        session_offsets = sorted([random.randint(0, window_seconds - 300) for _ in range(n_user_sess)])
        
        for offset in session_offsets:
            s_id = f"s-{uuid.uuid4().hex[:12]}"
            s_start = effective_start + timedelta(seconds=offset)
            
            platform = np.random.choice(platforms, p=plat_weights)
            if platform == "Desktop":
                device_cat = "Desktop"
            else:
                device_cat = np.random.choice(["Mobile", "Tablet"], p=[0.92, 0.08])
                
            if random.random() < 0.65:
                src_pool = traffic_sources.get(u["acquisition_channel"], ["Google Organic"])
                t_source = random.choice(src_pool)
            else:
                all_srcs = ["Google Organic", "Meta Ads", "Google CPC", "Direct", "CRM Email"]
                t_source = random.choice(all_srcs)
                
            time_period = "Period_1" if s_start < PERIOD_1_END else "Period_2"
            
            # Baseline search participation ~58%
            search_prob = 0.58
            if "Organic" in t_source or t_source == "Direct":
                search_prob += 0.06
            elif "Ads" in t_source:
                search_prob -= 0.06
            if platform == "Desktop":
                search_prob += 0.05
            has_search = (random.random() < search_prob)
            
            dur = int(np.random.lognormal(mean=6.7, sigma=0.65))
            dur = int(np.clip(dur, 120, 3600))
            s_end = s_start + timedelta(seconds=dur)

            records.append({
                "session_id": s_id,
                "user_id": u["user_id"],
                "platform": platform,
                "device_category": device_cat,
                "traffic_source": t_source,
                "session_start": s_start,
                "session_end": s_end,
                "session_duration_sec": dur,
                "has_search": has_search,
                "time_period": time_period
            })

    df = pd.DataFrame(records)
    df = df.sort_values("session_start").reset_index(drop=True)
    print(f"Sessions generated: {len(df)} rows.")
    return df


# ==============================================================================
# 4. GENERATE SEARCH EVENTS
# ==============================================================================
def generate_search_events(
    sessions_df: pd.DataFrame, 
    products_df: pd.DataFrame, 
    session_latest_time: dict
) -> tuple[pd.DataFrame, dict]:
    print("Generating search events...")
    
    search_sessions = sessions_df[sessions_df["has_search"]].to_dict(orient="records")
    
    broad_queries = [
        "oversized t shirt", "floral dress", "running shoes", "linen shirt men", 
        "high waist jeans", "leather jacket", "sneakers white", "hoodie black",
        "cotton trousers", "formal shoes", "party wear dress", "denim jacket",
        "graphic tee", "ethnic kurta", "summer shorts", "polo t shirt", "handbags"
    ]
    
    query_types = ["broad", "branded", "long_tail_specific"]
    qt_weights = [0.42, 0.33, 0.25]
    
    filters_options = ["none", "price_filter", "size_filter", "brand_filter", "sort_discount"]
    filter_weights = [0.55, 0.18, 0.12, 0.08, 0.07]

    records = []
    session_searches_map = {}

    for s in search_sessions:
        s_id = s["session_id"]
        u_id = s["user_id"]
        s_start = s["session_start"]
        
        # Multi-search distribution to achieve ~1.95 searches per search session
        n_searches = int(np.random.choice([1, 2, 3, 4], p=[0.50, 0.32, 0.14, 0.04]))
        
        session_searches = []
        curr_ts = s_start + timedelta(seconds=random.randint(15, 60))
        
        for q_idx in range(n_searches):
            srch_id = f"srch-{uuid.uuid4().hex[:12]}"
            q_type = np.random.choice(query_types, p=qt_weights)
            
            sample_prod = products_df.sample(1).iloc[0]
            cat_inferred = sample_prod["master_category"]
            brand = sample_prod["brand"]
            clean_sub = sample_prod["sub_category"].split(" - ")[-1]
            
            if q_type == "broad":
                query_text = random.choice(broad_queries)
                if random.random() < 0.025:
                    results_count = 0
                else:
                    results_count = int(np.random.triangular(25, 75, 140))
            elif q_type == "branded":
                query_text = f"{brand} {clean_sub.lower()}"
                if random.random() < 0.010:
                    results_count = 0
                else:
                    results_count = int(np.random.triangular(12, 38, 70))
            else: # long_tail_specific
                modifiers = ["slim fit", "pure cotton", "vintage", "oversized", "breathable", "linen"]
                colors = ["black", "beige", "navy blue", "white", "emerald green"]
                sizes = ["M", "L", "XL", "9", "10"]
                query_text = f"{random.choice(modifiers)} {random.choice(colors)} {clean_sub.lower()} {random.choice(sizes)}"
                
                if random.random() < 0.108:
                    results_count = 0
                else:
                    results_count = int(np.random.triangular(2, 9, 24))

            is_zero = (results_count == 0)
            filters_used = np.random.choice(filters_options, p=filter_weights)
            
            reformulated = False
            if q_idx < n_searches - 1:
                reformulated = True
            elif is_zero:
                reformulated = (random.random() < 0.42)
                
            if is_zero:
                has_pdp_click = False
            else:
                base_ctr_logit = 0.65
                if q_type == "branded":
                    base_ctr_logit += 0.50
                elif q_type == "long_tail_specific":
                    base_ctr_logit -= 0.15
                if filters_used != "none":
                    base_ctr_logit += 0.25
                has_pdp_click = (random.random() < sigmoid(base_ctr_logit))

            search_record = {
                "search_id": srch_id,
                "session_id": s_id,
                "user_id": u_id,
                "query_text": query_text,
                "query_type": q_type,
                "inferred_category": cat_inferred,
                "results_count": results_count,
                "is_zero_result": is_zero,
                "filters_used": filters_used,
                "search_timestamp": curr_ts,
                "reformulated_in_session": reformulated,
                "has_pdp_click": has_pdp_click
            }
            records.append(search_record)
            session_searches.append(search_record)
            
            # Track latest session timestamp
            if curr_ts > session_latest_time[s_id]:
                session_latest_time[s_id] = curr_ts
                
            curr_ts = curr_ts + timedelta(seconds=random.randint(25, 60))
            
        session_searches_map[s_id] = session_searches

    df = pd.DataFrame(records)
    df = df.sort_values("search_timestamp").reset_index(drop=True)
    print(f"Search events generated: {len(df)} rows.")
    return df, session_searches_map


# ==============================================================================
# 5. GENERATE PRODUCT VIEWS
# ==============================================================================
def generate_product_views(
    sessions_df: pd.DataFrame, 
    products_df: pd.DataFrame, 
    session_searches_map: dict,
    session_latest_time: dict
) -> tuple[pd.DataFrame, dict]:
    print("Generating product views...")
    
    sessions_dict = sessions_df.set_index("session_id").to_dict(orient="index")
    products_list = products_df.to_dict(orient="records")
    products_by_cat = {}
    for p in products_list:
        products_by_cat.setdefault(p["master_category"], []).append(p)

    records = []
    session_views_map = {}

    srp_positions = list(range(1, 41))
    pos_probs = [1.0 / (pos ** 0.85) for pos in srp_positions]
    pos_probs = [p / sum(pos_probs) for p in pos_probs]

    for s_id, s_info in sessions_dict.items():
        u_id = s_info["user_id"]
        s_start = s_info["session_start"]
        has_search = s_info["has_search"]
        platform = s_info["platform"]
        
        session_views = []
        searches_in_sess = session_searches_map.get(s_id, [])
        
        # 1. Search-originated views
        for srch in searches_in_sess:
            if srch["has_pdp_click"]:
                n_clicks = int(np.random.choice([1, 2, 3], p=[0.72, 0.22, 0.06]))
                cat = srch["inferred_category"]
                cat_prods = products_by_cat.get(cat, products_list)
                
                view_cursor = srch["search_timestamp"] + timedelta(seconds=random.randint(8, 25))
                for _ in range(n_clicks):
                    view_id = f"v-{uuid.uuid4().hex[:12]}"
                    prod = random.choice(cat_prods)
                    srp_pos = int(np.random.choice(srp_positions, p=pos_probs))
                    
                    dwell = int(np.random.lognormal(mean=4.0, sigma=0.6))
                    dwell = int(np.clip(dwell, 10, 480))
                    
                    avail_sizes = prod["available_sizes"].split(",")
                    stockout_sizes = prod["stockout_sizes"].split(",") if prod["stockout_sizes"] else []
                    
                    selected_size = random.choice(avail_sizes)
                    is_in_stock = (selected_size not in stockout_sizes)
                    
                    # Add to cart probability (calibrated to ~20% event ATCR)
                    logit_atc = -1.45
                    if not is_in_stock:
                        logit_atc -= 2.05
                    if prod["discount_pct"] >= 20.0:
                        logit_atc += 0.35
                    if prod["retail_price"] > 90.0:
                        logit_atc -= 0.25
                    if platform == "Mobile Web":
                        logit_atc -= 0.12
                        
                    added_to_cart = (random.random() < sigmoid(logit_atc))
                    
                    v_rec = {
                        "view_id": view_id,
                        "session_id": s_id,
                        "user_id": u_id,
                        "product_id": prod["product_id"],
                        "search_id": srch["search_id"],
                        "srp_position": srp_pos,
                        "referrer_channel": "search_srp",
                        "view_timestamp": view_cursor,
                        "dwell_time_sec": dwell,
                        "selected_size": selected_size,
                        "is_size_in_stock": is_in_stock,
                        "added_to_cart": added_to_cart,
                        "_effective_price": prod["effective_price"]
                    }
                    records.append(v_rec)
                    session_views.append(v_rec)
                    
                    if view_cursor > session_latest_time[s_id]:
                        session_latest_time[s_id] = view_cursor
                        
                    view_cursor = view_cursor + timedelta(seconds=dwell + random.randint(5, 30))

        # 2. Browse views
        # ~52% of non-search sessions view products, and ~18% of search sessions do additional browsing
        do_browse = (not has_search and random.random() < 0.52) or (has_search and random.random() < 0.18)
        if do_browse:
            n_browse = int(np.random.choice([1, 2, 3], p=[0.60, 0.28, 0.12]))
            ref_ch = random.choice(["home_curated", "category_browse", "item_recommendation"])
            
            b_cursor = max(s_start + timedelta(seconds=random.randint(15, 45)), session_latest_time[s_id] + timedelta(seconds=20))
            for _ in range(n_browse):
                view_id = f"v-{uuid.uuid4().hex[:12]}"
                prod = random.choice(products_list)
                dwell = int(np.random.lognormal(mean=3.8, sigma=0.55))
                dwell = int(np.clip(dwell, 10, 420))
                
                avail_sizes = prod["available_sizes"].split(",")
                stockout_sizes = prod["stockout_sizes"].split(",") if prod["stockout_sizes"] else []
                selected_size = random.choice(avail_sizes)
                is_in_stock = (selected_size not in stockout_sizes)
                
                logit_atc = -1.55
                if not is_in_stock:
                    logit_atc -= 1.95
                if prod["discount_pct"] >= 20.0:
                    logit_atc += 0.30
                if prod["retail_price"] > 90.0:
                    logit_atc -= 0.20
                    
                added_to_cart = (random.random() < sigmoid(logit_atc))
                
                v_rec = {
                    "view_id": view_id,
                    "session_id": s_id,
                    "user_id": u_id,
                    "product_id": prod["product_id"],
                    "search_id": None,
                    "srp_position": None,
                    "referrer_channel": ref_ch,
                    "view_timestamp": b_cursor,
                    "dwell_time_sec": dwell,
                    "selected_size": selected_size,
                    "is_size_in_stock": is_in_stock,
                    "added_to_cart": added_to_cart,
                    "_effective_price": prod["effective_price"]
                }
                records.append(v_rec)
                session_views.append(v_rec)
                
                if b_cursor > session_latest_time[s_id]:
                    session_latest_time[s_id] = b_cursor
                    
                b_cursor = b_cursor + timedelta(seconds=dwell + random.randint(10, 35))

        if session_views:
            session_views_map[s_id] = session_views

    df = pd.DataFrame(records)
    df = df.sort_values("view_timestamp").reset_index(drop=True)
    print(f"Product views generated: {len(df)} rows.")
    return df, session_views_map


# ==============================================================================
# 6. GENERATE CART EVENTS
# ==============================================================================
def generate_cart_events(
    product_views_df: pd.DataFrame, 
    session_latest_time: dict
) -> tuple[pd.DataFrame, dict]:
    print("Generating cart events...")
    
    atc_views = product_views_df[product_views_df["added_to_cart"]].to_dict(orient="records")
    
    records = []
    session_carts_map = {}

    for v in atc_views:
        s_id = v["session_id"]
        v_time = v["view_timestamp"]
        
        cart_id = f"c-{uuid.uuid4().hex[:12]}"
        
        add_sec = random.randint(10, max(12, min(50, v["dwell_time_sec"])))
        added_at = v_time + timedelta(seconds=add_sec)
            
        qty = int(np.random.choice([1, 2], p=[0.92, 0.08]))
        item_price = v["_effective_price"]
        
        cart_rec = {
            "cart_item_id": cart_id,
            "session_id": s_id,
            "user_id": v["user_id"],
            "product_id": v["product_id"],
            "view_id": v["view_id"],
            "order_id": None,
            "selected_size": v["selected_size"] if v["selected_size"] else "M",
            "quantity": qty,
            "item_price": item_price,
            "added_at": added_at,
            "is_purchased": False
        }
        records.append(cart_rec)
        session_carts_map.setdefault(s_id, []).append(cart_rec)
        
        if added_at > session_latest_time[s_id]:
            session_latest_time[s_id] = added_at

    df = pd.DataFrame(records)
    df = df.sort_values("added_at").reset_index(drop=True)
    print(f"Cart events generated: {len(df)} rows across {len(session_carts_map)} sessions.")
    return df, session_carts_map


# ==============================================================================
# 7. GENERATE ORDERS & BACKFILL CART EVENTS
# ==============================================================================
def generate_orders(
    cart_events_df: pd.DataFrame, 
    sessions_df: pd.DataFrame, 
    users_df: pd.DataFrame, 
    session_carts_map: dict,
    session_latest_time: dict
) -> tuple[pd.DataFrame, pd.DataFrame]:
    print("Generating orders and reconciling transactions...")
    
    sessions_dict = sessions_df.set_index("session_id").to_dict(orient="index")
    users_dict = users_df.set_index("user_id").to_dict(orient="index")
    
    order_records = []
    
    carts_dict = cart_events_df.to_dict(orient="records")
    carts_by_session = {}
    for c in carts_dict:
        carts_by_session.setdefault(c["session_id"], []).append(c)

    payment_methods = ["Digital Wallet", "Credit Card", "Debit Card", "Buy Now Pay Later"]
    pm_weights = [0.42, 0.28, 0.18, 0.12]

    for s_id, items in carts_by_session.items():
        s_info = sessions_dict[s_id]
        u_info = users_dict[s_info["user_id"]]
        
        platform = s_info["platform"]
        user_tier = u_info["user_tier"]
        user_type = u_info["user_type"]
        
        gmv = round(float(sum(item["item_price"] * item["quantity"] for item in items)), 2)
        
        # Checkout conversion model with competing friction signals
        # Calibrated for ~40.5% session completion
        logit_checkout = -0.38
        
        has_shipping_fee = (gmv < 50.0)
        if has_shipping_fee:
            if gmv >= 35.0:
                logit_checkout -= 0.55
            else:
                logit_checkout -= 0.35
                
        if platform == "Mobile Web":
            logit_checkout -= 0.45
        elif platform == "iOS":
            logit_checkout += 0.25
            
        if user_tier == "Gold":
            logit_checkout += 0.65
        elif user_tier == "Silver":
            logit_checkout += 0.30
        if user_type == "returning":
            logit_checkout += 0.20
            
        p_checkout = sigmoid(logit_checkout)
        is_converted = (random.random() < p_checkout)
        
        if is_converted:
            order_id = f"ord-{uuid.uuid4().hex[:12]}"
            
            latest_cart_time = max(item["added_at"] for item in items)
            order_sec = random.randint(45, 180)
            order_ts = latest_cart_time + timedelta(seconds=order_sec)

            if order_ts > session_latest_time[s_id]:
                session_latest_time[s_id] = order_ts

            for item in items:
                item["order_id"] = order_id
                item["is_purchased"] = True
                
            total_items = sum(item["quantity"] for item in items)
            
            if user_tier in ["Gold", "Silver"] and random.random() < 0.40:
                discount_amount = round(gmv * 0.10, 2)
            elif random.random() < 0.15:
                discount_amount = 5.00
            else:
                discount_amount = 0.00
                
            shipping_fee = 0.00 if gmv >= 50.0 else 5.99
            net_paid = round(gmv - discount_amount + shipping_fee, 2)
            
            pm = np.random.choice(payment_methods, p=pm_weights)
            
            order_records.append({
                "order_id": order_id,
                "session_id": s_id,
                "user_id": s_info["user_id"],
                "total_items": total_items,
                "gross_merchandise_value": gmv,
                "discount_amount": discount_amount,
                "shipping_fee": shipping_fee,
                "net_paid_amount": net_paid,
                "payment_method": pm,
                "checkout_step_reached": "payment_complete",
                "order_timestamp": order_ts
            })

    orders_df = pd.DataFrame(order_records)
    orders_df = orders_df.sort_values("order_timestamp").reset_index(drop=True)
    
    updated_carts_df = pd.DataFrame(carts_dict)
    updated_carts_df = updated_carts_df.sort_values("added_at").reset_index(drop=True)
    
    print(f"Orders generated: {len(orders_df)} orders.")
    print(f"Purchased cart items backfilled: {updated_carts_df['is_purchased'].sum()} items.")
    return orders_df, updated_carts_df


# ==============================================================================
# 8. SYNCHRONIZE SESSION END TIMES
# ==============================================================================
def synchronize_sessions(sessions_df: pd.DataFrame, session_latest_time: dict) -> pd.DataFrame:
    print("Synchronizing session end boundaries with actual activity...")
    sess_records = sessions_df.to_dict(orient="records")
    
    for s in sess_records:
        s_id = s["session_id"]
        latest_act = session_latest_time.get(s_id, s["session_start"])
        
        # Guarantee session_end is strictly after latest event
        if latest_act >= s["session_end"]:
            new_end = latest_act + timedelta(seconds=random.randint(45, 180))
            s["session_end"] = new_end
            s["session_duration_sec"] = int((new_end - s["session_start"]).total_seconds())

    df = pd.DataFrame(sess_records)
    print("Session end boundaries synchronized.")
    return df


# ==============================================================================
# 9. EXPORT CSVs & CREATE DUCKDB DATABASE
# ==============================================================================
def export_and_database(
    users_df: pd.DataFrame,
    sessions_df: pd.DataFrame,
    products_df: pd.DataFrame,
    searches_df: pd.DataFrame,
    views_df: pd.DataFrame,
    carts_df: pd.DataFrame,
    orders_df: pd.DataFrame,
    base_dir: str
):
    raw_dir = os.path.join(base_dir, "data", "raw")
    db_path = os.path.join(base_dir, "data", "ecommerce_analytics.duckdb")
    os.makedirs(raw_dir, exist_ok=True)
    
    clean_views_df = views_df.drop(columns=["_effective_price"], errors="ignore")
    
    print(f"\nExporting CSV files to {raw_dir}...")
    users_df.to_csv(os.path.join(raw_dir, "users.csv"), index=False)
    sessions_df.to_csv(os.path.join(raw_dir, "sessions.csv"), index=False)
    products_df.to_csv(os.path.join(raw_dir, "products.csv"), index=False)
    searches_df.to_csv(os.path.join(raw_dir, "search_events.csv"), index=False)
    clean_views_df.to_csv(os.path.join(raw_dir, "product_views.csv"), index=False)
    carts_df.to_csv(os.path.join(raw_dir, "cart_events.csv"), index=False)
    orders_df.to_csv(os.path.join(raw_dir, "orders.csv"), index=False)
    print("All 7 CSVs successfully saved.")

    print(f"\nBuilding DuckDB database at {db_path}...")
    if os.path.exists(db_path):
        os.remove(db_path)
        
    con = duckdb.connect(db_path)
    con.execute("CREATE TABLE users AS SELECT * FROM users_df")
    con.execute("CREATE TABLE sessions AS SELECT * FROM sessions_df")
    con.execute("CREATE TABLE products AS SELECT * FROM products_df")
    con.execute("CREATE TABLE search_events AS SELECT * FROM searches_df")
    con.execute("CREATE TABLE product_views AS SELECT * FROM clean_views_df")
    con.execute("CREATE TABLE cart_events AS SELECT * FROM carts_df")
    con.execute("CREATE TABLE orders AS SELECT * FROM orders_df")
    
    print("DuckDB tables created and indexed.")
    con.close()
    print("Database build complete.")


# ==============================================================================
# MAIN PIPELINE EXECUTION
# ==============================================================================
def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print("=" * 60)
    print("E-COMMERCE PRODUCT ANALYTICS DATA GENERATOR")
    print(f"Project directory: {base_dir}")
    print(f"Seed: {SEED} | Observation Window: {OBSERVATION_DAYS} days")
    print("=" * 60)

    # 1. Products
    products_df = generate_products(TARGET_PRODUCTS)

    # 2. Users
    users_df = generate_users(TARGET_USERS)

    # 3. Sessions
    sessions_df = generate_sessions(users_df, TARGET_SESSIONS)

    # Activity timestamp tracker for each session
    session_latest_time = {s_id: s_start for s_id, s_start in zip(sessions_df["session_id"], sessions_df["session_start"])}

    # 4. Search Events
    searches_df, session_searches_map = generate_search_events(sessions_df, products_df, session_latest_time)

    # 5. Product Views
    views_df, session_views_map = generate_product_views(sessions_df, products_df, session_searches_map, session_latest_time)

    # 6. Cart Events
    carts_df, session_carts_map = generate_cart_events(views_df, session_latest_time)

    # 7. Orders & Backfill
    orders_df, updated_carts_df = generate_orders(carts_df, sessions_df, users_df, session_carts_map, session_latest_time)

    # 8. Synchronize session end times so they strictly envelop all user activities
    final_sessions_df = synchronize_sessions(sessions_df, session_latest_time)

    # 9. Validation Suite Execution
    clean_views_df = views_df.drop(columns=["_effective_price"], errors="ignore")
    validate_all(
        users_df=users_df,
        sessions_df=final_sessions_df,
        products_df=products_df,
        searches_df=searches_df,
        views_df=clean_views_df,
        carts_df=updated_carts_df,
        orders_df=orders_df
    )

    # 10. Export & Database Creation
    export_and_database(
        users_df=users_df,
        sessions_df=final_sessions_df,
        products_df=products_df,
        searches_df=searches_df,
        views_df=clean_views_df,
        carts_df=updated_carts_df,
        orders_df=orders_df,
        base_dir=base_dir
    )

    print("\nDATA GENERATION COMPLETE!")


if __name__ == "__main__":
    main()
