"""
Unit & Integration Tests for Stage 6 A/B Experiment Simulator & Design Engine
"""

import math
import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ab_experiment import ABExperimentSimulator, ExperimentSummary


@pytest.fixture
def simulator():
    return ABExperimentSimulator(seed=42)


def test_deterministic_assignment(simulator):
    """Test that the same user always gets assigned to the same variant."""
    user_ids = ["USR_0001", "USR_0042", "USR_0999", "USR_5432", "USR_8888"]
    for uid in user_ids:
        v1 = simulator.assign_variant("exp_v1", uid)
        v2 = simulator.assign_variant("exp_v1", uid)
        assert v1 == v2, f"User {uid} received inconsistent assignment"
        assert v1 in ("Control", "Treatment")


def test_allocation_balance(simulator):
    """Test that assignment across large user population is approximately 50/50."""
    users = [f"USER_{i:05d}" for i in range(2000)]
    assignments = [simulator.assign_variant("exp_v1", u) for u in users]
    ctrl_count = assignments.count("Control")
    trt_count = assignments.count("Treatment")
    ctrl_pct = ctrl_count / len(users)
    trt_pct = trt_count / len(users)
    assert 0.47 <= ctrl_pct <= 0.53, f"Control allocation skewed: {ctrl_pct:.3f}"
    assert 0.47 <= trt_pct <= 0.53, f"Treatment allocation skewed: {trt_pct:.3f}"


def test_experiment_isolation(simulator):
    """Test that changing experiment_id re-randomizes user assignment."""
    users = [f"USER_{i:04d}" for i in range(200)]
    v1_list = [simulator.assign_variant("exp_query_relaxation_v1", u) for u in users]
    v2_list = [simulator.assign_variant("exp_query_relaxation_v2", u) for u in users]
    differences = sum(1 for a, b in zip(v1_list, v2_list) if a != b)
    diff_pct = differences / len(users)
    assert 0.35 <= diff_pct <= 0.65, f"Hash orthogonality failed: {diff_pct:.2f}"


def test_eligibility_rules(simulator):
    """Test exact eligibility rules: >=4 tokens AND strict results < 3."""
    # Eligible
    assert simulator.is_eligible("red silk evening dress", 0) is True
    assert simulator.is_eligible("blue oversized winter hoodie jacket", 1) is True
    assert simulator.is_eligible("floral print summer dress", 2) is True

    # Ineligible due to short query (<4 tokens)
    assert simulator.is_eligible("blue dress", 0) is False
    assert simulator.is_eligible("black leather shoes", 1) is False
    assert simulator.is_eligible("", 0) is False

    # Ineligible due to sufficient strict results (>=3)
    assert simulator.is_eligible("red silk evening dress", 3) is False
    assert simulator.is_eligible("blue oversized winter hoodie jacket", 15) is False


def test_dataset_generation_structure(simulator):
    """Test generated experiment dataset columns, rows, and provenance flags."""
    df = simulator.generate_experiment_dataset(treatment_lift_pp=0.035)
    assert len(df) == 941, f"Expected 941 eligible rows, got {len(df)}"
    required_cols = [
        "experiment_id", "user_id", "session_id", "query_text", "variant",
        "eligible", "strict_result_count", "final_result_count",
        "relaxation_triggered", "relaxation_status", "pdp_view", "cart",
        "order", "gmv", "outcome_source"
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column: {col}"

    ctrl_rows = df[df["variant"] == "Control"]
    assert (ctrl_rows["outcome_source"] == "observed").all()
    trt_rows = df[df["variant"] == "Treatment"]
    assert (trt_rows["outcome_source"] == "simulated").all()


def test_probability_clamping(simulator):
    """Test that extreme lift values do not break probability bounds [0, 1]."""
    df_neg = simulator.generate_experiment_dataset(treatment_lift_pp=-0.50)
    trt_neg = df_neg[df_neg["variant"] == "Treatment"]
    assert trt_neg["pdp_view"].sum() == 0

    df_pos = simulator.generate_experiment_dataset(treatment_lift_pp=1.50)
    trt_pos = df_pos[df_pos["variant"] == "Treatment"]
    assert trt_pos["pdp_view"].sum() == len(trt_pos)


def test_two_proportion_z_test_math():
    """Verify two-proportion z-test calculations against known values."""
    res = ABExperimentSimulator.two_proportion_z_test(
        control_conversions=30,
        control_n=1000,
        treatment_conversions=60,
        treatment_n=1000,
        alpha=0.05
    )
    assert res["control_ctr"] == 0.03
    assert res["treatment_ctr"] == 0.06
    assert round(res["absolute_lift_pp"], 2) == 3.00
    assert round(res["relative_lift_pct"], 1) == 100.0
    assert res["statistically_significant"] is True
    assert res["p_value"] < 0.01
    assert res["ci_95_lower_pp"] > 0


def test_confidence_interval_bounds():
    """Test CI bounds consistency."""
    res = ABExperimentSimulator.two_proportion_z_test(
        control_conversions=15,
        control_n=500,
        treatment_conversions=35,
        treatment_n=500,
        alpha=0.05
    )
    assert res["ci_95_lower_pp"] < res["absolute_lift_pp"] < res["ci_95_upper_pp"]


def test_power_analysis_positive_sample_sizes(simulator):
    """Test that sample size estimation produces strictly positive, monotone sizes."""
    df_power = simulator.run_power_analysis()
    assert len(df_power) >= 4
    n_vals = df_power["total_required_n"].tolist()
    assert all(n > 0 for n in n_vals)
    for i in range(len(n_vals) - 1):
        assert n_vals[i] > n_vals[i + 1], "Sample size not monotonically decreasing with MDE"


def test_scenarios_and_decision_framework(simulator):
    """Test five scenario outcomes and decision framework."""
    df_scen = simulator.run_scenario_analysis()
    assert len(df_scen) == 5
    decisions = df_scen["decision"].tolist()
    assert "DO NOT SHIP" in decisions
    assert "ITERATE" in decisions
    assert "SHIP" in decisions


def test_business_impact_sanity(simulator):
    """Test that modeled business impact is non-negative and finite."""
    df = simulator.generate_experiment_dataset(treatment_lift_pp=0.035)
    summary = simulator.analyze_experiment(df)
    assert summary.incremental_clicks >= 0
    assert summary.incremental_orders >= 0
    assert summary.incremental_gmv >= 0.0
    assert summary.annualized_gmv >= 0.0
    assert not math.isnan(summary.annualized_gmv)


def test_invalid_sample_size_error():
    """Test that invalid sample sizes raise ValueError."""
    with pytest.raises(ValueError):
        ABExperimentSimulator.two_proportion_z_test(0, 0, 10, 100)
