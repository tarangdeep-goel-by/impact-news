### Node: skilled_emigration
**PASS** skilled_emigration→indian_diaspora_nri w=0.95 (current=0.95)
**FIX** skilled_emigration→phd_research_programs — type should be AFFECTS (was DISRUPTS). w=0.60 (current=0.60). Reason: Emigration does not physically block or halt (DISRUPT) PhD programs; it reduces the candidate pool, which AFFECTS their enrollment and quality.

### Node: spring_harvest_festivals
**KILL** spring_harvest_festivals→domestic_flight_ticket — Rule 21 violation. Intermediary: passenger_aviation_traffic. Festivals drive travel demand (traffic), which in turn spikes ticket prices.

### Node: tier_2_3_city_expansion
**PASS** tier_2_3_city_expansion→investment_property_value w=0.70 (current=0.70)
**KILL** tier_2_3_city_expansion→commercial_airports — Rule 21 violation. Intermediary: passenger_aviation_traffic or ministry_of_civil_aviation. City expansion creates travel demand, which necessitates government/private bodies to produce airports.
**PASS** tier_2_3_city_expansion→rural_urban_migration_corridors w=0.60 (current=0.60)

### Node: urban_population_density
**PASS** urban_population_density→traffic_congestion w=0.90 (current=0.90)
**PASS** urban_population_density→residential_rent w=0.85 (current=0.85)
**KILL** urban_population_density→municipal_water_supply — Rule 21 violation. Intermediary: municipal_water_grid. Density physically overloads the grid (T4), and the grid's failure is what disrupts the actual water supply service (I2).
**KILL** urban_population_density→arable_topsoil — Rule 21 violation / Invalid mechanism. High population density (people per sq km) does not pave over land; urban spatial expansion (sprawl) does.
**PASS** urban_population_density→sewage_drainage_network w=0.80 (current=0.80)
**PASS** urban_population_density→municipal_water_grid w=0.80 (current=0.80)
**KILL** urban_population_density→particulate_matter_levels — Rule 21 violation. Intermediary: vehicular_emissions or domestic_emissions. Density itself does not emit PM; it concentrates the vehicles and households that do.
**PASS** urban_population_density→voter_turnout_aggregates w=0.55 (current=0.55)

### Node: voter_turnout_aggregates
**KILL** voter_turnout_aggregates→state_governments — Rule 21 violation. Intermediary: state_assembly_elections. Turnout does not produce governments; it feeds into elections, which produce governments.
**PASS** voter_turnout_aggregates→community_gathering w=0.80 (current=0.80)

### Node: waqf_boards
**PASS** waqf_boards→rental_housing w=0.60 (current=0.60)

### Node: wedding_season_aggregate
**PASS** wedding_season_aggregate→wedding_venue w=0.95 (current=0.95)
**PASS** wedding_season_aggregate→wedding_planning_service w=0.90 (current=0.90)
**FIX** wedding_season_aggregate→retail_gold_investment — type should be AFFECTS (was SUPPLIES). w=0.85 (current=0.85). Reason: The wedding season does not supply gold (jewelers do); it drives massive consumer demand, thereby affecting retail gold investment.
**PASS** wedding_season_aggregate→event_and_construction_noise w=0.85 (current=0.85)
**KILL** wedding_season_aggregate→aggregate_consumer_confidence — Rule 21 violation / Invalid mechanism. Mandatory social spending for weddings drives retail sales, but it does not inherently produce economic optimism or "consumer confidence" (a psychological macroeconomic metric).
**KILL** wedding_season_aggregate→international_gold_prices — Rule 21 violation. Intermediary: retail_gold_investment. The season drives local retail gold purchases, and that aggregate volume is what shocks international prices.

## SUMMARY
- Edges reviewed: 23
- PASS (unchanged): 13
- PASS (weight adjusted): 0
- FIX (type change): 2
- KILL: 8
- ADD: 0

## WEIGHT OVERRIDES
```yaml
edges: []
```