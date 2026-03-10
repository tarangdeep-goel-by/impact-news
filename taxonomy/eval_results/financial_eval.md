```yaml
missing_edges:
  - from: upi
    to: income_tax
    type: AFFECTS
    description: "The formalization of the economy via UPI leaves a digital trail, bringing more MSMEs and individuals into the formal income tax net."
    severity: P1
  - from: cpi_inflation
    to: fd_rates
    type: AFFECTS
    description: "High inflation erodes real returns on fixed deposits, eventually forcing banks to adjust rates to maintain positive real yields for depositors."
    severity: P1
  - from: nifty_50
    to: stt
    type: PRODUCES
    description: "Higher equity market valuations and trading volumes directly drive Securities Transaction Tax (STT) collections for the government."
    severity: P2
  - from: crude_oil
    to: excise_duty
    type: AFFECTS
    description: "The government frequently adjusts excise duty on crude oil/fuel to absorb global price shocks and manage retail inflation."
    severity: P1

incorrect_edges:
  - from: epf_interest_rate
    to: gsec_yield
    issue: "Direction should be reversed. G-sec yields dictate the earnings of the EPF corpus, which allows EPFO to declare the interest rate. The EPF rate does not benchmark or drive G-sec yields."
  - from: nifty_50
    to: sensex
    issue: "Direction and relationship type are wrong. Nifty and Sensex are parallel indices driven by the same underlying large-cap stocks. One does not cause or affect the other; they are highly correlated."
  - from: us_fed_rate
    to: dollar_index
    issue: "Dangling edge. The node 'us_fed_rate' does not exist in the graph. It should be re-mapped to the existing 'fed_funds_rate' node."
  - from: gst
    to: gst_municipal
    issue: "Dangling edge. The target node 'gst_municipal' does not exist in the nodes list."

missing_nodes:
  - id: psu_banks
    aliases: ["public sector banks", "government banks", "SBI"]
    category: "financial"
    why: "Referenced in multiple existing edges (e.g., basel_iii, rbi_circular) but missing from the nodes array. They dominate the Indian banking sector."
  - id: food_inflation
    aliases: ["food prices", "vegetable prices", "grocery inflation"]
    category: "financial"
    why: "Accounts for ~46% of India's CPI basket. Heavily referenced in existing edges but completely missing from the nodes list."
  - id: monsoon_forecast
    aliases: ["monsoon", "IMD forecast", "southwest monsoon"]
    category: "financial"
    why: "Crucial driver of rural demand, agriculture, and food inflation in India. Referenced in edges but missing in nodes."
  - id: fno_trading
    aliases: ["derivatives trading", "options trading", "futures and options"]
    category: "financial"
    why: "Retail F&O trading is a massive, systemic trend in Indian markets currently under heavy SEBI regulatory scrutiny."
  - id: petrol_diesel_price
    aliases: ["fuel prices", "petrol price", "diesel price"]
    category: "financial"
    why: "Directly impacts household budgets and transport inflation; it is the critical missing link between crude_oil and Indian cpi_inflation."

duplicate_nodes:
  - keep: nifty_50
    merge: nifty
  - keep: home_loan
    merge: home_loans
  - keep: education_loan
    merge: education_loans
  - keep: personal_loan
    merge: personal_loans
  - keep: auto_loan
    merge: vehicle_loans
  - keep: npa
    merge: npa_bad_loans
  - keep: npa
    merge: npa_crisis
  - keep: health_insurance
    merge: health_insurance_financial
  - keep: property_tax
    merge: property_tax_financial
  - keep: gst
    merge: gst_vat
  - keep: cpi_inflation
    merge: inflation_rate
  - keep: repo_rate
    merge: policy_interest_rate

description_issues:
  - from: financial_system
    to: monetary_policy
    issue: "Missing description. There are approximately 38 hierarchical 'CONTAINS' edges at the end of the JSON that lack descriptions entirely."
  - from: health_insurance
    to: health_insurance_premium
    issue: "Tautological description ('Health insurance cost determined by premium'). It should explain the causal mechanism, e.g., 'Rising hospital claims and medical inflation force insurers to hike premiums'."
  - from: union_budget
    to: customs_duty
    issue: "Vague description ('Budget announces customs duty changes'). Should specify: 'The Union Budget adjusts import tariffs to protect domestic manufacturing (Make in India) or control inflation'."

scores:
  completeness: 7
  accuracy: 8
  granularity: 6
  india_specificity: 9
  overall: 7.5
```