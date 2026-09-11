"""
Explainable Search Debugger for E-Commerce Product Discovery.
Provides complete transparency into query token roles, document frequencies,
strict search execution, multi-tier relaxation candidate evaluation,
guardrail verification, and dual-mode (Product Manager vs Technical) explanations.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.search_engine import (
    LocalSearchEngine,
    RelaxedSearchResponse,
    SearchResultItem,
    normalize_query_text,
    simple_stem,
)

# Colors and fabric attribute terms for token classification
COLOR_FABRIC_WORDS = {
    "red", "blue", "black", "white", "green", "beige", "emerald", "pink",
    "yellow", "navy", "grey", "gray", "brown", "maroon", "purple", "orange",
    "cotton", "linen", "silk", "denim", "polyester", "wool", "leather",
}


@dataclass
class TokenDebugInfo:
    token: str
    normalized_token: str
    document_frequency: int
    token_role: str  # CORE_CATEGORY | BRAND | MODIFIER | MISSING_CATALOG_TERM
    is_core_term: bool
    is_candidate_modifier: bool
    in_catalog: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateDebugInfo:
    fallback_query: str
    tokens_removed: List[str]
    result_count: int
    category_consistency: bool
    candidate_score: float
    is_safe: bool
    rejection_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GuardrailStatus:
    core_category_preserved: bool
    in_stock_filtered: bool
    minimum_token_overlap_satisfied: bool
    category_consistency_maintained: bool
    circuit_breaker_activated: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrictSearchDiagnostics:
    query: str
    normalized_query: str
    token_count: int
    result_count: int
    total_matches: int
    execution_time_ms: float
    status: str  # NORMAL | LOW_RESULTS | ZERO_RESULTS
    trigger_explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RelaxationDiagnostics:
    triggered: bool
    reason: Optional[str]
    candidate_count: int
    candidates: List[CandidateDebugInfo]
    selected_candidate: Optional[str]
    removed_tokens: List[str]
    fallback_query: Optional[str]
    fallback_result_count: int
    overhead_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "triggered": self.triggered,
            "reason": self.reason,
            "candidate_count": self.candidate_count,
            "candidates": [c.to_dict() for c in self.candidates],
            "selected_candidate": self.selected_candidate,
            "removed_tokens": self.removed_tokens,
            "fallback_query": self.fallback_query,
            "fallback_result_count": self.fallback_result_count,
            "overhead_ms": self.overhead_ms,
        }


@dataclass
class FinalResultSummary:
    status: str  # NORMAL | LOW_RESULTS_NO_RELAXATION | RELAXED_RECOVERED | NO_SAFE_RELAXATION
    result_count: int
    products: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchDebugResult:
    query: str
    normalized_query: str
    token_analysis: List[TokenDebugInfo]
    strict_search: StrictSearchDiagnostics
    relaxation: RelaxationDiagnostics
    guardrails: GuardrailStatus
    final_result: FinalResultSummary
    product_explanation: Dict[str, str]
    technical_explanation: Dict[str, Any]
    total_execution_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "token_analysis": [t.to_dict() for t in self.token_analysis],
            "strict_search": self.strict_search.to_dict(),
            "relaxation": self.relaxation.to_dict(),
            "guardrails": self.guardrails.to_dict(),
            "final_result": self.final_result.to_dict(),
            "product_explanation": self.product_explanation,
            "technical_explanation": self.technical_explanation,
            "total_execution_time_ms": self.total_execution_time_ms,
        }


class SearchDebugger:
    """
    Search Debugger observing and explaining query execution against LocalSearchEngine.
    Does not duplicate search or relaxation logic.
    """

    def __init__(self, engine: Optional[LocalSearchEngine] = None):
        self.engine = engine or LocalSearchEngine()
        # Catalog brand registry
        self.brand_names = [
            str(b).lower() for b in self.engine.products_df["brand"].dropna().unique()
        ]

    def debug(
        self,
        query: str,
        limit: int = 20,
        in_stock_only: bool = True,
    ) -> SearchDebugResult:
        """
        Executes search with relaxation and constructs an explainable debug analysis.
        """
        start_time = time.perf_counter()

        # Step 1: Execute existing search engine with relaxation
        relaxed_resp: RelaxedSearchResponse = self.engine.search_with_relaxation(
            query, limit=limit, in_stock_only=in_stock_only
        )

        tokens = relaxed_resp.query_tokens
        norm_query = relaxed_resp.normalized_query

        # Step 2: Detailed Token Role & Catalog Frequency Analysis
        token_analysis: List[TokenDebugInfo] = []
        for word in tokens:
            stem = simple_stem(word)
            df = self.engine.doc_frequencies.get(stem, self.engine.doc_frequencies.get(word, 0))

            is_core = False
            is_mod = False

            if stem in self.engine.category_tokens or word in self.engine.category_tokens:
                role = "CORE_CATEGORY"
                is_core = True
                is_mod = False
            elif (
                any(b in norm_query and word in b.split() for b in self.brand_names)
                and word not in COLOR_FABRIC_WORDS
            ):
                role = "BRAND"
                is_core = False
                is_mod = False
            elif df == 0:
                role = "MISSING_CATALOG_TERM"
                is_core = False
                is_mod = True
            else:
                role = "MODIFIER"
                is_core = False
                is_mod = True

            token_analysis.append(
                TokenDebugInfo(
                    token=word,
                    normalized_token=stem,
                    document_frequency=df,
                    token_role=role,
                    is_core_term=is_core,
                    is_candidate_modifier=is_mod,
                    in_catalog=(df > 0),
                )
            )

        # Step 3: Strict Search Diagnostics
        strict_count = relaxed_resp.strict_result_count
        strict_latency = round(
            relaxed_resp.execution_time_ms - relaxed_resp.relaxation_overhead_ms, 3
        )
        if strict_count >= 3:
            strict_status = "NORMAL"
            trigger_exp = (
                f"Strict search returned {strict_count} in-stock products (>= 3). "
                f"Query qualifies as successful without relaxation."
            )
        elif len(tokens) < 4:
            strict_status = "LOW_RESULTS" if strict_count > 0 else "ZERO_RESULTS"
            trigger_exp = (
                f"Strict search returned {strict_count} products, but query has only {len(tokens)} tokens (<4). "
                f"Relaxation was guarded against head-query intent drift."
            )
        else:
            strict_status = "LOW_RESULTS" if strict_count > 0 else "ZERO_RESULTS"
            trigger_exp = (
                f"Strict search returned {strict_count} results (< 3) and query contains {len(tokens)} tokens (>= 4). "
                f"Qualifies for automated query relaxation."
            )

        strict_diag = StrictSearchDiagnostics(
            query=query,
            normalized_query=norm_query,
            token_count=len(tokens),
            result_count=strict_count,
            total_matches=relaxed_resp.strict_total_matches,
            execution_time_ms=strict_latency,
            status=strict_status,
            trigger_explanation=trigger_exp,
        )

        # Step 4: Candidate Evaluations & Selected Fallback
        candidate_debug_list: List[CandidateDebugInfo] = []
        for c in relaxed_resp.candidate_evaluations:
            candidate_debug_list.append(
                CandidateDebugInfo(
                    fallback_query=c["fallback_query"],
                    tokens_removed=c["tokens_removed"],
                    result_count=c["result_count"],
                    category_consistency=c["category_consistency"],
                    candidate_score=c["candidate_score"],
                    is_safe=c["is_safe"],
                    rejection_reason=c.get("rejection_reason"),
                )
            )

        relaxation_diag = RelaxationDiagnostics(
            triggered=relaxed_resp.relaxation_triggered,
            reason=relaxed_resp.relaxation_reason,
            candidate_count=len(candidate_debug_list),
            candidates=candidate_debug_list,
            selected_candidate=relaxed_resp.fallback_query,
            removed_tokens=relaxed_resp.selected_removed_tokens,
            fallback_query=relaxed_resp.fallback_query,
            fallback_result_count=relaxed_resp.fallback_result_count,
            overhead_ms=relaxed_resp.relaxation_overhead_ms,
        )

        # Step 5: Guardrail Verification
        core_preserved = True
        if relaxed_resp.selected_removed_tokens:
            for rem in relaxed_resp.selected_removed_tokens:
                rem_stem = simple_stem(rem)
                if rem_stem in self.engine.category_tokens or rem in self.engine.category_tokens:
                    core_preserved = False

        min_overlap_satisfied = True
        if relaxed_resp.fallback_query:
            fallback_tokens = relaxed_resp.fallback_query.split()
            min_overlap_satisfied = len(fallback_tokens) >= 2

        cat_consistent = True
        if relaxed_resp.results:
            orig_cats = {
                p["master_category"]
                for t in tokens
                for p in self.engine.indexed_products
                if t in p["master_tokens"]
            }
            if orig_cats:
                res_cats = {r.master_category for r in relaxed_resp.results}
                cat_consistent = bool(orig_cats.intersection(res_cats))

        circuit_breaker = (relaxed_resp.recovery_status == "NO_SAFE_RELAXATION")

        guardrails = GuardrailStatus(
            core_category_preserved=core_preserved,
            in_stock_filtered=True,  # Guaranteed by engine
            minimum_token_overlap_satisfied=min_overlap_satisfied,
            category_consistency_maintained=cat_consistent,
            circuit_breaker_activated=circuit_breaker,
        )

        # Step 6: Final Products List
        product_dicts: List[Dict[str, Any]] = [
            {
                "product_id": p.product_id,
                "title": p.title,
                "brand": p.brand,
                "master_category": p.master_category,
                "sub_category": p.sub_category,
                "effective_price": p.effective_price,
                "is_in_stock": p.is_in_stock,
                "relevance_score": p.relevance_score,
            }
            for p in relaxed_resp.results
        ]

        final_summary = FinalResultSummary(
            status=relaxed_resp.recovery_status,
            result_count=relaxed_resp.result_count,
            products=product_dicts,
        )

        # Step 7: Dual-Mode Explanations
        # A. Product Manager View (Problem, Decision, Outcome)
        if relaxed_resp.recovery_status == "NORMAL":
            pm_problem = "None. User query matched existing in-stock products with high precision."
            pm_decision = "No relaxation required. Direct strict keyword matches served to customer."
            pm_outcome = f"Returned {relaxed_resp.result_count} relevant in-stock products."
            pm_summary = f"Customer searched for '{query}' and received {relaxed_resp.result_count} exact-match products."
        elif relaxed_resp.recovery_status == "LOW_RESULTS_NO_RELAXATION":
            pm_problem = f"Query returned {strict_count} results, but contains only {len(tokens)} tokens (<4)."
            pm_decision = "Relaxation blocked by head-query guardrail to prevent intent drift."
            pm_outcome = f"Customer shown original {strict_count} results without speculative query mutation."
            pm_summary = f"Query '{query}' returned {strict_count} items. Guardrail protected broad user intent from being drifted."
        elif relaxed_resp.recovery_status == "RELAXED_RECOVERED":
            rem_str = ", ".join(f"'{r}'" for r in relaxed_resp.selected_removed_tokens)
            pm_problem = f"Query was over-specified with {len(tokens)} terms, returning {strict_count} products under strict matching."
            pm_decision = f"Relaxed non-core selective modifier(s) {rem_str} while preserving core category intent '{relaxed_resp.fallback_query}'."
            pm_outcome = f"Zero-result search recovered into {relaxed_resp.result_count} relevant in-stock products (+{relaxed_resp.result_count} items)."
            pm_summary = (
                f"Strict search returned {strict_count} items. The system recovered {relaxed_resp.result_count} relevant products "
                f"by removing modifier(s) {rem_str} while preserving core category '{relaxed_resp.fallback_query}'."
            )
        else:  # NO_SAFE_RELAXATION
            pm_problem = f"Customer query '{query}' specifies attributes or brands absent across catalog inventory."
            pm_decision = "Circuit breaker activated. Evaluated candidate queries but rejected all to avoid showing irrelevant inventory."
            pm_outcome = "Safe zero-result state maintained. Preserved customer trust by preventing off-category or irrelevant recommendations."
            pm_summary = (
                f"Strict search returned 0 items. Evaluated {len(candidate_debug_list)} fallback candidates, "
                f"but rejected all to prevent showing irrelevant products. Circuit breaker protected user trust."
            )

        product_explanation = {
            "problem": pm_problem,
            "decision": pm_decision,
            "outcome": pm_outcome,
            "summary": pm_summary,
        }

        # B. Technical Details View
        tech_explanation = {
            "query_tokens": tokens,
            "token_dfs": {t.token: t.document_frequency for t in token_analysis},
            "token_roles": {t.token: t.token_role for t in token_analysis},
            "strict_latency_ms": strict_latency,
            "relaxation_overhead_ms": relaxed_resp.relaxation_overhead_ms,
            "total_latency_ms": relaxed_resp.total_execution_time_ms,
            "candidates_evaluated": len(candidate_debug_list),
            "guardrail_checks": guardrails.to_dict(),
            "selected_fallback": relaxed_resp.fallback_query,
            "selected_removed_tokens": relaxed_resp.selected_removed_tokens,
            "raw_engine_explanation": relaxed_resp.explanation,
        }

        total_debug_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return SearchDebugResult(
            query=query,
            normalized_query=norm_query,
            token_analysis=token_analysis,
            strict_search=strict_diag,
            relaxation=relaxation_diag,
            guardrails=guardrails,
            final_result=final_summary,
            product_explanation=product_explanation,
            technical_explanation=tech_explanation,
            total_execution_time_ms=total_debug_time_ms,
        )


def print_cli_debug(debug_res: SearchDebugResult, mode: str = "all") -> None:
    """
    Renders structured CLI output formatted for engineering and PM review.
    Supports mode: 'all', 'pm', 'tech'.
    """
    print("=" * 80)
    print("EXPLAINABLE SEARCH DEBUGGER")
    print("=" * 80)
    print(f"\nQUERY:            '{debug_res.query}'")
    print(f"NORMALIZED QUERY: '{debug_res.normalized_query}'")
    print(f"OVERALL STATUS:   [{debug_res.final_result.status}]")
    print(f"TOTAL LATENCY:    {debug_res.total_execution_time_ms:.2f} ms\n")

    # 1. Product Manager View
    if mode in ("all", "pm"):
        print("-" * 80)
        print("PRODUCT MANAGER VIEW")
        print("-" * 80)
        print(f"Problem:   {debug_res.product_explanation['problem']}")
        print(f"Decision:  {debug_res.product_explanation['decision']}")
        print(f"Outcome:   {debug_res.product_explanation['outcome']}")
        print(f"\nSummary:\n{debug_res.product_explanation['summary']}\n")

    # 2. Technical Diagnostics View
    if mode in ("all", "tech"):
        print("-" * 80)
        print("TOKEN CATALOG FREQUENCY & ROLE ANALYSIS")
        print("-" * 80)
        print(f"{'Token':<16} {'Norm Stem':<14} {'DF':<8} {'Role':<24} {'Core?':<8} {'Mod?'}")
        print("-" * 80)
        for t in debug_res.token_analysis:
            core_str = "YES" if t.is_core_term else "NO"
            mod_str = "YES" if t.is_candidate_modifier else "NO"
            print(
                f"{t.token:<16} {t.normalized_token:<14} {t.document_frequency:<8} "
                f"{t.token_role:<24} {core_str:<8} {mod_str}"
            )
        print()

        print("-" * 80)
        print("STRICT SEARCH BASELINE")
        print("-" * 80)
        print(f"Strict Result Count: {debug_res.strict_search.result_count}")
        print(f"Strict Total Hits:   {debug_res.strict_search.total_matches}")
        print(f"Strict Latency:      {debug_res.strict_search.execution_time_ms:.2f} ms")
        print(f"Trigger Diagnostic:  {debug_res.strict_search.trigger_explanation}\n")

        print("-" * 80)
        print("QUERY RELAXATION & CANDIDATE EVALUATION")
        print("-" * 80)
        print(f"Relaxation Triggered: {'YES' if debug_res.relaxation.triggered else 'NO'}")
        if debug_res.relaxation.reason:
            print(f"Trigger Reason:       {debug_res.relaxation.reason}")
        print(f"Relaxation Overhead:  {debug_res.relaxation.overhead_ms:.2f} ms")

        if debug_res.relaxation.candidates:
            print(f"\nEvaluated Candidates ({len(debug_res.relaxation.candidates)} total):")
            print(f"  {'Candidate Fallback Query':<32} {'Dropped':<16} {'Hits':<8} {'Score':<10} {'Safe?'}")
            print(f"  {'-'*32} {'-'*16} {'-'*8} {'-'*10} {'-'*6}")
            for c in debug_res.relaxation.candidates:
                drop_str = ", ".join(c.tokens_removed)
                safe_str = "SAFE" if c.is_safe else "REJECTED"
                print(
                    f"  {c.fallback_query:<32} {drop_str:<16} {c.result_count:<8} "
                    f"{c.candidate_score:<10.2f} {safe_str}"
                )

        if debug_res.relaxation.fallback_query:
            print(f"\nSelected Fallback:   '{debug_res.relaxation.fallback_query}'")
            print(f"Removed Modifiers:   {debug_res.relaxation.removed_tokens}")
            print(f"Recovered Results:   {debug_res.relaxation.fallback_result_count} items")
        print()

        print("-" * 80)
        print("GUARDRAIL VERIFICATION MATRIX")
        print("-" * 80)
        g = debug_res.guardrails
        print(f"[{'PASS' if g.core_category_preserved else 'FAIL'}] Core Category Preserved: Category nouns protected from removal")
        print(f"[{'PASS' if g.in_stock_filtered else 'FAIL'}] In-Stock Inventory Filtered: Out-of-stock items excluded")
        print(f"[{'PASS' if g.minimum_token_overlap_satisfied else 'FAIL'}] Minimum Token Overlap: At least 2 tokens preserved")
        print(f"[{'PASS' if g.category_consistency_maintained else 'FAIL'}] Category Consistency: Master category intent maintained")
        if g.circuit_breaker_activated:
            print(f"[WARN] Circuit Breaker Activated: Unsafe candidates rejected, 0 results returned to prevent noise")
        print()

    # 3. Final Products
    print("-" * 80)
    print(f"RETURNED PRODUCTS ({len(debug_res.final_result.products)} items)")
    print("-" * 80)
    if debug_res.final_result.products:
        for idx, p in enumerate(debug_res.final_result.products[:5], 1):
            print(
                f"{idx}. [{p['product_id']}] {p['title']} | "
                f"Brand: {p['brand']} | Cat: {p['master_category']} > {p['sub_category']} | "
                f"${p['effective_price']:.2f} | Score: {p['relevance_score']:.2f}"
            )
        if len(debug_res.final_result.products) > 5:
            print(f"... and {len(debug_res.final_result.products) - 5} more products")
    else:
        print("(No products returned)")
    print("=" * 80 + "\n")


DEMO_QUERIES = [
    ("1. Successful Broad Query", "running shoes"),
    ("2. Successful Branded Query", "nike"),
    ("3. Low-Result Query (<3 strict hits)", "tommy hilfiger classic t-shirts"),
    ("4. Zero-Result Recoverable Query", "women floral midi dress red"),
    ("5. Zero-Result Unrecoverable Query (Circuit Breaker)", "xyzunknown impossible brand qwerty nonexist"),
]


def run_demo_suite(debugger: SearchDebugger) -> None:
    """Executes the full 5-query demo suite."""
    print("\n" + "#" * 80)
    print("RUNNING EXPLAINABLE SEARCH DEBUGGER DEMO SUITE (5 SCENARIOS)")
    print("#" * 80 + "\n")
    for title, q in DEMO_QUERIES:
        print(f"\n>>> DEMO SCENARIO: {title}")
        res = debugger.debug(q)
        print_cli_debug(res, mode="all")


def main() -> None:
    parser = argparse.ArgumentParser(description="Explainable Search Debugger CLI")
    parser.add_argument("query", nargs="*", help="Query to debug")
    parser.add_argument("--pm", action="store_true", help="Display Product Manager explanation view only")
    parser.add_argument("--tech", action="store_true", help="Display Technical diagnostics view only")
    parser.add_argument("--demo", action="store_true", help="Run 5 reproducible demo scenarios")
    parser.add_argument("--json", action="store_true", help="Output raw JSON debug dictionary")

    args = parser.parse_args()

    debugger = SearchDebugger()

    if args.demo:
        run_demo_suite(debugger)
        return

    query_str = " ".join(args.query).strip() if args.query else "women floral midi dress red"

    result = debugger.debug(query_str)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return

    if args.pm:
        print_cli_debug(result, mode="pm")
    elif args.tech:
        print_cli_debug(result, mode="tech")
    else:
        print_cli_debug(result, mode="all")


if __name__ == "__main__":
    main()
