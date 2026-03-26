Here is the audit of the edge quality and weights based on the provided rules. Nodes where all edges passed unchanged have been skipped.

### node: upi_transaction_success
**PASS** upi_transaction_success→food_delivery_services w=0.90 (current=0.90)
**FIX** upi_transaction_success→real_money_gaming_and_betting — type should be FUNDS (was SUPPLIES). w=0.85 (current=0.85). Reason: UPI transactions directly provide the financial capital (funds) for wallet top-ups, fitting the definition of FUNDS perfectly.
**FIX** upi_transaction_success→street_vendor_income — type should be FUNDS (was DEPENDS_ON). w=0.80 (current=0.80). Reason: The UPI transaction is the literal mechanism of payment that directly funds the vendor's income.
**PASS** upi_transaction_success→temple_donation w=0.75 (current=0.75)

### node: concert_ticket
**FIX** concert_ticket→hotel_room — type should be AFFECTS (was FUNDS). w=0.60 (current=0.60). Reason: A concert ticket does not financially pay for a hotel room. The event drives the fan's behavior to book a room, making AFFECTS the correct causal relationship.

### node: cricket_match_ticket
**PASS** cricket_match_ticket→traffic_congestion w=0.85 (current=0.85)
**FIX** cricket_match_ticket→real_money_gaming_and_betting — type should be AFFECTS (was PRODUCES). w=0.65 (current=0.65). Reason: The ticket itself doesn't literally create betting; the engagement with the match drives betting behavior. AFFECTS is the appropriate behavioral link.
**PASS** cricket_match_ticket→stampedes w=0.40 (current=0.40)

### node: puja_pandal_contribution
**PASS** puja_pandal_contribution→festive_idol w=0.90 (current=0.90)
**FIX** puja_pandal_contribution→construction_worker_wages — type should be FUNDS (was EMPLOYS). w=0.85 (current=0.85). Reason: The contribution itself doesn't hire the workers (the committee does), but the contribution directly FUNDS the wages.
**KILL** puja_pandal_contribution→street_food — Rule 21 violation. Intermediary: puja_pandal / community_gathering. (Contributions fund the pandal, which attracts the crowd, which buys the food).
**KILL** puja_pandal_contribution→traffic_congestion — Rule 21 violation. Intermediary: puja_pandal / street_blockage.
**KILL** puja_pandal_contribution→event_and_construction_noise — Rule 21 violation. Intermediary: loudspeaker_systems.
**PASS** puja_pandal_contribution→community_hall w=0.70 (current=0.70)
**KILL** puja_pandal_contribution→fire_hazards — Rule 21 violation. Intermediary: temporary_electrical_wiring.

### node: rwa_regulation
**PASS** rwa_regulation→firecracker w=0.80 (current=0.80)
**PASS** rwa_regulation→fiber_broadband_tariff w=0.70 (current=0.70)
**FIX** rwa_regulation→community_hall — type should be REGULATES (was AFFECTS). w=0.70 (current=0.70). Reason: The description explicitly states RWAs "set the pricing and availability rules", which is the exact definition of REGULATES.

### node: wedding_planning_service
**PASS** wedding_planning_service→wedding_venue w=0.85 (current=0.85)
**FIX** wedding_planning_service→gig_worker_payouts — type should be FUNDS (was EMPLOYS). w=0.80 (current=0.80). Reason: While the planner EMPLOYS the worker, the target node is "payouts", meaning the planner's budget directly FUNDS those payouts.
**PASS** wedding_planning_service→fine_dining_restaurants w=0.70 (current=0.70)
**PASS** wedding_planning_service→urban_company_partner_earnings w=0.60 (current=0.60)

### node: building_materials_cost
**FIX** building_materials_cost→investment_property_value — type should be AFFECTS (was PRODUCES). w=0.80 (current=0.80). Reason: Costs do not literally "create" or "generate" property value; they inflate/affect the valuation.
**KILL** building_materials_cost→structural_collapse — Rule 21 violation. Intermediary: substandard_materials / poor_construction_quality.
**PASS** building_materials_cost→residential_rent w=0.60 (current=0.60)
**PASS** building_materials_cost→construction_worker_wages w=0.60 (current=0.60)

### node: drinking_water_quality
**FIX** drinking_water_quality→cholera_and_diarrhea — type should be DISRUPTS (was PRODUCES). w=0.90 (current=0.90). Reason: High water quality physically blocks/halts the transmission of waterborne diseases (negative polarity).
**FIX** drinking_water_quality→typhoid — type should be DISRUPTS (was PRODUCES). w=0.80 (current=0.80). Reason: Safe drinking water eliminates/halts the transmission vector.

### node: electricity_tariff
**FIX** electricity_tariff→ev_charging_tariff — type should be AFFECTS (was SUPPLIES). w=0.90 (current=0.90). Reason: A tariff does not "supply" another tariff; the baseline residential rate directly dictates/affects the EV charging rate.
**KILL** electricity_tariff→liquid_milk — Rule 21 violation. Intermediary: cold_chain_operating_costs.

### node: lpg_cylinder
**PASS** lpg_cylinder→street_food w=0.80 (current=0.80)
**PASS** lpg_cylinder→fine_dining_restaurants w=0.70 (current=0.70)
**PASS** lpg_cylinder→fire_hazards w=0.70 (current=0.70)
**KILL** lpg_cylinder→asthma — Rule 21 violation. Intermediary: indoor_air_pollution / smoke.

### node: private_water_tanker
**FIX** private_water_tanker→rwa_maintenance_fees — type should be AFFECTS (was FUNDS). w=0.80 (current=0.80). Reason: The tanker does not fund the fees; the high cost of the tanker forces the fees to increase (AFFECTS).
**PASS** private_water_tanker→drinking_water_quality w=0.70 (current=0.70)

### node: repair_service_charges
**FIX** repair_service_charges→rwa_maintenance_fees — type should be AFFECTS (was FUNDS). w=0.60 (current=0.60). Reason: Service charges do not fund the maintenance fees; they are an expense that drives up (AFFECTS) the fees.

### node: residential_power_supply
**PASS** residential_power_supply→residential_borewells w=0.90 (current=0.90)
**PASS** residential_power_supply→municipal_water_supply w=0.80 (current=0.80)
**PASS** residential_power_supply→broadband_network_quality w=0.80 (current=0.80)
**KILL** residential_power_supply→ev_charging_tariff — Rule 21 violation. Power supply dictates the *ability* to charge, but it does not structurally dictate the *tariff* (price) itself.
**KILL** residential_power_supply→rwa_maintenance_fees — Rule 21 violation. Intermediary: diesel_generators.
**KILL** residential_power_supply→electrocution_hazard — Rule 21 violation. Intermediary: degraded_wiring_insulation.

### node: sewage_infrastructure
**FIX** sewage_infrastructure→open_drains — type should be DISRUPTS (was PRODUCES). w=0.90 (current=0.90). Reason: Underground sewage replaces and eliminates (halts) open drains.
**FIX** sewage_infrastructure→drinking_water_quality — type should be AFFECTS (was DISRUPTS). w=0.80 (current=0.80). Reason: Leaking sewage degrades/contaminates water quality. AFFECTS is the standard type for quality degradation.
**FIX** sewage_infrastructure→polluted_surface_water — type should be DISRUPTS (was PRODUCES). w=0.80 (current=0.80). Reason: Functional sewage treatment prevents/halts raw effluent from reaching surface water.
**KILL** sewage_infrastructure→dengue — Rule 21 violation. Intermediary: stagnant_water / mosquito_breeding.
**KILL** sewage_infrastructure→malaria — Rule 21 violation. Intermediary: stagnant_water / mosquito_breeding.

### node: waste_collection_services
**PASS** waste_collection_services→street_garbage w=0.90 (current=0.90)
**FIX** waste_collection_services→rwa_maintenance_fees — type should be AFFECTS (was FUNDS). w=0.70 (current=0.70). Reason: The service does not fund the fees; the cost of the privatized contract increases (AFFECTS) the maintenance fees.

---

## SUMMARY
- Edges reviewed: 92
- PASS (unchanged): 63
- PASS (weight adjusted): 0
- FIX (type change): 17
- KILL: 12
- ADD: 0

## WEIGHT OVERRIDES
```yaml
edges: []
```
*(No weight overrides were necessary; all existing weights fell within the appropriate calibration ranges for their respective causal strengths.)*