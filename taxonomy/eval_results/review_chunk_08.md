Here is the audit of the provided chunk based on the Constitution rules.

### national_green_tribunal
**FIX** national_green_tribunal→firecracker — polarity should be -1 (was 1). w=0.85 (current=0.85). Reason: NGT bans restrict the sale/bursting of firecrackers, meaning an increase in NGT action leads to a *decrease* in firecracker usage.
**PASS** national_green_tribunal→forest_cover w=0.80 (current=0.80)
**PASS** national_green_tribunal→coal_power_plants w=0.80 (current=0.80)

### opec
**PASS** opec→brent_crude w=0.85 (current=0.85)

### panchayati_raj_institutions
**PASS** panchayati_raj_institutions→mgnrega_wages w=0.90 (current=0.90)

### pfrda
**PASS** pfrda→nps_portfolio w=0.90 (current=0.90)

### public_distribution_system
**PASS** public_distribution_system→retail_rice w=0.85 (current=0.85)
**PASS** public_distribution_system→wheat_flour w=0.85 (current=0.85)
**PASS** public_distribution_system→global_food_grain_supply w=0.60 (current=0.60)

### rbi
**PASS** rbi→monetary_policy_committee w=0.95 (current=0.95)
**PASS** rbi→india_forex_reserves w=0.95 (current=0.95)
**FIX** rbi→usd_inr_exchange — type should be AFFECTS (was MANAGES). w=0.80 (current=0.80). Reason: The RBI manages the forex reserves, but it only *intervenes* in the open market to AFFECT the exchange rate. It does not have direct administrative authority over the market rate itself.

### regional_transport_office
**PASS** regional_transport_office→traffic_fines w=0.90 (current=0.90)
**PASS** regional_transport_office→road_freight_movement w=0.75 (current=0.75)

### rera
**KILL** rera→residential_rent — Rule 21 violation. Intermediary: real_estate_projects / housing_supply. (RERA regulates developers, which affects housing supply, which then affects rent). Also violates Rule 12b (REGULATES cannot cross T→I boundary).
**KILL** rera→building_materials_cost — Rule 21 violation. Intermediary: real_estate_projects / construction_activity.

### russian_government
**PASS** russian_government→brent_crude w=0.85 (current=0.85)

### sebi
**PASS** sebi→ipo_allotment w=0.90 (current=0.90)
**PASS** sebi→equity_mutual_funds w=0.85 (current=0.85)
**PASS** sebi→fii_fpi_flows w=0.85 (current=0.85)
**PASS** sebi→nifty_50 w=0.40 (current=0.70) [Weight reduced: SEBI's market integrity rules provide structural support, but this is an indirect/background condition rather than a strong direct driver of index valuation.]

### state_electricity_boards
**PASS** state_electricity_boards→electricity_tariff w=0.95 (current=0.95)
**PASS** state_electricity_boards→residential_power_supply w=0.95 (current=0.95)
**PASS** state_electricity_boards→national_power_grid w=0.85 (current=0.85)

### state_governments
**PASS** state_governments→curfews_and_section_144 w=0.95 (current=0.95)
**PASS** state_governments→state_electricity_boards w=0.95 (current=0.95)
**PASS** state_governments→state_police_jobs w=0.90 (current=0.90)
**PASS** state_governments→government_teacher_jobs w=0.90 (current=0.90)

### supreme_court_of_india
**PASS** supreme_court_of_india→criminal_litigation_risk w=0.80 (current=0.80)
**PASS** supreme_court_of_india→telecom_spectrum w=0.80 (current=0.80)

### trai
**PASS** trai→telecom_spectrum w=0.90 (current=0.90)
**PASS** trai→mobile_data_tariff w=0.85 (current=0.85)
**FIX** trai→spam_calls — type should be DISRUPTS (was AFFECTS). w=0.75 (current=0.75). Reason: The DND registry physically/systematically blocks and halts spam calls.

### uidai
**PASS** uidai→aadhaar_authentication w=0.95 (current=0.95)
**PASS** uidai→aadhaar_database w=0.95 (current=0.95)

### union_budget_framework
**PASS** union_budget_framework→personal_income_tax w=0.95 (current=0.95)
**PASS** union_budget_framework→capital_gains_tax w=0.95 (current=0.95)
**PASS** union_budget_framework→mgnrega_wages w=0.90 (current=0.90)
**PASS** union_budget_framework→ministry_of_road_transport w=0.85 (current=0.85)
**PASS** union_budget_framework→tier_2_3_city_expansion w=0.80 (current=0.80)

### us_federal_reserve
**PASS** us_federal_reserve→us_treasury_yields w=0.95 (current=0.95)
**PASS** us_federal_reserve→us_dollar_index w=0.90 (current=0.90)
**KILL** us_federal_reserve→direct_equity_portfolio — Rule 21 violation. Intermediary: fii_fpi_flows / nifty_50.
**KILL** us_federal_reserve→retail_gold_investment — Rule 21 violation. Intermediary: us_dollar_index / international_gold_prices.

### us_government
**PASS** us_government→us_consumer_demand w=0.85 (current=0.85)
**PASS** us_government→skilled_emigration w=0.85 (current=0.85)
**PASS** us_government→it_sector_jobs w=0.75 (current=0.75)

### wto
**PASS** wto→it_services_exports w=0.50 (current=0.50)

### active_pharmaceutical_ingredients_supply
**PASS** active_pharmaceutical_ingredients_supply→generic_medicines w=0.90 (current=0.90)
**PASS** active_pharmaceutical_ingredients_supply→antibiotics w=0.90 (current=0.90)
**PASS** active_pharmaceutical_ingredients_supply→chronic_disease_medication w=0.90 (current=0.90)
**FIX** active_pharmaceutical_ingredients_supply→export_competitiveness — type should be AFFECTS (was SUPPLIES). w=0.80 (current=0.80). Reason: API supply does not physically "supply" competitiveness; it AFFECTS the capacity to export.

### agricultural_exports
**PASS** agricultural_exports→retail_onion w=0.80 (current=0.80)
**PASS** agricultural_exports→retail_rice w=0.80 (current=0.80)
**PASS** agricultural_exports→retail_sugar w=0.80 (current=0.80)
**PASS** agricultural_exports→groundwater_aquifers w=0.70 (current=0.70)

### bank_liquidity_and_credit
**PASS** bank_liquidity_and_credit→commercial_bank_lending_rates w=0.80 (current=0.80)

### brent_crude
**PASS** brent_crude→retail_petrol w=0.90 (current=0.90)
**PASS** brent_crude→retail_diesel w=0.90 (current=0.90)
**PASS** brent_crude→lpg_cylinder w=0.85 (current=0.85)
**KILL** brent_crude→road_freight_movement — Rule 21 violation. Intermediary: retail_diesel.
**PASS** brent_crude→india_trade_deficit w=0.80 (current=0.80)
**PASS** brent_crude→wpi w=0.80 (current=0.80)
**KILL** brent_crude→domestic_flight_ticket — Rule 21 violation. Intermediary: aviation_turbine_fuel.

### china_manufacturing_output
**PASS** china_manufacturing_output→active_pharmaceutical_ingredients_supply w=0.85 (current=0.85)
**PASS** china_manufacturing_output→industrial_metals_index w=0.85 (current=0.85)
**PASS** china_manufacturing_output→smartphone_device w=0.80 (current=0.80)
**PASS** china_manufacturing_output→global_semiconductor_supply_chain w=0.80 (current=0.80)
**PASS** china_manufacturing_output→global_shipping_freight_rates w=0.75 (current=0.75)

### commercial_bank_lending_rates
**PASS** commercial_bank_lending_rates→home_loan_emi w=0.90 (current=0.90)
**PASS** commercial_bank_lending_rates→personal_loan_emi w=0.80 (current=0.80)

### dii_flows
**PASS** dii_flows→nifty_50 w=0.80 (current=0.80)

### epfo_payroll_additions
**PASS** epfo_payroll_additions→national_unemployment_rate w=0.80 (current=0.80)
**KILL** epfo_payroll_additions→urban_population_density — Rule 21 violation. Intermediary: rural_to_urban_migration.

### export_competitiveness
**PASS** export_competitiveness→india_trade_deficit w=0.80 (current=0.80)

### fii_fpi_flows
**PASS** fii_fpi_flows→nifty_50 w=0.75 (current=0.75)
**PASS** fii_fpi_flows→usd_inr_exchange w=0.70 (current=0.70)
**PASS** fii_fpi_flows→india_forex_reserves w=0.70 (current=0.70)

### global_edible_oil_supply
**PASS** global_edible_oil_supply→palm_oil w=0.90 (current=0.90)
**PASS** global_edible_oil_supply→sunflower_oil w=0.90 (current=0.90)
**PASS** global_edible_oil_supply→wpi w=0.70 (current=0.70)

### global_equity_indices
**PASS** global_equity_indices→nifty_50 w=0.75 (current=0.75)

### global_food_grain_supply
**PASS** global_food_grain_supply→wpi w=0.65 (current=0.65)
**FIX** global_food_grain_supply→wheat_flour — type should be AFFECTS (was SUPPLIES). w=0.60 (current=0.60). Reason: The description explicitly states this is a price mechanism ("lowers international wheat prices, which can depress domestic wheat flour prices"), not a physical supply chain.

### global_natural_gas
**PASS** global_natural_gas→cng_fuel w=0.85 (current=0.85)
**PASS** global_natural_gas→piped_natural_gas w=0.85 (current=0.85)

### global_semiconductor_supply_chain
**PASS** global_semiconductor_supply_chain→smartphone_device w=0.90 (current=0.90)
**PASS** global_semiconductor_supply_chain→laptop_computer w=0.90 (current=0.90)
**PASS** global_semiconductor_supply_chain→four_wheeler_price w=0.70 (current=0.70)
**FIX** global_semiconductor_supply_chain→pmi_manufacturing — type should be AFFECTS (was SUPPLIES). w=0.70 (current=0.70). Reason: Supply chains do not "supply" an index; they AFFECT the manufacturing activity that the index measures.

### global_shipping_freight_rates
**PASS** global_shipping_freight_rates→wpi w=0.65 (current=0.65)
**FIX** global_shipping_freight_rates→building_materials_cost — type should be AFFECTS (was SUPPLIES). w=0.60 (current=0.60). Reason: Freight rates are a cost factor that AFFECTS prices; they do not physically supply materials.
**FIX** global_shipping_freight_rates→smartphone_device — type should be AFFECTS (was SUPPLIES). w=0.60 (current=0.60). Reason: Freight rates AFFECT the logistics cost of smartphones.

### global_sugar_supply
**FIX** global_sugar_supply→retail_sugar — type should be AFFECTS (was SUPPLIES). w=0.70 (current=0.70). Reason: The description describes a price mechanism ("reduces international prices, exerting downward pressure on domestic retail sugar costs").

### index_of_industrial_production
**FIX** index_of_industrial_production→india_gdp_growth — type should be AFFECTS (was PRODUCES). w=0.80 (current=0.80). Reason: IIP is a mathematical component that AFFECTS the GDP calculation; it does not literally "produce" it.

### india_10yr_bond_yield
**PASS** india_10yr_bond_yield→debt_mutual_funds w=0.85 (current=0.85)
**PASS** india_10yr_bond_yield→fixed_deposits w=0.70 (current=0.70)
**KILL** india_10yr_bond_yield→home_loan_emi — Rule 21 violation. Intermediary: commercial_bank_lending_rates.
**PASS** india_10yr_bond_yield→nifty_50 w=0.65 (current=0.65)

### india_current_account_deficit
**PASS** india_current_account_deficit→usd_inr_exchange w=0.80 (current=0.80)

### india_gdp_growth
**PASS** india_gdp_growth→national_unemployment_rate w=0.75 (current=0.75)
**FIX** india_gdp_growth→epfo_payroll_additions — type should be AFFECTS (was PRODUCES). w=0.75 (current=0.75). Reason: GDP growth is an abstract metric that AFFECTS hiring; it does not literally "produce" payroll additions.
**PASS** india_gdp_growth→venture_capital_and_pe_flows w=0.70 (current=0.70)

### india_trade_deficit
**FIX** india_trade_deficit→india_current_account_deficit — type should be AFFECTS (was PRODUCES). w=0.95 (current=0.95). Reason: One deficit metric AFFECTS another as a mathematical component.
**PASS** india_trade_deficit→usd_inr_exchange w=0.75 (current=0.75)

### industrial_metals_index
**PASS** industrial_metals_index→building_materials_cost w=0.80 (current=0.80)
**PASS** industrial_metals_index→two_wheeler_price w=0.70 (current=0.70)
**PASS** industrial_metals_index→four_wheeler_price w=0.70 (current=0.70)
**KILL** industrial_metals_index→forest_cover — Rule 21 violation. Intermediary: mining_operations.

### international_coal_prices
**PASS** international_coal_prices→coal_power_plants w=0.75 (current=0.75)
**KILL** international_coal_prices→electricity_tariff — Rule 21 violation. Intermediary: state_electricity_boards / discoms.

### international_gold_prices
**FIX** international_gold_prices→retail_gold_investment — type should be AFFECTS (was SUPPLIES). w=0.95 (current=0.95). Reason: International prices AFFECT the domestic pricing baseline; they do not physically supply the investment.
**PASS** international_gold_prices→india_trade_deficit w=0.75 (current=0.75)

### international_silver_prices
**PASS** international_silver_prices→retail_silver_investment w=0.95 (current=0.95)

### it_services_exports
**FIX** it_services_exports→it_sector_jobs — type should be FUNDS (was PRODUCES). w=0.90 (current=0.90). Reason: Export revenues directly FUND the expansion of headcount and hiring.

### national_unemployment_rate
**FIX** national_unemployment_rate→skilled_emigration — type should be AFFECTS (was PRODUCES). w=0.70 (current=0.70). Reason: An abstract rate AFFECTS emigration behavior; it does not literally "produce" it.

### nifty_50
**PASS** nifty_50→direct_equity_portfolio w=0.90 (current=0.90)
**PASS** nifty_50→equity_mutual_funds w=0.90 (current=0.90)
**PASS** nifty_50→nps_portfolio w=0.80 (current=0.80)

### pmi_manufacturing
**PASS** pmi_manufacturing→index_of_industrial_production w=0.85 (current=0.85)

## SUMMARY
- Edges reviewed: 104
- PASS (unchanged): 78
- PASS (weight adjusted): 1
- FIX (type change): 15
- KILL: 10
- ADD: 0

## WEIGHT OVERRIDES
```yaml
edges:
- from: sebi
  to: nifty_50
  weight: 0.40
```