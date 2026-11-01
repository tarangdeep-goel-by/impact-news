# impact-news: research notes

Written from a full read of the current tree and the git history (103 commits, 2026-03-10 to 2026-04-07, plus a README commit on 2026-10-11). Facts are checked against code or commit messages. `TODO(tarang)` marks things only the author knows.

Predecessor: [`n8n-news-agent`](https://github.com/tarangdeep-goel-by/n8n-news-agent) (January to March 2026), an interest-based news digest on n8n and later FastAPI.

## 1. One-paragraph summary

Impact News reads Indian economy, markets and world RSS feeds and tries to answer "what could this change for an ordinary person in India, and for me in particular?". For about three and a half weeks (2026-03-10 to 2026-04-03) the answer came from a hand-built causal graph (about 760 nodes and 1,500 to 1,600 edges, of which about 770 to 880 were typed, weighted causal edges and the rest `CONTAINS` hierarchy links) traversed from a trigger node to citizen-level impact nodes, first with a modified Dijkstra, then Personalized PageRank, then a max-product "Causal Shock Propagation" search. On 2026-04-03 that engine was deleted and replaced by a two-tier Gemini pipeline that uses the taxonomy as a controlled vocabulary and builds a small causal graph per news event (macro shifts driving micro impacts), stored in SQLite. Users onboard through a Telegram bot, get a node-weight profile, and receive articles scored against it.

## 2. Current architecture (HEAD)

```
RSS (12 feeds) -> ArticleCollector -> Deduplicator (sha256 URL, title fingerprint, MinHash LSH) -> SQLite.articles
SQLite.articles -> select_diverse_articles (round-robin by source)
  -> TitleDeduplicator (Jaccard >= 0.6 vs last 24h + current batch)
  -> Tier 1: ArticleClassifier.classify_v3  [gemini-3.1-flash-lite-preview + T-tree + up to 50 active events]
       relevant=false -> article_impacts(rejection_reason)
       relevant=true  -> macro_shifts[], exclude_l1s[], event_match | event_name
  -> TaxonomyContext.format_i_trees_excluding(exclude_l1s)
  -> Tier 2: ImpactAnalyzer.analyze_new_v3 / analyze_update_v3  [gemini-3.1-pro-preview]
       -> micro_impacts[] (i_node, trajectory, probability, magnitude, delay_days, rationale, driving_t_nodes)
  -> EventStore.create_event_v3 / upsert_event_v3 -> events, macro_shifts, micro_impact_revisions, provenance
  -> article_impacts (flattened)
  -> profiling.matcher.score_article_for_user -> push / digest / skip -> article_matches
  -> Telegram (pipeline.run sends directly; bot jobs send pending matches)
  -> feedback buttons -> diagnostics / depth questions -> node weight adjustments
```

### Entry points

| Command | What it does | File |
|---|---|---|
| `python main.py collect` | One collection run | `main.py`, `pipeline/collector.py` |
| `python main.py bot` (or `run`) | Telegram bot: onboarding, `/profile`, feedback, delivery jobs | `bot/bot.py` |
| `python -m pipeline.ingest [--limit N --all --stats --events]` | Event-aware two-tier analysis. Resolves stale events first. | `pipeline/ingest.py` |
| `python -m pipeline.run [--collect --limit N --dry-run]` | Collect, Tier 1, Tier 2, score for the first user profile, send to Telegram | `pipeline/run.py` |
| `python -m graph.merge` | Rebuild `data/merged_graph.yaml` from `taxonomy/*-new.yaml` + `T7.yaml` | `graph/merge.py` |
| `python -m tests.eval.tier1_eval [--dry-run]` | 190-case relevance and trigger eval | `tests/eval/tier1_eval.py` |
| `python -m tests.eval.tier2_eval [--dry-run]` | 20-article impact ranking eval | `tests/eval/tier2_eval.py` |
| `python -m scripts.pipeline_trace --limit 15` | Markdown trace of the full flow for a synthetic Bangalore profile | `scripts/pipeline_trace.py` |

Nothing schedules collection or analysis. The bot's `JobQueue` only delivers existing matches (every 300 s for `high`, daily at `DIGEST_HOUR` for `medium`).

### Components

| Path | Role |
|---|---|
| `config.py` | `RSS_FEEDS` (12) and `Settings`: `gemini_api_key`, `telegram_bot_token`, `telegram_chat_id`, `graph_path`, `db_path`, `gemini_model` (`gemini-3.1-flash-lite-preview`), `gemini_pro_model` (`gemini-3.1-pro-preview`), `score_high_threshold` 0.5, `score_medium_threshold` 0.2, `digest_hour` 8. `collect_interval_hours` and `pipeline_interval_seconds` are unused. |
| `models.py` | `Article` (id = sha256(url), fingerprint = first 50 alphanumerics of the title), `CollectionResult`. Also graph-era leftovers (`Node`, `Edge`, `UserGraph`, `NodeMatch`, ...) that nothing imports. |
| `pipeline/collector.py` | `feedparser` in a thread pool per feed, `asyncio.gather`, HTML clean. Stores RSS title + summary only. No full-text scraping (unlike the predecessor). |
| `pipeline/dedup.py` | Layer 1: URL hash or fingerprint in `seen_hashes`. Layer 2: `datasketch` MinHash LSH on title word tokens, 128 permutations, threshold 0.8, rebuilt per batch. |
| `pipeline/gemini.py` | `google-genai` client, `temperature=0.3`. `parse_json_response` strips fences and slices the outermost `[...]` or `{...}`. |
| `engine/taxonomy_context.py` | Loads `merged_graph.yaml`, builds parent/child maps from `CONTAINS` edges, renders indented trees (`node_id: alias1, alias2`) for prompts. |
| `engine/classifier.py` + `engine/prompts/classify.py` | Tier 1. Up to 4 attempts, with 5/10/20 s backoff on 429/503. Drops event matches with confidence < 0.7. Coerces unknown trajectories to `escalating`. |
| `engine/llm_engine.py` + `engine/prompts/analyze_new.py`, `analyze_update.py` | Tier 2. Validates `i_node` against the taxonomy, clamps probability/magnitude to [0,1], `delay_days` to [1,365], sorts by probability x magnitude. Also contains the older V1 and V2 code paths (unused by the pipelines). |
| `engine/confidence_filter.py` | Tiers impacts as high (p >= 0.7 and p*m >= 0.4) / medium (p >= 0.5 and p*m >= 0.2) / low. Used only by `scripts/pipeline_trace.py`. |
| `pipeline/events.py` | `EventStore`: V1 (`events`), V2 (`trigger_instances`, `impact_edges`, `edge_support`) and V3 (`macro_shifts`, `micro_impact_revisions`, ...) methods. Pipelines use V3. |
| `pipeline/database.py` | SQLite schema (WAL, foreign keys on) and CRUD for articles, matches, profiles, feedback log. |
| `pipeline/delivery.py` | `score_all_users` bridge from `article_impacts` to `article_matches`. Not called from anywhere. |
| `profiling/` | Questionnaire YAML (segment 0: 5 questions, segments 1 and 2: 6 and 5 questions that the bot never asks, `diagnostics.yaml`: 14 diagnostic, 7 depth and 5 deepening questions), 80 cities with tier and seasonal flags, 17 universal nodes, `ProfileEngine`, `matcher.py`, `diagnostics.py`. |
| `bot/bot.py` | `python-telegram-bot` v20+: onboarding `ConversationHandler` (city, work, transport, housing, family), `/profile`, feedback/diagnostic/depth/deepening callbacks, delivery jobs. |
| `taxonomy/` | Source YAMLs. Only `I1-new..I8-new`, `T1-new..T6-new` and `T7.yaml` are merged. `I1..I11.yaml` and `T1..T5.yaml` are the older v4 trees, unused. |
| `data/merged_graph.yaml` | Runtime artefact: 381 nodes, 366 edges, all `CONTAINS`. 175 T nodes (136 leaves) under 7 roots, 206 I nodes (160 leaves) under 8 roots. Tracked in git even though `.gitignore` lists `data/`. |
| `plans/` | 16 design docs written during the build, including the PPR and graph v2 plans and the LLM replacement plan. |

### The taxonomy (current)

Two "worlds", from the graph-era constitution (Rule 2, "Locus of Interface Test"): *can a single citizen directly experience this in their body, wallet, schedule or environment?* Yes means I-world (impact), no means T-world (trigger).

- T1 Macroeconomic & Financial Markets, T2 Domestic Governance & Policy, T3 Geopolitical & External Forces, T4 Physical Infrastructure & Logistics, T5 Digital & Tech Infrastructure, T6 Social & Demographic Systems, T7 Ecological & Planetary Systems.
- I1 Income & Livelihood, I2 Cost of Living, I3 Mobility & Transport, I4 Health & Bodily Safety, I5 Education & Skilling, I6 Civic & Legal Friction, I7 Habitat & Surroundings, I8 Digital & Leisure.
- Nodes carry `aliases` (English plus Hinglish, e.g. "Ghar ka Kharcha", "atta", "gehu"), `category`, `level`, `is_category`.
- Commit `2b5dc6c`: I-world prompt context dropped from about 19K to about 10.8K tokens after the restructure.

### Tier 1 prompt (`engine/prompts/classify.py`)

- Inputs: full T-tree, up to 50 non-resolved events (id, name, category, stage, up to 5 shifts with trajectory, 150-char summary), title, summary.
- Explicit "when in doubt, include" bias, then long lists of what to filter (opinion pieces with no new fact, lobbying, company-specific news, causeless market roundups) and what not to filter (enacted foreign policy, quantified risk tied to real events, central bank signalling, IMF/World Bank revisions).
- Disambiguation rules: T2 is India acting, T3 is a foreign actor, tag both if India responds to a foreign event; T1 is measured outcomes, T2 is decisions.
- Output: `{relevant, macro_shifts:[{t_node, trajectory, context}], exclude_l1s, event_match:{event_id, confidence}, event_name}` or `{relevant:false, reason}`. Trajectory is one of `escalating`, `deescalating`, `status_quo` ("the non-event is the event"), `disruption`.
- Event matching is on root cause: "different sectors affected by the same crisis = same event".

### Tier 2 prompts

- New event (`analyze_new.py`): "multi-order impact cascade". 1st order (direct, p 0.7-1.0), 2nd order (knock-on, p 0.4-0.8), 3rd order (systemic, p 0.2-0.5). Target 6-10 impacts. Leaf IDs only. Think about "rickshaw drivers, housewives, factory workers, farmers, students, gig workers". Each impact also gets `scope`: `national`, `state:<Name>` or `city:<Name>`.
- Update (`analyze_update.py`): given a compressed state string (`Active Shifts: ...`, `Active Impacts: node (prob, mag, Nd)`), output only new or changed impacts with probability >= 0.2. Unchanged impacts are kept by the store.

### Storage (SQLite, `data/impact_news.db`)

| Table / view | Purpose |
|---|---|
| `articles`, `seen_hashes`, `execution_logs`, `sources` | Collection. `sources` is never written. |
| `article_impacts` | Per article: `is_relevant`, `triggers_json`, `impacts_json`, `rejection_reason`, `event_id`, `tier1_ms`, `tier2_ms`. |
| `events`, `event_articles` | Event header (name, summary, stage, category, denormalised `triggers_json` and `current_impacts_json`, `article_count`) and article membership. |
| `macro_shifts` | One row per (event, t_node), upserted with the latest trajectory and context. |
| `micro_impact_revisions` | Append-only. PK (event_id, i_node, article_id). |
| `current_micro_impacts` (view) | Latest revision per (event, i_node) via `ROW_NUMBER() OVER (PARTITION BY event_id, i_node ORDER BY created_at DESC)`. |
| `impact_drivers` | M:N edges from an event's micro impact to the macro shifts that drive it. Rebuilt on each update. |
| `shift_support`, `impact_support` | Which articles support which shift and which impact. |
| `trigger_instances`, `impact_edges`, `edge_support` | V2 schema (2026-04-03 to 04-05). Still created, no longer written. `decay_mature_edges` only touches these. |
| `article_tags` | Graph-era leftover, unused. |
| `user_profiles` | Telegram chat id, city, tier, raw answers, `node_weights_json`. |
| `article_matches` | Score, matched nodes, explanation, severity (`high`/`medium`), `delivered_at`, `feedback`. |
| `profile_feedback_log` | Feedback, diagnostic and depth answers, `node_adjustments_json`. |

So the per-event causal graph is: event -> macro_shift (T-node, trajectory) -> [impact_drivers] -> micro impact (I-node, p, m, delay) with article provenance on both ends.

### Personal scoring (`profiling/`)

- Profile = `UNIVERSAL_NODES` (17 nodes at 1.0: staples, LPG, electricity tariff, medicines, air pollution, extreme heat, mobile tariffs, scams, GST, ...) + city-tier activations + seasonal activations (from `cities.yaml`) + answer activations. Merge rule is max. Universals floor at 0.5.
- Per impact: `impact = p x m`, `personal = impact x weight` (skip if weight <= 0). Take the top 3, `score = min(sum/2, 1)`. `>= 0.5` push, `>= 0.2` digest, else skip.
- Location filter: `city:` and `state:` scopes must fuzzy-match the user's city/state; `national` or missing scope always passes.
- Feedback: thumbs-down asks a diagnostic question tied to the matched nodes (e.g. "not my industry" -> pick industry), thumbs-up occasionally asks a deepening question. Answers become relative weight deltas, applied with the universal floor.

### Config / env

`.env` via `pydantic-settings`: `GEMINI_API_KEY` (required for analysis), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, plus optional `DB_PATH`, `GRAPH_PATH`, `GEMINI_MODEL`, `GEMINI_PRO_MODEL`, `DIGEST_HOUR`, `SCORE_HIGH_THRESHOLD`, `SCORE_MEDIUM_THRESHOLD`.

### Libraries

`feedparser`, `datasketch`, `google-genai`, `pyyaml`, `pydantic`/`pydantic-settings`, `python-telegram-bot` (its JobQueue needs the `job-queue` extra, which `requirements.txt` does not request), `networkx` (only `graph/merge.py`). `sentence-transformers`, `faiss-cpu`, `beautifulsoup4` and `aiohttp` are in `requirements.txt` but no current code imports them (graph-era leftovers that make the image much heavier).

## 3. Evolution, stage by stage

Five stages in this repo, after the three in the predecessor (`n8n-news-agent` `docs/NOTES.md` section 5). Each "why" is quoted from a commit message, a plan in `plans/`, or a deleted doc (read with `git show <sha>^:<path>`); where nothing says, it is marked `TODO(tarang)`. Most graph-era code and data were deleted in `ecf7aa7`; `taxonomy/TAXONOMY.md`, `GRAPH_GOVERNANCE.md`, `research/` and `tests/golden/` followed in `a48afa8` (2026-04-06).

### Stage A: causal graph v1 (2026-03-10 to 2026-03-11)

- Commits: [`8b18007`](https://github.com/tarangdeep-goel-by/impact-news/commit/8b18007), [`1ecd03c`](https://github.com/tarangdeep-goel-by/impact-news/commit/1ecd03c), [`c61d52d`](https://github.com/tarangdeep-goel-by/impact-news/commit/c61d52d), [`5af232a`](https://github.com/tarangdeep-goel-by/impact-news/commit/5af232a), [`f9993ff`](https://github.com/tarangdeep-goel-by/impact-news/commit/f9993ff).
- What: the first commit is plans, research and five domain graphs (food and energy, employment, finance, local governance, a "universal life dependency" graph on India's CPI basket). `1ecd03c` merged them into one NetworkX graph (1,688 nodes, 2,464 edges), added a FAISS index over node aliases (`all-MiniLM-L6-v2`, threshold 0.55, top 3), a 9-question onboarding questionnaire producing a user graph, and RSS ingestion with exact + MinHash dedup. Article flow: Gemini extracts `tags`, `indirect_effects`, `domains` (10 articles per call) -> FAISS maps tags to nodes -> traversal -> `combined = tag_match x graph_score x user_importance` -> severity -> Gemini explanation -> Telegram (`pipeline/matcher.py`, `bot/bot.py` at `4beb73d`). This article side was added in `203eca8` (2026-03-13), on the merged v1 graph, just before it was cleared.
- Why a graph: `plans/MASTER-PLAN.md`, "Key Design Decision": "Don't ask the LLM to reason causally. Ask it to classify events. Let pre-built templates handle the causal chains. This sidesteps the 3+ hop reliability problem entirely." Its confidence table expected 85-95% on the first hop and 25-45% by the personal hop.
- What changed inside the stage: `plans/graph_v2_implementation.md` found 29% of edges were taxonomy rather than causal, 558 leaves had no causal edges, and "BFS without weights lights up the entire graph". A Gemini research chat (`taxonomy/eval_results/taxonomy_separation_research.md`, deleted in `bdf17d7`) proposed "elevators and trains". `5af232a` added weight, polarity and delay to edges, `IS_A` child->parent (0.2) and `CONTAINS` parent->child (0.9) edges, and a modified Dijkstra "with elevator logic". `f9993ff` redesigned onboarding to 10 + 5 sector questions.
- Dropped at the end: the five merged domain files, eval chunks and merged graphs (`bdf17d7`, "Clean slate"). `TODO(tarang)`: why rebuild from scratch rather than patch the merged graph?

### Stage B: two worlds and Personalized PageRank (2026-03-13 to 2026-03-19)

- Commits: [`203eca8`](https://github.com/tarangdeep-goel-by/impact-news/commit/203eca8), [`bdf17d7`](https://github.com/tarangdeep-goel-by/impact-news/commit/bdf17d7), [`fd4000b`](https://github.com/tarangdeep-goel-by/impact-news/commit/fd4000b), [`af563d8`](https://github.com/tarangdeep-goel-by/impact-news/commit/af563d8), [`3e032e4`](https://github.com/tarangdeep-goel-by/impact-news/commit/3e032e4), [`5c2de41`](https://github.com/tarangdeep-goel-by/impact-news/commit/5c2de41), [`8211e87`](https://github.com/tarangdeep-goel-by/impact-news/commit/8211e87), [`5dca235`](https://github.com/tarangdeep-goel-by/impact-news/commit/5dca235), [`d69f98e`](https://github.com/tarangdeep-goel-by/impact-news/commit/d69f98e), [`76b2e5e`](https://github.com/tarangdeep-goel-by/impact-news/commit/76b2e5e), [`353da85`](https://github.com/tarangdeep-goel-by/impact-news/commit/353da85).
- What: taxonomy v4, 5 T-world and 11 I-world L1s, generated root by root with Gemini 3.1 Pro (507 I nodes, 231 T nodes). Edges in three layers: intra-L1 laterals, cross-L1 "portals", T->I "bridges". Edge schema `{from, to, type, weight, polarity, delay, description}`, e.g. `southwest_monsoon -> traffic_congestion, PRODUCES, 0.85, +1, IMMEDIATE`. `TAXONOMY.md` grew into a 21-rule constitution: Rule 2 (Locus of Interface: can a citizen directly experience it? yes = I-world), Rule 3 (no node in both worlds), Rule 12b (edge type priority PRODUCES, SUPPLIES, FUNDS, DISRUPTS, DEPENDS_ON, REGULATES, MANAGES, EMPLOYS, COMPETES_WITH, AFFECTS fallback; REGULATES/MANAGES may not cross T->I), Rule 14 (DAG within each world), Rule 18 (bridge targeting by homogeneity). I->T feedback edges were in earlier designs, then banned (`5c2de41`, 2026-03-14; `d69f98e` purged the remaining references) because "they create cycles". Scenario suite: 52, then 58.
- Why PPR (`8211e87`): `plans/ppr-markov-engine.md`, "Current Dijkstra floods 90% of the graph because weights cluster 0.6–0.9. A single crude oil trigger reaches nearly every node." PPR separated probability (stationary distribution, restart 0.20), magnitude (hub-penalised dominant path) and timing (summed delays). Commit: Brent reached 33 nodes instead of about 450, RBI 70. `645f2e4` made it multi-seed (trigger plus up to 3 ancestors at x0.5 per level).
- Why CIS: `76b2e5e` weight calibration (type defaults -> Gemini re-rating of 755 edges -> replay of 5 historical events) gave NDCG@10 0.16 and concluded the bottleneck "is PPR favoring intermediate nodes over citizen-level leaves, not weights". `353da85` added `CIS = probability x magnitude x world_boost x leaf_boost` (I-world x3, L4 x2, L3 x1.2, categories x0.3) and a path-selection fix: NDCG@10 0.16 -> 0.41.
- Dropped: the Dijkstra engine and the old onboarding/inference code (`5dca235`, "will rebuild for current 738-node graph"); 921 Gemini-generated I->I laterals for "polarity inconsistency, AFFECTS overuse" (`ac7353b`), regenerated as 150 + 46 (`72b8390`, `6365265`).
- Also built: the Impact Atlas, a Cytoscape.js visualiser with a "PPR shockwave" mode (`8d0001f`); `tests/golden/cases.yaml`.

### Stage C: edge surgery and Causal Shock Propagation (2026-03-25 to 2026-03-28)

- Commits: [`52d16e4`](https://github.com/tarangdeep-goel-by/impact-news/commit/52d16e4), [`38b6128`](https://github.com/tarangdeep-goel-by/impact-news/commit/38b6128), [`ba48801`](https://github.com/tarangdeep-goel-by/impact-news/commit/ba48801), [`05429a4`](https://github.com/tarangdeep-goel-by/impact-news/commit/05429a4), [`2303fda`](https://github.com/tarangdeep-goel-by/impact-news/commit/2303fda), [`a4c99ab`](https://github.com/tarangdeep-goel-by/impact-news/commit/a4c99ab), [`ab98628`](https://github.com/tarangdeep-goel-by/impact-news/commit/ab98628), [`4beb73d`](https://github.com/tarangdeep-goel-by/impact-news/commit/4beb73d).
- What: `52d16e4` restored state from an iCloud archive "after local data loss" (`TODO(tarang)`: what happened?), bringing 71 scenarios, 25 canaries, `ground_truth.yaml` (16 real Indian events, 10 ranked impacts each) and Rule 21 (Direct Causation: no A->C edge if the signal must pass through B). T->T laterals and T->I bridges rebuilt: 762 nodes, 1,621 edges, scenarios 56/71, NDCG 0.31. Gemini adjacency review of 766 edges: 133 killed for Rule 21, 79 type fixes, 30 reweights. Re-rating of all 769 causal edges: 17 polarity flips, NDCG 0.32 -> 0.33, and the commit says "structural gaps are the bottleneck, not weights". `a4c99ab` added intermediaries (`retail_inflation_cpi`, `aviation_turbine_fuel`, `agricultural_household_income`): canaries 7 -> 15 of 25, scenarios 66/71. `ab98628`: magnitude = weakest edge instead of a product, because the product "was squaring the probability".
- Why CSP (`4beb73d`, commit message): PPR's fan-out split probability across outgoing edges when a shock hits all of them; the 20% restart leaked signal every hop; "1-hop infrastructure nodes always dominated over 2-3 hop citizen impacts". Algorithm (`_run_causal_shock`):

```
seeds = trigger + CONTAINS ancestors (x0.5 per level, max 3), normalised
score[seed] = seed weight
max-heap on score
pop u; for each causal successor v:
    s = score[u] * weight(u,v) * hop_friction   # hop_friction = 0.85
    if s >= threshold and s > score[v]: score[v] = s; path[v] = path[u] + [v]; push
depth limit 6-8 hops
magnitude = min(edge weights on path); polarity = product of edge polarities x event direction
delay = sum of delay ranks, capped at LONG_TERM
then push scores down CONTAINS edges (x0.9) to children, then rank by CIS
```

  A widest-path-style Dijkstra on the product of weights, under 5 ms for 769 nodes. RBI -> home_loan_emi moved from #6 to #1, brent -> flight_ticket from #22 to #1.
- What the graph got right: readable hop-by-hop paths (`a85dd96` hop tracing), 100% must-miss precision in the later A/B, and the T/I definition that the LLM era kept. The probability / magnitude / delay / polarity split from the PPR plan became the fields the LLM is asked for, and `ground_truth.yaml` became the yardstick used against it.
- What was wrong: the event-set NDCG stayed at 0.31 to 0.33 through the whole stage while most commits were edge kills, gap fills and intermediaries.

### Stage D: the LLM replaces the graph (2026-04-02 to 2026-04-03)

- Commits: [`f6f7c02`](https://github.com/tarangdeep-goel-by/impact-news/commit/f6f7c02), [`627d05a`](https://github.com/tarangdeep-goel-by/impact-news/commit/627d05a), [`d2a1643`](https://github.com/tarangdeep-goel-by/impact-news/commit/d2a1643), [`92090f2`](https://github.com/tarangdeep-goel-by/impact-news/commit/92090f2), [`2fbacd0`](https://github.com/tarangdeep-goel-by/impact-news/commit/2fbacd0), [`ecf7aa7`](https://github.com/tarangdeep-goel-by/impact-news/commit/ecf7aa7), [`b41243b`](https://github.com/tarangdeep-goel-by/impact-news/commit/b41243b).
- Why: `plans/llm-engine-replacement.md`, the graph is "rigid and expensive to maintain". The test was additive: Gemini gets both trees as text and returns I-world leaves with probability, magnitude, polarity, delay and mechanism, compared with the graph on its own tests.
- Evidence: `f6f7c02`, 19 golden cases: LLM 60% must-hit recall (80% after node-id fixes in `627d05a`), 83% must-miss precision, 6.2 impacts per case; graph 30%, 100%, 26.8. The LLM handled abstract triggers like `repo_rate` that the graph could not resolve; its false positives were read as "profile-awareness issues, not causal reasoning errors". `d2a1643`, 16 ground-truth events: LLM R@10 31.9%, NDCG 0.454; graph R@10 21.2%, NDCG 0.313; LLM won 10, graph 2, tie 4. `92090f2`: `gemini-3.1-flash-lite-preview` NDCG 0.460 at about 3 s per event. `2fbacd0`: first ingest run, 23 of 105 articles relevant; `b41243b` contrasts 22% with 100% under the graph engine.
- What it reversed: the master plan's "don't ask the LLM to reason causally". `plans/PRODUCT-VISION.md` (2026-04-03), principle 6: "Taxonomy as vocabulary, not engine."
- Dropped (`ecf7aa7`, 193 files, about 91,000 lines removed): PPR/CSP engine, FAISS embeddings, scenarios, canaries, audit tools, graph scripts, the Impact Atlas, all causal edge files, eval results. 22 Python files left (from 65+). Kept: T+I trees, `TAXONOMY.md`, `merge.py`, the LLM engine, ingestion, golden tests, the bot.

### Stage E: two tiers, events, smaller taxonomy, profiles (2026-04-03 to 2026-04-07)

- Commits: [`c45023d`](https://github.com/tarangdeep-goel-by/impact-news/commit/c45023d), [`9df0c3e`](https://github.com/tarangdeep-goel-by/impact-news/commit/9df0c3e), [`5de0f1d`](https://github.com/tarangdeep-goel-by/impact-news/commit/5de0f1d), [`a48afa8`](https://github.com/tarangdeep-goel-by/impact-news/commit/a48afa8), [`2b5dc6c`](https://github.com/tarangdeep-goel-by/impact-news/commit/2b5dc6c), [`6a6c347`](https://github.com/tarangdeep-goel-by/impact-news/commit/6a6c347), [`e51b810`](https://github.com/tarangdeep-goel-by/impact-news/commit/e51b810), [`e1303b0`](https://github.com/tarangdeep-goel-by/impact-news/commit/e1303b0), [`fc4724a`](https://github.com/tarangdeep-goel-by/impact-news/commit/fc4724a), [`8e54fab`](https://github.com/tarangdeep-goel-by/impact-news/commit/8e54fab), [`120e321`](https://github.com/tarangdeep-goel-by/impact-news/commit/120e321); full table in section 4.
- Two tiers (`c45023d` plan, `9df0c3e`): split the single 19K-token call into Flash Lite + T-tree for relevance and event matching and a reasoning model for impacts, "roughly 5x cheaper per article on average". `PRODUCT-VISION.md` describes an agent choosing tools and models; what was built is a fixed two-stage pipeline.
- Flat M:N schema (`5de0f1d`): `plans/macroshift-flat-schema.md`, the nested Event -> TriggerInstance -> ImpactEdge model "assumes 1:1 causation inherited from graph traversal", while impacts are multi-causal. Macro shifts and micro impacts became siblings, Tier 2 output became append-only revisions. Tier 1 F1 91.7% -> 93.7%.
- Taxonomy restructure: T-world 5 -> 7 L1s split by "speed and source", every node must read with escalating / deescalating / status_quo / disruption (`plans/taxonomy-restructure.md`, `a48afa8`). I-world 11 -> 8 L1s, 321 -> 160 leaves, prompt about 19K -> 10.8K tokens (`2b5dc6c`). The enum-matrix idea was dropped because "Personalization requires specific I-nodes (retail_petrol vs lpg_cylinder), not abstract categories" (`dd75857`).
- Tier 2 eval and prompt: 20 real articles, Claude-written ground truth (`6a6c347`); baseline showed sparse predictions, 1-3 per article (`3f41663`); the multi-order cascade prompt took NDCG@10 0.541 -> 0.673, R@10 43% -> 57%, P@10 76% -> 44% (`e51b810`).
- Profiles and delivery: `e1303b0` (questionnaire, universal nodes, city defaults, matcher, onboarding), `fc4724a` (diagnostic feedback loop), `8e54fab` (`pipeline.run`), `120e321` (HTML parse mode, because "Markdown special chars in LLM rationale caused parse failures").
- Dropped: the V2 trigger-instance schema (tables still created, no longer written), the 11-root I-world and 5-root T-world as runtime inputs (YAMLs still in `taxonomy/`), `TAXONOMY.md` and `tests/golden/` (`a48afa8`).

## 4. LLM era timeline

| Date | Commit(s) | Change | Measured result (from commit) |
|---|---|---|---|
| 04-03 | `2fbacd0` | Single-call ingest with no-impact filter | 105 articles, 23 relevant |
| 04-03 | `9df0c3e`, `92b8d95` | Two tiers, events, V2 trigger->edge schema, title dedup, edge decay, feed changes | |
| 04-03 | `5b9d492`..`7df78cd` | Tier 1 eval set: 190 hand-reviewed articles (Sep 2024 to Apr 2026) | P 87%, R 97%, F1 92% on 100 cases |
| 04-05 | `5de0f1d` | V3 MacroShift/MicroImpact flat M:N, append-only revisions | Tier 1 F1 93.7% |
| 04-06 | `a48afa8` | T-world 5 -> 7 categories, Gemini Pro-arbitrated ground truth | Tier 1 P 75%, R 91%, F1 82.5% |
| 04-06 | `2b5dc6c` | I-world 11 -> 8 categories, 160 leaves | NDCG 0.492 |
| 04-06 | `6a6c347`, `3f41663` | Tier 2 eval rebuilt: 20 real articles, ground truth written by Claude, predictions by Gemini | NDCG 0.490 |
| 04-06 | `e4ec617` | Trim ground truth to top 5, add P@k, drop L2 leaks | NDCG 0.541, R 43%, P 76% |
| 04-06 | `e51b810` | Multi-order cascade prompt | NDCG 0.673, R@10 57%, P@10 44% |
| 04-06 | `b8855dc` | Confidence filter | high tier 74% precision, 40% recall |
| 04-07 | `e1303b0`, `fc4724a` | Profiling, matcher, Telegram onboarding, adaptive feedback | |
| 04-07 | `8e54fab`, `120e321` | `pipeline.run`; HTML parse mode | |
| 04-07 | `841a7e1` | Public release scrub | |
| 10-11 | `d15a0da` | Product and architecture README | |

Checked-in eval snapshots agree with the README: Tier 1 relevance P 0.752, R 0.913, F1 0.825, trigger exact recall 0.672; Tier 2 mean NDCG@10 0.673, R@10 0.570, R@5 0.520, P@10 0.444, and a mean of about 39.8 s per article for the Tier 2 Pro call.

## 5. Decisions and trade-offs

- **Hand-built graph vs LLM reasoning.** The graph gave explainable paths and perfect must-miss precision but needed constant edge surgery and missed abstract triggers. The LLM gave better recall and ranking with a fraction of the code, at the cost of non-determinism, preview-model dependence and per-article latency and cost.
- **Taxonomy kept as a controlled vocabulary.** Outputs are validated against node IDs, which keeps personalisation (node weights) possible.
- **Two tiers.** Cheap Flash Lite filters most articles; Pro only runs on relevant ones. Tier 1 also narrows the I-tree via `exclude_l1s` to shrink Tier 2 prompts.
- **Recall over precision in Tier 1** ("when in doubt, include") and in the cascade prompt. Precision is recovered later by profile weights and the push/digest thresholds.
- **Events as the unit of memory.** Articles attach to events matched on root cause; impacts are revised, never overwritten.
- **Flat M:N over nested triggers.** V2 nested edges under a trigger instance; V3 lets one impact be driven by several shifts.
- **Cross-model eval.** Ground truth written by Claude, predictions by Gemini, to avoid a model grading its own style.
- **SQLite, single process.** Simple and local; no concurrency story.

## 6. Bugs and rough edges found while reading

1. **Tier 1 exclusion uses the old I-world codes.** `engine/prompts/classify.py` still lists I1 Food & Nutrition ... I11 Leisure (11 categories). The runtime taxonomy has I1 Income ... I8 Digital & Leisure. `format_i_trees_excluding` filters by the new codes, so an `exclude_l1s` of `["I7", "I11"]` meant as "Education, Leisure" removes I7 Habitat & Surroundings instead. The Tier 2 eval always passes the full I-tree, so this never showed up in metrics.
2. **`scope` is dropped.** The Tier 2 prompts ask for `scope`, `MicroImpact` has the field, but `_analyze_v3` does not copy it (or `order`) into the validated result. The matcher treats missing scope as national, so the city/state filter never removes anything in practice.
3. **Bot delivery still uses Markdown.** `120e321` moved `pipeline.run` to HTML because LLM rationale broke Markdown, but `bot._deliver_matches` still sends `parse_mode="Markdown"`.
4. **`pipeline/delivery.py` is never called.** Matches only appear via `pipeline.run`, which also sends immediately (both push and digest tiers), so the bot's digest job mostly has nothing to send unless `--dry-run` was used.
5. **`pipeline.run` always creates a new event** and scores only `get_all_user_ids()[0]`.
6. **Confidence filter imported but unused** in `pipeline.run`.
7. **Digest time is UTC.** `run_daily(time=dt.time(digest_hour, 0))` has no tzinfo, and python-telegram-bot defaults to UTC, so 8 means 13:30 IST.
8. **Decay only touches V2 tables.** `decay_mature_edges` updates `impact_edges`; V3 impacts never decay. Stale events are resolved after 7 days without updates.
9. **Duplicate impacts can crash inserts.** `micro_impact_revisions` has PK (event_id, i_node, article_id) with plain `INSERT`; if Tier 2 returns the same `i_node` twice for one article, the whole event write fails.
10. **Tier 2 JSON parse retries once**, not four times (only API errors get the full retry loop).
11. **Skipped articles are re-scored** forever by `score_new_articles_for_user` (no match row is written for `skip`), and only the latest 50 are considered.
12. **Summary-only input.** The collector keeps the RSS summary, often one or two sentences, so Tier 1 and 2 reason from very little text.
13. **Stale docs and leftovers.** `CLAUDE.md` describes a single-call engine, 14 feeds, 769 nodes and `tests/golden/` which no longer exists. `graph/merge.py` tries to import `scripts.dump_adjacency` and `graph.migrate_weights` (deleted; the error is caught). `scripts/pipeline_trace.py` hard-codes a DB path in a sibling `../../impact-news/data/` checkout. Old taxonomy YAMLs and V1/V2 code paths remain.
14. **Heavy unused dependencies** (`sentence-transformers`, `faiss-cpu`).
15. **No unit tests**; evals need live API quota and overwrite their snapshots.
16. **JobQueue dependency.** `requirements.txt` has `python-telegram-bot>=20.0` without the `[job-queue]` extra. In v20+ `app.job_queue` is `None` unless APScheduler is installed, so `bot.main()` would fail at `job_queue.run_repeating`. I did not run it; worth checking in a clean venv.

## 7. Open questions for the author

- `TODO(tarang)`: what made you start a new repo on 2026-03-10 rather than extend n8n-news-agent? The Python digest and impact-news overlapped for a few days.
- `TODO(tarang)`: what happened on 2026-03-25 (the "local data loss")?
- `TODO(tarang)`: was the Impact Atlas visualiser (Cytoscape.js, deleted in `ecf7aa7`) used much? Any screenshots worth keeping?
- `TODO(tarang)`: has the bot been run for real users beyond yourself, and is it still running anywhere?
- `TODO(tarang)`: does the graph-era work still feel worth it in hindsight, given the LLM beat it within a day of being tried?
