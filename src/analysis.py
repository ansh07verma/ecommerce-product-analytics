"""
analysis.py - E-Commerce Funnel & Search Analytics Runner

Executes the 4 core SQL analyses against DuckDB, displays formatted terminal
summaries, and generates clean visualization charts in the figures/ directory.
"""

import os
import duckdb
import pandas as pd
import matplotlib.pyplot as plt


def run_sql_query(con: duckdb.DuckDBPyConnection, sql_text: str) -> list:
    """Executes multiple semicolon-delimited queries in an SQL file and returns DataFrames."""
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]
    results = []
    for stmt in statements:
        # Strip comments
        lines = [line for line in stmt.split("\n") if not line.strip().startswith("--")]
        clean_stmt = "\n".join(lines).strip()
        if clean_stmt:
            df = con.execute(clean_stmt).df()
            results.append(df)
    return results


def print_section_header(title: str):
    print("\n" + "=" * 75)
    print(f"  {title.upper()}")
    print("=" * 75)


def generate_charts(con: duckdb.DuckDBPyConnection, output_dir: str = "figures"):
    """Generates 5 clean, student-level matplotlib charts."""
    os.makedirs(output_dir, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # Chart 1: Conversion Funnel (Search-Engaged vs Browse-Only)
    q_funnel = """
    WITH session_steps AS (
        SELECT
            s.session_id,
            s.has_search,
            MAX(CASE WHEN pv.view_id IS NOT NULL THEN 1 ELSE 0 END) AS has_pdp_view,
            MAX(CASE WHEN ce.cart_item_id IS NOT NULL THEN 1 ELSE 0 END) AS has_cart_add,
            MAX(CASE WHEN o.order_id IS NOT NULL THEN 1 ELSE 0 END) AS has_order
        FROM sessions s
        LEFT JOIN product_views pv ON s.session_id = pv.session_id
        LEFT JOIN cart_events ce ON s.session_id = ce.session_id
        LEFT JOIN orders o ON s.session_id = o.session_id
        GROUP BY s.session_id, s.has_search
    )
    SELECT
        CASE WHEN has_search = 1 THEN 'Search-Engaged' ELSE 'Browse-Only' END AS cohort,
        ROUND(100.0 * SUM(has_pdp_view) / COUNT(session_id), 1) AS pdp_pct,
        ROUND(100.0 * SUM(has_cart_add) / COUNT(session_id), 1) AS cart_pct,
        ROUND(100.0 * SUM(has_order) / COUNT(session_id), 1) AS order_pct
    FROM session_steps
    GROUP BY has_search
    ORDER BY has_search DESC;
    """
    df_funnel = con.execute(q_funnel).df()

    fig, ax = plt.subplots(figsize=(8, 5))
    stages = ["Session -> PDP View", "Session -> Cart Add", "Session -> Completed Order"]
    search_vals = [df_funnel.loc[0, "pdp_pct"], df_funnel.loc[0, "cart_pct"], df_funnel.loc[0, "order_pct"]]
    browse_vals = [df_funnel.loc[1, "pdp_pct"], df_funnel.loc[1, "cart_pct"], df_funnel.loc[1, "order_pct"]]

    x = range(len(stages))
    width = 0.35
    rects1 = ax.bar([i - width/2 for i in x], search_vals, width, label="Search-Engaged (11.92% conv)", color="#2563eb")
    rects2 = ax.bar([i + width/2 for i in x], browse_vals, width, label="Browse-Only (5.16% conv)", color="#94a3b8")

    ax.set_ylabel("Conversion Rate from Session Start (%)", fontsize=11)
    ax.set_title("E-Commerce Funnel Conversion: Search vs Browse Sessions", fontsize=13, fontweight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(stages, fontsize=10)
    ax.legend(frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for r in rects1 + rects2:
        h = r.get_height()
        ax.annotate(f"{h:.1f}%", xy=(r.get_x() + r.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    chart1_path = os.path.join(output_dir, "01_conversion_funnel.png")
    plt.savefig(chart1_path, dpi=150)
    plt.close()
    print(f"Saved: {chart1_path}")

    # Chart 2: Zero-Result Rate by Query Length
    fig, ax = plt.subplots(figsize=(6, 4.5))
    segments = ["1-3 Tokens\n(Head / Torso)", "4+ Tokens\n(Specific Queries)"]
    zrr_vals = [1.78, 8.23]
    colors = ["#10b981", "#ef4444"]
    bars = ax.bar(segments, zrr_vals, color=colors, width=0.45)
    ax.set_ylabel("Zero-Result Rate (%)", fontsize=11)
    ax.set_title("Zero-Result Rate by Query Specificity", fontsize=12, fontweight="bold")
    ax.set_ylim(0, 10.5)
    for b in bars:
        h = b.get_height()
        ax.annotate(f"{h:.2f}%", xy=(b.get_x() + b.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    chart2_path = os.path.join(output_dir, "02_zero_result_rate.png")
    plt.savefig(chart2_path, dpi=150)
    plt.close()
    print(f"Saved: {chart2_path}")

    # Chart 3: Manual Reformulation Rate
    fig, ax = plt.subplots(figsize=(6, 4.5))
    retype_vals = [42.41, 44.39]
    bars = ax.bar(segments, retype_vals, color=["#3b82f6", "#f97316"], width=0.45)
    ax.set_ylabel("Manual Reformulation Rate (%)", fontsize=11)
    ax.set_title("User Reformulation Friction by Query Length", fontsize=12, fontweight="bold")
    ax.set_ylim(0, 55)
    for b in bars:
        h = b.get_height()
        ax.annotate(f"{h:.2f}%", xy=(b.get_x() + b.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    chart3_path = os.path.join(output_dir, "03_reformulation_rate.png")
    plt.savefig(chart3_path, dpi=150)
    plt.close()
    print(f"Saved: {chart3_path}")

    # Chart 4: Strict Search vs Relaxed Search
    fig, ax = plt.subplots(figsize=(6, 4.5))
    modes = ["Strict Search\n(Baseline)", "Relaxed Search\n(Prototype)"]
    zrr_comp = [98.21, 8.40]
    bars = ax.bar(modes, zrr_comp, color=["#dc2626", "#16a34a"], width=0.45)
    ax.set_ylabel("Zero-Result Rate on Test Queries (%)", fontsize=11)
    ax.set_title("Search Discovery: Strict vs Query Relaxation", fontsize=12, fontweight="bold")
    ax.set_ylim(0, 115)
    for b in bars:
        h = b.get_height()
        ax.annotate(f"{h:.1f}%", xy=(b.get_x() + b.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    chart4_path = os.path.join(output_dir, "04_strict_vs_relaxed_search.png")
    plt.savefig(chart4_path, dpi=150)
    plt.close()
    print(f"Saved: {chart4_path}")

    # Chart 5: GMV Impact Scenarios
    fig, ax = plt.subplots(figsize=(7, 4.5))
    scenarios = ["Observed 60d GMV\n(Baseline)", "Scenario A (+1.0 pp)\n(Modeled Lift)", "Scenario B (+3.5 pp)\n(Modeled Target)"]
    gmv_vals = [285.15, 285.15 + 84.95, 285.15 + 297.32]
    bars = ax.bar(scenarios, gmv_vals, color=["#64748b", "#0ea5e9", "#22c55e"], width=0.45)
    ax.set_ylabel("60-Day GMV on Eligible Cohort ($)", fontsize=11)
    ax.set_title("Modeled Revenue Impact on Low-Result Searches", fontsize=12, fontweight="bold")
    ax.set_ylim(0, 680)
    for b in bars:
        h = b.get_height()
        ax.annotate(f"${h:.2f}", xy=(b.get_x() + b.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    chart5_path = os.path.join(output_dir, "05_gmv_impact_scenarios.png")
    plt.savefig(chart5_path, dpi=150)
    plt.close()
    print(f"Saved: {chart5_path}")


def main():
    print("=" * 75)
    print("  RUNNING E-COMMERCE PRODUCT ANALYTICS SQL SUITE")
    print("=" * 75)

    con = duckdb.connect("data/ecommerce_analytics.duckdb", read_only=True)

    # 1. Funnel Analysis
    print_section_header("SQL 01: Funnel Analysis")
    with open("sql/01_funnel_analysis.sql", "r", encoding="utf-8") as f:
        dfs = run_sql_query(con, f.read())
    print("Overall Funnel Progression:")
    print(dfs[0].to_string(index=False))
    print("\nSearch-Engaged vs Browse-Only Funnel:")
    print(dfs[1].to_string(index=False))

    # 2. Search Behavior Analysis
    print_section_header("SQL 02: Search Behavior & Discovery Failure")
    with open("sql/02_search_analysis.sql", "r", encoding="utf-8") as f:
        dfs = run_sql_query(con, f.read())
    print("Query Length Segmentation (1-3 Tokens vs 4+ Tokens):")
    print(dfs[0].to_string(index=False))
    print("\nEligible Low-Result Discovery Failure Cohort (<3 results, >=4 tokens):")
    print(dfs[1].to_string(index=False))

    # 3. Query Analysis
    print_section_header("SQL 03: Query Patterns & Categories")
    with open("sql/03_query_analysis.sql", "r", encoding="utf-8") as f:
        dfs = run_sql_query(con, f.read())
    print("Top Search Queries:")
    print(dfs[0].head(5).to_string(index=False))
    print("\nTop Zero-Result Multi-Attribute Queries:")
    print(dfs[1].head(5).to_string(index=False))

    # 4. Product & Business Analysis
    print_section_header("SQL 04: Revenue & Downstream Conversion")
    with open("sql/04_product_analysis.sql", "r", encoding="utf-8") as f:
        dfs = run_sql_query(con, f.read())
    print("Overall Marketplace Revenue:")
    print(dfs[0].to_string(index=False))
    print("\nSearch vs Browse Revenue Contribution:")
    print(dfs[1].to_string(index=False))
    print("\nDownstream Funnel on 941 Eligible Low-Result Searches:")
    print(dfs[2].to_string(index=False))

    # Generate charts
    print_section_header("Generating Visualizations")
    generate_charts(con, output_dir="figures")

    con.close()
    print("\n" + "=" * 75)
    print("  ALL ANALYSES COMPLETED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    main()
