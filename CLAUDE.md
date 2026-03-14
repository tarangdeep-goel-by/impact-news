# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Impact News is a causal news personalization engine for Telegram. It ingests articles from RSS feeds, uses Gemini LLM to extract what each article affects, matches those tags against a knowledge graph via embeddings, scores articles against a user's personal dependency graph, and delivers high-impact articles with explanations.

Core concept: "Not what interests you. What affects you." — causal chains from macro events (oil price hike) → personal impacts (your EMI, your food costs).

## Architecture

```
RSS Feeds → Collector (async) → Dedup (fingerprint+URL) → SQLite
  → Matcher (Gemini tag extraction + FAISS embedding match)
  → Traverse (causal impact propagation, modified Dijkstra)
  → Scorer (article impacts × user dependency graph)
  → Telegram Bot (high-priority alerts + daily digest)
```

**Three layers:**
1. **Personal Life Graph** — user answers 9 onboarding questions → inference rules map to graph nodes → BFS reachability
2. **Causal Knowledge Graph** — taxonomy of 5 trigger L1s (system) + 11 impact L1s (citizen), merged from domain YAML files + edge patches, loaded via NetworkX
3. **Delivery & Scoring** — sparse dot product scoring, 0.3x decay for indirect reachability

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `pipeline/` | Article collection (`collector.py`), tag extraction + scoring (`matcher.py`), SQLite (`database.py`), dedup (`dedup.py`), Gemini client (`gemini.py`) |
| `graph/` | NetworkX graph (`graph.py`), YAML merge (`merge.py`), impact propagation (`traverse.py`), FAISS embeddings (`embeddings.py`), quality audit (`quality.py`), coverage gaps (`coverage.py`), validation (`admin.py`) |
| `user/` | Onboarding questions (`onboarding.py`), answer→node inference with city/sector mappings (`inference.py`) |
| `bot/` | Telegram bot handlers, delivery jobs (`bot.py`) |
| `audit/` | Graph maintenance scripts (eval, patch generation, analysis) |
| `taxonomy/` | `TAXONOMY.md` — v4 taxonomy design (locked). YAML source files removed in latest clean slate commit; need to be regenerated |
| `data/` | Runtime: `impact_news.db`, `embeddings.faiss`, `user_graph.json`, `merged_graph.yaml` |

## Commands

### Run the app
```bash
python main.py run        # Full: bot + periodic pipeline (collect + process + deliver)
python main.py bot        # Bot only (onboarding + delivery, no pipeline)
python main.py collect    # One-shot article collection
python main.py process    # One-shot tag extraction + matching (requires user profile)
python main.py            # Default: init, collect once, test embedding queries
```

### Graph maintenance
```bash
python -m graph.quality --json    # Quality scorecard
python -m graph.coverage gaps     # Taxonomy gap analysis
python -m graph.merge             # Rebuild merged graph from YAML sources
python -m graph.admin validate    # Check duplicates, lint node IDs
python -m graph.traverse <node>   # Trace impact propagation from a node
```

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

## Conventions

- **Node IDs:** `snake_case`, regex `^[a-z][a-z0-9_]*$` (e.g., `crude_oil`, `home_loan_emi`)
- **Edge types:** 12 canonical types in UPPER_SNAKE_CASE: `AFFECTS`, `PRODUCES`, `REGULATES`, `DISRUPTS`, `SUPPLIES`, `DEPENDS_ON`, `CONTAINS`, `IS_A`, `FUNDS`, `COMPETES_WITH`, `EMPLOYS`, `MANAGES`
- **Edge properties:** `weight` (0-1), `polarity` (±1), `delay` (IMMEDIATE/SHORT_TERM/MEDIUM_TERM/LONG_TERM)
- **Categories:** 15 canonical L1 categories defined in `taxonomy/TAXONOMY.md`
- **Embeddings:** `all-MiniLM-L6-v2` (384-dim), indexes all node aliases + node ID via FAISS
- **Scoring thresholds:** high ≥ 0.5, medium ≥ 0.2

## Project History

- **Mar 8:** Conceived the core idea — "not what interests you, what affects you." Research confirmed no existing product combines causal chain modeling with citizen-centric impact taxonomy. Built master plan, research docs, initial taxonomy + graph YAML files.
- **Mar 10:** Built full pipeline infrastructure (collector, dedup, matcher, scorer, bot, graph engine). Multiple worktree sessions for graph v2 (edge weights, traversal) and user profiling redesign.
- **Mar 11-12:** Graph governance — taxonomy normalization, dedup, Gemini-generated nodes, fixed 74 node ID mismatches, redesigned profiling to tiered questions.
- **Mar 13:** v4 taxonomy locked (Trigger/Impact split, 5+11 L1s, boundary rules, stress tested). "Clean slate" commit — removed old graph YAML data, kept scripts + v4 design.

## Current State

All infrastructure code is complete and ready. The v4 taxonomy design is locked in `taxonomy/TAXONOMY.md`. Graph YAML data files were removed in the clean slate commit and need to be rebuilt from the v4 design.

**Next steps:** L2 subcategories → L3 leaf nodes → edges → rebuild YAML graph files.

Expected YAML files (not yet present):
- `taxonomy/universal_life_dependency_graph.yaml`
- `taxonomy/employment_domain_graph.yaml`
- `taxonomy/financial_system_domain_graph.yaml`
- `taxonomy/food_energy_graph.yaml`
- `taxonomy/local_governance_graph.yaml`
- `taxonomy/edge_patches.yaml`

## Key Design Docs

- `taxonomy/TAXONOMY.md` — v4 taxonomy: L1 categories, edge types, naming rules
- `GRAPH_GOVERNANCE.md` — graph quality rules, normalization, dedup policies
- `plans/MASTER-PLAN.md` — project vision and roadmap
- `plans/IMPLEMENTATION-PLAN.md` — phased build plan
- `research/` — design research for questionnaire, tag extraction, and taxonomy
