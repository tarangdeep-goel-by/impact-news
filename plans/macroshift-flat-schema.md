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

**After (flat M:N):**
```
Event
  ├─ MacroShift (t_node + trajectory + context)
  ├─ MacroShift ...
  │
  ├─ MicroImpact (i_node + trajectory + prob + mag + delay + rationale)
  │    └─ driven by: [MacroShift A, MacroShift B]   ← M:N join
  ├─ MicroImpact ...
  │    └─ driven by: [MacroShift B]
```

Key differences:
- MacroShifts and MicroImpacts are siblings under Event, not parent-child
- Each MicroImpact has `driving_shifts` — M:N relationship to MacroShifts
- Tier 2 synthesizes ALL shifts together, not per-trigger isolation
- `trajectory` field: escalating / deescalating / status_quo / disruption

## Schema

```sql
-- Replace trigger_instances
CREATE TABLE macro_shifts (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(event_id),
    t_node TEXT NOT NULL,
    trajectory TEXT NOT NULL,  -- escalating | deescalating | status_quo | disruption
    context TEXT NOT NULL,     -- 1-line: what changed and why
    created_at TEXT DEFAULT (datetime('now')),
    status TEXT DEFAULT 'active'
);

-- Replace impact_edges
CREATE TABLE micro_impacts (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(event_id),
    i_node TEXT NOT NULL,
    trajectory TEXT NOT NULL,  -- escalating | deescalating | status_quo
    probability REAL NOT NULL,
    magnitude REAL NOT NULL,
    delay_days INTEGER NOT NULL,
    rationale TEXT NOT NULL,    -- 1-line: WHY this impact exists (synthesized from multiple shifts)
    maturity_date TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- M:N join: which macro shifts drive which micro impacts
CREATE TABLE impact_drivers (
    micro_impact_id TEXT NOT NULL REFERENCES micro_impacts(id),
    macro_shift_id TEXT NOT NULL REFERENCES macro_shifts(id),
    PRIMARY KEY (micro_impact_id, macro_shift_id)
);

-- Replace edge_support (article provenance)
CREATE TABLE impact_support (
    micro_impact_id TEXT NOT NULL REFERENCES micro_impacts(id),
    article_id TEXT NOT NULL REFERENCES articles(id),
    added_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (micro_impact_id, article_id)
);
```

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

**Input:** Basket of ALL macro_shifts + filtered I-tree + article
**Output:** Flat list of MicroImpacts, each with driving_t_nodes

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

**Key change:** Tier 2 no longer groups impacts under triggers. It sees the full basket of shifts and reasons about combined effects. A single MicroImpact can cite multiple MacroShifts as drivers.

## EventStore Changes

- `create_event_v2` → uses new tables (macro_shifts, micro_impacts, impact_drivers)
- `upsert_event` → upsert macro_shifts and micro_impacts independently
  - MacroShifts with ID → update trajectory/context
  - MacroShifts without ID → insert
  - MicroImpacts with ID → update prob/mag/delay/rationale
  - MicroImpacts without ID → insert
  - Rebuild impact_drivers links after each upsert
- `get_event_state` → returns all active macro_shifts + micro_impacts for an event
- `decay_mature_impacts` → same logic, on micro_impacts table

## TypedDict Changes

```python
class MacroShift(TypedDict, total=False):
    id: str
    t_node: str
    trajectory: str    # escalating | deescalating | status_quo | disruption
    context: str

class MicroImpact(TypedDict, total=False):
    id: str
    i_node: str
    trajectory: str
    probability: float
    magnitude: float
    delay_days: int
    rationale: str
    driving_t_nodes: list[str]  # T-node IDs, not MacroShift IDs (for prompt simplicity)
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

- `trigger_instances` table → `macro_shifts` table
- `impact_edges` table → `micro_impacts` table
- `edge_support` table → `impact_support` table
- TriggerInstance/ImpactEdgeV2 TypedDicts → MacroShift/MicroImpact
- Tier 1 prompt: "triggers" → "macro_shifts" with trajectory
- Tier 2 prompts: grouped trigger_instances → flat basket synthesis
- ImpactAnalyzer v2 methods: parse new output format
- pipeline/ingest.py: wire to new EventStore methods
- pipeline/events.py: new CRUD methods

## Execution Order

```
1. New TypedDicts in base.py (MacroShift, MicroImpact)
2. New tables in database.py (macro_shifts, micro_impacts, impact_drivers, impact_support)
3. EventStore new methods in events.py
4. Tier 1 prompt: macro_shifts + trajectory
5. Tier 2 prompts: basket synthesis + flat output
6. ImpactAnalyzer: parse new format
7. Ingest pipeline rewire
8. Update Tier 1 eval ground truth with trajectory
9. Run eval, verify no regression
10. Run pipeline on 50 articles, verify M:N relationships
```

Steps 1-3 are independent. Steps 4-5 are independent. Both converge at 6-7.

## Verification

- Run Tier 1 eval (190 cases) — relevance F1 should stay ≥90%
- Run pipeline on 50 articles — check micro_impacts have multiple driving_t_nodes
- Check: "RBI holds rate" article produces status_quo trajectory
- Check: impact_drivers table has M:N entries (one micro_impact driven by 2+ macro_shifts)
- Tree view: events show macro_shifts alongside micro_impacts, not nested
