# Plan: MacroShift + MicroImpact — Flat M:N Schema Rebuild

## Why

The hierarchical model (Event → TriggerInstance → ImpactEdge) assumes 1:1 causation inherited from graph traversal. In reality, citizen impacts are multi-causal: retail_petrol goes up because of brent_crude AND usd_inr_exchange AND ministry_of_finance subsidy removal. The hierarchical grouping can't represent this. Also, "trigger" is a graph-era concept — in the LLM world, T-nodes are macro-level state changes, not traversal entry points.

## Architecture Change

**Before (hierarchical):**
```
Event
  └─ TriggerInstance (t_node + context)
       └─ ImpactEdge (i_node, prob, mag, delay)
       └─ ImpactEdge ...
  └─ TriggerInstance ...
       └─ ImpactEdge ...
```

**After (flat M:N with event-sourced revisions):**
```
Event
  ├─ MacroShift (t_node + trajectory + context)      ← ONE per t_node per event
  ├─ MacroShift ...
  │
  ├─ MicroImpact (i_node + trajectory + prob + mag + delay + rationale)
  │    └─ driven by: [MacroShift A, MacroShift B]   ← M:N join
  ├─ MicroImpact ...
  │    └─ driven by: [MacroShift B]
  │
  └─ Revisions log: every Tier 2 output is an immutable INSERT, not an UPDATE
```

Key differences:
- MacroShifts and MicroImpacts are siblings under Event, not parent-child
- Each MicroImpact has `driving_shifts` — M:N relationship to MacroShifts
- Tier 2 synthesizes ALL shifts together, not per-trigger isolation
- `trajectory` field: escalating / deescalating / status_quo / disruption
- **Event-sourced:** every LLM output is appended as a revision, current state is a SQL view
- **UNIQUE(event_id, t_node)** and **UNIQUE(event_id, i_node)** at the active-state level — one MacroShift per T-node per event, one MicroImpact per I-node per event

## Schema

```sql
-- One active MacroShift per T-node per event
CREATE TABLE macro_shifts (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(event_id),
    t_node TEXT NOT NULL,
    trajectory TEXT NOT NULL,  -- escalating | deescalating | status_quo | disruption
    context TEXT NOT NULL,     -- 1-line: what changed and why (synthesized if multiple forces)
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    status TEXT DEFAULT 'active',
    UNIQUE(event_id, t_node)
);

-- Immutable revision log — every Tier 2 output INSERTs here
CREATE TABLE micro_impact_revisions (
    event_id TEXT NOT NULL REFERENCES events(event_id),
    i_node TEXT NOT NULL,
    article_id TEXT NOT NULL REFERENCES articles(id),  -- which article caused this revision
    trajectory TEXT NOT NULL,  -- escalating | deescalating | status_quo
    probability REAL NOT NULL,
    magnitude REAL NOT NULL,
    delay_days INTEGER NOT NULL,
    rationale TEXT NOT NULL,    -- 1-line: WHY this impact exists (synthesized from multiple shifts)
    driving_t_nodes TEXT NOT NULL,  -- JSON array: ["brent_crude", "usd_inr_exchange"]
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (event_id, i_node, article_id)
);

-- Current state = latest revision per (event_id, i_node)
CREATE VIEW current_micro_impacts AS
SELECT event_id, i_node, article_id, trajectory, probability,
       magnitude, delay_days, rationale, driving_t_nodes, created_at
FROM (
    SELECT *, ROW_NUMBER() OVER(
        PARTITION BY event_id, i_node ORDER BY created_at DESC
    ) as rn
    FROM micro_impact_revisions
) WHERE rn = 1;

-- M:N join: which macro shifts drive which micro impacts
-- Rebuilt from driving_t_nodes in current_micro_impacts
CREATE TABLE impact_drivers (
    event_id TEXT NOT NULL,
    i_node TEXT NOT NULL,
    macro_shift_id TEXT NOT NULL REFERENCES macro_shifts(id),
    PRIMARY KEY (event_id, i_node, macro_shift_id)
);

-- Article provenance for macro shifts
CREATE TABLE shift_support (
    macro_shift_id TEXT NOT NULL REFERENCES macro_shifts(id),
    article_id TEXT NOT NULL REFERENCES articles(id),
    added_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (macro_shift_id, article_id)
);

-- Article provenance for micro impacts (derived from revisions)
CREATE TABLE impact_support (
    event_id TEXT NOT NULL,
    i_node TEXT NOT NULL,
    article_id TEXT NOT NULL REFERENCES articles(id),
    added_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (event_id, i_node, article_id)
);
```

### Why event-sourced revisions

The old model did UPSERT — read state, LLM outputs new values, overwrite row. This breaks when:
1. **Concurrency:** Two articles on same event processed simultaneously → both read V1, both write V2, last write wins
2. **LLM ghosting:** LLM silently drops impacts it considers irrelevant to current article
3. **Lost provenance:** Can't trace WHY a value changed or WHEN

With revisions: every Tier 2 output is an immutable INSERT. The SQL view gives current state. Old revisions are preserved for audit. Concurrent writes both land safely (different article_ids).

## Tier 1 Changes

**Output schema:**
```json
{
    "relevant": true,
    "macro_shifts": [
        {
            "t_node": "brent_crude",
            "trajectory": "escalating",
            "context": "Oil prices spiked 4% after Iran attacks on Gulf infrastructure"
        },
        {
            "t_node": "usd_inr_exchange",
            "trajectory": "escalating",
            "context": "Rupee weakening as FIIs pull out amid geopolitical uncertainty"
        }
    ],
    "exclude_l1s": ["I7", "I11"],
    "event_match": {"event_id": "abc123", "confidence": 0.9},
    "event_name": null
}
```

**Prompt changes:**
- "Identify which T-world systems experienced a material shift in state"
- Remove "1-3 triggers" cap → find ALL active macro shifts
- Add trajectory enum with examples
- "status_quo" is valid when expectations were defied (RBI holds rate when cut expected)

## Tier 2 Changes

**Input:** Compressed state summary + filtered I-tree + article

For new events: macro_shifts from Tier 1 + filtered I-tree + article.

For event updates: compressed current state + new article's macro_shifts + filtered I-tree + article.

**Compressed state format** (not full JSON dump):
```
Active Shifts: brent_crude (escalating), usd_inr_exchange (escalating)
Active Impacts: retail_petrol (prob=0.85, mag=0.6, 7d), edible_oils (prob=0.75, mag=0.5, 30d)
```

**Prompt instruction:** "Given this current state and the new article, output ONLY the I-nodes that change or are newly created. Provide new absolute values. Do NOT repeat unchanged impacts."

**Output:** Flat list of MicroImpacts (only changed/new ones), each with driving_t_nodes:

```json
{
    "micro_impacts": [
        {
            "i_node": "retail_petrol",
            "trajectory": "escalating",
            "probability": 0.95,
            "magnitude": 0.8,
            "delay_days": 7,
            "rationale": "Crude oil spike + rupee weakening both push import bill up, OMCs will pass to consumers",
            "driving_t_nodes": ["brent_crude", "usd_inr_exchange"]
        }
    ],
    "summary": "...",
    "stage": "escalating"
}
```

**Key change:** Tier 2 sees the full basket of shifts and reasons about combined effects. A single MicroImpact can cite multiple MacroShifts as drivers. Only outputs deltas — unchanged impacts are retained automatically by the revision model.

## Store Logic

**On Tier 2 output:**
1. **MacroShifts:** UPSERT by `(event_id, t_node)` — update trajectory/context if changed. Add to `shift_support`.
2. **MicroImpact revisions:** INSERT into `micro_impact_revisions` — one row per changed i_node with the article_id that caused the revision. Never update or delete.
3. **Impact drivers:** Rebuild from `driving_t_nodes` in `current_micro_impacts` view.
4. **Impact support:** INSERT into `impact_support` — derived from the revision's article_id.

**maturity_date calculation:** Tier 2 outputs `delay_days`. Backend deterministically calculates `maturity_date = article.published_at + delay_days`. The LLM never does time math.

## TypedDict Changes

```python
class MacroShift(TypedDict, total=False):
    id: str
    t_node: str
    trajectory: str    # escalating | deescalating | status_quo | disruption
    context: str

class MicroImpact(TypedDict, total=False):
    i_node: str
    trajectory: str
    probability: float
    magnitude: float
    delay_days: int
    rationale: str
    driving_t_nodes: list[str]  # T-node IDs, not MacroShift IDs (for prompt simplicity)

class MicroImpactRevision(TypedDict):
    event_id: str
    i_node: str
    article_id: str
    trajectory: str
    probability: float
    magnitude: float
    delay_days: int
    rationale: str
    driving_t_nodes: list[str]
```

## What Carries Forward (no changes needed)

- Tier 1 eval dataset (190 cases) — add trajectory field to ground truth
- RSS feeds (12 sources)
- Title dedup, exclusion-based spotlight
- T-world and I-world taxonomies
- GeminiClient, retry logic
- Event matching (summary-based)
- Article collection pipeline

## What Gets Replaced

- `trigger_instances` table → `macro_shifts` table (with UNIQUE constraint)
- `impact_edges` table → `micro_impact_revisions` table + `current_micro_impacts` view
- `edge_support` table → `shift_support` + `impact_support` tables
- TriggerInstance/ImpactEdgeV2 TypedDicts → MacroShift/MicroImpact/MicroImpactRevision
- Tier 1 prompt: "triggers" → "macro_shifts" with trajectory
- Tier 2 prompts: grouped trigger_instances → compressed state + basket synthesis
- Tier 2 output: full state → deltas only (changed/new impacts)
- ImpactAnalyzer v2 methods: parse new output format
- pipeline/ingest.py: wire to new store logic (INSERT revisions, not UPSERT)
- pipeline/events.py: new CRUD methods with revision model

## Execution Order

```
1. New TypedDicts in base.py (MacroShift, MicroImpact, MicroImpactRevision)
2. New tables + view in database.py (macro_shifts, micro_impact_revisions, current_micro_impacts, impact_drivers, shift_support, impact_support)
3. EventStore new methods in events.py (revision-based writes)
4. Tier 1 prompt: macro_shifts + trajectory
5. Tier 2 prompts: compressed state input + delta output
6. ImpactAnalyzer: parse new format
7. Ingest pipeline rewire
8. Update Tier 1 eval ground truth with trajectory
9. Run eval, verify no regression
10. Run pipeline on 50 articles, verify M:N relationships + revision history
```

Steps 1-3 are independent. Steps 4-5 are independent. Both converge at 6-7.

## Verification

- Run Tier 1 eval (190 cases) — relevance F1 should stay >=90%
- Run pipeline on 50 articles — check micro_impact_revisions has multiple rows per (event_id, i_node)
- Check: "RBI holds rate" article produces status_quo trajectory
- Check: current_micro_impacts view returns latest revision per node
- Check: impact_drivers table has M:N entries (one i_node driven by 2+ macro_shifts)
- Check: shift_support tracks which articles support each MacroShift
- Check: concurrent article processing doesn't lose data (both revisions preserved)
- Tree view: events show macro_shifts alongside current micro_impacts, not nested
