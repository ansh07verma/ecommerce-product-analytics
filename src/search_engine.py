"""
Deterministic Local E-Commerce Search Engine MVP & Query Relaxation Engine.
Provides strict keyword-based product retrieval, ranking, stock filtering,
and intelligent automated query relaxation / soft-match fallback against
the catalog stored in DuckDB / raw CSV.
"""

from __future__ import annotations

import itertools
import os
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import duckdb
import pandas as pd


# Minimal functional stopwords in English fashion queries (preserving domain terms like 'men', 'women')
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


@dataclass
class CandidateFallback:
    remaining_tokens: List[str]
    dropped_tokens: List[str]
    candidate_query: str


@dataclass
class RelaxedSearchResponse:
    original_query: str
    normalized_query: str
    query_tokens: List[str]
    strict_result_count: int
    strict_total_matches: int
    relaxation_triggered: bool
    relaxation_reason: Optional[str]
    recovery_status: str  # NORMAL | LOW_RESULTS_NO_RELAXATION | RELAXED_RECOVERED | NO_SAFE_RELAXATION
    candidate_queries: List[str]
    selected_removed_tokens: List[str]
    fallback_query: Optional[str]
    fallback_result_count: int
    total_matches: int
    execution_time_ms: float
    relaxation_overhead_ms: float
    in_stock_only: bool
    explanation: str
    results: List[SearchResultItem]

    @property
    def selected_removed_token(self) -> Optional[str]:
        """Convenience property for single-token removal compatibility."""
        return self.selected_removed_tokens[0] if self.selected_removed_tokens else None

    @property
    def total_execution_time_ms(self) -> float:
        """Alias for execution_time_ms per specification."""
        return self.execution_time_ms

    @property
    def result_count(self) -> int:
        return len(self.results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "normalized_query": self.normalized_query,
            "query_tokens": self.query_tokens,
            "strict_result_count": self.strict_result_count,
            "strict_total_matches": self.strict_total_matches,
            "relaxation_triggered": self.relaxation_triggered,
            "relaxation_reason": self.relaxation_reason,
            "recovery_status": self.recovery_status,
            "candidate_queries": self.candidate_queries,
            "selected_removed_tokens": self.selected_removed_tokens,
            "selected_removed_token": self.selected_removed_token,
            "fallback_query": self.fallback_query,
            "fallback_result_count": self.fallback_result_count,
            "total_matches": self.total_matches,
            "total_execution_time_ms": self.execution_time_ms,
            "execution_time_ms": self.execution_time_ms,
            "relaxation_overhead_ms": self.relaxation_overhead_ms,
            "in_stock_only": self.in_stock_only,
            "explanation": self.explanation,
            "results": [asdict(r) for r in self.results],
        }


class LocalSearchEngine:
    """
    In-Memory Keyword Search & Query Relaxation Engine for E-Commerce Product Catalog.
    Indexes the 1,600 product catalog and executes deterministic strict keyword matching
    with automated query relaxation fallback.
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
        Precomputes tokenized representation, field lookup structures,
        and domain category terminology for fast, deterministic in-memory matching.
        """
        self.indexed_products: List[Dict[str, Any]] = []
        self.category_tokens: Set[str] = set()

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

            self.category_tokens.update(master_tokens)
            self.category_tokens.update(sub_tokens)

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

        # Precompute document frequencies across all catalog tokens
        self.doc_frequencies: Dict[str, int] = {}
        for p in self.indexed_products:
            for t in p["doc_tokens"]:
                self.doc_frequencies[t] = self.doc_frequencies.get(t, 0) + 1

    def search(
        self,
        query: str,
        limit: int = 20,
        in_stock_only: bool = True,
    ) -> SearchResponse:
        """
        Executes deterministic strict keyword search against the catalog.
        Requires all query tokens to be present in candidate products.
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

    def _generate_candidate_fallbacks(self, tokens: List[str]) -> List[CandidateFallback]:
        """
        Deterministic Candidate Generation:
        Generates candidate token combinations by dropping 1 or 2 tokens, preserving order.
        Guarantees at least 2 tokens remain.
        """
        candidates: List[CandidateFallback] = []
        n = len(tokens)
        if n < 3:
            return candidates

        # Tier 1: Single token drops
        for i in range(n):
            rem = [t for j, t in enumerate(tokens) if j != i]
            drop = [tokens[i]]
            candidates.append(CandidateFallback(remaining_tokens=rem, dropped_tokens=drop, candidate_query=" ".join(rem)))

        # Tier 2: Double token drops
        if n >= 4:
            for i, j in itertools.combinations(range(n), 2):
                rem = [tokens[k] for k in range(n) if k != i and k != j]
                drop = [tokens[i], tokens[j]]
                if len(rem) >= 2:
                    candidates.append(CandidateFallback(remaining_tokens=rem, dropped_tokens=drop, candidate_query=" ".join(rem)))

        return candidates

    def search_with_relaxation(
        self,
        query: str,
        limit: int = 20,
        in_stock_only: bool = True,
        min_results: int = 3,
    ) -> RelaxedSearchResponse:
        """
        Executes strict search with intelligent automated query relaxation fallback.
        Triggers relaxation ONLY when:
          1. len(query_tokens) >= 4 (specific query)
          2. strict_result_count < min_results (default 3)

        Preserves core product/category intent, identifies candidate modifiers based on
        catalog document frequency, evaluates candidate queries deterministically, and applies
        category consistency and in-stock guardrails.
        """
        start_time = time.perf_counter()

        # Step 1: Execute strict search baseline
        strict_resp = self.search(query, limit=limit, in_stock_only=in_stock_only)
        strict_time = time.perf_counter()
        strict_latency_ms = strict_resp.execution_time_ms
        query_tokens = strict_resp.query_tokens
        strict_count = strict_resp.result_count

        # Step 2: Check relaxation trigger conditions
        # Case A: Short query (< 4 tokens) -> No relaxation to prevent head-query drift
        if len(query_tokens) < 4:
            status = "NORMAL" if strict_count >= min_results else "LOW_RESULTS_NO_RELAXATION"
            total_time_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
            explanation = (
                f"Strict search returned {strict_count} in-stock results. No query relaxation needed."
                if status == "NORMAL"
                else f"Strict search returned {strict_count} results, but query has {len(query_tokens)} tokens (<4). "
                f"Query relaxation was not triggered to protect head-query intent."
            )
            return RelaxedSearchResponse(
                original_query=query,
                normalized_query=strict_resp.normalized_query,
                query_tokens=query_tokens,
                strict_result_count=strict_count,
                strict_total_matches=strict_resp.total_matches,
                relaxation_triggered=False,
                relaxation_reason=None,
                recovery_status=status,
                candidate_queries=[],
                selected_removed_tokens=[],
                fallback_query=None,
                fallback_result_count=strict_count,
                total_matches=strict_resp.total_matches,
                execution_time_ms=total_time_ms,
                relaxation_overhead_ms=0.0,
                in_stock_only=in_stock_only,
                explanation=explanation,
                results=strict_resp.results,
            )

        # Case B: Specific query (>= 4 tokens) with adequate results -> Normal
        if strict_count >= min_results:
            total_time_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
            explanation = (
                f"Strict search returned {strict_count} in-stock results (>= {min_results}). "
                f"No query relaxation needed."
            )
            return RelaxedSearchResponse(
                original_query=query,
                normalized_query=strict_resp.normalized_query,
                query_tokens=query_tokens,
                strict_result_count=strict_count,
                strict_total_matches=strict_resp.total_matches,
                relaxation_triggered=False,
                relaxation_reason=None,
                recovery_status="NORMAL",
                candidate_queries=[],
                selected_removed_tokens=[],
                fallback_query=None,
                fallback_result_count=strict_count,
                total_matches=strict_resp.total_matches,
                execution_time_ms=total_time_ms,
                relaxation_overhead_ms=0.0,
                in_stock_only=in_stock_only,
                explanation=explanation,
                results=strict_resp.results,
            )

        # Case C: Relaxation Triggered! (>= 4 tokens AND < 3 results)
        relaxation_reason = (
            f"Strict search returned fewer than {min_results} results ({strict_count} returned) "
            f"for a specific {len(query_tokens)}-token query."
        )

        # Step 3: Identify Candidate Modifiers & Document Frequencies
        token_dfs: Dict[str, int] = {}
        for t in query_tokens:
            token_dfs[t] = self.doc_frequencies.get(t, 0)

        # Categorize tokens into category terms vs. modifiers
        modifiers = [t for t in query_tokens if t not in self.category_tokens]
        category_terms = [t for t in query_tokens if t in self.category_tokens]

        # In the rare edge case where all tokens are category tokens, allow dropping the most selective category term
        tokens_eligible_to_drop = modifiers if modifiers else query_tokens

        # Step 4: Generate Candidate Fallback Queries
        # Priority ordering: tokens with lowest catalog DF (most selective or completely absent first)
        sorted_droppable = sorted(tokens_eligible_to_drop, key=lambda t: (token_dfs[t], t))

        candidates_to_eval: List[Tuple[str, List[str]]] = []

        # Tier 1: Single-token drops
        for m in sorted_droppable:
            cand_tokens = [t for t in query_tokens if t != m]
            candidates_to_eval.append((" ".join(cand_tokens), [m]))

        # Tier 2: Two-token drops (if needed and feasible)
        if len(sorted_droppable) >= 2:
            for m1, m2 in itertools.combinations(sorted_droppable, 2):
                cand_tokens = [t for t in query_tokens if t != m1 and t != m2]
                candidates_to_eval.append((" ".join(cand_tokens), sorted([m1, m2])))

        # Tier 3: Three-token drops (for very long queries >= 5 tokens)
        if len(query_tokens) >= 5 and len(sorted_droppable) >= 3:
            for m1, m2, m3 in itertools.combinations(sorted_droppable, 3):
                cand_tokens = [t for t in query_tokens if t != m1 and t != m2 and t != m3]
                # Ensure at least 2 tokens remain
                if len(cand_tokens) >= 2:
                    candidates_to_eval.append((" ".join(cand_tokens), sorted([m1, m2, m3])))

        # Step 5 & 6: Evaluate Candidates & Apply Relevance Guardrails
        best_cand: Optional[str] = None
        best_score = -1e9
        best_resp: Optional[SearchResponse] = None
        best_removed: List[str] = []
        evaluated_queries: List[str] = []

        # Detect original master category intention (e.g. Women, Men, Footwear, Accessories)
        orig_master_cats: Set[str] = set()
        for t in query_tokens:
            for p in self.indexed_products:
                if t in p["master_tokens"]:
                    orig_master_cats.add(p["master_category"])

        for cand_str, removed_tokens in candidates_to_eval:
            if cand_str in evaluated_queries:
                continue
            evaluated_queries.append(cand_str)

            cand_resp = self.search(cand_str, limit=limit, in_stock_only=in_stock_only)
            r_count = cand_resp.result_count

            if r_count == 0:
                continue

            # Deterministic Candidate Scoring Formula
            score = 0.0

            # 1. Result Recovery Quality
            if r_count >= min_results:
                score += 50.0
            else:
                score += 20.0
            score += min(15.0, r_count * 1.5)

            # 2. Intent Preservation / Token Retention
            retention_ratio = len(cand_resp.query_tokens) / len(query_tokens)
            score += retention_ratio * 25.0
            score -= len(removed_tokens) * 8.0  # Penalty per token removed

            # Heavy penalty if a core category was dropped when modifiers were available
            if any(t in self.category_tokens for t in removed_tokens) and modifiers:
                score -= 100.0

            # 3. Category Consistency Guardrail
            cand_master_cats = set(item.master_category for item in cand_resp.results)
            if orig_master_cats:
                overlap = orig_master_cats.intersection(cand_master_cats)
                if overlap:
                    score += 25.0
                else:
                    score -= 80.0  # Severe penalty for category drift
            else:
                score += 10.0

            # 4. Average Relevance Quality
            avg_rel = sum(item.relevance_score for item in cand_resp.results) / max(1, r_count)
            score += avg_rel * 0.15

            if score > best_score:
                best_score = score
                best_cand = cand_str
                best_resp = cand_resp
                best_removed = removed_tokens
                # Early stop if a single-token drop successfully recovers >= min_results
                if r_count >= min_results and len(removed_tokens) == 1:
                    break

        total_time_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
        overhead_ms = round(max(0.0, total_time_ms - strict_latency_ms), 3)

        # Step 7 & 8: Build Structured Response & Explanation
        if best_cand and best_resp and best_resp.result_count > 0:
            status = "RELAXED_RECOVERED"
            removed_desc = ", ".join(f"'{r}' (catalog DF={token_dfs.get(r, 0)})" for r in best_removed)
            explanation = (
                f"Strict search returned {strict_count} results for '{query}'. "
                f"The modifier(s) {removed_desc} were identified as non-core attributes causing strict retrieval failure. "
                f"Relaxing them preserved core category intent '{best_cand}', "
                f"successfully recovering {best_resp.result_count} relevant in-stock products in {overhead_ms:.2f} ms."
            )
            return RelaxedSearchResponse(
                original_query=query,
                normalized_query=strict_resp.normalized_query,
                query_tokens=query_tokens,
                strict_result_count=strict_count,
                strict_total_matches=strict_resp.total_matches,
                relaxation_triggered=True,
                relaxation_reason=relaxation_reason,
                recovery_status=status,
                candidate_queries=evaluated_queries,
                selected_removed_tokens=best_removed,
                fallback_query=best_cand,
                fallback_result_count=best_resp.result_count,
                total_matches=best_resp.total_matches,
                execution_time_ms=total_time_ms,
                relaxation_overhead_ms=overhead_ms,
                in_stock_only=in_stock_only,
                explanation=explanation,
                results=best_resp.results,
            )
        else:
            status = "NO_SAFE_RELAXATION"
            explanation = (
                f"Strict search returned {strict_count} results for '{query}'. "
                f"Evaluated {len(evaluated_queries)} candidate relaxed queries, but none produced safe, "
                f"category-consistent in-stock matches in the product catalog."
            )
            return RelaxedSearchResponse(
                original_query=query,
                normalized_query=strict_resp.normalized_query,
                query_tokens=query_tokens,
                strict_result_count=strict_count,
                strict_total_matches=strict_resp.total_matches,
                relaxation_triggered=True,
                relaxation_reason=relaxation_reason,
                recovery_status=status,
                candidate_queries=evaluated_queries,
                selected_removed_tokens=[],
                fallback_query=None,
                fallback_result_count=strict_count,
                total_matches=strict_resp.total_matches,
                execution_time_ms=total_time_ms,
                relaxation_overhead_ms=overhead_ms,
                in_stock_only=in_stock_only,
                explanation=explanation,
                results=strict_resp.results,
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


def print_cli_search(response: SearchResponse | RelaxedSearchResponse) -> None:
    """Renders formatted CLI search output matching the project specification."""
    print("========================================")
    if isinstance(response, RelaxedSearchResponse) and response.relaxation_triggered:
        print("SEARCH (WITH AUTOMATED QUERY RELAXATION)")
    else:
        print("SEARCH")
    print("========================================")
    print(f"\nQuery:\n{response.original_query}\n")
    print(f"Normalized Query:\n{response.normalized_query}\n")

    if isinstance(response, RelaxedSearchResponse):
        print(f"Strict Result Count:\n{response.strict_result_count}\n")
        if response.relaxation_triggered:
            print(f"[RELAXATION TRIGGERED]")
            print(f"Reason: {response.relaxation_reason}")
            print(f"Recovery Status: {response.recovery_status}")
            if response.fallback_query:
                print(f"Selected Removed Token(s): {response.selected_removed_tokens}")
                print(f"Fallback Query: {response.fallback_query}")
                print(f"Fallback Result Count: {response.fallback_result_count}")
            print(f"\nExplanation:\n{response.explanation}\n")

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

    final_count = response.result_count
    print(f"Final Returned Result Count:\n{final_count}")
    if response.total_matches > final_count:
        print(f"Total Matches in Catalog: {response.total_matches}")
    print(f"\nExecution Time:\n{response.execution_time_ms:.2f} ms")
    if isinstance(response, RelaxedSearchResponse) and response.relaxation_overhead_ms > 0:
        print(f"Relaxation Overhead: {response.relaxation_overhead_ms:.2f} ms")
    print("========================================\n")


if __name__ == "__main__":
    import sys

    default_query = "women floral midi dress red"
    query_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else default_query

    engine = LocalSearchEngine()
    resp = engine.search_with_relaxation(query_input)
    print_cli_search(resp)
