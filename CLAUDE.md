# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Impact News is a causal news personalization engine for Telegram. It ingests articles from RSS feeds, uses Gemini LLM to extract what each article affects, matches those tags against a knowledge graph via embeddings, scores articles against a user's personal dependency graph, and delivers high-impact articles with explanations.

Core concept: "Not what interests you. What affects you." — causal chains from macro events (oil price hike) → personal impacts (your EMI, your food costs).

## Architecture

```
RSS Feeds → Collector (async) → Dedup (fingerprint+URL) → SQLite
  → Matcher (Gemini tag extraction + FAISS embedding match)
  → PPR Engine (Personalized PageRank probability + hub-penalized magnitude)
  → Scorer (article impacts × user dependency graph)
  → Telegram Bot (high-priority alerts + daily digest)
```

**Three layers (user profiling not yet rebuilt for new graph):**
1. **Personal Life Graph** — *needs rebuild*: user onboarding → inference rules → graph nodes → BFS reachability
2. **Causal Knowledge Graph** — taxonomy of 5 trigger L1s (system) + 11 impact L1s (citizen), merged from domain YAML files + edge patches, loaded via NetworkX
3. **Impact Scoring** — PPR (probability: will this reach me?) + hub-penalized path product (magnitude: how hard?) + delay sum (timing: when?). Constants and shared utilities live in `graph/markov_engine.py`.
4. **Delivery** — Telegram bot delivers HIGH alerts every 5min + MEDIUM digest at 8am

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `pipeline/` | Article collection (`collector.py`), tag extraction + scoring (`matcher.py`), SQLite (`database.py`), dedup (`dedup.py`), Gemini client (`gemini.py`) |
| `graph/` | NetworkX graph (`graph.py`), YAML merge (`merge.py`), PPR engine + shared constants (`markov_engine.py`), FAISS embeddings (`embeddings.py`), quality audit (`quality.py`), coverage gaps (`coverage.py`), validation (`admin.py`) |
| `bot/` | Telegram bot: delivery jobs + feedback (`bot.py`). Onboarding removed — needs rebuild for new graph |
| `audit/` | Graph maintenance scripts (eval, patch generation, analysis) |
| `taxonomy/` | `TAXONOMY.md` — v4 taxonomy design (locked). YAML source files removed in latest clean slate commit; need to be regenerated |
| `data/` | Runtime: `impact_news.db`, `embeddings.faiss`, `merged_graph.yaml` |
| `viz/` | Impact Atlas: Cytoscape.js interactive graph visualizer (top-down, street view, PPR shockwave) |

## Commands

### Run the app
```bash
python main.py run        # Bot + delivery jobs
python main.py bot        # Bot only (delivery + feedback)
python main.py collect    # One-shot article collection
python main.py            # Default: init, collect once, test embedding queries
```

Note: Article scoring (`process`) requires user profiling which needs rebuilding for the new graph.

### Graph maintenance
```bash
python -m graph.quality --json           # Quality scorecard
python -m graph.coverage gaps            # Taxonomy gap analysis
python -m graph.merge                    # Rebuild merged graph from YAML sources
python -m graph.admin validate           # Check edge refs, structural integrity
python -m graph.admin lint               # Lint YAML files for naming conventions
python -m graph.markov_engine <node>     # PPR impact analysis (standalone)
python -m graph.scenarios                # Run scenario suite with PPR engine
```

### Tests
```bash
python -m graph.scenarios                # Run scenario suite (PPR engine)
python -m graph.export_viz               # Export graph.json for Impact Atlas visualizer
```

### Impact Atlas (Interactive Visualizer)
```bash
python -m graph.export_viz               # Generate viz/data/graph.json (run after graph changes)
cd viz && python -m http.server 8080     # Serve at http://localhost:8080
```

Golden test harness (`tests/golden/run.py`) was removed — needs rebuild with new user profiling. Test case definitions kept in `tests/golden/cases.yaml` as reference for test design patterns (band assertions, must_hit/must_miss, score separation).

### Docker
```bash
docker compose up --build -d      # Start (dev mode: sleep infinity)
docker exec -it impact-news bash  # Shell into container
docker exec impact-news python main.py collect  # Run command inside
```

### Local development
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

## Environment Variables

Required in `.env`:
- `GEMINI_API_KEY` — Google Gemini API
- `TELEGRAM_BOT_TOKEN` — Telegram bot token
- `TELEGRAM_CHAT_ID` — Target chat for delivery

## Configuration

All tunable parameters are in `config.py` via Pydantic Settings (loaded from `.env`):

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `ppr_restart_prob` | 0.20 | PPR restart probability (shock intensity) |
| `ppr_prob_threshold` | 0.005 | PPR cutoff (nodes below this are discarded) |
| `ppr_magnitude_blend` | 0.5 | Weight of magnitude vs probability |
| `hub_dampening_threshold` | 20 | Penalize high fan-in nodes above this degree |
| `match_threshold` | 0.55 | FAISS embedding similarity cutoff |
| `max_hops` | 3 | BFS depth for user graph reachability |
| `score_high_threshold` | 0.5 | Score ≥ 0.5 → HIGH severity |
| `score_medium_threshold` | 0.2 | Score ≥ 0.2 → MEDIUM severity |
| `indirect_weight` | 0.7 | Discount for indirect effects |
| `gemini_model` | `gemini-2.0-flash` | Gemini model for tag extraction |
| `pipeline_interval_seconds` | 7200 | Pipeline run interval (2 hours) |
| `digest_hour` | 8 | Daily digest delivery hour |

RSS feeds are also configured in `config.py` as `RSS_FEEDS` list.

## Conventions

- **Node IDs:** `snake_case`, regex `^[a-z][a-z0-9_]*$` (e.g., `crude_oil`, `home_loan_emi`)
- **Edge types:** 12 canonical types in UPPER_SNAKE_CASE: `AFFECTS`, `PRODUCES`, `REGULATES`, `DISRUPTS`, `SUPPLIES`, `DEPENDS_ON`, `CONTAINS`, `IS_A`, `FUNDS`, `COMPETES_WITH`, `EMPLOYS`, `MANAGES`
- **Edge properties:** `weight` (0-1), `polarity` (±1), `delay` (IMMEDIATE/SHORT_TERM/MEDIUM_TERM/LONG_TERM)
- **Categories:** 15 canonical L1 categories defined in `taxonomy/TAXONOMY.md`
- **Embeddings:** `all-MiniLM-L6-v2` (384-dim), indexes all node aliases + node ID via FAISS IndexFlatIP
- **Scoring:** PPR engine (Personalized PageRank) with restart_prob=0.20, prob_threshold=0.005
- **No linting config:** No formal linter/formatter configured. Code follows PEP 8 informally.

## Project History

- **Mar 8:** Conceived the core idea — "not what interests you, what affects you." Research confirmed no existing product combines causal chain modeling with citizen-centric impact taxonomy. Built master plan, research docs, initial taxonomy + graph YAML files.
- **Mar 10:** Built full pipeline infrastructure (collector, dedup, matcher, scorer, bot, graph engine). Multiple worktree sessions for graph v2 (edge weights, traversal) and user profiling redesign.
- **Mar 11-12:** Graph governance — taxonomy normalization, dedup, Gemini-generated nodes, fixed 74 node ID mismatches, redesigned profiling to tiered questions.
- **Mar 13:** v4 taxonomy locked (Trigger/Impact split, 5+11 L1s, boundary rules, stress tested). "Clean slate" commit — removed old graph YAML data, kept scripts + v4 design.
- **Mar 15:** Replaced Dijkstra traversal with PPR (Personalized PageRank) engine. 3-layer scoring: probability (PPR), magnitude (hub-penalized path product), timing (delay sum). Reduces node reach from ~90% to 10-30% per trigger. 58 scenarios passing. Removed legacy Dijkstra (`traverse.py`) and old user profiling (`user/`) — both will be rebuilt for the new graph.

## Current State

Infrastructure code complete. v4 taxonomy design locked in `taxonomy/TAXONOMY.md`. **Graph is fully built**: 738 nodes, 1831 edges across all 16 L1 categories.

**Graph data files** (all present, all Gemini 3.1 Pro audited):
- `taxonomy/I1.yaml` through `I11.yaml` — 11 Impact L1 trees (CONTAINS + social movements in I4)
- `taxonomy/T1.yaml` through `T5.yaml` — 5 Trigger L1 trees (CONTAINS + T→T laterals)
- `taxonomy/bridge_edges.yaml` — 286 T→I bridge edges (L2 targets decomposed per Rule 18)
- `taxonomy/lateral_edges.yaml` — 219 I→I lateral edges (intra-L1 + cross-L1 portals)
- `taxonomy/scenarios.yaml` — 58 scenario tests (all T-world triggered, all passing)
- `taxonomy/laterals/` — per-L1 lateral edge source files
- `data/merged_graph.yaml` — merged output (built by `python -m graph.merge`)

**Scoring engine:** Multi-seed PPR in `graph/markov_engine.py`
- 3-phase: seed expansion (walk UP CONTAINS) → PPR on causal subgraph → CONTAINS propagation down
- Config in `config.py`: upward_seed_decay=0.5, max_seed_levels=3

**Audit tooling** (in `audit/`):
- `generate_laterals.py` / `generate_portals.py` — Gemini edge generation
- `review_laterals.py` / `fix_laterals.py` — Gemini edge review + fix
- `review_taxonomy.py` — Gemini constitution review
- `eval_graph.py` — domain-level evaluation

**Next steps:** Weight calibration (structural heuristics → Gemini re-rating → historical event replay), then user profiling rebuild.

## Key Design Docs

- `taxonomy/TAXONOMY.md` — v4 taxonomy: L1 categories, edge types, naming rules
- `GRAPH_GOVERNANCE.md` — graph quality rules, normalization, dedup policies
- `plans/MASTER-PLAN.md` — project vision and roadmap
- `plans/IMPLEMENTATION-PLAN.md` — phased build plan
- `research/` — design research for questionnaire, tag extraction, and taxonomy
