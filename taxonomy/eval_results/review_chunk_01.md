### Node: aadhaar_authentication
**PASS** aadhaar_authentication→pan_aadhaar_linkage w=1.00 (current=1.0)
**PASS** aadhaar_authentication→digilocker_documents w=0.95 (current=0.95)
**KILL** aadhaar_authentication→epf_balance — Rule 21 violation. Intermediary: epf_withdrawal. Aadhaar authentication enables the withdrawal transaction, it does not directly act upon the balance itself.
**PASS** aadhaar_authentication→mgnrega_wages w=0.95 (current=0.95)
**PASS** aadhaar_authentication→epramaan_and_sso w=0.90 (current=0.9)
**PASS** aadhaar_authentication→e_mandate_autopay w=0.80 (current=0.8)
**FIX** aadhaar_authentication→deepfake_and_identity_theft — type should be DISRUPTS (was AFFECTS). w=0.60 (current=0.6). Reason: Robust biometric authentication systematically blocks or halts identity theft, making DISRUPTS the more accurate specific verb.

### Node: broadband_network_quality
**FIX** broadband_network_quality→ott_subscription — type should be AFFECTS (was DEPENDS_ON). w=0.60 (current=0.85). Reason: OTT subscriptions themselves do not structurally depend on broadband (users can subscribe and stream via mobile data). Broadband quality merely affects the user experience and retention. Weight lowered to reflect moderate dependency.
**FIX** broadband_network_quality→k12_edtech — type should be AFFECTS (was DEPENDS_ON). w=0.70 (current=0.8). Reason: K-12 edtech platforms are not structurally unable to function without home broadband, as mobile data is a primary substitute in India.

### Node: digilocker_documents
**FIX** digilocker_documents→traffic_fines — type should be DISRUPTS (was AFFECTS). w=0.80 (current=0.8). Reason: Presenting valid digital documents systematically blocks or prevents the issuance of a fine.

### Node: laptop_computer
**PASS** laptop_computer→higher_ed_online_degrees w=0.90 (current=0.9)
**FIX** laptop_computer→video_game — type should be AFFECTS (was DEPENDS_ON). w=0.60 (current=0.8). Reason: Video games as a broad category do not structurally depend on laptops (mobile and console gaming are massive). Laptops affect the PC gaming segment. Weight lowered to reflect the moderate share of PC gaming in India.

### Node: liquid_milk
**FIX** liquid_milk→paneer_and_cheese — type should be SUPPLIES (was PRODUCES). w=0.95 (current=0.95). Reason: Liquid milk is a raw material/ingredient that provides physical goods to the manufacturing process of paneer and cheese.
**FIX** liquid_milk→butter_and_ghee — type should be SUPPLIES (was PRODUCES). w=0.95 (current=0.95). Reason: Liquid milk is the physical raw material supplied to extract butter and ghee.
**PASS** liquid_milk→childhood_malnutrition w=0.75 (current=0.75)
**PASS** liquid_milk→mid_day_meal w=0.70 (current=0.7)

### Node: mobile_network_quality
**FIX** mobile_network_quality→cab_aggregator_fare — type should be AFFECTS (was DEPENDS_ON). w=0.70 (current=0.7). Reason: The fare itself does not structurally depend on the network; rather, network quality affects local driver supply, which in turn affects the fare via surge pricing.

### Node: pan_aadhaar_linkage
**PASS** pan_aadhaar_linkage→personal_income_tax w=1.00 (current=1.0)
**FIX** pan_aadhaar_linkage→tds_deduction — type should be DISRUPTS (was DEPENDS_ON). w=0.80 (current=0.8). Reason: DEPENDS_ON with a negative polarity is semantically invalid. Successful linkage systematically blocks or prevents the penal higher TDS deduction.

### Node: personal_data_privacy
**FIX** personal_data_privacy→deepfake_and_identity_theft — type should be DISRUPTS (was AFFECTS). w=0.80 (current=0.8). Reason: Strong privacy controls systematically block the availability of data used by identity thieves.

### Node: wheat_flour
**FIX** wheat_flour→biscuits_and_snacks — type should be SUPPLIES (was PRODUCES). w=0.90 (current=0.9). Reason: Wheat flour is a physical ingredient supplied to the snack manufacturing industry; it does not literally create the snacks on its own.
**FIX** wheat_flour→instant_noodles — type should be SUPPLIES (was PRODUCES). w=0.90 (current=0.9). Reason: Wheat flour is a physical ingredient supplied to make noodles.

## SUMMARY
- Edges reviewed: 82
- PASS (unchanged): 69
- PASS (weight adjusted): 0
- FIX (type change): 12
- KILL: 1
- ADD: 0

## WEIGHT OVERRIDES
```yaml
edges:
- from: broadband_network_quality
  to: ott_subscription
  weight: 0.60
- from: broadband_network_quality
  to: k12_edtech
  weight: 0.70
- from: laptop_computer
  to: video_game
  weight: 0.60
```