import os
import math
import numpy as np
import pandas as pd
import duckdb
from scipy import stats
import matplotlib.pyplot as plt

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'ecommerce_analytics.duckdb')
FIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports', 'figures')

def get_db_connection(read_only: bool = True):
    """Establish connection to DuckDB analytical database."""
    return duckdb.connect(DB_PATH, read_only=read_only)

def load_table(table_name: str, con=None) -> pd.DataFrame:
    """Load an entire table from DuckDB into a Pandas DataFrame."""
    should_close = False
    if con is None:
        con = get_db_connection()
        should_close = True
    df = con.execute(f"SELECT * FROM {table_name}").df()
    if should_close:
        con.close()
    return df

def run_query(query: str, con=None) -> pd.DataFrame:
    """Execute arbitrary analytical query against DuckDB."""
    should_close = False
    if con is None:
        con = get_db_connection()
        should_close = True
    df = con.execute(query).df()
    if should_close:
        con.close()
    return df

def calc_proportion_ci(k: int, n: int, confidence: float = 0.95):
    """
    Calculate Wilson Score Confidence Interval for a proportion.
    Superior to normal approximation for small n or extreme p.
    """
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    z = stats.norm.ppf((1 + confidence) / 2)
    denom = 1 + (z ** 2) / n
    centre = (p + (z ** 2) / (2 * n)) / denom
    margin = (z * math.sqrt((p * (1 - p) / n) + (z ** 2) / (4 * (n ** 2)))) / denom
    ci_lower = max(0.0, centre - margin)
    ci_upper = min(1.0, centre + margin)
    return p, ci_lower, ci_upper

def two_proportion_z_test(k1: int, n1: int, k2: int, n2: int):
    """
    Perform two-proportion two-tailed hypothesis z-test.
    Returns: diff, z_stat, p_value, (ci_lower, ci_upper)
    """
    p1 = k1 / n1
    p2 = k2 / n2
    diff = p1 - p2
    p_pool = (k1 + k2) / (n1 + n2)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z_stat = diff / se_pool if se_pool > 0 else 0.0
    p_val = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    se_diff = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    ci = (diff - 1.96 * se_diff, diff + 1.96 * se_diff)
    return diff, z_stat, p_val, ci

def calc_odds_ratio(k1: int, n1: int, k2: int, n2: int):
    """
    Calculate Odds Ratio (OR) and 95% Wald CI.
    k1/n1: group 1 success
    k2/n2: group 2 success
    """
    a = k1
    b = n1 - k1
    c = k2
    d = n2 - k2
    if b == 0 or c == 0:
        return np.nan, np.nan, np.nan
    or_val = (a * d) / (b * c)
    se_log_or = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    ci_lower = math.exp(math.log(or_val) - 1.96 * se_log_or)
    ci_upper = math.exp(math.log(or_val) + 1.96 * se_log_or)
    return or_val, ci_lower, ci_upper

def calculate_funnel_summary(con=None):
    """Calculate standard session-level conversion funnel metrics."""
    q = """
    SELECT 
        COUNT(DISTINCT s.session_id) AS total_sessions,
        COUNT(DISTINCT pv.session_id) AS pdp_sessions,
        COUNT(DISTINCT ce.session_id) AS cart_sessions,
        COUNT(DISTINCT o.session_id) AS order_sessions
    FROM sessions s
    LEFT JOIN product_views pv ON s.session_id = pv.session_id
    LEFT JOIN cart_events ce ON s.session_id = ce.session_id
    LEFT JOIN orders o ON s.session_id = o.session_id
    """
    df = run_query(q, con)
    s = df.iloc[0]
    stages = [
        {"stage": "1. Total Sessions", "n": int(s['total_sessions']), "step_cr": 1.0, "overall_cr": 1.0},
        {"stage": "2. PDP View", "n": int(s['pdp_sessions']), "step_cr": s['pdp_sessions']/s['total_sessions'], "overall_cr": s['pdp_sessions']/s['total_sessions']},
        {"stage": "3. Add to Cart", "n": int(s['cart_sessions']), "step_cr": s['cart_sessions']/s['pdp_sessions'], "overall_cr": s['cart_sessions']/s['total_sessions']},
        {"stage": "4. Order Placed", "n": int(s['order_sessions']), "step_cr": s['order_sessions']/s['cart_sessions'], "overall_cr": s['order_sessions']/s['total_sessions']}
    ]
    return pd.DataFrame(stages)

if __name__ == '__main__':
    print("Testing exploratory_analysis module...")
    funnel = calculate_funnel_summary()
    print("Funnel Metrics:")
    print(funnel)
    diff, z, p, ci = two_proportion_z_test(8286, 41766, 77, 2807)
    print(f"\nSizing In-Stock vs Out-Stock Z-Test: Diff={diff:.4f}, Z={z:.2f}, p={p:.2e}, 95% CI=[{ci[0]:.4f}, {ci[1]:.4f}]")
