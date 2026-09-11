"""
Unit & Integration Tests for Stage 7 Business Impact Model & GMV Opportunity Analysis
"""

import math
import sys
from pathlib import Path
import pytest
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.business_impact import BusinessImpactModel, BaselineFunnel, ScenarioResult


@pytest.fixture
def model():
    return BusinessImpactModel()


def test_baseline_funnel_extraction(model):
    """Verify baseline funnel metrics match DuckDB ground truth."""
    b = model.baseline
    assert b.total_searches == 32245
    assert b.eligible_searches == 941
    assert b.subgroup_a_zero_results == 898
    assert b.subgroup_b_low_results == 43
    assert b.searches_with_pdp_click == 29
    assert round(b.search_to_pdp_ctr, 4) == round(29 / 941, 4)
    assert b.cart_items_count == 7
    assert round(b.pdp_to_cart_rate, 4) == round(7 / 29, 4)
    assert b.orders_count == 2
    assert round(b.cart_to_order_rate, 4) == round(2 / 7, 4)
    assert round(b.total_order_gmv, 2) == 285.15
    assert round(b.average_order_value, 2) == round(285.15 / 2, 2)
    assert b.observation_window_days == 60


def test_scenario_calculation_propagation(model):
    """Verify that funnel math propagates deterministically."""
    res = model.calculate_scenario("Target", ctr_lift_pp=0.035, recovery_rate=0.9181)
    expected_recovered = 941 * 0.9181
    assert round(res.recovered_searches, 1) == round(expected_recovered, 1)
    expected_inc_pdp = expected_recovered * 0.035
    assert round(res.incremental_pdp_views, 2) == round(expected_inc_pdp, 2)
    expected_inc_carts = expected_inc_pdp * (7 / 29)
    assert round(res.incremental_carts, 2) == round(expected_inc_carts, 2)
    expected_inc_orders = expected_inc_carts * (2 / 7)
    assert round(res.incremental_orders, 2) == round(expected_inc_orders, 2)
    expected_gross_gmv = expected_inc_orders * (285.15 / 2)
    assert round(res.gross_incremental_gmv, 2) == round(expected_gross_gmv, 2)
    expected_annual = expected_gross_gmv * (365.0 / 60.0)
    assert round(res.annualized_gross_gmv, 2) == round(expected_annual, 2)


def test_cannibalization_erosion(model):
    """Test that cannibalization discounts GMV linearly."""
    res_0 = model.calculate_scenario("Cann_0", ctr_lift_pp=0.035, cannibalization_rate=0.0)
    res_25 = model.calculate_scenario("Cann_25", ctr_lift_pp=0.035, cannibalization_rate=0.25)
    res_50 = model.calculate_scenario("Cann_50", ctr_lift_pp=0.035, cannibalization_rate=0.50)
    res_100 = model.calculate_scenario("Cann_100", ctr_lift_pp=0.035, cannibalization_rate=1.00)

    assert res_0.net_incremental_gmv == res_0.gross_incremental_gmv
    assert round(res_25.net_incremental_gmv, 2) == round(res_0.gross_incremental_gmv * 0.75, 2)
    assert round(res_50.net_incremental_gmv, 2) == round(res_0.gross_incremental_gmv * 0.50, 2)
    assert res_100.net_incremental_gmv == 0.0


def test_ctr_scenarios_monotonicity(model):
    """Test that higher CTR lift produces strictly higher incremental GMV."""
    df_scen = model.run_ctr_scenarios()
    assert len(df_scen) == 4
    gmvs = df_scen["annualized_gross_gmv"].tolist()
    for i in range(len(gmvs) - 1):
        assert gmvs[i] < gmvs[i + 1], "Annualized GMV not strictly increasing with CTR lift"


def test_recovery_matrix_dimensions(model):
    """Test recovery x CTR sensitivity matrix structure."""
    df_mat = model.run_recovery_ctr_matrix()
    assert df_mat.shape == (4, 4)
    for _, row in df_mat.iterrows():
        vals = row.tolist()
        for j in range(len(vals) - 1):
            assert vals[j] < vals[j + 1]
    for col in df_mat.columns:
        vals = df_mat[col].tolist()
        for k in range(len(vals) - 1):
            assert vals[k] < vals[k + 1]


def test_break_even_solver(model):
    """Test break-even solver across four requested targets ($10k, $25k, $50k, $100k)."""
    df_be = model.calculate_break_even()
    assert len(df_be) == 4
    targets = df_be["target_annual_gmv"].tolist()
    assert targets == ["$10,000", "$25,000", "$50,000", "$100,000"]
    for _, row in df_be.iterrows():
        assert row["feasibility_assessment"] == "Not achievable under current model assumptions"


def test_sensitivity_ranking_completeness(model):
    """Test sensitivity ranking contains all expected variables and positive swings."""
    df_sens = model.run_sensitivity_ranking()
    assert len(df_sens) == 7
    swings = df_sens["gmv_swing"].tolist()
    assert all(s >= 0 for s in swings)
    assert df_sens["elasticity_rank"].tolist() == list(range(1, 8))


def test_probability_bounds_and_clamping(model):
    """Test that extreme or negative parameters are safely clamped."""
    r_over = model.calculate_scenario("Over", ctr_lift_pp=0.035, recovery_rate=1.5)
    r_100 = model.calculate_scenario("Max", ctr_lift_pp=0.035, recovery_rate=1.0)
    assert r_over.annualized_gross_gmv == r_100.annualized_gross_gmv

    r_neg = model.calculate_scenario("Neg", ctr_lift_pp=-0.05)
    assert r_neg.incremental_pdp_views == 0.0
    assert r_neg.annualized_gross_gmv == 0.0


def test_roi_and_payback_logic(model):
    """Test economic calculation logic."""
    res = model.calculate_scenario("Target", ctr_lift_pp=0.035, eng_cost_override=1000.0)
    assert round(res.roi_net_benefit, 2) == 808.69
    assert round(res.roi_percentage, 1) == 80.9
    assert round(res.payback_months, 1) == 6.6


def test_monotonic_relationships(model):
    """Test mathematical monotonicity across all dimensions."""
    # 1. Higher recovery -> Higher GMV
    g_rec1 = model.calculate_scenario("R1", ctr_lift_pp=0.035, recovery_rate=0.50).annualized_gross_gmv
    g_rec2 = model.calculate_scenario("R2", ctr_lift_pp=0.035, recovery_rate=0.90).annualized_gross_gmv
    assert g_rec1 < g_rec2

    # 2. Higher CTR lift -> Higher GMV
    g_ctr1 = model.calculate_scenario("C1", ctr_lift_pp=0.010).annualized_gross_gmv
    g_ctr2 = model.calculate_scenario("C2", ctr_lift_pp=0.035).annualized_gross_gmv
    assert g_ctr1 < g_ctr2

    # 3. Higher cannibalization -> Lower Net GMV
    g_cann1 = model.calculate_scenario("K1", ctr_lift_pp=0.035, cannibalization_rate=0.10).annualized_net_gmv
    g_cann2 = model.calculate_scenario("K2", ctr_lift_pp=0.035, cannibalization_rate=0.30).annualized_net_gmv
    assert g_cann1 > g_cann2

    # 4. Higher cost -> Lower ROI
    roi1 = model.calculate_scenario("Cost1", ctr_lift_pp=0.035, eng_cost_override=5000.0).roi_percentage
    roi2 = model.calculate_scenario("Cost2", ctr_lift_pp=0.035, eng_cost_override=20000.0).roi_percentage
    assert roi1 > roi2
