# E-Commerce Product Analytics: Search Discovery Optimization & Automated Query Relaxation

> **A rigorous Product Management & Product Analytics case study diagnosing search discovery breakdown on multi-attribute queries, designing an automated soft-match fallback engine, modeling A/B experimentation, and demonstrating capital discipline in e-commerce search infrastructure.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.0+-FFF000?style=flat&logo=duckdb&logoColor=black)](https://duckdb.org/)
[![Tests](https://img.shields.io/badge/Tests-71%20Passed-brightgreen?style=flat)](tests/)
[![PRD Validation](https://img.shields.io/badge/PRD%20Checks-25%2F25%20Passed-brightgreen?style=flat)](src/final_prd_validation.py)
[![Data Validation](https://img.shields.io/badge/Data%20Checks-59%2F59%20Passed-brightgreen?style=flat)](src/data_validation.py)
[![Product Focus](https://img.shields.io/badge/Focus-Product%20Management%20%7C%20Analytics-blueviolet?style=flat)](reports/)

---

## 🎯 Portfolio Quick Links

- 📄 **[Definitive PM Case Study](reports/final_pm_case_study.md)**: Complete 17-section portfolio case study covering problem diagnosis, algorithm architecture, competitive trade-offs, A/B experiment design, and capital discipline.
- 🎤 **[PM Interview Cheat Sheet](reports/pm_interview_cheat_sheet.md)**: 30s / 60s / 2min elevator pitches, Top 15 interview defense questions with supporting metrics and caveats.
- 📊 **[Interactive Search Health Dashboard](reports/search_dashboard.html)**: Standalone single-file HTML/JS dashboard with 6 visual panels (KPIs, Funnel, Relaxation Recovery, A/B Simulator, and ROI Sensitivity).
- 🔍 **[Interactive Search Debugger UI](docs/search_debugger_guide.md)**: Local developer & PM debugger showing real-time token classification, candidate ranking, and guardrail enforcement.

---

## ⚡ 60-Second Executive Summary

1. **The Discovery Failure**: In an apparel marketplace dataset (32,245 searches, 16,000 users in DuckDB), shoppers typing specific multi-attribute queries ($\ge 4$ words like *"women red silk evening dress"*) experienced an **8.23% historical zero-result rate** [OBSERVED] (4.6x higher than head queries) and a **44.39% manual reformulation rate** [OBSERVED]. Search-to-PDP Click-Through Rate (CTR) for these 941 low-result searches collapsed to **3.08%** [OBSERVED].
2. **Root Cause**: Over-specification. Shoppers use natural descriptive modifiers (color, fabric, occasion). Strict conjunctive boolean search fails when a single non-essential modifier misses catalog metadata, even when matching inventory exists.
3. **The V1 Intervention**: Evaluated six search technologies via a weighted decision matrix. Selected **Automated Query Relaxation / Soft-Match Fallback** (#1 rank, 9.05 score) [PRODUCT ASSUMPTION] over vector search and LLMs because it directly fixes over-specification, runs deterministically in under 39ms, requires zero cloud API cost, and provides explainable fallback results.
4. **Validation & Latency**: On local benchmarks across 879 unmatchable queries, relaxation achieved a **91.81% algorithmic recovery rate** [LOCAL BENCHMARK], reducing strict zero-result rate from 98.21% down to 8.40% (-80.70 pp reduction). P95 total latency was **38.53 ms** [LOCAL BENCHMARK], well within our $\le 50	ext{ ms}$ relaxation budget and $\le 250	ext{ ms}$ end-to-end Gateway SLA.
5. **Experimentation & Business Impact**: Designed an offline A/B experiment (50/50 user hashing, two-proportion z-test) targeting a +3.5 pp CTR lift (76 days to power at ~15.7 searches/day) [MODELED]. Business modeling projects **+$1,808.69 in gross annualized GMV** (**+$1,356.52 net** at 25% cannibalization) [MODELED]. At 100x traffic scale, this grows to **+$180.9K/year** with zero marginal infrastructure cost.
6. **PM Capital Discipline Decision**: **Validate before scaling.** At current boutique volume, standalone return does not justify a $28.5K dedicated search cluster [PRODUCT ASSUMPTION]. Recommendation is to deploy a lightweight canary experiment; ship if CTR lift $\ge +1.5	ext{ pp}$ ($p < 0.05$) [PRODUCT ASSUMPTION]; deprioritize if statistically inconclusive.

---

## 📊 Key Verified Metrics & Data Provenance

| Dimension | Metric | Provenance | Product Context |
| :--- | :---: | :---: | :--- |
| **Marketplace Scale** | 32,245 searches / 31,328 sessions | `[OBSERVED]` | 60-day historical fashion dataset |
| **Search Conversion Leverage** | 11.92% vs. 4.75% session conversion | `[OBSERVED]` | Search-engaged shoppers convert 2.51x higher |
| **4+ Token Query Share** | 33.85% (10,914 searches) | `[OBSERVED]` | High-intent long-tail traffic cohort |
| **Historical 4+ Token ZRR** | **8.23%** (vs. 1.78% on 1–3 tokens) | `[OBSERVED]` | Discovery breakdown on specific queries |
| **Manual Reformulation Rate** | **44.39%** on 4+ token queries | `[OBSERVED]` | Customer friction & vocabulary struggle |
| **Eligible Discovery Failure** | **941 searches** (~15.7/day) | `[OBSERVED]` | $\ge 4$ tokens AND $< 3$ strict results |
| **Baseline Search $	o$ PDP CTR** | **3.08%** (29 clicks / 941 searches) | `[OBSERVED]` | Primary baseline conversion metric |
| **Benchmark Recovery Rate** | **91.81%** (807 / 879 recovered) | `[LOCAL BENCHMARK]` | Algorithmic fallback efficacy |
| **Relaxation Latency (P95)** | **38.53 ms** | `[LOCAL BENCHMARK]` | Sub-50ms relaxation budget |
| **Simulated Experiment Lift** | **+3.23 pp** ($p = 0.0141$) | `[SIMULATED]` | Offline A/B target scenario simulation |
| **Annualized Gross GMV Impact** | **+$1,808.69 / year** | `[MODELED]` | Modeled at +3.5 pp CTR lift |
| **Annualized Net GMV Impact** | **+$1,356.52 / year** | `[MODELED]` | Adjusted for 25% cannibalization |
| **Illustrative 100x Scale GMV** | **+$180,869 / year** | `[MODELED]` | Scale potential with $0 marginal cloud cost |
| **Pre-Declared Ship Threshold**| **$\ge +1.5	ext{ pp}$ CTR ($p < 0.05$)** | `[PRODUCT ASSUMPTION]`| Canary go/no-go shipment criterion |

*All project metrics carry strict provenance labels: `[OBSERVED]` (historical data), `[LOCAL BENCHMARK]` (catalog search engine), `[PRODUCT ASSUMPTION]` (planning inputs), `[SIMULATED]` (offline A/B generator), or `[MODELED]` (deterministic financial calculations).*

---

## 🏗️ Architecture & Latency SLA Definition

```
[ Shopper Query: "women red silk evening dress" ]
                       │
                       ▼
         ┌───────────────────────────┐
         │ Strict Search Execution   │ ──( >=3 results )──► Return Direct Matches
         └─────────────┬─────────────┘
                       │ (< 3 results & >= 4 tokens)
                       ▼
         ┌───────────────────────────┐
         │ Token Classification      │ ──► Protect Category Nouns ("dress")
         └─────────────┬─────────────┘
                       ▼
         ┌───────────────────────────┐
         │ Candidate Generation      │ ──► Generate 1-drop & 2-drop subsets
         └─────────────┬─────────────┘
                       ▼
         ┌───────────────────────────┐
         │ Scoring & Ranking         │ ──► Score by token rarity (IDF) & catalog density
         └─────────────┬─────────────┘
                       ▼
         ┌───────────────────────────┐
         │ Guardrail Verification    │ ──► Category check, stock > 0, >=50% overlap
         └─────────────┬─────────────┘
                       ▼
[ Render Explainable Fallback UI: "Showing 8 results for red dress (relaxed: silk, evening)" ]
```

### Latency SLA Standard
To eliminate cross-document ambiguity, latency is governed by two complementary standards:
1. **$\le 50	ext{ ms}$ Algorithmic Relaxation Budget**: The maximum latency budget allocated specifically to fallback candidate generation, ranking, and guardrail validation in `src/query_relaxation.py`.
2. **$\le 250	ext{ ms}$ End-to-End Search API SLA**: The proposed production Gateway SLA including HTTP network overhead, authentication, strict execution, and fallback rendering.
- **Measured Local Performance**: Strict search runs in **2.08 ms**; full relaxation fallback runs in **38.53 ms P95** [LOCAL BENCHMARK], comfortably satisfying both constraints.

---

## 🧪 Experimentation & Business Impact

### Offline A/B Simulator (Stage 6)
- **Design**: User-level deterministic hashing (`MD5(user_id) % 100`), 50/50 allocation.
- **Eligibility**: Queries with $\ge 4$ tokens and $< 3$ strict results.
- **Primary Metric**: Search $	o$ PDP Click-Through Rate (CTR).
- **Hypothesis**: Treatment (strict + relaxation fallback) increases Search $	o$ PDP CTR by $\ge +1.5	ext{ pp}$ ($p < 0.05$) [PRODUCT ASSUMPTION].
- **Sample Size / Velocity**: Power analysis for $+3.5	ext{ pp}$ MDE requires 596 searches/arm (~1,192 total), running for **~76 days** at current velocity (~15.7 eligible searches/day) [MODELED].

### Financial & Capital Discipline Model (Stage 7.1)
- **Central Scenario**: +3.5 pp CTR lift $	o$ **+$297.32 gross GMV / 60 days** $	o$ **+$1,808.69 annualized gross GMV** [MODELED].
- **Cannibalization Adjustment**: At 25% cannibalization discount, net impact is **+$1,356.52 / year** [MODELED].
- **Capital Discipline Assessment**: Dedicated search cluster infrastructure is estimated at **$28,500 Year-1 cost** [PRODUCT ASSUMPTION — ILLUSTRATIVE PLANNING INPUT]. Building dedicated infrastructure for ~$1.8K annual revenue would destroy shareholder value.
- **Strategic Recommendation**: Deploy query relaxation as a zero-marginal-cost in-memory service inside existing application compute. Validate with a live canary experiment before committing any capital.

---

## 🚀 Running the Project Locally

### 1. Run Automated Test Suite
```bash
# Run all 71 unit and integration tests
pytest tests/

# Validate DuckDB data integrity (59/59 checks)
python src/data_validation.py

# Validate PRD consistency (25/25 checks)
python src/final_prd_validation.py
```

### 2. Launch Search Health Dashboard
```bash
# Generate the dashboard JSON & HTML
python src/search_dashboard.py --html

# Open reports/search_dashboard.html in your browser
# Or launch a local server:
python -m http.server 8000 --directory reports
# Navigate to: http://localhost:8000/search_dashboard.html
```

### 3. Launch Interactive Search Debugger
```bash
# Launch the local Search Debugger web interface
python src/search_debugger_ui.py --port 8080
# Open: http://localhost:8080
```

### 4. Run Business Impact & Simulation CLIs
```bash
# Run the complete business impact analysis suite
python src/business_impact.py --all

# Run the A/B experiment simulator
python src/ab_experiment.py --simulate --days 60
```

---

## 📁 Project Structure

```
ecommerce-product-analytics/
├── data/
│   └── ecommerce_analytics.duckdb       # Validated DuckDB store (119K events, 1.6K SKUs)
├── src/                                 # Core Production & Analytical Logic
│   ├── search_engine.py                 # Deterministic local search engine & indexing
│   ├── query_relaxation.py              # Automated Query Relaxation / Soft-Match engine
│   ├── search_debugger.py               # Algorithmic search inspection & trace engine
│   ├── search_debugger_ui.py            # Web UI for search debugging & query profiling
│   ├── ab_experiment.py                 # A/B randomization, power analysis & simulator
│   ├── business_impact.py               # Financial impact model, sensitivity & break-even
│   ├── search_dashboard.py              # Single-file HTML/JSON dashboard generator
│   ├── data_validation.py               # 59 automated DuckDB data validation checks
│   └── final_prd_validation.py          # 25 automated PRD metric consistency checks
├── tests/                               # 71 Automated Unit & Integration Tests
│   ├── test_search_engine.py            # Strict search & indexing tests (11 tests)
│   ├── test_query_relaxation.py         # Relaxation algorithms & guardrail tests (15 tests)
│   ├── test_search_debugger.py          # Trace capture & UI endpoint tests (10 tests)
│   ├── test_ab_experiment.py            # Randomization, hashing & power tests (10 tests)
│   ├── test_business_impact.py          # Revenue formulas & sensitivity tests (15 tests)
│   └── test_search_dashboard.py         # Dashboard calculations & JSON tests (10 tests)
├── docs/                                # Technical & Architectural Documentation
│   ├── prd_search_discovery_mvp.md      # Comprehensive Product Requirement Document
│   ├── search_debugger_guide.md         # Guide to explainable search inspection
│   └── working_search_mvp.md            # Search engine indexing & ranking architecture
└── reports/                             # Portfolio Case Studies & Strategic Reports
    ├── final_pm_case_study.md           # ⭐ Definitive 17-Section PM Portfolio Case Study
    ├── pm_interview_cheat_sheet.md      # 🎤 PM Interview Cheat Sheet & Top 15 Q&As
    ├── search_dashboard.html            # 📊 Standalone Search Health Analytics Dashboard
    ├── search_solution_evaluation.md    # Stage 5 competitive architecture evaluation
    ├── ab_experiment_report.md          # Stage 6 A/B experiment design & power report
    └── business_impact_report.md        # Stage 7 financial model & break-even analysis
```

---

## 📌 Project Limitations

To maintain uncompromising product management credibility:
- **Synthetic Data**: Funnel events and catalog data are generated via a deterministic seed (`seed=42`) in DuckDB.
- **Local Search Engine**: Benchmarks reflect a local in-memory inverted index, not a production distributed cluster.
- **Offline Experiment Simulation**: A/B metrics evaluate simulated behavioral distributions rather than live causal traffic.
- **Static Funnel Assumptions**: Annualized GMV projections assume constant downstream conversion and linear traffic extrapolation without seasonality.

**Strategic Takeaway**: *Prioritize interventions based on root-cause fit and capital discipline. Validate customer willingness to purchase with lightweight software before investing in expensive infrastructure.*
