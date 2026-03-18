# T-world Review: T1_T2

Here is the review of the T-world lateral edges based on the provided rules:

### INVALID (Rule Violations)
Rule 18 strictly prohibits using **MANAGES** and **REGULATES** as causal edges. These represent structural metadata (hierarchies/jurisdictions) rather than lateral causal flows. You must convert these to valid Rule 12b verbs (FUNDS, PRODUCES, DISRUPTS, AFFECTS) or remove them if they are purely hierarchical:
*   **Hierarchical Metadata (Remove or move to ontology):**
    *   `ministry_of_finance → income_tax_department (MANAGES)`
    *   `ministry_of_civil_aviation → dgca (MANAGES)`
    *   `ministry_of_health → cdsco (MANAGES)`
    *   `ministry_of_health → fssai (MANAGES)`
    *   `rbi → monetary_policy_committee (MANAGES)`
    *   `supreme_court_of_india → high_courts (MANAGES)`
    *   `state_governments → regional_transport_office (MANAGES)`
*   **Convert to FUNDS / PRODUCES:**
    *   `ministry_of_road_transport → highway_network (MANAGES)` 
    *   `ministry_of_railways → indian_railways_network (MANAGES)`
    *   `ministry_of_railways → dedicated_freight_corridors (MANAGES)`
    *   `ministry_of_power → national_power_grid (MANAGES)`
    *   `rbi → india_forex_reserves (MANAGES)`
    *   `epfo → epfo_payroll_additions (MANAGES)`
    *   `uidai → aadhaar_database (MANAGES)`
    *   `municipal_corporations → municipal_water_grid (MANAGES)`
    *   `municipal_corporations → sewage_drainage_network (MANAGES)`
*   **Convert to DISRUPTS / AFFECTS (Cross-world/Regulatory actions):**
    *   `sebi → nifty_50 (REGULATES)` -> *DISRUPTS* (curbs volatility)
    *   `trai → telecom_spectrum / telecom_towers_network (REGULATES)` -> *AFFECTS*
    *   `dgca → commercial_airports (REGULATES)` -> *AFFECTS*
    *   `cpcb → coal_power_plants (REGULATES)` -> *DISRUPTS*
    *   `supreme_court_of_india → enforcement_directorate (REGULATES)` -> *DISRUPTS*
    *   `national_green_tribunal → coal_power_plants / highway_network (REGULATES)` -> *DISRUPTS*
    *   `municipal_corporations → urban_population_density (REGULATES)` -> *AFFECTS*
    *   `us_government → global_semiconductor_supply_chain (REGULATES)` -> *DISRUPTS*
    *   `european_union → global_shipping_routes (REGULATES)` -> *DISRUPTS*
    *   `wto → india_trade_deficit (REGULATES)` -> *AFFECTS*

### QUESTIONABLE (Type Upgrades per Rule 12b)
Several edges use the fallback `AFFECTS` when a stronger, more specific causal verb applies:
*   `meteorological_systems → energy_power_infrastructure (AFFECTS)` -> Upgrade to **SUPPLIES** (Provides solar/wind kinetic energy).
*   `arabian_sea_marine_system → southwest_monsoon (AFFECTS)` -> Upgrade to **SUPPLIES** (Provides atmospheric moisture).
*   `forest_cover → groundwater_aquifers (AFFECTS)` -> Upgrade to **SUPPLIES** (Recharges water tables).
*   `indian_union_government → biophysical_and_ecological_systems (AFFECTS)` -> Upgrade to **DISRUPTS** (Mechanism explicitly states "fragmentation or degradation").
*   `gst_council → union_budget_framework (AFFECTS)` -> Upgrade to **FUNDS** (Determines tax revenue available).
*   `chinese_government → china_manufacturing_output (AFFECTS)` -> Upgrade to **FUNDS** (Mechanism cites "state subsidies, credit easing").
*   `union_budget_framework → india_gdp_growth (AFFECTS)` -> Upgrade to **FUNDS** (Capital expenditure allocations).

### MISSING
*   `rbi → indian_macroeconomic_indicators (AFFECTS)`: Missing the direct link between the central bank's broader monetary policy and national inflation/GDP metrics.
*   `opec → india_trade_deficit (AFFECTS, p=1)`: Global oil prices directly and severely dictate India's import bill.
*   `ministry_of_finance → rbi (AFFECTS)`: Government borrowing targets directly pressure RBI's liquidity management and rate decisions.
*   `indian_ocean_dipole → cyclonic_storm_systems (PRODUCES)`: IOD phases directly influence the frequency and intensity of cyclones in the Bay of Bengal/Arabian Sea.

### QUALITY SCORE: 6.5/10
**Critique:** The domain knowledge, mechanistic descriptions (Rule 15), and polarity mapping (Rule 1) are exceptionally strong and highly accurate for the Indian context. However, the graph structure is heavily penalized for the widespread use of `MANAGES` and `REGULATES` (29 instances). In this ontology, regulatory/administrative oversight is metadata; lateral edges must strictly represent the *flow* of capital, resources, or disruption. Fixing the verbs will immediately raise this to a 9.5/10.