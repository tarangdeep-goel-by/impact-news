```yaml
missing_edges:
  - from: residential_rent
    to: consumer
    type: AFFECTS
    description: "Rent is one of the largest monthly expenses for urban Indian households; changes directly impact disposable income."
    severity: P0
  - from: mortgage_rates
    to: consumer
    type: AFFECTS
    description: "Higher mortgage rates increase EMI burdens for middle-class homeowners, reducing their spending capacity."
    severity: P0
  - from: hospital_services
    to: consumer
    type: AFFECTS
    description: "India has high out-of-pocket healthcare costs; hospital expenses directly drain household savings."
    severity: P0
  - from: city_water_supply
    to: consumer
    type: SUPPLIES
    description: "Municipal water supply is critical for daily household needs; shortages force reliance on expensive private tankers."
    severity: P0
  - from: crude_oil
    to: petrol
    type: AFFECTS
    description: "Global crude oil prices dictate retail petrol and diesel prices in India."
    severity: P0
  - from: repo_rate
    to: mortgage_rates
    type: AFFECTS
    description: "The RBI's repo rate directly determines floating home loan interest rates."
    severity: P0
  - from: two_wheelers
    to: consumer
    type: SUPPLIES
    description: "Two-wheelers are the primary mode of personal transport for the Indian middle class."
    severity: P1

incorrect_edges:
  - from: drinking_water
    to: groundwater
    issue: "Direction reversed and wrong type. Groundwater SUPPLIES drinking water, drinking water does not CONTAIN groundwater."
  - from: home_ownership
    to: mortgage_rates
    issue: "Direction reversed and wrong type. Mortgage rates AFFECT home ownership affordability. Home ownership does not CONTAIN mortgage rates."
  - from: climate_change
    to: global_temperature
    issue: "Direction reversed. Global temperature rise PRODUCES/AFFECTS climate change, or they are synonymous. Climate change doesn't CONTAIN it."
  - from: artificial_intelligence
    to: generative_ai
    issue: "Ontological/Taxonomic edge (CONTAINS) used in a causal graph. Generative AI is a subset, but it doesn't causally affect AI in this direction."

missing_nodes:
  - id: water_tanker_services
    aliases: ["water tankers", "private water supply", "tanker mafia"]
    category: "housing_and_shelter"
    why: "Crucial fallback for urban Indian consumers (especially in Bangalore, Chennai, NCR) when municipal water fails."
  - id: two_wheelers
    aliases: ["scooters", "motorcycles", "bikes"]
    category: "housing_and_shelter"
    why: "The dominant form of personal mobility in India; highly sensitive to petrol prices and financing rates."
  - id: gold_prices
    aliases: ["gold rate", "jewellery prices"]
    category: "recreation_and_culture"
    why: "Gold is a massive cultural expense (weddings) and primary savings vehicle for Indian households."
  - id: railway_fares
    aliases: ["train tickets", "IRCTC", "passenger trains"]
    category: "recreation_and_culture"
    why: "Indian Railways is the lifeline of long-distance travel for the masses; pricing affects millions."

duplicate_nodes:
  - keep: flood
    merge: floods
  - keep: drought
    merge: droughts
  - keep: heatwave
    merge: heatwaves
  - keep: cyclone
    merge: cyclones_hurricanes
  - keep: air_quality
    merge: air_pollution

description_issues:
  - from: monsoon
    to: malaria
    issue: "Missing description. Should explain that stagnant post-monsoon water creates breeding grounds for Anopheles mosquitoes."
  - from: monsoon
    to: city_water_supply
    issue: "Missing description. Should explain that monsoon rainfall fills municipal reservoirs, dictating urban water security for the year."
  - from: monsoon
    to: stormwater_drain
    issue: "Missing description. Should note that heavy monsoons overwhelm urban stormwater drains, leading to localized flooding."
  - from: urban_flooding
    to: disease_surveillance
    issue: "Missing description. Should explain that flooding mixes sewage with drinking water, requiring surveillance for waterborne diseases like cholera and typhoid."

scores:
  completeness: 7
  accuracy: 7
  granularity: 8
  india_specificity: 9
  overall: 7.5
```