# Taxonomy v4 — Impact News Knowledge Graph

## Status: L1s LOCKED (2026-03-13). L2s pending.

---

## Core Design Principles

### 1. Nodes are ENTITIES, not events
- `crude_oil` is a node. `crude_oil_price_hike` is NOT — that's an edge property.
- `monsoon` is a node. `monsoon_deficit` is NOT.
- The graph captures what exists; edges and their properties capture what changed and how.

### 2. Classification Test: "Locus of Interface"
> Can a single citizen directly experience this entity in their body, wallet, schedule, or environment?
- **YES → Impact** (citizen-level entity)
- **NO → Trigger** (system-level entity)

### 3. Impacts can cause other Impacts
- `diesel` (Impact: Transport) → `freight_rates` (Impact: Transport) → `tomato` (Impact: Food)
- The Trigger/Impact split is about the entity's **nature**, not its position in a chain.

### 4. Edges carry properties
- **direction**: positive (+) or negative (-)
- **magnitude**: 0.2 / 0.4 / 0.7 / 0.9
- **delay**: IMMEDIATE / SHORT_TERM / MEDIUM_TERM / LONG_TERM
- **type**: AFFECTS, PRODUCES, REGULATES, DISRUPTS, SUPPLIES, DEPENDS_ON, etc.

---

## L1 Categories (LOCKED)

### 5 Trigger L1s (The System Layer)

| ID | Name | Definition | Examples |
|---|---|---|---|
| T1 | Natural & Planetary Systems | Earth-scale biophysical, meteorological, and geological entities operating independently of human institutions | southwest_monsoon, el_nino, himalayan_tectonic_plates, global_surface_temperature |
| T2 | Institutional & Sovereign Entities | State, regulatory, and geopolitical bodies, plus the statutory frameworks and policies they enforce | rbi, gst_council, supreme_court, us_federal_reserve, ministry_of_road_transport |
| T3 | Macroeconomic & Global Markets | Aggregate economic variables, global commodity markets, and international supply chains | brent_crude, nifty_50, usd_inr_exchange, global_semiconductor_supply_chain, wpi |
| T4 | Technological & Physical Infrastructure | Underlying physical grids, foundational technologies, and national-scale infrastructure | national_power_grid, 5g_spectrum, dedicated_freight_corridors, submarine_internet_cables |
| T5 | Social, Demographic & Cultural Forces | Aggregate human populations, mass social movements, and macro-cultural shifts | india_working_age_population, organized_labor_unions, migration_corridors, major_religious_festivals |

#### Trigger Boundary Rules
- T1 vs T2: If created by nature → T1. If created by government → T2.
- T2 vs T3: If driven by legal fiat/state policy → T2. If driven by market forces → T3.
- T3 vs T4: If it's a price/index/supply chain → T3. If it's a physical grid/platform/network → T4.
- T4 vs T5: If it's man-made infrastructure → T4. If it's collective human behavior → T5.
- T1 vs T5: If it's physical earth → T1. If it's human population dynamics → T5.

### 11 Impact L1s (The Citizen Layer)

| ID | Name | Definition | ~Weight | Examples |
|---|---|---|---|---|
| I1 | Food & Nutrition | All consumable food and beverages for household or out-of-home consumption | ~18% | retail_tomato, atta, swiggy_delivery_fees, dairy_milk, poultry |
| I2 | Housing & Utilities | Physical shelter and the direct utilities required to maintain it | ~10% | residential_rent, municipal_water, electricity_tariff, lpg_cylinder, property_maintenance |
| I3 | Transport & Mobility | Entities related to physical movement of the citizen from A to B | ~10% | retail_petrol, metro_fare, road_potholes, ola_uber_pricing, two_wheeler |
| I4 | Livelihood & Employment | Jobs, wages, hiring, gig work — the citizen's earning capacity | ~12% | it_sector_jobs, tcs_salary, gig_worker_payouts, startup_layoffs, minimum_wage |
| I5 | Personal Finance & Wealth | Loans, EMIs, investments, savings, taxation — the citizen's balance sheet | ~12% | home_loan_emi, mutual_fund_portfolio, retail_gold, income_tax, fixed_deposits |
| I6 | Health & Physiology | Physical and mental wellbeing, plus healthcare services consumed | ~8% | dengue, hospital_beds, retail_insulin, therapy_consultation, generic_medicines |
| I7 | Education & Human Capital | Formal/informal learning, credentialing, and skill acquisition | ~6% | school_fees, neet_exam, edtech_subscription, anganwadi, engineering_cutoffs |
| I8 | Safety & Security | Protection against physical harm, crime, and legal jeopardy | ~4% | neighborhood_crime, traffic_accidents, cyber_fraud, police_response_time, fire_hazard |
| I9 | Local Environmental Quality | Immediate physical environment the citizen breathes, feels, and navigates | ~4% | delhi_aqi, ambient_temperature, noise_pollution, urban_flooding |
| I10 | Digital Life & Connectivity | Citizen's interface with the digital world — access, costs, identity | ~6% | upi_transactions, jio_5g_tariff, aadhaar_auth, whatsapp, data_privacy |
| I11 | Leisure, Culture & Community | Discretionary time/spending on entertainment, social connections, civic participation | ~8% | ipl_tickets, netflix_subscription, rwa_rules, cinema_halls, wedding_venue |

#### Impact Boundary Rules
- I1 vs I2: If you eat/drink it → I1. If you live in it → I2.
- I2 vs I3: If stationary (shelter/utilities) → I2. If movement → I3.
- I3 vs I4: Movement of citizen → I3. Earning money → I4.
- I4 vs I5: Earning/employment → I4. Storing/investing/borrowing money → I5.
- I5 vs I6: Balance sheet impact → I5. Acquiring skills/knowledge → I7.
- I6 vs I7: Health of body/mind → I6. Education/learning → I7.
- I7 vs I8: Physical harm/crime → I8. Acquiring skills → I7.
- I8 vs I9: Physical safety threats → I8. Air/water/noise quality → I9.
- I9 vs I10: Environmental quality → I9. Digital services → I10.
- I10 vs I11: Digital/connectivity → I10. Entertainment/social/community → I11.
- I1 vs I5: If it's food you pay for → both involved; the food entity is I1, the payment mechanism is I5.

---

## Stress Test Results

| Entity | Classification | L1 |
|---|---|---|
| crude_oil | Trigger | T3: Macro & Global Markets |
| diesel | Impact | I3: Transport & Mobility |
| delhi_air_quality | Impact | I9: Local Environmental Quality |
| southwest_monsoon | Trigger | T1: Natural & Planetary |
| rbi_repo_rate | Trigger | T2: Institutional & Sovereign |
| home_loan | Impact | I5: Personal Finance & Wealth |
| bmrcl_metro | Trigger | T4: Tech & Physical Infrastructure |
| tomato | Impact | I1: Food & Nutrition |
| tcs (corporation) | Trigger | T3: Macro & Global Markets |
| tcs_salary | Impact | I4: Livelihood & Employment |
| upi (protocol) | Trigger | T4: Tech & Physical Infrastructure |
| upi_transaction | Impact | I10: Digital Life & Connectivity |
| hospital_beds | Impact | I6: Health & Physiology |
| school_fees | Impact | I7: Education & Human Capital |
| gold | Impact | I5: Personal Finance & Wealth |
| bangalore_traffic | Impact | I3: Transport & Mobility |
| gst | Trigger | T2: Institutional & Sovereign |
| farmer_protest | Trigger | T5: Social, Demographic & Cultural |
| diwali_festival | Trigger | T5: Social, Demographic & Cultural |
| netflix_subscription | Impact | I11: Leisure, Culture & Community |

---

## Example Causal Chains

### Chain 1: Inflation Cascade (Macro → Plate)
```
[T3] Brent Crude → [T2] Oil Marketing Policy → [I3] Retail Diesel →
[I3] Trucking Freight → [I1] Retail Tomato Price → [I5] Household Savings
```

### Chain 2: Climate-Health Nexus (Planet → Lungs)
```
[T1] Post-Monsoon Winds → [T3] Punjab Stubble Burning →
[I9] Delhi AQI → [I6] Pediatric Asthma → [I6] Inhaler Demand
```

### Chain 3: Digital Infrastructure Shock (Regulation → Wallet)
```
[T2] RBI Regulatory Action → [T4] Paytm Payments Bank →
[I10] FASTag Wallet → [I3] Toll Plaza Wait Times → [I4] Gig Worker Earnings
```

---

## Personalization Model

User Profile: `city=bangalore, job=IT, diet=non_veg, loans=home_loan, investments=mutual_funds`

When "US Fed cuts rates by 50bps" happens:
- **I5 (Finance):** NIFTY rises → mutual fund portfolio up. "Your SIP likely sees 2-3% bump."
- **I4 (Livelihood):** US tech budgets expand → IT hiring improves. "Better appraisal conditions next quarter."
- **I5 (Finance):** RBI may follow → home loan EMI drops. "Your ₹50k EMI could decrease."
- **I1 (Food):** Global wheat prices dip slightly → suppressed, low relevance for this user.

---

## Research Context

### Frameworks Referenced
- **OECD Better Life Index** — 11 dimensions (Material + Quality of Life). Closest prior art.
- **COICOP 2018** — 13 divisions of household consumption. Pure spending taxonomy.
- **Social Progress Index** — 12 components across Basic Needs, Foundations, Opportunity.
- **UNDP MPI** — 3 dimensions: Health, Education, Living Standards.
- **EU Social Taxonomy** — Workers, Consumers, Communities stakeholder split.
- **FinCaKG** — Financial causality knowledge graph (academic). Causal chains from text.

### Key Finding
No existing product or framework combines causal chain modeling with citizen-centric impact taxonomy. This is genuinely novel.

---

## Next Steps
1. Generate L2 subcategories for each L1 (MECE within each)
2. Generate L3 leaf nodes under each L2
3. Build edges between Trigger and Impact entities
4. Map user profile attributes to Impact L1s for personalization
5. Rebuild the graph with new taxonomy
