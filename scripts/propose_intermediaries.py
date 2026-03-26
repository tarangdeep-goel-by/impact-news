"""Ask Gemini to propose intermediary nodes for rejected gap-fill edges.

Usage:
    python3 scripts/propose_intermediaries.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.graph_builder import GraphGemini

TAXONOMY_MD = PROJECT_ROOT / "taxonomy" / "TAXONOMY.md"

PROMPT = """You are a taxonomy architect for an Indian causal impact knowledge graph.

## Constitution (Full)

{constitution}

## Context

We audited 28 proposed gap-fill edges. 18 were REJECTED for Rule 21 violations — the causal signal requires an intermediary node that doesn't exist in the graph yet.

Per the constitution (line 384-389):
> If A affects C through B, but B does not exist in the taxonomy:
> - DO NOT draw A→C as a temporary fix.
> - DO propose the addition of Node B (following Rule 5 and Rule 9), then draw A→B and B→C.

## Existing Graph Context

Here are the 18 rejected edges grouped by the intermediary they need:

### Group 1: Natural disasters → citizen physical damage
Rejected edges:
- cyclonic_storm_systems → structural_collapse (via "housing_damage")
- himalayan_tectonic_plates → structural_collapse (via "housing_damage")
- indian_plate_interior → structural_collapse (via "housing_damage")
- indian_plate_interior → residential_power_supply (via power_substations — THIS NODE EXISTS in T4)

Note: `structural_collapse` (I8-L4) exists. `power_substations` (T4-L4) exists.
For indian_plate_interior → residential_power_supply, the intermediary `power_substations` already exists, so we just need the edge indian_plate_interior → power_substations.

Question: Is "housing_damage" the right intermediary, or should these natural forces directly bridge to structural_collapse? Earthquakes and cyclones don't damage "housing" as a concept — they directly cause structural collapses of buildings. Is the intermediary actually needed here, or was Gemini being overly strict?

### Group 2: Forest cover → environmental impacts
Rejected edges:
- forest_cover → ambient_aqi (via "particulate_matter")
- forest_cover → urban_flooding (via "surface_runoff")
- forest_cover → drinking_water_quality (via "river_systems" — himalayan/peninsular river systems EXIST)

Note: `ambient_aqi` (I9-L4), `urban_flooding` (I9-L4), `drinking_water_quality` (I2-L4) all exist.
Peninsular_river_systems (T1-L4) and himalayan_river_systems (T1-L4) exist but are T-world.

Question: Does forest_cover → urban_flooding really need a "surface_runoff" intermediary? Surface runoff isn't a taxonomy entity — it's a physical mechanism. Similarly, does forest_cover → ambient_aqi need "particulate_matter"? PM is a measurement, not a causal entity. Reconsider whether these are genuine bypasses or whether the direct edge is valid because the "intermediary" is a mechanism description, not a graph entity.

### Group 3: Water systems → downstream impacts
Rejected edges:
- peninsular_river_systems → drinking_water_quality (via municipal_water_supply — EXISTS)
- peninsular_river_systems → farm_labor_wages (via "canal_irrigation")
- groundwater_aquifers → drinking_water_quality (via residential_borewells — EXISTS)

Note: municipal_water_supply (I2-L4) and residential_borewells (I2-L4) exist.
For peninsular_river_systems → drinking_water_quality: the intermediary municipal_water_supply EXISTS, so we just need the edge peninsular_river_systems → municipal_water_supply (already approved as Edge #5) and municipal_water_supply → drinking_water_quality.
For groundwater_aquifers → drinking_water_quality: residential_borewells EXISTS, so we need groundwater_aquifers → residential_borewells (already approved as Edge #13) and residential_borewells → drinking_water_quality.

Question: Do municipal_water_supply → drinking_water_quality and residential_borewells → drinking_water_quality edges already exist?

### Group 4: Cyclone → flight disruption
Rejected edge:
- cyclonic_storm_systems → domestic_flight_ticket (via commercial_airports — EXISTS in T4)

Note: cyclonic_storm_systems already has edges to T4 infra (power_substations, telecom_towers, seaports, power_grid). But NOT to commercial_airports.
commercial_airports (T4-L4) exists. domestic_flight_ticket (I3-L4) exists.

This just needs: cyclonic_storm_systems → commercial_airports (T→T lateral) + verify commercial_airports → domestic_flight_ticket bridge exists.

### Group 5: RERA → housing costs
Rejected edges:
- rera → residential_rent (via "real_estate_developers")
- rera → building_materials_cost (via "real_estate_developers")

Question: Does RERA really go through "real_estate_developers"? RERA directly regulates the real estate market — its rules on carpet area, project registration, and escrow accounts directly affect housing pricing. The "intermediary" is the regulation mechanism itself. Reconsider.

### Group 6: International institutions → Indian economy
Rejected edges:
- european_union → it_sector_jobs (via "it_services_exports")
- imf → india_10yr_bond_yield (via "sovereign_credit_rating")
- wto → it_sector_jobs (via "it_services_exports")

Note: `it_sector_jobs` (I4-L4), `india_10yr_bond_yield` (T3-L4) exist.

### Group 7: Bank liquidity → loan EMIs
Rejected edges:
- bank_liquidity_and_credit → home_loan_emi (via "commercial_bank_lending_rates")
- bank_liquidity_and_credit → personal_loan_emi (via "commercial_bank_lending_rates")

Note: `home_loan_emi` (I5-L4), `personal_loan_emi` (I5-L4) exist.
Also note: `rbi` (T2-L4) already has edges to home_loan_emi and other financial nodes. Does bank_liquidity_and_credit operate through RBI's MCLR/repo rate (which already exists as a path), or is there a direct bank-level mechanism?

## Your Task

For each of the 7 groups above:

1. **First, re-evaluate the rejection.** Was the intermediary genuinely needed, or was the original Gemini audit being overly strict? Consider:
   - Is the "intermediary" a physical mechanism (like surface_runoff, particulate_matter) or a genuine causal entity?
   - Does the intermediary pass Rule 5 (Matchable by LLM from headlines, Mappable to user, Edgeable)?
   - Would creating the intermediary node add real value to the graph, or just add complexity?

2. **For cases where the intermediary IS needed and DOESN'T exist:**
   Propose the new node with:
   - node_id (snake_case)
   - name (human readable)
   - parent node (which existing node should CONTAINS it)
   - level (L3 or L4)
   - category (which L1)
   - aliases (for embedding matching)
   - Rule 5 justification: Matchable? Mappable? Edgeable?

3. **For each new node, define the two-hop chain:**
   - Edge A→B: from, to, type, weight, polarity, delay, description
   - Edge B→C: from, to, type, weight, polarity, delay, description

4. **For cases where the intermediary EXISTS:**
   Just specify the missing edge(s) needed.

5. **For cases where the direct edge IS actually valid (no real intermediary needed):**
   State clearly: "Direct edge valid. Original rejection was overly strict because [reason]."
   Provide the corrected edge spec.

## Output Format

For each group, provide a clear verdict, then the specific edges/nodes to add. Use YAML format for edges and nodes.

At the end, provide a COMPLETE SUMMARY listing:
- All new nodes to create (with parent, level, category)
- All new edges to add (both intermediary edges and direct edges)
- Total count of new nodes and new edges
"""


def main():
    constitution = TAXONOMY_MD.read_text()
    prompt = PROMPT.format(constitution=constitution)

    print(f"Prompt length: {len(prompt)} chars")
    print("Calling Gemini 3.1 Pro Preview for intermediary proposals...")

    gemini = GraphGemini()
    response = gemini.call(prompt, thinking_budget=32000, max_output_tokens=16000)

    out_path = PROJECT_ROOT / "taxonomy" / "eval_results" / "phase4b_intermediary_proposals.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(response)
    print(f"\nResponse saved to {out_path}")
    print("\n" + response)


if __name__ == "__main__":
    main()
