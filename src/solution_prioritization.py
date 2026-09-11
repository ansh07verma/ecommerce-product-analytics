"""
solution_prioritization.py - Solution Exploration & Prioritization
Generates solution scoring, experiment matrix, and Figures 16, 17, 18.
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
FIGURES_DIR = os.path.join(REPORTS_DIR, 'figures')
os.makedirs(FIGURES_DIR, exist_ok=True)

# ---------------------------------------------------------
# 1. SOLUTION BRAINSTORM & SCORING DATA
# ---------------------------------------------------------
solutions_data = [
    {
        'Solution_ID': 'SOL-01',
        'Solution_Name': 'Query Relaxation (Soft-Match Fallback)',
        'Category': 'Retrieval / Query Fallback',
        'User_Problem_Addressed': 'Zero results on over-constrained multi-token queries',
        'Mechanism': 'If strict match returns < 3 results, automatically drop least-selective modifier or relax conjunction to (N-1) tokens with clear UI indicator',
        'Expected_Impact': 'Directly eliminates 8.23% ZRR on 4+ token queries, recovering high-intent discovery drop-offs',
        'Reach': 4,
        'Impact': 4,
        'Confidence': 4,
        'Effort': 2,
        'Risk_Score': 2,
        'Qualitative_Risk': 'Low-Medium: May return lower-relevance items if key noun is dropped instead of modifier',
        'Data_Requirements': 'Search logs, token frequency dictionary, stop-words/modifier token list',
        'Evidence_Supporting': '898 zero-result events on 4+ tokens (8.23% vs 1.78%); 44.4% reformulation rate indicates user persistence',
        'Evidence_Missing': 'Exact token drop heuristics and user tolerance for partial attribute matches'
    },
    {
        'Solution_ID': 'SOL-02',
        'Solution_Name': 'Interactive Query Refinement Chips',
        'Category': 'UI / Discovery Recovery',
        'User_Problem_Addressed': 'User frustration and friction during manual query reformulation',
        'Mechanism': 'Display individual query tokens as removable pill chips ([Black x] [Cotton x] [Jeans x]) above results, enabling 1-tap relaxation',
        'Expected_Impact': 'Reduces reformulation friction, guides user to broad catalog coverage without guesswork',
        'Reach': 4,
        'Impact': 3,
        'Confidence': 4,
        'Effort': 2,
        'Risk_Score': 1,
        'Qualitative_Risk': 'Very Low: Completely transparent; user retains full control over query changes',
        'Data_Requirements': 'Client-side query token parser and URL state synchronization',
        'Evidence_Supporting': '44.39% reformulation rate on 4+ token searches proves users actively attempt manual keyword stripping',
        'Evidence_Missing': 'Percentage of users who notice and tap chips vs re-typing in search bar'
    },
    {
        'Solution_ID': 'SOL-03',
        'Solution_Name': 'Attribute-Aware Query Parsing (Facet Extraction)',
        'Category': 'Query Processing & NLU',
        'User_Problem_Addressed': 'Semantic mismatch between raw text query and structured catalog fields',
        'Mechanism': 'Parse queries using dictionary/regex entity extraction into category, brand, color, gender, and size filters',
        'Expected_Impact': 'Transforms fuzzy text matching into high-precision faceted filtering, eliminating multi-token retrieval noise',
        'Reach': 4,
        'Impact': 5,
        'Confidence': 3,
        'Effort': 3,
        'Risk_Score': 3,
        'Qualitative_Risk': 'Medium: Token misclassification (e.g. "orange" fruit color vs brand) filters out valid products',
        'Data_Requirements': 'Product catalog attribute dictionary, entity mapping tables, synonym taxonomies',
        'Evidence_Supporting': 'Query length exploratory analysis shows 4+ token queries combine category + color + style tokens',
        'Evidence_Missing': 'Distribution of attribute types across all search tokens in query logs'
    },
    {
        'Solution_ID': 'SOL-04',
        'Solution_Name': 'Attribute-Token Matching & Field Weighting',
        'Category': 'Retrieval & Ranking',
        'User_Problem_Addressed': 'Sub-optimal keyword relevance scoring across title, description, and tags',
        'Mechanism': 'Tune search engine BM25 field weights to heavily boost category/product_name matches over descriptions, with partial token scoring',
        'Expected_Impact': 'Surfaces partial-match items higher in results rather than dropping them entirely',
        'Reach': 4,
        'Impact': 4,
        'Confidence': 3,
        'Effort': 3,
        'Risk_Score': 2,
        'Qualitative_Risk': 'Low-Medium: Re-weighting could inadvertently regress 1-3 token head query rankings',
        'Data_Requirements': 'Search index schema config, query evaluation benchmark set',
        'Evidence_Supporting': 'Lower CTR on 4+ token queries (62.97% vs 70.77%) indicates ranked results are less appealing',
        'Evidence_Missing': 'Full relevance grade judgments on current search result positions 1-10'
    },
    {
        'Solution_ID': 'SOL-05',
        'Solution_Name': 'Fallback Recommendations on Zero-Results',
        'Category': 'Discovery Recovery',
        'User_Problem_Addressed': 'Immediate session abandonment upon encountering empty zero-result state',
        'Mechanism': 'Display trending / top-seller carousel in inferred category or popular marketplace items when query returns 0 hits',
        'Expected_Impact': 'Provides an immediate escape hatch to keep users in the discovery funnel rather than bouncing',
        'Reach': 2,
        'Impact': 2,
        'Confidence': 4,
        'Effort': 1,
        'Risk_Score': 1,
        'Qualitative_Risk': 'Very Low: Any visual catalog display is superior to an empty blank page',
        'Data_Requirements': 'Category top-seller ranking cache, client fallback widget',
        'Evidence_Supporting': '898 zero-result sessions suffer lower overall session conversion (13.01% vs 14.85% baseline)',
        'Evidence_Missing': 'CTR on unrequested category recommendations vs abandonment'
    },
    {
        'Solution_ID': 'SOL-06',
        'Solution_Name': 'Related-Query Suggestions ("People also searched")',
        'Category': 'UI / Query Assistance',
        'User_Problem_Addressed': 'User does not know how to successfully rephrase an over-constrained query',
        'Mechanism': 'Mine search session co-occurrence logs to suggest successful 2-3 token queries related to current search',
        'Expected_Impact': 'Guides users toward known high-recall query formulations',
        'Reach': 3,
        'Impact': 3,
        'Confidence': 3,
        'Effort': 3,
        'Risk_Score': 2,
        'Qualitative_Risk': 'Low: Suggestions may be irrelevant or outdated if query volume is low',
        'Data_Requirements': 'Session query transition logs, query-to-query graph mining pipeline',
        'Evidence_Supporting': 'High reformulation rate (44.39%) demonstrates user willingness to try alternate queries',
        'Evidence_Missing': 'Coverage of query graph on long-tail specific queries'
    },
    {
        'Solution_ID': 'SOL-07',
        'Solution_Name': 'Synonym & Spelling Normalization',
        'Category': 'Query Processing',
        'User_Problem_Addressed': 'Vocabulary mismatch (e.g. "sneakers" vs "running shoes") and spelling typos',
        'Mechanism': 'Apply domain-specific fashion synonym expansion and Levenshtein edit-distance typo correction prior to search',
        'Expected_Impact': 'Recovers misspellings and regional terminology differences',
        'Reach': 2,
        'Impact': 2,
        'Confidence': 4,
        'Effort': 2,
        'Risk_Score': 2,
        'Qualitative_Risk': 'Low-Medium: False synonym expansion (e.g. expanding "tank top" to "crop top") dilutes precision',
        'Data_Requirements': 'Fashion synonym dictionary, spellcheck corpus',
        'Evidence_Supporting': 'Industry baseline search hygiene practice',
        'Evidence_Missing': 'Typo frequency in the specific 10,914 4+ token queries (evidence suggests specific attributes, not typos, cause failure)'
    },
    {
        'Solution_ID': 'SOL-08',
        'Solution_Name': 'Semantic Vector Search (Neural Retrieval)',
        'Category': 'Retrieval / Dense ML',
        'User_Problem_Addressed': 'Lack of conceptual understanding of multi-word queries',
        'Mechanism': 'Embed queries and catalog products into shared vector space using fine-tuned transformer model with approximate nearest neighbor (ANN) retrieval',
        'Expected_Impact': 'Captures complex semantic intent and stylistic descriptions beyond exact keyword tokens',
        'Reach': 4,
        'Impact': 5,
        'Confidence': 2,
        'Effort': 5,
        'Risk_Score': 4,
        'Qualitative_Risk': 'High: Search latency regression, unpredictable semantic hallucinations, high infrastructure & maintenance cost',
        'Data_Requirements': 'Vector database, GPU serving cluster, fine-tuned embedding model, query-click training pairs',
        'Evidence_Supporting': 'Strong literature on dense retrieval outperforming BM25 on long complex queries',
        'Evidence_Missing': 'Infrastructure capacity, latency SLA compliance, click-log training volume'
    },
    {
        'Solution_ID': 'SOL-09',
        'Solution_Name': 'Search Result Diversification',
        'Category': 'Ranking / Post-Processing',
        'User_Problem_Addressed': 'Results clustered on a single attribute variant (e.g. all one brand or color)',
        'Mechanism': 'Apply Maximal Marginal Relevance (MMR) re-ranking to diversify top 20 results across categories and brands',
        'Expected_Impact': 'Gives user broader visual options within the query bounds',
        'Reach': 3,
        'Impact': 2,
        'Confidence': 3,
        'Effort': 3,
        'Risk_Score': 2,
        'Qualitative_Risk': 'Low-Medium: May demote the single best exact match for hyper-specific queries',
        'Data_Requirements': 'Category & brand similarity matrices, re-ranking scoring engine',
        'Evidence_Supporting': 'Diversification aids exploratory browsing',
        'Evidence_Missing': 'Does not solve zero-result queries (cannot diversify 0 results)'
    },
    {
        'Solution_ID': 'SOL-10',
        'Solution_Name': 'Personalized Search Ranking',
        'Category': 'Ranking / Personalization ML',
        'User_Problem_Addressed': 'Generic result ranking failing to match individual shopper style/brand affinity',
        'Mechanism': 'Re-rank search results based on user historical category affinity, brand affinity, and price-point preference',
        'Expected_Impact': 'Increases CTR on returned items for returning high-intent users',
        'Reach': 2,
        'Impact': 3,
        'Confidence': 2,
        'Effort': 4,
        'Risk_Score': 3,
        'Qualitative_Risk': 'Medium-High: Cold start on new users (69.8% of user base); filter bubbles; zero impact on zero-result queries',
        'Data_Requirements': 'Real-time user profile store, feature pipeline, ML ranking model',
        'Evidence_Supporting': 'Returning users have higher baseline conversion (17.3% vs 14.1%)',
        'Evidence_Missing': 'Zero-result queries cannot be personalized; irrelevant to initial discovery failure'
    }
]

df_solutions = pd.DataFrame(solutions_data)
# Formula: Solution Score = Impact * Reach * Confidence / Effort
df_solutions['Solution_Score'] = (df_solutions['Impact'] * df_solutions['Reach'] * df_solutions['Confidence']) / df_solutions['Effort']
df_solutions = df_solutions.sort_values(by=['Solution_Score', 'Impact', 'Confidence'], ascending=[False, False, False]).reset_index(drop=True)
df_solutions['Rank'] = range(1, len(df_solutions) + 1)

# Save solution prioritization CSV
sol_csv_path = os.path.join(REPORTS_DIR, 'solution_prioritization.csv')
df_solutions.to_csv(sol_csv_path, index=False)
print(f'Saved {sol_csv_path}')

# ---------------------------------------------------------
# 2. EXPERIMENT MATRIX DATA
# ---------------------------------------------------------
experiments_data = [
    {
        'Rank': 1,
        'Experiment_ID': 'EXP-01',
        'Experiment_Name': 'Automated Soft Query Relaxation on Zero/Low Results (MVP)',
        'Hypothesis': 'Automatically relaxing over-constrained 4+ token queries when strict results < 3 will eliminate zero-result dead-ends, increasing Search-to-PDP CTR and search-to-order conversion without increasing bounce rate.',
        'Control': 'Status quo: Strict keyword matching. If 0 items match all tokens, return empty state.',
        'Treatment': 'If results < 3 on 4+ token query, automatically drop least-selective modifier or relax conjunction to (N-1) tokens. Display banner: "We could not find exact matches for all terms; showing best matches for [Relaxed Query]".',
        'Primary_Metric': 'Search-to-PDP CTR on 4+ token queries (Eligible sessions)',
        'Secondary_Metrics': 'Zero-Result Rate (ZRR) on 4+ tokens, Search-to-Cart Rate, Search-to-Order Conversion, Query Reformulation Rate',
        'Guardrail_Metrics': 'Search Latency (p95 < 250ms), Bounce Rate (< 40%), Irrelevant Click Demotion (PDP view duration < 5s rate), Overall Marketplace Conversion',
        'Risk': 'Low-Medium: Relevancy noise if key product noun is dropped',
        'Effort': 'Low-Medium (2-3 weeks engineering: backend retrieval fallback + frontend banner)'
    },
    {
        'Rank': 2,
        'Experiment_ID': 'EXP-02',
        'Experiment_Name': 'Interactive Query Refinement Chips (User-Guided Relaxation)',
        'Hypothesis': 'Exposing query tokens as interactive tappable removal chips ([Black x] [Cotton x] [Casual x] [Shirt x]) empowers shoppers to self-correct over-constrained queries with 1 tap, reducing reformulation abandonment.',
        'Control': 'Standard search bar with raw text string. User must manually clear and re-type keywords.',
        'Treatment': 'Display individual parsed tokens as dismissible pill chips immediately above search results. Tapping (x) removes the token and instantly refreshes results.',
        'Primary_Metric': 'Search-to-PDP CTR on 4+ token queries',
        'Secondary_Metrics': 'Chip Engagement Rate (% sessions tapping at least 1 chip), Reformulation Friction (time to next PDP click), Session Conversion Rate',
        'Guardrail_Metrics': 'Search page dwell time, Total queries per session, Unintended chip click rate',
        'Risk': 'Low: Zero algorithmic risk; completely user-controlled',
        'Effort': 'Low-Medium (2 weeks frontend engineering + search state binding)'
    },
    {
        'Rank': 3,
        'Experiment_ID': 'EXP-03',
        'Experiment_Name': 'Attribute-Aware Faceted Query Parsing vs Free-Text',
        'Hypothesis': 'Parsing multi-token queries into structured catalog filters (Color, Category, Brand, Gender) produces higher-relevance result sets than unstructured full-text keyword matching, increasing discovery-to-cart conversion.',
        'Control': 'Raw keyword matching across product text fields.',
        'Treatment': 'Query parser detects entity tokens and applies them as faceted database filters with relaxed text match on residual terms.',
        'Primary_Metric': 'Search-to-Cart Conversion Rate on multi-attribute queries',
        'Secondary_Metrics': 'Search-to-PDP CTR, Add-to-Cart per Search, Average Order Value (AOV)',
        'Guardrail_Metrics': 'Parsing Latency (< 50ms overhead), Entity Misclassification Rate, Catalog sync lag',
        'Risk': 'Medium: Entity misclassification (false filter application) could hide relevant products',
        'Effort': 'Medium-High (4-6 weeks engineering: entity dictionary, classifier, query router)'
    },
    {
        'Rank': 4,
        'Experiment_ID': 'EXP-04',
        'Experiment_Name': 'Zero-Result Category Fallback Recommendations',
        'Hypothesis': 'Presenting top-selling items in the closest inferred category when zero results occur preserves session momentum and reduces immediate site abandonment.',
        'Control': 'Generic "No results found" message with search tips.',
        'Treatment': 'On zero results, display: "No exact matches found. Check out popular items in [Inferred Category]:" followed by an 8-item top-seller carousel.',
        'Primary_Metric': 'Post-Zero-Result Session Continuation Rate (Non-bounce rate)',
        'Secondary_Metrics': 'Fallback Carousel CTR, Downstream Session Conversion Rate',
        'Guardrail_Metrics': 'Search bounce rate, Negative feedback clicks',
        'Risk': 'Low: Zero risk of regressing existing results since current state is 0 hits',
        'Effort': 'Low (1-2 weeks engineering: recommendation widget integration)'
    }
]

df_experiments = pd.DataFrame(experiments_data)
exp_csv_path = os.path.join(REPORTS_DIR, 'experiment_matrix.csv')
df_experiments.to_csv(exp_csv_path, index=False)
print(f'Saved {exp_csv_path}')

# ---------------------------------------------------------
# 3. FIGURE 16: SOLUTION PRIORITIZATION
# ---------------------------------------------------------
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# Subplot 1: Ranked Solution Scores
colors = ['#1a5276' if r <= 3 else '#7fb3d5' if r <= 5 else '#bdc3c7' for r in df_solutions['Rank']]
bars = ax1.barh(df_solutions['Solution_Name'][::-1], df_solutions['Solution_Score'][::-1], color=colors[::-1], edgecolor='#2c3e50', linewidth=0.8)
ax1.set_xlabel('Solution Score = (Impact ? Reach ? Confidence) / Effort', fontsize=11, fontweight='bold', labelpad=10)
ax1.set_title('Ranked Solution Prioritization Scores\n(Top 3 Highlighted in Navy)', fontsize=13, fontweight='bold', pad=15)
for bar in bars:
    w = bar.get_width()
    ax1.text(w + 0.5, bar.get_y() + bar.get_height()/2, f'{w:.1f}', va='center', ha='left', fontsize=10, fontweight='bold', color='#2c3e50')
ax1.set_xlim(0, 36)
ax1.grid(axis='x', linestyle='--', alpha=0.7)

# Subplot 2: Impact vs Effort Quadrant
ax2.axvline(2.5, color='#95a5a6', linestyle='--', linewidth=1.2, alpha=0.8)
ax2.axhline(3.0, color='#95a5a6', linestyle='--', linewidth=1.2, alpha=0.8)

# Quadrant labels
ax2.text(1.2, 4.7, 'HIGH IMPACT / LOW EFFORT\n? PRIORITY SWEET SPOT ?', fontsize=10, fontweight='bold', color='#27ae60', alpha=0.9)
ax2.text(3.7, 4.7, 'HIGH IMPACT / HIGH EFFORT\nStrategic Long-Term Bets', fontsize=10, fontweight='bold', color='#2980b9', alpha=0.9)
ax2.text(1.2, 1.3, 'LOW IMPACT / LOW EFFORT\nQuick Fillers / Low Priority', fontsize=10, fontweight='bold', color='#7f8c8d', alpha=0.9)
ax2.text(3.7, 1.3, 'LOW IMPACT / HIGH EFFORT\nAvoid / Money Pit', fontsize=10, fontweight='bold', color='#c0392b', alpha=0.9)

for _, row in df_solutions.iterrows():
    color = '#27ae60' if row['Rank'] == 1 else '#2980b9' if row['Rank'] in [2, 3] else '#7f8c8d'
    size = row['Reach'] * 90
    ax2.scatter(row['Effort'], row['Impact'], s=size, color=color, alpha=0.75, edgecolors='black', linewidth=1.2, zorder=4)
    offset_y = 0.12 if row['Rank'] % 2 == 0 else -0.15
    offset_x = 0.05
    label = f"{row['Solution_ID']} (Rank {row['Rank']})"
    ax2.annotate(label, (row['Effort'] + offset_x, row['Impact'] + offset_y), fontsize=9, fontweight='bold', color='#2c3e50', zorder=5)

ax2.set_xlabel('Engineering Effort (1 = Minimal, 5 = High)', fontsize=11, fontweight='bold', labelpad=10)
ax2.set_ylabel('Expected Impact (1 = Minor, 5 = Transformative)', fontsize=11, fontweight='bold', labelpad=10)
ax2.set_title('Solution Value Matrix: Impact vs. Effort\n(Bubble size = Reach; Green = Selected MVP)', fontsize=13, fontweight='bold', pad=15)
ax2.set_xlim(0.8, 5.2)
ax2.set_ylim(0.8, 5.2)
ax2.set_xticks([1, 2, 3, 4, 5])
ax2.set_yticks([1, 2, 3, 4, 5])

plt.tight_layout()
fig16_path = os.path.join(FIGURES_DIR, '16_solution_prioritization.png')
plt.savefig(fig16_path, dpi=200, bbox_inches='tight')
plt.close()
print(f'Saved {fig16_path}')

# ---------------------------------------------------------
# 4. FIGURE 17: EXPERIMENT METRIC TREE
# ---------------------------------------------------------
fig, ax = plt.subplots(figsize=(16, 9), facecolor='#fdfefe')
ax.axis('off')

levels = [
    {
        'title': '1. BUSINESS GOAL',
        'box_color': '#1b2631',
        'text_color': 'white',
        'y': 0.88,
        'boxes': [
            {'text': 'MAXIMIZE MARKETPLACE GMV & PURCHASE CONVERSION\nRecover lost transactions from high-intent search abandonment (Baseline GMV: $217.9k)', 'x': 0.5, 'w': 0.65}
        ]
    },
    {
        'title': '2. USER OUTCOME (JTBD)',
        'box_color': '#21618c',
        'text_color': 'white',
        'y': 0.70,
        'boxes': [
            {'text': 'SEAMLESS DISCOVERY FOR SPECIFIC SHOPPERS\n"When I describe what I want using multiple attributes, search understands my intent and shows relevant products"', 'x': 0.5, 'w': 0.72}
        ]
    },
    {
        'title': '3. PRIMARY PRODUCT METRIC',
        'box_color': '#117a65',
        'text_color': 'white',
        'y': 0.52,
        'boxes': [
            {'text': 'SEARCH-TO-PDP CLICK-THROUGH RATE (CTR) ON 4+ TOKEN QUERIES\nBaseline: 62.97% | Target Direction: Statistically Significant Positive Lift', 'x': 0.5, 'w': 0.68}
        ]
    },
    {
        'title': '4. SUPPORTING METRICS (FUNNEL & BEHAVIOR)',
        'box_color': '#2e86c1',
        'text_color': 'white',
        'y': 0.32,
        'boxes': [
            {'text': 'Zero-Result Rate (ZRR)\nBaseline: 8.23% (Target: < 2.5%)', 'x': 0.16, 'w': 0.22},
            {'text': 'Search-to-Cart Rate\nBaseline Funnel Progression', 'x': 0.39, 'w': 0.21},
            {'text': 'Search-to-Order CR\nBaseline: 13.01%', 'x': 0.61, 'w': 0.21},
            {'text': 'Query Reformulation\nBaseline: 44.39% (Target: Decrease)', 'x': 0.84, 'w': 0.22}
        ]
    },
    {
        'title': '5. GUARDRAIL METRICS (SYSTEM HEALTH & TRUST)',
        'box_color': '#78281f',
        'text_color': 'white',
        'y': 0.12,
        'boxes': [
            {'text': 'Search Latency\np95 < 250ms (Zero regression)', 'x': 0.16, 'w': 0.22},
            {'text': 'Short-Query CTR\nBaseline: 70.77% (No cannibalization)', 'x': 0.39, 'w': 0.21},
            {'text': 'Bounce Rate\nImmediate exit < 40%', 'x': 0.61, 'w': 0.21},
            {'text': 'Quick-Back Rate\nPDP view < 5s (Irrelevant click check)', 'x': 0.84, 'w': 0.22}
        ]
    }
]

ax.text(0.5, 0.98, 'Success Metric Tree ? Search Discovery MVP', ha='center', va='top', fontsize=15, fontweight='bold', color='#1a252f')
ax.text(0.5, 0.95, 'Alignment from Top-Level Business Impact down to Real-Time Telemetry & System Guardrails', ha='center', va='top', fontsize=10, fontstyle='italic', color='#566573')

for i, lvl in enumerate(levels):
    ax.text(0.02, lvl['y'], lvl['title'], ha='left', va='center', fontsize=9, fontweight='bold', color=lvl['box_color'])
    for b in lvl['boxes']:
        box_w = b['w']
        box_h = 0.09
        rect = patches.FancyBboxPatch(
            (b['x'] - box_w/2, lvl['y'] - box_h/2), box_w, box_h,
            boxstyle='round,pad=0.015,rounding_size=0.015',
            facecolor=lvl['box_color'], edgecolor='#1a252f', linewidth=1.2, zorder=3
        )
        ax.add_patch(rect)
        ax.text(b['x'], lvl['y'], b['text'], ha='center', va='center', fontsize=8.5, fontweight='bold', color=lvl['text_color'], zorder=4)

arrow_props = dict(arrowstyle='->', color='#2c3e50', lw=1.8, mutation_scale=15)
ax.annotate('', xy=(0.5, 0.75), xytext=(0.5, 0.83), arrowprops=arrow_props)
ax.annotate('', xy=(0.5, 0.57), xytext=(0.5, 0.65), arrowprops=arrow_props)

for dest_x in [0.16, 0.39, 0.61, 0.84]:
    ax.annotate('', xy=(dest_x, 0.37), xytext=(0.5, 0.47), arrowprops=dict(arrowstyle='->', color='#2980b9', lw=1.3, linestyle='--'))
    ax.annotate('', xy=(dest_x, 0.17), xytext=(dest_x, 0.27), arrowprops=dict(arrowstyle='->', color='#922b21', lw=1.3))

plt.tight_layout()
fig17_path = os.path.join(FIGURES_DIR, '17_experiment_metric_tree.png')
plt.savefig(fig17_path, dpi=200, bbox_inches='tight')
plt.close()
print(f'Saved {fig17_path}')

# ---------------------------------------------------------
# 5. FIGURE 18: USER JOURNEY BEFORE VS AFTER
# ---------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 8), facecolor='#fcfcfc')
ax1.axis('off')
ax2.axis('off')

def draw_flow_step(ax, x, y, title, subtitle, box_color, border_color='#2c3e50', w=0.15, h=0.55):
    rect = patches.FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle='round,pad=0.02,rounding_size=0.03',
        facecolor=box_color, edgecolor=border_color, linewidth=1.5, zorder=3
    )
    ax.add_patch(rect)
    ax.text(x, y + 0.08, title, ha='center', va='center', fontsize=9.5, fontweight='bold', color='#1a252f', zorder=4)
    ax.text(x, y - 0.10, subtitle, ha='center', va='center', fontsize=7.5, color='#34495e', zorder=4, multialignment='center')

# BEFORE JOURNEY
ax1.text(0.01, 0.5, 'BEFORE\n(Status Quo)', ha='left', va='center', fontsize=12, fontweight='bold', color='#c0392b')
before_steps = [
    {'x': 0.12, 'title': '1. Search Query', 'sub': 'Shopper enters 4+ tokens\ne.g. "men black slim cotton shirt"\n[High Intent]', 'color': '#ebedef'},
    {'x': 0.30, 'title': '2. Rigid Retrieval', 'sub': 'Strict conjunct match across fields\nRequires all tokens present\n[Rigid System]', 'color': '#fadbd8'},
    {'x': 0.48, 'title': '3. Discovery Failure', 'sub': '8.23% Zero Results (898 events)\nPoor / sparse result catalog\n62.97% CTR (vs 70.77% short)', 'color': '#f5b7b1'},
    {'x': 0.68, 'title': '4. Friction Cycle', 'sub': '44.39% Reformulation rate\nFrustrated manual re-typing\nHigh cognitive load', 'color': '#edbb99'},
    {'x': 0.88, 'title': '5. Abandonment', 'sub': 'Discovery bounce / drop-off\nLost session conversion (13.0%)\nUnrealized GMV', 'color': '#f1948a'}
]

for s in before_steps:
    draw_flow_step(ax1, s['x'], 0.5, s['title'], s['sub'], s['color'])

for i in range(len(before_steps) - 1):
    x_start = before_steps[i]['x'] + 0.08
    x_end = before_steps[i+1]['x'] - 0.08
    ax1.annotate('', xy=(x_end, 0.5), xytext=(x_start, 0.5), arrowprops=dict(arrowstyle='->', color='#c0392b', lw=2))

# AFTER JOURNEY
ax2.text(0.01, 0.5, 'AFTER\n(MVP Solution)', ha='left', va='center', fontsize=12, fontweight='bold', color='#1e8449')
after_steps = [
    {'x': 0.12, 'title': '1. Search Query', 'sub': 'Shopper enters 4+ tokens\ne.g. "men black slim cotton shirt"\n[High Intent]', 'color': '#ebedef'},
    {'x': 0.30, 'title': '2. Intent Fallback', 'sub': 'If strict match < 3 hits:\nDrop least-selective modifier\nor soft-relax conjunction', 'color': '#d4efdf'},
    {'x': 0.48, 'title': '3. Curated Results', 'sub': 'Relevant purchasable products\nClear UI context banner\nZRR drops toward zero', 'color': '#a9dfbf'},
    {'x': 0.68, 'title': '4. PDP Engagement', 'sub': 'Higher Click-Through Rate\nShopper explores matched items\nSmooth journey to cart', 'color': '#7dcea0'},
    {'x': 0.88, 'title': '5. Conversion', 'sub': 'Add to Cart ? Checkout\nTarget: Uplift in session CR\nCaptured GMV & trust', 'color': '#52be80'}
]

for s in after_steps:
    draw_flow_step(ax2, s['x'], 0.5, s['title'], s['sub'], s['color'])

for i in range(len(after_steps) - 1):
    x_start = after_steps[i]['x'] + 0.08
    x_end = after_steps[i+1]['x'] - 0.08
    ax2.annotate('', xy=(x_end, 0.5), xytext=(x_start, 0.5), arrowprops=dict(arrowstyle='->', color='#1e8449', lw=2))

ax1.set_xlim(0, 1)
ax1.set_ylim(0, 1)
ax2.set_xlim(0, 1)
ax2.set_ylim(0, 1)

plt.tight_layout()
fig18_path = os.path.join(FIGURES_DIR, '18_user_journey_before_after.png')
plt.savefig(fig18_path, dpi=200, bbox_inches='tight')
plt.close()
print(f'Saved {fig18_path}')
print('All solution exploration processing complete!')