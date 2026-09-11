"""
test_search.py - Tests for Search & Query Relaxation Prototype
"""

import pytest
from src.search import normalize_query, strict_search, relaxed_search, simple_stem


@pytest.fixture(scope="module")
def sample_catalog():
    return [
        {
            "product_id": "p-1",
            "title": "Zara Slim Fit Dresses",
            "brand": "Zara",
            "master_category": "Women",
            "sub_category": "Dresses",
            "price": 45.00,
            "inventory_units": 10,
            "tokens": {"zara", "slim", "fit", "dress", "women", "m", "l", "xl"},
        },
        {
            "product_id": "p-2",
            "title": "H&M Vintage Wash Dresses",
            "brand": "H&M",
            "master_category": "Women",
            "sub_category": "Dresses",
            "price": 38.00,
            "inventory_units": 5,
            "tokens": {"h", "m", "vintage", "wash", "dress", "women", "s", "m"},
        },
        {
            "product_id": "p-3",
            "title": "Forever 21 Floral Dresses",
            "brand": "Forever 21",
            "master_category": "Women",
            "sub_category": "Dresses",
            "price": 29.00,
            "inventory_units": 8,
            "tokens": {"forever", "21", "floral", "dress", "women", "xs", "s", "m"},
        },
        {
            "product_id": "p-4",
            "title": "Roadster Slim Fit Jeans",
            "brand": "Roadster",
            "master_category": "Men",
            "sub_category": "Jeans",
            "price": 42.00,
            "inventory_units": 12,
            "tokens": {"roadster", "slim", "fit", "jean", "men", "32", "34"},
        },
        {
            "product_id": "p-5",
            "title": "Out of Stock Dress",
            "brand": "Biba",
            "master_category": "Women",
            "sub_category": "Dresses",
            "price": 50.00,
            "inventory_units": 0,  # Out of stock
            "tokens": {"biba", "dress", "women"},
        },
    ]


def test_simple_stem():
    """Verifies that plural nouns are correctly stripped to their singular stem."""
    assert simple_stem("dresses") == "dress"
    assert simple_stem("boots") == "boot"
    assert simple_stem("jeans") == "jean"
    assert simple_stem("shoes") == "shoe"
    assert simple_stem("men") == "men"  # Should not strip 's' from irregular words


def test_normalize_query():
    """Verifies that queries are lowercase, stripped of punctuation, and tokenized."""
    tokens = normalize_query("Women's RED Silk Evening Dresses!")
    assert "women" in tokens
    assert "red" in tokens
    assert "silk" in tokens
    assert "even" in tokens or "evening" in tokens
    assert "dress" in tokens


def test_strict_search_matching(sample_catalog):
    """Verifies that strict search requires all tokens to be present."""
    results = strict_search(["zara", "dress"], sample_catalog)
    assert len(results) == 1
    assert results[0]["title"] == "Zara Slim Fit Dresses"


def test_strict_search_stockout_filtering(sample_catalog):
    """Verifies that out-of-stock items (inventory_units <= 0) are excluded."""
    results = strict_search(["biba", "dress"], sample_catalog)
    assert len(results) == 0


def test_strict_search_no_match(sample_catalog):
    """Verifies that a query with non-matching words returns zero results."""
    results = strict_search(["leather", "jacket"], sample_catalog)
    assert len(results) == 0


def test_relaxed_search_short_query_no_relaxation(sample_catalog):
    """Verifies that short head queries (1-3 tokens) are never relaxed."""
    res = relaxed_search("leather jacket", sample_catalog)
    assert res["is_relaxed"] is False
    assert res["result_count"] == 0


def test_relaxed_search_adequate_results_no_relaxation(sample_catalog):
    """Verifies that queries with >= 3 results do not trigger relaxation."""
    res = relaxed_search("women dress", sample_catalog)
    assert res["is_relaxed"] is False
    assert res["result_count"] >= 3


def test_relaxed_search_triggers_and_recovers(sample_catalog):
    """Verifies that a 4+ token query returning 0 results safely relaxes non-category modifiers."""
    # Query has 5 tokens: "women", "red", "silk", "evening", "dress"
    # Products have "women" and "dress", but not "red", "silk", "evening"
    res = relaxed_search("women red silk evening dress", sample_catalog)
    assert res["is_relaxed"] is True
    assert res["result_count"] >= 3
    # Category noun 'dress' must be preserved!
    assert "dress" in res["relaxed_query"]
    assert "women" in res["relaxed_query"]


def test_relaxed_search_preserves_category_protection(sample_catalog):
    """Verifies that category nouns (like 'dress' or 'jean') are not removed."""
    res = relaxed_search("women red silk evening dress", sample_catalog)
    for product in res["results"]:
        assert product["sub_category"] == "Dresses"


def test_relaxed_search_minimum_tokens_remain(sample_catalog):
    """Verifies that relaxed query retains at least 2 tokens."""
    res = relaxed_search("vintage oversized cotton t-shirt", sample_catalog)
    tokens_remaining = res["relaxed_query"].split()
    assert len(tokens_remaining) >= 2
