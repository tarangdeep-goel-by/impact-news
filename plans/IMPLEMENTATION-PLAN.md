# Impact News — Implementation Plan

> From research to working system. Everything we need to build, in order.

**Created**: 2026-03-10
**Status**: Ready to build

---

## What We're Building

```
Article comes in
  → LLM extracts free-form tags (what does this affect?)
  → Embeddings match tags to graph nodes
  → Check: do any matched nodes connect to this user's graph?
  → If yes: generate explanation + severity
  → Deliver via Telegram
```

**Cost: $0/month.** Runs on your Mac.

---

## Research Completed

| Research Area | File | Key Finding |
|---|---|---|
| Causal templates (56 templates, 14 domains) | `plans/MASTER-PLAN.md` | Templates are optional for MVP — LLM + graph handles it |
| Data sources catalog | Agent output (session) | GDELT (free) + RSS + Gemini free tier = $0 stack |
| Deep graph: Food + Energy | `taxonomy/food_energy_graph.yaml` | 322 nodes, 608 edges |
| Deep graph: Employment + Financial | `taxonomy/employment_domain_graph.yaml` + `financial_system_domain_graph.yaml` | 457 nodes, 646 edges |
| Deep graph: Local Governance | `taxonomy/local_governance_graph.yaml` | 330 nodes, 518 edges |
| Article → Graph matching | `research/tag-extraction-and-graph-matching-design.md` | Two-stage hybrid: LLM free-form tags → embedding match |
| User questionnaire | `research/questionnaire-design.md` | 9 questions, 31 seconds, ~65% graph coverage |
| CPI baskets + COICOP | `research/cost-of-living-taxonomy-research.md` | India CPI = 358 items, used as taxonomy backbone |

---

## The Build: 7 Steps

### Step 1: Merge & Load the Graph

**What:** Combine 4 graph YAML files into a single unified graph. Deduplicate shared anchor nodes (crude_oil, monsoon, rbi_repo_rate appear in multiple files). Load into NetworkX in-memory.

**Tasks:**
- [ ] Write merge script that reads all 4 YAML files
- [ ] Identify shared anchor nodes across files (same ID in multiple files)
- [ ] Merge edges from all files, deduplicate
- [ ] Validate: no orphan nodes, no broken edge references
- [ ] Load into NetworkX `DiGraph`
- [ ] Export merged graph as single `graph.yaml`
- [ ] Print stats: total nodes, edges, connected components, avg degree

**Output:** `graph.py` — loads the unified graph, provides lookup functions

**Expected:** ~1,100 unique nodes, ~1,700+ edges after dedup

---

### Step 2: Build the Embedding Index

**What:** Embed all node aliases into vectors for fast matching. Each node has ~4 aliases → ~4,400 vectors.

**Tasks:**
- [ ] Install `sentence-transformers`, `faiss-cpu`
- [ ] Load graph, extract all (node_id, alias) pairs
- [ ] Embed aliases using `all-MiniLM-L6-v2` (384-dim, runs locally, free)
- [ ] Build FAISS IndexFlatIP (inner product = cosine sim on normalized vectors)
- [ ] Save index + mapping to disk (reload without re-embedding)
- [ ] Test: query "oil prices rising" → should return `crude_oil`, `petrol_price`, `brent_crude`
- [ ] Test: query "RBI MPC decision" → should return `rbi_repo_rate`, `rbi_mpc`, `monetary_policy`
- [ ] Tune threshold: 0.65 auto-accept, 0.50-0.65 candidate, <0.50 reject

**Output:** `embeddings.py` — `match_tags_to_nodes(tags: list[str]) → list[NodeMatch]`

**Expected:** ~6.8MB FAISS index, <5ms per query

---

### Step 3: User Onboarding (The Questionnaire)

**What:** 9 questions that connect the user to the graph. Start with Telegram bot.

**The 9 questions (ordered by graph activation power):**

| # | Question | Format | Nodes Activated |
|---|----------|--------|-----------------|
| 1 | Which city do you live in? | Autocomplete / top 50 buttons | ~180 |
| 2 | What do you do for work? | Sector picker + free text title | ~150 |
| 3 | Own or rent? | 3 buttons: Own(loan) / Own(paid) / Rent | ~60 |
| 4 | How do you commute? | Multi-select: car/bike/metro/bus/auto/WFH | ~70 |
| 5 | Active loans? | Multi-select: home/car/education/personal/none | ~40 |
| 6 | Investments? | Multi-select: stocks/MF/FD/gold/PPF/crypto/none | ~80 |
| 7 | Dietary restrictions? | Buttons: veg/non-veg/vegan/other | ~50 |
| 8 | Family dependents? | Buttons: kids/parents/both/none | ~60 |
| 9 | Health conditions? | Multi-select: diabetes/BP/asthma/none/prefer not to say | ~40 |

**Total: ~31 seconds, ~65% graph coverage (730 of 1,110 nodes reachable)**

**Tasks:**
- [ ] Define inference rules for each answer (city → state → DISCOM → tariff)
- [ ] Write `connect_user_to_graph(answers) → list[Edge]` function
- [ ] For each answer, compute which graph nodes become user dependencies
- [ ] Store user graph as JSON: `{user_id, edges: [{node_id, relation, importance}]}`
- [ ] Precompute user reachability set: all nodes within 3 hops of user (via backward BFS)
- [ ] Build Telegram bot with inline keyboards for each question
- [ ] Conversational flow: one question per message, skip always available
- [ ] After Q9: "Got it! I'll start monitoring news that affects your life."

**Output:** `onboarding.py` + `user_graph.json` + Telegram bot flow

**Inference engine examples:**
```
City: "Bangalore" →
  - BBMP (municipal), BESCOM (electricity), BWSSB (water)
  - Karnataka state policy, Cauvery water dispute
  - Tropical climate, monsoon risk, AQI moderate
  - IT corridor, startup hub
  - Metro (BMRCL), BMTC bus

Sector: "IT/Software" + Title: "Product Manager" →
  - Tech sector, SaaS sub-sector likely
  - US economy dependency (client geography)
  - AI disruption risk: medium
  - Income band: 20-40 LPA (estimated)
  - H-1B relevance: low (if India-based)

Own (with loan) →
  - Home loan EMI, floating rate likely
  - RBI repo rate: HIGH sensitivity
  - Property tax (BBMP), stamp duty
  - RERA, real estate market
```

---

### Step 4: Article Ingestion Pipeline

**What:** Fetch articles, deduplicate, prepare for processing.

**Sources (all free):**
- GDELT via BigQuery (15-min events, 1TB/month free)
- RSS feeds: Reuters India, Economic Times, Livemint, BBC India, NDTV, The Hindu
- NewsAPI.org free tier (100 req/day for supplemental)

**Tasks:**
- [ ] GDELT BigQuery query: fetch events from last 30 minutes, India-relevant
- [ ] RSS parser using `feedparser`: poll 6-8 feeds
- [ ] Canonical article schema: `{id, title, summary, source, url, published_at}`
- [ ] Dedup: SHA256 hash of normalized title → SQLite `seen_hashes` table
- [ ] Near-dedup: MinHash (datasketch) with 0.8 similarity threshold
- [ ] SQLite database: `articles`, `seen_hashes`, `processed_articles`
- [ ] Cron job: run every 30 minutes

**Output:** `ingest.py` — fetches, deduplicates, stores new articles in SQLite

**Expected:** ~100-200 unique articles/day after dedup

---

### Step 5: Tag Extraction + Graph Matching

**What:** The core algorithm. Article → tags → graph nodes → user match.

**Two-stage hybrid approach:**

```
Stage 1: LLM extracts free-form tags
  Article headline + summary → Gemini Flash →
  {
    "tags": ["crude oil", "OPEC production cut", "fuel prices"],
    "indirect_effects": ["transport costs", "food inflation"],
    "domains": ["energy", "food"]
  }

Stage 2: Embedding match tags → graph nodes
  Each tag → FAISS query → top-K matching nodes (threshold > 0.65)
  "crude oil" → crude_oil (0.92), brent_crude (0.87), wti_crude (0.84)
  "fuel prices" → petrol_price (0.88), diesel_price (0.85)

Stage 3: Check user reachability
  Matched nodes ∩ user reachability set → hits
  crude_oil ∈ user_reachable? → YES (path: crude_oil → petrol_price → user.commute)

Stage 4: Score
  score = Σ(match_confidence × hop_decay × edge_strength × user_importance)
  hop_decay = [1.0, 0.85, 0.65, 0.45]
```

**Tasks:**
- [ ] Gemini Flash API integration (free tier: 1,500 req/day)
- [ ] Tag extraction prompt with 5 few-shot examples
- [ ] Critical instruction: "what does this AFFECT, not just what it MENTIONS"
- [ ] Separate `tags` (direct) from `indirect_effects` (lower weight)
- [ ] FAISS matching with threshold tuning
- [ ] User reachability set computation (backward BFS, 3 hops, cached)
- [ ] Scoring function: noisy-OR aggregation across paths
- [ ] Hub node dampening: penalize high-degree nodes ("India", "economy")
- [ ] Stop-list for overly broad tags
- [ ] SQLite: store matched articles with scores + matched nodes + paths

**Output:** `matcher.py` — `process_article(article) → list[UserImpact]`

**Prompt for Stage 1:**
```
You are a news impact analyst. Given a news article, extract:

1. tags: What real-world things does this article directly affect?
   (commodities, policies, sectors, companies, infrastructure)
2. indirect_effects: What secondary effects might follow?
   (price changes, supply disruptions, policy responses)
3. domains: Which broad domains?
   (energy, food, financial, employment, local_governance,
    geopolitics, climate, health, trade, technology, housing)

Be exhaustive. Think about second and third order effects.
Do NOT just list what the article mentions — list what it AFFECTS.

Article:
{title}
{summary}
```

---

### Step 6: Explanation Generation

**What:** When an article matches a user, generate "this affects you because..."

**Tasks:**
- [ ] Explanation prompt: takes article + matched nodes + path to user + user context
- [ ] Gemini Flash generates 2-3 sentence explanation
- [ ] Include: why relevant, how it affects, approximate magnitude if possible
- [ ] Severity classification: high / medium / low
- [ ] Cache explanations (same article, same path = same explanation)

**Prompt:**
```
A news article matched this user's life graph.

Article: {title} — {summary}
Matched on: {matched_nodes}
Path to user: {node} → {edge} → {node} → ... → user's {dependency}
User context: {relevant user info from graph}

Write a concise explanation (2-3 sentences):
1. Why this is relevant to them specifically
2. How it might concretely affect their life
3. Severity: high/medium/low

Be specific and practical. Use numbers where possible.
Don't be alarmist. If uncertainty is high, say so.
```

**Output:** `explain.py` — `generate_explanation(article, matches) → Explanation`

---

### Step 7: Telegram Delivery

**What:** Send matched articles to user via Telegram bot.

**Delivery tiers:**
- **High severity:** Push immediately via Telegram
- **Medium severity:** Batch into daily digest (8 AM)
- **Low severity:** Weekly summary (Sunday evening)

**Tasks:**
- [ ] Telegram bot setup (python-telegram-bot)
- [ ] Message format:
  ```
  📰 OPEC announces 2M barrel production cut

  This affects you because you drive to work daily.
  Petrol prices may rise 10-15% in the next 2-4 weeks,
  adding ~₹800-1,200 to your monthly commute cost.

  Severity: Medium
  Source: Reuters | 2 hours ago

  [Relevant? 👍 👎]  [Read article →]
  ```
- [ ] Daily digest: compile all medium-severity matches, send at 8 AM
- [ ] Feedback buttons: 👍 (relevant) / 👎 (not relevant) → tune thresholds
- [ ] `/profile` command: re-run questionnaire or update specific answers
- [ ] `/settings` command: change notification preferences
- [ ] Store feedback in SQLite for threshold calibration

**Output:** `bot.py` — Telegram bot with onboarding + delivery + feedback

---

## Putting It All Together

```
impact-news/
├── graph/
│   ├── merge.py          # Step 1: merge YAML → unified graph
│   ├── graph.py          # Graph loading + traversal functions
│   └── embeddings.py     # Step 2: FAISS index over node aliases
├── user/
│   ├── onboarding.py     # Step 3: questionnaire → user graph
│   ├── inference.py      # City/job/etc → graph node inference
│   └── user_graph.json   # User's connections to the graph
├── pipeline/
│   ├── ingest.py         # Step 4: GDELT + RSS → SQLite
│   ├── matcher.py        # Step 5: article → tags → graph → user
│   └── explain.py        # Step 6: generate explanations
├── bot/
│   └── bot.py            # Step 7: Telegram bot
├── taxonomy/
│   ├── food_energy_graph.yaml
│   ├── employment_domain_graph.yaml
│   ├── financial_system_domain_graph.yaml
│   ├── local_governance_graph.yaml
│   └── merged_graph.yaml  # Output of merge step
├── research/                    # All research docs
├── plans/                       # This file + master plan
├── data/
│   └── impact_news.db          # SQLite: articles, matches, feedback
├── main.py                     # Cron entry point
├── requirements.txt
└── .env                        # GEMINI_API_KEY, TELEGRAM_BOT_TOKEN
```

---

## Dependencies

```
# Core
networkx          # In-memory graph
sentence-transformers  # Embedding model (all-MiniLM-L6-v2)
faiss-cpu         # Vector similarity search
google-generativeai  # Gemini Flash free tier
python-telegram-bot  # Telegram bot
feedparser        # RSS parsing
datasketch        # MinHash deduplication
pyyaml            # YAML parsing
google-cloud-bigquery  # GDELT via BigQuery

# Standard
sqlite3           # Built-in
hashlib           # Built-in
```

---

## Execution Order

```
Week 1 (Foundation):
  Day 1: Step 1 (merge graph) + Step 2 (embeddings)
  Day 2: Step 3 (onboarding + inference rules)
  Day 3: Step 4 (ingestion pipeline)

Week 2 (Core + Delivery):
  Day 4: Step 5 (tag extraction + matching)
  Day 5: Step 6 (explanation generation)
  Day 6: Step 7 (Telegram bot)
  Day 7: Integration test — run end-to-end on real articles

Week 3 (Calibrate):
  - Run for a week, observe output quality
  - Tune: tag extraction prompt, embedding threshold, scoring weights
  - Add/fix graph nodes based on articles that should have matched but didn't
  - Adjust notification thresholds based on volume
```

---

## Cost: $0/month

| Component | Cost |
|-----------|------|
| Gemini 2.0 Flash (1,500 req/day free) | $0 |
| GDELT BigQuery (1TB/month free) | $0 |
| RSS feeds | $0 |
| all-MiniLM-L6-v2 (runs locally) | $0 |
| FAISS (runs locally) | $0 |
| NetworkX (runs locally) | $0 |
| SQLite (local file) | $0 |
| Telegram bot | $0 |
| Your Mac (already running) | $0 |
| **Total** | **$0** |

---

## Success Criteria (after week 3)

- [ ] Ingesting 100+ articles/day from 6+ sources
- [ ] <10% false positives (articles flagged as relevant that aren't)
- [ ] <20% false negatives (relevant articles that were missed) — harder to measure
- [ ] Daily digest arriving at 8 AM with 3-10 relevant items
- [ ] Explanations are specific and actionable (not generic "this may affect the economy")
- [ ] Feedback loop working: 👍/👎 stored and usable for tuning
