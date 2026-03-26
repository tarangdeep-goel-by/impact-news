### Node: `winter_smog`
- **FIX** winter_smog→ambient_aqi — type should be AFFECTS (was PRODUCES). w=0.95 (current=0.95). Reason: AQI is a metric/index, so smog AFFECTS it rather than literally producing it. Additionally, polarity should be 1 (increased smog increases the AQI number).
- **PASS** winter_smog→asthma w=0.90 (current=0.90)
- **PASS** winter_smog→copd w=0.85 (current=0.85)
- **KILL** winter_smog→domestic_flight_ticket — Rule 21 violation. Intermediary: `commercial_airports` or `flight_cancellations`.

### Node: `arable_topsoil`
- **KILL** arable_topsoil→global_food_grain_supply — Rule 21 violation. Intermediary: `agricultural_crop_yield`.
- **KILL** arable_topsoil→seasonal_migrant_labor — Rule 21 violation. Intermediary: `agricultural_income` or `rural_unemployment`.

### Node: `cyclonic_storm_systems`
- **PASS** cyclonic_storm_systems→major_seaports w=0.95 (current=0.95)
- **PASS** cyclonic_storm_systems→telecom_towers_network w=0.90 (current=0.90)
- **PASS** cyclonic_storm_systems→power_substations w=0.90 (current=0.90)
- **PASS** cyclonic_storm_systems→commercial_airports w=0.90 (current=0.90)
- **PASS** cyclonic_storm_systems→global_shipping_routes w=0.85 (current=0.85)
- **PASS** cyclonic_storm_systems→national_power_grid w=0.85 (current=0.85)
- **PASS** cyclonic_storm_systems→marine_fish_stocks w=0.85 (current=0.85)
- **FIX** cyclonic_storm_systems→structural_collapse — type should be PRODUCES (was DISRUPTS). w=0.80 (current=0.80). Reason: Cyclones literally cause/create structural collapses; DISRUPTS implies halting or blocking a collapse.
- **PASS** cyclonic_storm_systems→forest_cover w=0.70 (current=0.70)

### Node: `el_nino_southern_oscillation`
- **PASS** el_nino_southern_oscillation→southwest_monsoon w=0.85 (current=0.85)
- **KILL** el_nino_southern_oscillation→global_sugar_supply — Rule 21 violation. Intermediary: `southwest_monsoon` and `sugarcane_yield`.

### Node: `forest_cover`
- **PASS** forest_cover→peninsular_river_systems w=0.80 (current=0.80)
- **PASS** forest_cover→urban_flooding w=0.70 (current=0.70)
- **FIX** forest_cover→wildlife_encounters — type should be AFFECTS (was PRODUCES). w=0.60 (current=0.60). Reason: Polarity must also be -1 (more forest cover *reduces* wildlife encounters in human settlements).
- **PASS** forest_cover→ambient_aqi w=0.60 (current=0.60)
- **PASS** forest_cover→himalayan_river_systems w=0.60 (current=0.60)

### Node: `global_surface_temperature`
- **PASS** global_surface_temperature→himalayan_glaciers w=0.90 (current=0.90)
- **PASS** global_surface_temperature→bay_of_bengal_marine_system w=0.85 (current=0.85)
- **KILL** global_surface_temperature→rural_urban_migration_corridors — Rule 21 violation. Intermediary: `agricultural_viability` or `crop_yields`.

### Node: `groundwater_aquifers`
- **PASS** groundwater_aquifers→residential_borewells w=0.90 (current=0.90)
- **KILL** groundwater_aquifers→rural_urban_migration_corridors — Rule 21 violation. Intermediary: `farming_viability` or `agricultural_income`.

### Node: `himalayan_tectonic_plates`
- **FIX** himalayan_tectonic_plates→structural_collapse — type should be PRODUCES (was DISRUPTS). w=0.90 (current=0.90). Reason: Earthquakes directly cause/create structural collapses.
- **PASS** himalayan_tectonic_plates→highway_network w=0.80 (current=0.80)

### Node: `indian_plate_interior`
- **FIX** indian_plate_interior→structural_collapse — type should be PRODUCES (was DISRUPTS). w=0.80 (current=0.80). Reason: Earthquakes directly cause/create structural collapses.
- **PASS** indian_plate_interior→power_substations w=0.70 (current=0.70)

### Node: `migratory_pest_populations`
- **PASS** migratory_pest_populations→agricultural_crop_damage w=0.85 (current=0.85)
- **KILL** migratory_pest_populations→global_food_grain_supply — Rule 21 violation. Intermediary: `agricultural_crop_damage`.

### Node: `southwest_monsoon`
- **PASS** southwest_monsoon→peninsular_river_systems w=0.95 (current=0.95)
- **PASS** southwest_monsoon→urban_flooding w=0.90 (current=0.90)
- **PASS** southwest_monsoon→stagnant_water_pools w=0.90 (current=0.90)
- **PASS** southwest_monsoon→groundwater_aquifers w=0.90 (current=0.90)
- **PASS** southwest_monsoon→agricultural_crop_damage w=0.85 (current=0.85)
- **PASS** southwest_monsoon→traffic_congestion w=0.85 (current=0.85)
- **PASS** southwest_monsoon→road_potholes w=0.85 (current=0.85)
- **KILL** southwest_monsoon→residential_borewells — Rule 21 violation. Intermediary: `groundwater_aquifers`.
- **KILL** southwest_monsoon→construction_worker_wages — Rule 21 violation. Intermediary: `outdoor_construction_activity`.
- **KILL** southwest_monsoon→open_drains — Invalid edge. Empty description and monsoon does not produce drains.
- **KILL** southwest_monsoon→global_food_grain_supply — Rule 21 violation. Intermediary: `agricultural_crop_yield`.
- **KILL** southwest_monsoon→ride_hailing_services — Rule 21 violation. Intermediary: `ride_hailing_demand`.
- **KILL** southwest_monsoon→delivery_and_logistics — Rule 21 violation. Intermediary: `delivery_demand`.
- **KILL** southwest_monsoon→mgnrega_wages — Rule 21 violation. Intermediary: `agricultural_crop_damage`.
- **KILL** southwest_monsoon→global_sugar_supply — Rule 21 violation. Intermediary: `sugarcane_yield`.
- **KILL** southwest_monsoon→coal_power_plants — Rule 21 violation. Intermediary: `coal_mines`.
- **KILL** southwest_monsoon→agricultural_exports — Rule 21 violation. Intermediary: `agricultural_production`.
- **KILL** southwest_monsoon→seasonal_migrant_labor — Rule 21 violation. Intermediary: `agricultural_labor_demand`.
- **PASS** southwest_monsoon→highway_network w=0.70 (current=0.70)
- **KILL** southwest_monsoon→road_freight_movement — Rule 21 violation. Intermediary: `highway_network` or `road_flooding`.

### Node: `cci`
- **PASS** cci→cab_aggregator_fare w=0.75 (current=0.75)
- **KILL** cci→ondc_platform — Rule 21 violation. Intermediary: `e_commerce_platforms`.

### Node: `epfo`
- **FIX** epfo→epf_balance — type should be AFFECTS (was MANAGES). w=0.95 (current=0.95). Reason: Rule 12b violation. MANAGES cannot cross the T→I boundary.
- **PASS** epfo→epfo_payroll_additions w=0.95 (current=0.95)
- **PASS** epfo→dii_flows w=0.85 (current=0.85)
- **PASS** epfo→female_labor_force_participation w=0.60 (current=0.60)

### Node: `high_courts`
- **PASS** high_courts→criminal_litigation_risk w=0.70 (current=0.70)
- **FIX** high_courts→residential_rent — type should be AFFECTS (was REGULATES). w=0.55 (current=0.55). Reason: Rule 12b violation. REGULATES cannot cross the T→I boundary.

### Node: `ministry_of_agriculture`
- **FIX** ministry_of_agriculture→mgnrega_wages — type should be FUNDS (was MANAGES). w=0.85 (current=0.85). Reason: Rule 12b violation. MANAGES cannot cross the T→I boundary. FUNDS is appropriate as the ministry administers the budget allocation and wage disbursement.

---

## SUMMARY
- Edges reviewed: 116
- PASS (unchanged): 88
- PASS (weight adjusted): 0
- FIX (type change): 8
- KILL: 20
- ADD: 0

## WEIGHT OVERRIDES
```yaml
edges: []
```