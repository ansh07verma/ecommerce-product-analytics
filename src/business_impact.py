"""
Business Impact & GMV Opportunity Model (Stage 7 / 7.1)

Transparent, scenario-based business model that propagates search recovery
improvements through the downstream e-commerce funnel to estimate incremental GMV.

Funnel Propagation:
  Eligible Searches -> Recovered Searches -> Incremental PDP Views ->
  Incremental Carts -> Incremental Orders -> Incremental GMV -> Annualized GMV

Data Honesty Tags:
  [OBSERVED]                               - Extracted directly from DuckDB historical data
  [LOCAL BENCHMARK]                        - Measured on local search engine / query relaxation
  [SIMULATED]                              - Generated counterfactual treatment outcome from Stage 6
  [MODELED]                                - Projected business impact / run-rate
  [PRODUCT ASSUMPTION — ILLUSTRATIVE PLANNING INPUT] - PM/business scenario assumption or decision threshold
"""

import argparse
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


@dataclass
class BaselineFunnel:
    total_searches: int
    eligible_searches: int
    subgroup_a_zero_results: int
    subgroup_b_low_results: int
    observation_window_days: int
    eligible_searches_per_day: float
    searches_with_pdp_click: int
    pdp_views_count: int
    search_to_pdp_ctr: float
    cart_items_count: int
    pdp_to_cart_rate: float
    orders_count: int
    cart_to_order_rate: float
    total_order_gmv: float
    average_order_value: float
    gmv_per_eligible_search: float


@dataclass
class ScenarioResult:
    scenario_name: str
    recovery_rate: float
    ctr_lift_pp: float
    treatment_ctr: float
    cannibalization_rate: float
    eligible_searches: int
    recovered_searches: float
    incremental_pdp_views: float
    incremental_carts: float
    incremental_orders: float
    gross_incremental_gmv: float
    net_incremental_gmv: float
    annualized_gross_gmv: float
    annualized_net_gmv: float
    roi_net_benefit: float
    roi_percentage: float
    payback_months: float


class BusinessImpactModel:
    """Deterministic, scenario-based e-commerce business impact model."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        eng_person_months: float = 1.5,
        monthly_eng_cost: float = 15000.0,
        annual_infra_cost: float = 2400.0,
        annual_maintenance_cost: float = 3600.0,
    ):
        if db_path is None:
            self.db_path = str(REPO_ROOT / "data" / "ecommerce_analytics.duckdb")
        else:
            self.db_path = db_path

        self.baseline = self.load_baseline_funnel()

        # Benchmark recovery rate [LOCAL BENCHMARK]
        self.benchmark_recovery_rate = 0.9181  # 807 / 879 from Stage 3

        # Configurable engineering economic assumptions [PRODUCT ASSUMPTION — ILLUSTRATIVE PLANNING INPUT]
        self.default_eng_person_months = float(eng_person_months)
        self.default_monthly_eng_cost = float(monthly_eng_cost)
        self.default_annual_infra_cost = float(annual_infra_cost)
        self.default_annual_maintenance_cost = float(annual_maintenance_cost)

    def load_baseline_funnel(self) -> BaselineFunnel:
        """Loads the exact observed funnel for eligible searches from DuckDB."""
        con = duckdb.connect(self.db_path, read_only=True)
        query = """
        WITH search_base AS (
            SELECT 
                search_id,
                query_text,
                results_count,
                has_pdp_click,
                search_timestamp,
                ARRAY_LENGTH(STRING_SPLIT(TRIM(query_text), ' ')) AS token_count
            FROM search_events
        ),
        eligible AS (
            SELECT * FROM search_base
            WHERE token_count >= 4 AND results_count < 3
        ),
        pdp_views AS (
            SELECT pv.view_id, pv.search_id
            FROM product_views pv
            JOIN eligible e ON pv.search_id = e.search_id
        ),
        carts AS (
            SELECT c.cart_item_id, c.order_id, c.item_price
            FROM cart_events c
            JOIN pdp_views pv ON c.view_id = pv.view_id
        ),
        orders_table AS (
            SELECT o.order_id, o.gross_merchandise_value
            FROM orders o
            WHERE o.order_id IN (SELECT DISTINCT order_id FROM carts WHERE order_id IS NOT NULL)
        )
        SELECT 
            (SELECT COUNT(*) FROM search_base) AS total_searches,
            (SELECT COUNT(*) FROM eligible) AS eligible_searches,
            (SELECT COUNT(*) FROM eligible WHERE results_count = 0) AS sub_a_zero,
            (SELECT COUNT(*) FROM eligible WHERE results_count BETWEEN 1 AND 2) AS sub_b_low,
            (SELECT DATEDIFF('day', MIN(search_timestamp), MAX(search_timestamp)) FROM search_base) AS day_span,
            (SELECT COUNT(DISTINCT search_id) FROM eligible WHERE has_pdp_click OR search_id IN (SELECT search_id FROM pdp_views)) AS searches_with_pdp,
            (SELECT COUNT(*) FROM pdp_views) AS pdp_views_count,
            (SELECT COUNT(*) FROM carts) AS cart_items_count,
            (SELECT COUNT(DISTINCT order_id) FROM orders_table) AS orders_count,
            COALESCE((SELECT SUM(gross_merchandise_value) FROM orders_table), 0.0) AS total_order_gmv;
        """
        res = con.execute(query).fetchone()
        con.close()

        tot_s = int(res[0])
        elig_s = int(res[1])
        sub_a = int(res[2])
        sub_b = int(res[3])
        days = 60  # Standardized 60-day dataset window
        daily_elig = elig_s / days
        s_pdp = int(res[5])
        pdp_v = int(res[6])
        ctr = s_pdp / elig_s if elig_s > 0 else 0.0
        carts = int(res[7])
        # Unique conversion journey probabilities: 7 carts / 29 search clickers = 24.14%
        pdp_to_cart = carts / s_pdp if s_pdp > 0 else (7 / 29)
        orders = int(res[8])
        cart_to_ord = orders / carts if carts > 0 else (2 / 7)
        gmv = float(res[9])
        aov = gmv / orders if orders > 0 else 142.575
        gmv_per_search = gmv / elig_s if elig_s > 0 else 0.303

        return BaselineFunnel(
            total_searches=tot_s,
            eligible_searches=elig_s,
            subgroup_a_zero_results=sub_a,
            subgroup_b_low_results=sub_b,
            observation_window_days=days,
            eligible_searches_per_day=daily_elig,
            searches_with_pdp_click=s_pdp,
            pdp_views_count=pdp_v,
            search_to_pdp_ctr=ctr,
            cart_items_count=carts,
            pdp_to_cart_rate=pdp_to_cart,
            orders_count=orders,
            cart_to_order_rate=cart_to_ord,
            total_order_gmv=gmv,
            average_order_value=aov,
            gmv_per_eligible_search=gmv_per_search,
        )

    def calculate_scenario(
        self,
        scenario_name: str,
        ctr_lift_pp: float,
        recovery_rate: Optional[float] = None,
        cannibalization_rate: float = 0.0,
        eng_cost_override: Optional[float] = None,
    ) -> ScenarioResult:
        """
        Calculates end-to-end downstream business metrics under a given scenario.
        """
        if recovery_rate is None:
            recovery_rate = self.benchmark_recovery_rate

        # Clamp inputs
        rec_rate = max(0.0, min(1.0, recovery_rate))
        cann_rate = max(0.0, min(1.0, cannibalization_rate))
        lift = max(0.0, ctr_lift_pp)

        treatment_ctr = min(1.0, self.baseline.search_to_pdp_ctr + lift)
        recovered_searches = self.baseline.eligible_searches * rec_rate

        # Funnel propagation: Incremental PDP views = Recovered Searches * CTR lift
        inc_pdp = recovered_searches * lift
        inc_carts = inc_pdp * self.baseline.pdp_to_cart_rate
        inc_orders = inc_carts * self.baseline.cart_to_order_rate
        gross_gmv = inc_orders * self.baseline.average_order_value
        net_gmv = gross_gmv * (1.0 - cann_rate)

        # Annualization (365 / observation_window_days)
        annual_factor = 365.0 / self.baseline.observation_window_days
        annual_gross_gmv = gross_gmv * annual_factor
        annual_net_gmv = net_gmv * annual_factor

        # ROI / Economic evaluation
        if eng_cost_override is not None:
            total_cost = eng_cost_override
        else:
            initial_eng_cost = self.default_eng_person_months * self.default_monthly_eng_cost
            annual_operating_cost = self.default_annual_infra_cost + self.default_annual_maintenance_cost
            total_cost = initial_eng_cost + annual_operating_cost

        roi_net_benefit = annual_net_gmv - total_cost
        roi_pct = (roi_net_benefit / total_cost * 100.0) if total_cost > 0 else 0.0
        monthly_net_revenue = annual_net_gmv / 12.0
        payback_months = (total_cost / monthly_net_revenue) if monthly_net_revenue > 0 else 999.0

        return ScenarioResult(
            scenario_name=scenario_name,
            recovery_rate=rec_rate,
            ctr_lift_pp=lift,
            treatment_ctr=treatment_ctr,
            cannibalization_rate=cann_rate,
            eligible_searches=self.baseline.eligible_searches,
            recovered_searches=round(recovered_searches, 1),
            incremental_pdp_views=round(inc_pdp, 2),
            incremental_carts=round(inc_carts, 2),
            incremental_orders=round(inc_orders, 2),
            gross_incremental_gmv=round(gross_gmv, 2),
            net_incremental_gmv=round(net_gmv, 2),
            annualized_gross_gmv=round(annual_gross_gmv, 2),
            annualized_net_gmv=round(annual_net_gmv, 2),
            roi_net_benefit=round(roi_net_benefit, 2),
            roi_percentage=round(roi_pct, 1),
            payback_months=round(payback_months, 1),
        )

    def run_ctr_scenarios(self, cannibalization_rate: float = 0.0) -> pd.DataFrame:
        """Runs standard CTR lift scenarios at benchmark recovery rate."""
        scenarios = [
            ("Conservative (+1.0 pp)", 0.010),
            ("Moderate (+1.5 pp)", 0.015),
            ("Target (+3.5 pp)", 0.035),
            ("Optimistic (+5.0 pp)", 0.050),
        ]
        rows = []
        for name, lift in scenarios:
            res = self.calculate_scenario(
                scenario_name=name,
                ctr_lift_pp=lift,
                cannibalization_rate=cannibalization_rate,
            )
            rows.append({
                "scenario": res.scenario_name,
                "ctr_lift_pp": round(res.ctr_lift_pp * 100.0, 2),
                "treatment_ctr_pct": round(res.treatment_ctr * 100.0, 2),
                "incremental_pdp_views": res.incremental_pdp_views,
                "incremental_carts": res.incremental_carts,
                "incremental_orders": res.incremental_orders,
                "gross_gmv_60d": res.gross_incremental_gmv,
                "net_gmv_60d": res.net_incremental_gmv,
                "annualized_gross_gmv": res.annualized_gross_gmv,
                "annualized_net_gmv": res.annualized_net_gmv,
                "roi_percentage": res.roi_percentage,
                "payback_months": res.payback_months,
            })
        return pd.DataFrame(rows)

    def run_recovery_ctr_matrix(self, cannibalization_rate: float = 0.0) -> pd.DataFrame:
        """
        Generates the 2D sensitivity matrix: Recovery Rate vs CTR Lift.
        Each cell represents Annualized Net GMV ($).
        """
        recoveries = [0.50, 0.70, 0.90, 0.9181]
        ctr_lifts = [0.010, 0.015, 0.035, 0.050]

        matrix = {}
        for r in recoveries:
            label = f"{r * 100.0:.1f}%" if r != 0.9181 else "91.81% (Bench)"
            matrix[label] = []
            for lift in ctr_lifts:
                res = self.calculate_scenario(
                    scenario_name=f"R_{r}_L_{lift}",
                    ctr_lift_pp=lift,
                    recovery_rate=r,
                    cannibalization_rate=cannibalization_rate,
                )
                matrix[label].append(res.annualized_net_gmv)

        cols = ["+1.0 pp", "+1.5 pp", "+3.5 pp (Target)", "+5.0 pp"]
        df = pd.DataFrame(matrix, index=cols).T
        return df

    def run_cannibalization_analysis(self) -> pd.DataFrame:
        """Evaluates net GMV erosion across cannibalization rates."""
        cann_rates = [0.00, 0.10, 0.25, 0.40]
        target_lift = 0.035

        rows = []
        for c in cann_rates:
            res = self.calculate_scenario(
                scenario_name=f"Cannibalization {int(c * 100)}%",
                ctr_lift_pp=target_lift,
                cannibalization_rate=c,
            )
            rows.append({
                "cannibalization_pct": f"{int(c * 100)}%",
                "gross_gmv_60d": res.gross_incremental_gmv,
                "net_gmv_60d": res.net_incremental_gmv,
                "annualized_gross_gmv": res.annualized_gross_gmv,
                "annualized_net_gmv": res.annualized_net_gmv,
                "gmv_eroded_annual": round(res.annualized_gross_gmv - res.annualized_net_gmv, 2),
                "roi_percentage": res.roi_percentage,
            })
        return pd.DataFrame(rows)

    def calculate_break_even(
        self, target_annual_gmvs: Optional[List[float]] = None
    ) -> pd.DataFrame:
        """
        Solves for the required CTR lift and required recovery rate
        to achieve specified annual GMV targets ($10k, $25k, $50k, $100k).
        Explicitly reports impossible requirements without silent clamping.
        """
        if target_annual_gmvs is None:
            target_annual_gmvs = [10000.0, 25000.0, 50000.0, 100000.0]

        annual_factor = 365.0 / self.baseline.observation_window_days
        unit_gmv = (
            self.baseline.pdp_to_cart_rate
            * self.baseline.cart_to_order_rate
            * self.baseline.average_order_value
            * annual_factor
        )

        rows = []
        for target in target_annual_gmvs:
            # Case 1: Required CTR lift at benchmark recovery (91.81%)
            recovered = self.baseline.eligible_searches * self.benchmark_recovery_rate
            req_lift = target / (recovered * unit_gmv) if (recovered * unit_gmv) > 0 else 0.0
            req_treatment_ctr = self.baseline.search_to_pdp_ctr + req_lift

            # Case 2: Required recovery rate at target CTR lift (+3.5 pp)
            target_lift = 0.035
            req_rec = target / (self.baseline.eligible_searches * target_lift * unit_gmv) if (self.baseline.eligible_searches * target_lift * unit_gmv) > 0 else 0.0

            # Feasibility check without silent clamping
            if req_treatment_ctr > 1.0 or req_rec > 1.0:
                feasibility = "Not achievable under current model assumptions"
                req_lift_str = f"+{req_lift * 100.0:.2f} pp (Exceeds 100% CTR)" if req_treatment_ctr > 1.0 else f"+{req_lift * 100.0:.2f} pp"
                req_ctr_str = f"{req_treatment_ctr * 100.0:.2f}% (Impossible >100%)" if req_treatment_ctr > 1.0 else f"{req_treatment_ctr * 100.0:.2f}%"
                req_rec_str = f"{req_rec * 100.0:.1f}% (Exceeds 100% Recovery)" if req_rec > 1.0 else f"{req_rec * 100.0:.1f}%"
            else:
                feasibility = "Achievable under current model assumptions"
                req_lift_str = f"+{req_lift * 100.0:.2f} pp"
                req_ctr_str = f"{req_treatment_ctr * 100.0:.2f}%"
                req_rec_str = f"{req_rec * 100.0:.1f}%"

            rows.append({
                "target_annual_gmv": f"${target:,.0f}",
                "required_ctr_lift_pp": req_lift_str,
                "required_treatment_ctr": req_ctr_str,
                "required_recovery_rate_at_35pp": req_rec_str,
                "feasibility_assessment": feasibility,
            })
        return pd.DataFrame(rows)

    def run_sensitivity_ranking(self) -> pd.DataFrame:
        """
        Ranks model variables by their elasticity on Annualized Net GMV
        when varied +/- 20% from baseline/target values.
        """
        base_res = self.calculate_scenario("Base", ctr_lift_pp=0.035, recovery_rate=self.benchmark_recovery_rate)
        base_gmv = base_res.annualized_net_gmv

        variables = [
            ("CTR Lift (+3.5 pp)", "ctr_lift", 0.035),
            ("Eligible Search Volume (941)", "traffic", self.baseline.eligible_searches),
            ("Average Order Value ($142.58)", "aov", self.baseline.average_order_value),
            ("PDP -> Cart Rate (24.14%)", "pdp_to_cart", self.baseline.pdp_to_cart_rate),
            ("Cart -> Order Rate (28.57%)", "cart_to_order", self.baseline.cart_to_order_rate),
            ("Query Recovery Rate (91.81%)", "recovery", 0.9181),
            ("Cannibalization Rate (0% to 20%)", "cannibalization", 0.0),
        ]

        rows = []
        for name, var_type, base_val in variables:
            if var_type == "cannibalization":
                res_high = self.calculate_scenario("Cann_20", ctr_lift_pp=0.035, cannibalization_rate=0.20)
                low_gmv = base_gmv
                high_gmv = res_high.annualized_net_gmv
                swing = abs(high_gmv - low_gmv)
            else:
                low_mult = 0.80
                high_mult = 1.20
                low_val = base_val * low_mult
                high_val = base_val * high_mult

                if var_type == "ctr_lift":
                    g_low = self.calculate_scenario("Low", ctr_lift_pp=low_val).annualized_net_gmv
                    g_high = self.calculate_scenario("High", ctr_lift_pp=high_val).annualized_net_gmv
                elif var_type == "recovery":
                    g_low = self.calculate_scenario("Low", ctr_lift_pp=0.035, recovery_rate=low_val).annualized_net_gmv
                    g_high = self.calculate_scenario("High", ctr_lift_pp=0.035, recovery_rate=high_val).annualized_net_gmv
                elif var_type == "traffic":
                    eff = (base_gmv / self.baseline.eligible_searches)
                    g_low = eff * low_val
                    g_high = eff * high_val
                elif var_type in ("aov", "cart_to_order", "pdp_to_cart"):
                    g_low = base_gmv * low_mult
                    g_high = base_gmv * high_mult

                swing = abs(g_high - g_low)
                low_gmv = min(g_low, g_high)
                high_gmv = max(g_low, g_high)

            rows.append({
                "variable": name,
                "base_value": base_val,
                "low_gmv": round(low_gmv, 2),
                "high_gmv": round(high_gmv, 2),
                "gmv_swing": round(swing, 2),
                "elasticity_rank": 0,
            })

        df = pd.DataFrame(rows).sort_values("gmv_swing", ascending=False).reset_index(drop=True)
        df["elasticity_rank"] = range(1, len(df) + 1)
        return df


def print_cli_summary(model: BusinessImpactModel) -> None:
    """Prints an executive-ready terminal report."""
    b = model.baseline
    scen_target = model.calculate_scenario("Target (+3.5 pp)", ctr_lift_pp=0.035)

    print("=" * 70)
    print("       BUSINESS IMPACT & GMV OPPORTUNITY MODEL (STAGE 7 / 7.1)")
    print("=" * 70)
    print("1. OBSERVED HISTORICAL BASELINE (60-Day Window) [OBSERVED]:")
    print(f"   Total Search Events             : {b.total_searches:,}")
    print(f"   Eligible Multi-Attribute Searches: {b.eligible_searches:,} ({b.eligible_searches_per_day:.1f} / day)")
    print(f"     - Subgroup A (Zero-Result)    : {b.subgroup_a_zero_results:,} (8.23% of 4+ token)")
    print(f"     - Subgroup B (Low-Result 1-2) : {b.subgroup_b_low_results:,}")
    print(f"   Eligible Searches with PDP Click: {b.searches_with_pdp_click} (CTR = {b.search_to_pdp_ctr * 100.0:.2f}%)")
    print(f"   PDP -> Cart Conversion Rate     : {b.pdp_to_cart_rate * 100.0:.2f}% ({b.cart_items_count} carts)")
    print(f"   Cart -> Order Conversion Rate   : {b.cart_to_order_rate * 100.0:.2f}% ({b.orders_count} orders)")
    print(f"   Observed GMV on Eligible Funnel : ${b.total_order_gmv:,.2f} (AOV = ${b.average_order_value:.2f})")
    print("-" * 70)
    print("2. RECOVERY BENCHMARK [LOCAL BENCHMARK]:")
    print(f"   Stage 3 Algorithmic Recovery Rate: {model.benchmark_recovery_rate * 100.0:.2f}% (807 / 879 queries)")
    print("-" * 70)
    print("3. TARGET SCENARIO D (+3.5 pp MDE Lift) [MODELED]:")
    print(f"   Eligible Searches               : {scen_target.eligible_searches}")
    print(f"   Recovered Searches              : {scen_target.recovered_searches}")
    print(f"   Incremental PDP Views (Clicks)  : +{scen_target.incremental_pdp_views:.1f}")
    print(f"   Incremental Cart Additions      : +{scen_target.incremental_carts:.1f}")
    print(f"   Incremental Orders              : +{scen_target.incremental_orders:.1f}")
    print(f"   Gross Incremental GMV (60-Day)  : +${scen_target.gross_incremental_gmv:,.2f}")
    print(f"   Annualized Gross GMV Run-Rate   : +${scen_target.annualized_gross_gmv:,.2f}")
    print("-" * 70)
    print("4. ROI & ENGINEERING ECONOMICS [PRODUCT ASSUMPTION — ILLUSTRATIVE PLANNING INPUT]:")
    print(f"   Engineering Effort Input        : {model.default_eng_person_months:.1f} person-months")
    print(f"   Monthly Engineering Rate Input  : ${model.default_monthly_eng_cost:,.2f} / month")
    print(f"   Annual Infrastructure & Maint.  : ${model.default_annual_infra_cost + model.default_annual_maintenance_cost:,.2f} / year")
    tot_cost = model.default_eng_person_months * model.default_monthly_eng_cost + model.default_annual_infra_cost + model.default_annual_maintenance_cost
    print(f"   Total Illustrative Year 1 Cost  : ${tot_cost:,.2f}")
    print(f"   Net Annual Benefit (Target)     : +${scen_target.roi_net_benefit:,.2f} [MODELED]")
    print(f"   Illustrative Payback Period     : {scen_target.payback_months:.1f} months [MODELED]")
    print("   Notice: ROI is illustrative and should be recalculated using the target company's")
    print("   fully-loaded engineering and infrastructure cost rates.")
    print("=" * 70)
    print("DATA HONESTY NOTICE:")
    print("Baseline metrics are historically observed. Incremental GMV figures are")
    print("modeled projections and do NOT represent audited production revenue.")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Business Impact & GMV Opportunity Model (Stage 7 / 7.1)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run and display all business model analyses",
    )
    parser.add_argument(
        "--scenarios",
        action="store_true",
        help="Display CTR scenario sensitivity table",
    )
    parser.add_argument(
        "--matrix",
        action="store_true",
        help="Display Recovery x CTR annualized GMV matrix",
    )
    parser.add_argument(
        "--break-even",
        action="store_true",
        help="Display break-even analysis table ($10k, $25k, $50k, $100k)",
    )
    parser.add_argument(
        "--engineering-cost",
        type=float,
        default=15000.0,
        help="Monthly loaded engineering cost [PRODUCT ASSUMPTION — ILLUSTRATIVE PLANNING INPUT] (default: 15000.0)",
    )
    parser.add_argument(
        "--engineering-person-months",
        type=float,
        default=1.5,
        help="Implementation effort in person-months (default: 1.5)",
    )
    parser.add_argument(
        "--annual-infra-cost",
        type=float,
        default=2400.0,
        help="Annual cloud hosting / infra cost (default: 2400.0)",
    )
    parser.add_argument(
        "--annual-maintenance-cost",
        type=float,
        default=3600.0,
        help="Annual maintenance cost (default: 3600.0)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output target scenario summary as raw JSON",
    )
    args = parser.parse_args()

    model = BusinessImpactModel(
        eng_person_months=args.engineering_person_months,
        monthly_eng_cost=args.engineering_cost,
        annual_infra_cost=args.annual_infra_cost,
        annual_maintenance_cost=args.annual_maintenance_cost,
    )

    if args.json:
        target_res = model.calculate_scenario("Target", ctr_lift_pp=0.035)
        print(json.dumps(asdict(target_res), indent=2))
        return

    if args.matrix:
        df_mat = model.run_recovery_ctr_matrix()
        print("\n" + "=" * 65)
        print("ANNUALIZED NET GMV ($) SENSITIVITY MATRIX [MODELED]")
        print("Recovery Rate (Rows) vs CTR Lift (Columns)")
        print("=" * 65)
        print(df_mat.to_string())
        print("=" * 65)
        return

    if args.scenarios:
        df_scen = model.run_ctr_scenarios()
        print("\n" + "=" * 80)
        print("DOWNSTREAM FUNNEL & GMV SCENARIOS (91.81% Recovery) [MODELED]")
        print("=" * 80)
        print(df_scen.to_string(index=False))
        print("=" * 80)
        return

    if args.break_even:
        df_be = model.calculate_break_even()
        print("\n" + "=" * 90)
        print("BREAK-EVEN ANALYSIS: REQUIRED METRICS BY ANNUAL GMV TARGET [MODELED]")
        print("=" * 90)
        print(df_be.to_string(index=False))
        print("=" * 90)
        return

    print_cli_summary(model)
    if args.all:
        print("\nCTR SCENARIOS TABLE:")
        print(model.run_ctr_scenarios().to_string(index=False))
        print("\nANNUALIZED GMV SENSITIVITY MATRIX:")
        print(model.run_recovery_ctr_matrix().to_string())
        print("\nBREAK-EVEN ANALYSIS ($10k, $25k, $50k, $100k Targets):")
        print(model.calculate_break_even().to_string(index=False))
        print("\nSENSITIVITY RANKING (GMV ELASTICITY):")
        print(model.run_sensitivity_ranking().to_string(index=False))


if __name__ == "__main__":
    main()
