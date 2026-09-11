"""
Interactive Local Web Dashboard for Explainable Search Debugger.
Provides a modern, lightweight single-page application and REST API
using standard Python libraries (zero external web dependencies).

Run with:
    python src/search_debugger_ui.py --port 8080
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.search_debugger import DEMO_QUERIES, SearchDebugger, SearchDebugResult

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search Discovery & Relaxation Debugger</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #090d16;
            --bg-secondary: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-blue: #38bdf8;
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --accent-purple: #a855f7;
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: var(--font-sans);
            line-height: 1.5;
            padding: 24px 32px 64px 32px;
        }

        .container {
            max-width: 1280px;
            margin: 0 auto;
        }

        /* Header */
        header {
            margin-bottom: 24px;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }
        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .badge-logo {
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
            color: #04131f;
            font-weight: 800;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 14px;
            letter-spacing: 0.05em;
        }
        h1 {
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.02em;
        }
        .subtitle {
            color: var(--text-secondary);
            font-size: 13px;
        }

        /* Mode Switcher */
        .mode-toggle {
            display: flex;
            background: var(--bg-secondary);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 4px;
            gap: 4px;
        }
        .mode-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .mode-btn.active {
            background: var(--card-bg);
            color: var(--accent-blue);
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }

        /* Search Bar & Demo Chips */
        .search-section {
            background: var(--bg-secondary);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 28px;
        }
        .search-form {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
        }
        .search-input {
            flex: 1;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            color: var(--text-primary);
            font-family: var(--font-sans);
            font-size: 15px;
            padding: 12px 16px;
            outline: none;
            transition: border-color 0.2s;
        }
        .search-input:focus {
            border-color: var(--accent-blue);
        }
        .btn-submit {
            background: linear-gradient(135deg, #0284c7, #0369a1);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0 24px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        .btn-submit:hover {
            background: #0284c7;
        }

        .demo-chips-label {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 8px;
        }
        .demo-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .chip {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            color: var(--text-secondary);
            font-size: 12px;
            padding: 5px 12px;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .chip:hover {
            border-color: var(--accent-blue);
            color: var(--text-primary);
        }
        .chip-tag {
            font-size: 10px;
            padding: 1px 6px;
            border-radius: 10px;
            font-weight: 700;
        }
        .tag-green { background: rgba(16, 185, 129, 0.2); color: #34d399; }
        .tag-blue { background: rgba(56, 189, 248, 0.2); color: #7dd3fc; }
        .tag-amber { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
        .tag-rose { background: rgba(244, 63, 94, 0.2); color: #fda4af; }

        /* Status & KPI Cards */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .kpi-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 16px;
        }
        .kpi-label {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 4px;
        }
        .kpi-value {
            font-size: 22px;
            font-weight: 700;
        }
        .kpi-sub {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        /* Status Badges */
        .status-badge {
            display: inline-block;
            font-size: 12px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            letter-spacing: 0.04em;
        }
        .status-RELAXED_RECOVERED { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .status-NORMAL { background: rgba(56, 189, 248, 0.2); color: #7dd3fc; border: 1px solid rgba(56, 189, 248, 0.3); }
        .status-LOW_RESULTS_NO_RELAXATION { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
        .status-NO_SAFE_RELAXATION { background: rgba(244, 63, 94, 0.2); color: #fda4af; border: 1px solid rgba(244, 63, 94, 0.3); }

        /* Content Sections */
        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            padding-bottom: 12px;
        }
        .card-title {
            font-size: 16px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .card-subtitle {
            font-size: 12px;
            color: var(--text-muted);
        }

        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        th {
            text-align: left;
            padding: 10px 12px;
            color: var(--text-muted);
            font-weight: 600;
            border-bottom: 1px solid var(--card-border);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.04);
        }
        tr:hover td {
            background: rgba(255,255,255,0.02);
        }
        .font-mono { font-family: var(--font-mono); }

        /* Role Pills */
        .role-pill {
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            display: inline-block;
        }
        .role-CORE_CATEGORY { background: rgba(168, 85, 247, 0.2); color: #d8b4fe; border: 1px solid rgba(168, 85, 247, 0.4); }
        .role-BRAND { background: rgba(56, 189, 248, 0.2); color: #7dd3fc; border: 1px solid rgba(56, 189, 248, 0.4); }
        .role-MODIFIER { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
        .role-MISSING_CATALOG_TERM { background: rgba(244, 63, 94, 0.2); color: #fda4af; border: 1px solid rgba(244, 63, 94, 0.4); }

        /* Guardrails Grid */
        .guardrails-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 12px;
        }
        .guardrail-item {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 12px 14px;
            border-radius: 8px;
            font-size: 13px;
        }
        .check-icon {
            font-weight: 800;
            font-size: 14px;
            line-height: 1;
        }
        .pass-icon { color: var(--accent-green); }
        .warn-icon { color: var(--accent-amber); }

        /* PM Narrative Callout */
        .pm-narrative-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 16px;
        }
        .pm-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 16px;
        }
        .pm-card-label {
            font-size: 11px;
            font-weight: 700;
            color: var(--accent-blue);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 6px;
        }
        .pm-card-text {
            font-size: 14px;
            color: var(--text-primary);
        }

        /* Products Grid */
        .products-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 16px;
        }
        .product-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .product-brand {
            font-size: 11px;
            font-weight: 700;
            color: var(--accent-cyan);
            text-transform: uppercase;
            margin-bottom: 2px;
        }
        .product-title {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--text-primary);
        }
        .product-meta {
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 12px;
        }
        .product-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid rgba(255,255,255,0.06);
            padding-top: 10px;
        }
        .product-price {
            font-size: 15px;
            font-weight: 700;
            color: var(--text-primary);
        }
        .product-score {
            font-size: 11px;
            font-family: var(--font-mono);
            color: var(--text-muted);
        }

        .hidden { display: none !important; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <div>
                <div class="header-title">
                    <span class="badge-logo">SEARCH DISCOVERY</span>
                    <h1>Explainable Search Debugger</h1>
                </div>
                <div class="subtitle">Deterministic Query Relaxation & Recovery Diagnostic Console</div>
            </div>
            <div class="mode-toggle">
                <button class="mode-btn active" id="btnModeAll" onclick="setMode('all')">Complete View</button>
                <button class="mode-btn" id="btnModePM" onclick="setMode('pm')">👔 Product Manager</button>
                <button class="mode-btn" id="btnModeTech" onclick="setMode('tech')">⚙️ Technical Details</button>
            </div>
        </header>

        <!-- Search Bar & Presets -->
        <section class="search-section">
            <form class="search-form" onsubmit="event.preventDefault(); runSearch();">
                <input type="text" id="queryInput" class="search-input" placeholder="Enter multi-attribute search query (e.g. 'women floral midi dress red')..." value="women floral midi dress red" />
                <button type="submit" class="btn-submit">Inspect Query</button>
            </form>
            <div class="demo-chips-label">Quick Demo Scenarios</div>
            <div class="demo-chips">
                <div class="chip" onclick="setQuery('running shoes')">
                    <span class="chip-tag tag-blue">Broad Query</span>
                    <span>running shoes</span>
                </div>
                <div class="chip" onclick="setQuery('nike')">
                    <span class="chip-tag tag-blue">Branded</span>
                    <span>nike</span>
                </div>
                <div class="chip" onclick="setQuery('tommy hilfiger classic t-shirts')">
                    <span class="chip-tag tag-amber">Low Results</span>
                    <span>tommy hilfiger classic t-shirts</span>
                </div>
                <div class="chip" onclick="setQuery('women floral midi dress red')">
                    <span class="chip-tag tag-green">Recoverable Zero-Result</span>
                    <span>women floral midi dress red</span>
                </div>
                <div class="chip" onclick="setQuery('xyzunknown impossible brand qwerty nonexist')">
                    <span class="chip-tag tag-rose">Circuit Breaker</span>
                    <span>xyzunknown impossible brand qwerty nonexist</span>
                </div>
            </div>
        </section>

        <!-- Loading State -->
        <div id="loading" class="hidden" style="text-align:center; padding: 40px; color: var(--accent-blue);">
            Loading search diagnostics from catalog...
        </div>

        <!-- Main Diagnostics Content -->
        <main id="content">
            <!-- KPI Summary Bar -->
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-label">Recovery Health Status</div>
                    <div id="kpiStatus"><span class="status-badge status-RELAXED_RECOVERED">RELAXED_RECOVERED</span></div>
                    <div id="kpiStatusSub" class="kpi-sub">Strict 0 → Recovered 16</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Strict Matches</div>
                    <div id="kpiStrictCount" class="kpi-value">0</div>
                    <div id="kpiStrictSub" class="kpi-sub">Catalog in-stock hits</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Recovered Products</div>
                    <div id="kpiRecoveredCount" class="kpi-value" style="color:var(--accent-green)">16</div>
                    <div id="kpiRecoveredSub" class="kpi-sub">+16 net discovery lift</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Execution Latency</div>
                    <div id="kpiLatency" class="kpi-value">8.27 ms</div>
                    <div id="kpiLatencySub" class="kpi-sub">Target SLA: &le; 250 ms (PASS)</div>
                </div>
            </div>

            <!-- Product Manager Narrative Section -->
            <section id="sectionPM" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">👔 Product Manager Explanation View</div>
                        <div class="card-subtitle">Non-technical executive discovery narrative for PMs and interviewers</div>
                    </div>
                </div>
                <div class="pm-narrative-grid">
                    <div class="pm-card">
                        <div class="pm-card-label">Problem Identification</div>
                        <div id="pmProblem" class="pm-card-text">Query was over-specified with 5 terms, returning 0 products under strict matching.</div>
                    </div>
                    <div class="pm-card">
                        <div class="pm-card-label">Recovery Decision</div>
                        <div id="pmDecision" class="pm-card-text">Relaxed non-core selective modifier(s) 'midi', 'red' while preserving core category intent 'women floral dress'.</div>
                    </div>
                    <div class="pm-card">
                        <div class="pm-card-label">Customer Outcome</div>
                        <div id="pmOutcome" class="pm-card-text">Zero-result search recovered into 16 relevant in-stock products (+16 items).</div>
                    </div>
                </div>
                <div style="margin-top: 16px; background: rgba(0,0,0,0.2); border-left: 3px solid var(--accent-blue); padding: 12px 16px; border-radius: 4px;">
                    <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase; margin-bottom:2px;">Executive Narrative</div>
                    <div id="pmSummary" style="font-size:13px; color:var(--text-secondary);">Strict search returned 0 items. The system recovered 16 relevant products by removing modifier(s) 'midi', 'red' while preserving core category 'women floral dress'.</div>
                </div>
            </section>

            <!-- Technical Token Frequency & Role Analysis -->
            <section id="sectionTokens" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">⚙️ Token Catalog Frequency & Semantic Role Analysis</div>
                        <div class="card-subtitle">Per-token document frequency (DF) calculated against the 1,600-product catalog</div>
                    </div>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Query Token</th>
                            <th>Normalized Stem</th>
                            <th>Catalog DF</th>
                            <th>Semantic Role</th>
                            <th>Protected Core Category?</th>
                            <th>Eligible Modifier?</th>
                        </tr>
                    </thead>
                    <tbody id="tokenTableBody">
                        <!-- Filled by JS -->
                    </tbody>
                </table>
            </section>

            <!-- Technical Candidates Table & Guardrails -->
            <section id="sectionCandidates" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">🎯 Candidate Fallback Evaluation & Multi-Factor Scoring</div>
                        <div class="card-subtitle">Multi-tier candidate queries scored via deterministic objective function</div>
                    </div>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Candidate Fallback Query</th>
                            <th>Dropped Modifier(s)</th>
                            <th>Recovered Hits</th>
                            <th>Category Consistent</th>
                            <th>Candidate Score</th>
                            <th>Decision Status</th>
                        </tr>
                    </thead>
                    <tbody id="candidateTableBody">
                        <!-- Filled by JS -->
                    </tbody>
                </table>

                <div style="margin-top: 24px;">
                    <div class="card-title" style="font-size:14px; margin-bottom:12px;">🛡️ Active Guardrail Verification Matrix</div>
                    <div class="guardrails-list" id="guardrailsList">
                        <!-- Filled by JS -->
                    </div>
                </div>
            </section>

            <!-- Final Products Returned -->
            <section id="sectionProducts" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">🛍️ Final Search Results Returned to Customer</div>
                        <div class="card-subtitle" id="productsSubtitle">Showing top in-stock products matching final query</div>
                    </div>
                </div>
                <div class="products-grid" id="productsGrid">
                    <!-- Filled by JS -->
                </div>
            </section>
        </main>
    </div>

    <script>
        let currentMode = 'all';

        function setMode(mode) {
            currentMode = mode;
            document.getElementById('btnModeAll').classList.toggle('active', mode === 'all');
            document.getElementById('btnModePM').classList.toggle('active', mode === 'pm');
            document.getElementById('btnModeTech').classList.toggle('active', mode === 'tech');

            document.getElementById('sectionPM').classList.toggle('hidden', mode === 'tech');
            document.getElementById('sectionTokens').classList.toggle('hidden', mode === 'pm');
            document.getElementById('sectionCandidates').classList.toggle('hidden', mode === 'pm');
        }

        function setQuery(q) {
            document.getElementById('queryInput').value = q;
            runSearch();
        }

        async function runSearch() {
            const query = document.getElementById('queryInput').value.trim();
            if (!query) return;

            document.getElementById('loading').classList.remove('hidden');
            document.getElementById('content').style.opacity = '0.5';

            try {
                const res = await fetch('/api/debug?q=' + encodeURIComponent(query));
                const data = await res.json();
                renderDebugResult(data);
            } catch (err) {
                console.error(err);
                alert('Failed to fetch search debug analysis.');
            } finally {
                document.getElementById('loading').classList.add('hidden');
                document.getElementById('content').style.opacity = '1.0';
            }
        }

        function renderDebugResult(d) {
            // KPI Summary
            const status = d.final_result.status;
            document.getElementById('kpiStatus').innerHTML = `<span class="status-badge status-${status}">${status}</span>`;
            document.getElementById('kpiStatusSub').textContent = `Strict ${d.strict_search.result_count} → Recovered ${d.final_result.result_count}`;
            document.getElementById('kpiStrictCount').textContent = d.strict_search.result_count;
            document.getElementById('kpiRecoveredCount').textContent = d.final_result.result_count;
            const diff = d.final_result.result_count - d.strict_search.result_count;
            document.getElementById('kpiRecoveredSub').textContent = diff > 0 ? `+${diff} net discovery lift` : 'Zero recovery change';
            document.getElementById('kpiLatency').textContent = `${d.total_execution_time_ms.toFixed(2)} ms`;
            document.getElementById('kpiLatencySub').textContent = `Strict: ${d.strict_search.execution_time_ms.toFixed(2)}ms | Overhead: ${d.relaxation.overhead_ms.toFixed(2)}ms`;

            // PM Narrative
            document.getElementById('pmProblem').textContent = d.product_explanation.problem;
            document.getElementById('pmDecision').textContent = d.product_explanation.decision;
            document.getElementById('pmOutcome').textContent = d.product_explanation.outcome;
            document.getElementById('pmSummary').textContent = d.product_explanation.summary;

            // Token Analysis Table
            const tokenTbody = document.getElementById('tokenTableBody');
            tokenTbody.innerHTML = '';
            d.token_analysis.forEach(t => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="font-mono" style="font-weight:600">${t.token}</td>
                    <td class="font-mono" style="color:var(--text-secondary)">${t.normalized_token}</td>
                    <td class="font-mono" style="font-weight:700">${t.document_frequency}</td>
                    <td><span class="role-pill role-${t.token_role}">${t.token_role}</span></td>
                    <td style="color:${t.is_core_term ? 'var(--accent-purple)' : 'var(--text-muted)'}; font-weight:600">${t.is_core_term ? 'PROTECTED' : 'NO'}</td>
                    <td style="color:${t.is_candidate_modifier ? 'var(--accent-amber)' : 'var(--text-muted)'}; font-weight:600">${t.is_candidate_modifier ? 'YES' : 'NO'}</td>
                `;
                tokenTbody.appendChild(tr);
            });

            // Candidates Table
            const candTbody = document.getElementById('candidateTableBody');
            candTbody.innerHTML = '';
            if (d.relaxation.candidates && d.relaxation.candidates.length > 0) {
                d.relaxation.candidates.forEach(c => {
                    const isSelected = (c.fallback_query === d.relaxation.fallback_query);
                    const tr = document.createElement('tr');
                    if (isSelected) tr.style.background = 'rgba(16, 185, 129, 0.08)';
                    tr.innerHTML = `
                        <td class="font-mono" style="font-weight:${isSelected ? '700' : '500'}; color:${isSelected ? 'var(--accent-green)' : 'var(--text-primary)'}">
                            ${isSelected ? '★ ' : ''}${c.fallback_query}
                        </td>
                        <td class="font-mono" style="color:var(--text-secondary)">${c.tokens_removed.join(', ') || '(none)'}</td>
                        <td class="font-mono" style="font-weight:700">${c.result_count}</td>
                        <td>${c.category_consistency ? '<span style="color:var(--accent-green)">✓ Consistent</span>' : '<span style="color:var(--accent-rose)">✗ Drift</span>'}</td>
                        <td class="font-mono">${c.candidate_score.toFixed(2)}</td>
                        <td>
                            ${c.is_safe ? '<span style="color:var(--accent-green); font-weight:700">SELECTED</span>' : `<span style="color:var(--accent-rose); font-size:11px">${c.rejection_reason || 'REJECTED'}</span>`}
                        </td>
                    `;
                    candTbody.appendChild(tr);
                });
            } else {
                candTbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:16px;">No candidate fallback evaluation triggered for this query.</td></tr>';
            }

            // Guardrails
            const g = d.guardrails;
            const gList = document.getElementById('guardrailsList');
            gList.innerHTML = `
                <div class="guardrail-item">
                    <span class="check-icon ${g.core_category_preserved ? 'pass-icon' : 'warn-icon'}">${g.core_category_preserved ? '✓' : '✗'}</span>
                    <div><strong>Core Category Preserved</strong><div style="font-size:11px; color:var(--text-secondary)">Core product nouns protected from deletion</div></div>
                </div>
                <div class="guardrail-item">
                    <span class="check-icon pass-icon">✓</span>
                    <div><strong>In-Stock Inventory Filtered</strong><div style="font-size:11px; color:var(--text-secondary)">Strictly returns purchasable items</div></div>
                </div>
                <div class="guardrail-item">
                    <span class="check-icon ${g.minimum_token_overlap_satisfied ? 'pass-icon' : 'warn-icon'}">${g.minimum_token_overlap_satisfied ? '✓' : '✗'}</span>
                    <div><strong>Minimum Token Overlap</strong><div style="font-size:11px; color:var(--text-secondary)">At least 2 original query tokens preserved</div></div>
                </div>
                <div class="guardrail-item">
                    <span class="check-icon ${g.category_consistency_maintained ? 'pass-icon' : 'warn-icon'}">${g.category_consistency_maintained ? '✓' : '✗'}</span>
                    <div><strong>Category Consistency</strong><div style="font-size:11px; color:var(--text-secondary)">Prevents department drift</div></div>
                </div>
                ${g.circuit_breaker_activated ? `
                <div class="guardrail-item" style="border-color:var(--accent-rose)">
                    <span class="check-icon warn-icon" style="color:var(--accent-rose)">!</span>
                    <div><strong style="color:var(--accent-rose)">Circuit Breaker Activated</strong><div style="font-size:11px; color:var(--text-secondary)">Zero results returned rather than irrelevant items</div></div>
                </div>` : ''}
            `;

            // Products Grid
            const pGrid = document.getElementById('productsGrid');
            pGrid.innerHTML = '';
            document.getElementById('productsSubtitle').textContent = `Returned ${d.final_result.products.length} in-stock products matching final query`;

            if (d.final_result.products && d.final_result.products.length > 0) {
                d.final_result.products.forEach(p => {
                    const card = document.createElement('div');
                    card.className = 'product-card';
                    card.innerHTML = `
                        <div>
                            <div class="product-brand">${p.brand}</div>
                            <div class="product-title">${p.title}</div>
                            <div class="product-meta">${p.master_category} &gt; ${p.sub_category}</div>
                        </div>
                        <div class="product-footer">
                            <div class="product-price">$${p.effective_price.toFixed(2)}</div>
                            <div class="product-score">Score: ${p.relevance_score.toFixed(2)}</div>
                        </div>
                    `;
                    pGrid.appendChild(card);
                });
            } else {
                pGrid.innerHTML = '<div style="grid-column: 1 / -1; text-align:center; padding:32px; color:var(--text-muted);">No products returned for this query.</div>';
            }
        }

        // Run default search on load
        window.addEventListener('DOMContentLoaded', () => {
            runSearch();
        });
    </script>
</body>
</html>
"""


class DebuggerHTTPRequestHandler(BaseHTTPRequestHandler):
    debugger: SearchDebugger = None  # Class-level reference

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

        elif path == "/api/debug":
            query = params.get("q", ["women floral midi dress red"])[0]
            debug_res: SearchDebugResult = self.debugger.debug(query)
            payload = json.dumps(debug_res.to_dict(), indent=2).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)

        elif path == "/api/demos":
            demos_payload = json.dumps(DEMO_QUERIES).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(demos_payload)

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def log_message(self, format: str, *args: Any) -> None:
        # Keep server logs minimal
        return


def run_ui_server(port: int = 8080) -> None:
    """Starts the explainable search debugger HTTP server."""
    print(f"Initializing Search Engine & Debugger...")
    debugger = SearchDebugger()
    DebuggerHTTPRequestHandler.debugger = debugger

    server_address = ("", port)
    httpd = HTTPServer(server_address, DebuggerHTTPRequestHandler)
    print("=" * 70)
    print(f"EXPLAINABLE SEARCH DEBUGGER UI SERVER RUNNING AT:")
    print(f"http://localhost:{port}/")
    print("=" * 70)
    print("Press Ctrl+C to terminate.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Explainable Search Debugger UI Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default 8080)")
    args = parser.parse_args()

    run_ui_server(port=args.port)
