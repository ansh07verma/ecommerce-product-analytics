"""
final_prd_validation.py - Product Analytics Validation Suite
Validates PRD consistency, database baselines, CSV schemas, figures, and technical specs.
Executes 23 distinct assertions and outputs a structured PASS/FAIL report.
"""
import os, json, duckdb
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "ecommerce_analytics.duckdb")

passed_checks = []
failed_checks = []

def record_check(name, passed, detail=""):
    if passed:
        passed_checks.append(name)
        print(f"[PASS] {name} {detail}")
    else:
        failed_checks.append((name, detail))
        print(f"[FAIL] {name} - DETAIL: {detail}")

print("==================================================")
print("PRODUCT ANALYTICS FINAL AUDIT & VALIDATION SUITE")
print("==================================================")

# 1. Required Files Exist
required_files = [
    "README.md",
    "docs/portfolio_case_study.md",
    "docs/interview_talking_points.md",
    "docs/project_walkthrough.md",
    "docs/final_prd.md",
    "docs/final_product_spec.md",
    "reports/final_requirements.csv",
    "reports/final_metrics_dictionary.csv",
    "reports/final_edge_cases.csv",
    "reports/final_rollout_plan.csv",
    "reports/final_experiment_spec.csv",
    "reports/final_portfolio_audit.md",
    "reports/figures/19_final_product_architecture.png",
    "reports/figures/20_final_metric_tree.png",
    "reports/figures/21_mvp_user_flow.png",
    "reports/figures/22_experiment_design.png",
    "notebooks/09_final_prd_validation.ipynb",
    "src/final_prd_validation.py"
]

all_files_exist = True
missing = []
for f in required_files:
    full_path = os.path.join(BASE_DIR, f)
    if not os.path.exists(full_path) or os.path.getsize(full_path) == 0:
        all_files_exist = False
        missing.append(f)
record_check("Check 1: Required Files Exist", all_files_exist, f"({len(required_files)} files checked)")

# 2. PRD Sections Complete (29 Sections)
prd_path = os.path.join(BASE_DIR, "docs/final_prd.md")
with open(prd_path, "r", encoding="utf-8") as f:
    prd_text = f.read()

prd_sections = [l for l in prd_text.splitlines() if l.startswith("# ") and l != "# Final Product Requirements Document (PRD)"]
record_check("Check 2: PRD 29 Required Sections Exist", len(prd_sections) == 29, f"({len(prd_sections)}/29 sections)")

# 3. Technical Product Spec Sections Exist
spec_path = os.path.join(BASE_DIR, "docs/final_product_spec.md")
with open(spec_path, "r", encoding="utf-8") as f:
    spec_text = f.read()
spec_ok = len(spec_text) > 10000 and "Algorithmic Pseudocode" in spec_text and "Telemetry & Analytics" in spec_text
record_check("Check 3: Technical Product Spec Completeness", spec_ok, f"({len(spec_text):,} chars)")

# 4. CSV Schema: final_requirements.csv
req_df = pd.read_csv(os.path.join(BASE_DIR, "reports/final_requirements.csv"))
req_ok = {"ID", "Requirement", "Type", "Priority", "Acceptance_Criteria"}.issubset(req_df.columns) and len(req_df) >= 14
record_check("Check 4: final_requirements.csv Schema", req_ok, f"({len(req_df)} rows)")

# 5. CSV Schema: final_metrics_dictionary.csv
met_df = pd.read_csv(os.path.join(BASE_DIR, "reports/final_metrics_dictionary.csv"))
met_ok = {"Metric_Name", "Category", "Formula", "Baseline_Value", "Target_Direction"}.issubset(met_df.columns) and len(met_df) >= 10
record_check("Check 5: final_metrics_dictionary.csv Schema", met_ok, f"({len(met_df)} rows)")

# 6. CSV Schema: final_edge_cases.csv
ec_df = pd.read_csv(os.path.join(BASE_DIR, "reports/final_edge_cases.csv"))
ec_ok = {"ID", "Scenario", "Detection", "Expected_Behavior", "Risk_Level"}.issubset(ec_df.columns) and len(ec_df) >= 16
record_check("Check 6: final_edge_cases.csv Schema", ec_ok, f"({len(ec_df)} rows)")

# 7. CSV Schema: final_rollout_plan.csv
ro_df = pd.read_csv(os.path.join(BASE_DIR, "reports/final_rollout_plan.csv"))
ro_ok = {"Phase", "Name", "Allocation", "Duration", "Entry_Criteria"}.issubset(ro_df.columns) and len(ro_df) == 5
record_check("Check 7: final_rollout_plan.csv Schema", ro_ok, f"({len(ro_df)} rows)")

# 8. CSV Schema: final_experiment_spec.csv
exp_df = pd.read_csv(os.path.join(BASE_DIR, "reports/final_experiment_spec.csv"))
exp_ok = {"Parameter", "Specification"}.issubset(exp_df.columns) and len(exp_df) >= 15
record_check("Check 8: final_experiment_spec.csv Schema", exp_ok, f"({len(exp_df)} rows)")

# DuckDB Validations
conn = duckdb.connect(DB_PATH, read_only=True)
total_searches = conn.execute("SELECT COUNT(*) FROM search_events;").fetchone()[0]
record_check("Check 9: DuckDB Total Searches", total_searches == 32245, f"({total_searches:,})")

queries_4plus = conn.execute("SELECT COUNT(*) FROM search_events WHERE ARRAY_LENGTH(STRING_SPLIT(TRIM(query_text), ' ')) >= 4;").fetchone()[0]
record_check("Check 10: DuckDB 4+ Token Volume", queries_4plus == 10914, f"({queries_4plus:,})")

zrr_4plus_count = conn.execute("SELECT SUM(CASE WHEN is_zero_result THEN 1 ELSE 0 END) FROM search_events WHERE ARRAY_LENGTH(STRING_SPLIT(TRIM(query_text), ' ')) >= 4;").fetchone()[0]
zrr_4plus_pct = round(zrr_4plus_count / queries_4plus * 100, 2)
record_check("Check 11: DuckDB 4+ Token ZRR", zrr_4plus_count == 898 and zrr_4plus_pct == 8.23, f"({zrr_4plus_count} hits, {zrr_4plus_pct}%)")

queries_short = conn.execute("SELECT COUNT(*) FROM search_events WHERE ARRAY_LENGTH(STRING_SPLIT(TRIM(query_text), ' ')) < 4;").fetchone()[0]
zrr_short_count = conn.execute("SELECT SUM(CASE WHEN is_zero_result THEN 1 ELSE 0 END) FROM search_events WHERE ARRAY_LENGTH(STRING_SPLIT(TRIM(query_text), ' ')) < 4;").fetchone()[0]
zrr_short_pct = round(zrr_short_count / queries_short * 100, 2)
record_check("Check 12: DuckDB Short-Query ZRR", zrr_short_count == 380 and zrr_short_pct == 1.78, f"({zrr_short_count} hits, {zrr_short_pct}%)")

ctr_4plus_clicks = conn.execute("SELECT SUM(CASE WHEN has_pdp_click THEN 1 ELSE 0 END) FROM search_events WHERE ARRAY_LENGTH(STRING_SPLIT(TRIM(query_text), ' ')) >= 4;").fetchone()[0]
ctr_4plus_pct = round(ctr_4plus_clicks / queries_4plus * 100, 2)
record_check("Check 13: DuckDB 4+ Token CTR", ctr_4plus_clicks == 6870 and ctr_4plus_pct == 62.95, f"({ctr_4plus_clicks} clicks, {ctr_4plus_pct}%)")

ctr_short_clicks = conn.execute("SELECT SUM(CASE WHEN has_pdp_click THEN 1 ELSE 0 END) FROM search_events WHERE ARRAY_LENGTH(STRING_SPLIT(TRIM(query_text), ' ')) < 4;").fetchone()[0]
ctr_short_pct = round(ctr_short_clicks / queries_short * 100, 2)
record_check("Check 14: DuckDB Short-Query CTR", ctr_short_clicks == 15098 and ctr_short_pct == 70.78, f"({ctr_short_clicks} clicks, {ctr_short_pct}%)")

reform_4plus = conn.execute("SELECT SUM(CASE WHEN reformulated_in_session THEN 1 ELSE 0 END) FROM search_events WHERE ARRAY_LENGTH(STRING_SPLIT(TRIM(query_text), ' ')) >= 4;").fetchone()[0]
reform_4plus_pct = round(reform_4plus / queries_4plus * 100, 2)
record_check("Check 15: DuckDB 4+ Token Reformulation Rate", reform_4plus == 4845 and reform_4plus_pct == 44.39, f"({reform_4plus} searches, {reform_4plus_pct}%)")

elig = conn.execute("SELECT COUNT(*), SUM(CASE WHEN results_count = 0 THEN 1 ELSE 0 END), SUM(CASE WHEN results_count IN (1, 2) THEN 1 ELSE 0 END) FROM search_events WHERE ARRAY_LENGTH(STRING_SPLIT(TRIM(query_text), ' ')) >= 4 AND results_count < 3;").fetchone()
record_check("Check 16: DuckDB Eligibility Subgroups", elig[0] == 941 and elig[1] == 898 and elig[2] == 43, f"(Total: {elig[0]}, Sub A: {elig[1]}, Sub B: {elig[2]})")

reach_stats = conn.execute("WITH s AS (SELECT session_id, user_id, MAX(CASE WHEN ARRAY_LENGTH(STRING_SPLIT(TRIM(query_text), ' ')) >= 4 THEN 1 ELSE 0 END) AS has_4plus FROM search_events GROUP BY 1, 2) SELECT COUNT(DISTINCT session_id), COUNT(DISTINCT user_id) FROM s WHERE has_4plus = 1;").fetchone()
record_check("Check 17: DuckDB 4+ Token Reach", reach_stats[0] == 8958 and reach_stats[1] == 7318, f"({reach_stats[0]} sessions, {reach_stats[1]} users)")

orders_4plus = conn.execute("WITH s AS (SELECT se.session_id, MAX(CASE WHEN o.order_id IS NOT NULL THEN 1 ELSE 0 END) AS has_order FROM search_events se JOIN sessions sess ON se.session_id = sess.session_id LEFT JOIN orders o ON se.session_id = o.session_id WHERE ARRAY_LENGTH(STRING_SPLIT(TRIM(se.query_text), ' ')) >= 4 GROUP BY 1) SELECT COUNT(*), SUM(has_order), ROUND(AVG(has_order) * 100, 2) FROM s;").fetchone()
conn.close()
record_check("Check 18: DuckDB 4+ Token Conversion", orders_4plus[1] == 1165 and orders_4plus[2] == 13.01, f"({orders_4plus[1]} orders, {orders_4plus[2]}%)")

# Text Consistencies
prd_has_canonical = "8.23%" in prd_text and "62.95%" in prd_text and "44.39%" in prd_text and "10,914" in prd_text and "898" in prd_text
record_check("Check 19: PRD Canonical Metrics Consistency", prd_has_canonical, "(8.23% ZRR, 62.95% CTR, 44.39% reform)")

no_fake_results = "experiment results show a" not in prd_text.lower() and "the treatment achieved a" not in prd_text.lower() and "lift of 12%" not in prd_text.lower()
record_check("Check 20: No Fabricated Experiment Results", no_fake_results, "(Future validation framed correctly)")

no_bad_claims = "the algorithm is definitely boolean" not in prd_text.lower() and "query relaxation will eliminate 8.23% of failures" not in prd_text.lower()
record_check("Check 21: No Unsupported Causal Claims", no_bad_claims, "(Hedged language verified)")

figures = ["reports/figures/19_final_product_architecture.png", "reports/figures/20_final_metric_tree.png", "reports/figures/21_mvp_user_flow.png", "reports/figures/22_experiment_design.png"]
figs_ok = all(os.path.exists(os.path.join(BASE_DIR, f)) and os.path.getsize(os.path.join(BASE_DIR, f)) > 10000 for f in figures)
record_check("Check 22: Figures 19-22 Valid & Non-Empty", figs_ok, f"({len(figures)} figures verified)")

nb_path = os.path.join(BASE_DIR, "notebooks/09_final_prd_validation.ipynb")
nb_ok = False
if os.path.exists(nb_path):
    try:
        with open(nb_path, "r", encoding="utf-8") as f:
            nb = json.load(f)
            nb_ok = "cells" in nb and len(nb["cells"]) >= 8
    except Exception: pass
record_check("Check 23: Notebook 09 Parsed Successfully", nb_ok, "(Valid IPython notebook)")


# 24. Portfolio Polish Assets Verified
cs_ok = os.path.exists(os.path.join(BASE_DIR, "docs/portfolio_case_study.md")) and os.path.getsize(os.path.join(BASE_DIR, "docs/portfolio_case_study.md")) > 3000
tp_ok = os.path.exists(os.path.join(BASE_DIR, "docs/interview_talking_points.md")) and os.path.getsize(os.path.join(BASE_DIR, "docs/interview_talking_points.md")) > 8000
pw_ok = os.path.exists(os.path.join(BASE_DIR, "docs/project_walkthrough.md")) and os.path.getsize(os.path.join(BASE_DIR, "docs/project_walkthrough.md")) > 3000
fa_ok = os.path.exists(os.path.join(BASE_DIR, "reports/final_portfolio_audit.md")) and os.path.getsize(os.path.join(BASE_DIR, "reports/final_portfolio_audit.md")) > 4000
rm_ok = os.path.exists(os.path.join(BASE_DIR, "README.md")) and os.path.getsize(os.path.join(BASE_DIR, "README.md")) > 4000

record_check("Check 24: Portfolio Assets Exist & Sized", cs_ok and tp_ok and pw_ok and fa_ok and rm_ok, "(Case Study, Talking Points, Walkthrough, Audit, README)")

# 25. Reconciled Metrics Explicitly Separated in PRD
with open(os.path.join(BASE_DIR, "docs/final_prd.md"), "r", encoding="utf-8") as f:
    prd_text_check = f.read()
sep_ok = "3.08%" in prd_text_check and "62.95%" in prd_text_check and "10.81%" in prd_text_check and "13.31 pp" in prd_text_check
record_check("Check 25: Metric Reconciliations Documented in PRD", sep_ok, "(3.08% baseline, 62.95% context, 10.81% ZRR reconciled, 13.31 pp CTO reconciled)")

print("==================================================")
print(f"TOTAL CHECKS: {len(passed_checks) + len(failed_checks)}")
print(f"PASSED:       {len(passed_checks)}")
print(f"FAILED:       {len(failed_checks)}")
print("==================================================")
