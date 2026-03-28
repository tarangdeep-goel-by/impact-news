"""Propose fixes for all structural breaks across scenarios + canaries.

Usage:
    python3 scripts/propose_all_fixes.py
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

After a quality pass that killed 133 Rule 21-violating edges, we have 20 structural breaks across our scenario and canary test suites. For each break, the trigger node cannot reach the target node through the causal graph.

Your job: for each break, determine the MINIMUM fix — whether that's a new intermediary node, a direct edge between existing nodes, or adding edges to an underconnected existing node. Follow Rule 21 strictly.

## The 20 Structural Breaks

### Break 1: southwest_monsoon (T1-L4) → retail_rice (I1-L3)
**Trigger outgoing (8):** urban_flooding PRODUCES, agricultural_crop_damage AFFECTS, traffic_congestion PRODUCES, stagnant_water_pools PRODUCES, road_potholes PRODUCES, peninsular_river_systems SUPPLIES, groundwater_aquifers SUPPLIES, highway_network DISRUPTS
**Target incoming (3):** public_distribution_system SUPPLIES, agricultural_exports AFFECTS, millets COMPETES_WITH
**Analysis:** Monsoon reaches agricultural_crop_damage but crop_damage has no path to retail_rice. The old killed edge was monsoon→global_food_grain_supply (bypassing via crop yield). Crop damage should logically affect food grain supply or rice directly.

### Break 2: himalayan_glaciers (T1-L4) → structural_collapse (I8-L4)
**Trigger outgoing (1):** himalayan_river_systems SUPPLIES
**Target incoming (4):** cyclonic_storm_systems PRODUCES, himalayan_tectonic_plates PRODUCES, indian_plate_interior PRODUCES, fire_hazards PRODUCES
**Analysis:** Glaciers only reach river systems. The canary expects glaciers → structural_collapse via glacial lake outburst floods (GLOFs) or landslides. Is this a legitimate causal chain or should the canary be updated?

### Break 3: fssai (T2-L4) → nutritional_supplements (I6-L4)
**Trigger outgoing (1):** street_food AFFECTS
**Target incoming (1):** maternity_services PRODUCES
**Analysis:** FSSAI regulates food safety including supplements. Currently only has 1 outgoing edge (to street_food). Needs bridge to nutritional_supplements.

### Break 4: ministry_of_education (T2-L4) → cbse_exams (I7-L4)
**Trigger outgoing (1):** university_entrance AFFECTS
**Target incoming (1):** private_schools SUPPLIES
**Analysis:** Ministry directly controls CBSE. Currently only bridges to university_entrance. Severely underconnected.

### Break 5: ministry_of_education (T2-L4) → mid_day_meal (I7-L4)
**Trigger outgoing (1):** university_entrance AFFECTS
**Target incoming (4):** liquid_milk SUPPLIES, retail_rice SUPPLIES, poultry_eggs SUPPLIES, tur_dal SUPPLIES
**Analysis:** Ministry directly funds and administers mid-day meal scheme. Missing bridge.

### Break 6: international_gold_prices (T3-L4) → wedding_planning_service (I11-L4)
**Trigger outgoing (2):** retail_gold_investment AFFECTS, india_trade_deficit AFFECTS
**Target incoming (1):** wedding_season_aggregate AFFECTS
**Analysis:** Gold prices affect wedding budgets because gold is a major wedding expense in India. But the path gold→retail_gold_investment→???→wedding_planning_service has no link. Does retail_gold_investment affect wedding costs? Or does this go via wedding_season_aggregate?

### Break 7: national_unemployment_rate (T3-L4) → it_sector_jobs (I4-L4)
**Trigger outgoing (1):** skilled_emigration AFFECTS
**Target incoming (3):** us_government AFFECTS, it_services_exports FUNDS, engineering_education SUPPLIES
**Analysis:** Unemployment rate has only 1 causal outgoing edge. Severely underconnected for a major macro indicator. Should have edges to employment nodes.

### Break 8: national_unemployment_rate (T3-L4) → mgnrega_wages (I4-L4)
**Same trigger context as Break 7.**
**Analysis:** High unemployment → more MGNREGA demand. But unemployment rate doesn't connect to mgnrega.

### Break 9: national_power_grid (T4-L3) → small_factory_owner_income (I4-L4)
**Trigger outgoing (1):** power_substations SUPPLIES
**Target incoming (0):** NO causal incoming edges at all
**Analysis:** small_factory_owner_income has zero incoming causal edges — it's completely disconnected. Power grid failures should affect MSME income via power supply disruptions.

### Break 10: autumn_festive_season (T5-L4) → intercity_bus_fare (I3-L4)
**Trigger outgoing (9):** retail_sugar, firecracker, event_noise, puja_pandal, festive_idol, crowd_emergencies, butter_and_ghee, irctc_train_ticket AFFECTS + PRODUCES
**Target incoming (2):** retail_diesel AFFECTS, highway_toll_fare AFFECTS
**Analysis:** Festive season drives massive intercity travel. Has edge to irctc_train_ticket but not intercity_bus_fare. Direct bridge needed?

### Break 11: rural_urban_migration_corridors (T5-L4) → domestic_help_wages (I4-L4)
**Trigger outgoing (2):** pg_and_hostel_fees AFFECTS, urban_population_density PRODUCES
**Target incoming (1):** female_labor_force_participation AFFECTS
**Analysis:** Rural-urban migration supplies domestic help labor pool, affecting wages. Missing bridge.

### Break 12: upi_and_bank_scams (I8-L4) → personal_data_privacy (I10-L4)
**Trigger outgoing (3):** savings_account_balance DISRUPTS, fir_registration PRODUCES, upi_transaction_limits AFFECTS
**Target incoming (1):** data_breaches_and_leaks DISRUPTS
**Analysis:** Scams compromise personal data. Does scam → personal_data_privacy need an intermediary (data_breaches_and_leaks exists and feeds into it)?

### Break 13: engineering_education (I7-L4) → personal_loan_emi (I5-L4)
**Trigger outgoing (2):** it_sector_jobs SUPPLIES, college_university_fees PRODUCES
**Target incoming (2):** monetary_policy_committee AFFECTS, commercial_bank_lending_rates AFFECTS
**Analysis:** Engineering education costs drive education loans → personal loan EMIs. The path should go via college_university_fees → education_loan → personal_loan_emi. Does education_loan exist?

### Break 14: engineering_education (I7-L4) → private_tutors (I7-L4)
**Trigger outgoing (2):** it_sector_jobs SUPPLIES, college_university_fees PRODUCES
**Target incoming (1):** k12_edtech COMPETES_WITH
**Analysis:** Engineering entrance exam pressure drives demand for private tutors. Is this a direct edge?

### Break 15: wpi (T3-L4) → minimum_wage (I4-L4)
**Trigger outgoing (3):** kirana_store_income AFFECTS, monetary_policy_committee AFFECTS, india_10yr_bond_yield AFFECTS
**Target incoming (0):** NO causal incoming edges
**Analysis:** minimum_wage has zero incoming edges — completely disconnected. WPI/inflation should affect minimum wage revisions. Also CPI feeds wage revisions.

### Break 16: southwest_monsoon (T1-L4) → mgnrega_wages (I4-L4)
**Same trigger context as Break 1.**
**Analysis:** Monsoon failure → crop damage → rural distress → MGNREGA demand spike. The path monsoon → agricultural_crop_damage exists. Need: agricultural_crop_damage → mgnrega_wages (is this direct or via rural_unemployment?).

### Break 17: brent_crude (T3-L4) → domestic_flight_ticket (I3-L4)
**Trigger outgoing (5):** retail_petrol SUPPLIES, retail_diesel SUPPLIES, lpg_cylinder SUPPLIES, india_trade_deficit AFFECTS, wpi AFFECTS
**Target incoming (2):** dgca AFFECTS, commercial_airports AFFECTS
**Analysis:** Brent crude → aviation turbine fuel → flight ticket price. ATF doesn't exist in graph. Need intermediary.

### Break 18: autumn_festive_season (T5-L4) → wedding_venue (I11-L4)
**Same trigger context as Break 10.**
**Target incoming (3):** wedding_season_aggregate AFFECTS, fine_dining_restaurants SUPPLIES, wedding_planning_service FUNDS
**Analysis:** Festive season (Oct-Dec) overlaps with wedding season. Does autumn_festive_season directly affect wedding_venue, or does this go via wedding_season_aggregate?

### Break 19: wpi (T3-L4) → aggregate_consumer_confidence (T5-L4)
**Same trigger context as Break 15.**
**Target incoming (1):** autumn_festive_season AFFECTS
**Analysis:** Wholesale inflation → consumer price perception → consumer confidence. Need CPI intermediary?

### Break 20: gst_council (T2-L4) → biscuits_and_snacks (I1-L3)
**Trigger outgoing (2):** indirect_taxes AFFECTS, wpi AFFECTS
**Target incoming (5):** wheat_flour SUPPLIES, retail_sugar SUPPLIES, palm_oil SUPPLIES, poultry_eggs SUPPLIES, retail_salt SUPPLIES
**Analysis:** gst_council → indirect_taxes (I5-L3) but indirect_taxes has 0 outgoing edges. GST rate changes directly affect FMCG prices. Fix: add edges from indirect_taxes.

## Instructions

For each of the 20 breaks, provide ONE of these verdicts:

**NEW_NODE**: An intermediary node is needed. Provide:
- Node spec: id, name, parent, level, category, aliases
- Rule 5 check: matchable, mappable, edgeable
- Two edges: A→new_node and new_node→B with full specs

**DIRECT_EDGE**: A direct edge between existing nodes fixes this. Provide:
- Edge spec: from, to, type, weight, polarity, delay, description
- Rule 21 justification: why this is direct (no intermediary needed)

**ADD_EDGES**: An existing underconnected node needs more outgoing edges. Provide:
- Which node needs edges
- Edge specs for each new edge

**UPDATE_CANARY**: The canary expectation is wrong — the causal chain doesn't hold in reality. Provide:
- Why the chain is invalid
- Suggested canary update (different target, or remove)

**NO_FIX**: Legitimate gap that can't be fixed without creating taxonomy bloat.

## Output Format

For each break:
```
### Break N: trigger → target
**VERDICT**: [NEW_NODE / DIRECT_EDGE / ADD_EDGES / UPDATE_CANARY / NO_FIX]
[specs...]
```

End with a COMPLETE SUMMARY in YAML:
```yaml
new_nodes:
- id: ...
  ...
new_edges:
- from: ...
  ...
canary_updates:
- id: ...
  ...
```
"""


def main():
    constitution = TAXONOMY_MD.read_text()
    prompt = PROMPT.format(constitution=constitution)

    print(f"Prompt length: {len(prompt)} chars")
    print("Calling Gemini 3.1 Pro Preview...")

    gemini = GraphGemini()
    response = gemini.call(prompt, thinking_budget=32000, max_output_tokens=65000)

    out_path = PROJECT_ROOT / "taxonomy" / "eval_results" / "all_structural_fixes.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(response)
    print(f"\nResponse saved to {out_path}")
    print("\n" + response)


if __name__ == "__main__":
    main()
