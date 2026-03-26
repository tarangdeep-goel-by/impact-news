Here is the architectural review and resolution for the 18 rejected edges across the 7 groups, applying the Constitution's rules on direct causation, entity validity, and edge semantics.

---

### Group 1: Natural disasters → citizen physical damage

**Verdict: Original rejection was overly strict.**
"Housing damage" is an event/change, not an entity (violates Rule 1). The taxonomy already contains `structural_collapse` (I8-L4) to represent the physical failure of buildings. Earthquakes and cyclones apply direct physical force to structures, causing them to collapse. No intermediary is needed for the first three. For the fourth, the intermediary `power_substations` already exists in T4, so we just need to wire it.

**Edges to Add:**
```yaml
- from: cyclonic_storm_systems
  to: structural_collapse
  type: DISRUPTS
  weight: 0.8
  polarity: 1
  delay: IMMEDIATE
  description: "High-velocity cyclonic winds directly cause structural failure and roof collapse in vulnerable residential buildings."

- from: himalayan_tectonic_plates
  to: structural_collapse
  type: DISRUPTS
  weight: 0.9
  polarity: 1
  delay: IMMEDIATE
  description: "Seismic shifts in the Himalayan fault lines directly cause structural failure in northern Indian real estate."

- from: indian_plate_interior
  to: structural_collapse
  type: DISRUPTS
  weight: 0.8
  polarity: 1
  delay: IMMEDIATE
  description: "Intra-plate earthquakes directly compromise building foundations and cause structural collapses."

- from: indian_plate_interior
  to: power_substations
  type: DISRUPTS
  weight: 0.7
  polarity: -1
  delay: IMMEDIATE
  description: "Seismic activity physically damages transformers and grid substations, reducing operational capacity."
```

---

### Group 2: Forest cover → environmental impacts

**Verdict: Original rejection was overly strict for AQI and Flooding; Intermediary needed for Water.**
"Particulate matter" is a metric, and "surface runoff" is a physical mechanism—neither are valid taxonomy entities. Forests directly filter air and absorb water. These direct edges are valid. For drinking water, forests regulate the watershed that feeds river systems, which then supply drinking water, so the river system intermediaries (which exist) should be used.

**Edges to Add:**
```yaml
- from: forest_cover
  to: ambient_aqi
  type: AFFECTS
  weight: 0.6
  polarity: -1
  delay: LONG_TERM
  description: "Tree canopies directly act as physical sinks for airborne pollutants, lowering the ambient AQI (improving air quality)."

- from: forest_cover
  to: urban_flooding
  type: DISRUPTS
  weight: 0.7
  polarity: -1
  delay: SHORT_TERM
  description: "Root systems and forest floors directly absorb heavy rainfall, reducing the volume of water that reaches urban centers."

- from: forest_cover
  to: peninsular_river_systems
  type: AFFECTS
  weight: 0.8
  polarity: 1
  delay: MEDIUM_TERM
  description: "Forest catchments regulate water flow into peninsular rivers, maintaining base flows during non-monsoon months."

- from: forest_cover
  to: himalayan_river_systems
  type: AFFECTS
  weight: 0.6
  polarity: 1
  delay: MEDIUM_TERM
  description: "Himalayan forest cover prevents soil erosion and regulates glacial melt runoff into northern river systems."
```

---

### Group 3: Water systems → downstream impacts

**Verdict: Intermediaries exist for drinking water; New node needed for irrigation.**
The edges to `drinking_water_quality` simply need to be routed from the existing municipal and borewell nodes. For farm wages, "canal irrigation" is a massive physical infrastructure network in India that passes Rule 5 (Matchable, Mappable, Edgeable) and should exist as a T4 node.

**New Node to Create:**
```yaml
canal_irrigation_networks:
  name: "Canal Irrigation Networks"
  parent: water_infrastructure  # Assuming T4-L3 exists
  level: L4
  category: T4
  aliases: [canal_systems, irrigation_canals, agricultural_water_supply]
  justification: "Matchable: Frequently in news regarding agriculture. Mappable: Crucial for rural users. Edgeable: Connects rivers to crop yields and farm labor."
```

**Edges to Add:**
```yaml
- from: municipal_water_supply
  to: drinking_water_quality
  type: AFFECTS
  weight: 0.9
  polarity: 1
  delay: IMMEDIATE
  description: "The treatment and distribution quality of municipal water directly determines the safety of household drinking water."

- from: residential_borewells
  to: drinking_water_quality
  type: AFFECTS
  weight: 0.8
  polarity: 1
  delay: IMMEDIATE
  description: "Groundwater extracted via borewells directly dictates the mineral and contaminant levels in household drinking water."

- from: peninsular_river_systems
  to: canal_irrigation_networks
  type: SUPPLIES
  weight: 0.9
  polarity: 1
  delay: IMMEDIATE
  description: "Peninsular rivers act as the primary water source feeding state-level agricultural canal networks."

- from: canal_irrigation_networks
  to: farm_labor_wages
  type: AFFECTS
  weight: 0.6
  polarity: 1
  delay: MEDIUM_TERM
  description: "Reliable canal irrigation increases crop intensity and yields, driving up the demand and wages for agricultural labor."
```

---

### Group 4: Cyclone → flight disruption

**Verdict: Intermediary exists, just needs wiring.**
Cyclones disrupt airport infrastructure, which in turn causes flight cancellations and ticket price surges. Both nodes exist.

**Edges to Add:**
```yaml
- from: cyclonic_storm_systems
  to: commercial_airports
  type: DISRUPTS
  weight: 0.9
  polarity: -1
  delay: IMMEDIATE
  description: "High winds and flooding from cyclones force commercial airports to halt operations and ground flights."

- from: commercial_airports
  to: domestic_flight_ticket
  type: AFFECTS
  weight: 0.8
  polarity: -1
  delay: SHORT_TERM
  description: "When airport operational capacity drops due to closures, flight cancellations cause remaining ticket prices to surge."
```

---

### Group 5: RERA → housing costs

**Verdict: Original rejection was overly strict.**
RERA is the regulatory framework itself. While it regulates developers, the mechanism of action *is* the regulation. RERA's compliance mandates (escrow accounts, carpet area rules) directly alter the cost structure of housing projects. Bypassing "real_estate_developers" is valid under the Administrative Exemption (Rule 21) because developers cannot independently veto the compliance costs—they are forced pass-throughs.

**Edges to Add:**
```yaml
- from: rera
  to: residential_rent
  type: REGULATES
  weight: 0.5
  polarity: 1
  delay: MEDIUM_TERM
  description: "Stricter RERA compliance increases project costs and delays supply, which pushes up residential rental rates."

- from: rera
  to: building_materials_cost
  type: REGULATES
  weight: 0.4
  polarity: 1
  delay: MEDIUM_TERM
  description: "RERA mandates on construction quality and standardized materials directly influence the demand and pricing of premium building materials."
```

---

### Group 6: International institutions → Indian economy

**Verdict: Intermediaries are needed and missing.**
"IT services exports" and "Sovereign credit rating" are massive macroeconomic entities (T3) that absolutely pass Rule 5. They are the exact transmission belts between global institutions and domestic impacts.

**New Nodes to Create:**
```yaml
it_services_exports:
  name: "IT Services Exports"
  parent: international_trade  # Assuming T3-L3 exists
  level: L4
  category: T3
  aliases: [tech_exports, software_exports, it_bpm_revenues]
  justification: "Matchable: Core macro metric in Indian business news. Mappable: Drives IT sector health. Edgeable: Connects global demand to domestic IT jobs."

sovereign_credit_rating:
  name: "Sovereign Credit Rating"
  parent: macroeconomic_indicators  # Assuming T3-L3 exists
  level: L4
  category: T3
  aliases: [india_credit_rating, moody_rating, s_and_p_rating]
  justification: "Matchable: Major news event when changed. Mappable: Dictates national borrowing costs. Edgeable: Connects IMF/agencies to bond yields."
```

**Edges to Add:**
```yaml
- from: european_union
  to: it_services_exports
  type: AFFECTS
  weight: 0.6
  polarity: 1
  delay: MEDIUM_TERM
  description: "Economic health and digital policies of the EU directly dictate the volume of IT service contracts outsourced to India."

- from: wto
  to: it_services_exports
  type: REGULATES
  weight: 0.5
  polarity: 1
  delay: LONG_TERM
  description: "WTO agreements on cross-border data flows and digital trade tariffs directly govern the profitability of Indian IT exports."

- from: it_services_exports
  to: it_sector_jobs
  type: PRODUCES
  weight: 0.9
  polarity: 1
  delay: SHORT_TERM
  description: "Growth in IT export revenues directly funds the expansion of headcount and hiring in the Indian tech sector."

- from: imf
  to: sovereign_credit_rating
  type: AFFECTS
  weight: 0.8
  polarity: 1
  delay: MEDIUM_TERM
  description: "IMF macroeconomic assessments and growth outlooks heavily influence the sovereign credit ratings assigned to India."

- from: sovereign_credit_rating
  to: india_10yr_bond_yield
  type: AFFECTS
  weight: 0.9
  polarity: -1
  delay: IMMEDIATE
  description: "An upgrade in sovereign credit rating lowers the perceived risk of Indian debt, directly decreasing the 10-year bond yield."
```

---

### Group 7: Bank liquidity → loan EMIs

**Verdict: Intermediary is needed and missing.**
"Commercial bank lending rates" (like MCLR or Repo-Linked Lending Rates) are the exact T3 macroeconomic aggregates that bridge systemic liquidity to retail EMIs.

**New Node to Create:**
```yaml
commercial_bank_lending_rates:
  name: "Commercial Bank Lending Rates"
  parent: interest_rates  # Assuming T3-L3 exists
  level: L4
  category: T3
  aliases: [mclr, rllr, bank_interest_rates, base_rate]
  justification: "Matchable: Standard financial news metric. Mappable: Directly determines user loan costs. Edgeable: Connects liquidity/RBI to retail EMIs."
```

**Edges to Add:**
```yaml
- from: bank_liquidity_and_credit
  to: commercial_bank_lending_rates
  type: AFFECTS
  weight: 0.8
  polarity: -1
  delay: SHORT_TERM
  description: "Higher systemic liquidity reduces the cost of funds for banks, prompting them to lower their benchmark lending rates."

- from: commercial_bank_lending_rates
  to: home_loan_emi
  type: AFFECTS
  weight: 0.9
  polarity: 1
  delay: IMMEDIATE
  description: "Changes in bank benchmark lending rates are directly passed on to floating-rate retail home loan EMIs."

- from: commercial_bank_lending_rates
  to: personal_loan_emi
  type: AFFECTS
  weight: 0.8
  polarity: 1
  delay: IMMEDIATE
  description: "Increases in commercial lending rates directly raise the interest burden and EMIs for unsecured personal loans."
```

---

### COMPLETE SUMMARY

**New Nodes to Create (4 Total):**
1. `canal_irrigation_networks` (T4-L4, Parent: water_infrastructure)
2. `it_services_exports` (T3-L4, Parent: international_trade)
3. `sovereign_credit_rating` (T3-L4, Parent: macroeconomic_indicators)
4. `commercial_bank_lending_rates` (T3-L4, Parent: interest_rates)

**New Edges to Add (20 Total):**
*Direct Edges Restored (Overly Strict Rejections):*
1. `cyclonic_storm_systems` → `structural_collapse`
2. `himalayan_tectonic_plates` → `structural_collapse`
3. `indian_plate_interior` → `structural_collapse`
4. `forest_cover` → `ambient_aqi`
5. `forest_cover` → `urban_flooding`
6. `rera` → `residential_rent`
7. `rera` → `building_materials_cost`

*Edges to Existing Intermediaries:*
8. `indian_plate_interior` → `power_substations`
9. `forest_cover` → `peninsular_river_systems`
10. `forest_cover` → `himalayan_river_systems`
11. `municipal_water_supply` → `drinking_water_quality`
12. `residential_borewells` → `drinking_water_quality`
13. `cyclonic_storm_systems` → `commercial_airports`
14. `commercial_airports` → `domestic_flight_ticket`

*Edges to New Intermediaries:*
15. `peninsular_river_systems` → `canal_irrigation_networks`
16. `canal_irrigation_networks` → `farm_labor_wages`
17. `european_union` → `it_services_exports`
18. `wto` → `it_services_exports`
19. `it_services_exports` → `it_sector_jobs`
20. `imf` → `sovereign_credit_rating`
21. `sovereign_credit_rating` → `india_10yr_bond_yield`
22. `bank_liquidity_and_credit` → `commercial_bank_lending_rates`
23. `commercial_bank_lending_rates` → `home_loan_emi`
24. `commercial_bank_lending_rates` → `personal_loan_emi`

*(Note: Edge count is 24 because resolving the 18 rejected paths required creating the full A→B→C chains where intermediaries were missing).*