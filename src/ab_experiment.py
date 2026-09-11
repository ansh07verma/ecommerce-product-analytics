"""
A/B Experiment Simulator & Experiment Design Engine (Stage 6)

Offline A/B experiment simulator for evaluating Automated Query Relaxation vs
Strict Search on high-intent, multi-attribute queries in an e-commerce marketplace.

Primary Metric:
  Search -> PDP CTR on eligible search events (>=4 tokens, strict results < 3).

Baseline [OBSERVED]:
  3.08% (29 clicks / 941 eligible opportunities in historical dataset).

Randomization Unit:
  User-level deterministic hashing: hash(experiment_id + user_id) % 100
  - 0-49: Control (Strict Search)
  - 50-99: Treatment (Strict Search + Query Relaxation)

Data Honesty Tags:
  [OBSERVED]          - Extracted directly from historical dataset
  [LOCAL BENCHMARK]   - Measured on local search engine / query relaxation
  [SIMULATED]         - Generated counterfactual treatment outcome
  [MODELED]           - Projected downstream business metric
  [PRODUCT ASSUMPTION]- PM/business decision rule or threshold
"""

import argparse
import hashlib
import json
import math
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.search_engine import LocalSearchEngine


@dataclass
class ExperimentSummary:
    experiment_id: str
    alpha: float
    power: float
    target_mde: float
    total_eligible: int
    control_n: int
    control_conversions: int
    control_ctr: float
    treatment_n: int
    treatment_conversions: int
    treatment_ctr: float
    absolute_lift_pp: float
    relative_lift_pct: float
    pooled_p: float
    standard_error: float
    z_score: float
    p_value: float
    ci_95_lower_pp: float
    ci_95_upper_pp: float
    statistically_significant: bool
    practically_significant: bool
    decision: str
    decision_rationale: str
    incremental_clicks: int
    incremental_orders: int
    incremental_gmv: float
    annualized_gmv: float


class ABExperimentSimulator:
    """Offline A/B Experiment Simulator & Design Engine."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        experiment_id: str = "exp_query_relaxation_v1",
        seed: int = 42,
    ):
        self.experiment_id = experiment_id
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        if db_path is None:
            self.db_path = str(REPO_ROOT / "data" / "ecommerce_analytics.duckdb")
        else:
            self.db_path = db_path

        # Baseline parameters [OBSERVED]
        self.baseline_ctr = 0.030818  # 29 / 941
        self.observed_pdp_to_cart = 7 / 29  # 24.14%
        self.observed_cart_to_order = 2 / 7  # 28.57%
        self.observed_avg_order_gmv = 142.575  # $285.15 / 2
        self.modeled_daily_eligible = 15.683  # 941 / 60 days

        # Ship decision thresholds [PRODUCT ASSUMPTION]
        self.min_detectable_effect = 0.035  # +3.5 pp
        self.ship_threshold_lift_pp = 1.5  # +1.5 pp minimum practical significance
        self.significance_level = 0.05  # alpha
        self.target_power = 0.80  # 1 - beta

    @staticmethod
    def assign_variant(experiment_id: str, user_id: str) -> str:
        """
        Deterministic user-level hash bucket.
        0-49: Control, 50-99: Treatment.
        Uses MD5 for guaranteed platform-independent determinism.
        """
        combined = f"{experiment_id}:{user_id}".encode("utf-8")
        hash_val = int(hashlib.md5(combined).hexdigest(), 16)
        bucket = hash_val % 100
        return "Control" if bucket < 50 else "Treatment"

    @staticmethod
    def is_eligible(query_text: str, strict_results_count: int) -> bool:
        """
        Eligibility rule:
        1. >= 4 meaningful tokens
        2. Strict search returns < 3 results
        """
        if not query_text:
            return False
        tokens = [t for t in query_text.strip().split() if len(t) > 0]
        return len(tokens) >= 4 and strict_results_count < 3

    def load_eligible_searches_from_db(self) -> pd.DataFrame:
        """
        Loads eligible searches and traces real observed downstream conversion events
        from DuckDB relational tables.
        """
        con = duckdb.connect(self.db_path, read_only=True)
        query = """
        WITH search_base AS (
            SELECT 
                s.search_id,
                s.session_id,
                s.user_id,
                s.query_text,
                s.results_count AS strict_result_count,
                s.is_zero_result,
                s.search_timestamp,
                ARRAY_LENGTH(STRING_SPLIT(TRIM(s.query_text), ' ')) AS token_count,
                s.has_pdp_click AS observed_has_pdp_click
            FROM search_events s
            WHERE ARRAY_LENGTH(STRING_SPLIT(TRIM(s.query_text), ' ')) >= 4
              AND s.results_count < 3
        ),
        pdp_agg AS (
            SELECT 
                search_id,
                COUNT(*) AS pdp_views_count,
                MAX(added_to_cart) AS had_cart_add
            FROM product_views
            WHERE search_id IS NOT NULL
            GROUP BY search_id
        ),
        cart_agg AS (
            SELECT 
                pv.search_id,
                COUNT(c.cart_item_id) AS cart_items_count,
                MAX(c.is_purchased) AS had_purchase
            FROM cart_events c
            JOIN product_views pv ON c.view_id = pv.view_id
            WHERE pv.search_id IS NOT NULL
            GROUP BY pv.search_id
        ),
        order_agg AS (
            SELECT 
                pv.search_id,
                COUNT(DISTINCT o.order_id) AS orders_count,
                SUM(o.gross_merchandise_value) AS total_order_gmv
            FROM orders o
            JOIN cart_events c ON o.order_id = c.order_id
            JOIN product_views pv ON c.view_id = pv.view_id
            WHERE pv.search_id IS NOT NULL
            GROUP BY pv.search_id
        )
        SELECT 
            sb.search_id,
            sb.session_id,
            sb.user_id,
            sb.query_text,
            sb.strict_result_count,
            sb.is_zero_result,
            sb.search_timestamp,
            sb.token_count,
            CASE WHEN sb.observed_has_pdp_click OR COALESCE(pa.pdp_views_count, 0) > 0 THEN 1 ELSE 0 END AS observed_pdp_view,
            CASE WHEN COALESCE(pa.had_cart_add, FALSE) OR COALESCE(ca.cart_items_count, 0) > 0 THEN 1 ELSE 0 END AS observed_cart,
            CASE WHEN COALESCE(ca.had_purchase, FALSE) OR COALESCE(oa.orders_count, 0) > 0 THEN 1 ELSE 0 END AS observed_order,
            COALESCE(oa.total_order_gmv, 0.0) AS observed_gmv
        FROM search_base sb
        LEFT JOIN pdp_agg pa ON sb.search_id = pa.search_id
        LEFT JOIN cart_agg ca ON sb.search_id = ca.search_id
        LEFT JOIN order_agg oa ON sb.search_id = oa.search_id
        ORDER BY sb.search_timestamp ASC;
        """
        df = con.execute(query).df()
        con.close()
        return df

    def generate_experiment_dataset(
        self,
        treatment_lift_pp: float = 0.035,
        engine: Optional[LocalSearchEngine] = None,
        evaluate_engine: bool = False,
    ) -> pd.DataFrame:
        """
        Generates the A/B experiment dataset.
        - Assigns users deterministically to Control vs Treatment.
        - Control outcomes: historical [OBSERVED] behavior.
        - Treatment outcomes: counterfactual [SIMULATED] behavior via treatment-effect model.
        - Treatment probability = clamp(baseline_ctr + treatment_lift_pp, 0.0, 1.0).
        """
        df = self.load_eligible_searches_from_db()
        df["experiment_id"] = self.experiment_id
        df["variant"] = df["user_id"].apply(lambda u: self.assign_variant(self.experiment_id, u))
        df["eligible"] = True

        if evaluate_engine and engine is not None:
            final_counts = []
            rel_triggered = []
            rel_statuses = []
            for _, row in df.iterrows():
                if row["variant"] == "Control":
                    final_counts.append(row["strict_result_count"])
                    rel_triggered.append(False)
                    rel_statuses.append("NONE_CONTROL")
                else:
                    res = engine.search(row["query_text"], enable_relaxation=True)
                    final_counts.append(res.total_results)
                    rel_triggered.append(res.relaxation_triggered)
                    rel_statuses.append(res.relaxation_status)
            df["final_result_count"] = final_counts
            df["relaxation_triggered"] = rel_triggered
            df["relaxation_status"] = rel_statuses
        else:
            df["final_result_count"] = np.where(
                df["variant"] == "Control",
                df["strict_result_count"],
                np.where(df["strict_result_count"] == 0, 8, df["strict_result_count"]),
            )
            df["relaxation_triggered"] = df["variant"] == "Treatment"
            df["relaxation_status"] = np.where(
                df["variant"] == "Control",
                "NONE_CONTROL",
                np.where(df["strict_result_count"] == 0, "SUCCESS", "NOT_TRIGGERED"),
            )

        pdp_views = []
        carts = []
        orders = []
        gmvs = []
        outcome_sources = []

        treatment_p = max(0.0, min(1.0, self.baseline_ctr + treatment_lift_pp))
        sim_rng = np.random.default_rng(self.seed)

        for _, row in df.iterrows():
            if row["variant"] == "Control":
                pdp_views.append(int(row["observed_pdp_view"]))
                carts.append(int(row["observed_cart"]))
                orders.append(int(row["observed_order"]))
                gmvs.append(float(row["observed_gmv"]))
                outcome_sources.append("observed")
            else:
                is_pdp = int(sim_rng.random() < treatment_p)
                pdp_views.append(is_pdp)
                if is_pdp:
                    is_cart = int(sim_rng.random() < self.observed_pdp_to_cart)
                    carts.append(is_cart)
                    if is_cart:
                        is_order = int(sim_rng.random() < self.observed_cart_to_order)
                        orders.append(is_order)
                        if is_order:
                            gmv = round(float(sim_rng.normal(self.observed_avg_order_gmv, 25.0)), 2)
                            gmvs.append(max(20.0, gmv))
                        else:
                            gmvs.append(0.0)
                    else:
                        orders.append(0)
                        gmvs.append(0.0)
                else:
                    carts.append(0)
                    orders.append(0)
                    gmvs.append(0.0)
                outcome_sources.append("simulated")

        df["pdp_view"] = pdp_views
        df["cart"] = carts
        df["order"] = orders
        df["gmv"] = gmvs
        df["outcome_source"] = outcome_sources
        return df

    @staticmethod
    def two_proportion_z_test(
        control_conversions: int,
        control_n: int,
        treatment_conversions: int,
        treatment_n: int,
        alpha: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Standard two-proportion z-test (two-sided).
        """
        if control_n <= 0 or treatment_n <= 0:
            raise ValueError("Sample sizes must be positive integers.")

        p_c = control_conversions / control_n
        p_t = treatment_conversions / treatment_n
        diff = p_t - p_c
        relative_lift = (diff / p_c) if p_c > 0 else 0.0
        pooled_p = (control_conversions + treatment_conversions) / (control_n + treatment_n)
        se_null = math.sqrt(pooled_p * (1.0 - pooled_p) * (1.0 / control_n + 1.0 / treatment_n))
        se_diff = math.sqrt((p_c * (1.0 - p_c) / control_n) + (p_t * (1.0 - p_t) / treatment_n))
        z_crit = 1.959963984540054

        if se_null > 0:
            z_score = diff / se_null
            p_value = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z_score) / math.sqrt(2.0))))
        else:
            z_score = 0.0
            p_value = 1.0

        ci_lower = diff - z_crit * se_diff
        ci_upper = diff + z_crit * se_diff

        return {
            "control_n": control_n,
            "control_conversions": control_conversions,
            "control_ctr": p_c,
            "treatment_n": treatment_n,
            "treatment_conversions": treatment_conversions,
            "treatment_ctr": p_t,
            "absolute_lift_pp": diff * 100.0,
            "relative_lift_pct": relative_lift * 100.0,
            "pooled_p": pooled_p,
            "standard_error": se_null,
            "z_score": z_score,
            "p_value": p_value,
            "ci_95_lower_pp": ci_lower * 100.0,
            "ci_95_upper_pp": ci_upper * 100.0,
            "statistically_significant": p_value < alpha,
        }

    @staticmethod
    def calculate_sample_size(
        baseline_rate: float,
        mde: float,
        alpha: float = 0.05,
        power: float = 0.80,
    ) -> Tuple[int, int]:
        """Calculates required sample size per variant for two-proportion z-test."""
        if mde <= 0:
            return (0, 0)
        p1 = baseline_rate
        p2 = baseline_rate + mde
        p_avg = (p1 + p2) / 2.0
        z_alpha = 1.959963984540054
        z_beta = 0.8416212335729143
        numerator = (
            z_alpha * math.sqrt(2 * p_avg * (1 - p_avg))
            + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
        ) ** 2
        denominator = (p2 - p1) ** 2
        n_variant = math.ceil(numerator / denominator)
        return n_variant, n_variant * 2

    def run_power_analysis(self) -> pd.DataFrame:
        mde_list = [0.010, 0.015, 0.020, 0.035, 0.050]
        records = []
        for mde in mde_list:
            n_per_var, total_n = self.calculate_sample_size(
                baseline_rate=self.baseline_ctr,
                mde=mde,
                alpha=self.significance_level,
                power=self.target_power,
            )
            modeled_days = math.ceil(total_n / self.modeled_daily_eligible)
            modeled_months = round(modeled_days / 30.0, 1)
            records.append({
                "mde_pp": round(mde * 100.0, 2),
                "target_ctr": round((self.baseline_ctr + mde) * 100.0, 2),
                "required_n_per_variant": n_per_var,
                "total_required_n": total_n,
                "daily_eligible_traffic": round(self.modeled_daily_eligible, 1),
                "modeled_duration_days": modeled_days,
                "modeled_duration_months": modeled_months,
            })
        return pd.DataFrame(records)

    def analyze_experiment(self, df: pd.DataFrame) -> ExperimentSummary:
        ctrl = df[df["variant"] == "Control"]
        trt = df[df["variant"] == "Treatment"]
        c_n = len(ctrl)
        c_conv = int(ctrl["pdp_view"].sum())
        t_n = len(trt)
        t_conv = int(trt["pdp_view"].sum())

        test_res = self.two_proportion_z_test(
            control_conversions=c_conv,
            control_n=c_n,
            treatment_conversions=t_conv,
            treatment_n=t_n,
            alpha=self.significance_level,
        )

        abs_lift_pp = test_res["absolute_lift_pp"]
        stat_sig = test_res["statistically_significant"]
        pract_sig = abs_lift_pp >= self.ship_threshold_lift_pp

        if stat_sig and pract_sig and abs_lift_pp > 0:
            decision = "SHIP"
            rationale = (
                f"Statistically significant (p={test_res['p_value']:.4f} < {self.significance_level}) "
                f"and exceeds practical significance threshold (+{self.ship_threshold_lift_pp} pp)."
            )
        elif abs_lift_pp > 0 and (not stat_sig or not pract_sig):
            decision = "ITERATE"
            rationale = (
                f"Directionally positive (+{abs_lift_pp:.2f} pp) but underpowered/inconclusive "
                f"(p={test_res['p_value']:.4f}) or below practical threshold."
            )
        else:
            decision = "DO NOT SHIP"
            rationale = f"Negative or zero lift ({abs_lift_pp:.2f} pp) relative to control."

        inc_clicks = max(0, t_conv - int(c_conv * (t_n / c_n)))
        inc_orders = int(trt["order"].sum()) - int(ctrl["order"].sum() * (t_n / c_n))
        inc_orders = max(0, int(round(inc_orders)))
        inc_gmv = max(0.0, float(trt["gmv"].sum() - ctrl["gmv"].sum() * (t_n / c_n)))
        annualized_gmv = inc_gmv * (365.0 / 60.0)

        return ExperimentSummary(
            experiment_id=self.experiment_id,
            alpha=self.significance_level,
            power=self.target_power,
            target_mde=self.min_detectable_effect,
            total_eligible=len(df),
            control_n=c_n,
            control_conversions=c_conv,
            control_ctr=test_res["control_ctr"],
            treatment_n=t_n,
            treatment_conversions=t_conv,
            treatment_ctr=test_res["treatment_ctr"],
            absolute_lift_pp=abs_lift_pp,
            relative_lift_pct=test_res["relative_lift_pct"],
            pooled_p=test_res["pooled_p"],
            standard_error=test_res["standard_error"],
            z_score=test_res["z_score"],
            p_value=test_res["p_value"],
            ci_95_lower_pp=test_res["ci_95_lower_pp"],
            ci_95_upper_pp=test_res["ci_95_upper_pp"],
            statistically_significant=stat_sig,
            practically_significant=pract_sig,
            decision=decision,
            decision_rationale=rationale,
            incremental_clicks=inc_clicks,
            incremental_orders=inc_orders,
            incremental_gmv=round(inc_gmv, 2),
            annualized_gmv=round(annualized_gmv, 2),
        )

    def run_scenario_analysis(self) -> pd.DataFrame:
        scenarios = [
            ("Scenario A (Null)", 0.000),
            ("Scenario B (+1.0 pp)", 0.010),
            ("Scenario C (+1.5 pp)", 0.015),
            ("Scenario D (+3.5 pp)", 0.035),
            ("Scenario E (+5.0 pp)", 0.050),
        ]
        rows = []
        for name, lift_pp in scenarios:
            df = self.generate_experiment_dataset(treatment_lift_pp=lift_pp)
            summary = self.analyze_experiment(df)
            n_per_var, total_n = self.calculate_sample_size(self.baseline_ctr, max(0.005, lift_pp))
            est_days = math.ceil(total_n / self.modeled_daily_eligible) if total_n > 0 else 0
            rows.append({
                "scenario": name,
                "assumed_lift_pp": round(lift_pp * 100.0, 2),
                "assumed_treatment_ctr": round((self.baseline_ctr + lift_pp) * 100.0, 2),
                "control_ctr": round(summary.control_ctr * 100.0, 2),
                "observed_sim_treatment_ctr": round(summary.treatment_ctr * 100.0, 2),
                "simulated_abs_lift_pp": round(summary.absolute_lift_pp, 2),
                "simulated_rel_lift_pct": round(summary.relative_lift_pct, 1),
                "p_value": round(summary.p_value, 4),
                "stat_sig": "YES" if summary.statistically_significant else "NO",
                "pract_sig": "YES" if summary.practically_significant else "NO",
                "decision": summary.decision,
                "required_n_total": total_n,
                "modeled_duration_days": est_days,
                "incremental_orders_modeled": summary.incremental_orders,
                "annualized_gmv_modeled": summary.annualized_gmv,
            })
        return pd.DataFrame(rows)

    def run_sequential_simulation(self, days: int = 60, treatment_lift_pp: float = 0.035) -> pd.DataFrame:
        df = self.generate_experiment_dataset(treatment_lift_pp=treatment_lift_pp)
        df = df.sort_values("search_timestamp").reset_index(drop=True)
        chunk_size = len(df) / days
        daily_rows = []
        for d in range(1, days + 1):
            subset = df.iloc[: int(round(d * chunk_size))]
            ctrl = subset[subset["variant"] == "Control"]
            trt = subset[subset["variant"] == "Treatment"]
            c_n = len(ctrl)
            c_c = int(ctrl["pdp_view"].sum())
            t_n = len(trt)
            t_c = int(trt["pdp_view"].sum())
            if c_n > 0 and t_n > 0:
                stat = self.two_proportion_z_test(c_c, c_n, t_c, t_n, alpha=self.significance_level)
                daily_rows.append({
                    "day": d,
                    "control_n": c_n,
                    "treatment_n": t_n,
                    "total_n": c_n + t_n,
                    "control_ctr": round(stat["control_ctr"] * 100.0, 2),
                    "treatment_ctr": round(stat["treatment_ctr"] * 100.0, 2),
                    "absolute_lift_pp": round(stat["absolute_lift_pp"], 2),
                    "relative_lift_pct": round(stat["relative_lift_pct"], 1),
                    "p_value": round(stat["p_value"], 4),
                    "ci_lower_pp": round(stat["ci_95_lower_pp"], 2),
                    "ci_upper_pp": round(stat["ci_95_upper_pp"], 2),
                    "significant": stat["statistically_significant"],
                })
        return pd.DataFrame(daily_rows)


def print_cli_report(summary: ExperimentSummary, scenario_name: str = "Default (+3.5 pp)") -> None:
    print("=" * 65)
    print("       QUERY RELAXATION A/B EXPERIMENT SIMULATOR (STAGE 6)")
    print("=" * 65)
    print(f"Experiment ID         : {summary.experiment_id}")
    print(f"Scenario              : {scenario_name}")
    print(f"Randomization Unit    : User-level deterministic MD5 hash (50/50)")
    print(f"Total Eligible Events : {summary.total_eligible} [OBSERVED]")
    print("-" * 65)
    print("VARIANT METRICS:")
    print("  Control (Strict Search):")
    print(f"    Sample Size (N)     : {summary.control_n}")
    print(f"    PDP Views (Clicks)  : {summary.control_conversions}")
    print(f"    Search -> PDP CTR   : {summary.control_ctr * 100.0:.2f}% [OBSERVED]")
    print("  Treatment (Strict + Relaxation):")
    print(f"    Sample Size (N)     : {summary.treatment_n}")
    print(f"    PDP Views (Clicks)  : {summary.treatment_conversions}")
    print(f"    Search -> PDP CTR   : {summary.treatment_ctr * 100.0:.2f}% [SIMULATED]")
    print("-" * 65)
    print("STATISTICAL INFERENCE (Two-Proportion Z-Test, alpha=0.05, power=0.80):")
    sign = "+" if summary.absolute_lift_pp >= 0 else ""
    print(f"  Absolute Lift         : {sign}{summary.absolute_lift_pp:.2f} percentage points")
    print(f"  Relative Lift         : {sign}{summary.relative_lift_pct:.1f}%")
    print(f"  95% Confidence Interval: [{summary.ci_95_lower_pp:.2f} pp, {summary.ci_95_upper_pp:.2f} pp]")
    print(f"  Z-Score               : {summary.z_score:.3f}")
    print(f"  P-Value               : {summary.p_value:.4f}")
    sig_str = "YES (p < 0.05)" if summary.statistically_significant else "NO (p >= 0.05)"
    print(f"  Statistically Sig     : {sig_str}")
    prac_str = "YES" if summary.practically_significant else "NO"
    print(f"  Practically Sig (>=1.5pp): {prac_str}")
    print("-" * 65)
    print("PRODUCT DECISION FRAMEWORK:")
    print(f"  DECISION              : >>> {summary.decision} <<< [PRODUCT ASSUMPTION]")
    print(f"  Rationale             : {summary.decision_rationale}")
    print("-" * 65)
    print("MODELED DOWNSTREAM BUSINESS IMPACT (60-Day Experiment Window):")
    print(f"  Incremental Clicks    : +{summary.incremental_clicks} [MODELED]")
    print(f"  Incremental Orders    : +{summary.incremental_orders} [MODELED]")
    print(f"  Incremental GMV       : +${summary.incremental_gmv:,.2f} [MODELED]")
    print(f"  Annualized GMV Run-Rate: +${summary.annualized_gmv:,.2f} [MODELED]")
    print("=" * 65)
    print("DATA HONESTY DISCLAIMER:")
    print("Control outcomes reflect historical observed events. Treatment outcomes")
    print("are counterfactual simulated projections under the specified MDE.")
    print("=" * 65)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="A/B Experiment Simulator & Design for Query Relaxation (Stage 6)"
    )
    parser.add_argument(
        "--mde",
        type=float,
        default=0.035,
        help="Treatment lift in proportion (default: 0.035 for +3.5 pp)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        choices=["all", "null", "low", "target", "high"],
        help="Run predefined scenario(s)",
    )
    parser.add_argument(
        "--power-analysis",
        action="store_true",
        help="Run sample size and experiment duration power analysis",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as raw JSON",
    )
    args = parser.parse_args()

    simulator = ABExperimentSimulator()

    if args.power_analysis:
        df_power = simulator.run_power_analysis()
        if args.json:
            print(df_power.to_json(orient="records", indent=2))
        else:
            print("\n" + "=" * 65)
            print("EXPERIMENT POWER & DURATION ANALYSIS (Baseline CTR = 3.08%)")
            print("=" * 65)
            print(
                df_power.to_string(
                    index=False,
                    columns=[
                        "mde_pp",
                        "target_ctr",
                        "required_n_per_variant",
                        "total_required_n",
                        "modeled_duration_days",
                        "modeled_duration_months",
                    ],
                )
            )
            print("=" * 65)
            print(f"Assumed Daily Traffic: {simulator.modeled_daily_eligible:.1f} eligible opportunities/day [MODELED]")
            print("Notice: Lower MDEs require prohibitive durations on current traffic volume.")
        return

    if args.scenario == "all":
        df_scenarios = simulator.run_scenario_analysis()
        if args.json:
            print(df_scenarios.to_json(orient="records", indent=2))
        else:
            print("\n" + "=" * 80)
            print("A/B EXPERIMENT SCENARIO & SENSITIVITY ANALYSIS (STAGE 6)")
            print("=" * 80)
            print(
                df_scenarios.to_string(
                    index=False,
                    columns=[
                        "scenario",
                        "assumed_lift_pp",
                        "control_ctr",
                        "observed_sim_treatment_ctr",
                        "simulated_abs_lift_pp",
                        "p_value",
                        "stat_sig",
                        "decision",
                        "required_n_total",
                        "modeled_duration_days",
                    ],
                )
            )
            print("=" * 80)
        return

    lift = args.mde
    if args.scenario == "null":
        lift = 0.000
    elif args.scenario == "low":
        lift = 0.015
    elif args.scenario == "target":
        lift = 0.035
    elif args.scenario == "high":
        lift = 0.050

    df_exp = simulator.generate_experiment_dataset(treatment_lift_pp=lift)
    summary = simulator.analyze_experiment(df_exp)

    if args.json:
        print(json.dumps(asdict(summary), indent=2))
    else:
        print_cli_report(summary, scenario_name=f"+{lift * 100.0:.1f} pp Lift")


if __name__ == "__main__":
    main()
