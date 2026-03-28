Here is the analysis and resolution for each of the 20 structural breaks, strictly applying the Direct Causation Principle (Rule 21) and the Taxonomy Constitution.

### Break 1: southwest_monsoon (T1-L4) → retail_rice (I1-L3)
**VERDICT**: DIRECT_EDGE
**Edge spec**: 
- from: `agricultural_crop_damage`
- to: `retail_rice`
- type: `AFFECTS`
- weight: 0.8
- polarity: +1
- delay: MEDIUM_TERM
- description: "Agricultural crop damage directly reduces the harvest yield of paddy, restricting market supply and driving up the retail price of rice."
**Rule 21 justification**: The physical destruction of the crop is the direct mechanism that restricts supply and raises the retail price. No further intermediary is needed.

### Break 2: himalayan_glaciers (T1-L4) → structural_collapse (I8-L4)
**VERDICT**: UPDATE_CANARY
**Reason**: Himalayan glaciers melting primarily affects northern river systems. A 4-hop chain to a generic `structural_collapse` node is too tenuous, low-probability for the average citizen, and bypasses specific regional flood mechanics. 
**Suggested update**: Change canary target to `himalayan_river_systems` or remove entirely.

### Break 3: fssai (T2-L4) → nutritional_supplements (I6-L4)
**VERDICT**: DIRECT_EDGE
**Edge spec**:
- from: `fssai`
- to: `nutritional_supplements`
- type: `AFFECTS`
- weight: 0.7
- polarity: +1
- delay: MEDIUM_TERM
- description: "FSSAI directly sets formulation, safety, and labeling standards for nutritional supplements, affecting their compliance costs and market availability."
**Rule 21 justification**: FSSAI is the direct regulatory authority over food supplements. (Note: `REGULATES` cannot be used as it is a cross-world T→I edge per Rule 12b, so `AFFECTS` is the correct fallback).

### Break 4: ministry_of_education (T2-L4) → cbse_exams (I7-L4)
**VERDICT**: DIRECT_EDGE
**Edge spec**:
- from: `ministry_of_education`
- to: `cbse_exams`
- type: `AFFECTS`
- weight: 0.9
- polarity: +1
- delay: SHORT_TERM
- description: "The Ministry of Education directly sets policies, syllabus frameworks, and operational guidelines for CBSE board exams."
**Rule 21 justification**: The Ministry has direct administrative control over the CBSE board.

### Break 5: ministry_of_education (T2-L4) → mid_day_meal (I7-L4)
**VERDICT**: DIRECT_EDGE
**Edge spec**:
- from: `ministry_of_education`
- to: `mid_day_meal`
- type: `FUNDS`
- weight: 0.9
- polarity: +1
- delay: SHORT_TERM
- description: "The Ministry of Education directly allocates the budget and administers the PM POSHAN (Mid-Day Meal) scheme."
**Rule 21 justification**: Direct financial backing fits the `FUNDS` edge type perfectly.

### Break 6: international_gold_prices (T3-L4) → wedding_planning_service (I11-L4)
**VERDICT**: UPDATE_CANARY
**Reason**: International gold prices affect `retail_gold_investment` (jewelry), but do not directly change the cost or demand for `wedding_planning_service` (which is driven by labor, venue, and event scale). The canary conflates "wedding jewelry budget" with "wedding planner fees".
**Suggested update**: Change canary target to `retail_gold_investment`.

### Break 7: national_unemployment_rate (T3-L4) → it_sector_jobs (I4-L4)
**VERDICT**: UPDATE_CANARY
**Reason**: `national_unemployment_rate` is an aggregate lagging indicator, not a causal driver of IT sector jobs. Both are driven by macro factors (e.g., GDP, US Fed rates). Expecting a causal path from an aggregate metric to a specific sector violates direct causation (Rule 21) and Rule 7 (no feedback loops from aggregates).
**Suggested update**: Remove canary.

### Break 8: national_unemployment_rate (T3-L4) → mgnrega_wages (I4-L4)
**VERDICT**: DIRECT_EDGE
**Edge spec**:
- from: `national_unemployment_rate`
- to: `mgnrega_wages`
- type: `AFFECTS`
- weight: 0.8
- polarity: +1
- delay: SHORT_TERM
- description: "Higher national unemployment reflects severe job scarcity, directly driving rural labor to demand more MGNREGA work and triggering higher wage allocations."
**Rule 21 justification**: While an aggregate metric, high unemployment statutorily and behaviorally triggers employment guarantee fund utilization.

### Break 9: national_power_grid (T4-L3) → small_factory_owner_income (I4-L4)
**VERDICT**: ADD_EDGES
**Node needing edges**: `power_substations` (T4-L4)
**Edge spec**:
- from: `power_substations`
- to: `small_factory_owner_income`
- type: `AFFECTS`
- weight: 0.8
- polarity: +1
- delay: SHORT_TERM
- description: "Stable power supply from local substations ensures continuous factory operations, directly supporting MSME owner income and preventing downtime losses."

### Break 10: autumn_festive_season (T5-L4) → intercity_bus_fare (I3-L4)
**VERDICT**: DIRECT_EDGE
**Edge spec**:
- from: `autumn_festive_season`
- to: `intercity_bus_fare`
- type: `AFFECTS`
- weight: 0.8
- polarity: +1
- delay: IMMEDIATE
- description: "The autumn festive season triggers massive migrant travel home, causing intercity private bus operators to surge ticket prices."
**Rule 21 justification**: The festival directly causes the demand surge that operators use to hike fares.

### Break 11: rural_urban_migration_corridors (T5-L4) → domestic_help_wages (I4-L4)
**VERDICT**: DIRECT_EDGE
**Edge spec**:
- from: `rural_urban_migration_corridors`
- to: `domestic_help_wages`
- type: `AFFECTS`
- weight: 0.7
- polarity: -1
- delay: MEDIUM_TERM
- description: "Increased rural-urban migration expands the urban informal labor pool, putting downward pressure on domestic help wages due to oversupply."
**Rule 21 justification**: Migration directly supplies the labor pool for this specific sector.

### Break 12: upi_and_bank_scams (I8-L4) → personal_data_privacy (I10-L4)
**VERDICT**: DIRECT_EDGE
**Edge spec**:
- from: `upi_and_bank_scams`
- to: `personal_data_privacy`
- type: `DISRUPTS`
- weight: 0.8
- polarity: -1
- delay: IMMEDIATE
- description: "Financial scams often involve phishing and credential theft, directly compromising the victim's personal data privacy."
**Rule 21 justification**: The scam itself is the mechanism of privacy violation.

### Break 13: engineering_education (I7-L4) → personal_loan_emi (I5-L4)
**VERDICT**: DIRECT_EDGE
**Edge spec**:
- from: `college_university_fees`
- to: `personal_loan_emi`
- type: `AFFECTS`
- weight: 0.7
- polarity: +1
- delay: MEDIUM_TERM
- description: "High engineering and university fees frequently force parents to take unsecured personal loans, directly increasing their EMI burden."
**Rule 21 justification**: The fee payment is the direct catalyst for taking the loan. (Avoids creating a redundant `education_loan` node if personal loans cover the financial burden).

### Break 14: engineering_education (I7-L4) → private_tutors (I7-L4)
**VERDICT**: DIRECT_EDGE
**Edge spec**:
- from: `engineering_education`
- to: `private_tutors`
- type: `AFFECTS`
- weight: 0.8
- polarity: +1
- delay: SHORT_TERM
- description: "The highly competitive nature of engineering entrance exams directly drives student demand for private tutoring and coaching."
**Rule 21 justification**: The education track directly creates the demand for the supplementary service.

### Break 15: wpi (T3-L4) → minimum_wage (I4-L4)
**VERDICT**: NEW_NODE
**Node spec**:
- id: `retail_inflation_cpi`
- name: "Retail Inflation (CPI)"
- parent: `macroeconomic_indices` (T3-L3)
- level: L4
- category: T3
- aliases: ["consumer price index", "CPI"]
- Rule 5 check: Matchable (Yes, headline staple), Mappable (Yes), Edgeable (Yes, drives wages and rates).
**Edges**:
1. `wpi` → `retail_inflation_cpi` (type: `AFFECTS`, weight: 0.8, polarity: +1, delay: SHORT_TERM, description: "Wholesale price increases are passed down the supply chain to consumer retail prices.")
2. `retail_inflation_cpi` → `minimum_wage` (type: `AFFECTS`, weight: 0.9, polarity: +1, delay: MEDIUM_TERM, description: "CPI directly dictates the Dearness Allowance (DA) and statutory minimum wage revisions.")

### Break 16: southwest_monsoon (T1-L4) → mgnrega_wages (I4-L4)
**VERDICT**: DIRECT_EDGE
**Edge spec**:
- from: `agricultural_crop_damage`
- to: `mgnrega_wages`
- type: `AFFECTS`
- weight: 0.8
- polarity: +1
- delay: SHORT_TERM
- description: "Crop damage destroys agricultural livelihoods, forcing rural workers to fall back on MGNREGA, spiking wage demand."
**Rule 21 justification**: The loss of the crop is the direct catalyst for seeking alternative state employment.

### Break 17: brent_crude (T3-L4) → domestic_flight_ticket (I3-L4)
**VERDICT**: NEW_NODE
**Node spec**:
- id: `aviation_turbine_fuel`
- name: "Aviation Turbine Fuel (ATF)"
- parent: `energy_commodities` (T3-L3)
- level: L4
- category: T3
- aliases: ["jet fuel", "ATF prices"]
- Rule 5 check: Matchable (Yes), Mappable (Yes), Edgeable (Yes).
**Edges**:
1. `brent_crude` → `aviation_turbine_fuel` (type: `SUPPLIES`, weight: 0.9, polarity: +1, delay: SHORT_TERM, description: "Brent crude is directly refined into aviation turbine fuel, dictating its base cost.")
2. `aviation_turbine_fuel` → `domestic_flight_ticket` (type: `AFFECTS`, weight: 0.8, polarity: +1, delay: IMMEDIATE, description: "ATF constitutes ~40% of airline operating costs, directly driving domestic flight ticket pricing.")

### Break 18: autumn_festive_season (T5-L4) → wedding_venue (I11-L4)
**VERDICT**: ADD_EDGES
**Node needing edges**: `autumn_festive_season`
**Edge spec**:
- from: `autumn_festive_season`
- to: `wedding_season_aggregate`
- type: `AFFECTS`
- weight: 0.9
- polarity: +1
- delay: IMMEDIATE
- description: "The autumn festive calendar (e.g., Dev Uthani Ekadashi) directly dictates the start of the auspicious Hindu wedding season."
*(Note: `wedding_season_aggregate` already connects to `wedding_venue`, so this completes the path).*

### Break 19: wpi (T3-L4) → aggregate_consumer_confidence (T5-L4)
**VERDICT**: ADD_EDGES
**Node needing edges**: `retail_inflation_cpi` (Created in Break 15)
**Edge spec**:
- from: `retail_inflation_cpi`
- to: `aggregate_consumer_confidence`
- type: `AFFECTS`
- weight: 0.8
- polarity: -1
- delay: SHORT_TERM
- description: "High retail inflation erodes household purchasing power, directly lowering aggregate consumer confidence."

### Break 20: gst_council (T2-L4) → biscuits_and_snacks (I1-L3)
**VERDICT**: ADD_EDGES
**Node needing edges**: `indirect_taxes` (I5-L3)
**Edge spec**:
- from: `indirect_taxes`
- to: `biscuits_and_snacks`
- type: `AFFECTS`
- weight: 0.9
- polarity: +1
- delay: IMMEDIATE
- description: "Changes in indirect tax rates (GST) are directly passed on to the retail prices of FMCG goods like biscuits and snacks."

---

### COMPLETE SUMMARY

```yaml
new_nodes:
  - id: retail_inflation_cpi
    name: "Retail Inflation (CPI)"
    parent: macroeconomic_indices
    level: L4
    category: T3
    aliases: ["consumer price index", "CPI"]
    matchable: true
    mappable: true
    edgeable: true

  - id: aviation_turbine_fuel
    name: "Aviation Turbine Fuel (ATF)"
    parent: energy_commodities
    level: L4
    category: T3
    aliases: ["jet fuel", "ATF prices"]
    matchable: true
    mappable: true
    edgeable: true

new_edges:
  - from: agricultural_crop_damage
    to: retail_rice
    type: AFFECTS
    weight: 0.8
    polarity: 1
    delay: MEDIUM_TERM
    description: "Agricultural crop damage directly reduces the harvest yield of paddy, restricting market supply and driving up the retail price of rice."

  - from: fssai
    to: nutritional_supplements
    type: AFFECTS
    weight: 0.7
    polarity: 1
    delay: MEDIUM_TERM
    description: "FSSAI directly sets formulation, safety, and labeling standards for nutritional supplements, affecting their compliance costs and market availability."

  - from: ministry_of_education
    to: cbse_exams
    type: AFFECTS
    weight: 0.9
    polarity: 1
    delay: SHORT_TERM
    description: "The Ministry of Education directly sets policies, syllabus frameworks, and operational guidelines for CBSE board exams."

  - from: ministry_of_education
    to: mid_day_meal
    type: FUNDS
    weight: 0.9
    polarity: 1
    delay: SHORT_TERM
    description: "The Ministry of Education directly allocates the budget and administers the PM POSHAN (Mid-Day Meal) scheme."

  - from: national_unemployment_rate
    to: mgnrega_wages
    type: AFFECTS
    weight: 0.8
    polarity: 1
    delay: SHORT_TERM
    description: "Higher national unemployment reflects severe job scarcity, directly driving rural labor to demand more MGNREGA work and triggering higher wage allocations."

  - from: power_substations
    to: small_factory_owner_income
    type: AFFECTS
    weight: 0.8
    polarity: 1
    delay: SHORT_TERM
    description: "Stable power supply from local substations ensures continuous factory operations, directly supporting MSME owner income and preventing downtime losses."

  - from: autumn_festive_season
    to: intercity_bus_fare
    type: AFFECTS
    weight: 0.8
    polarity: 1
    delay: IMMEDIATE
    description: "The autumn festive season triggers massive migrant travel home, causing intercity private bus operators to surge ticket prices."

  - from: rural_urban_migration_corridors
    to: domestic_help_wages
    type: AFFECTS
    weight: 0.7
    polarity: -1
    delay: MEDIUM_TERM
    description: "Increased rural-urban migration expands the urban informal labor pool, putting downward pressure on domestic help wages due to oversupply."

  - from: upi_and_bank_scams
    to: personal_data_privacy
    type: DISRUPTS
    weight: 0.8
    polarity: -1
    delay: IMMEDIATE
    description: "Financial scams often involve phishing and credential theft, directly compromising the victim's personal data privacy."

  - from: college_university_fees
    to: personal_loan_emi
    type: AFFECTS
    weight: 0.7
    polarity: 1
    delay: MEDIUM_TERM
    description: "High engineering and university fees frequently force parents to take unsecured personal loans, directly increasing their EMI burden."

  - from: engineering_education
    to: private_tutors
    type: AFFECTS
    weight: 0.8
    polarity: 1
    delay: SHORT_TERM
    description: "The highly competitive nature of engineering entrance exams directly drives student demand for private tutoring and coaching."

  - from: wpi
    to: retail_inflation_cpi
    type: AFFECTS
    weight: 0.8
    polarity: 1
    delay: SHORT_TERM
    description: "Wholesale price increases are passed down the supply chain to consumer retail prices."

  - from: retail_inflation_cpi
    to: minimum_wage
    type: AFFECTS
    weight: 0.9
    polarity: 1
    delay: MEDIUM_TERM
    description: "CPI directly dictates the Dearness Allowance (DA) and statutory minimum wage revisions."

  - from: agricultural_crop_damage
    to: mgnrega_wages
    type: AFFECTS
    weight: 0.8
    polarity: 1
    delay: SHORT_TERM
    description: "Crop damage destroys agricultural livelihoods, forcing rural workers to fall back on MGNREGA, spiking wage demand."

  - from: brent_crude
    to: aviation_turbine_fuel
    type: SUPPLIES
    weight: 0.9
    polarity: 1
    delay: SHORT_TERM
    description: "Brent crude is directly refined into aviation turbine fuel, dictating its base cost."

  - from: aviation_turbine_fuel
    to: domestic_flight_ticket
    type: AFFECTS
    weight: 0.8
    polarity: 1
    delay: IMMEDIATE
    description: "ATF constitutes ~40% of airline operating costs, directly driving domestic flight ticket pricing."

  - from: autumn_festive_season
    to: wedding_season_aggregate
    type: AFFECTS
    weight: 0.9
    polarity: 1
    delay: IMMEDIATE
    description: "The autumn festive calendar (e.g., Dev Uthani Ekadashi) directly dictates the start of the auspicious Hindu wedding season."

  - from: retail_inflation_cpi
    to: aggregate_consumer_confidence
    type: AFFECTS
    weight: 0.8
    polarity: -1
    delay: SHORT_TERM
    description: "High retail inflation erodes household purchasing power, directly lowering aggregate consumer confidence."

  - from: indirect_taxes
    to: biscuits_and_snacks
    type: AFFECTS
    weight: 0.9
    polarity: 1
    delay: IMMEDIATE
    description: "Changes in indirect tax rates (GST) are directly passed on to the retail prices of FMCG goods like biscuits and snacks."

canary_updates:
  - id: "Break 2: himalayan_glaciers -> structural_collapse"
    reason: "Himalayan glaciers melting primarily affects northern river systems. A 4-hop chain to generic structural collapse is too tenuous and bypasses specific regional flood mechanics. Update canary target to himalayan_river_systems or remove."
  
  - id: "Break 6: international_gold_prices -> wedding_planning_service"
    reason: "International gold prices affect retail gold investment, but do not directly change the cost or demand for wedding planning services (which are labor/event driven). The canary conflates jewelry budgets with planner fees. Remove canary or change target to retail_gold_investment."
  
  - id: "Break 7: national_unemployment_rate -> it_sector_jobs"
    reason: "National unemployment rate is an aggregate lagging indicator, not a causal driver of IT sector jobs. Both are driven by macro factors (e.g., GDP, Fed rates). Expecting a causal path from an aggregate metric to a specific sector violates direct causation. Remove canary."
```