"""
Deterministic Local E-Commerce Search Engine MVP.
Provides strict keyword-based product retrieval, ranking, and stock filtering
against the catalog stored in DuckDB / raw CSV.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import duckdb
import pandas as pd


# Minimal functional stopwords in English fashion queries (preserving content terms like 'men', 'women')
DEFAULT_STOPWORDS: Set[str] = {
    "a", "an", "the", "in", "on", "at", "for", "with", "by", "of", "and", "or", "to"
}


def simple_stem(token: str) -> str:
    """
    Deterministic rule-based suffix normalization for English fashion catalog terms.
    Normalizes common plurals while preserving stem identities.
    """
    t = token.lower()
    if t.endswith("ies") and len(t) > 4:
        return t[:-3] + "y"
    elif t.endswith("sses") or t.endswith("shes") or t.endswith("ches") or t.endswith("xes"):
        return t[:-2]
    elif t.endswith("es") and len(t) > 4 and not t.endswith("tees"):
        return t[:-1]
    elif t.endswith("s") and not t.endswith("ss") and len(t) > 2 and t != "men":
        return t[:-1]
    return t


def normalize_query_text(query: str, remove_stopwords: bool = True) -> Tuple[str, List[str]]:
    """
    Normalizes query string:
    - Lowercase
    - Punctuation removal (preserving alphanumeric and whitespace)
    - Whitespace normalization
    - Stopword filtering (optional)
    - Deterministic token stemming
    """
    if not query or not isinstance(query, str):
        return "", []

    cleaned = query.lower()
    # Replace non-alphanumeric characters with spaces, except hyphens inside terms
    cleaned = re.sub(r"[^\w\s-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    raw_tokens = cleaned.split()
    processed_tokens: List[str] = []

    for t in raw_tokens:
        clean_t = t.strip("-")
        if not clean_t:
            continue
        if remove_stopwords and clean_t in DEFAULT_STOPWORDS:
            continue
        stemmed = simple_stem(clean_t)
        if stemmed and stemmed not in processed_tokens:
            processed_tokens.append(stemmed)

    normalized_query = " ".join(processed_tokens)
    return normalized_query, processed_tokens


@dataclass
class SearchResultItem:
    product_id: str
    title: str
    brand: str
    master_category: str
    sub_category: str
    retail_price: float
    effective_price: float
    discount_pct: float
    inventory_units: int
    available_sizes: str
    stockout_sizes: str
    is_in_stock: bool
    relevance_score: float
    matched_terms: List[str]


@dataclass
class SearchResponse:
    original_query: str
    normalized_query: str
    query_tokens: List[str]
    result_count: int
    total_matches: int
    execution_time_ms: float
    in_stock_only: bool
    results: List[SearchResultItem]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "normalized_query": self.normalized_query,
            "query_tokens": self.query_tokens,
            "result_count": self.result_count,
            "total_matches": self.total_matches,
            "execution_time_ms": self.execution_time_ms,
            "in_stock_only": self.in_stock_only,
            "results": [asdict(r) for r in self.results],
        }


class LocalSearchEngine:
    """
    In-Memory Keyword Search Engine for E-Commerce Product Catalog.
    Indexes the 1,600 product catalog and executes deterministic strict keyword matching.
    """

    def __init__(
        self,
        db_path: str = "data/ecommerce_analytics.duckdb",
        csv_path: str = "data/raw/products.csv",
    ) -> None:
        self.db_path = db_path
        self.csv_path = csv_path
        self.products_df: pd.DataFrame = self._load_catalog()
        self._build_index()

    def _load_catalog(self) -> pd.DataFrame:
        """Load product catalog from DuckDB with fallback to CSV."""
        if os.path.exists(self.db_path):
            try:
                con = duckdb.connect(self.db_path, read_only=True)
                df = con.execute("SELECT * FROM products").df()
                con.close()
                return df
            except Exception as e:
                print(f"Warning: DuckDB connection failed ({e}). Falling back to CSV.")

        if os.path.exists(self.csv_path):
            return pd.read_csv(self.csv_path)

        raise FileNotFoundError(
            f"Could not load product catalog from {self.db_path} or {self.csv_path}."
        )

    def _build_index(self) -> None:
        """
        Precomputes tokenized representation and field lookup structures
        for fast, deterministic in-memory matching.
        """
        self.indexed_products: List[Dict[str, Any]] = []

        for _, row in self.products_df.iterrows():
            title_str = str(row.get("title", ""))
            brand_str = str(row.get("brand", ""))
            sub_str = str(row.get("sub_category", ""))
            master_str = str(row.get("master_category", ""))
            sizes_str = str(row.get("available_sizes", ""))
            stockout_str = str(row.get("stockout_sizes", ""))
            inv_units = int(row.get("inventory_units", 0))

            # Parse size tokens
            size_tokens = [s.strip().lower() for s in sizes_str.split(",") if s.strip()]
            stockout_tokens = [s.strip().lower() for s in stockout_str.split(",") if s.strip()]

            # Build token sets per field
            _, title_tokens = normalize_query_text(title_str, remove_stopwords=False)
            _, brand_tokens = normalize_query_text(brand_str, remove_stopwords=False)
            _, sub_tokens = normalize_query_text(sub_str, remove_stopwords=False)
            _, master_tokens = normalize_query_text(master_str, remove_stopwords=False)

            # Combined document tokens for boolean verification
            doc_tokens = set(title_tokens + brand_tokens + sub_tokens + master_tokens + size_tokens)

            item = {
                "product_id": str(row["product_id"]),
                "title": title_str,
                "brand": brand_str,
                "master_category": master_str,
                "sub_category": sub_str,
                "retail_price": round(float(row.get("retail_price", 0.0)), 2),
                "effective_price": round(float(row.get("effective_price", 0.0)), 2),
                "discount_pct": round(float(row.get("discount_pct", 0.0)), 2),
                "inventory_units": inv_units,
                "available_sizes": sizes_str,
                "stockout_sizes": stockout_str,
                "is_in_stock": inv_units > 0,
                "avg_rating": round(float(row.get("avg_rating", 0.0)), 2),
                "review_count": int(row.get("review_count", 0)),
                # Internal matching fields
                "title_tokens": set(title_tokens),
                "brand_tokens": set(brand_tokens),
                "sub_tokens": set(sub_tokens),
                "master_tokens": set(master_tokens),
                "size_tokens": set(size_tokens),
                "stockout_tokens": set(stockout_tokens),
                "doc_tokens": doc_tokens,
                "clean_title_lower": title_str.lower(),
            }
            self.indexed_products.append(item)

    def search(
        self,
        query: str,
        limit: int = 20,
        in_stock_only: bool = True,
    ) -> SearchResponse:
        """
        Executes deterministic strict keyword search against the catalog.

        Parameters:
        - query: Raw search query string.
        - limit: Maximum number of ranked results to return (default 20).
        - in_stock_only: If True, filters out products with 0 units or out-of-stock sizes.
        """
        start_time = time.perf_counter()

        normalized_query, query_tokens = normalize_query_text(query)

        # Empty query handling
        if not query_tokens:
            execution_time_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
            return SearchResponse(
                original_query=query,
                normalized_query=normalized_query,
                query_tokens=[],
                result_count=0,
                total_matches=0,
                execution_time_ms=execution_time_ms,
                in_stock_only=in_stock_only,
                results=[],
            )

        candidate_results: List[Tuple[float, Dict[str, Any], List[str]]] = []

        # Strict Matching: ALL query tokens must be present in the product's document tokens
        for prod in self.indexed_products:
            # 1. In-stock check
            if in_stock_only:
                if not prod["is_in_stock"]:
                    continue
                # If query specifically mentions a size that is in stockout_tokens, filter out
                size_conflict = False
                for qt in query_tokens:
                    if qt in prod["stockout_tokens"]:
                        size_conflict = True
                        break
                if size_conflict:
                    continue

            # 2. Strict boolean token presence check (AND condition)
            if not all(qt in prod["doc_tokens"] for qt in query_tokens):
                continue

            # 3. Calculate deterministic relevance score
            score, matched_terms = self._calculate_relevance(prod, normalized_query, query_tokens)
            candidate_results.append((score, prod, matched_terms))

        # Sort candidates deterministically:
        # 1. Relevance score DESC
        # 2. Product ID ASC (tie-breaker ensuring 100% deterministic ordering)
        candidate_results.sort(key=lambda x: (-x[0], x[1]["product_id"]))

        total_matches = len(candidate_results)
        ranked_items = candidate_results[:limit]

        result_objects: List[SearchResultItem] = []
        for score, prod, matched_terms in ranked_items:
            result_objects.append(
                SearchResultItem(
                    product_id=prod["product_id"],
                    title=prod["title"],
                    brand=prod["brand"],
                    master_category=prod["master_category"],
                    sub_category=prod["sub_category"],
                    retail_price=prod["retail_price"],
                    effective_price=prod["effective_price"],
                    discount_pct=prod["discount_pct"],
                    inventory_units=prod["inventory_units"],
                    available_sizes=prod["available_sizes"],
                    stockout_sizes=prod["stockout_sizes"],
                    is_in_stock=prod["is_in_stock"],
                    relevance_score=score,
                    matched_terms=matched_terms,
                )
            )

        execution_time_ms = round((time.perf_counter() - start_time) * 1000.0, 3)

        return SearchResponse(
            original_query=query,
            normalized_query=normalized_query,
            query_tokens=query_tokens,
            result_count=len(result_objects),
            total_matches=total_matches,
            execution_time_ms=execution_time_ms,
            in_stock_only=in_stock_only,
            results=result_objects,
        )

    def _calculate_relevance(
        self, prod: Dict[str, Any], normalized_query: str, query_tokens: List[str]
    ) -> Tuple[float, List[str]]:
        """
        Computes deterministic relevance score:
        - Exact phrase match in title: +50.0
        - Title token match: +10.0 per token
        - Brand token match: +8.0 per token
        - Sub-category token match: +6.0 per token
        - Master category token match: +4.0 per token
        - Size token match: +3.0 per token
        - Rating tie-breaker: + avg_rating * 0.1
        - Review volume tie-breaker: + min(review_count, 100) * 0.001
        """
        score = 0.0
        matched_terms: Set[str] = set()

        # Exact phrase bonus
        if normalized_query and normalized_query in prod["clean_title_lower"]:
            score += 50.0

        for qt in query_tokens:
            term_matched = False
            if qt in prod["title_tokens"]:
                score += 10.0
                term_matched = True
            if qt in prod["brand_tokens"]:
                score += 8.0
                term_matched = True
            if qt in prod["sub_tokens"]:
                score += 6.0
                term_matched = True
            if qt in prod["master_tokens"]:
                score += 4.0
                term_matched = True
            if qt in prod["size_tokens"]:
                score += 3.0
                term_matched = True

            if term_matched:
                matched_terms.add(qt)

        # Micro-commercial tie-breakers for stability
        score += round(prod["avg_rating"] * 0.1, 4)
        score += round(min(prod["review_count"], 100) * 0.001, 4)

        return round(score, 4), sorted(list(matched_terms))


def print_cli_search(response: SearchResponse) -> None:
    """Renders formatted CLI search output matching the project specification."""
    print("========================================")
    print("SEARCH")
    print("========================================")
    print(f"\nQuery:\n{response.original_query}\n")
    print(f"Normalized Query:\n{response.normalized_query}\n")

    if response.results:
        print("Results:")
        for idx, item in enumerate(response.results, 1):
            stock_str = "In Stock" if item.is_in_stock else "Out of Stock"
            print(
                f"{idx}. [{item.product_id}] {item.title} | "
                f"Brand: {item.brand} | Cat: {item.master_category} > {item.sub_category} | "
                f"${item.effective_price:.2f} ({stock_str}) | Score: {item.relevance_score:.4f}"
            )
        print()
    else:
        print("Results:\n(No matching products found)\n")

    print(f"Result Count:\n{response.result_count}")
    if response.total_matches > response.result_count:
        print(f"Total Matches in Catalog: {response.total_matches}")
    print(f"\nExecution Time:\n{response.execution_time_ms:.2f} ms")
    print("========================================\n")


if __name__ == "__main__":
    import sys

    default_query = "women floral midi dress red"
    query_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else default_query

    engine = LocalSearchEngine()
    resp = engine.search(query_input)
    print_cli_search(resp)
