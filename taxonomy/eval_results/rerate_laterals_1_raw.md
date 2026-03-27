# laterals_1 Weight Re-Rating — Gemini 3.1 Pro

<details><summary>Thinking (3696 chars)</summary>

**Edge Calibration for a Causal Knowledge Graph**

Okay, let's get this done. My primary goal here is to carefully calibrate the edge properties – Weight, Polarity, and Delay – for a knowledge graph designed to represent causal relationships between macro events and their impact on the daily lives of Indian citizens. The output needs to be a clean YAML array with specific fields, adhering strictly to the defined parameters. Absolutely no Markdown fences or extraneous commentary are permitted.

The rules are straightforward, although the nuances of weight assignment require careful consideration. Weight directly represents the strength of the causal influence, with a spectrum ranging from near pass-through (0.85-0.95) to weak or indirect links (0.20-0.40) and edges below 0.20 being eliminated. Polarity is binary: +1 for the same direction and -1 for the opposite. Delay specifies the temporal nature of the impact: IMMEDIATE (hours/days), SHORT_TERM (days/weeks), MEDIUM_TERM (weeks/months), or LONG_TERM (months/years).

With the rules established, I need to evaluate each edge, paying close attention to its current weight, polarity, and delay, and then make adjustments based on my expert assessment of the causal relationship.

*   `liquid_milk` -> `paneer_and_cheese`: Milk is the core ingredient, high pass-through, so a weight of 0.90 with a Short Term Delay is fair.
*   `liquid_milk` -> `butter_and_ghee`: Same logic, direct byproducts and high pass-through, so a weight of 0.90 is what I would expect for this as well.
*   `wheat_flour` -> `biscuits_and_snacks`: Base ingredient, but dilution from packaging and other inputs. 0.75 is more appropriate.
*   `wheat_flour` -> `instant_noodles`: Same reasoning as above. 0.75 should be fine here too.
*   `retail_sugar` -> `biscuits_and_snacks`:  Sugar is a component, but not the only one. 0.60 seems about right.
*   `palm_oil` -> `biscuits_and_snacks`: Major cost, but buffered by pricing power. 0.65 is reasonable.
*   `palm_oil` -> `instant_noodles`: Like biscuits, but FMCG pricing is sticky. 0.65 again.
*   `palm_oil` -> `street_food`: Street vendors are more sensitive to oil prices, so 0.80. IMMEDIATE delay is also best here.
*   `mustard_oil` -> `street_food`: Regional reliance calls for a weight of 0.70. IMMEDIATE delay is fair.
*   `retail_potato` -> `street_food`: Core ingredient with a high pass-through, 0.85, with IMMEDIATE delay.
*   `retail_onion` -> `street_food`: Essential, direct margin impact. 0.80 and IMMEDIATE delay.
*   `poultry_chicken` -> `quick_service_restaurants`: Contracts buffer price shocks; 0.60. MEDIUM_TERM, I think.
*   `retail_tomato` -> `quick_service_restaurants`: QSRs will just remove tomatoes, so 0.50 should work. SHORT_TERM for this one.
*   `paneer_and_cheese` -> `quick_service_restaurants`: High input cost, but fixed menu prices. 0.60 and MEDIUM_TERM.
*   `mutton_and_lamb` -> `fine_dining_restaurants`: Higher margins in fine dining will buffer the raw material costs. So 0.55 and MEDIUM_TERM.
*   `marine_fish` -> `fine_dining_restaurants`: Market price dictates the cost.  A good weight for this will be 0.70 with a SHORT_TERM delay.
*   `garlic_and_ginger` -> `fine_dining_restaurants`: Small percentage of overall cost so 0.30 and a SHORT_TERM delay works for this.
*   `quick_service_restaurants` -> `food_delivery_services`: QSRs drive high volume, so 0.85 with an IMMEDIATE delay will do.
*   `fine_dining_restaurants` -> `food_delivery_services`: Lower volume, higher ticket, 0.50 and IMMEDIATE.
*   `street_food` -> `food_delivery_services`: Growing, lower ticket size so 0.45 and IMMEDIATE.
*   `millets` -> `retail_rice`: Slow substitution, 0.30, and LONG_TERM

</details>

## Response

```yaml
```yaml
- from: liquid_milk
  to: paneer_and_cheese
  weight: 0.90
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Milk is the primary raw material for paneer and cheese, resulting in a near 1:1 cost pass-through during production."
- from: liquid_milk
  to: butter_and_ghee
  weight: 0.90
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Butter and ghee are direct fat-extracted byproducts, making their production costs highly sensitive to milk prices."
- from: wheat_flour
  to: biscuits_and_snacks
  weight: 0.75
  polarity: 1
  delay: SHORT_TERM
  reasoning: "While a foundational ingredient, packaging and marketing costs dilute the direct price pass-through of wheat flour."
- from: wheat_flour
  to: instant_noodles
  weight: 0.75
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Wheat flour is the main structural ingredient, but FMCG pricing power and other inputs buffer the final cost."
- from: retail_sugar
  to: biscuits_and_snacks
  weight: 0.60
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Sugar is a critical input but only one of many ingredients, noticeably diluting its individual cost impact."
- from: palm_oil
  to: biscuits_and_snacks
  weight: 0.65
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Palm oil is a major variable cost for frying, but mass-market snack prices are sticky and buffered by manufacturers."
- from: palm_oil
  to: instant_noodles
  weight: 0.65
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Pre-frying in palm oil makes it a major cost, though FMCG companies absorb minor shocks to maintain price points."
- from: palm_oil
  to: street_food
  weight: 0.80
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Street vendors buy oil frequently and have thin margins, forcing them to pass costs to consumers almost immediately."
- from: mustard_oil
  to: street_food
  weight: 0.70
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Regional street foods rely heavily on mustard oil, and price spikes directly impact vendor daily operating costs."
- from: retail_potato
  to: street_food
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Potatoes are the high-volume base for ubiquitous snacks, making their price spikes a direct threat to vendor margins."
- from: retail_onion
  to: street_food
  weight: 0.80
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Onions are essential for daily street food preparation, and vendors adjust portion sizes or prices immediately during shortages."
- from: poultry_chicken
  to: quick_service_restaurants
  weight: 0.60
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "QSRs use long-term procurement contracts that buffer immediate chicken price shocks, delaying the pass-through to menu prices."
- from: retail_tomato
  to: quick_service_restaurants
  weight: 0.50
  polarity: 1
  delay: SHORT_TERM
  reasoning: "During severe price spikes, QSRs often temporarily remove tomatoes from menus rather than raising overall prices."
- from: paneer_and_cheese
  to: quick_service_restaurants
  weight: 0.60
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Dairy is a high-cost input, but standardized QSR menu pricing absorbs short-term fluctuations."
- from: mutton_and_lamb
  to: fine_dining_restaurants
  weight: 0.55
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Premium meats are expensive, but the high gross margins in fine dining significantly dilute the raw ingredient cost pass-through."
- from: marine_fish
  to: fine_dining_restaurants
  weight: 0.70
  polarity: 1
  delay: SHORT_TERM
  reasoning: "High-grade seafood is often priced dynamically 'as per catch', leading to a stronger and faster cost pass-through."
- from: garlic_and_ginger
  to: fine_dining_restaurants
  weight: 0.30
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Aromatics form the base of gravies but represent a very small percentage of total fine dining operational costs."
- from: quick_service_restaurants
  to: food_delivery_services
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Standardized fast-food chains provide the massive, consistent order volumes that sustain delivery platform operations."
- from: fine_dining_restaurants
  to: food_delivery_services
  weight: 0.50
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Fine dining provides high-ticket orders but at a much lower volume, making its overall impact on delivery platforms moderate."
- from: street_food
  to: food_delivery_services
  weight: 0.45
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Street food is growing on delivery apps but remains a lower-ticket, highly fragmented segment."
- from: millets
  to: retail_rice
  weight: 0.30
  polarity: -1
  delay: LONG_TERM
  reasoning: "Substitution of traditional white rice with millets is a very slow demographic shift and remains weak at a macro level."
- from: millets
  to: wheat_flour
  weight: 0.30
  polarity: -1
  delay: LONG_TERM
  reasoning: "Gluten-free millet substitution is noticeable in urban health niches but barely dents overall wheat flour consumption."
- from: sunflower_oil
  to: mustard_oil
  weight: 0.40
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Cross-elasticity exists during price spikes, but strong regional taste preferences limit widespread substitution."
- from: palm_oil
  to: sunflower_oil
  weight: 0.65
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Commercial kitchens readily substitute expensive sunflower oil with cheaper palm oil to protect their margins."
- from: coffee_powder
  to: tea_leaves
  weight: 0.25
  polarity: -1
  delay: LONG_TERM
  reasoning: "The shift from traditional tea to coffee is a slow, generational lifestyle change with weak immediate substitution effects."
- from: poultry_eggs
  to: biscuits_and_snacks
  weight: 0.40
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Eggs are used in premium baking, but the vast majority of mass-market Indian snacks are eggless, diluting the impact."
- from: chana_dal
  to: street_food
  weight: 0.75
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Besan (from chana dal) is indispensable for fried street snacks, making its price a direct hit to vendor daily costs."
- from: tur_dal
  to: moong_dal
  weight: 0.70
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Indian households actively and quickly substitute expensive tur dal with cheaper moong dal during price surges."
- from: retail_salt
  to: biscuits_and_snacks
  weight: 0.20
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Salt is extremely cheap; even large percentage price changes have a negligible impact on overall snack manufacturing costs."
- from: turmeric_powder
  to: street_food
  weight: 0.30
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Turmeric is used in very small quantities, so price fluctuations have a weak impact on overall street vendor margins."
- from: lpg_cylinder
  to: street_food
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Commercial LPG is a massive daily operating expense for street vendors, directly dictating their profit margins."
- from: lpg_cylinder
  to: fine_dining_restaurants
  weight: 0.50
  polarity: 1
  delay: SHORT_TERM
  reasoning: "While fuel is a necessary cost, the high menu prices in fine dining easily absorb LPG price fluctuations."
- from: retail_diesel
  to: marine_fish
  weight: 0.80
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Diesel for mechanized trawlers is the single largest operational cost in marine fishing, directly impacting catch prices."
- from: outdoor_heat
  to: green_vegetables
  weight: 0.85
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Severe heatwaves cause rapid wilting and field spoilage, instantly and drastically reducing the market supply of leafy greens."
- from: outdoor_heat
  to: liquid_milk
  weight: 0.65
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Thermal stress in dairy cattle noticeably depresses daily milk yields, tightening supply within days."
- from: outdoor_heat
  to: poultry_chicken
  weight: 0.75
  polarity: -1
  delay: IMMEDIATE
  reasoning: "High ambient temperatures cause mass mortality in crowded broiler farms, immediately disrupting chicken supply."
- from: polluted_surface_water
  to: freshwater_fish
  weight: 0.85
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Industrial effluents in lakes and rivers cause immediate mass fish kills, destroying local freshwater stocks."
- from: street_waterlogging
  to: food_delivery_services
  weight: 0.90
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Flooded urban streets physically prevent two-wheeler gig workers from navigating, instantly halting delivery operations."
- from: upi_transaction_success
  to: food_delivery_services
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Food delivery apps are almost entirely dependent on real-time UPI gateways to process orders and dispatch riders."
- from: retail_sugar
  to: diabetes
  weight: 0.75
  polarity: 1
  delay: LONG_TERM
  reasoning: "Chronic high consumption of refined sugar is a strong, direct dietary driver of insulin resistance over time."
- from: biscuits_and_snacks
  to: obesity
  weight: 0.70
  polarity: 1
  delay: LONG_TERM
  reasoning: "Regular consumption of calorie-dense, ultra-processed snacks is a major contributor to rising urban obesity."
- from: instant_noodles
  to: obesity
  weight: 0.60
  polarity: 1
  delay: LONG_TERM
  reasoning: "High-carbohydrate instant noodles provide empty calories, noticeably contributing to weight gain over time."
- from: retail_salt
  to: hypertension
  weight: 0.80
  polarity: 1
  delay: LONG_TERM
  reasoning: "Excessive dietary sodium intake is a direct and strong clinical driver of elevated blood pressure."
- from: street_food
  to: cholera_and_diarrhea
  weight: 0.75
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Unhygienic water used in street food preparation is a primary and immediate vector for waterborne pathogens."
- from: green_vegetables
  to: childhood_malnutrition
  weight: 0.60
  polarity: -1
  delay: LONG_TERM
  reasoning: "Micronutrient intake from greens reduces stunting, but overall caloric and protein intake are also required."
- from: liquid_milk
  to: childhood_malnutrition
  weight: 0.80
  polarity: -1
  delay: LONG_TERM
  reasoning: "Regular milk consumption provides essential complete proteins and calcium, strongly combating childhood wasting."
- from: poultry_eggs
  to: childhood_malnutrition
  weight: 0.75
  polarity: -1
  delay: LONG_TERM
  reasoning: "Eggs are a highly bioavailable source of protein that strongly improves nutritional outcomes in growing children."
- from: street_food
  to: street_vendor_income
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "The daily sale of street food has a near 1:1 relationship with the cash income generated for informal urban vendors."
- from: food_delivery_services
  to: food_delivery_payouts
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "The volume of orders processed by platforms directly and immediately dictates the per-delivery payouts earned by gig workers."
- from: retail_rice
  to: kirana_store_income
  weight: 0.65
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Bulk sales of staples provide consistent baseline revenue, but thin margins dilute their impact on actual store profit."
- from: biscuits_and_snacks
  to: kirana_store_income
  weight: 0.80
  polarity: 1
  delay: SHORT_TERM
  reasoning: "High-margin, fast-moving consumer goods like snacks provide the critical daily cash flow and profit for kirana stores."
- from: liquid_milk
  to: mid_day_meal
  weight: 0.75
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Government procurement of milk is a mandated and highly political component of school mid-day meals in many states."
- from: retail_rice
  to: mid_day_meal
  weight: 0.90
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Fortified retail-grade rice is the absolute bulk caloric foundation supplied to government schools for the scheme."
- from: poultry_eggs
  to: mid_day_meal
  weight: 0.70
  polarity: 1
  delay: SHORT_TERM
  reasoning: "State governments procure millions of eggs weekly to fulfill mandatory protein requirements in school meals."
- from: fine_dining_restaurants
  to: wedding_venue
  weight: 0.40
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Premium catering is a subset of fine dining operations, but it is not the primary driver of wedding venue supply."
- from: food_delivery_services
  to: street_garbage
  weight: 0.80
  polarity: 1
  delay: IMMEDIATE
  reasoning: "The massive volume of single-use plastic containers from food delivery is a primary and immediate contributor to urban litter."
- from: instant_noodles
  to: street_garbage
  weight: 0.65
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Non-biodegradable, multi-layered plastic wrappers from instant noodles are a ubiquitous component of street litter."
- from: biscuits_and_snacks
  to: street_garbage
  weight: 0.70
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Discarded metallic and plastic wrappers from packaged snacks directly increase the volume of urban solid waste."
- from: street_food
  to: street_garbage
  weight: 0.80
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Informal street food stalls generate significant and immediate localized waste through discarded paper plates and cups."
- from: food_delivery_services
  to: traffic_congestion
  weight: 0.45
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Delivery riders add to urban density, but larger vehicles like cars and buses are the primary drivers of congestion."
- from: fine_dining_restaurants
  to: parking_fees
  weight: 0.30
  polarity: 1
  delay: IMMEDIATE
  reasoning: "The concentration of fine dining drives up local valet demand, but this is a highly localized effect with weak macro pass-through."
- from: residential_power_supply
  to: residential_borewells
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Electric pumps are absolutely required to extract groundwater; power cuts instantly halt borewell operations."
- from: residential_power_supply
  to: municipal_water_supply
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Municipal pumping stations require continuous electricity, and grid failures rapidly disrupt pipeline pressure."
- from: municipal_water_supply
  to: private_water_tanker
  weight: 0.90
  polarity: -1
  delay: IMMEDIATE
  reasoning: "There is a direct inverse relationship; when municipal water fails, households immediately call private water tankers."
- from: residential_borewells
  to: private_water_tanker
  weight: 0.85
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Dry or non-functional borewells instantly trigger the need for housing societies to purchase private tanker water."
- from: private_water_tanker
  to: rwa_maintenance_fees
  weight: 0.90
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Housing societies pass the high emergency cost of purchasing private tanker water directly into monthly maintenance bills."
- from: municipal_water_supply
  to: drinking_water_quality
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: "The treatment level of municipal water directly and immediately determines the baseline safety of tap water."
- from: private_water_tanker
  to: drinking_water_quality
  weight: 0.80
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Unregulated private tankers often source hard or contaminated water, directly degrading residential drinking water safety."
- from: sewage_infrastructure
  to: drinking_water_quality
  weight: 0.85
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Leaking underground sewage pipes frequently and directly contaminate parallel municipal drinking water lines."
- from: piped_natural_gas
  to: lpg_cylinder
  weight: 0.95
  polarity: -1
  delay: LONG_TERM
  reasoning: "Expansion of city gas distribution networks directly and permanently replaces household reliance on LPG cylinders."
- from: building_materials_cost
  to: residential_rent
  weight: 0.40
  polarity: 1
  delay: LONG_TERM
  reasoning: "Rents are driven more by local demand and location than by the pure replacement cost of building materials."
- from: residential_rent
  to: pg_and_hostel_fees
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Increases in baseline residential rents force PG operators to pass costs directly to tenants via higher per-bed fees."
- from: waste_collection_services
  to: rwa_maintenance_fees
  weight: 0.75
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Privatized door-to-door garbage collection contracts are fixed costs paid directly from housing society maintenance pools."
- from: domestic_help_cost
  to: rwa_maintenance_fees
  weight: 0.60
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Rising wages for domestic labor increase the cost of hiring cleaning staff for housing society common areas."
- from: repair_service_charges
  to: rwa_maintenance_fees
  weight: 0.40
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Routine plumbing and electrical repairs are a noticeable but relatively small portion of overall RWA budgets."
- from: retail_diesel
  to: private_water_tanker
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Diesel prices directly dictate the freight costs, which are the primary operational expense for private water tankers."
- from: retail_diesel
  to: waste_collection_services
  weight: 0.70
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Fuel costs for garbage trucks directly impact the operational expenses of municipal and private waste collection contracts."
- from: retail_petrol
  to: repair_service_charges
  weight: 0.40
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Higher petrol prices increase commuting costs for independent technicians, but labor remains the primary service cost."
- from: construction_worker_wages
  to: construction_labor_wages
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Macro-level construction wage trends have a near 1:1 pass-through to the daily rates for residential home building."
- from: domestic_help_wages
  to: domestic_help_cost
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Informal sector wage standards directly and immediately determine what households must pay for maids and cooks."
- from: street_waterlogging
  to: sewage_infrastructure
  weight: 0.85
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Flooded streets overwhelm underground drainage networks, disrupting functionality and causing sewage to back up."
- from: polluted_surface_water
  to: municipal_water_supply
  weight: 0.80
  polarity: -1
  delay: IMMEDIATE
  reasoning: "High pollution levels in source rivers (like ammonia spikes) force municipalities to instantly halt water intake and treatment."
- from: building_materials_cost
  to: investment_property_value
  weight: 0.50
  polarity: 1
  delay: LONG_TERM
  reasoning: "Material prices inflate replacement costs, but land value and market demand are the primary drivers of real estate valuation."
- from: drinking_water_quality
  to: cholera_and_diarrhea
  weight: 0.90
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Access to clean, treated drinking water directly and immediately prevents outbreaks of waterborne diarrheal diseases."
- from: drinking_water_quality
  to: typhoid
  weight: 0.85
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Safe residential drinking water eliminates the primary transmission vector for Salmonella typhi."
- from: pg_and_hostel_fees
  to: college_university_fees
  weight: 0.60
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Rising accommodation costs significantly inflate the total cost of higher education for outstation students."
- from: lpg_cylinder
  to: fire_hazards
  weight: 0.75
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Leaking or improperly maintained LPG cylinders are a primary and immediate cause of catastrophic residential fires."
- from: waste_collection_services
  to: street_garbage
  weight: 0.90
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Reliable door-to-door waste collection directly and immediately prevents residents from dumping household trash on streets."
- from: sewage_infrastructure
  to: open_drains
  weight: 0.90
  polarity: -1
  delay: LONG_TERM
  reasoning: "The construction of underground sewage networks directly replaces and permanently eliminates open street drains."
- from: sewage_infrastructure
  to: polluted_surface_water
  weight: 0.85
  polarity: -1
  delay: LONG_TERM
  reasoning: "Functional sewage treatment prevents raw residential effluent from being discharged into local lakes and rivers."
- from: residential_power_supply
  to: broadband_network_quality
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Local ISP distribution switches and home Wi-Fi routers require continuous electricity, dropping connections instantly during power cuts."
- from: rwa_maintenance_fees
  to: community_gathering
  weight: 0.40
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "A portion of society maintenance collections funds events, but it is a highly discretionary and weak causal link."
- from: domestic_help_cost
  to: working_hours
  weight: 0.45
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: "Unaffordable domestic help forces professionals to spend more time on chores, noticeably reducing available working hours."
- from: electricity_tariff
  to: ev_charging_tariff
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Residential electricity rates have a near 1:1 direct pass-through to the cost of charging electric vehicles at home."
- from: retail_diesel
  to: intercity_bus_fare
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Higher retail diesel prices directly increase the operating costs for private intercity buses, leading to higher passenger fares."
- from: retail_diesel
  to: city_bus_fare
  weight: 0.40
  polarity: 1
  delay: LONG_TERM
  reasoning: "State transport fares are highly subsidized and politically sticky, severely delaying and diluting the pass-through of fuel costs."
- from: retail_diesel
  to: cab_aggregator_fare
  weight: 0.65
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Diesel price hikes increase running costs for commercial fleets, eventually prompting aggregators to raise base fares."
- from: cng_fuel
  to: auto_rickshaw_fare
  weight: 0.80
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Spikes in CNG fuel prices trigger union demands for higher fares, though official meter revisions take time to implement."
- from: cng_fuel
  to: cab_aggregator_fare
  weight: 0.75
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Higher CNG prices increase operational costs for city-based cab fleets, leading to upward revisions in ride-hailing fares."
- from: retail_petrol
  to: bike_taxi_fare
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Bike taxi riders rely entirely on petrol, so increased prices directly push up the per-kilometer rates charged on apps."
- from: ev_charging_tariff
  to: e_rickshaw_fare
  weight: 0.75
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Increases in commercial EV charging tariffs raise daily operating costs for drivers, leading to higher passenger fares."
- from: four_wheeler_price
  to: vehicle_insurance_premium
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "The insured declared value (IDV) is a direct percentage of the purchase price, producing a near 1:1 impact on premiums."
- from: two_wheeler_price
  to: vehicle_insurance_premium
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Higher acquisition costs directly increase the replacement value, resulting in a near 1:1 increase in insurance premiums."
- from: road_potholes
  to: vehicle_servicing_cost
  weight: 0.80
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Driving over road potholes causes physical damage to suspensions and tires, directly increasing servicing and repair costs."
- from: road_potholes
  to: traffic_congestion
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Severe road potholes force vehicles to slow down drastically, immediately producing traffic bottlenecks and congestion."
- from: traffic_congestion
  to: cab_aggregator_fare
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Severe traffic congestion instantly triggers surge pricing algorithms due to increased trip duration and lower vehicle availability."
- from: metro_fare
  to: cab_aggregator_fare
  weight: 0.50
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: "Metro networks compete with cabs, but cross-elasticity is moderate as they serve slightly different convenience needs."
- from: city_bus_fare
  to: local_train_ticket
  weight: 0.30
  polarity: -1
  delay: LONG_TERM
  reasoning: "Both transit modes are heavily subsidized and politically controlled, rarely competing dynamically on price alone."
- from: auto_rickshaw_fare
  to: e_rickshaw_fare
  weight: 0.65
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Cheaper e-rickshaws compete for last-mile connectivity, suppressing the ability of traditional autos to hike shared fares."
- from: cab_aggregator_fare
  to: auto_rickshaw_fare
  weight: 0.60
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Cab aggregators offering cheap shared rides force traditional auto-rickshaws to negotiate lower fares to remain competitive."
- from: domestic_flight_ticket
  to: premium_train_fare
  weight: 0.75
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Discounted flight tickets compete directly with dynamic pricing on premium trains, capping how much railways can charge."
- from: highway_toll_fare
  to: intercity_bus_fare
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Increased highway toll fares add directly to route costs, which are quickly passed on to passengers as higher ticket prices."
- from: highway_toll_fare
  to: cab_aggregator_fare
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Highway and state border tolls are added 1:1 directly to the final bill of outstation or airport cab aggregator rides."
- from: parking_fees
  to: cab_aggregator_fare
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "High parking fees at airports and railway stations are passed on 1:1 directly to consumers in their cab aggregator fares."
- from: street_waterlogging
  to: traffic_congestion
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Street waterlogging reduces drivable road width and forces vehicles to crawl, instantly producing severe traffic gridlock."
- from: street_waterlogging
  to: road_potholes
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Stagnant water seeps into asphalt, weakening the road surface and rapidly producing potholes under vehicle weight."
- from: riots_and_clashes
  to: traffic_congestion
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Civil riots and clashes physically block major intersections, causing immediate and severe traffic congestion."
- from: mobile_network_quality
  to: cab_aggregator_fare
  weight: 0.60
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Better network quality ensures accurate driver supply visibility, preventing artificial shortages that trigger surge fares."
- from: cab_aggregator_fare
  to: cab_driver_earnings
  weight: 0.80
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Despite platform commissions, higher fares collected from passengers directly produce higher daily earnings for cab drivers."
- from: auto_rickshaw_fare
  to: auto_driver_earnings
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Meter fares paid by daily commuters in cash have a near 1:1 pass-through to the take-home earnings of auto drivers."
- from: bike_taxi_fare
  to: gig_worker_payouts
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: "The per-ride fares charged for bike taxis directly fund the payouts distributed to gig workers, minus platform cuts."
- from: traffic_congestion
  to: food_delivery_payouts
  weight: 0.70
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Severe traffic delays reduce the number of trips a rider can complete per shift, directly lowering their daily payouts."
- from: road_potholes
  to: road_traffic_accidents
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Deep road potholes cause drivers to swerve unpredictably or lose control, directly and immediately producing accidents."
- from: traffic_congestion
  to: traffic_noise
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Gridlocked traffic leads to excessive honking and prolonged engine idling, directly producing high levels of urban noise."
- from: traffic_congestion
  to: particulate_matter_levels
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Vehicles idling in severe traffic congestion emit concentrated exhaust fumes, instantly elevating local PM2.5 levels."
- from: retail_diesel
  to: particulate_matter_levels
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: "The combustion of retail diesel in commercial vehicles is a primary and direct source of high particulate matter emissions."
- from: domestic_flight_ticket
  to: tour_package
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Domestic flight tickets are a massive cost component of travel itineraries, directly producing higher prices for tour packages."
- from: intercity_bus_fare
  to: pilgrimage_package
  weight: 0.80
  polarity: 1
  delay: SHORT_TERM
  reasoning: "The cost of intercity bus travel is bundled into group travel, directly affecting the pricing of budget religious packages."
- from: irctc_train_ticket
  to: pilgrimage_package
  weight: 0.75
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Railway ticket costs form the baseline transport expense for many religious tours, directly producing the final package cost."
- from: highway_toll_fare
  to: fastag_wallet
  weight: 0.95
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Deductions for higher highway toll fares directly and instantly deplete prepaid balances in users' FASTag wallets 1:1."
- from: metro_fare
  to: ncmc_smart_card
  weight: 0.95
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Increased metro fares result in larger per-trip deductions, directly and instantly depleting stored value on smart cards 1:1."
- from: traffic_congestion
  to: police_response_time
  weight: 0.80
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Severe traffic congestion physically blocks law enforcement vehicles, directly increasing response times to emergencies."
- from: traffic_congestion
  to: quick_commerce_payouts
  weight: 0.75
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Traffic delays reduce the total number of 10-minute grocery deliveries a rider can complete, directly lowering payouts."
- from: retail_petrol
  to: food_delivery_payouts
  weight: 0.85
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Higher retail petrol costs directly eat into the net take-home earnings of food delivery riders who pay for their own fuel."
- from: mgnrega_wages
  to: farm_labor_wages
  weight: 0.85
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Higher guaranteed MGNREGA wages set a strong floor, forcing private agricultural employers to raise farm labor wages."
- from: startup_layoffs
  to: urban_unemployment_rate
  weight: 0.40
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Startups employ a relatively small fraction of the total urban workforce, diluting the macro impact of their layoffs."
- from: it_sector_jobs
  to: startup_jobs
  weight: 0.60
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: "Established IT sector companies compete directly with startups for the same pool of software engineering talent."
- from: minimum_wage
  to: construction_worker_wages
  weight: 0.85
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Revisions in state minimum wage laws directly elevate the baseline pay for manual construction workers."
- from: agricultural_crop_damage
  to: farm_labor_wages
  weight: 0.75
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Severe crop damage reduces harvest volume, leading farmers to hire less labor and depress daily farm wages."
- from: agricultural_crop_damage
  to: rural_unemployment_rate
  weight: 0.80
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Destruction of crops eliminates seasonal harvesting jobs, directly spiking unemployment in rural agricultural belts."
- from: gig_worker_unions
  to: food_delivery_payouts
  weight: 0.65
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Collective bargaining and strikes by gig worker unions force aggregator platforms to revise base pay and incentives upward."
- from: gig_worker_unions
  to: quick_commerce_payouts
  weight: 0.65
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Unionized pressure on 10-minute delivery platforms leads to better per-order payouts and wait-time compensation."
- from: gig_worker_unions
  to: cab_driver_earnings
  weight: 0.65
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Organized protests by ride-hailing unions compel platforms to reduce commission rates, improving net driver earnings."
- from: organized_labor_unions
  to: working_hours
  weight: 0.75
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: "Trade unions actively negotiate and enforce strict limits on maximum working hours and mandatory overtime pay."
- from: quick_commerce_payouts
  to: kirana_store_income
  weight: 0.75
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: "The expansion of quick commerce delivery networks directly cannibalizes the daily sales and income of neighborhood kirana stores."
- from: street_vendor_income
  to: kirana_store_income
  weight: 0.40
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: "Informal street vendors selling fresh produce compete for the same local consumer spend as fixed kirana stores."
- from: defense_agniveer_roles
  to: rural_unemployment_rate
  weight: 0.40
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: "Short-term military recruitment schemes absorb rural youth, but the numbers are small compared to the total population."
- from: engineering_education
  to: it_sector_jobs
  weight: 0.90
  polarity: 1
  delay: LONG_TERM
  reasoning: "Engineering colleges produce the core graduate workforce that supplies talent to the IT sector over a multi-year cycle."
- from: management_education
  to: startup_jobs
  weight: 0.60
  polarity: 1
  delay: LONG_TERM
  reasoning: "Business schools supply operational and strategic talent to startups, though many roles are filled by non-MBAs."
- from: civil_services_exam
  to: upsc_civil_services
  weight: 0.95
  polarity: 1
  delay: LONG_TERM
  reasoning: "The civil services examination pipeline is the absolute, direct prerequisite supplying candidates for central administrative roles."
- from: teaching_eligibility_exams
  to: government_teacher_jobs
  weight: 0.95
  polarity: 1
  delay: LONG_TERM
  reasoning: "Clearing state and central teaching eligibility tests is the mandatory direct prerequisite for government teacher jobs."
- from: upi_transaction_success
  to: street_vendor_income
  weight: 0.85
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Street vendors increasingly rely on successful UPI transactions; gateway failures instantly result in lost sales."
- from: smartphone_device
  to: gig_worker_payouts
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Gig workers absolutely require functional smartphones to receive orders and secure their platform payouts."
- from: wedding_planning_service
  to: urban_company_partner_earnings
  weight: 0.70
  polarity: 1
  delay: SHORT_TERM
  reasoning: "The booming wedding service industry drives massive demand and funds payouts for freelance beauticians on urban platforms."
- from: building_materials_cost
  to: construction_worker_wages
  weight: 0.50
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: "Spikes in cement and steel prices squeeze contractor margins, leading them to suppress daily wages for construction labor."
- from: agricultural_crop_damage
  to: retail_onion
  weight: 0.90
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Crop damage directly reduces the market supply of onions, causing immediate and sharp retail price inflation."
- from: agricultural_crop_damage
  to: retail_tomato
  weight: 0.90
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Unseasonal rains damaging tomato crops lead to severe supply shortages and immediate spikes in retail tomato prices."
- from: working_hours
  to: anxiety_disorders
  weight: 0.75
  polarity: 1
  delay: LONG_TERM
  reasoning: "Prolonged and unregulated working hours directly trigger chronic stress and anxiety disorders over time."
- from: working_hours
  to: hypertension
  weight: 0.65
  polarity: 1
  delay: LONG_TERM
  reasoning: "Excessive working hours and lack of rest contribute directly to the onset of lifestyle conditions like hypertension."
- from: urban_unemployment_rate
  to: burglary_and_theft
  weight: 0.50
  polarity: 1
  delay: MEDIUM_TERM
  reasoning: "Spikes in urban joblessness correlate with increased desperation, leading to higher rates of petty property crime."
- from: retail_gold_investment
  to: direct_equity_portfolio
  weight: 0.40
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: "Physical gold investments compete with direct equity portfolios for discretionary retail investment allocation."
- from: credit_card_dues
  to: bnpl_installments
  weight: 0.50
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Credit card usage competes directly with Buy Now Pay Later (BNPL) installments for short-term unsecured consumer financing."
- from: chit_fund_contribution
  to: recurring_deposits
  weight: 0.50
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: "Informal chit fund contributions compete with formal bank recurring deposits for monthly retail savings."
- from: cryptocurrency_portfolio
  to: direct_equity_portfolio
  weight: 0.40
  polarity: -1
  delay: SHORT_TERM
  reasoning: "High-risk cryptocurrency portfolios compete with direct equity portfolios for speculative retail capital."
- from: endowment_policy_premium
  to: term_insurance_premium
  weight: 0.60
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: "Traditional endowment policies lock up capital, competing directly with pure term insurance premiums for retail budgets."
- from: endowment_policy_premium
  to: equity_mutual_funds
  weight: 0.60
  polarity: -1
  delay: MEDIUM_TERM
  reasoning: "Endowment policies compete with equity mutual funds as long-term wealth accumulation vehicles."
- from: personal_loan_emi
  to: savings_account_balance
  weight: 0.90
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Monthly personal loan EMI auto-deductions directly and instantly deplete available savings account balances."
- from: home_loan_emi
  to: savings_account_balance
  weight: 0.95
  polarity: -1
  delay: IMMEDIATE
  reasoning: "High home loan EMI obligations are massive deductions that significantly reduce the monthly residual savings account balance."
- from: credit_card_dues
  to: savings_account_balance
  weight: 0.90
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Clearing monthly credit card dues directly and instantly reduces the available savings account balance."
- from: bnpl_installments
  to: savings_account_balance
  weight: 0.85
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Auto-debit of BNPL installments directly depletes retail savings account balances."
- from: auto_loan_emi
  to: savings_account_balance
  weight: 0.90
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Monthly auto loan EMI deductions reduce the net disposable liquidity in savings accounts almost 1:1."
- from: microfinance_loan
  to: savings_account_balance
  weight: 0.80
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Repayment of microfinance loans drains the limited savings account balances of low-income borrowers."
- from: direct_equity_portfolio
  to: capital_gains_tax
  weight: 0.95
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Profitable liquidation of direct equity portfolios directly and legally generates capital gains tax liabilities."
- from: equity_mutual_funds
  to: capital_gains_tax
  weight: 0.95
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Redemptions from equity mutual funds directly trigger capital gains tax obligations for the investor."
- from: debt_mutual_funds
  to: capital_gains_tax
  weight: 0.95
  polarity: 1
  delay: SHORT_TERM
  reasoning: "Redemption of debt mutual funds generates direct capital gains tax liabilities based on the holding period."
- from: investment_property_value
  to: capital_gains_tax
  weight: 0.90
  polarity: 1
  delay: LONG_TERM
  reasoning: "Appreciation and subsequent sale of investment properties produce substantial capital gains tax liabilities."
- from: personal_income_tax
  to: savings_account_balance
  weight: 0.95
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Direct deduction of personal income tax (TDS) reduces the net disposable income available in savings accounts 1:1."
- from: term_insurance_premium
  to: personal_income_tax
  weight: 0.70
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Payment of term insurance premiums provides Section 80C deductions, directly lowering personal income tax liabilities."
- from: health_insurance_premium
  to: personal_income_tax
  weight: 0.70
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Health insurance premium payments qualify for Section 80D deductions, reducing overall personal income tax."
- from: epf_balance
  to: personal_income_tax
  weight: 0.75
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Employee contributions to the EPF balance reduce taxable income under Section 80C, lowering personal income tax."
- from: ppf_investment
  to: personal_income_tax
  weight: 0.75
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Investments made into the Public Provident Fund (PPF) directly reduce personal income tax liability via statutory deductions."
- from: nps_portfolio
  to: personal_income_tax
  weight: 0.70
  polarity: -1
  delay: SHORT_TERM
  reasoning: "Contributions to the National Pension System (NPS) provide additional tax deductions, lowering personal income tax."
- from: ipo_allotment
  to: direct_equity_portfolio
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Successful IPO allotments directly and instantly add new shares to an investor's direct equity portfolio."
- from: it_sector_salary
  to: personal_income_tax
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Formal IT sector salaries generate substantial personal income tax liabilities through direct PAYE/TDS mechanisms."
- from: factory_worker_jobs
  to: epf_balance
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Formal employment in factory worker jobs mandates statutory contributions that directly fund EPF balances."
- from: government_teacher_jobs
  to: nps_portfolio
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "State government teacher salaries include mandatory deductions that directly fund their NPS portfolios."
- from: upi_and_bank_scams
  to: savings_account_balance
  weight: 0.95
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Financial cyber frauds and UPI scams directly and instantly siphon funds, depleting victims' savings account balances."
- from: pan_aadhaar_linkage
  to: tds_deduction
  weight: 0.90
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Successful PAN-Aadhaar linkage directly prevents the application of penal 20% higher TDS deduction rates."
- from: e_mandate_autopay
  to: equity_mutual_funds
  weight: 0.95
  polarity: 1
  delay: IMMEDIATE
  reasoning: "Digital e-mandate autopay systems directly execute the recurring transfer of funds into equity mutual fund SIPs 1:1."
- from: e_mandate_autopay
  to: term_insurance_premium
  weight: 0.90
  polarity: 1
  delay: IMMEDIATE
  reasoning: "E-mandate autopay ensures the timely, automated funding of annual term insurance premiums."
- from: burglary_and_theft
  to: retail_gold_investment
  weight: 0.90
  polarity: -1
  delay: IMMEDIATE
  reasoning: "Incidents of residential burglary and theft directly result in the immediate loss of physical retail gold investments."
- from: vehicle_theft
  to: motor_insurance_premium
  weight: 0.75
  polarity: 1
  delay: LONG_TERM
  reasoning: "High rates of vehicle theft in an area drive insurers to increase comprehensive motor insurance premiums at renewal."
- from: road_traffic_accidents
  to: motor_insurance_premium
  weight: 0.85
  polarity: 1
  delay: LONG_TERM
  reasoning: "Accident claims result in the loss of No Claim Bonus (NCB), directly forcing up subsequent motor insurance premiums."
- from: obesity
  to: diabetes
  weight: 0.85
  polarity: 1
  delay: LONG_TERM
  reasoning: "Excess body weight is a strong, direct clinical cause of insulin resistance, leading to type 2 diabetes over time."
- from: obesity
  to: hypertension
  weight: 0.80
  polarity: 1
  delay: LONG_TERM
  reasoning: "Increased body mass forces the heart to work harder, directly elevating blood pressure and causing hypertension."
```
```
