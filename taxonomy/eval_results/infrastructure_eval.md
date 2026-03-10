```yaml
missing_edges:
  - from: tolls
    to: trucking_costs
    type: AFFECTS
    description: "Toll revisions (including NHAI FASTag rate hikes) directly increase road freight operational costs, which are passed down to goods pricing."
    severity: P0
  - from: power_outage
    to: broadband_internet
    type: DISRUPTS
    description: "Local power cuts frequently drain ISP node backup batteries, causing neighborhood-wide internet outages that disrupt remote work."
    severity: P1
  - from: coal_shortage
    to: power_outage
    type: PRODUCES
    description: "Domestic coal shortages at thermal power plants trigger pre-emptive load shedding and massive power outages across states."
    severity: P0
  - from: monsoon
    to: pothole
    type: PRODUCES
    description: "Heavy monsoon rains wash away poor-quality bitumen, creating widespread potholes that severely damage vehicles and slow traffic."
    severity: P1
  - from: aviation_turbine_fuel
    to: domestic_flights
    type: AFFECTS
    description: "ATF prices make up around 40% of airline operating costs in India; price hikes directly cause spikes in domestic airfares."
    severity: P0

incorrect_edges:
  - from: broadband_internet
    to: bsnl_fiber
    issue: "Direction is reversed. BSNL Fiber SUPPLIES broadband internet, it is not produced by it."
  - from: broadband_internet
    to: private_isp
    issue: "Direction is reversed. Private ISPs SUPPLY broadband internet."
  - from: water_treatment
    to: wtp
    issue: "Direction is reversed. Water Treatment Plants (WTP) PRODUCE water treatment."
  - from: water_scarcity
    to: inter_state_water_disputes
    issue: "Relationship type is wrong. Water scarcity PRODUCES/CAUSES disputes; it does not CONTAIN them."
  - from: water_treatment
    to: stp
    issue: "Direction is reversed. Sewage Treatment Plants (STP) PRODUCE water treatment/purification."

missing_nodes:
  - id: lpg_cylinder
    aliases: ["cooking gas", "LPG price", "commercial cylinder", "domestic cylinder"]
    category: "utilities"
    why: "LPG is the primary cooking fuel for most Indian households; its price fluctuations heavily impact monthly household budgets and restaurant costs."
  - id: solid_waste_management
    aliases: ["garbage collection", "waste disposal", "landfill", "BBMP garbage"]
    category: "infrastructure"
    why: "A critical municipal utility directly affecting daily life, public health, and urban aesthetics in Indian cities."
  - id: stormwater_drains
    aliases: ["SWD", "drainage system", "raja kaluve"]
    category: "water_infrastructure"
    why: "Encroached or clogged stormwater drains are the primary structural cause of urban flooding in cities like Bangalore, Mumbai, and Chennai."
  - id: aviation_turbine_fuel
    aliases: ["ATF", "jet fuel"]
    category: "utilities"
    why: "Essential node to connect global crude oil prices to domestic air travel costs."

duplicate_nodes:
  - keep: interstate_water_disputes
    merge: inter_state_water_disputes
  - keep: bus_fare
    merge: bus_fares
  - keep: dam_reservoir
    merge: reservoirs_and_dams
  - keep: metro_systems
    merge: metro_rail
  - keep: auto_rickshaw
    merge: auto_taxi

description_issues:
  - from: global
    to: global
    issue: "Severe lack of coverage. Approximately 250 out of 291 edges (85%) have no description. Causal graphs need descriptions to explain the 'why' behind the edge."
  - from: water_privatization
    to: city_water_supply
    issue: "Missing description. Needs context that in India, this usually means O&M (Operations & Maintenance) contracts rather than full utility privatization."
  - from: transport_and_mobility
    to: private_vehicles
    issue: "Uses a taxonomic 'CONTAINS' edge with no description. Should explain how policy or infrastructure shifts usage between private and public transport."

scores:
  completeness: 7
  accuracy: 7
  granularity: 8
  india_specificity: 9
  overall: 7.5
```