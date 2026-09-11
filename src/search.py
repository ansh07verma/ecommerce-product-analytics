import re
import itertools
from typing import List, Dict, Any, Optional, Set
import duckdb
import pandas as pd

# Standard stopwords that do not convey fashion merchandise intent
STOPWORDS: Set[str] = {
    "a", "an", "the", "in", "on", "at", "for", "with", "by", "of", "and", "or", "to"
}

# Core merchandise category nouns that should be protected from query relaxation
CATEGORY_TERMS: Set[str] = {
    "dress", "dresses", "jacket", "jackets", "boots", "boot", "shoes", "shoe",
    "jeans", "jean", "shirt", "shirts", "t-shirt", "pants", "pant", "sweater",
    "sweaters", "hoodie", "hoodies", "skirt", "skirts", "blazer", "blazers",
    "coat", "coats", "sneakers", "sandals", "heels", "top", "tops", "shorts",
    "women", "men", "apparel", "footwear", "accessories"
}


def simple_stem(token: str) -> str:
    """Simple rule-based plural stripper for common fashion terms."""
    t = token.lower()
    if t.endswith("ies") and len(t) > 4:
        return t[:-3] + "y"
    elif t.endswith("sses") or t.endswith("shes") or t.endswith("ches"):
        return t[:-2]
    elif t.endswith("es") and len(t) > 4:
        return t[:-1]
    elif t.endswith("s") and not t.endswith("ss") and len(t) > 2 and t != "men":
        return t[:-1]
    return t


def normalize_query(query: str) -> List[str]:
    """Tokenizes, cleans, and stems a user search query."""
    if not query or not isinstance(query, str):
        return []
    cleaned = re.sub(r"[^\w\s-]", " ", query.lower())
    tokens = []
    for word in cleaned.split():
        clean_word = word.strip("-")
        if clean_word and clean_word not in STOPWORDS:
            stemmed = simple_stem(clean_word)
            if stemmed not in tokens:
                tokens.append(stemmed)
    return tokens


def load_catalog(db_path: str = "data/ecommerce_analytics.duckdb") -> List[Dict[str, Any]]:
    """Loads the product catalog from DuckDB into an in-memory searchable list."""
    con = duckdb.connect(db_path, read_only=True)
    df = con.execute(
        "SELECT product_id, title, brand, master_category, sub_category, "
        "effective_price, inventory_units, available_sizes FROM products"
    ).df()
    con.close()

    catalog = []
    for _, row in df.iterrows():
        title_tokens = normalize_query(str(row["title"]))
        brand_tokens = normalize_query(str(row["brand"]))
        master_tokens = normalize_query(str(row["master_category"]))
        sub_tokens = normalize_query(str(row["sub_category"]))
        size_tokens = [s.strip().lower() for s in str(row["available_sizes"]).split(",") if s.strip()]

        doc_tokens = set(title_tokens + brand_tokens + master_tokens + sub_tokens + size_tokens)

        catalog.append({
            "product_id": row["product_id"],
            "title": row["title"],
            "brand": row["brand"],
            "master_category": row["master_category"],
            "sub_category": row["sub_category"],
            "price": float(row["effective_price"]),
            "inventory_units": int(row["inventory_units"]),
            "tokens": doc_tokens,
        })
    return catalog


def strict_search(tokens: List[str], catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Performs strict boolean search: all tokens must be present.
    Filters out items with zero inventory.
    """
    matches = []
    for item in catalog:
        if item["inventory_units"] > 0 and all(t in item["tokens"] for t in tokens):
            matches.append(item)
    return matches


def relaxed_search(
    query: str, catalog: List[Dict[str, Any]], min_results: int = 3
) -> Dict[str, Any]:
    """
    Executes strict search with automated query relaxation fallback.
    
    Steps:
    1. Normalize query tokens.
    2. Run strict search.
    3. If results >= min_results, return strict matches.
    4. If query >= 4 tokens and results < min_results:
       - Identify candidate modifiers (protecting category nouns).
       - Try dropping 1 modifier.
       - If needed, try dropping 2 modifiers.
       - Ensure at least 2 tokens remain.
    5. Return relaxed matches or strict results if no safe fallback exists.
    """
    tokens = normalize_query(query)
    strict_results = strict_search(tokens, catalog)

    # Condition: Only relax if query is specific (>= 4 tokens) and returns few results (< 3)
    if len(tokens) < 4 or len(strict_results) >= min_results:
        return {
            "original_query": query,
            "tokens": tokens,
            "is_relaxed": False,
            "relaxed_query": query,
            "removed_tokens": [],
            "result_count": len(strict_results),
            "results": strict_results,
        }

    # Identify category terms vs droppable modifiers
    stemmed_category_terms = {simple_stem(c) for c in CATEGORY_TERMS}
    modifiers = [t for t in tokens if t not in stemmed_category_terms]
    droppable = modifiers if modifiers else tokens

    # Strategy 1: Single-token drops
    for mod in droppable:
        candidate_tokens = [t for t in tokens if t != mod]
        if len(candidate_tokens) >= 2:
            candidate_results = strict_search(candidate_tokens, catalog)
            if len(candidate_results) >= min_results:
                return {
                    "original_query": query,
                    "tokens": tokens,
                    "is_relaxed": True,
                    "relaxed_query": " ".join(candidate_tokens),
                    "removed_tokens": [mod],
                    "result_count": len(candidate_results),
                    "results": candidate_results,
                }

    # Strategy 2: Two-token drops (if 1-drop was insufficient)
    if len(droppable) >= 2:
        for m1, m2 in itertools.combinations(droppable, 2):
            candidate_tokens = [t for t in tokens if t != m1 and t != m2]
            if len(candidate_tokens) >= 2:
                candidate_results = strict_search(candidate_tokens, catalog)
                if len(candidate_results) >= min_results:
                    return {
                        "original_query": query,
                        "tokens": tokens,
                        "is_relaxed": True,
                        "relaxed_query": " ".join(candidate_tokens),
                        "removed_tokens": [m1, m2],
                        "result_count": len(candidate_results),
                        "results": candidate_results,
                    }

    # Strategy 3: Three-token drops (for queries with >= 5 tokens, ensuring at least 2 tokens remain)
    if len(tokens) >= 5 and len(droppable) >= 3:
        for m1, m2, m3 in itertools.combinations(droppable, 3):
            candidate_tokens = [t for t in tokens if t != m1 and t != m2 and t != m3]
            if len(candidate_tokens) >= 2:
                candidate_results = strict_search(candidate_tokens, catalog)
                if len(candidate_results) >= min_results:
                    return {
                        "original_query": query,
                        "tokens": tokens,
                        "is_relaxed": True,
                        "relaxed_query": " ".join(candidate_tokens),
                        "removed_tokens": [m1, m2, m3],
                        "result_count": len(candidate_results),
                        "results": candidate_results,
                    }

    # Fallback: No safe relaxation found
    return {
        "original_query": query,
        "tokens": tokens,
        "is_relaxed": False,
        "relaxed_query": query,
        "removed_tokens": [],
        "result_count": len(strict_results),
        "results": strict_results,
    }


def main():
    """Demonstrates strict search and query relaxation on sample queries."""
    print("=" * 70)
    print("E-COMMERCE SEARCH PROTOTYPE: STRICT VS RELAXED SEARCH")
    print("=" * 70)

    catalog = load_catalog()
    print(f"Catalog loaded: {len(catalog)} in-stock products indexed.\n")

    demo_queries = [
        "slim fit black dresses XL",
        "vintage black jeans L",
        "breathable black jeans M",
        "pure cotton white jeans 10",
        "shoes",
    ]

    for q in demo_queries:
        res = relaxed_search(q, catalog)
        print(f"Query: \"{q}\"")
        print(f"  Tokens: {res['tokens']}")
        print(f"  Relaxed: {res['is_relaxed']}")
        if res["is_relaxed"]:
            print(f"  Relaxed Query: \"{res['relaxed_query']}\" (dropped {res['removed_tokens']})")
        print(f"  Results Returned: {res['result_count']}")
        if res["results"]:
            sample = res["results"][0]
            print(f"  Example Match: {sample['title']} (${sample['price']:.2f})")
        print("-" * 70)


if __name__ == "__main__":
    main()
