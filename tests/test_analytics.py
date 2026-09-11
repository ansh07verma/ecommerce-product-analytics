"""
test_analytics.py - Tests for SQL Funnel Data & Business Calculations
"""

import os
import duckdb
import pytest
from src.business_impact import get_baseline_metrics, estimate_scenario


@pytest.fixture(scope="module")
def db_connection():
    db_path = "data/ecommerce_analytics.duckdb"
    if not os.path.exists(db_path):
        pytest.skip(f"Database not found at {db_path}")
    con = duckdb.connect(db_path, read_only=True)
    yield con
    con.close()


def test_database_tables_exist(db_connection):
    """Verifies that all 7 core e-commerce tables exist in DuckDB."""
    tables = [t[0] for t in db_connection.execute("SHOW TABLES").fetchall()]
    expected = ["users", "sessions", "products", "search_events", "product_views", "cart_events", "orders"]
    for exp in expected:
        assert exp in tables, f"Expected table {exp} not found in database."


def test_total_searches_count(db_connection):
    """Verifies the canonical project metric of 32,245 search events."""
    count = db_connection.execute("SELECT COUNT(*) FROM search_events").fetchone()[0]
    assert count == 32245


def test_total_orders_count(db_connection):
    """Verifies the canonical project metric of 2,880 completed orders."""
    count = db_connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    assert count == 2880


def test_specific_query_volume_and_zrr(db_connection):
    """Verifies 4+ token query count (10,914) and 8.23% Zero-Result Rate."""
    query = """
    SELECT
        COUNT(*) AS total_4plus,
        SUM(is_zero_result) AS zrr_count,
        ROUND(100.0 * SUM(is_zero_result) / COUNT(*), 2) AS zrr_pct
    FROM search_events
    WHERE (LENGTH(TRIM(query_text)) - LENGTH(REPLACE(TRIM(query_text), ' ', '')) + 1) >= 4;
    """
    total, zrr_count, zrr_pct = db_connection.execute(query).fetchone()
    assert total == 10914
    assert zrr_count == 898
    assert zrr_pct == 8.23


def test_eligible_cohort_size_and_ctr(db_connection):
    """Verifies the eligible low-result cohort (941 searches, 29 clicks, 3.08% CTR)."""
    query = """
    SELECT
        COUNT(*) AS eligible_count,
        SUM(has_pdp_click) AS clicks,
        ROUND(100.0 * SUM(has_pdp_click) / COUNT(*), 2) AS ctr_pct
    FROM search_events
    WHERE (LENGTH(TRIM(query_text)) - LENGTH(REPLACE(TRIM(query_text), ' ', '')) + 1) >= 4
      AND results_count < 3;
    """
    eligible, clicks, ctr = db_connection.execute(query).fetchone()
    assert eligible == 941
    assert clicks == 29
    assert ctr == 3.08


def test_business_impact_scenario_calculations():
    """Verifies the business impact scenario calculation formulas."""
    mock_baseline = {
        "eligible_searches_60d": 941,
        "baseline_ctr": 0.0308,
        "pdp_to_cart_rate": 0.2414,
        "cart_to_order_rate": 0.2857,
        "aov": 142.58,
    }
    # Test Scenario A: +1.0 pp CTR lift
    res_a = estimate_scenario(mock_baseline, ctr_lift=0.010, recovery_rate=0.9181)
    assert res_a["recovered_searches"] == 863.9
    assert res_a["gross_gmv_60d"] == pytest.approx(84.95, abs=0.5)
    assert res_a["annualized_gross_gmv"] == pytest.approx(516.77, abs=0.5)

    # Test Scenario B: +3.5 pp CTR lift
    res_b = estimate_scenario(mock_baseline, ctr_lift=0.035, recovery_rate=0.9181)
    assert res_b["gross_gmv_60d"] == pytest.approx(297.32, abs=0.5)
    assert res_b["annualized_gross_gmv"] == pytest.approx(1808.69, abs=0.5)
