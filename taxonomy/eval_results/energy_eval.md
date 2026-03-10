```yaml
missing_edges:
  - from: diesel
    to: freight_rates
    type: AFFECTS
    description: "Diesel constitutes ~60% of trucking costs. Diesel price hikes directly increase freight rates, which is the primary transmission mechanism for wholesale inflation in India."
    severity: P0
  - from: freight_rates
    to: fmcg_prices
    type: AFFECTS
    description: "Higher freight rates increase the landed cost of FMCG goods, leading to shrinkflation or direct MRP hikes for consumers."
    severity: P0
  - from: cng
    to: auto_rickshaw_fares
    type: AFFECTS
    description: "CNG price hikes lead to strikes by auto/taxi unions, forcing state transport authorities to revise base fares, directly hitting the common man's daily commute budget."
    severity: P0
  - from: cooking_gas_commercial
    to: restaurant_menu_prices
    type: AFFECTS
    description: "19kg commercial LPG price fluctuations (which happen monthly) directly impact restaurant operating margins, leading to menu price revisions or reduced portion sizes."
    severity: P0
  - from: election_cycle
    to: fuel_price_deregulation
    type: DISRUPTS
    description: "In India, OMCs unofficially freeze daily petrol/diesel price revisions months ahead of major state or general elections, absorbing losses, and hike them immediately after voting ends."
    severity: P0
  - from: discom_debt
    to: power_deficit
    type: PRODUCES
    description: "Financially stressed DISCOMs cannot afford to buy power on exchanges during peak demand, leading to load shedding (power cuts) even when national generation capacity is sufficient."
    severity: P0
  - from: windfall_tax
    to: oil_refining
    type: AFFECTS
    description: "Special Additional Excise Duty (SAED) on export of refined products (petrol/diesel/ATF) directly hits the gross refining margins of private refiners like Reliance and Nayara."
    severity: P1
  - from: coal
    to: cement_manufacturing
    type: SUPPLIES
    description: "The cement industry is highly energy-intensive and relies heavily on petcoke and coal. Coal shortages or price spikes directly increase cement prices, affecting real estate."
    severity: P1

incorrect_edges:
  - from: energy_and_fuel
    to: crude_oil
    issue: "Uses CONTAINS. This is a causal graph, not a taxonomy. Taxonomy edges break causal pathfinding algorithms."
  - from: crude_oil
    to: brent_crude
    issue: "Uses CONTAINS. Brent is a benchmark/type, not a causal downstream effect."
  - from: bescom
    to: bbmp
    issue: "Uses LOCATED_IN. This is a geospatial/knowledge graph edge, not a causal edge. Does BESCOM cause BBMP?"
  - from: msedcl
    to: bmc_mumbai
    issue: "Uses LOCATED_IN. Breaks causal chain logic."
  - from: electricity_tariff
    to: tariff_structure
    issue: "Wrong causal direction. The tariff structure (slabs, fixed charges) PRODUCES the final electricity tariff, not the other way around."
  - from: global_commodity_cycle
    to: lithium
    issue: "Too vague and indirect. The commodity cycle is an abstract macroeconomic concept; it doesn't directly 'affect' lithium without intermediate demand/supply nodes."

node_definition_issues:
  - id: energy_and_fuel
    issue: "Purely taxonomic parent node. Serves no causal purpose and will clutter pathfinding."
    fix: "Delete node and all its CONTAINS edges."
  - id: industrial_metals_and_materials
    issue: "Purely taxonomic parent node."
    fix: "Delete node."
  - id: fuel_cost_gig
    issue: "Too specific and weirdly named. It represents a concept but isn't a recognizable entity in news."
    fix: "Rename to 'gig_worker_operating_costs' and add aliases ['delivery partner fuel cost', 'Uber driver fuel expense']."
  - id: administered_gas_price
    issue: "Missing key aliases used in Indian financial journalism."
    fix: "Add aliases ['APM', 'domestic gas pricing guidelines', 'Kirit Parikh formula']."
  - id: bescom
    issue: "Too granular if other major state DISCOMs aren't included, or too specific if meant to represent all urban DISCOMs."
    fix: "Keep, but ensure major debt-heavy DISCOMs (UPPCL, TANGEDCO) are also added, or abstract to 'state_discom'."

missing_nodes:
  - id: discom_debt
    aliases: ["DISCOM losses", "state power utility debt", "AT&C losses", "power sector dues"]
    category: "energy_policy"
    why: "The single biggest bottleneck in the Indian power sector. Drives bailouts (UDAY, RDSS) and causes power cuts because DISCOMs can't pay generators."
  - id: freight_rates
    aliases: ["trucking rates", "transportation costs", "lorry freight"]
    category: "infrastructure"
    why: "The missing middle link between diesel prices and consumer goods inflation. News constantly reports on truck operator unions raising freight rates."
  - id: windfall_tax
    aliases: ["SAED", "Special Additional Excise Duty", "windfall tax on crude"]
    category: "energy_policy"
    why: "A major fortnightly policy trigger in India affecting OMC stocks (Reliance, ONGC, Oil India) and government tax revenues."
  - id: election_cycle
    aliases: ["state elections", "Lok Sabha elections", "model code of conduct"]
    category: "governance"
    why: "In India, elections are a massive causal factor for energy pricing. Fuel prices are frozen, and free electricity schemes are announced, severely impacting OMC and DISCOM financials."
  - id: auto_rickshaw_fares
    aliases: ["auto fares", "taxi fares", "cab pricing"]
    category: "consumer_life"
    why: "Direct citizen impact of CNG price hikes. When CNG goes up, unions strike, and fares are officially hiked by state RTOs."

duplicate_nodes:
  - keep: crude_oil
    merge: crude_oil_price
  - keep: opec
    merge: opec_decision
  - keep: opec
    merge: opec_policy
  - keep: coal_shortage
    merge: coal_stock_crisis
  - keep: lng
    merge: lng_trade

description_issues:
  - from: renewable_energy
    to: solar_energy
    issue: "Empty description. (Also a CONTAINS edge that should be deleted)."
  - from: electricity_tariff
    to: tariff_structure
    issue: "Empty description."
  - from: bescom
    to: electricity_bill
    issue: "Empty description."
  - from: city_gas_distribution
    to: cng_stations
    issue: "Empty description."
  - from: natural_gas
    to: png
    issue: "Too vague ('Gas price hikes raise PNG prices'). Needs to explain the APM allocation mechanism and how CGDs pass on costs."
  - from: smart_meter
    to: cross_subsidy
    issue: "Empty description. How exactly do smart meters affect cross-subsidies? Mechanism is missing."

cross_domain_gaps:
  - from_domain: energy
    to_domain: telecom
    missing_link: "diesel -> telecom_tariffs. Telecom towers in India rely heavily on diesel generators during power cuts. High diesel prices increase telco operating costs, putting upward pressure on mobile recharge tariffs."
  - from_domain: energy
    to_domain: real_estate
    missing_link: "coal -> cement_prices -> housing_costs. Coal is the primary energy source for cement kilns. Coal price spikes drive up construction material costs, impacting real estate prices."
  - from_domain: energy
    to_domain: politics
    missing_link: "petrol/lpg -> anti_incumbency. High retail fuel and cooking gas prices are major drivers of voter dissatisfaction and frequently feature in election manifestos."
  - from_domain: energy
    to_domain: financial_markets
    missing_link: "windfall_tax -> nifty_energy_index. Changes in windfall taxes immediately impact the stock prices of heavyweight companies like Reliance and ONGC, moving the broader market indices."

scores:
  completeness: 5.0
  accuracy: 4.0
  granularity: 6.0
  india_specificity: 7.0
  description_quality: 3.0
  overall: 4.8
```