"""
Unit & Integration Tests for Explainable Search Debugger.
Validates structured diagnostics, token analysis, catalog document frequency exposure,
strict search diagnostics, candidate evaluations, guardrail verification,
dual-mode explanations (PM vs Technical), and deterministic output.
"""

from __future__ import annotations

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from src.search_debugger import SearchDebugger, SearchDebugResult


@pytest.fixture(scope="module")
def debugger() -> SearchDebugger:
    """Instantiate a shared SearchDebugger instance."""
    return SearchDebugger()


def test_1_debugger_returns_correct_query(debugger: SearchDebugger):
    """Debugger preserves original and normalized query text."""
    res = debugger.debug("women floral midi dress red")
    assert isinstance(res, SearchDebugResult)
    assert res.query == "women floral midi dress red"
    assert res.normalized_query == "women floral midi dress red"


def test_2_token_analysis_is_correct(debugger: SearchDebugger):
    """Tokens are classified accurately into CORE_CATEGORY, MODIFIER, MISSING_CATALOG_TERM."""
    res = debugger.debug("women floral midi dress red")
    tokens_map = {t.token: t for t in res.token_analysis}

    assert "women" in tokens_map
    assert tokens_map["women"].token_role == "CORE_CATEGORY"
    assert tokens_map["women"].is_core_term is True
    assert tokens_map["women"].is_candidate_modifier is False

    assert "dress" in tokens_map
    assert tokens_map["dress"].token_role == "CORE_CATEGORY"
    assert tokens_map["dress"].is_core_term is True

    assert "midi" in tokens_map
    assert tokens_map["midi"].token_role == "MISSING_CATALOG_TERM"
    assert tokens_map["midi"].is_candidate_modifier is True

    assert "floral" in tokens_map
    assert tokens_map["floral"].token_role == "MODIFIER"
    assert tokens_map["floral"].is_candidate_modifier is True


def test_3_document_frequency_is_exposed_correctly(debugger: SearchDebugger):
    """Catalog document frequencies are accurately computed and exposed."""
    res = debugger.debug("women floral midi dress red")
    tokens_map = {t.token: t for t in res.token_analysis}

    assert tokens_map["midi"].document_frequency == 0
    assert tokens_map["dress"].document_frequency == 165
    assert tokens_map["women"].document_frequency > 100
    assert tokens_map["red"].document_frequency > 0


def test_4_strict_result_count_is_correct(debugger: SearchDebugger):
    """Strict search baseline diagnostics correctly report 0 hits for failing multi-term query."""
    res = debugger.debug("women floral midi dress red")
    assert res.strict_search.result_count == 0
    assert res.strict_search.status == "ZERO_RESULTS"
    assert res.strict_search.token_count == 5
    assert "Qualifies for automated query relaxation" in res.strict_search.trigger_explanation


def test_5_relaxation_trigger_is_correct(debugger: SearchDebugger):
    """Relaxation triggers for eligible queries and does not trigger for successful queries."""
    res_eligible = debugger.debug("women floral midi dress red")
    assert res_eligible.relaxation.triggered is True
    assert res_eligible.final_result.status == "RELAXED_RECOVERED"

    res_normal = debugger.debug("running shoes")
    assert res_normal.relaxation.triggered is False
    assert res_normal.final_result.status == "NORMAL"
    assert res_normal.strict_search.result_count >= 3


def test_6_candidate_list_is_exposed(debugger: SearchDebugger):
    """All evaluated candidates are exposed with dropped tokens, scores, and safety flags."""
    res = debugger.debug("women floral midi dress red")
    assert len(res.relaxation.candidates) > 0
    for cand in res.relaxation.candidates:
        assert isinstance(cand.fallback_query, str)
        assert len(cand.tokens_removed) >= 1
        assert isinstance(cand.candidate_score, float)
        assert isinstance(cand.is_safe, bool)


def test_7_selected_fallback_is_correct(debugger: SearchDebugger):
    """Selected fallback matches the best-scoring candidate preserving category intent."""
    res = debugger.debug("women floral midi dress red")
    assert res.relaxation.fallback_query == "women floral dress"
    assert res.relaxation.selected_candidate == "women floral dress"


def test_8_removed_tokens_are_correct(debugger: SearchDebugger):
    """Removed tokens identify the specific modifiers causing retrieval failure."""
    res = debugger.debug("women floral midi dress red")
    assert "midi" in res.relaxation.removed_tokens
    assert "red" in res.relaxation.removed_tokens
    assert "dress" not in res.relaxation.removed_tokens
    assert "women" not in res.relaxation.removed_tokens


def test_9_recovery_count_is_correct(debugger: SearchDebugger):
    """Fallback result count recovers in-stock products."""
    res = debugger.debug("women floral midi dress red")
    assert res.relaxation.fallback_result_count == 16
    assert res.final_result.result_count == 16
    assert len(res.final_result.products) == 16
    for p in res.final_result.products:
        assert p["is_in_stock"] is True
        assert p["master_category"] == "Women"
        assert p["sub_category"] == "Dresses"


def test_10_explanation_is_dynamically_generated(debugger: SearchDebugger):
    """Product Manager and Technical explanations are populated dynamically from computed data."""
    res = debugger.debug("women floral midi dress red")
    pm = res.product_explanation
    tech = res.technical_explanation

    assert "women floral dress" in pm["decision"]
    assert "16" in pm["outcome"]
    assert "0" in pm["problem"]
    assert len(pm["summary"]) > 20

    assert tech["strict_latency_ms"] >= 0
    assert tech["relaxation_overhead_ms"] >= 0
    assert tech["total_latency_ms"] > 0
    assert tech["guardrail_checks"]["core_category_preserved"] is True
    assert tech["guardrail_checks"]["in_stock_filtered"] is True


def test_11_no_safe_relaxation_is_correctly_exposed(debugger: SearchDebugger):
    """Unmatchable query triggers circuit breaker, returning NO_SAFE_RELAXATION with 0 results."""
    res = debugger.debug("xyzunknown impossible brand qwerty nonexist")
    assert res.strict_search.result_count == 0
    assert res.relaxation.triggered is True
    assert res.final_result.status == "NO_SAFE_RELAXATION"
    assert res.final_result.result_count == 0
    assert res.guardrails.circuit_breaker_activated is True
    assert "Circuit breaker activated" in res.product_explanation["decision"]


def test_12_debugger_is_deterministic(debugger: SearchDebugger):
    """Multiple debugger runs on identical queries produce identical results."""
    res1 = debugger.debug("women floral midi dress red")
    res2 = debugger.debug("women floral midi dress red")

    assert res1.final_result.status == res2.final_result.status
    assert res1.relaxation.fallback_query == res2.relaxation.fallback_query
    assert res1.relaxation.removed_tokens == res2.relaxation.removed_tokens
    assert res1.final_result.result_count == res2.final_result.result_count
    assert [p["product_id"] for p in res1.final_result.products] == [
        p["product_id"] for p in res2.final_result.products
    ]


def test_13_serialization_to_dict(debugger: SearchDebugger):
    """to_dict() produces valid JSON-serializable dictionary matching API schema."""
    res = debugger.debug("women floral midi dress red")
    d = res.to_dict()

    assert "query" in d
    assert "token_analysis" in d
    assert "strict_search" in d
    assert "relaxation" in d
    assert "guardrails" in d
    assert "final_result" in d
    assert "product_explanation" in d
    assert "technical_explanation" in d
    assert "total_execution_time_ms" in d
    assert isinstance(d["token_analysis"], list)
    assert len(d["token_analysis"]) == 5
