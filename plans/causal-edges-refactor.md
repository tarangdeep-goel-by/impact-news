# Plan: Causal Edges Refactor — Tier Split + Spotlight Taxonomy

## Context

After running 392 articles through the two-tier pipeline, one event ("Middle East Conflict") absorbed 64 articles, 45 triggers, and 49 impacts. Root cause: flat `triggers_json`/`impacts_json` on events with append-only updates.

Additionally, both tiers are doing the wrong work:
- Tier 1 (cheap) doesn't identify triggers — Tier 2 re-discovers them
- Tier 2 (expensive) gets the full 19K-token taxonomy when it only needs a subset

This refactor fixes both: hierarchical causal edges + a clean tier responsibility split.

## Architecture Change

**Before:** Tier 1 = relevance + event match. Tier 2 = triggers + impacts (full 19K taxonomy).

**After:** Tier 1 = relevance + triggers + event match + exclusion spotlight. Tier 2 = impacts only (I-tree minus excluded L1s).

```
Tier 1 (flash-lite, ~7K tokens):
  Input:  article + T-tree (6K) + active events
  Output: triggers [{t_node, context}], exclude_l1s ["I7", "I11"], event_match

Tier 2 (pro, ~8-15K tokens):  
  Input:  triggers from T1 + I-tree MINUS excluded L1s + article + (existing edges if update)
  Output: trigger_instances [{t_node, context, edges: [{i_node, prob, mag, delay_days, polarity, mechanism}]}]
```

**Spotlight is exclusion-based, not inclusion-based.** Tier 1 identifies which I-world L1 categories are DEFINITELY NOT affected (e.g., Education won't be affected by a shipping crisis). Tier 2 gets everything else. This is safe — worst case Tier 1 excludes nothing and Tier 2 gets the full I-tree. We never risk missing valid impact chains.

**Data model change:**
```
Event (flat lists)          →   Event
  triggers_json                   └─ TriggerInstance (t_node, context)
  current_impacts_json                 └─ ImpactEdge (i_node, prob, mag, delay_days, polarity, mechanism)
                                       └─ ImpactEdge ...
                                  └─ TriggerInstance ...
                                       └─ ImpactEdge ...
```

Each edge tracks provenance (which articles support it) and has a maturity_date for decay.

## Implementation Steps

### Phase 0: New types in engine/base.py
- Add: `TriggerContext` (t_node + context), `ImpactEdge` (i_node, prob, mag, delay_days, polarity, mechanism, id), `TriggerInstance` (t_node, context, edges, id), `ClassificationResultV2` (relevant, triggers, exclude_l1s, event_match, event_name, reason), `AnalysisResultV2` (trigger_instances, stage, summary, is_relevant, rejection_reason)
- Keep existing types for golden test backward compat

### Phase 1: TaxonomyContext — exclusion-based I-tree filtering
- File: `engine/taxonomy_context.py`
- Add `format_i_trees_excluding(exclude_l1s: list[str]) -> str` — renders full I-tree MINUS the excluded L1 categories
- Add `_cat_to_node` cache mapping "I3" → node_id in `__init__`
- Exclusion-based: Tier 1 says "definitely NOT Education, NOT Leisure" → Tier 2 gets everything else
- Worst case (no exclusions): full I-tree (~12K tokens). Typical case: 2-3 excluded → ~9-10K tokens

### Phase 2: Database schema — causal edges tables
- File: `pipeline/database.py`
- Add tables: `trigger_instances`, `impact_edges`, `edge_support`
- Keep `triggers_json`/`current_impacts_json` on events as denormalized cache for Tier 1 prompt

### Phase 3: EventStore — causal edges CRUD
- File: `pipeline/events.py`
- Add: `create_event_v2()`, `upsert_event_edges()`, `get_event_edges()`, `decay_mature_edges()`, `_recompute_event_denorm()`
- Keep existing methods for backward compat

### Phase 4: Tier 1 prompt — T-tree aware classification
- File: `engine/prompts/classify.py` — rewrite to include T-tree, output triggers [{t_node, context}] + exclude_l1s
- Tier 1 outputs `exclude_l1s`: I-world L1 categories that are DEFINITELY NOT affected
- Must list all 11 I-world L1 codes in the prompt so Tier 1 knows what's available to exclude
- Rule: "Be conservative — only exclude categories you are CERTAIN have no causal link. When in doubt, don't exclude."
- File: `engine/classifier.py` — accept taxonomy in constructor, return ClassificationResultV2

### Phase 5: Tier 2 prompts — exclusion-filtered I-tree + causal edges output
- File: `engine/prompts/analyze_new.py` — receives triggers with context + I-tree (minus exclusions) + article. No T-tree. Outputs trigger_instances with nested edges.
- File: `engine/prompts/analyze_update.py` — same + receives existing instances with IDs for upsert. Edges with `id` = update, without = insert. Omitted edges = removed.

### Phase 6: ImpactAnalyzer — v2 methods
- File: `engine/llm_engine.py`
- Add: `analyze_new_v2()`, `analyze_update_v2()`, `_analyze_v2()`
- Keep existing methods unchanged (golden tests)

### Phase 7: Pipeline integration
- File: `pipeline/ingest.py`
- Rewire process_articles to: Tier 1 (with T-tree) → spotlight filter → Tier 2 (v2) → event CRUD (v2)
- Add edge decay alongside stale event resolution

## Dependency Graph
```
Phase 0 ──┬──→ Phase 1 ──────────────────┐
           ├──→ Phase 2 → Phase 3 ────────┤
           ├──→ Phase 4 ──────────────────┤
           └──→ Phase 5 → Phase 6 ────────┤
                                           └──→ Phase 7
```
Phases 1, 2, 4, 5 are independent and parallelizable.

## Files Modified (no new files)

| File | Change |
|------|--------|
| `engine/base.py` | +5 TypedDicts |
| `engine/taxonomy_context.py` | +format_i_subtrees(), +_cat_to_node |
| `pipeline/database.py` | +3 tables, +7 indexes |
| `pipeline/events.py` | +5 methods |
| `engine/prompts/classify.py` | Rewrite: +T-tree, new output schema |
| `engine/classifier.py` | +taxonomy param, return ClassificationResultV2 |
| `engine/prompts/analyze_new.py` | Rewrite: triggers + filtered I-tree input, trigger_instances output |
| `engine/prompts/analyze_update.py` | Rewrite: +existing instances, upsert output |
| `engine/llm_engine.py` | +analyze_new_v2, +analyze_update_v2, +_analyze_v2 |
| `pipeline/ingest.py` | Rewire to v2 flow |

## Token Budget

| Component | Before | After |
|-----------|--------|-------|
| Tier 1 prompt | ~2K | ~7K (added T-tree 6K) |
| Tier 2 new prompt | ~19K | ~12K typical (triggers 0.3K + I-tree minus 2-3 L1s ~9K + article 0.3K + rules 1K) |
| Tier 2 update prompt | ~20K | ~13K typical (same + existing edges ~1K) |
| Tier 2 worst case (no exclusions) | ~19K | ~14K (full I-tree + triggers + rules, but no T-tree) |

Savings are modest on token count (~5-7K per Tier 2 call) but the real win is:
1. Tier 2 no longer re-discovers triggers (Tier 1 already did that)
2. Causal edges prevent the mega-event accumulation problem
3. Exclusion-based filtering is safe — we never miss impacts

## Verification
1. `python3 -m pipeline.ingest --limit 10` — full pipeline with new flow
2. Check: trigger_instances and impact_edges tables populated
3. Check: Tier 1 outputs T-node IDs with context + exclude_l1s
4. Check: Tier 2 receives I-tree minus excluded L1s
5. Check: event updates use upsert (edges have IDs, existing edges updated not duplicated)
6. Check: `python3 -m pipeline.ingest --events` shows events with structured causal edges
7. Golden tests still pass: `python3 -m tests.golden.runner --case crude_oil_car`

## Existing Event Migration
Old 17 events have no trigger_instances/impact_edges rows. When Tier 2 loads edges for an old event, `get_event_edges()` returns `[]` — Tier 2 treats it as fresh analysis, creating all-new edges. This is correct behavior — no migration script needed.
