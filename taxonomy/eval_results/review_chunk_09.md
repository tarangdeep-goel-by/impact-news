**Node: sensex**
- PASS sensex→direct_equity_portfolio w=0.90 (current=0.9)
- PASS sensex→equity_mutual_funds w=0.90 (current=0.9)

**Node: sovereign_credit_rating**
- PASS sovereign_credit_rating→india_10yr_bond_yield w=0.90 (current=0.9)

**Node: us_consumer_demand**
- KILL us_consumer_demand→it_sector_jobs — Rule 21 violation. Intermediary: corporate_tech_spending / it_services_exports.
- FIX us_consumer_demand→china_manufacturing_output — type should be AFFECTS (was FUNDS). w=0.80 (current=0.8). Reason: US consumers do not directly fund Chinese factories; they buy retail goods, which creates demand that affects factory output.
- KILL us_consumer_demand→it_sector_salary — Rule 21 violation. Intermediary: it_services_exports / corporate_revenue.

**Node: us_dollar_index**
- PASS us_dollar_index→usd_inr_exchange w=0.90 (current=0.9)
- PASS us_dollar_index→international_gold_prices w=0.85 (current=0.85)

**Node: us_treasury_yields**
- PASS us_treasury_yields→fii_fpi_flows w=0.85 (current=0.8) [Adjusted weight: highly reliable portfolio rebalancing mechanism]

**Node: usd_inr_exchange**
- PASS usd_inr_exchange→tour_package w=0.80 (current=0.8)
- PASS usd_inr_exchange→india_forex_reserves w=0.80 (current=0.8)
- PASS usd_inr_exchange→smartphone_device w=0.80 (current=0.75) [Adjusted weight: near-deterministic pass-through for electronics]
- PASS usd_inr_exchange→laptop_computer w=0.80 (current=0.75) [Adjusted weight: near-deterministic pass-through for electronics]
- PASS usd_inr_exchange→wpi w=0.75 (current=0.7) [Adjusted weight: strong direct pass-through for imported wholesale goods]
- PASS usd_inr_exchange→skilled_emigration w=0.50 (current=0.6) [Adjusted weight: moderate behavioral incentive, heavily gated by visas]

**Node: venture_capital_and_pe_flows**
- PASS venture_capital_and_pe_flows→startup_jobs w=0.85 (current=0.85)
- PASS venture_capital_and_pe_flows→startup_layoffs w=0.80 (current=0.8)
- KILL venture_capital_and_pe_flows→epfo_payroll_additions — Rule 21 violation. Intermediary: startup_jobs.

**Node: wpi**
- KILL wpi→aggregate_consumer_confidence — Rule 21 violation. Intermediary: cpi (retail prices).
- PASS wpi→india_10yr_bond_yield w=0.75 (current=0.75)
- PASS wpi→kirana_store_income w=0.70 (current=0.7)
- PASS wpi→monetary_policy_committee w=0.60 (current=0.7) [Adjusted weight: MPC primarily targets CPI, making WPI a secondary informational input]

**Node: aadhaar_database**
- PASS aadhaar_database→aadhaar_authentication w=0.95 (current=0.95)
- KILL aadhaar_database→data_centers — Rule 21 violation / Invalid Direction. The description states Aadhaar requires data centers, meaning the dependency flows the other way (Data Centers -> Aadhaar).
- PASS aadhaar_database→pan_aadhaar_linkage w=0.90 (current=0.9)
- PASS aadhaar_database→upi_platform w=0.85 (current=0.85)
- FIX aadhaar_database→data_breaches_and_leaks — type should be PRODUCES (was AFFECTS). w=0.75 (current=0.7). Reason: Vulnerabilities in the database literally generate/produce the data breaches.

**Node: canal_irrigation_networks**
- KILL canal_irrigation_networks→farm_labor_wages — Rule 21 violation. Intermediary: crop_yield / agricultural_intensity.

**Node: coal_power_plants**
- FIX coal_power_plants→national_power_grid — type should be SUPPLIES (was PRODUCES). w=0.90 (current=0.9). Reason: Power plants supply physical electricity/energy to the grid; they do not "produce" the grid itself.
- KILL coal_power_plants→residential_power_supply — Rule 21 violation. Intermediary: national_power_grid / power_substations.
- KILL coal_power_plants→global_surface_temperature — Rule 21 violation. Intermediary: greenhouse_gas_emissions.
- PASS coal_power_plants→particulate_matter_levels w=0.85 (current=0.8) [Adjusted weight: direct and near-deterministic physical emission]

**Node: commercial_airports**
- PASS commercial_airports→domestic_flight_ticket w=0.80 (current=0.8)
- PASS commercial_airports→noise_pollution w=0.80 (current=0.75) [Adjusted weight: highly reliable physical mechanism]
- PASS commercial_airports→tour_package w=0.65 (current=0.65)

**Node: data_centers**
- KILL data_centers→national_power_grid — Rule 21 violation / Invalid Direction. Data centers depend on the grid, not vice versa.
- PASS data_centers→digilocker_documents w=0.90 (current=0.9)
- KILL data_centers→optical_fibre_network — Rule 21 violation / Invalid Direction. Data centers depend on optical fibre, not vice versa.
- PASS data_centers→ott_subscription w=0.65 (current=0.65)

**Node: dedicated_freight_corridors**
- PASS dedicated_freight_corridors→railway_freight_movement w=0.90 (current=0.9)
- KILL dedicated_freight_corridors→export_competitiveness — Rule 21 violation. Intermediary: logistics_costs / railway_freight_movement.
- KILL dedicated_freight_corridors→building_materials_cost — Rule 21 violation. Intermediary: railway_freight_movement.

**Node: global_shipping_routes**
- FIX global_shipping_routes→palm_oil — type should be AFFECTS (was SUPPLIES). w=0.80 (current=0.85). Reason: Shipping routes do not supply the oil; disruptions on the routes affect the landed price/availability of the oil.
- FIX global_shipping_routes→sunflower_oil — type should be AFFECTS (was SUPPLIES). w=0.80 (current=0.85). Reason: Same as above.
- PASS global_shipping_routes→global_shipping_freight_rates w=0.80 (current=0.8)

**Node: highway_network**
- PASS highway_network→road_freight_movement w=0.95 (current=0.95)
- PASS highway_network→highway_toll_fare w=0.95 (current=0.95)
- PASS highway_network→traffic_noise w=0.85 (current=0.85)
- PASS highway_network→road_traffic_accidents w=0.80 (current=0.8)
- PASS highway_network→tier_2_3_city_expansion w=0.70 (current=0.8) [Adjusted weight: strong but long-term and conditional on other economic factors]
- PASS highway_network→forest_cover w=0.80 (current=0.75) [Adjusted weight: direct physical destruction during construction]
- KILL highway_network→intercity_bus_fare — Rule 21 violation. Intermediary: fuel_consumption / travel_time.
- KILL highway_network→tour_package — Rule 21 violation. Intermediary: travel_time / logistics_costs.

**Node: indian_railways_network**
- PASS indian_railways_network→railway_freight_movement w=0.95 (current=0.95)
- PASS indian_railways_network→irctc_train_ticket w=0.95 (current=0.95)
- PASS indian_railways_network→train_cancellations_and_delays w=0.90 (current=0.9)
- PASS indian_railways_network→seasonal_migrant_labor w=0.85 (current=0.9) [Adjusted weight: strong enabler, but migration also depends on economic push/pull factors]

**Node: major_seaports**
- PASS major_seaports→global_shipping_routes w=0.85 (current=0.85)
- PASS major_seaports→palm_oil w=0.75 (current=0.75)

**Node: municipal_water_grid**
- PASS municipal_water_grid→municipal_water_supply w=0.95 (current=0.95)

**Node: national_power_grid**
- PASS national_power_grid→power_substations w=0.95 (current=0.95)
- KILL national_power_grid→residential_power_supply — Rule 21 violation. Intermediary: power_substations.

**Node: nuclear_power_plants**
- FIX nuclear_power_plants→national_power_grid — type should be SUPPLIES (was PRODUCES). w=0.85 (current=0.8). Reason: Power plants supply physical electricity to the grid; they do not produce the grid itself.
- KILL nuclear_power_plants→residential_power_supply — Rule 21 violation. Intermediary: national_power_grid / power_substations.

**Node: oil_gas_pipelines**
- PASS oil_gas_pipelines→piped_natural_gas w=0.95 (current=0.95)
- PASS oil_gas_pipelines→cng_fuel w=0.95 (current=0.95)

**Node: ondc_platform**
- KILL ondc_platform→data_centers — Rule 21 violation / Invalid Direction. ONDC depends on data centers, not vice versa.
- PASS ondc_platform→food_delivery_services w=0.75 (current=0.75)
- FIX ondc_platform→cab_aggregator_fare — type should be AFFECTS (was COMPETES_WITH). w=0.70 (current=0.7). Reason: A platform competes with other platforms, not with a "fare". It affects the fare.

**Node: optical_fibre_network**
- PASS optical_fibre_network→broadband_network_quality w=0.90 (current=0.9)
- PASS optical_fibre_network→fiber_broadband_tariff w=0.80 (current=0.75) [Adjusted weight: strong direct pricing mechanism based on bandwidth supply]
- KILL optical_fibre_network→tier_2_3_city_expansion — Rule 21 violation. Intermediary: it_sector_jobs / remote_work.

**Node: power_substations**
- PASS power_substations→residential_power_supply w=0.95 (current=0.95)
- FIX power_substations→ev_charging_tariff — type should be AFFECTS (was SUPPLIES). w=0.70 (current=0.85). Reason: Substations supply electricity to the stations, which affects the tariff. They do not supply the tariff itself.

**Node: railway_freight_movement**
- FIX railway_freight_movement→building_materials_cost — type should be AFFECTS (was SUPPLIES). w=0.80 (current=0.75). Reason: Freight movement affects the cost; it does not supply the cost.

**Node: renewable_energy_parks**
- FIX renewable_energy_parks→national_power_grid — type should be SUPPLIES (was PRODUCES). w=0.85 (current=0.85). Reason: Parks supply physical electricity to the grid.
- KILL renewable_energy_parks→electricity_tariff — Rule 21 violation. Intermediary: power_purchase_cost.

**Node: road_freight_movement**
- FIX road_freight_movement→retail_tomato — type should be AFFECTS (was SUPPLIES). w=0.85 (current=0.85). Reason: Freight movement affects the retail price; it does not supply the tomato itself.
- FIX road_freight_movement→retail_onion — type should be AFFECTS (was SUPPLIES). w=0.85 (current=0.85). Reason: Same as above.
- FIX road_freight_movement→retail_potato — type should be AFFECTS (was SUPPLIES). w=0.85 (current=0.85). Reason: Same as above.
- FIX road_freight_movement→building_materials_cost — type should be AFFECTS (was SUPPLIES). w=0.85 (current=0.85). Reason: Freight movement affects the cost.
- FIX road_freight_movement→liquid_milk — type should be AFFECTS (was SUPPLIES). w=0.80 (current=0.8). Reason: Freight movement affects the retail price.
- FIX road_freight_movement→poultry_chicken — type should be AFFECTS (was SUPPLIES). w=0.75 (current=0.75). Reason: Freight movement affects the retail price.
- PASS road_freight_movement→wpi w=0.75 (current=0.7) [Adjusted weight: strong direct pass-through of transport overheads]

**Node: satellite_network**
- PASS satellite_network→broadband_network_quality w=0.65 (current=0.65)
- PASS satellite_network→telecom_towers_network w=0.60 (current=0.6)

**Node: semiconductor_fabs**
- PASS semiconductor_fabs→global_semiconductor_supply_chain w=0.95 (current=0.95)
- KILL semiconductor_fabs→smartphone_device — Rule 21 violation. Intermediary: global_semiconductor_supply_chain.
- KILL semiconductor_fabs→laptop_computer — Rule 21 violation. Intermediary: global_semiconductor_supply_chain.
- KILL semiconductor_fabs→four_wheeler_price — Rule 21 violation. Intermediary: global_semiconductor_supply_chain / auto_manufacturing.
- KILL semiconductor_fabs→two_wheeler_price — Rule 21 violation. Intermediary: global_semiconductor_supply_chain / auto_manufacturing.
- KILL semiconductor_fabs→data_centers — Rule 21 violation. Intermediary: global_semiconductor_supply_chain / server_manufacturing.

**Node: sewage_drainage_network**
- FIX sewage_drainage_network→street_waterlogging — type should be DISRUPTS (was AFFECTS). w=0.90 (current=0.9). Reason: Drainage networks physically block, clear, or halt waterlogging.
- FIX sewage_drainage_network→polluted_surface_water — type should be DISRUPTS (was AFFECTS). w=0.85 (current=0.85). Reason: Proper drainage physically prevents/halts the discharge of untreated effluents.
- KILL sewage_drainage_network→cholera_and_diarrhea — Rule 21 violation. Intermediary: polluted_surface_water / drinking_water_quality.
- PASS sewage_drainage_network→peninsular_river_systems w=0.80 (current=0.75) [Adjusted weight: highly reliable physical degradation mechanism]
- PASS sewage_drainage_network→himalayan_river_systems w=0.80 (current=0.75) [Adjusted weight: highly reliable physical degradation mechanism]

**Node: submarine_internet_cables**
- PASS submarine_internet_cables→optical_fibre_network w=0.90 (current=0.9)
- KILL submarine_internet_cables→broadband_network_quality — Rule 21 violation. Intermediary: optical_fibre_network.

**Node: telecom_spectrum**
- PASS telecom_spectrum→mobile_data_tariff w=0.85 (current=0.85)

**Node: telecom_towers_network**
- KILL telecom_towers_network→telecom_spectrum — Rule 21 violation / Invalid Direction. Towers depend on spectrum, not vice versa.
- FIX telecom_towers_network→mobile_network_quality — type should be SUPPLIES (was AFFECTS). w=0.90 (current=0.9). Reason: Towers physically supply the wireless data/signal that constitutes network quality.
- KILL telecom_towers_network→national_power_grid — Rule 21 violation / Invalid Direction. Towers depend on the grid, not vice versa.
- KILL telecom_towers_network→optical_fibre_network — Rule 21 violation / Invalid Direction. Towers depend on fibre backhaul, not vice versa.
- PASS telecom_towers_network→public_wifi w=0.70 (current=0.7)
- KILL telecom_towers_network→female_labor_force_participation — Rule 21 violation. Intermediary: remote_work / gig_economy_jobs.

**Node: upi_platform**
- PASS upi_platform→upi_transaction_success w=0.95 (current=0.95)
- PASS upi_platform→e_mandate_autopay w=0.90 (current=0.9)
- PASS upi_platform→fastag_wallet w=0.85 (current=0.85)
- KILL upi_platform→telecom_towers_network — Rule 21 violation / Invalid Direction. UPI depends on telecom towers, not vice versa.

**Node: water_treatment_plants**
- PASS water_treatment_plants→municipal_water_grid w=0.95 (current=0.95)
- PASS water_treatment_plants→drinking_water_quality w=0.90 (current=0.9)
- KILL water_treatment_plants→cholera_and_diarrhea — Rule 21 violation. Intermediary: drinking_water_quality.

**Node: aggregate_consumer_confidence**
- KILL aggregate_consumer_confidence→pmi_manufacturing — Rule 21 violation. Intermediary: consumer_spending / manufacturing_orders.
- KILL aggregate_consumer_confidence→pmi_services — Rule 21 violation. Intermediary: discretionary_spending.
- KILL aggregate_consumer_confidence→home_loan_emi — Rule 21 violation. Intermediary: home_loan_demand.
- KILL aggregate_consumer_confidence→two_wheeler_price — Rule 21 violation. Intermediary: two_wheeler_demand.

**Node: autumn_festive_season**
- FIX autumn_festive_season→firecracker — type should be AFFECTS (was PRODUCES). w=0.95 (current=0.95). Reason: A season does not literally manufacture firecrackers; it affects the demand/sales.
- FIX autumn_festive_season→festive_idol — type should be AFFECTS (was PRODUCES). w=0.95 (current=0.95). Reason: Same as above.
- PASS autumn_festive_season→event_and_construction_noise w=0.90 (current=0.9)
- PASS autumn_festive_season→puja_pandal_contribution w=0.90 (current=0.9)
- PASS autumn_festive_season→retail_sugar w=0.85 (current=0.85)
- KILL autumn_festive_season→winter_smog — Rule 21 violation. Intermediary: firecracker.
- PASS autumn_festive_season→irctc_train_ticket w=0.85 (current=0.85)
- PASS autumn_festive_season→aggregate_consumer_confidence w=0.85 (current=0.85)
- PASS autumn_festive_season→butter_and_ghee w=0.80 (current=0.8)
- KILL autumn_festive_season→wedding_venue — Invalid Edge. Overlap in time is correlation, not direct causation.
- KILL autumn_festive_season→index_of_industrial_production — Rule 21 violation. Intermediary: consumer_demand.
- KILL autumn_festive_season→gig_worker_payouts — Rule 21 violation. Intermediary: e_commerce_demand.
- KILL autumn_festive_season→pmi_manufacturing — Rule 21 violation. Intermediary: inventory_build_ups / consumer_demand.
- KILL autumn_festive_season→railway_freight_movement — Rule 21 violation. Intermediary: consumer_demand.
- PASS autumn_festive_season→crowd_emergencies w=0.70 (current=0.6) [Adjusted weight: strong physical risk during massive festive gatherings]

**Node: female_labor_force_participation**
- PASS female_labor_force_participation→india_gdp_growth w=0.75 (current=0.75)
- PASS female_labor_force_participation→domestic_help_wages w=0.70 (current=0.7)
- PASS female_labor_force_participation→private_preschools w=0.70 (current=0.6) [Adjusted weight: strong direct demand driver for childcare]

**Node: india_aging_population**
- PASS india_aging_population→senior_citizen_savings_scheme w=0.85 (current=0.8) [Adjusted weight: highly reliable demographic funding flow]
- PASS india_aging_population→home_monitoring_devices w=0.75 (current=0.7) [Adjusted weight: strong direct retail demand driver]
- PASS india_aging_population→female_labor_force_participation w=0.70 (current=0.65) [Adjusted weight: strong structural disruptor of formal employment for women]
- PASS india_aging_population→health_insurance_premium w=0.75 (current=0.6) [Adjusted weight: strong direct actuarial mechanism]

**Node: india_working_age_population**
- PASS india_working_age_population→epfo_payroll_additions w=0.85 (current=0.85)
- PASS india_working_age_population→skilled_emigration w=0.80 (current=0.8)
- PASS india_working_age_population→urban_unemployment_rate w=0.70 (current=0.6) [Adjusted weight: strong direct labor supply effect]
- PASS india_working_age_population→india_gdp_growth w=0.70 (current=0.6) [Adjusted weight: strong macroeconomic production frontier expansion]

**Node: indian_diaspora_nri**
- PASS indian_diaspora_nri→india_forex_reserves w=0.90 (current=0.9)
- PASS indian_diaspora_nri→investment_property_value w=0.70 (current=0.65) [Adjusted weight: strong direct funding source for real estate]

**Node: islamic_festivals**
- PASS islamic_festivals→mutton_and_lamb w=0.90 (current=0.9)

**Node: major_temple_trusts**
- PASS major_temple_trusts→religious_tourism_demand w=0.80 (current=0.75) [Adjusted weight: strong direct producer of tourism demand]

**Node: mass_boycott_movements**
- PASS mass_boycott_movements→cinema_ticket w=0.80 (current=0.7) [Adjusted weight: strong direct disruption of box office sales]
- PASS mass_boycott_movements→quick_service_restaurants w=0.70 (current=0.65) [Adjusted weight: strong direct disruption of footfall]
- KILL mass_boycott_movements→fii_fpi_flows — Rule 21 violation. Intermediary: corporate_earnings / social_unrest.

**Node: regional_language_movements**
- PASS regional_language_movements→state_governments w=0.70 (current=0.7)
- PASS regional_language_movements→content_moderation_policies w=0.70 (current=0.65) [Adjusted weight: strong direct pressure on platforms]
- PASS regional_language_movements→mass_boycott_movements w=0.70 (current=0.6) [Adjusted weight: strong direct trigger for boycotts]

**Node: regional_new_year_festivals**
- FIX regional_new_year_festivals→irctc_train_ticket — type should be AFFECTS (was PRODUCES). w=0.75 (current=0.65). Reason: Festivals affect ticket demand; they do not literally produce tickets.
- FIX regional_new_year_festivals→retail_gold_investment — type should be AFFECTS (was PRODUCES). w=0.80 (current=0.6). Reason: Festivals affect gold demand; they do not literally produce gold.

**Node: rural_urban_migration_corridors**
- PASS rural_urban_migration_corridors→urban_population_density w=0.90 (current=0.9)
- PASS rural_urban_migration_corridors→pg_and_hostel_fees w=0.80 (current=0.8)

**Node: seasonal_migrant_labor**
- PASS seasonal_migrant_labor→irctc_train_ticket w=0.85 (current=0.8) [Adjusted weight: highly reliable demand spike for unreserved travel]
- FIX seasonal_migrant_labor→construction_worker_wages — type should be AFFECTS (was SUPPLIES). w=0.80 (current=0.75). Reason: Labor supplies labor, which affects wages. It does not supply the wage itself.
- PASS seasonal_migrant_labor→farm_labor_wages w=0.80 (current=0.75) [Adjusted weight: strong direct labor supply effect on wages]
- PASS seasonal_migrant_labor→road_freight_movement w=0.80 (current=0.75) [Adjusted weight: strong direct labor supply for logistics]
- PASS seasonal_migrant_labor→commercial_airports w=0.60 (current=0.6)

## SUMMARY
- Edges reviewed: 138
- PASS (unchanged): 39
- PASS (weight adjusted): 31
- FIX (type change): 25
- KILL: 43
- ADD: 0

## WEIGHT OVERRIDES
```yaml
edges:
- from: us_treasury_yields
  to: fii_fpi_flows
  weight: 0.85
- from: usd_inr_exchange
  to: smartphone_device
  weight: 0.80
- from: usd_inr_exchange
  to: laptop_computer
  weight: 0.80
- from: usd_inr_exchange
  to: wpi
  weight: 0.75
- from: usd_inr_exchange
  to: skilled_emigration
  weight: 0.50
- from: wpi
  to: monetary_policy_committee
  weight: 0.60
- from: aadhaar_database
  to: data_breaches_and_leaks
  weight: 0.75
- from: coal_power_plants
  to: particulate_matter_levels
  weight: 0.85
- from: commercial_airports
  to: noise_pollution
  weight: 0.80
- from: global_shipping_routes
  to: palm_oil
  weight: 0.80
- from: global_shipping_routes
  to: sunflower_oil
  weight: 0.80
- from: highway_network
  to: tier_2_3_city_expansion
  weight: 0.70
- from: highway_network
  to: forest_cover
  weight: 0.80
- from: indian_railways_network
  to: seasonal_migrant_labor
  weight: 0.85
- from: nuclear_power_plants
  to: national_power_grid
  weight: 0.85
- from: optical_fibre_network
  to: fiber_broadband_tariff
  weight: 0.80
- from: power_substations
  to: ev_charging_tariff
  weight: 0.70
- from: railway_freight_movement
  to: building_materials_cost
  weight: 0.80
- from: road_freight_movement
  to: wpi
  weight: 0.75
- from: sewage_drainage_network
  to: peninsular_river_systems
  weight: 0.80
- from: sewage_drainage_network
  to: himalayan_river_systems
  weight: 0.80
- from: autumn_festive_season
  to: crowd_emergencies
  weight: 0.70
- from: female_labor_force_participation
  to: private_preschools
  weight: 0.70
- from: india_aging_population
  to: senior_citizen_savings_scheme
  weight: 0.85
- from: india_aging_population
  to: home_monitoring_devices
  weight: 0.75
- from: india_aging_population
  to: female_labor_force_participation
  weight: 0.70
- from: india_aging_population
  to: health_insurance_premium
  weight: 0.75
- from: india_working_age_population
  to: urban_unemployment_rate
  weight: 0.70
- from: india_working_age_population
  to: india_gdp_growth
  weight: 0.70
- from: indian_diaspora_nri
  to: investment_property_value
  weight: 0.70
- from: major_temple_trusts
  to: religious_tourism_demand
  weight: 0.80
- from: mass_boycott_movements
  to: cinema_ticket
  weight: 0.80
- from: mass_boycott_movements
  to: quick_service_restaurants
  weight: 0.70
- from: regional_language_movements
  to: content_moderation_policies
  weight: 0.70
- from: regional_language_movements
  to: mass_boycott_movements
  weight: 0.70
- from: regional_new_year_festivals
  to: irctc_train_ticket
  weight: 0.75
- from: regional_new_year_festivals
  to: retail_gold_investment
  weight: 0.80
- from: seasonal_migrant_labor
  to: irctc_train_ticket
  weight: 0.85
- from: seasonal_migrant_labor
  to: construction_worker_wages
  weight: 0.80
- from: seasonal_migrant_labor
  to: farm_labor_wages
  weight: 0.80
- from: seasonal_migrant_labor
  to: road_freight_movement
  weight: 0.80
```