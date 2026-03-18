# laterals_1 Weight Re-Rating — Gemini 3.1 Pro

<details><summary>Thinking (4007 chars)</summary>

**Causal Knowledge Graph Calibration for Macro Events in India**

Alright, let's get down to brass tacks. I've got a causal knowledge graph to calibrate, specifically focusing on how macro-level events ripple through the daily lives of Indian citizens. My job is to quantify the "causal pass-through rate" for each edge, reflecting how much a change in the source event impacts the target. I need to output a YAML array, each entry including `from`, `to`, `weight`, and `reasoning`. I'm using a scale, as defined. The edges are as follows, and here's my line of thought, edge by edge:
```yaml
- from: smartphone_device
  to: instant_messaging
  weight: 0.90
  reasoning: "Instant messaging applications structurally require a smartphone to function, resulting in a near 1:1 pass-through in adoption."
- from: mobile_network_quality
  to: upi_transaction_success
  weight: 0.80
  reasoning: "UPI transactions require real-time network connectivity, though retries and Wi-Fi slightly buffer the failure rate."
- from: mobile_network_quality
  to: aadhaar_authentication
  weight: 0.80
  reasoning: "Aadhaar OTP and biometric authentications rely heavily on network stability, making them highly sensitive to connectivity drops."
- from: aadhaar_authentication
  to: digital_document_storage
  weight: 0.90
  reasoning: "Accessing platforms like DigiLocker mandates successful Aadhaar authentication, creating a near 1:1 dependency."
- from: aadhaar_authentication
  to: online_citizen_services
  weight: 0.85
  reasoning: "Most e-Seva portals use Aadhaar as the primary login anchor, making service access highly dependent on authentication success."
- from: upi_ecosystem
  to: transit_and_toll_payments
  weight: 0.70
  reasoning: "While UPI is a major funding source for FASTag and NCMC, alternative methods like net banking and cards dilute the direct pass-through."
- from: upi_ecosystem
  to: recurring_digital_payments
  weight: 0.75
  reasoning: "e-Mandates heavily utilize UPI infrastructure, though credit and debit card autopay options provide some buffer."
- from: personal_data_privacy
  to: telemarketing_and_spam
  weight: 0.45
  reasoning: "Stronger privacy laws reduce spam, but the effect is diluted by existing data leaks and unregulated data brokers."
- from: smartphone_device
  to: social_media_presence
  weight: 0.85
  reasoning: "Active social media engagement is predominantly mobile-first, making it strongly dependent on smartphone access."
- from: smartphone_device
  to: upi_ecosystem
  weight: 0.90
  reasoning: "The UPI ecosystem is inherently designed for mobile devices, creating a near absolute dependency on smartphone ownership."
- from: digital_entertainment
  to: cinema_and_theatre
  weight: 0.50
  reasoning: "OTT adoption noticeably reduces physical cinema visits, though the unique theatrical experience prevents a complete 1:1 substitution."
- from: holiday_accommodation
  to: tour_package
  weight: 0.45
  reasoning: "Hotel tariffs make up a significant portion of tour packages, meaning a 10% rise in room rates translates to roughly a 4-5% increase in total package costs."
- from: rwa_regulation
  to: community_gathering
  weight: 0.60
  reasoning: "Stricter RWA rules noticeably constrain gatherings, though residents often bypass them by hosting events outside the society."
- from: rwa_regulation
  to: festivals_and_celebrations
  weight: 0.55
  reasoning: "RWA restrictions limit the scale of residential festivals, but public celebrations and individual household traditions dilute the overall impact."
- from: festivals_and_celebrations
  to: religious_pilgrimage
  weight: 0.70
  reasoning: "Festive seasons strongly trigger religious travel, though capacity constraints and booking lead times buffer the immediate surge."
- from: festivals_and_celebrations
  to: live_events
  weight: 0.75
  reasoning: "Festivals directly drive the organization of cultural events and concerts, resulting in a strong pass-through to the live entertainment sector."
-

</details>

## Response

```yaml
```yaml
- from: smartphone_device
  to: instant_messaging
  weight: 0.90
  reasoning: "Instant messaging applications structurally require a smartphone to function, resulting in a near 1:1 pass-through in adoption."
- from: mobile_network_quality
  to: upi_transaction_success
  weight: 0.80
  reasoning: "UPI transactions require real-time network connectivity, though retries and Wi-Fi slightly buffer the failure rate."
- from: mobile_network_quality
  to: aadhaar_authentication
  weight: 0.80
  reasoning: "Aadhaar OTP and biometric authentications rely heavily on network stability, making them highly sensitive to connectivity drops."
- from: aadhaar_authentication
  to: digital_document_storage
  weight: 0.90
  reasoning: "Accessing platforms like DigiLocker mandates successful Aadhaar authentication, creating a near 1:1 dependency."
- from: aadhaar_authentication
  to: online_citizen_services
  weight: 0.85
  reasoning: "Most e-Seva portals use Aadhaar as the primary login anchor, making service access highly dependent on authentication success."
- from: upi_ecosystem
  to: transit_and_toll_payments
  weight: 0.70
  reasoning: "While UPI is a major funding source for FASTag and NCMC, alternative methods like net banking and cards dilute the direct pass-through."
- from: upi_ecosystem
  to: recurring_digital_payments
  weight: 0.75
  reasoning: "e-Mandates heavily utilize UPI infrastructure, though credit and debit card autopay options provide some buffer."
- from: personal_data_privacy
  to: telemarketing_and_spam
  weight: 0.45
  reasoning: "Stronger privacy laws reduce spam, but the effect is diluted by existing data leaks and unregulated data brokers."
- from: smartphone_device
  to: social_media_presence
  weight: 0.85
  reasoning: "Active social media engagement is predominantly mobile-first, making it strongly dependent on smartphone access."
- from: smartphone_device
  to: upi_ecosystem
  weight: 0.90
  reasoning: "The UPI ecosystem is inherently designed for mobile devices, creating a near absolute dependency on smartphone ownership."
- from: digital_entertainment
  to: cinema_and_theatre
  weight: 0.50
  reasoning: "OTT adoption noticeably reduces physical cinema visits, though the unique theatrical experience prevents a complete substitution."
- from: holiday_accommodation
  to: tour_package
  weight: 0.45
  reasoning: "Hotel tariffs make up a significant portion of tour packages, meaning a 10% rise in room rates translates to roughly a 4-5% increase in total package costs."
- from: rwa_regulation
  to: community_gathering
  weight: 0.60
  reasoning: "Stricter RWA rules noticeably constrain gatherings, though residents often bypass them by hosting events outside the society."
- from: rwa_regulation
  to: festivals_and_celebrations
  weight: 0.55
  reasoning: "RWA restrictions limit the scale of residential festivals, but public celebrations and individual household traditions dilute the overall impact."
- from: festivals_and_celebrations
  to: religious_pilgrimage
  weight: 0.70
  reasoning: "Festive seasons strongly trigger religious travel, though capacity constraints and booking lead times buffer the immediate surge."
- from: festivals_and_celebrations
  to: live_events
  weight: 0.75
  reasoning: "Festivals directly drive the organization of cultural events and concerts, resulting in a strong pass-through to the live entertainment sector."
- from: wedding_venue
  to: wedding_planning_service
  weight: 0.50
  reasoning: "Venue costs dictate a large portion of the wedding budget, directly influencing the scale and pricing of associated planning services."
- from: public_spaces
  to: community_gathering
  weight: 0.65
  reasoning: "The availability of parks and halls strongly facilitates community events, though private venues serve as alternatives."
- from: tourist_attraction_ticket
  to: tour_package
  weight: 0.20
  reasoning: "Monument entry fees constitute a very small fraction of total holiday expenses, making their impact on overall tour package pricing weak."
- from: religious_pilgrimage
  to: tourism_services
  weight: 0.75
  reasoning: "High pilgrim volumes directly and strongly drive demand for local transport, guides, and hospitality services in temple towns."
- from: liquid_milk
  to: paneer_and_cheese
  weight: 0.85
  reasoning: "Since milk is the primary raw material, changes in procurement costs are passed almost directly into the retail prices of paneer and cheese."
- from: liquid_milk
  to: butter_and_ghee
  weight: 0.85
  reasoning: "Butter and ghee are direct fat derivatives of milk, making their production costs highly sensitive to wholesale milk prices."
- from: wheat_flour
  to: biscuits_and_snacks
  weight: 0.60
  reasoning: "While wheat is a core ingredient, FMCG companies often buffer price shocks through shrinkflation rather than direct price hikes."
- from: wheat_flour
  to: instant_noodles
  weight: 0.60
  reasoning: "Maida is the structural base for noodles, but manufacturers absorb minor cost fluctuations to maintain psychological price points."
- from: palm_oil
  to: biscuits_and_snacks
  weight: 0.55
  reasoning: "Palm oil is heavily used for frying, but its cost impact is diluted by other ingredients and corporate margin absorption."
- from: palm_oil
  to: instant_noodles
  weight: 0.55
  reasoning: "Noodles are pre-fried in palm oil, making margins sensitive to oil prices, though retail prices are kept sticky."
- from: retail_sugar
  to: biscuits_and_snacks
  weight: 0.50
  reasoning: "Sugar is a bulk ingredient in sweet snacks, but its price pass-through is moderated by alternative sweeteners and pack size adjustments."
- from: retail_potato
  to: biscuits_and_snacks
  weight: 0.45
  reasoning: "Potato price spikes affect chip manufacturers, but long-term procurement contracts and shrinkflation significantly dilute the retail price impact."
- from: retail_potato
  to: street_food
  weight: 0.75
  reasoning: "Street vendors have thin margins and cannot absorb potato price hikes, forcing them to quickly raise prices or reduce portion sizes."
- from: retail_onion
  to: street_food
  weight: 0.65
  reasoning: "Onions are a staple base, and while vendors try to substitute or reduce usage during price spikes, costs eventually pass to consumers."
- from: retail_tomato
  to: street_food
  weight: 0.60
  reasoning: "Tomatoes are heavily used, but vendors often substitute with purees or tamarind during price surges, buffering the direct cost impact."
- from: liquid_milk
  to: street_food
  weight: 0.85
  reasoning: "Roadside tea stalls rely entirely on liquid milk with no viable substitutes, leading to near-immediate per-cup price hikes when milk prices rise."
- from: poultry_chicken
  to: quick_service_restaurants
  weight: 0.55
  reasoning: "While chicken is the primary protein, QSR chains use long-term hedging contracts and menu mix adjustments to buffer wholesale price volatility."
- from: tur_dal
  to: chana_dal
  weight: 0.35
  reasoning: "Tur and chana dal are partial substitutes, so a price spike in tur dal shifts some demand, causing a weak but noticeable rise in chana dal prices."
- from: mutton_and_lamb
  to: poultry_chicken
  weight: 0.30
  reasoning: "Mutton is already a premium meat, so price increases only push a small segment of consumers toward chicken, resulting in a weak indirect effect."
- from: food_delivery_services
  to: quick_service_restaurants
  weight: 0.60
  reasoning: "High aggregator commissions force QSRs to mark up their online menu prices noticeably to protect their operational margins."
- from: wheat_flour
  to: street_food
  weight: 0.75
  reasoning: "Maida is the foundational base for many street foods, and informal vendors quickly pass raw material cost increases directly to consumers."
- from: municipal_water_supply
  to: private_water_tanker
  weight: 0.85
  reasoning: "Shortages in municipal water supply create an immediate and near 1:1 surge in demand for private water tankers in urban residential areas."
- from: residential_power_supply
  to: residential_water_supply
  weight: 0.75
  reasoning: "Apartment borewells and municipal pumps structurally depend on electricity, meaning power cuts strongly disrupt water supply unless backed by generators."
- from: electricity_tariff
  to: rwa_maintenance_fees
  weight: 0.35
  reasoning: "Common area electricity is a fraction of total RWA expenses, so a 10% tariff hike only weakly increases overall monthly maintenance bills."
- from: private_water_tanker
  to: rwa_maintenance_fees
  weight: 0.40
  reasoning: "Reliance on expensive tankers inflates society expenses, but the cost is diluted when distributed across all residents in the maintenance bill."
- from: home_construction_and_modification
  to: rental_housing
  weight: 0.30
  reasoning: "Higher construction costs prompt landlords to seek higher rents, but the actual pass-through is weak as rental yields are primarily dictated by local market demand."
- from: piped_natural_gas
  to: lpg_cylinder
  weight: 0.85
  reasoning: "The installation of PNG networks in urban households leads to a near 1:1 structural cannibalization of LPG cylinder demand."
- from: sewage_infrastructure
  to: pest_control_services
  weight: 0.50
  reasoning: "Overflowing sewage noticeably increases local pest populations, driving up household demand for extermination services."
- from: residential_power_supply
  to: electricity_tariff
  weight: 0.60
  reasoning: "Frequent power cuts force reliance on expensive diesel generators, noticeably increasing the effective per-unit power cost for residents."
- from: retail_diesel
  to: highway_bus_travel
  weight: 0.40
  reasoning: "Diesel accounts for roughly 40% of a bus's operating cost, meaning a 10% fuel hike translates to a diluted 4% increase in ticket fares."
- from: cng_fuel
  to: auto_rickshaw_fare
  weight: 0.65
  reasoning: "CNG price hikes strongly pressure driver margins, but regulated meter fares make the actual pass-through to consumers sticky and delayed."
- from: cng_fuel
  to: cab_aggregator_fare
  weight: 0.75
  reasoning: "Cab aggregators dynamically adjust their per-kilometer pricing algorithms to pass on rising CNG fuel costs and maintain driver supply."
- from: road_potholes
  to: vehicle_servicing_cost
  weight: 0.70
  reasoning: "Poor road conditions strongly accelerate suspension and tire wear, directly increasing the frequency of vehicle repair costs."
- from: road_potholes
  to: traffic_congestion
  weight: 0.80
  reasoning: "Damaged roads force vehicles to slow down significantly, acting as a strong and direct catalyst for urban traffic bottlenecks."
- from: traffic_congestion
  to: ride_hailing_services
  weight: 0.85
  reasoning: "Heavy traffic directly triggers surge pricing algorithms and increases ride-time charges for app-based transport services."
- from: vehicle_acquisition
  to: vehicle_insurance_premium
  weight: 0.90
  reasoning: "Motor insurance premiums are calculated as a direct mathematical percentage of the vehicle's Insured Declared Value (IDV)."
- from: highway_toll_fare
  to: highway_bus_travel
  weight: 0.25
  reasoning: "Toll taxes make up a very small percentage of total intercity bus operating costs, resulting in a weak pass-through to passenger fares."
- from: retail_petrol
  to: bike_taxi_fare
  weight: 0.75
  reasoning: "Petrol is the primary variable cost for bike taxis, and aggregators quickly adjust fares upward to sustain driver unit economics."
- from: ev_charging_tariff
  to: e_rickshaw_fare
  weight: 0.50
  reasoning: "Higher charging tariffs increase operating costs, but informal, fixed-route pricing makes fare increases noticeable but sticky."
- from: traffic_congestion
  to: auto_rickshaw_fare
  weight: 0.70
  reasoning: "Increased ride times due to traffic strongly prompt auto drivers to demand higher negotiated fares or rely on waiting charges."
- from: traffic_congestion
  to: cab_aggregator_fare
  weight: 0.85
  reasoning: "Traffic congestion increases the duration of the trip, which directly and mathematically increases the time-based component of cab fares."
- from: mgnrega_wages
  to: farm_labor_wages
  weight: 0.85
  reasoning: "MGNREGA sets the statutory floor wage in rural areas, forcing private farmers to match or exceed it to attract agricultural labor."
- from: mgnrega_wages
  to: construction_worker_wages
  weight: 0.70
  reasoning: "By providing local employment, MGNREGA reduces distress migration to cities, tightening urban labor supply and strongly pushing up construction wages."
- from: minimum_wage
  to: domestic_help_wages
  weight: 0.50
  reasoning: "While domestic help operates in the informal sector, statutory minimum wages create a societal benchmark that noticeably pulls up prevailing rates."
- from: urban_unemployment_rate
  to: food_delivery_payouts
  weight: 0.65
  reasoning: "High urban joblessness increases the supply of gig workers, giving platforms the leverage to noticeably reduce per-delivery payouts."
- from: urban_unemployment_rate
  to: cab_driver_earnings
  weight: 0.65
  reasoning: "A lack of formal jobs drives more individuals to drive cabs, increasing competition and noticeably diluting individual daily earnings."
- from: startup_layoffs
  to: urban_unemployment_rate
  weight: 0.20
  reasoning: "Startup employees represent a tiny fraction of the total urban workforce, making layoffs a very weak driver of the overall macroeconomic unemployment rate."
- from: rural_unemployment_rate
  to: farm_labor_wages
  weight: 0.60
  reasoning: "High rural unemployment indicates an excess supply of labor, which noticeably depresses the daily wages farmers are willing to pay."
- from: it_sector_jobs
  to: urban_unemployment_rate
  weight: 0.35
  reasoning: "While the IT sector is a major formal employer, it only absorbs a specific educated demographic, making its impact on total urban unemployment weak."
- from: small_factory_owner_income
  to: factory_worker_jobs
  weight: 0.60
  reasoning: "Increased MSME profitability provides the capital needed for expansion, noticeably driving the hiring of additional shop floor workers."
- from: defense_agniveer_roles
  to: rural_unemployment_rate
  weight: 0.20
  reasoning: "Given the massive size of the rural workforce, the capped annual intake of Agniveer recruits has a very weak impact on the overall rural unemployment rate."
- from: minimum_wage
  to: factory_worker_jobs
  weight: 0.40
  reasoning: "Higher statutory wages increase formal labor costs, weakly incentivizing employers to automate or shift toward informal contract labor."
- from: working_hours
  to: factory_worker_jobs
  weight: 0.75
  reasoning: "Relaxing labor laws to allow 12-hour shifts strongly reduces the total headcount needed, as fewer workers can cover the same operational hours."
- from: home_loan_emi
  to: personal_income_tax
  weight: 0.30
  reasoning: "Increases in home loan interest payments provide higher Section 24(b) deductions, weakly reducing overall personal income tax liability."
- from: life_insurance
  to: personal_income_tax
  weight: 0.25
  reasoning: "Life insurance premiums offer tax deductions, but the strict 1.5 Lakh limit under Section 80C makes the overall tax reduction weak."
- from: health_insurance_premium
  to: personal_income_tax
  weight: 0.25
  reasoning: "Health insurance provides Section 80D deductions, but statutory caps limit the actual pass-through to total income tax savings."
- from: ppf_investment
  to: personal_income_tax
  weight: 0.25
  reasoning: "PPF contributions lower taxable income, but the effect is heavily diluted by the overarching Section 80C investment ceiling."
- from: nps_portfolio
  to: personal_income_tax
  weight: 0.20
  reasoning: "NPS offers an exclusive 50,000 INR deduction under 80CCD(1B), providing a very weak overall reduction in total tax liability for higher brackets."
- from: fixed_deposits
  to: tds_deduction
  weight: 0.95
  reasoning: "Interest earned on fixed deposits beyond the exemption limit triggers a direct, mathematically mandated Tax Deducted at Source (TDS)."
- from: direct_equity_portfolio
  to: capital_gains_tax
  weight: 0.90
  reasoning: "Profits booked from selling direct equity holdings trigger a direct and unavoidable statutory capital gains tax liability."
- from: mutual_funds
  to: capital_gains_tax
  weight: 0.90
  reasoning: "Redeeming mutual fund units at a profit generates a direct capital gains tax obligation based on strict holding period rules."
- from: investment_property_value
  to: capital_gains_tax
  weight: 0.90
  reasoning: "Selling appreciated real estate directly triggers Long-Term Capital Gains (LTCG) tax, resulting in a near 1:1 pass-through on the taxable amount."
- from: cryptocurrency_portfolio
  to: tds_deduction
  weight: 0.95
  reasoning: "Indian tax regulations mandate a strict, unavoidable 1% TDS on all cryptocurrency sell or trade transactions."
- from: cryptocurrency_portfolio
  to: capital_gains_tax
  weight: 0.95
  reasoning: "Profits from cryptocurrency are taxed at a flat, unavoidable 30% rate, creating a near 1:1 pass-through to tax liability."
- from: ipo_allotment
  to: direct_equity_portfolio
  weight: 0.95
  reasoning: "Successful IPO allotments are directly and entirely credited into the retail investor's demat account as direct equity holdings."
- from: credit_card_dues
  to: personal_loan_emi
  weight: 0.65
  reasoning: "Accumulating high-interest credit card debt strongly pushes consumers to take out personal loans for debt consolidation."
- from: retail_gold_investment
  to: gold_loan_interest
  weight: 0.60
  reasoning: "Holding physical gold enables access to gold loans, noticeably driving the generation of interest obligations during liquidity crunches."
- from: savings_account_balance
  to: mutual_funds
  weight: 0.70
  reasoning: "Surplus liquidity in savings accounts acts as the primary and strong funding source for automated SIPs and mutual fund investments."
- from: savings_account_balance
  to: equity_investments
  weight: 0.70
  reasoning: "Retail investors strongly rely on transferring available savings account balances to their brokerage accounts to fund direct equity purchases."
- from: personal_income_tax
  to: savings_account_balance
  weight: 0.80
  reasoning: "Higher income tax outflows directly and strongly reduce the net disposable income available to be retained in household savings accounts."
- from: home_loan_emi
  to: savings_account_balance
  weight: 0.85
  reasoning: "Monthly auto-debits for home loan EMIs directly and strongly deplete the available liquidity in retail savings accounts."
- from: vector_borne_diseases
  to: blood_tests
  weight: 0.85
  reasoning: "Outbreaks of dengue and malaria directly mandate high volumes of diagnostic blood tests for confirmation and platelet monitoring."
- from: vector_borne_diseases
  to: hospital_beds
  weight: 0.60
  reasoning: "While many cases are managed at home, severe vector-borne infections noticeably drive up hospital and ICU bed occupancy."
- from: respiratory_infections
  to: doctor_consultation
  weight: 0.80
  reasoning: "Surges in airborne diseases like the flu directly and strongly drive patients to seek outpatient doctor consultations."
- from: respiratory_infections
  to: antibiotics
  weight: 0.65
  reasoning: "Bacterial respiratory infections and secondary viral complications noticeably drive the prescription and consumption of antibiotics."
- from: obesity
  to: diabetes
  weight: 0.60
  reasoning: "Excess body fat is a major driver of insulin resistance, noticeably increasing the long-term risk of developing Type 2 diabetes."
- from: diabetes
  to: cardiovascular_health
  weight: 0.55
  reasoning: "Chronic high blood sugar damages blood vessels over time, noticeably deteriorating overall cardiovascular health."
- from: hypertension
  to: heart_disease
  weight: 0.60
  reasoning: "Prolonged high blood pressure exerts continuous strain on arteries, noticeably increasing the probability of ischemic heart disease."
- from: metabolic_disorders
  to: chronic_disease_medication
  weight: 0.85
  reasoning: "Managing metabolic conditions like diabetes requires strict, lifelong adherence to prescription medications like insulin."
- from: cardiovascular_health
  to: chronic_disease_medication
  weight: 0.70
  reasoning: "Improvements in cardiovascular health through lifestyle or surgery strongly reduce the ongoing need for prescription heart medications."
- from: doctor_consultation
  to: prescription_drugs
  weight: 0.85
  reasoning: "Outpatient doctor visits are the primary mechanism for generating medical prescriptions, directly driving pharmaceutical sales."
- from: doctor_consultation
  to: diagnostic_services
  weight: 0.75
  reasoning: "Physicians heavily rely on ordering blood tests and imaging during consultations to confirm diagnoses, strongly driving diagnostic volumes."
- from: mental_health_conditions
  to: mental_health_services
  weight: 0.50
  reasoning: "Rising mental health issues increase demand for therapy, but societal stigma and lack of access dilute the actual pass-through to clinical services."
- from: pediatric_vaccines
  to: respiratory_infections
  weight: 0.75
  reasoning: "Childhood immunization programs build strong herd immunity, significantly reducing the incidence of communicable respiratory diseases."
- from: water_and_food_borne_diseases
  to: childhood_malnutrition
  weight: 0.70
  reasoning: "Repeated bouts of diarrhea strongly cause severe nutrient malabsorption in children, directly leading to chronic stunting and wasting."
- from: surgical_procedures
  to: painkillers_and_antipyretics
  weight: 0.85
  reasoning: "Post-operative recovery protocols universally require analgesics, creating a near 1:1 dependency on painkiller consumption."
- from: oncology
  to: inpatient_care
  weight: 0.80
  reasoning: "Cancer treatments, including intensive chemotherapy and surgeries, strongly require frequent and prolonged hospital admissions."
- from: respiratory_conditions
  to: home_monitoring_devices
  weight: 0.65
  reasoning: "Chronic lung diseases noticeably drive patients to purchase home medical equipment like pulse oximeters and nebulizers for daily management."
- from: maternity_services
  to: surgical_procedures
  weight: 0.70
  reasoning: "The increasing prevalence of institutional deliveries and C-sections strongly boosts overall surgical procedure volumes in hospitals."
- from: diagnostic_services
  to: surgical_procedures
  weight: 0.60
  reasoning: "Medical imaging and pathology results noticeably inform and generate the clinical justification for surgical interventions."
- from: mid_day_meal
  to: government_schools
  weight: 0.75
  reasoning: "The provision of free mid-day meals acts as a strong economic incentive, significantly boosting student enrollment and daily attendance."
- from: free_textbooks_uniforms
  to: government_schools
  weight: 0.65
  reasoning: "Distributing free supplies noticeably reduces out-of-pocket expenses for low-income parents, improving retention rates in government schools."
- from: private_schools
  to: school_fees
  weight: 0.85
  reasoning: "The expansion and premiumization of private school infrastructure are directly and strongly passed on to parents through higher admission fees."
- from: entrance_examinations
  to: test_prep_industry
  weight: 0.85
  reasoning: "The extreme competition and difficulty of college entrance exams directly mandate specialized coaching, strongly driving the test prep industry."
```
```
