"""
Stage 6 Visualizations: A/B Experiment Analysis & Experiment Design

Generates 3 presentation-ready figures:
  1. reports/figures/23_experiment_ctr_comparison.png (Control vs Treatment CTR by Scenario)
  2. reports/figures/24_sample_size_vs_mde.png (Sample Size & Duration vs MDE Curve)
  3. reports/figures/25_daily_monitoring_lift.png (Sequential Experiment Trajectory & Peeking Warning)
"""

import math
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ab_experiment import ABExperimentSimulator

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


def plot_chart_23_ctr_comparison(simulator: ABExperimentSimulator) -> None:
    """Chart 23: Control vs Treatment CTR across Scenarios with 95% CIs."""
    scenarios = [
        ("Scenario A\n(Null 0.0pp)", 0.000),
        ("Scenario B\n(+1.0pp)", 0.010),
        ("Scenario C\n(+1.5pp)", 0.015),
        ("Scenario D\n(+3.5pp Target)", 0.035),
        ("Scenario E\n(+5.0pp)", 0.050),
    ]

    labels = []
    c_ctrs = []
    t_ctrs = []
    ci_err_lower = []
    ci_err_upper = []
    decisions = []

    for name, lift in scenarios:
        df = simulator.generate_experiment_dataset(treatment_lift_pp=lift)
        sum_res = simulator.analyze_experiment(df)
        labels.append(name)
        c_ctrs.append(sum_res.control_ctr * 100.0)
        t_ctrs.append(sum_res.treatment_ctr * 100.0)
        p_t = sum_res.treatment_ctr
        se_t = math.sqrt(p_t * (1 - p_t) / sum_res.treatment_n) * 100.0
        ci_err_lower.append(1.96 * se_t)
        ci_err_upper.append(1.96 * se_t)
        decisions.append(sum_res.decision)

    x = np.arange(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    rects1 = ax.bar(x - width/2, c_ctrs, width, label="Control: Strict Search [OBSERVED]", color="#64748b", edgecolor="#334155")
    rects2 = ax.bar(
        x + width/2,
        t_ctrs,
        width,
        yerr=[ci_err_lower, ci_err_upper],
        capsize=4,
        label="Treatment: Strict + Query Relaxation [SIMULATED]",
        color="#2563eb",
        edgecolor="#1d4ed8"
    )

    ax.axhline(3.08, color="#dc2626", linestyle="--", alpha=0.7, label="Historical Baseline CTR (3.08% [OBSERVED])")

    for idx, (rect, dec) in enumerate(zip(rects2, decisions)):
        height = rect.get_height()
        color = "#16a34a" if dec == "SHIP" else ("#d97706" if dec == "ITERATE" else "#dc2626")
        ax.annotate(
            f"{dec}\n({t_ctrs[idx]:.2f}%)",
            xy=(rect.get_x() + rect.get_width() / 2, height + ci_err_upper[idx] + 0.3),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center", va="bottom",
            fontsize=9, weight="bold", color=color
        )

    for rect in rects1:
        height = rect.get_height()
        ax.annotate(
            f"{height:.2f}%",
            xy=(rect.get_x() + rect.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center", va="bottom",
            fontsize=9, color="#334155"
        )

    ax.set_ylabel("Search -> PDP Click-Through Rate (%)")
    ax.set_title("Search -> PDP CTR by Scenario: Control vs Treatment [SIMULATED]", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 10.0)
    ax.legend(loc="upper left", framealpha=0.95)
    plt.tight_layout()

    save_path = FIGURES_DIR / "23_experiment_ctr_comparison.png"
    fig.savefig(save_path, dpi=300)
    plt.close(fig)
    print(f"Saved {save_path}")


def plot_chart_24_power_curve(simulator: ABExperimentSimulator) -> None:
    """Chart 24: Required Sample Size & Experiment Duration vs MDE."""
    mde_sweep = np.linspace(0.008, 0.060, 100)
    n_total = []
    durations = []

    for mde in mde_sweep:
        _, total_n = simulator.calculate_sample_size(simulator.baseline_ctr, mde)
        days = total_n / simulator.modeled_daily_eligible
        n_total.append(total_n)
        durations.append(days)

    fig, ax1 = plt.subplots(figsize=(10, 6), dpi=300)

    color_n = "#0284c7"
    ax1.set_xlabel("Minimum Detectable Effect (MDE in Percentage Points)")
    ax1.set_ylabel("Total Required Sample Size (Control + Treatment)", color=color_n)
    line1 = ax1.plot(mde_sweep * 100.0, n_total, color=color_n, linewidth=2.5, label="Required Sample Size (alpha=0.05, power=0.80)")
    ax1.tick_params(axis="y", labelcolor=color_n)
    ax1.set_yscale("log")
    ax1.grid(True, which="both", linestyle="--", alpha=0.5)

    ax2 = ax1.twinx()
    color_days = "#d97706"
    ax2.set_ylabel("Modeled Duration in Days (~15.7 searches/day) [MODELED]", color=color_days)
    line2 = ax2.plot(mde_sweep * 100.0, durations, color=color_days, linewidth=2.5, linestyle="-.", label="Modeled Duration (Days)")
    ax2.tick_params(axis="y", labelcolor=color_days)
    ax2.set_yscale("log")

    _, n_target = simulator.calculate_sample_size(simulator.baseline_ctr, 0.035)
    days_target = n_target / simulator.modeled_daily_eligible
    ax1.plot([3.5], [n_target], marker="o", markersize=8, color="#dc2626")
    ax1.annotate(
        f"Target MDE (+3.5 pp)\nTotal N = {n_target:,}\n~{math.ceil(days_target)} days (~2.5 mo)",
        xy=(3.5, n_target),
        xytext=(4.2, n_target * 1.5),
        arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1.5),
        fontsize=9, weight="bold", color="#dc2626"
    )

    _, n_15 = simulator.calculate_sample_size(simulator.baseline_ctr, 0.015)
    days_15 = n_15 / simulator.modeled_daily_eligible
    ax1.plot([1.5], [n_15], marker="s", markersize=8, color="#7c3aed")
    ax1.annotate(
        f"Min Ship (+1.5 pp)\nTotal N = {n_15:,}\n~{math.ceil(days_15)} days (~10.9 mo)",
        xy=(1.5, n_15),
        xytext=(2.0, n_15 * 1.2),
        arrowprops=dict(arrowstyle="->", color="#7c3aed", lw=1.5),
        fontsize=9, weight="bold", color="#7c3aed"
    )

    plt.title("Statistical Power Curve: Sample Size & Duration vs MDE [MODELED]", pad=15)
    plt.tight_layout()

    save_path = FIGURES_DIR / "24_sample_size_vs_mde.png"
    fig.savefig(save_path, dpi=300)
    plt.close(fig)
    print(f"Saved {save_path}")


def plot_chart_25_daily_monitoring(simulator: ABExperimentSimulator) -> None:
    """Chart 25: Sequential Experiment Monitoring & Peeking Hazard Demonstration."""
    df_daily = simulator.run_sequential_simulation(days=60, treatment_lift_pp=0.035)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), dpi=300, sharex=True)

    days = df_daily["day"]
    lift = df_daily["absolute_lift_pp"]
    ci_low = df_daily["ci_lower_pp"]
    ci_high = df_daily["ci_upper_pp"]

    ax1.plot(days, lift, color="#2563eb", linewidth=2, label="Cumulative Absolute Lift (pp)")
    ax1.fill_between(days, ci_low, ci_high, color="#93c5fd", alpha=0.35, label="95% Confidence Interval")
    ax1.axhline(0.0, color="#64748b", linestyle="-", linewidth=1)
    ax1.axhline(1.5, color="#16a34a", linestyle="--", linewidth=1.5, label="Min Practical Ship Threshold (+1.5 pp) [PRODUCT ASSUMPTION]")
    ax1.set_ylabel("Absolute Lift (pp)")
    ax1.set_title("Sequential Experiment Monitoring Simulation (Target Scenario D: +3.5 pp MDE)", pad=10)
    ax1.legend(loc="upper right", framealpha=0.9)
    ax1.grid(True, linestyle="--", alpha=0.5)

    p_vals = df_daily["p_value"]
    ax2.plot(days, p_vals, color="#7c3aed", linewidth=2, label="Cumulative P-Value (Two-Proportion Z-Test)")
    ax2.axhline(0.05, color="#dc2626", linestyle="--", linewidth=1.5, label="Significance Threshold (alpha = 0.05)")
    ax2.fill_between(days, 0, 0.05, color="#fee2e2", alpha=0.5, label="Statistically Significant Zone (p < 0.05)")

    ax2.annotate(
        "PEEKING HAZARD WARNING:\nEarly p < 0.05 bounces can create false positives!\nDo NOT stop early without sequential testing correction.",
        xy=(15, 0.08),
        xytext=(20, 0.25),
        arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1.5),
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#fff1f2", edgecolor="#fda4af"),
        fontsize=9, weight="bold", color="#991b1b"
    )

    ax2.set_xlabel("Experiment Day (Simulated Daily Traffic Accumulation)")
    ax2.set_ylabel("P-Value")
    ax2.set_ylim(0, 1.0)
    ax2.legend(loc="upper right", framealpha=0.9)
    ax2.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    save_path = FIGURES_DIR / "25_daily_monitoring_lift.png"
    fig.savefig(save_path, dpi=300)
    plt.close(fig)
    print(f"Saved {save_path}")


def main() -> None:
    simulator = ABExperimentSimulator()
    print("Generating Stage 6 Experiment Visualizations...")
    plot_chart_23_ctr_comparison(simulator)
    plot_chart_24_power_curve(simulator)
    plot_chart_25_daily_monitoring(simulator)
    print("Completed all Stage 6 figures.")


if __name__ == "__main__":
    main()
