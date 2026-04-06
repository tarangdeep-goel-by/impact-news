# Plan: I-world Restructure + Tier 2 Eval

## Current State

**T-world (done):** 7 categories, 136 leaf nodes. Tier 1 eval: P=75%, R=91%, F1=82.5%.
**I-world (todo):** 11 categories (I1-I11), 321 leaf nodes across 532 total nodes. Needs restructuring to 8 categories (I1-I8), ~150-200 L3 nodes with enum matrix.
**Tier 2 eval:** Framework exists (16 events, NDCG/Recall). Baseline: NDCG@10=0.542, Recall@10=33%. Uses OLD I-node IDs.

## What Changed: 11 → 8 I-world Categories

| New | Name | Test | Old Source |
|-----|------|------|-----------|
| I1 | Income & Livelihood | Money IN | Old I4 (Employment) |
| I2 | Cost of Living | Money OUT | Old I1 (Food) + I2 (Housing) + parts of I5 |
| I3 | Mobility & Transport | Getting around | Old I3 |
| I4 | Health & Bodily Safety | Staying safe | Old I6 (Health) + I8 (Safety) |
| I5 | Education & Skilling | Moving up | Old I7 |
| I6 | Civic & Legal Friction | State interactions | Parts of old I5 (taxes) + new |
| I7 | Habitat & Surroundings | Local environment | Old I9 + I2 (utilities) |
| I8 | Digital & Leisure | Downtime | Old I10 + I11 |

## Architecture: Keep Granular Leaves (No Enum Matrix)

I-world stays specific because it's the user-facing output. "Crude oil is going up" isn't useful — the user needs to know "retail petrol price is rising" vs "LPG cylinder cost is rising" because different users care about different fuels.

Current: 321 leaf nodes across 11 categories.
Target: ~200-250 leaf nodes across 8 categories. Prune redundant/dead nodes, merge categories, but keep leaf specificity (retail_petrol, lpg_cylinder, cng_price stay separate).

The prompt gets smaller through category merges and pruning (~30% reduction), not through abstraction.

## Phases

### Phase 3A: I-tree Deep Dives with Gemini (parallelize all 8)

Send ALL 8 I-world categories to Gemini in parallel (not sequentially like we did T-world). Each prompt gets:
- Current YAML nodes for that category
- New L1 name and test criteria
- Instruction to propose L2/L3 structure with enum parameters
- Target: 15-25 leaf nodes per category

**Order doesn't matter** — all 8 are independent. Send all at once.

| New L1 | Old Source | Current Nodes | Target Nodes |
|--------|-----------|---------------|-------------|
| I2 Cost of Living | I1+I2+I5 parts | ~90 | 25-30 |
| I1 Income & Livelihood | I4 | ~69 | 20-25 |
| I3 Mobility & Transport | I3 | ~43 | 15-20 |
| I4 Health & Bodily Safety | I6+I8 | ~111 | 20-25 |
| I5 Education & Skilling | I7 | ~50 | 15-20 |
| I6 Civic & Legal Friction | I5 parts + new | ~30 | 15-20 |
| I7 Habitat & Surroundings | I9+I2 parts | ~50 | 15-20 |
| I8 Digital & Leisure | I10+I11 | ~87 | 20-25 |

**Deliverable:** 8 new YAML files (I1-new.yaml through I8-new.yaml), each with L2/L3 nodes + enum definitions.

### Phase 3B: Rebuild Merged Graph + Validate

1. Rebuild `data/merged_graph.yaml` from new T-files + new I-files
2. Validate: all node IDs unique, all edges valid, no orphans
3. Verify `taxonomy_context.py` loads correctly, `format_i_trees()` works
4. Check prompt token count: should drop from ~19K to ~12K

### Phase 3C: Remap Tier 2 Ground Truth

The 16 eval events use old I-node IDs (e.g., `private_water_tanker`, `fastag_wallet`). Need to:
1. Extract all unique I-node IDs from tier2_cases.json
2. Build old→new mapping (some 1:1, some merge, some become node+enum)
3. Send disputed/ambiguous cases to Gemini Pro for arbitration (same process as Tier 1)
4. Update tier2_cases.json with new I-node IDs

### Phase 3D: Run Tier 2 Eval (Baseline for New I-world)

1. Run `python -m tests.eval.tier2_eval` on all 16 events
2. Record NDCG@10, Recall@10, Recall@5
3. Compare against old baseline (NDCG=0.542)
4. This is the new baseline to iterate from

### Phase 3E: Bridge Test — 20 News Scenarios

Pick 20 diverse Indian news articles (from our 671 collected) and run the full T→I pipeline:
1. Tier 1 classifies (picks T-nodes)
2. Tier 2 analyzes (maps T-nodes → I-node impacts)
3. Manual review: do the impact chains make sense?

This tests the T→I handoff, not just individual tiers.

### Phase 3F: Iterate Tier 2 Prompt

Based on eval results and bridge test:
1. Tune `engine/prompts/analyze_new.py` for better impact precision
2. Tune enum usage — does the LLM correctly pick enums?
3. Target: NDCG@10 ≥ 0.60, Recall@10 ≥ 50%

## Run Order (Next Session)

```
1. Phase 3A — I-tree deep dives (all 8 in parallel via Gemini)     ~30 min
2. Phase 3A — Review + write YAMLs                                 ~20 min
3. Phase 3B — Rebuild merged graph + validate                      ~5 min
4. Phase 3C — Remap Tier 2 ground truth                            ~15 min
5. Phase 3D — Run Tier 2 eval baseline                             ~10 min
6. Phase 3E — Bridge test (20 articles)                            ~15 min
7. Phase 3F — Iterate Tier 2 prompt if needed                      ~20 min
```

## Key Decisions for Next Session

1. **Prompt token budget:** Current ~19K. Target ~14K. Category merges (11→8) + pruning should get us there. If still too big, use Tier 1 `exclude_l1s` to only show relevant I-branches to Tier 2.

2. **Ground truth depth:** The 16 events have 10 ranked impacts each. Should we expand to 20+ events? Or is 16 enough for a baseline?

3. **Leaf specificity cutoff:** Some old nodes are very niche (e.g., `stray_animals`, `ncmc_smart_card`). Keep if they appear in ground truth, prune if never triggered in real articles.

## Files to Modify

| File | Change |
|------|--------|
| `taxonomy/I1-new.yaml` through `I8-new.yaml` | New I-world YAMLs (granular leaves, 8 categories) |
| `data/merged_graph.yaml` | Rebuilt from new T + new I files |
| `engine/prompts/analyze_new.py` | Updated I-world category names in prompt |
| `tests/eval/tier2_cases.json` | Remapped I-node IDs |
