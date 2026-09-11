"""
Unit & Integration Tests for Stage 8 Search Health & Product Analytics Dashboard
"""

import json
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.search_dashboard import get_dashboard_payload, generate_static_html


@pytest.fixture
def payload():
    return get_dashboard_payload()


def test_dashboard_payload_structure(payload):
    """Test that dashboard payload contains all required sections."""
    required_sections = [
        "metadata", "kpis", "pm_takeaway", "funnel", "discovery_failure",
        "query_relaxation_recovery", "experiment", "business_impact",
        "capital_discipline", "roadmap", "dataset_provenance"
    ]
    for sec in required_sections:
        assert sec in payload, f"Missing section: {sec}"


def test_kpi_card_values_and_tags(payload):
    """Verify KPI card values match observed and benchmark project ground truth."""
    kpis = {k["id"]: k for k in payload["kpis"]}
    assert len(kpis) == 6
    assert kpis["total_searches"]["value"] == "32,245"
    assert kpis["total_searches"]["tag"] == "[OBSERVED]"
    assert kpis["eligible_searches"]["value"] == "941"
    assert kpis["eligible_searches"]["tag"] == "[OBSERVED]"
    assert kpis["historical_zrr"]["value"] == "8.23%"
    assert kpis["historical_zrr"]["tag"] == "[OBSERVED]"
    assert kpis["relaxation_recovery"]["value"] == "91.81%"
    assert kpis["relaxation_recovery"]["tag"] == "[LOCAL BENCHMARK]"
    assert kpis["baseline_ctr"]["value"] == "3.08%"
    assert kpis["baseline_ctr"]["tag"] == "[OBSERVED]"
    assert "$1,808.69" in kpis["annualized_gmv"]["value"]
    assert kpis["annualized_gmv"]["tag"] == "[MODELED]"


def test_funnel_consistency(payload):
    """Verify funnel numbers match DuckDB."""
    f = payload["funnel"]
    assert f["total_searches"] == 32245
    assert f["eligible_searches"] == 941
    assert f["pdp_clicks"] == 29
    assert f["cart_items"] == 7
    assert f["orders"] == 2
    assert f["gmv"] == 285.15
    assert f["search_to_pdp_ctr"] == 3.08
    assert f["pdp_to_cart_rate"] == 24.14
    assert f["cart_to_order_rate"] == 28.57


def test_discovery_failure_metrics(payload):
    """Verify discovery failure comparison."""
    df = payload["discovery_failure"]
    assert df["share_4plus_tokens"] == "33.85%"
    assert df["zrr_4plus_tokens"] == "8.23%"
    assert df["zrr_1to3_tokens"] == "1.78%"
    assert df["ctr_4plus_tokens"] == "62.95%"
    assert df["retype_rate"] == "44.39%"


def test_relaxation_benchmark_metrics(payload):
    """Verify Stage 3 relaxation benchmark values."""
    rel = payload["query_relaxation_recovery"]
    assert rel["eligible_queries"] == 879
    assert rel["recovered_queries"] == 807
    assert rel["recovery_rate"] == "91.81%"
    assert rel["strict_zrr"] == "98.21%"
    assert rel["relaxed_zrr"] == "8.40%"
    assert rel["net_zrr_reduction"] == "80.70 pp"
    assert rel["p95_strict_latency"] == "2.08 ms"
    assert rel["p95_relaxed_latency"] == "38.53 ms"


def test_experiment_spec_and_simulation(payload):
    """Verify Stage 6 A/B experiment spec and simulation output."""
    exp = payload["experiment"]
    assert exp["primary_metric"] == "Search -> PDP CTR"
    assert "50/50" in exp["randomization"]
    sim = exp["simulated_scenario"]
    assert sim["control_ctr"] == "2.60%"
    assert sim["treatment_ctr"] == "5.83%"
    assert sim["absolute_lift"] == "+3.23 pp"
    assert sim["p_value"] == "0.0141"
    assert "NOT A LIVE A/B TEST" in sim["label"]


def test_business_impact_and_break_even(payload):
    """Verify Stage 7 business impact and 4 break-even milestones."""
    bi = payload["business_impact"]
    assert "$1,808.69" in bi["annualized_gross_gmv"]
    assert "$1,356.52" in bi["annualized_net_gmv_25cann"]
    assert "$180,869.00" in bi["illustrative_100x_gmv"]
    be = bi["break_even"]
    assert len(be) == 4
    targets = [b["target_annual_gmv"] for b in be]
    assert targets == ["$10,000", "$25,000", "$50,000", "$100,000"]
    for b in be:
        assert b["feasibility_assessment"] == "Not achievable under current model assumptions"


def test_capital_discipline_recommendation(payload):
    """Verify capital discipline framing and canary recommendation."""
    cd = payload["capital_discipline"]
    assert "LIGHTWEIGHT CANARY" in cd["recommendation"]
    assert len(cd["ship_criteria"]) >= 3
    assert len(cd["deprioritize_criteria"]) >= 3


def test_roadmap_completeness(payload):
    """Verify 6-stage product roadmap."""
    rm = payload["roadmap"]
    assert len(rm) == 6
    stages = [r["stage"] for r in rm]
    assert stages == ["V1", "V1.1", "V1.2", "V1.3", "V2.0", "V3.0"]


def test_static_html_generation(tmp_path):
    """Verify static HTML generation writes a valid, non-empty file."""
    out_file = tmp_path / "test_dashboard.html"
    res_path = generate_static_html(out_file)
    assert res_path.exists()
    content = res_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "E-Commerce Search Health &amp; Discovery Recovery" in content or "E-Commerce Search Health & Discovery Recovery" in content
    assert "32,245" in content
    assert "91.81%" in content
    assert "$1,808.69" in content
