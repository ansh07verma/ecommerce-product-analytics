import sys
import os

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
"""
Unit Tests for Local E-Commerce Search Engine MVP.
Verifies all 11 required core retrieval, ranking, stock filtering, and metadata behaviors.
"""

import pytest
from src.search_engine import LocalSearchEngine, SearchResponse, normalize_query_text


@pytest.fixture(scope="module")
def search_engine():
    """Initializes and caches the local search engine for testing."""
    return LocalSearchEngine(
        db_path="data/ecommerce_analytics.duckdb",
        csv_path="data/raw/products.csv",
    )


# 1. Basic query returns results
def test_basic_query_returns_results(search_engine):
    resp = search_engine.search("shoes")
    assert isinstance(resp, SearchResponse)
    assert resp.result_count > 0
    assert resp.total_matches > 0
    assert any("shoe" in item.title.lower() or "shoe" in item.sub_category.lower() for item in resp.results)


# 2. Case-insensitive search
def test_case_insensitive_search(search_engine):
    resp_lower = search_engine.search("nike running shoes")
    resp_upper = search_engine.search("NIKE RUNNING SHOES")
    resp_mixed = search_engine.search("NiKe RuNnInG ShOeS")

    assert resp_lower.result_count == resp_upper.result_count == resp_mixed.result_count
    assert resp_lower.total_matches == resp_upper.total_matches == resp_mixed.total_matches

    lower_ids = [r.product_id for r in resp_lower.results]
    upper_ids = [r.product_id for r in resp_upper.results]
    mixed_ids = [r.product_id for r in resp_mixed.results]

    assert lower_ids == upper_ids == mixed_ids


# 3. Multi-token query
def test_multi_token_query(search_engine):
    resp = search_engine.search("running shoes")
    assert resp.result_count > 0
    for r in resp.results:
        # Every product returned must match all tokens
        doc_str = f"{r.title} {r.brand} {r.master_category} {r.sub_category}".lower()
        assert "running" in doc_str
        assert "shoe" in doc_str


# 4. Exact/strong title matching ranks appropriately
def test_exact_strong_title_matching_ranks_appropriately(search_engine):
    # Search for an exact title that exists in catalog
    sample_prod = search_engine.indexed_products[0]
    target_title = sample_prod["title"]

    resp = search_engine.search(target_title)
    assert resp.result_count > 0
    # The exact title match should rank first due to phrase bonus
    top_result = resp.results[0]
    assert top_result.title == target_title
    # Verify that an exact title match ranks above a partial match
    partial_resp = search_engine.search("Dresses")
    assert top_result.relevance_score > partial_resp.results[0].relevance_score - 30.0
    assert top_result.relevance_score >= 50.0


# 5. Category matching
def test_category_matching(search_engine):
    resp = search_engine.search("women")
    assert resp.result_count > 0
    assert resp.total_matches >= 600
    for r in resp.results:
        assert r.master_category == "Women"


# 6. Out-of-stock filtering
def test_out_of_stock_filtering(search_engine):
    # Find a product with a known stockout size
    stockout_product = None
    stockout_size = None
    for p in search_engine.indexed_products:
        if p["stockout_tokens"]:
            stockout_product = p
            stockout_size = list(p["stockout_tokens"])[0]
            break

    assert stockout_product is not None
    assert stockout_size is not None

    # Query with specific stockout size and brand
    query = f"{stockout_product['brand']} {stockout_product['sub_category']} {stockout_size}"

    # With in_stock_only=True, this product must NOT be returned
    resp_in_stock = search_engine.search(query, in_stock_only=True)
    in_stock_ids = [r.product_id for r in resp_in_stock.results]
    assert stockout_product["product_id"] not in in_stock_ids

    # With in_stock_only=False, this product CAN be returned
    resp_all = search_engine.search(query, in_stock_only=False)
    all_ids = [r.product_id for r in resp_all.results]
    if stockout_product["product_id"] in all_ids:
        matched_item = next(r for r in resp_all.results if r.product_id == stockout_product["product_id"])
        assert matched_item.is_in_stock is True  # overall inventory exists but size was out of stock


# 7. Zero-result query
def test_zero_result_query(search_engine):
    resp = search_engine.search("nike diamond leather dress")
    assert resp.result_count == 0
    assert resp.total_matches == 0
    assert resp.results == []


# 8. Result limit
def test_result_limit(search_engine):
    limit_5 = search_engine.search("dress", limit=5)
    limit_10 = search_engine.search("dress", limit=10)
    limit_20 = search_engine.search("dress", limit=20)

    assert limit_5.result_count == 5
    assert limit_10.result_count == 10
    assert limit_20.result_count == 20
    assert limit_5.total_matches == limit_10.total_matches == limit_20.total_matches == 165


# 9. Deterministic ranking
def test_deterministic_ranking(search_engine):
    query = "mango casual dress"
    runs = [search_engine.search(query) for _ in range(5)]

    first_run_ids = [r.product_id for r in runs[0].results]
    first_run_scores = [r.relevance_score for r in runs[0].results]

    for run in runs[1:]:
        assert [r.product_id for r in run.results] == first_run_ids
        assert [r.relevance_score for r in run.results] == first_run_scores


# 10. Search metadata
def test_search_metadata(search_engine):
    raw_query = "   Women Floral Dresses, in Cotton!   "
    resp = search_engine.search(raw_query)

    assert resp.original_query == raw_query
    assert "women" in resp.query_tokens
    assert "floral" in resp.query_tokens
    assert "dress" in resp.query_tokens
    assert "cotton" in resp.query_tokens
    # Stopword 'in' should be filtered out
    assert "in" not in resp.query_tokens

    assert resp.execution_time_ms >= 0.0
    assert resp.result_count == len(resp.results)
    assert resp.total_matches >= resp.result_count
    assert resp.in_stock_only is True


# 11. Empty and invalid query handling
def test_empty_invalid_query_handling(search_engine):
    empty_cases = ["", "   ", None, "!!! ??? ,,,", "   in with on   "]

    for q in empty_cases:
        resp = search_engine.search(q)
        assert resp.result_count == 0
        assert resp.total_matches == 0
        assert resp.results == []
        assert resp.execution_time_ms >= 0.0


if __name__ == "__main__":
    pytest.main(["-v", __file__])
