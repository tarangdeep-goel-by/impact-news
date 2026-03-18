# laterals_2 Weight Re-Rating — Gemini 3.1 Pro

<details><summary>Thinking (3795 chars)</summary>

**Recalibrating the Causal Graph: Edge Weight Refinement**

Okay, I need to go through this knowledge graph and refine the edge weights, making sure they accurately reflect the pass-through rates between various Indian macro events and daily life factors; it's important to accurately reflect how each affects the other. I'll need to use the provided scale to capture the nature of each causal connection and make sure it has one, concise reasoning statement, and I'll keep the output in YAML.

*   `government_job_exams` -> `test_prep_industry`: The new weight should be 0.75 because changes in government exams directly drive the test prep industry, though prep cycles add a buffer.
*   `test_prep_industry` -> `coaching_fees`: I'll set the weight to 0.75 since industry expansion drives fee increases.
*   `test_prep_edtech` -> `offline_coaching_centers`: A weight of 0.55 is reasonable, given that edtech growth somewhat disrupts offline centers, but they still have a large degree of stickiness.
*   `k12_edtech` -> `private_tutors`: Considering that K12 edtech is slowly replacing home tutors, I'll use 0.50, as it is a diluted effect.
*   `educational_scholarships` -> `college_university_fees`: The value should be 0.45 because scholarships only reduce fees for a fraction of students.
*   `educational_scholarships` -> `undergraduate_programs`: I will set the weight to 0.35 since a scholarship increase does not necessarily lead to equal enrollment increases.
*   `anganwadi_system` -> `government_schools`: The value is a solid 0.75, because Anganwadi programs have a strong causal connection to government school enrollment.
*   `private_preschools` -> `private_schools`: The weight should be 0.80 since private preschools strongly feed into the private K-12 system.
*   `school_examinations` -> `private_tutors`: A weight of 0.70 is appropriate as exam pressure is a strong driver for tutoring demand.
*   `undergraduate_programs` -> `postgraduate_research`: I'll set it at 0.45 because while UG programs supply PG, a dilution exists because many graduates go directly into employment.
*   `college_university_fees` -> `higher_ed_online_degrees`: The weight should be 0.35 because high fees might push people toward online degrees as a secondary effect.
*   `corporate_upskilling` -> `higher_ed_online_degrees`: I'll use 0.60 as upskilling is a stronger driver for online degrees than high fees.
*   `riots_and_clashes` -> `violent_crime`: A weight of 0.75 is appropriate as riots often produce violent crime, but other factors contribute.
*   `riots_and_clashes` -> `property_crime`: I'll set it to 0.80, given riots directly produce property crimes like arson.
*   `riots_and_clashes` -> `curfews_and_section_144`: I'll keep the value at 0.90, as riots almost always lead to curfews.
*   `curfews_and_section_144` -> `street_harassment`: A value of 0.85 is appropriate because curfews stop street harassment due to physical disruption.
*   `electrocution_hazard` -> `fire_hazards`: The weight should be 0.70 because short circuits are a primary cause of building fires.
*   `deepfake_and_identity_theft` -> `financial_cyber_fraud`: A value of 0.65 reflects the increasing use of deepfakes for fraud, a current and emerging threat.
*   `fir_registration` -> `criminal_litigation_risk`: The value will be 0.95 because FIRs directly initiate litigation.
*   `child_kidnapping` -> `child_abuse_and_pocso`: I'll keep the value at 0.85 as kidnapping frequently leads to abuse.
*   `domestic_violence` -> `violent_crime`: I will set the value to 0.50 as domestic violence is often underreported, therefore the official rates are buffered.
*   `structural_collapse` -> `transit_accidents`: I will make this 0.60 because a collapse *can* lead to accidents, but it is not a primary cause.
*

</details>

## Response

```yaml
- from: government_job_exams
  to: test_prep_industry
  weight: 0.75
  reasoning: "Fluctuations in government job vacancies and exam schedules strongly and directly dictate enrollment volumes in the test prep industry."
- from: test_prep_industry
  to: coaching_fees
  weight: 0.75
  reasoning: "The corporatization and massive marketing overheads of the test prep industry are strongly passed on to students through higher coaching fees."
- from: test_prep_edtech
  to: offline_coaching_centers
  weight: 0.55
  reasoning: "Online platforms noticeably dilute offline enrollments, though the pass-through is buffered by parental preference for physical discipline."
- from: k12_edtech
  to: private_tutors
  weight: 0.50
  reasoning: "Edtech apps substitute some demand for private tutors, but the effect is diluted as many households use both simultaneously."
- from: educational_scholarships
  to: college_university_fees
  weight: 0.45
  reasoning: "Scholarships noticeably reduce net fees for recipients, but the overall pass-through is diluted because they only cover a fraction of the student body."
- from: educational_scholarships
  to: undergraduate_programs
  weight: 0.35
  reasoning: "While scholarships help affordability, gross enrollment is driven by many other socioeconomic factors, making this a weak direct pass-through."
- from: anganwadi_system
  to: government_schools
  weight: 0.75
  reasoning: "Anganwadi centers act as the primary, highly integrated feeder pipeline for primary enrollments in rural government schools."
- from: private_preschools
  to: private_schools
  weight: 0.80
  reasoning: "Private preschools serve as a direct, strong pipeline channeling children into private K-12 school admissions."
- from: school_examinations
  to: private_tutors
  weight: 0.70
  reasoning: "The intense pressure of board examinations strongly drives middle-class households to hire private tutors."
- from: undergraduate_programs
  to: postgraduate_research
  weight: 0.45
  reasoning: "Undergraduate programs supply the applicant pool, but the pass-through is diluted as the majority of graduates enter the workforce instead of research."
- from: college_university_fees
  to: higher_ed_online_degrees
  weight: 0.35
  reasoning: "Rising on-campus fees push some students online, but the effect is weak compared to the primary driver of working professionals seeking flexibility."
- from: corporate_upskilling
  to: higher_ed_online_degrees
  weight: 0.60
  reasoning: "The demand for corporate upskilling noticeably drives enrollments in flexible online degree programs."
- from: riots_and_clashes
  to: violent_crime
  weight: 0.75
  reasoning: "Mob violence during riots strongly and directly generates spikes in formal violent crime incidents like assaults."
- from: riots_and_clashes
  to: property_crime
  weight: 0.80
  reasoning: "Civil unrest strongly correlates with immediate, widespread incidents of arson, looting, and vandalism."
- from: riots_and_clashes
  to: curfews_and_section_144
  weight: 0.90
  reasoning: "Severe public disturbances almost universally force authorities to impose Section 144 and curfews to restore order."
- from: curfews_and_section_144
  to: street_harassment
  weight: 0.85
  reasoning: "Strict curfews physically empty public spaces, resulting in a near 1:1 halt of street-level harassment."
- from: electrocution_hazard
  to: fire_hazards
  weight: 0.70
  reasoning: "Electrical short circuits from poor wiring are a strong, primary ignition source for urban building fires."
- from: deepfake_and_identity_theft
  to: financial_cyber_fraud
  weight: 0.65
  reasoning: "Stolen identities and deepfakes are increasingly and noticeably weaponized to execute targeted financial frauds."
- from: fir_registration
  to: criminal_litigation_risk
  weight: 0.95
  reasoning: "The formal filing of an FIR is a near 1:1 legal trigger that initiates investigative processes and litigation risk."
- from: child_kidnapping
  to: child_abuse_and_pocso
  weight: 0.85
  reasoning: "Abducted children are highly vulnerable to trafficking, leading to a very strong pass-through to severe exploitation and abuse."
- from: domestic_violence
  to: violent_crime
  weight: 0.50
  reasoning: "Domestic abuse frequently involves violence, but the pass-through to formal violent crime statistics is heavily diluted by underreporting."
- from: structural_collapse
  to: transit_accidents
  weight: 0.60
  reasoning: "Bridge and overpass collapses directly cause severe transit accidents, though they represent a smaller fraction of total accidents."
- from: violent_crime
  to: fir_registration
  weight: 0.75
  reasoning: "Severe violent crimes like murder and assault have a strong pass-through to mandatory FIR registrations."
- from: property_crime
  to: fir_registration
  weight: 0.70
  reasoning: "Thefts strongly drive FIR registrations because police complaints are a mandatory prerequisite for claiming insurance."
- from: particulate_matter_levels
  to: ambient_aqi
  weight: 0.95
  reasoning: "PM2.5 and PM10 concentrations dictate the mathematical calculation of the Air Quality Index with a near 1:1 relationship."
- from: particulate_matter_levels
  to: winter_smog
  weight: 0.85
  reasoning: "High particulate matter combined with winter moisture strongly and physically manifests as dense smog."
- from: outdoor_cold
  to: winter_smog
  weight: 0.70
  reasoning: "Winter temperature inversions strongly trap existing pollutants close to the ground, exacerbating smog formation."
- from: street_garbage
  to: open_drains
  weight: 0.75
  reasoning: "Uncollected street garbage strongly contributes to the physical blockage and overflow of open neighborhood drains."
- from: open_drains
  to: polluted_surface_water
  weight: 0.80
  reasoning: "Untreated runoff from open drains is a strong, direct contributor to the toxicity of local lakes and rivers."
- from: street_waterlogging
  to: stagnant_water_pools
  weight: 0.90
  reasoning: "Receding floodwaters from waterlogged streets leave behind stagnant pools with near certainty."
- from: street_garbage
  to: stray_animals
  weight: 0.80
  reasoning: "Overflowing garbage provides a strong, reliable food source that sustains urban stray animal populations."
- from: neighborhood_greenery
  to: outdoor_heat
  weight: 0.50
  reasoning: "Tree canopies noticeably mitigate localized urban heat, though the effect is diluted by broader meteorological temperatures."
- from: neighborhood_greenery
  to: particulate_matter_levels
  weight: 0.40
  reasoning: "Urban flora acts as a physical filter for dust, but the impact on overall ambient PM levels is noticeable but diluted."
- from: neighborhood_greenery
  to: noise_pollution
  weight: 0.35
  reasoning: "Greenery provides a weak acoustic buffer against severe urban traffic and construction noise."
- from: urban_landfills
  to: particulate_matter_levels
  weight: 0.60
  reasoning: "Landfill fires release massive smoke, causing noticeable but episodic spikes in local particulate matter."
- from: urban_landfills
  to: polluted_surface_water
  weight: 0.70
  reasoning: "Toxic leachate from unlined landfills strongly and steadily contaminates nearby groundwater and surface water bodies."
- from: street_waterlogging
  to: traffic_noise
  weight: 0.75
  reasoning: "Waterlogged streets cause severe traffic bottlenecks, which strongly trigger excessive vehicular honking in Indian cities."
- from: winter_smog
  to: ambient_aqi
  weight: 0.95
  reasoning: "Dense winter smog is definitionally composed of trapped pollutants, resulting in a near 1:1 spike in the AQI."
- from: particulate_matter_levels
  to: respiratory_conditions
  weight: 0.80
  reasoning: "High concentrations of fine particulate matter strongly and directly trigger asthma and COPD exacerbations."
- from: stagnant_water_pools
  to: vector_borne_diseases
  weight: 0.75
  reasoning: "Stagnant water provides the primary breeding ground for mosquitoes, strongly driving localized dengue and malaria outbreaks."
- from: ambient_aqi
  to: school_types
  weight: 0.65
  reasoning: "Severe AQI spikes trigger strong, mandated policy responses like physical school closures in affected metro regions."
- from: outdoor_heat
  to: construction_worker_wages
  weight: 0.50
  reasoning: "Extreme heatwaves noticeably halt outdoor labor and reduce wages, though many informal workers are forced to continue working regardless."
- from: retail_diesel
  to: vegetables
  weight: 0.30
  reasoning: "Diesel hikes increase freight costs, but since freight is only a fraction of the final price, the pass-through to retail vegetables is weak."
- from: vehicle_fuel
  to: ride_hailing
  weight: 0.70
  reasoning: "Fuel costs form a massive portion of operational expenses, meaning price hikes strongly eat into ride-hailing driver margins."
- from: vegetables
  to: savings_account_balance
  weight: 0.25
  reasoning: "Vegetable inflation increases grocery budgets, but its overall impact on total household savings depletion is weak and indirect."
- from: it_sector_salary
  to: home_loan_emi
  weight: 0.75
  reasoning: "High disposable IT salaries strongly provide the primary cash flow required to service large urban home loan EMIs."
- from: unemployment_levels
  to: savings_account_balance
  weight: 0.80
  reasoning: "Prolonged unemployment strongly forces households to liquidate deposits and drain savings to survive."
- from: inpatient_care
  to: savings_account_balance
  weight: 0.85
  reasoning: "High out-of-pocket expenditures for sudden hospitalizations strongly and rapidly deplete middle-class savings."
- from: respiratory_infections
  to: construction_and_manual
  weight: 0.70
  reasoning: "Severe flu physically incapacitates manual laborers, strongly resulting in an immediate loss of daily wages."
- from: residential_rent
  to: savings_account_balance
  weight: 0.65
  reasoning: "Steep rent hikes consume a large share of urban paychecks, strongly reducing the capital available for savings."
- from: e_mandate_autopay
  to: mutual_funds
  weight: 0.80
  reasoning: "UPI e-mandates provide the structural automation that strongly drives the consistency of retail mutual fund SIPs."
- from: mobile_connectivity
  to: delivery_and_logistics
  weight: 0.95
  reasoning: "Gig delivery workers have a near 1:1 structural dependency on mobile internet to receive orders and navigate."
- from: civil_unrest
  to: retail_and_trade
  weight: 0.85
  reasoning: "Riots and curfews strongly and immediately force the physical closure of local shops and street vendors."
- from: engineering_education
  to: it_sector_jobs
  weight: 0.80
  reasoning: "Undergraduate engineering programs strongly supply the foundational entry-level talent pool for the IT sector."
- from: firecracker
  to: particulate_matter_levels
  weight: 0.85
  reasoning: "Mass combustion of firecrackers during festivals strongly and directly emits massive volumes of particulate matter."
- from: religious_pilgrimage
  to: railway_travel
  weight: 0.75
  reasoning: "Major pilgrimage seasons strongly drive massive, concentrated surges in railway passenger density and bookings."
- from: traffic_congestion
  to: particulate_matter_levels
  weight: 0.65
  reasoning: "Idling engines in traffic jams strongly produce localized spikes in vehicular exhaust and PM2.5."
- from: social_media_presence
  to: cyberbullying_and_trolling
  weight: 0.60
  reasoning: "Increased social media activity noticeably expands the surface area for users to become targets of cyberbullying."
- from: upi_ecosystem
  to: upi_and_bank_scams
  weight: 0.70
  reasoning: "The ubiquitous adoption of UPI strongly creates the high-velocity attack surface exploited by cybercriminals."
- from: waste_collection_services
  to: street_garbage
  weight: 0.85
  reasoning: "Failures in municipal waste collection strongly and immediately result in garbage accumulation on streets."
- from: urban_flooding
  to: repair_service_charges
  weight: 0.70
  reasoning: "Waterlogged homes strongly drive a sudden surge in demand and pricing for plumbers and electricians."
- from: coaching_fees
  to: savings_account_balance
  weight: 0.60
  reasoning: "Exorbitant competitive exam fees noticeably drain accumulated bank savings of middle-class parents."
- from: weddings_and_milestones
  to: retail_gold_investment
  weight: 0.85
  reasoning: "Cultural mandates for bridal jewelry during wedding seasons strongly drive massive household capital into retail gold."
- from: weddings_and_milestones
  to: personal_loan_emi
  weight: 0.65
  reasoning: "Social pressure to host lavish weddings strongly forces families to take out high-interest personal loans."
- from: retail_sugar
  to: diabetes
  weight: 0.65
  reasoning: "Sustained high consumption of refined sugar is a strong metabolic driver for the onset of Type 2 Diabetes."
- from: instant_noodles
  to: obesity
  weight: 0.45
  reasoning: "Reliance on ultra-processed foods noticeably contributes to obesity, though it is diluted by overall dietary habits."
- from: road_traffic_accidents
  to: hospital_beds
  weight: 0.60
  reasoning: "Severe road accidents noticeably consume critical care trauma beds, straining local inpatient capacity."
- from: home_broadband
  to: ott_subscription
  weight: 0.75
  reasoning: "High-bandwidth home broadband is a strong structural prerequisite for reliable OTT streaming."
- from: fastag_wallet
  to: highway_tolls
  weight: 0.95
  reasoning: "National highway toll collection has a near 1:1 structural and legal dependency on the FASTag ecosystem."
- from: lpg_cylinder
  to: respiratory_conditions
  weight: 0.65
  reasoning: "Unaffordable LPG strongly forces rural households back to burning biomass, producing smoke that exacerbates respiratory issues."
- from: municipal_water_supply
  to: water_and_food_borne_diseases
  weight: 0.80
  reasoning: "Reliable treated municipal water strongly prevents reliance on contaminated groundwater, reducing cholera and typhoid."
- from: urban_rail_transit
  to: residential_rent
  weight: 0.70
  reasoning: "Metro rail expansion strongly increases the connectivity premium of nearby neighborhoods, driving up rents."
- from: it_sector_salary
  to: residential_rent
  weight: 0.75
  reasoning: "Concentrations of high-paying IT jobs strongly inflate local real estate demand and residential rents in tech corridors."
- from: k12_edtech
  to: personal_computing_devices
  weight: 0.60
  reasoning: "The shift to online learning noticeably forces households to purchase personal computing devices."
- from: civil_unrest
  to: urban_bus_transit
  weight: 0.80
  reasoning: "Violent protests frequently target public infrastructure, strongly forcing the suspension of urban bus operations."
- from: childhood_malnutrition
  to: school_examinations
  weight: 0.45
  reasoning: "Chronic malnutrition noticeably impairs cognitive development and exam performance, though diluted by other educational factors."
- from: home_loan_emi
  to: residential_rent
  weight: 0.55
  reasoning: "Expensive EMIs noticeably force more families to remain in the rental market, increasing demand and rents."
- from: festivals_and_celebrations
  to: retail_sugar
  weight: 0.85
  reasoning: "Major Indian festivals strongly trigger massive, concentrated spikes in the consumption of sugar for traditional sweets."
- from: whatsapp_messaging
  to: riots_and_clashes
  weight: 0.75
  reasoning: "The viral spread of misinformation on WhatsApp is a strong, proven catalyst for localized mob violence in India."
- from: startup_layoffs
  to: credit_card_dues
  weight: 0.60
  reasoning: "Sudden job losses noticeably force professionals to rely on revolving credit card debt to maintain lifestyles."
- from: street_food
  to: water_and_food_borne_diseases
  weight: 0.70
  reasoning: "Unhygienic street food preparation is a strong, direct vector for outbreaks of typhoid and gastroenteritis."
- from: public_park
  to: cardiovascular_health
  weight: 0.30
  reasoning: "Access to parks encourages exercise, but the pass-through to improved cardiovascular health is weak and long-term."
- from: investment_and_job_scams
  to: savings_account_balance
  weight: 0.85
  reasoning: "Fraudulent schemes strongly and directly siphon off the life savings of vulnerable victims."
- from: child_abuse_and_pocso
  to: mental_health_conditions
  weight: 0.90
  reasoning: "Severe trauma from child abuse has a near 1:1 pass-through to long-term psychological conditions like PTSD."
- from: urban_flooding
  to: construction_and_manual
  weight: 0.85
  reasoning: "Severe urban flooding strongly and immediately halts outdoor manual labor, resulting in lost daily wages."
- from: equity_investments
  to: startup_ecosystem
  weight: 0.90
  reasoning: "Venture capital provides the critical cash runway that the startup ecosystem has a near 1:1 dependency on to survive."
- from: urban_flooding
  to: vegetables
  weight: 0.80
  reasoning: "Heavy monsoons strongly destroy agricultural yields and disrupt supply chains, causing severe vegetable price spikes."
- from: upi_ecosystem
  to: food_delivery_services
  weight: 0.85
  reasoning: "Food delivery platforms strongly depend on the UPI ecosystem to process high-volume retail transactions seamlessly."
- from: labor_and_trade_unions
  to: civil_unrest
  weight: 0.75
  reasoning: "Industrial strikes and bandh calls by unions strongly create civil unrest through blockades and market shutdowns."
- from: labor_and_trade_unions
  to: crowd_emergencies
  weight: 0.50
  reasoning: "Large worker rallies noticeably risk escalating into crowd crushes, though organizational control often buffers this."
- from: agrarian_collectives
  to: civil_unrest
  weight: 0.80
  reasoning: "Farmer union agitations strongly create civil unrest through sustained highway blockades and border sit-ins."
- from: agrarian_collectives
  to: crowd_emergencies
  weight: 0.55
  reasoning: "Massive farmer marches noticeably risk crowd emergencies, especially during clashes with police."
- from: identity_and_rights_movements
  to: civil_unrest
  weight: 0.80
  reasoning: "Caste and reservation agitations strongly trigger civil unrest through bandhs and public property damage."
- from: identity_and_rights_movements
  to: crowd_emergencies
  weight: 0.60
  reasoning: "Large-scale identity rallies noticeably escalate into violent crowd emergencies when police use force."
- from: labor_and_trade_unions
  to: railway_travel
  weight: 0.85
  reasoning: "Railway worker strikes and rail rokos strongly and directly force mass train cancellations."
- from: labor_and_trade_unions
  to: highway_bus_travel
  weight: 0.85
  reasoning: "Transport worker strikes strongly and directly halt private and state intercity bus services."
- from: agrarian_collectives
  to: railway_travel
  weight: 0.85
  reasoning: "Farmer union rail roko protests strongly blockade tracks, causing mass train cancellations on key routes."
- from: agrarian_collectives
  to: highway_bus_travel
  weight: 0.85
  reasoning: "Farmer union highway blockades strongly disrupt intercity bus services by stranding or rerouting vehicles."
- from: identity_and_rights_movements
  to: railway_travel
  weight: 0.80
  reasoning: "Student and reservation protests strongly target railway infrastructure, causing severe service disruptions."
- from: identity_and_rights_movements
  to: highway_bus_travel
  weight: 0.80
  reasoning: "Bandh calls by rights movements strongly force bus services off the roads in affected regions."
- from: labor_and_trade_unions
  to: construction_and_manual
  weight: 0.35
  reasoning: "Union pressure improves conditions, but the pass-through is weak because the construction sector remains highly informal."
- from: labor_and_trade_unions
  to: domestic_and_care
  weight: 0.25
  reasoning: "Domestic worker unions are nascent, making their current impact on formalizing household help wages very weak."
- from: agrarian_collectives
  to: agriculture_and_allied
  weight: 0.65
  reasoning: "Farmer unions strongly negotiate MSP increases and subsidies, directly improving agricultural income security."
- from: agrarian_collectives
  to: rural_employment_schemes
  weight: 0.55
  reasoning: "Farmer organizations noticeably pressure governments to increase MGNREGA allocations and improve implementation."
- from: identity_and_rights_movements
  to: rural_employment_schemes
  weight: 0.45
  reasoning: "Social justice movements noticeably demand expanded MGNREGA eligibility, though policy pass-through is diluted."
- from: organized_labor_unions
  to: minimum_wage
  weight: 0.65
  reasoning: "Collective bargaining by organized unions strongly pressures state governments to revise statutory minimum wages."
- from: gig_worker_unions
  to: gig_worker_payouts
  weight: 0.50
  reasoning: "Strikes noticeably force aggregator platforms to revise rate cards, though platforms strongly resist these changes."
- from: farmer_unions
  to: retail_tomato
  weight: 0.80
  reasoning: "Highway blockades by farmer unions strongly disrupt perishable supply chains, causing immediate vegetable price spikes."
- from: caste_reservation_movements
  to: medical_entrance
  weight: 0.85
  reasoning: "Quota agitations strongly and directly alter the seat matrices and category cutoffs for competitive exams like NEET."
```
