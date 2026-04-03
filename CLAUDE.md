# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Impact News is a causal news personalization engine for Telegram. It ingests articles from RSS feeds, sends each to Gemini LLM with the full T/I taxonomy as context, and in one call classifies whether the article has mass citizen impact and which specific trigger (T-node) and impact (I-node) dimensions are affected. Irrelevant articles (sports, celebrity, petty crime) are filtered. Results are stored for later matching against user profiles.

Core concept: "Not what interests you. What affects you."

## Architecture

```
RSS Feeds (14 sources)
  → ArticleCollector (async feedparser)
  → Deduplicator (URL hash + MinHash LSH)
  → SQLite (articles table)
  → LLMImpactEngine (one Gemini call per article)
     ├── no_impact: true → filtered with reason
     └── triggers: [T-nodes], impacts: [I-nodes with prob/mag/polarity/delay/mechanism]
  → article_impacts table
  → [Future] User Profile matching → Telegram delivery
```

**Two semantic worlds in the taxonomy:**
- **T-world (Triggers):** 5 L1 categories (T1-T5), 237 nodes. Macro-level system events citizens can't directly experience (crude oil, RBI policy, monsoon systems).
- **I-world (Impacts):** 11 L1 categories (I1-I11), 532 nodes. Citizen-level effects on body, wallet, schedule, environment (retail petrol, home loan EMI, school fees).

The LLM receives both full trees as prompt context and outputs structured JSON mapping articles to T-triggers and I-impacts. No graph traversal, no FAISS — the LLM reasons about causal chains directly.

## Commands

```bash
# Collect articles from RSS feeds
python main.py collect

# Classify articles via LLM engine (one Gemini call each)
python -m pipeline.ingest                    # 100 diverse unprocessed articles
python -m pipeline.ingest --limit 50         # Custom limit
python -m pipeline.ingest --all              # All unprocessed
python -m pipeline.ingest --stats            # Show classification stats

# Rebuild taxonomy hierarchy from YAML sources
python -m graph.merge

# Run golden test suite (must_hit/must_miss assertions)
python -m tests.golden.runner
python -m tests.golden.runner --case crude_oil_car

# Run event-based eval (NDCG, Recall@k against 16 ground truth events)
python -m tests.golden.eval_events
python -m tests.golden.eval_events --event gold_price

# Bot + delivery
python main.py bot
python main.py run                           # Bot + periodic collection

# Docker
docker compose up --build -d
docker exec -it impact-news bash
```

## Environment Variables

Required in `.env`:
- `GEMINI_API_KEY` — Google Gemini API key
- `TELEGRAM_BOT_TOKEN` — Telegram bot token
- `TELEGRAM_CHAT_ID` — Target chat for delivery

## Key Files

| File | Role |
|------|------|
| `engine/llm_engine.py` | `LLMImpactEngine` — sends article + full taxonomy to Gemini, parses structured JSON. Returns `(list[ImpactResult], metadata)` where metadata has `is_relevant`, `triggers`, `rejection_reason`. |
| `engine/prompt.py` | `build_impact_prompt()` — assembles the Gemini prompt with T-trees, I-trees, article, rules, and JSON output schema. Includes no-impact classification path. |
| `engine/taxonomy_context.py` | `TaxonomyContext` — loads `merged_graph.yaml`, builds CONTAINS hierarchy, formats trees as indented text for prompts. Key methods: `format_t_trees()`, `format_i_trees()`, `get_all_i_leaf_ids()`, `is_ancestor_of()`. |
| `engine/base.py` | `ImpactResult` TypedDict (node, probability, magnitude, polarity, delay, mechanism, path) and `ImpactEngine` Protocol. |
| `pipeline/ingest.py` | CLI pipeline: selects diverse articles, runs LLM engine, stores results in `article_impacts` table. |
| `pipeline/collector.py` | Async RSS fetcher across 14 feeds. |
| `pipeline/database.py` | SQLite schema: `articles`, `article_impacts`, `article_tags`, `article_matches`, `seen_hashes`, `execution_logs`. |
| `pipeline/gemini.py` | `GeminiClient.call(prompt)` wrapper + `parse_json_response()` (strips markdown fences, finds JSON boundaries). |
| `graph/merge.py` | `TaxonomyMerger` — merges T*.yaml + I*.yaml into `data/merged_graph.yaml`. Only CONTAINS edges matter now (hierarchy for taxonomy_context). |
| `config.py` | Pydantic Settings. Key: `gemini_model` (default: `gemini-3.1-flash-lite-preview`), `RSS_FEEDS` list, scoring thresholds. |

## Database Schema

The `article_impacts` table is the core output:
```sql
article_impacts (
    article_id TEXT PRIMARY KEY,
    is_relevant INTEGER,        -- 1 = has mass citizen impact, 0 = filtered
    triggers_json TEXT,         -- ["brent_crude", "global_shipping_routes"]
    impacts_json TEXT,          -- [{node, probability, magnitude, polarity, delay, mechanism}]
    rejection_reason TEXT,      -- "sports result", "individual crime", etc.
    processed_at TEXT
)
```

## Taxonomy Conventions

- **Node IDs:** `snake_case`, regex `^[a-z][a-z0-9_]*$` (e.g., `crude_oil`, `home_loan_emi`)
- **T/I split (Rule 2):** "Can a citizen directly experience this?" YES → I-world, NO → T-world
- **One node, one world (Rule 3):** Two sides of same entity = two nodes (e.g., `crude_oil` T3 vs `retail_diesel` I3)
- **Hierarchy:** L1 (root category) → L2 → L3 → L4 (leaf). Connected by CONTAINS edges.
- **16 L1 categories:** T1-T5 (Natural, Regulatory, Macro/Global, Tech, Geopolitics) + I1-I11 (Food, Housing, Transport, Employment, Finance, Education, Health, Safety, Utilities, Digital, Governance)
- **The LLM prompt tells Gemini to output I-world node IDs only as impacts, never T-world nodes.**

## LLM Engine Behavior

- `evaluate_article(title, summary)` returns `(impacts, metadata)` tuple
- For irrelevant articles: Gemini returns `{"no_impact": true, "reason": "..."}` → empty impacts list, `is_relevant=False`
- For relevant articles: Gemini returns `{"triggers": [...], "impacts": [...]}` → validated ImpactResult list
- Unknown node IDs from Gemini are logged and skipped (common: `retail_inflation_cpi`, `nifty_50` which are T-world)
- Exponential backoff on 429/503 errors (5s, 10s, 20s, up to 4 attempts)
- ~19K tokens per prompt (taxonomy context), ~3s per article on gemini-3.1-flash-lite

## Test Infrastructure

**Golden tests** (`tests/golden/cases.yaml`): 19 cases with synthetic user profiles + trigger nodes. Each case defines `must_hit` (nodes that MUST appear) and `must_miss` (false positive traps). Uses ancestor matching via taxonomy hierarchy.

**Event eval** (`tests/golden/ground_truth.yaml`): 16 real Indian events (Bangalore water crisis, Paytm ban, gold rally, etc.) with 10 ranked I-node impacts each. Metrics: Recall@10, NDCG@10, MRR.

Current: 80% must_hit recall, 83% must_miss precision, 0.460 NDCG on events.

## Current State

- **Ingestion pipeline:** Working. 390 articles collected, 105 classified (23 relevant, 82 filtered).
- **User profiling:** Not yet built for LLM architecture. Next major piece — match article I-nodes against user persona to determine personal relevance.
- **Taxonomy:** Locked. 769 nodes (237 T, 532 I). Source YAMLs in `taxonomy/`.

## Project History

- **Mar 8:** Conceived the idea. Built taxonomy v4 (T/I split, 16 L1s).
- **Mar 10-15:** Graph engine era: PPR, FAISS embeddings, 1831 causal edges, scenario suites.
- **Mar 22-26:** Phase 4 quality: canary runner, Gemini edge review, weight calibration. NDCG 0.41.
- **Apr 2-3:** LLM engine replaces graph engine. One Gemini call per article, no graph traversal. NDCG improved to 0.460. Graph code removed (-89K lines), taxonomy trees kept.
