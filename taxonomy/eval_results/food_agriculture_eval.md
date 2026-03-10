```yaml
missing_edges:
  - from: el_nino
    to: monsoon
    type: DISRUPTS
    description: "El Niño events severely disrupt the Southwest Monsoon, leading to droughts and reduced kharif crop yields in India."
    severity: P0
  - from: reservoir_levels
    to: rabi_crops
    type: AFFECTS
    description: "Winter (Rabi) crops like wheat and mustard depend heavily on post-monsoon reservoir levels and residual soil moisture."
    severity: P0
  - from: mgnrega
    to: farm_labor
    type: COMPETES_WITH
    description: "The MGNREGA rural employment guarantee scheme sets a wage floor and competes with agricultural labor availability during peak sowing/harvesting seasons."
    severity: P1
  - from: free_electricity_policy
    to: groundwater
    type: AFFECTS
    description: "State-level free electricity policies for farmers incentivize excessive pumping, leading to severe groundwater depletion in Punjab and Haryana."
    severity: P1
  - from: farmer_income
    to: rural_demand
    type: AFFECTS
    description: "Agricultural output and MSP directly determine farmer income, which drives rural demand for FMCG, tractors, and two-wheelers."
    severity: P0

incorrect_edges:
  - from: crop_insurance
    to: monsoon_forecast
    issue: "Direction and concept are wrong. Crop insurance claims depend on actual monsoon failure, not the forecast. The edge should be from 'monsoon' to 'crop_insurance' with type AFFECTS."
  - from: indonesia_coal
    to: indonesia_palm_oil
    issue: "Type is LOCATED_IN and description notes 'same country risk'. This is not a valid causal relationship in a causal graph. They share a geographical dependency, but coal does not cause/affect palm oil directly here."

missing_nodes:
  - id: el_nino
    aliases: ["El Nino", "La Nina", "ENSO"]
    category: "climate"
    why: "The single largest macroeconomic climate risk to Indian agriculture and food inflation."
  - id: reservoir_levels
    aliases: ["dam levels", "water reserves", "CWC reservoir data"]
    category: "water_infrastructure"
    why: "Critical determinant for India's winter (Rabi) crop production, distinct from direct monsoon rainfall."
  - id: farmer_income
    aliases: ["agricultural income", "farm profitability", "rural income"]
    category: "agriculture_and_farming"
    why: "The ultimate socio-economic outcome of this entire domain, linking agriculture to the broader Indian economy."
  - id: mgnrega
    aliases: ["NREGA", "rural employment guarantee"]
    category: "food_policy"
    why: "Currently listed as an alias for 'farm_labor', but it is actually a distinct government policy that heavily impacts farm labor availability and rural wage inflation."

duplicate_nodes:
  - keep: food_inflation_india
    merge: food_inflation
  - keep: food_waste
    merge: food_wastage
  - keep: cold_storage
    merge: cold_chain
  - keep: cold_storage
    merge: cold_chain_logistics
  - keep: poultry_industry
    merge: poultry_farming
  - keep: wheat
    merge: wheat_grain
  - keep: milk
    merge: fresh_milk
  - keep: corn
    merge: corn_grain
  - keep: corn
    merge: maize_corn

description_issues:
  - from: indonesia_coal
    to: indonesia_palm_oil
    issue: "Description 'Indonesia exports both coal and palm oil — same country risk' describes a correlation/shared attribute, not a causal mechanism."
  - from: agriculture_sector
    to: food_inflation
    issue: "Description is slightly generic. Could be improved to reflect that agriculture sector output shocks (supply side) are the primary driver of CPI volatility in India."
  - from: multiple (e.g., rice -> basmati_rice)
    to: multiple
    issue: "Over 50 'CONTAINS' edges have no descriptions. While standard for ontologies, adding brief context (e.g., 'Basmati is a premium export-oriented rice variety') would improve LLM context."

scores:
  completeness: 8
  accuracy: 8
  granularity: 7
  india_specificity: 9
  overall: 8.0
```