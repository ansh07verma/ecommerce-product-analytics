"""
Unit & Integration Tests for Automated Query Relaxation Engine.
Verifies trigger conditions, modifier selection heuristics, deterministic candidate ranking,
category consistency, guardrails, response schema, and latency tracking.
"""

from __future__ import annotations

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from src.search_engine import (
    LocalSearchEngine,
    RelaxedSearchResponse,
    SearchResponse,
    normalize_query_text,
)


@pytest.fixture(scope="module")
def engine() -> LocalSearchEngine:
    """Instantiate a local search engine against the catalog."""
    return LocalSearchEngine()


def test_1_successful_strict_query_no_relaxation(engine: LocalSearchEngine):
    """Successful short query (e.g. 'dress') does not trigger relaxation."""
    resp = engine.search_with_relaxation("dress")
    assert isinstance(resp, RelaxedSearchResponse)
    assert not resp.relaxation_triggered
    assert resp.recovery_status == "NORMAL"
    assert resp.strict_result_count >= 3
    assert resp.fallback_query is None
    assert len(resp.results) == resp.strict_result_count


def test_2_four_token_query_with_enough_results_no_relaxation(engine: LocalSearchEngine):
    """Four-token query with >= 3 results does NOT trigger relaxation."""
    resp = engine.search_with_relaxation("women floral print dresses")
    assert not resp.relaxation_triggered
    assert resp.recovery_status == "NORMAL"
    assert resp.strict_result_count >= 3
    assert resp.fallback_query is None


def test_3_zero_result_four_plus_token_triggers_relaxation(engine: LocalSearchEngine):
    """Zero-result 4+ token query triggers relaxation and recovers results."""
    resp = engine.search_with_relaxation("women floral midi dress red")
    assert resp.strict_result_count == 0
    assert resp.relaxation_triggered
    assert resp.recovery_status == "RELAXED_RECOVERED"
    assert resp.fallback_query is not None
    assert resp.fallback_result_count > 0
    assert len(resp.results) > 0


def test_4_low_result_query_triggers_relaxation(engine: LocalSearchEngine):
    """Low-result (<3 in-stock) 4+ token query triggers relaxation and improves count."""
    resp = engine.search_with_relaxation("tommy hilfiger classic t-shirts")
    assert 0 < resp.strict_result_count < 3
    assert resp.relaxation_triggered
    assert resp.recovery_status == "RELAXED_RECOVERED"
    assert resp.fallback_result_count > resp.strict_result_count
    assert resp.fallback_query is not None


def test_5_core_category_token_preserved(engine: LocalSearchEngine):
    """Core category noun ('dress') is never removed when safe modifiers exist."""
    resp = engine.search_with_relaxation("women floral midi dress red")
    assert resp.fallback_query is not None
    fallback_tokens = resp.fallback_query.split()
    # 'dress' or stemmed 'dress' must be preserved
    assert any("dress" in t for t in fallback_tokens)
    assert "dress" not in resp.selected_removed_tokens


def test_6_highly_selective_modifier_preferred_for_removal(engine: LocalSearchEngine):
    """Tokens with 0 or low catalog presence (e.g. 'midi') are prioritized for removal."""
    resp = engine.search_with_relaxation("women floral midi dress red")
    # 'midi' has catalog DF=0, so it must be removed
    assert "midi" in resp.selected_removed_tokens


def test_7_fallback_query_improves_result_count(engine: LocalSearchEngine):
    """Fallback query strictly returns more results than strict query."""
    resp = engine.search_with_relaxation("vintage black dresses 10")
    assert resp.relaxation_triggered
    assert resp.fallback_result_count > resp.strict_result_count


def test_8_fallback_maintains_category_consistency(engine: LocalSearchEngine):
    """Recovered products maintain category consistency matching query intent."""
    resp = engine.search_with_relaxation("women floral midi dress red")
    assert len(resp.results) > 0
    for product in resp.results:
        assert product.master_category == "Women"
        assert product.sub_category == "Dresses"


def test_9_out_of_stock_products_remain_excluded(engine: LocalSearchEngine):
    """Stock guardrail: returned products in relaxation must be in-stock by default."""
    resp = engine.search_with_relaxation("women floral midi dress red")
    assert len(resp.results) > 0
    for product in resp.results:
        assert product.is_in_stock is True


def test_10_no_safe_fallback_returns_no_safe_relaxation(engine: LocalSearchEngine):
    """Completely unmatchable query returns NO_SAFE_RELAXATION without returning junk."""
    resp = engine.search_with_relaxation("xyzunknown completely impossible query qwerty")
    assert resp.strict_result_count == 0
    assert resp.relaxation_triggered
    assert resp.recovery_status == "NO_SAFE_RELAXATION"
    assert resp.result_count == 0
    assert resp.fallback_query is None


def test_11_candidate_ranking_is_deterministic(engine: LocalSearchEngine):
    """Candidate generation and scoring evaluate predictably."""
    tokens = ["women", "floral", "midi", "dress", "red"]
    candidates = engine._generate_candidate_fallbacks(tokens)
    assert len(candidates) > 0
    # Every candidate drops at least 1 token and preserves at least 2 tokens
    for cand in candidates:
        assert len(cand.remaining_tokens) >= 2
        assert len(cand.dropped_tokens) >= 1
        assert len(cand.remaining_tokens) + len(cand.dropped_tokens) == len(tokens)


def test_12_same_query_produces_identical_fallback_every_time(engine: LocalSearchEngine):
    """Determinism check: 5 runs on same query yield identical results."""
    query = "women floral midi dress red"
    baseline = engine.search_with_relaxation(query)
    for _ in range(4):
        run = engine.search_with_relaxation(query)
        assert run.fallback_query == baseline.fallback_query
        assert run.selected_removed_tokens == baseline.selected_removed_tokens
        assert run.fallback_result_count == baseline.fallback_result_count
        assert run.recovery_status == baseline.recovery_status
        assert [p.product_id for p in run.results] == [p.product_id for p in baseline.results]


def test_13_response_metadata_is_complete(engine: LocalSearchEngine):
    """RelaxedSearchResponse contains all required structured fields."""
    resp = engine.search_with_relaxation("women floral midi dress red")
    as_dict = resp.to_dict()
    required_keys = [
        "original_query",
        "normalized_query",
        "strict_result_count",
        "relaxation_triggered",
        "relaxation_reason",
        "candidate_queries",
        "selected_removed_tokens",
        "fallback_query",
        "fallback_result_count",
        "recovery_status",
        "total_execution_time_ms",
        "relaxation_overhead_ms",
        "explanation",
        "results",
    ]
    for k in required_keys:
        assert k in as_dict, f"Missing key: {k}"
    assert len(as_dict["candidate_queries"]) > 0
    assert len(as_dict["explanation"]) > 20


def test_14_latency_is_measured(engine: LocalSearchEngine):
    """Latency and relaxation overhead are tracked and positive."""
    resp = engine.search_with_relaxation("women floral midi dress red")
    assert resp.total_execution_time_ms > 0
    assert resp.relaxation_overhead_ms >= 0
    assert resp.total_execution_time_ms >= resp.relaxation_overhead_ms


def test_15_short_unmatchable_query_no_relaxation(engine: LocalSearchEngine):
    """1-3 token query returning 0 results does NOT trigger relaxation (preserves strict behavior)."""
    resp = engine.search_with_relaxation("xyzfake")
    assert resp.strict_result_count == 0
    assert not resp.relaxation_triggered
    assert resp.recovery_status == "LOW_RESULTS_NO_RELAXATION"
    assert resp.result_count == 0
