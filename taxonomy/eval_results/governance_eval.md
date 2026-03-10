```yaml
missing_edges:
  - from: aqi_levels
    to: construction_projects
    type: DISRUPTS
    description: "Under the Graded Response Action Plan (GRAP) in cities like Delhi, severe AQI levels legally trigger immediate bans on construction and demolition activities."
    severity: P0
  - from: zoning_master_plan
    to: property_prices_locality
    type: AFFECTS
    description: "Changes in city master plans, such as increasing the Floor Area Ratio (FAR) or changing land use from agricultural to commercial, drastically swing local real estate values."
    severity: P0
  - from: welfare_schemes
    to: government_budget
    type: AFFECTS
    description: "Direct Benefit Transfers (DBT) and freebie schemes (like free bus rides or electricity) heavily deplete state exchequers, often increasing the fiscal deficit."
    severity: P0
  - from: elections
    to: dry_days
    type: PRODUCES
    description: "The Election Commission of India mandates 48 hours of 'dry days' (ban on alcohol sales) prior to polling and on counting days to prevent voter bribery."
    severity: P1
  - from: road_maintenance
    to: traffic_congestion
    type: PRODUCES
    description: "White-topping, asphalting, and pothole repair works frequently require lane closures, causing massive peak-hour traffic jams in major Indian metros."
    severity: P1

incorrect_edges:
  - from: municipal_expenditure
    to: tender_process
    issue: "Direction should be reversed or changed to DEPENDS_ON. The tender process precedes and regulates the expenditure; municipal bodies don't spend money to produce a tender."
  - from: traffic_enforcement
    to: traffic_fine_amount
    issue: "Incorrect causal direction. The Motor Vehicles Act (policy) sets the fine amount; traffic police merely enforce it. Should be reversed or linked from 'traffic_rules'."
  - from: state_tourism
    to: heritage_sites
    issue: "Factually misleading. Major heritage sites in India are managed by the central Archaeological Survey of India (ASI), not state tourism boards, though states promote them."
  - from: solid_waste_management
    to: plastic_ban
    issue: "Type should be REGULATED_BY rather than REGULATES. A plastic ban is a municipal policy designed to ease solid waste management, not a byproduct produced by it."

missing_nodes:
  - id: rto_services
    aliases: ["RTO", "driving license", "vehicle registration", "regional transport office"]
    category: "local_governance"
    why: "A massive daily-life governance touchpoint for citizens dealing with vehicle ownership, taxes, and licenses."
  - id: model_code_of_conduct
    aliases: ["MCC", "election code", "poll code"]
    category: "governance_and_regulation"
    why: "Crucial Indian political mechanism that halts all new government tenders, projects, and welfare announcements for months before elections."
  - id: aadhaar_kyc
    aliases: ["Aadhaar", "UIDAI", "identity verification", "PAN linking"]
    category: "governance_and_regulation"
    why: "The foundational identity layer required for citizens to access almost all government welfare schemes, subsidies, and financial services."

duplicate_nodes:
  - keep: public_parks
    merge: public_parks_spaces
  - keep: footpath
    merge: footpath_pedestrian
  - keep: road_maintenance
    merge: road_repair
  - keep: road_maintenance
    merge: street_maintenance
  - keep: solid_waste_management
    merge: waste_management

description_issues:
  - from: "ALL"
    to: "ALL"
    issue: "Extreme sparsity: 320 out of 323 edges (99%) have no descriptions. Causal chains in Indian governance are highly specific and require explanation."
  - from: ward_delimitation
    to: municipal_elections
    issue: "Missing description. Needs to explain how redrawing ward boundaries alters caste/gender reservation rosters and voter demographics, directly impacting election outcomes."
  - from: court_infrastructure_orders
    to: municipal_corporation
    issue: "Missing description. Should mention that High Courts and NGT frequently pull up civic bodies for inaction on potholes, lake pollution, and illegal encroachments."

scores:
  completeness: 7
  accuracy: 8
  granularity: 7
  india_specificity: 9
  overall: 7.7
```