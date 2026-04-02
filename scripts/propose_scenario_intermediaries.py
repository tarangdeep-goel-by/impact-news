"""Propose intermediary nodes to restore 9 broken scenario paths.

Usage:
    python3 scripts/propose_scenario_intermediaries.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.graph_builder import GraphGemini

TAXONOMY_MD = PROJECT_ROOT / "taxonomy" / "TAXONOMY.md"

PROMPT = """You are a taxonomy architect for an Indian causal impact knowledge graph.

## Constitution
{constitution}

## Context

We cleaned the graph by killing 133 edges that violated Rule 21 (bypassing test). This broke 9 scenario paths. We now need to add intermediary nodes to restore these paths correctly.

## Existing Graph Context

### Relevant existing nodes and their connections:
- `energy_commodities` (T3-L3): children = [brent_crude, global_natural_gas, international_coal_prices]
- `inflation_indices` (T3-L3): children = [wpi]
- `agricultural_commodities` (T3-L3): children = [global_edible_oil_supply, global_food_grain_supply, global_sugar_supply]
- `agriculture_and_allied` (I4-L3): children = [farm_labor_wages, agricultural_crop_damage]
- `indirect_taxes` (I5-L3): children = [], 0 causal outgoing, 1 causal incoming (gst_council → AFFECTS)
- `wpi` (T3-L4): causal out = [kirana_store_income AFFECTS, monetary_policy_committee AFFECTS, india_10yr_bond_yield AFFECTS]
- `aggregate_consumer_confidence` (T3-L4): exists, has outgoing edges
- `southwest_monsoon` (T1-L4): has edges to agricultural_crop_damage, urban_flooding, traffic_congestion, groundwater_aquifers
- `brent_crude` (T3-L4): has edges to retail_petrol, retail_diesel, lpg_cylinder
- `commercial_airports` (T4-L3): has edge to domestic_flight_ticket (AFFECTS)
- `autumn_festive_season` (T5-L4): has edges to butter_and_ghee, irctc_train_ticket, festive_idol, retail_sugar, firecracker, crowd_emergencies, etc.

### The 9 broken paths and what intermediaries are needed:

**Gap 1: southwest_monsoon → retail_rice (path broken)**
Killed edge: `southwest_monsoon → global_food_grain_supply` (Rule 21: goes via crop yield)
Need: monsoon → [crop production node] → global_food_grain_supply → wheat_flour → retail_rice
Question: Should the intermediary be `indian_crop_production` (T3)? Or `kharif_crop_yield` (T1)?

**Gap 2: southwest_monsoon → mgnrega_wages (bridge killed)**
Killed edge: `southwest_monsoon → mgnrega_wages` (Rule 21: goes via agricultural_crop_damage → rural distress)
The path should be: monsoon → agricultural_crop_damage → [rural_unemployment/distress] → mgnrega_wages
But agricultural_crop_damage (I4) → mgnrega_wages (I4) — is this a direct edge? When crops fail, does MGNREGA demand directly spike?

**Gap 3: brent_crude → domestic_flight_ticket (bridge killed)**
Killed edge: `brent_crude → domestic_flight_ticket` (Rule 21: goes via aviation fuel)
Need: brent_crude → aviation_turbine_fuel → domestic_flight_ticket
Question: Should `aviation_turbine_fuel` be under energy_commodities (T3-L3) alongside brent_crude? Or under a transport fuel category?

**Gap 4: gst_council → biscuits_and_snacks (path dead-ends at indirect_taxes)**
`indirect_taxes` (I5-L3) has zero causal outgoing edges. It's a tax category node.
The real chain: GST council sets rates → indirect_taxes (as a cost component) → retail prices of FMCG goods
Need: indirect_taxes should have outgoing edges to retail food items (it directly raises their prices)

**Gap 5: wpi → aggregate_consumer_confidence (killed)**
Killed edge: `wpi → aggregate_consumer_confidence` (Rule 21: WPI is wholesale, goes via CPI/retail prices)
Need: wpi → [CPI/retail_inflation] → aggregate_consumer_confidence
Question: Should we add `cpi` or `consumer_price_index` under inflation_indices (T3-L3)?

**Gap 6: autumn_festive_season → wedding_venue (path broken)**
The edge `autumn_festive_season → wedding_venue` was killed (festive season doesn't directly produce wedding venues).
Question: Is there a legitimate direct mechanism? Festive + wedding season overlap in Oct-Dec. Or does this go via `wedding_season_aggregate`?

**Gap 7: upi_platform → cab_aggregator_fare (rank too low, #24)**
Not a structural gap — the path exists but is too long/weak. May not need a new node.

## Your Task

For each gap (1-6, skip 7 as it's a ranking issue):

### 1. Determine if a new intermediary node is truly needed
- Could the path be restored by adding a DIRECT edge between existing nodes instead?
- Does the intermediary pass Rule 5 (Matchable by LLM from headlines, Mappable to user, Edgeable)?
- Is there an existing node that could serve as the intermediary?

### 2. For each new node needed, provide:
```yaml
- id: snake_case_id
  name: "Human Readable Name"
  parent: existing_parent_node_id
  level: 3 or 4
  category: T1/T2/T3/T4/T5/I1-I11
  aliases: [alias1, alias2, alias3]
  rule_5:
    matchable: "Can an LLM tag this from a news headline?"
    mappable: "Can a user connect to this?"
    edgeable: "What causal edges does it have?"
```

### 3. For each new or restored edge:
```yaml
- from: source_node
  to: target_node
  type: EDGE_TYPE
  weight: 0.XX
  polarity: 1 or -1
  delay: IMMEDIATE/SHORT_TERM/MEDIUM_TERM/LONG_TERM
  description: "Direct mechanism explanation"
```

### 4. For Gap 4 (indirect_taxes dead-end):
This may not need a new node — just new outgoing edges from `indirect_taxes`. Propose which edges indirect_taxes should have. Remember it's I5-L3 (taxation), so edges go to retail price nodes.

## Output Format

For each gap, state:
- **VERDICT**: NEW_NODE / EXISTING_NODE / DIRECT_EDGE / NO_FIX_NEEDED
- Then the node spec (if new) and edge specs in YAML

End with a COMPLETE SUMMARY of all new nodes and edges.
"""


def main():
    constitution = TAXONOMY_MD.read_text()
    prompt = PROMPT.format(constitution=constitution)

    print(f"Prompt length: {len(prompt)} chars")
    print("Calling Gemini 3.1 Pro Preview...")

    gemini = GraphGemini()
    response = gemini.call(prompt, thinking_budget=32000, max_output_tokens=65000)

    out_path = PROJECT_ROOT / "taxonomy" / "eval_results" / "scenario_intermediary_proposals.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(response)
    print(f"\nResponse saved to {out_path}")
    print("\n" + response)


if __name__ == "__main__":
    main()
