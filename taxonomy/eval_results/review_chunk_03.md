Here is the audit of the edge quality and weights for the provided chunk, based on the Constitution rules.

### auto_rickshaw_fare
**PASS** auto_rickshaw_fare→auto_driver_earnings w=0.80 (current=0.80)
**PASS** auto_rickshaw_fare→e_rickshaw_fare w=0.70 (current=0.70)

### bike_taxi_fare
**PASS** bike_taxi_fare→gig_worker_payouts w=0.80 (current=0.70) [Weight increased: Fares are the direct, near-deterministic source of the payout pool]

### cab_aggregator_fare
**PASS** cab_aggregator_fare→cab_driver_earnings w=0.80 (current=0.80)
**PASS** cab_aggregator_fare→auto_rickshaw_fare w=0.60 (current=0.60)

### city_bus_fare
**KILL** city_bus_fare→government_schools — Rule 21 violation. Intermediary: student_attendance / dropout_rate. (Fares do not directly affect the institution, they affect the students' ability to commute).
**PASS** city_bus_fare→local_train_ticket w=0.50 (current=0.50)

### cng_fuel
**FIX** cng_fuel→auto_rickshaw_fare — type should be AFFECTS (was SUPPLIES). w=0.80 (current=0.80). Reason: A fuel cannot "supply" a fare. It affects the operational cost, which changes the price of the fare.
**FIX** cng_fuel→cab_aggregator_fare — type should be AFFECTS (was SUPPLIES). w=0.70 (current=0.70). Reason: Same as above; fuel prices affect fare prices.

### domestic_flight_ticket
**FIX** domestic_flight_ticket→tour_package — type should be AFFECTS (was PRODUCES). w=0.80 (current=0.80). Reason: Flight tickets do not "literally create" tour packages; they are a cost component that affects the final package price.
**PASS** domestic_flight_ticket→premium_train_fare w=0.70 (current=0.70)

### ev_charging_tariff
**FIX** ev_charging_tariff→e_rickshaw_fare — type should be AFFECTS (was SUPPLIES). w=0.70 (current=0.70). Reason: A tariff (price) cannot supply a fare. It affects the operating cost and thus the fare.

### four_wheeler_price
**FIX** four_wheeler_price→vehicle_insurance_premium — type should be AFFECTS (was PRODUCES). w=0.90 (current=0.90). Reason: The vehicle price mathematically alters the premium amount (price of B), fitting AFFECTS better than PRODUCES.

### highway_toll_fare
**PASS** highway_toll_fare→intercity_bus_fare w=0.80 (current=0.80)
**PASS** highway_toll_fare→fastag_wallet w=0.80 (current=0.80)
**KILL** highway_toll_fare→building_materials_cost — Rule 21 violation. Intermediary: road_freight_rates.
**PASS** highway_toll_fare→cab_aggregator_fare w=0.70 (current=0.50) [Weight increased: Tolls are a direct, 1:1 pass-through cost added to the final cab bill]

### intercity_bus_fare
**FIX** intercity_bus_fare→pilgrimage_package — type should be AFFECTS (was PRODUCES). w=0.70 (current=0.70). Reason: Bus fares are a cost component that affects the package price, they do not literally create the package.

### irctc_train_ticket
**FIX** irctc_train_ticket→pilgrimage_package — type should be AFFECTS (was PRODUCES). w=0.70 (current=0.70). Reason: Train tickets affect the final pricing of the package.

### metro_fare
**PASS** metro_fare→ncmc_smart_card w=0.70 (current=0.70)
**PASS** metro_fare→cab_aggregator_fare w=0.60 (current=0.60)

### parking_fees
**PASS** parking_fees→cab_aggregator_fare w=0.70 (current=0.60) [Weight increased: Airport/station parking fees are a direct, deterministic pass-through to the rider's bill]

### retail_diesel
**FIX** retail_diesel→private_water_tanker — type should be AFFECTS (was SUPPLIES). w=0.80 (current=0.80). Reason: Diesel supplies the truck, but it *affects* the freight cost/service price of the tanker.
**FIX** retail_diesel→intercity_bus_fare — type should be AFFECTS (was SUPPLIES). w=0.80 (current=0.80). Reason: Fuel affects the fare price.
**PASS** retail_diesel→marine_fish w=0.60 (current=0.70) [Weight decreased: Slightly indirect as it passes through trawler operating costs, but acceptable as a primary commodity driver]
**KILL** retail_diesel→building_materials_cost — Rule 21 violation. Intermediary: road_freight_rates.
**FIX** retail_diesel→city_bus_fare — type should be AFFECTS (was SUPPLIES). w=0.70 (current=0.70). Reason: Fuel affects the fare price.
**PASS** retail_diesel→particulate_matter_levels w=0.80 (current=0.70) [Weight increased: Direct, physical combustion mechanism]
**PASS** retail_diesel→waste_collection_services w=0.60 (current=0.60)
**FIX** retail_diesel→cab_aggregator_fare — type should be AFFECTS (was SUPPLIES). w=0.60 (current=0.60). Reason: Fuel affects the fare price.

### retail_petrol
**FIX** retail_petrol→bike_taxi_fare — type should be AFFECTS (was SUPPLIES). w=0.80 (current=0.80). Reason: Fuel affects the fare price.
**FIX** retail_petrol→food_delivery_payouts — type should be AFFECTS (was SUPPLIES). w=0.80 (current=0.80). Reason: Petrol costs affect (reduce) the net take-home payouts; they do not supply them.
**PASS** retail_petrol→repair_service_charges w=0.60 (current=0.60)

### road_potholes
**FIX** road_potholes→vehicle_servicing_cost — type should be AFFECTS (was PRODUCES). w=0.80 (current=0.80). Reason: Potholes produce physical damage, which *affects* the servicing cost.
**PASS** road_potholes→traffic_congestion w=0.80 (current=0.80)
**PASS** road_potholes→road_traffic_accidents w=0.80 (current=0.80)
**KILL** road_potholes→food_delivery_payouts — Rule 21 violation. Intermediary: delivery_efficiency / traffic_congestion.

### traffic_congestion
**PASS** traffic_congestion→traffic_noise w=0.90 (current=0.90)
**PASS** traffic_congestion→cab_aggregator_fare w=0.80 (current=0.80)
**PASS** traffic_congestion→particulate_matter_levels w=0.80 (current=0.80)
**FIX** traffic_congestion→police_response_time — type should be AFFECTS (was DISRUPTS). w=0.70 (current=0.70). Reason: Congestion changes the metric (time) of the response. DISRUPTS is for halting/breaking a node entirely.
**FIX** traffic_congestion→quick_commerce_payouts — type should be AFFECTS (was DISRUPTS). w=0.70 (current=0.70). Reason: Changes the frequency of trips and thus the payout amount.
**FIX** traffic_congestion→food_delivery_payouts — type should be AFFECTS (was DISRUPTS). w=0.60 (current=0.60). Reason: Same as above.
**KILL** traffic_congestion→parking_fees — Rule 21 violation. Intermediary: municipal_corporation_policy.

### traffic_fines
**KILL** traffic_fines→road_traffic_accidents — Rule 21 violation. Intermediary: traffic_rule_compliance / reckless_driving.

### two_wheeler_price
**FIX** two_wheeler_price→vehicle_insurance_premium — type should be AFFECTS (was PRODUCES). w=0.90 (current=0.90). Reason: The price mathematically alters the premium amount.
**KILL** two_wheeler_price→food_delivery_payouts — Rule 21 violation. Intermediary: vehicle_loan_emi.

### agricultural_crop_damage
**FIX** agricultural_crop_damage→retail_onion — type should be AFFECTS (was DISRUPTS). w=0.90 (current=0.90). Reason: Crop damage disrupts the *supply*, which *affects* the retail price.
**FIX** agricultural_crop_damage→retail_tomato — type should be AFFECTS (was DISRUPTS). w=0.90 (current=0.90). Reason: Same as above.
**PASS** agricultural_crop_damage→farm_labor_wages w=0.80 (current=0.80)
**FIX** agricultural_crop_damage→rural_unemployment_rate — type should be AFFECTS (was PRODUCES). w=0.80 (current=0.80). Reason: AFFECTS is the correct verb for changing a statistical rate.

### caste_reservation_movements
**KILL** caste_reservation_movements→upsc_civil_services — Rule 21 violation. Intermediary: reservation_policy / government_legislation.
**KILL** caste_reservation_movements→state_police_jobs — Rule 21 violation. Intermediary: reservation_policy.
**KILL** caste_reservation_movements→government_teacher_jobs — Rule 21 violation. Intermediary: reservation_policy.

### construction_worker_wages
**PASS** construction_worker_wages→construction_labor_wages w=0.90 (current=0.90)

### creator_and_digital_earnings
**KILL** creator_and_digital_earnings→social_media_accounts — Rule 21 violation / Reversed Causality. Earnings do not create or support the accounts; the accounts generate the earnings.

### defense_agniveer_roles
**PASS** defense_agniveer_roles→rural_unemployment_rate w=0.70 (current=0.70)

### domestic_help_wages
**PASS** domestic_help_wages→domestic_help_cost w=0.90 (current=0.90)

### factory_worker_jobs
**PASS** factory_worker_jobs→epf_balance w=0.90 (current=0.90)
**KILL** factory_worker_jobs→asthma — Rule 21 violation. Intermediary: occupational_air_pollution / indoor_air_quality.

### farm_labor_wages
**KILL** farm_labor_wages→retail_rice — Rule 21 violation. Intermediary: farm_gate_price / wholesale_rice_price.
**KILL** farm_labor_wages→retail_onion — Rule 21 violation. Intermediary: farm_gate_price.
**KILL** farm_labor_wages→retail_sugar — Rule 21 violation. Intermediary: wholesale_sugar_price.

### farmer_unions
**KILL** farmer_unions→mgnrega_wages — Rule 21 violation. Intermediary: government_policy / ministry_of_rural_development.

### gig_worker_unions
**PASS** gig_worker_unions→food_delivery_payouts w=0.70 (current=0.70)
**PASS** gig_worker_unions→quick_commerce_payouts w=0.70 (current=0.70)
**PASS** gig_worker_unions→cab_driver_earnings w=0.70 (current=0.70)

### government_teacher_jobs
**PASS** government_teacher_jobs→nps_portfolio w=0.90 (current=0.90)
**PASS** government_teacher_jobs→government_schools w=0.90 (current=0.90)
**KILL** government_teacher_jobs→private_schools — Rule 21 violation. Intermediary: private_school_teacher_jobs. (Government jobs compete with private jobs, not the institution itself).

### it_sector_jobs
**PASS** it_sector_jobs→laptop_computer w=0.85 (current=0.85)
**PASS** it_sector_jobs→startup_jobs w=0.70 (current=0.70)

### it_sector_salary
**PASS** it_sector_salary→personal_income_tax w=0.90 (current=0.90)
**KILL** it_sector_salary→engineering_education — Rule 21 violation. Intermediary: engineering_college_enrollment.
**KILL** it_sector_salary→startup_jobs — Rule 21 violation. Intermediary: startup_operating_costs / startup_salaries.

### maternity_leave_benefits
**KILL** maternity_leave_benefits→factory_worker_jobs — Rule 21 violation. Intermediary: employer_payroll_costs.

### mgnrega_wages
**PASS** mgnrega_wages→farm_labor_wages w=0.80 (current=0.80)

### minimum_wage
**PASS** minimum_wage→construction_worker_wages w=0.90 (current=0.90)
**KILL** minimum_wage→rwa_maintenance_fees — Rule 21 violation. Intermediary: security_guard_wages.
**KILL** minimum_wage→fine_dining_restaurants — Rule 21 violation. Intermediary: restaurant_staff_wages.
**KILL** minimum_wage→city_bus_fare — Rule 21 violation. Intermediary: transport_worker_wages.
**KILL** minimum_wage→factory_worker_jobs — Rule 21 violation. Intermediary: factory_operating_costs.

### organized_labor_unions
**PASS** organized_labor_unions→working_hours w=0.80 (current=0.80)
**KILL** organized_labor_unions→factory_worker_jobs — Rule 21 violation. Intermediary: industrial_strikes / factory_operating_costs.

---

## SUMMARY
- Edges reviewed: 63
- PASS (unchanged): 18
- PASS (weight adjusted): 5
- FIX (type change): 18
- KILL: 22
- ADD: 0

## WEIGHT OVERRIDES
```yaml
edges:
- from: bike_taxi_fare
  to: gig_worker_payouts
  weight: 0.80
- from: highway_toll_fare
  to: cab_aggregator_fare
  weight: 0.70
- from: parking_fees
  to: cab_aggregator_fare
  weight: 0.70
- from: retail_diesel
  to: marine_fish
  weight: 0.60
- from: retail_diesel
  to: particulate_matter_levels
  weight: 0.80
```