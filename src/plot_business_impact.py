"""
Stage 7 Visualizations: Business Impact Model & GMV Opportunity Analysis

Generates 4 presentation-ready figures saved in reports/figures/:
  1. reports/figures/26_gmv_by_ctr_scenario.png (Gross & Net GMV across CTR Lifts)
  2. reports/figures/27_recovery_ctr_heatmap.png (Recovery Rate x CTR Lift Sensitivity Matrix)
  3. reports/figures/28_funnel_impact_comparison.png (Baseline vs Target Funnel Progression)
  4. reports/figures/29_cannibalization_tornado.png (Cannibalization Erosion & Sensitivity Tornado)
"""

import math
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.business_impact import BusinessImpactModel

FIGURES_DIR = REPO_ROOT / "reports" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Segoe UI", "DejaVu Sans", "Helvetica", "Arial"]
plt.rcParams["font.size"] = 10
plt.rcParams["axes.titlesize"] = 12
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.labelsize"] = 11
plt.rcParams["figure.titlesize"] = 14


def plot_chart_26_gmv_by_ctr(model: BusinessImpactModel) -> None:
    """Chart 26: Incremental Gross & Net GMV across CTR Scenarios."""
    scenarios = [
        ("Conservative\n(+1.0 pp)", 0.010),
        ("Moderate\n(+1.5 pp)", 0.015),
        ("Target MDE\n(+3.5 pp)", 0.035),
        ("Optimistic\n(+5.0 pp)", 0.050),
    ]

    labels = [s[0] for s in scenarios]
    gross_annual = []
    net_annual_25cann = []
    inc_orders = []

    for _, lift in scenarios:
        res_gross = model.calculate_scenario("G", ctr_lift_pp=lift, cannibalization_rate=0.0)
        res_net = model.calculate_scenario("N", ctr_lift_pp=lift, cannibalization_rate=0.25)
        gross_annual.append(res_gross.annualized_gross_gmv)
        net_annual_25cann.append(res_net.annualized_net_gmv)
        inc_orders.append(res_gross.incremental_orders * (365.0 / 60.0))

    x = np.arange(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    rects1 = ax.bar(x - width/2, gross_annual, width, label="Gross Annualized GMV (0% Cannibalization) [MODELED]", color="#0284c7", edgecolor="#0369a1")
    rects2 = ax.bar(x + width/2, net_annual_25cann, width, label="Net Annualized GMV (25% Cannibalization) [MODELED]", color="#0d9488", edgecolor="#0f766e")

    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f"${h:,.0f}", xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9, weight="bold", color="#0369a1")

    for rect in rects2:
        h = rect.get_height()
        ax.annotate(f"${h:,.0f}", xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9, color="#0f766e")

    ax.set_ylabel("Annualized Incremental GMV ($)")
    ax.set_title("Modeled Annualized GMV Opportunity by CTR Scenario (91.81% Recovery) [MODELED]", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, max(gross_annual) * 1.25)
    ax.legend(loc="upper left", framealpha=0.95)
    plt.tight_layout()

    save_path = FIGURES_DIR / "26_gmv_by_ctr_scenario.png"
    fig.savefig(save_path, dpi=300)
    plt.close(fig)
    print(f"Saved {save_path}")


def plot_chart_27_heatmap(model: BusinessImpactModel) -> None:
    """Chart 27: Annualized GMV Sensitivity Heatmap (Recovery Rate x CTR Lift)."""
    df_mat = model.run_recovery_ctr_matrix(cannibalization_rate=0.0)
    data = df_mat.values

    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
    cax = ax.imshow(data, cmap="YlGnBu", aspect="auto")

    # Annotate numbers in each cell
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = data[i, j]
            color = "white" if val > 1500 else "black"
            ax.text(j, i, f"${val:,.0f}", ha="center", va="center", color=color, fontsize=10, weight="bold")

    ax.set_xticks(np.arange(len(df_mat.columns)))
    ax.set_yticks(np.arange(len(df_mat.index)))
    ax.set_xticklabels(df_mat.columns, fontsize=10, weight="bold")
    ax.set_yticklabels(df_mat.index, fontsize=10, weight="bold")

    ax.set_xlabel("Search -> PDP CTR Lift (Percentage Points)", labelpad=10)
    ax.set_ylabel("Algorithmic Query Recovery Rate", labelpad=10)
    ax.set_title("Annualized Incremental GMV ($): Recovery Rate vs CTR Lift [MODELED]", pad=15)

    cbar = fig.colorbar(cax)
    cbar.set_label("Annualized Incremental GMV ($)", rotation=276, labelpad=18)

    plt.tight_layout()
    save_path = FIGURES_DIR / "27_recovery_ctr_heatmap.png"
    fig.savefig(save_path, dpi=300)
    plt.close(fig)
    print(f"Saved {save_path}")


def plot_chart_28_funnel_comparison(model: BusinessImpactModel) -> None:
    """Chart 28: Funnel Impact Comparison (Baseline vs Target Scenario D)."""
    b = model.baseline
    t = model.calculate_scenario("Target", ctr_lift_pp=0.035)

    stages = ["Eligible Searches", "PDP Clicks", "Cart Adds", "Orders"]
    baseline_vals = [b.eligible_searches, b.searches_with_pdp_click, b.cart_items_count, b.orders_count]
    target_vals = [
        b.eligible_searches,
        b.searches_with_pdp_click + t.incremental_pdp_views,
        b.cart_items_count + t.incremental_carts,
        b.orders_count + t.incremental_orders,
    ]

    x = np.arange(len(stages))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    rects1 = ax.bar(x - width/2, baseline_vals, width, label="Observed 60-Day Baseline [OBSERVED]", color="#64748b", edgecolor="#334155")
    rects2 = ax.bar(x + width/2, target_vals, width, label="Target Treatment (+3.5 pp CTR Lift) [MODELED]", color="#2563eb", edgecolor="#1d4ed8")

    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f"{h:.1f}" if h < 10 else f"{int(h)}", xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9, color="#334155")

    for idx, rect in enumerate(rects2):
        h = rect.get_height()
        diff = h - baseline_vals[idx]
        lift_str = f" (+{diff:.1f})" if diff > 0 else ""
        ax.annotate(f"{h:.1f}{lift_str}", xy=(rect.get_x() + rect.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9, weight="bold", color="#1d4ed8")

    ax.set_ylabel("Volume (Count of Events in 60-Day Window)")
    ax.set_yscale("log")
    ax.set_title("Downstream Funnel Progression: Baseline vs Target Treatment [MODELED]", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(stages, weight="bold")
    ax.set_ylim(0.5, 3000)
    ax.legend(loc="upper right", framealpha=0.95)
    plt.tight_layout()

    save_path = FIGURES_DIR / "28_funnel_impact_comparison.png"
    fig.savefig(save_path, dpi=300)
    plt.close(fig)
    print(f"Saved {save_path}")


def plot_chart_29_tornado(model: BusinessImpactModel) -> None:
    """Chart 29: Sensitivity Tornado Chart for Key Model Drivers."""
    df_sens = model.run_sensitivity_ranking()
    base_res = model.calculate_scenario("Base", ctr_lift_pp=0.035)
    base_gmv = base_res.annualized_net_gmv

    variables = df_sens["variable"].tolist()[::-1]  # reverse for bottom-to-top plotting
    low_swings = [(v - base_gmv) for v in df_sens["low_gmv"].tolist()[::-1]]
    high_swings = [(v - base_gmv) for v in df_sens["high_gmv"].tolist()[::-1]]

    y_pos = np.arange(len(variables))

    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    # Plot negative bars
    ax.barh(y_pos, low_swings, align="center", color="#ef4444", alpha=0.85, label="-20% Parameter Shock")
    # Plot positive bars
    ax.barh(y_pos, high_swings, align="center", color="#22c55e", alpha=0.85, label="+20% Parameter Shock")

    ax.axvline(0, color="#334155", linewidth=1.5, linestyle="-")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(variables, fontsize=10, weight="bold")
    ax.set_xlabel("Deviation from Base Annualized GMV ($1,809) [MODELED]")
    ax.set_title("Sensitivity Tornado: Elasticity of Annualized GMV to +/-20% Shocks [MODELED]", pad=15)
    ax.legend(loc="lower right", framealpha=0.95)
    plt.tight_layout()

    save_path = FIGURES_DIR / "29_cannibalization_tornado.png"
    fig.savefig(save_path, dpi=300)
    plt.close(fig)
    print(f"Saved {save_path}")


def main() -> None:
    model = BusinessImpactModel()
    print("Generating Stage 7 Business Impact Visualizations...")
    plot_chart_26_gmv_by_ctr(model)
    plot_chart_27_heatmap(model)
    plot_chart_28_funnel_comparison(model)
    plot_chart_29_tornado(model)
    print("Completed all Stage 7 figures.")


if __name__ == "__main__":
    main()
