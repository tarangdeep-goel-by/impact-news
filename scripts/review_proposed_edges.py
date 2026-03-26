"""Send proposed gap-fill edges to Gemini for Rule 21 validation.

Usage:
    python3 scripts/review_proposed_edges.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.graph_builder import GraphGemini

TAXONOMY_MD = PROJECT_ROOT / "taxonomy" / "TAXONOMY.md"

PROPOSED_EDGES = """
## Proposed Gap-Fill Edges (Phase 4b)

These edges were proposed by an AI audit of nodes with zero or sparse causal outgoing edges.
For each, the source node currently has no (or very few) causal outgoing edges.
Your job is to validate each one against Rule 21 and the graph's existing topology.

### Source Node Context (current graph state)

1. **forest_cover** (T1-L4): 4 incoming causal, 0 outgoing. Sibling `arable_topsoil` has 2 outgoing.
2. **peninsular_river_systems** (T1-L4): 3 incoming (sw_monsoon SUPPLIES, ne_monsoon SUPPLIES, sewage DISRUPTS), 0 outgoing. Sibling `himalayan_river_systems` → renewable_energy_parks.
3. **indian_plate_interior** (T1-L4): 0 incoming, 0 outgoing. Sibling `himalayan_tectonic_plates` → highway_network.
4. **northeast_monsoon** (T1-L4): 1 outgoing (→ peninsular_river_systems SUPPLIES). Sibling `southwest_monsoon` has 20 outgoing (incl. bridges to urban_flooding, agricultural_crop_damage, residential_borewells, etc).
5. **groundwater_aquifers** (T1-L4): 3 incoming, 1 outgoing (→ rural_urban_migration_corridors AFFECTS).
6. **cyclonic_storm_systems** (T1-L4): 7 outgoing — all to T-world infra nodes (power_substations, telecom_towers, seaports, shipping, power_grid, marine_fish_stocks, forest_cover). Zero direct I-world bridges.
7. **himalayan_tectonic_plates** (T1-L4): 1 outgoing (→ highway_network DISRUPTS). No I-world bridges.
8. **migratory_pest_populations** (T1-L4): 1 outgoing (→ global_food_grain_supply DISRUPTS). No I-world bridges.
9. **bank_liquidity_and_credit** (T3-L3): 0 outgoing. Parent `financial_and_capital_markets` also has no causal edges.
10. **european_union** (T2-L4): 0 outgoing. Siblings: us_government (3 out), chinese_government (1 out), russian_government (1 out).
11. **imf** (T2-L4): 0 outgoing. Sibling: opec → brent_crude.
12. **wto** (T2-L4): 0 outgoing. Sibling: opec → brent_crude.
13. **high_courts** (T2-L4): 0 outgoing. Siblings: supreme_court → criminal_litigation_risk + telecom_spectrum; NGT → firecracker + forest_cover + coal_power_plants.
14. **rera** (T2-L4): 0 outgoing. Siblings: TRAI (3 out), CCI (2 out), DGCA (2 out), MeitY (3 out).
15. **regional_new_year_festivals** (T5-L4): 0 outgoing. Siblings: autumn_festive_season (15 out!), wedding_season (6 out), spring_harvest (1 out), islamic_festivals (1 out).

### Proposed Edges

#### T1 Natural Systems → I-world bridges:

1. forest_cover → ambient_aqi (I9): AFFECTS w=0.75 pol=-1 LONG_TERM — "Deforestation removes natural air filtration, directly degrading regional ambient air quality"
2. forest_cover → urban_flooding (I9): AFFECTS w=0.7 pol=-1 MEDIUM_TERM — "Loss of forest cover eliminates natural water absorption, increasing surface runoff and flood severity"
3. forest_cover → drinking_water_quality (I2): AFFECTS w=0.7 pol=-1 LONG_TERM — "Forests filter watershed sediment; deforestation degrades downstream drinking water quality"
4. forest_cover → wildlife_encounters (I8): AFFECTS w=0.6 pol=1 MEDIUM_TERM — "Habitat loss pushes wildlife into human settlements"
5. peninsular_river_systems → municipal_water_supply (I2): SUPPLIES w=0.9 pol=1 SHORT_TERM — "Krishna, Godavari, Kaveri rivers supply municipal water to southern cities"
6. peninsular_river_systems → drinking_water_quality (I2): SUPPLIES w=0.8 pol=1 SHORT_TERM — "River water quality determines piped drinking water quality"
7. peninsular_river_systems → farm_labor_wages (I4): AFFECTS w=0.65 pol=1 MEDIUM_TERM — "Irrigation from peninsular rivers sustains farm employment"
8. indian_plate_interior → structural_collapse (I8): DISRUPTS w=0.6 pol=1 IMMEDIATE — "Intraplate earthquakes collapse poorly-built structures (Koyna 1967, Latur 1993)"
9. indian_plate_interior → residential_power_supply (I2): DISRUPTS w=0.5 pol=-1 IMMEDIATE — "Seismic events damage local power substations"
10. northeast_monsoon → agricultural_crop_damage (I4): AFFECTS w=0.8 pol=-1 SHORT_TERM — "NE monsoon rains hydrate Tamil Nadu/Andhra rabi crops, preventing drought"
11. northeast_monsoon → urban_flooding (I9): PRODUCES w=0.85 pol=1 IMMEDIATE — "Intense NE monsoon causes Chennai-type urban flooding"
12. groundwater_aquifers → drinking_water_quality (I2): SUPPLIES w=0.85 pol=1 SHORT_TERM — "Aquifers supply drinking water to rural India via borewells/handpumps"
13. groundwater_aquifers → residential_borewells (I2): SUPPLIES w=0.9 pol=1 SHORT_TERM — "Aquifer water table determines if residential borewells produce water"
14. cyclonic_storm_systems → structural_collapse (I8): DISRUPTS w=0.75 pol=1 IMMEDIATE — "Cyclonic winds collapse kutcha/semi-pucca coastal housing"
15. cyclonic_storm_systems → domestic_flight_ticket (I3): DISRUPTS w=0.7 pol=1 IMMEDIATE — "Cyclones force coastal airport closures, cancelling flights"
16. himalayan_tectonic_plates → structural_collapse (I8): DISRUPTS w=0.85 pol=1 IMMEDIATE — "Himalayan seismic activity causes building collapses in north India"
17. migratory_pest_populations → agricultural_crop_damage (I4): DISRUPTS w=0.85 pol=1 SHORT_TERM — "Desert locust swarms destroy standing crops"

#### T2 Institutional → I-world bridges:

18. high_courts → criminal_litigation_risk (I8): AFFECTS w=0.7 pol=-1 MEDIUM_TERM — "High court bail orders and sentencing directly determine criminal litigation outcomes"
19. high_courts → residential_rent (I2): REGULATES w=0.55 pol=1 LONG_TERM — "High court rent control rulings shape rental terms"
20. rera → residential_rent (I2): REGULATES w=0.7 pol=1 MEDIUM_TERM — "RERA compliance raises builder costs passed to buyers"
21. rera → building_materials_cost (I2): AFFECTS w=0.55 pol=1 MEDIUM_TERM — "RERA quality mandates increase demand for certified materials"
22. european_union → it_sector_jobs (I4): AFFECTS w=0.55 pol=-1 MEDIUM_TERM — "EU GDPR/AI regulations constrain Indian IT outsourcing"

#### T3 Market / T2 Institutional → T-world or I-world:

23. imf → india_10yr_bond_yield (T3): AFFECTS w=0.65 pol=1 SHORT_TERM — "IMF assessments influence sovereign credit perception, moving bond yields"
24. bank_liquidity_and_credit → home_loan_emi (I5): AFFECTS w=0.8 pol=-1 SHORT_TERM — "Tight liquidity raises MCLR, increasing home loan EMIs"
25. bank_liquidity_and_credit → personal_loan_emi (I5): AFFECTS w=0.75 pol=-1 SHORT_TERM — "Credit squeeze raises unsecured lending rates"
26. wto → it_sector_jobs (I4): AFFECTS w=0.5 pol=1 LONG_TERM — "WTO services liberalization expands Indian IT export market access"

#### T5 Social → I-world bridges:

27. regional_new_year_festivals → retail_gold_investment (I5): AFFECTS w=0.6 pol=1 SHORT_TERM — "Gold purchases spike during Ugadi/Puthandu/Vishu/Bihu"
28. regional_new_year_festivals → irctc_train_ticket (I3): AFFECTS w=0.65 pol=1 IMMEDIATE — "Mass hometown travel during regional new years spikes train demand"
"""

PROMPT_TEMPLATE = """You are a graph quality auditor for an Indian causal impact knowledge graph.

## Constitution (Key Rules)

{constitution_excerpt}

## Task

Review 28 proposed causal edges. For EACH edge, apply these checks:

### Check 1: Rule 21 (Bypassing Test)
Articulate the exact mechanism from A→B. Does the explanation REQUIRE mentioning a third node C that exists or should exist in this taxonomy? If so, the edge is INVALID — the signal should go A→C→B instead.

Common bypassing patterns to watch for:
- "Forest cover affects air quality" — does it go via particulate_matter or some intermediate?
- "Aquifers supply drinking water" — does it go via borewells/handpumps first?
- "IMF affects bond yields" — does it go via RBI/credit_rating first?
- "Bank liquidity affects EMI" — does it go via RBI repo rate first?

### Check 2: Edge Type Priority
Is AFFECTS used where a more specific type fits?
Priority: PRODUCES > SUPPLIES > FUNDS > DISRUPTS > REGULATES > EMPLOYS > MANAGES > DEPENDS_ON > COMPETES_WITH > AFFECTS

### Check 3: Existing Path Coverage
Given the source node context above, could this target already be reached via existing T→T chains + existing bridges? If yes, is the direct bridge still justified (shorter path = better signal)?

### Check 4: Weight & Polarity
Is the weight reasonable for the mechanism described? Is the polarity correct?

### Check 5: Missing Intermediate Edges
Would it be better to add an intermediate edge instead? For example, instead of cyclone → structural_collapse, should we add cyclone → housing_damage → structural_collapse?

## Output Format

For EACH of the 28 edges, respond with ONE of:

**APPROVE**: Edge #N source → target — Direct mechanism valid. [Optional: suggest weight/type adjustment]

**REJECT**: Edge #N source → target — Rule 21 violation. Signal goes source → intermediary → target. [Suggest the correct intermediate edge instead]

**MODIFY**: Edge #N source → target — Approve with changes: [new type/weight/polarity/target]. Reason: ...

**REDUNDANT**: Edge #N source → target — Already reachable via [existing path]. Direct bridge not needed unless [condition].

After reviewing all 28, provide a SUMMARY:
- How many approved, rejected, modified, redundant
- Any edges you'd ADD that weren't proposed (critical gaps you noticed)
- Overall quality assessment of the batch
"""

def main():
    # Read constitution excerpt (Rules 18, 20, 21 sections)
    constitution = TAXONOMY_MD.read_text()

    # Extract relevant rules
    lines = constitution.split('\n')
    excerpt_lines = []
    in_rule = False
    for i, line in enumerate(lines):
        if 'Rule 18' in line or 'Rule 20' in line or 'Rule 21' in line:
            in_rule = True
        if in_rule:
            excerpt_lines.append(line)
            # End when next rule starts (### Rule) or --- separator
            if i > 0 and (line.strip() == '---' or (line.startswith('### Rule') and not any(r in line for r in ['Rule 18', 'Rule 20', 'Rule 21']))):
                in_rule = False
                excerpt_lines.append('')

    constitution_excerpt = '\n'.join(excerpt_lines)

    prompt = PROMPT_TEMPLATE.format(constitution_excerpt=constitution_excerpt)
    prompt += "\n\n" + PROPOSED_EDGES

    print(f"Prompt length: {len(prompt)} chars")
    print("Calling Gemini 3.1 Pro Preview for edge review...")

    gemini = GraphGemini()
    response = gemini.call(prompt, thinking_budget=24000)

    # Save response
    out_path = PROJECT_ROOT / "taxonomy" / "eval_results" / "phase4b_edge_review.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(response)
    print(f"\nResponse saved to {out_path}")
    print("\n" + response)


if __name__ == "__main__":
    main()
