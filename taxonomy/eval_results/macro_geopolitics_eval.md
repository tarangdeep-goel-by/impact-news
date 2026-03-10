```yaml
missing_edges:
  - from: us_fed_rate
    to: rbi_monetary_policy
    type: AFFECTS
    description: "The RBI Monetary Policy Committee closely tracks the US Fed rate to maintain yield differentials and prevent INR depreciation/capital flight."
    severity: P0

  - from: rbi_monetary_policy
    to: real_estate_prices
    type: AFFECTS
    description: "RBI repo rate changes directly dictate home loan interest rates (EMIs), which is the primary driver of real estate housing demand in India."
    severity: P0

  - from: fii_portfolio_flows
    to: inr_usd
    type: AFFECTS
    description: "Foreign Institutional Investor (FII) buying or selling of Indian equities and bonds directly impacts the Rupee-Dollar exchange rate."
    severity: P1

  - from: crude_oil
    to: fuel_price_local
    type: AFFECTS
    description: "Global crude oil prices dictate the baseline cost for local petrol and diesel, even though state and central taxes buffer the final retail price."
    severity: P0

  - from: minimum_wage
    to: inflation_india
    type: AFFECTS
    description: "Increases in minimum wages drive up labor costs across sectors, contributing to core inflation metrics."
    severity: P2

incorrect_edges:
  - from: rera
    to: private_hospital
    issue: "RERA (Real Estate Regulatory Authority) regulates the real estate sector, not private hospitals. This edge is factually incorrect."

  - from: thermal_power_plant
    to: coal_prices
    issue: "Relationship type is 'CONSUMES'. A power plant consumes coal, not 'coal_prices'. The edge should be reversed to AFFECTS (coal_prices -> thermal_power_plant) or point to a 'coal' node."

  - from: us_china_trade
    to: india_us_trade
    issue: "Description 'US-China trade war creates opportunities and risks for India' is too vague. It should specify how supply chain shifts (China+1) affect bilateral trade volumes."

missing_nodes:
  - id: monsoon_performance
    aliases: ["monsoon", "rainfall", "El Nino", "La Nina"]
    category: "macro"
    why: "The monsoon is the most critical macroeconomic event in India, directly driving rural demand, agriculture output, and food inflation."

  - id: inr_usd_exchange_rate
    aliases: ["rupee value", "USD INR", "currency depreciation", "rupee fall"]
    category: "macro"
    why: "Crucial macro indicator that affects India's import bill (especially crude oil and electronics) and export competitiveness."

  - id: rural_demand
    aliases: ["rural consumption", "FMCG rural sales", "rural economy"]
    category: "macro"
    why: "A major driver of the Indian economy, highly dependent on MSP, monsoons, and government subsidies (like MGNREGA)."

duplicate_nodes:
  - keep: us_china_trade_war
    merge: us_china_trade

  - keep: ukraine_war
    merge: russia_ukraine

  - keep: middle_east_tensions
    merge: middle_east_conflict

  - keep: fdi_investment_flows
    merge: foreign_direct_investment

description_issues:
  - from: rera
    to: real_estate_prices
    issue: "Missing description. Should explain how compliance costs and restricted supply initially drive up prices, but increase buyer trust."

  - from: affordable_housing
    to: real_estate_prices
    issue: "Missing description. Should explain how government subsidies cap prices in specific housing tiers."

  - from: multiple_nodes
    to: multiple_nodes
    issue: "Approximately 45+ edges (especially 'CONTAINS' edges and cross-domain links like 'water_quality' -> 'urban_health_impact') completely lack descriptions."

scores:
  completeness: 7
  accuracy: 8
  granularity: 7
  india_specificity: 8
  overall: 7.5
```