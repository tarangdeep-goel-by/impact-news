### Node: curfews_and_section_144
- **FIX** curfews_and_section_144→street_food — type should be DISRUPTS (was DISRUPTS). w=0.90 (current=0.90). Reason: Polarity should be -1. An increase in curfews decreases street food operations.
- **FIX** curfews_and_section_144→street_vendor_income — type should be DISRUPTS (was DISRUPTS). w=0.90 (current=0.90). Reason: Polarity should be -1. An increase in curfews decreases street vendor income.
- **FIX** curfews_and_section_144→cinema_ticket — type should be DISRUPTS (was DISRUPTS). w=0.90 (current=0.90). Reason: Polarity should be -1. An increase in curfews decreases cinema ticket sales.
- **FIX** curfews_and_section_144→gig_worker_payouts — type should be DISRUPTS (was DISRUPTS). w=0.80 (current=0.80). Reason: Polarity should be -1. An increase in curfews decreases gig worker payouts.
- **FIX** curfews_and_section_144→offline_coaching_centers — type should be DISRUPTS (was DISRUPTS). w=0.80 (current=0.80). Reason: Polarity should be -1. An increase in curfews decreases offline coaching center operations.

### Node: police_response_time
- **FIX** police_response_time→assault_and_battery — type should be AFFECTS (was AFFECTS). w=0.70 (current=0.70). Reason: Polarity should be +1. An increase in police response time (meaning a slower response) leads to an increase in the severity and occurrence of assaults.

### Node: railway_accidents
- **FIX** railway_accidents→irctc_train_ticket — type should be DISRUPTS (was DISRUPTS). w=0.80 (current=0.80). Reason: Polarity should be -1. An increase in railway accidents decreases/disrupts IRCTC ticketing.

### Node: riots_and_clashes
- **PASS** riots_and_clashes→curfews_and_section_144 w=0.90 (current=0.90)
- **PASS** riots_and_clashes→internet_shutdowns w=0.90 (current=0.90)
- **FIX** riots_and_clashes→traffic_congestion — type should be PRODUCES (was DISRUPTS). w=0.80 (current=0.80). Reason: Riots physically block roads, which directly *produces* traffic congestion. Polarity remains +1.
- **PASS** riots_and_clashes→assault_and_battery w=0.80 (current=0.80)
- **PASS** riots_and_clashes→fire_hazards w=0.70 (current=0.70)
- **FIX** riots_and_clashes→public_park — type should be DISRUPTS (was DISRUPTS). w=0.70 (current=0.70). Reason: Polarity should be -1. An increase in riots decreases the accessibility and usage of public parks.

### Node: open_drains
- **KILL** open_drains→dengue — Rule 21 violation. Intermediary: stagnant_water_pools. (Open drains produce stagnant water pools, which then breed mosquitoes that cause dengue).
- **KILL** open_drains→malaria — Rule 21 violation. Intermediary: stagnant_water_pools.
- **PASS** open_drains→stagnant_water_pools w=0.80 (current=0.80)
- **PASS** open_drains→public_urination_odour w=0.70 (current=0.70)
- **PASS** open_drains→pest_control_services w=0.70 (current=0.70)

### Node: outdoor_heat
- **PASS** outdoor_heat→residential_electricity w=0.90 (current=0.90)
- **PASS** outdoor_heat→green_vegetables w=0.80 (current=0.80)
- **KILL** outdoor_heat→residential_power_supply — Rule 21 violation. Intermediary: residential_electricity. (The description explicitly states heat triggers massive AC usage, which overloads transformers).
- **PASS** outdoor_heat→poultry_chicken w=0.75 (current=0.75)
- **PASS** outdoor_heat→hospital_beds w=0.75 (current=0.75)
- **PASS** outdoor_heat→liquid_milk w=0.70 (current=0.70)
- **PASS** outdoor_heat→farm_labor_wages w=0.70 (current=0.70)
- **PASS** outdoor_heat→street_vendor_income w=0.70 (current=0.70)
- **PASS** outdoor_heat→polluted_surface_water w=0.60 (current=0.60)

## SUMMARY
- Edges reviewed: 89
- PASS (unchanged): 77
- PASS (weight adjusted): 0
- FIX (type change): 9
- KILL: 3
- ADD: 0

## WEIGHT OVERRIDES
```yaml
edges: []
```