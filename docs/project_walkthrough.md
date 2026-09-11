# 3?5 Minute Verbal Project Walkthrough

**Project:** E-Commerce Product Analytics ? Search & Conversion Funnel  
**Target Audience:** Recruiter / Hiring Manager / Senior PM Interviewer  
**Pacing:** ~130 words per minute (Total time: ~4 minutes)  

---

### 1. Opening ? The Hook (20 Seconds)
"Hi! Today I?m excited to share an e-commerce product analytics case study I built, examining search and conversion funnel friction across 31,000 user sessions. My goal was to move systematically from diagnostic data analysis to root-cause hypotheses, prioritize the highest-leverage opportunity, and design an experimentally testable search-recovery MVP."

---

### 2. The Problem ? What Was Going Wrong (30 Seconds)
"In our fashion marketplace, search is the primary high-intent channel: search-engaged shoppers convert at **11.9% compared to under 5% for browse shoppers**?a 2.5x advantage. 

However, when I segmented search performance by query length, I discovered a major breakdown: shoppers formulating highly specific, multi-attribute queries (like *'men black slim cotton shirt'*) were experiencing an alarming **8.2% zero-result rate**?nearly five times worse than short queries?and their click-through engagement dropped by almost 8 percentage points."

---

### 3. The Analysis ? Most Important Evidence (60 Seconds)
"To understand why this was happening, I queried our transaction and event database in DuckDB:
- First, this wasn't an edge case. Specific queries with 4 or more tokens represented **over 33% of all search traffic**?touching nearly 9,000 sessions and over 7,300 active users.
- Second, when these shoppers hit zero results, they didn't just give up immediately; **over 44% repeatedly re-typed queries in frustration**, trying to guess the catalog's exact vocabulary.
- Third, when analyzing query eligibility?defined as 4+ tokens with fewer than 3 results?I found **941 searches where discovery completely collapsed**, generating a dismal **3.08% CTR**.
- Finally, comparing funnel leaks using a RICE framework, Search Discovery Failure scored 64.0, easily outranking Mobile Web checkout friction, size stockouts, and shipping fee cliffs because upstream discovery gains compound through the entire funnel."

---

### 4. The Product Decision ? What I Chose & Why (45 Seconds)
"I defined our core Job to Be Done as: *'When I know roughly what product I want and describe it using multiple attributes, I want search to understand my intent and show relevant purchasable products so I can quickly buy.'*

After brainstorming and scoring 10 potential solutions, I rejected complex neural vector search for the MVP because of latency SLA risks and heavy infrastructure costs. Instead, I selected **Automated Query Relaxation and Soft-Match Fallback** as our MVP because it directly targets the 898 observed zero-result events with lean engineering effort and zero ML dependencies."

---

### 5. The MVP ? How It Works (45 Seconds)
"Here?s how the MVP works:
When a shopper enters a specific query with 4 or more tokens and primary retrieval returns fewer than 3 products, the gateway intercepts the request. 

It looks up the tokens in our catalog lexicon, **strictly preserves the primary product category noun**?like 'shirt' or 'dress'?identifies the least-selective modifier based on catalog document frequency, and executes a controlled fallback query on the remaining terms. 

If partial matches pass a minimum relevance threshold, we surface up to 20 products with a transparent notification banner: *'Showing closest matches for men black cotton shirt with slim removed,'* complete with a 1-tap link to force strict search."

---

### 6. The Experiment ? How I Would Validate It (45 Seconds)
"To validate this rigorously, I designed **EXP-01**: a controlled A/B test. 

We randomize users 50/50 at the persistent user level, but evaluate on our eligible low-result cohort where baseline CTR is **3.08%**. 

Our statistical power analysis shows that detecting a $+3.5	ext{ pp}$ lift requires ~1,000 eligible searches, representing about 9 weeks at current catalog traffic. In an initial 4-week test, we're powered to detect transformational lifts ($\ge +5.0	ext{ pp}$), while monitoring five critical guardrails: p95 search latency strictly under 250 ms, head-query CTR neutrality, and quick-back bounce rates within 1 percentage point."

---

### 7. Closing ? Expected Outcome & Next Evolution (20 Seconds)
"By recovering lost discovery for high-intent shoppers, this MVP captures unrealized GMV at zero customer acquisition cost. Once validated, the telemetry collected fuels our Phase 2 roadmap: interactive query refinement chips and structured attribute parsing. 

I?d be glad to dive into the SQL analysis, experiment trade-offs, or PRD specifications!"
