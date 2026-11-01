# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See `README.md` for the product overview and setup, and `docs/NOTES.md` for detailed notes, history and known bugs.

## What This Is

Impact News is a causal news-personalization engine for India, delivered over Telegram. It collects RSS articles, runs a two-tier Gemini pipeline that maps each relevant event from macro triggers (T-world) to citizen-level impacts (I-world), scores those impacts against a Telegram user's profile, and learns from feedback. Everything is stored in a local SQLite database (`data/impact_news.db`).

Core concept: "Not what interests you. What affects you."

## Architecture

```
RSS (12 feeds, config.RSS_FEEDS)
  -> ArticleCollector (async feedparser, RSS title + summary only)
  -> Deduplicator (sha256 URL, title fingerprint, MinHash LSH) -> SQLite.articles
  -> select_diverse_articles (round-robin by source) -> TitleDeduplicator (Jaccard >= 0.6)
  -> Tier 1: ArticleClassifier.classify_v3  [gemini_model, T-tree + up to 50 active events]
       relevant=false -> article_impacts.rejection_reason
       relevant=true  -> macro_shifts[], exclude_l1s[], event_match | event_name
  -> Tier 2: ImpactAnalyzer.analyze_new_v3 / analyze_update_v3  [gemini_pro_model, I-tree minus excluded roots]
       -> micro_impacts[] validated against data/merged_graph.yaml
  -> EventStore (V3): events, macro_shifts, micro_impact_revisions, impact_drivers, provenance
  -> profiling.matcher.score_article_for_user -> push (>= 0.5) / digest (>= 0.2) / skip -> article_matches
  -> Telegram delivery -> feedback -> diagnostics / depth questions -> node weight adjustments
```

The old hand-built causal graph engine (Dijkstra / PageRank / causal shock propagation, FAISS, scenario suites) was deleted on 2026-04-03. The taxonomy is now only a controlled vocabulary. See `docs/NOTES.md` section 3 for that history.

**Taxonomy (runtime artefact `data/merged_graph.yaml`):** 381 nodes, all edges `CONTAINS`.
- T-world: 175 nodes under 7 roots (T1 Macroeconomic & Financial Markets ... T7 Ecological & Planetary Systems).
- I-world: 206 nodes under 8 roots (I1 Income & Livelihood ... I8 Digital & Leisure).

## Commands

```bash
# Collect articles from RSS feeds
python main.py collect

# Event-aware two-tier analysis
python -m pipeline.ingest                    # up to 100 source-balanced unprocessed articles
python -m pipeline.ingest --limit 20
python -m pipeline.ingest --all
python -m pipeline.ingest --stats
python -m pipeline.ingest --events

# Convenience runner: collect, Tier 1, Tier 2, score for the first user profile, send to Telegram
python -m pipeline.run --collect --limit 20
python -m pipeline.run --limit 20 --dry-run  # no Telegram sends, but still writes to SQLite

# Telegram bot (onboarding, /profile, feedback, delivery jobs). `run` is an alias for `bot`.
python main.py bot

# Rebuild data/merged_graph.yaml from taxonomy/*-new.yaml + T7.yaml
python -m graph.merge

# Evals (call Gemini unless --dry-run; live runs overwrite the result snapshots)
python -m tests.eval.tier1_eval --dry-run
python -m tests.eval.tier2_eval --dry-run

# Markdown trace of one run for a synthetic profile
python -m scripts.pipeline_trace --limit 15

# Docker: the service idles (sleep infinity); run commands inside it
docker compose up --build -d
docker compose exec app python main.py collect
```

Nothing schedules collection or analysis. The bot's JobQueue only delivers existing matches (high every 300 s, medium daily at `DIGEST_HOUR`, interpreted as UTC).

## Environment Variables

`.env` via `pydantic-settings` (`config.py`):
- `GEMINI_API_KEY`: required for classification and analysis.
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: required for the bot and delivery.
- Optional: `DB_PATH`, `GRAPH_PATH`, `GEMINI_MODEL` (default `gemini-3.1-flash-lite-preview`), `GEMINI_PRO_MODEL` (default `gemini-3.1-pro-preview`), `DIGEST_HOUR` (8), `SCORE_HIGH_THRESHOLD` (0.5), `SCORE_MEDIUM_THRESHOLD` (0.2).

## Key Files

| File | Role |
|------|------|
| `main.py` | `collect` and `bot`/`run` entry points |
| `config.py` | `RSS_FEEDS` (12) and `Settings` |
| `pipeline/collector.py`, `pipeline/dedup.py` | RSS fetch, cleanup, two-layer dedup |
| `pipeline/ingest.py` | Event-aware two-tier analysis CLI |
| `pipeline/run.py` | Single-pass collect/analyze/score/send runner (always creates a new event) |
| `pipeline/events.py` | `EventStore` (V1, V2, V3 methods; pipelines use V3) |
| `pipeline/database.py` | SQLite schema (WAL, foreign keys) and CRUD |
| `pipeline/gemini.py` | `google-genai` client and `parse_json_response()` |
| `pipeline/delivery.py` | `score_all_users`; not wired into any entry point |
| `engine/classifier.py` + `engine/prompts/classify.py` | Tier 1 |
| `engine/llm_engine.py` + `engine/prompts/analyze_new.py`, `analyze_update.py` | Tier 2 (`ImpactAnalyzer`; V1/V2 paths are unused) |
| `engine/taxonomy_context.py` | Loads `merged_graph.yaml`, formats T/I trees for prompts, node lookups |
| `engine/confidence_filter.py` | Impact confidence tiers; used only by `scripts/pipeline_trace.py` |
| `profiling/` | Questionnaire YAML, cities, universal nodes, `ProfileEngine`, `matcher.py`, `diagnostics.py` |
| `bot/bot.py` | Telegram onboarding, `/profile`, feedback callbacks, delivery jobs |
| `graph/merge.py` | Builds `data/merged_graph.yaml` (hierarchy only) |
| `taxonomy/` | Source YAMLs; only `I1-new..I8-new`, `T1-new..T6-new`, `T7.yaml` are merged. `I1..I11.yaml`, `T1..T5.yaml` are unused v4 trees. |
| `tests/eval/` | Tier 1 (190 cases) and Tier 2 (20 articles) eval sets, runners and result snapshots |
| `plans/` | Historical design docs from the build |

## Database Schema (SQLite)

Main tables: `articles`, `seen_hashes`, `execution_logs`; `article_impacts` (per-article `is_relevant`, `triggers_json`, `impacts_json`, `rejection_reason`, `event_id`, `tier1_ms`, `tier2_ms`); `events`, `event_articles`; `macro_shifts`, `micro_impact_revisions` (append-only), view `current_micro_impacts`; `impact_drivers`, `shift_support`, `impact_support`; `user_profiles`, `article_matches`, `profile_feedback_log`. `trigger_instances`, `impact_edges`, `edge_support` (V2), `article_tags` and `sources` are still created but not written.

## Personal Scoring

```text
impact score   = probability x magnitude
personal score = impact score x user node weight
article score  = min(sum(top 3 personal scores) / 2, 1)
```

Profiles combine 17 universal nodes, city-tier and seasonal activations, and onboarding answers (merge = max, universals floored at 0.5).

## Testing

There is no unit-test suite. Evals live in `tests/eval/`, need live API quota unless `--dry-run`, and overwrite their snapshots. Saved snapshots: Tier 1 relevance P 0.752, R 0.913, F1 0.825; Tier 2 NDCG@10 0.673, R@10 0.570, P@10 0.444. `python -m compileall -q .` is a cheap syntax check.

## Known Issues

See `README.md` "Current boundaries" and `docs/NOTES.md` section 6. Notably: the Tier 1 prompt still lists the old 11 I-world categories; Tier 2 `scope` is dropped so the location filter has no effect; the bot sends with Markdown; `requirements.txt` lacks the `python-telegram-bot[job-queue]` extra and still lists unused graph-era packages.
