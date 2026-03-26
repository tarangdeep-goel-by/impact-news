### Node: `rural_unemployment_rate`
- **KILL** rural_unemployment_rate→urban_unemployment_rate — Rule 21 violation. Intermediary: `rural_urban_migration`. Lack of rural jobs drives migration, which then swells the urban labor pool.

### Node: `startup_layoffs`
- **PASS** startup_layoffs→urban_unemployment_rate w=0.70 (current=0.7)
- **PASS** startup_layoffs→depression w=0.65 (current=0.65)
- **KILL** startup_layoffs→gig_worker_payouts — Rule 21 violation. Intermediary: `gig_economy_workers` or `gig_labor_supply`. Layoffs increase the labor pool, which then drives down payouts.
- **KILL** startup_layoffs→investment_and_job_scams — Rule 21 violation. Intermediary: `job_seekers`. Layoffs create desperate job seekers, who are then targeted by scammers.
- **KILL** startup_layoffs→creator_and_digital_earnings — Rule 21 violation. Intermediary: `content_creators`. Layoffs supply the creator pool, which then generates earnings.

### Node: `street_vendor_income`
- **FIX** street_vendor_income→kirana_store_income — type should be COMPETES_WITH (was COMPETES_WITH). w=0.50 (current=0.5). Reason: Polarity must be -1 for COMPETES_WITH (if street vendor income increases, kirana store income decreases).

### Node: `transport_worker_unions`
- **KILL** transport_worker_unions→auto_driver_earnings — Rule 21 violation. Intermediary: `auto_rickshaw_fares`. Unions lobby for higher fares, which then boost earnings.

### Node: `upsc_civil_services`
- **KILL** upsc_civil_services→offline_coaching_centers — Rule 21 violation. Intermediary: `upsc_aspirants`. The civil service roles do not fund coaching centers; the aspirants competing for them do.

### Node: `urban_company_partner_earnings`
- **KILL** urban_company_partner_earnings→repair_service_charges — Rule 21 violation. Wrong source node. The platform's pricing models (`gig_platform_pricing`) set the baseline, not the partner's earnings.
- **KILL** urban_company_partner_earnings→pest_control_services — Rule 21 violation. Wrong source node. Standardized payouts/pricing set by the platform drive the market rates, not the earnings themselves.

### Node: `urban_unemployment_rate`
- **FIX** urban_unemployment_rate→burglary_and_theft — type should be AFFECTS (was PRODUCES). w=0.60 (current=0.6). Reason: Unemployment does not literally "create" or "generate" burglary; it AFFECTS the frequency of property crime by increasing desperation.

### Node: `retail_gold_investment`
- **KILL** retail_gold_investment→gold_loan_interest — Rule 21 violation. Intermediary: `gold_loans`. Possession of gold enables taking out a gold loan, which then generates interest obligations.
- **PASS** retail_gold_investment→direct_equity_portfolio w=0.50 (current=0.5)

### Node: `asthma`
- **FIX** asthma→chronic_disease_medication — type should be AFFECTS (was PRODUCES). w=0.85 (current=0.85). Reason: Asthma does not literally create or generate medication; it AFFECTS the demand and usage of it.
- **PASS** asthma→doctor_consultation w=0.85 (current=0.85)

### Node: `ayurvedic_medicines`
- **FIX** ayurvedic_medicines→generic_medicines — type should be COMPETES_WITH (was COMPETES_WITH). w=0.50 (current=0.5). Reason: Polarity must be -1 for COMPETES_WITH (as ayurvedic medicine usage increases, generic medicine usage decreases).

### Node: `childhood_malnutrition`
- **PASS** childhood_malnutrition→school_examinations w=0.60 (current=0.85). [Weight adjusted: 0.85 is near-deterministic, but malnutrition's effect on specific exam performance is moderate/conditional (0.60).]
- **KILL** childhood_malnutrition→anganwadi_system — Rule 21 violation. Intermediary: `state_government_policy` or `anganwadi_enrollment`. High malnutrition rates drive state policy/investment, which then expands the anganwadi system.
- **PASS** childhood_malnutrition→tuberculosis w=0.75 (current=0.75)

### Node: `cholera_and_diarrhea`
- **FIX** cholera_and_diarrhea→hospital_beds — type should be AFFECTS (was PRODUCES). w=0.70 (current=0.7). Reason: The disease does not literally create hospital beds; it AFFECTS bed occupancy rates.

## SUMMARY
- Edges reviewed: 48
- PASS (unchanged): 32
- PASS (weight adjusted): 1
- FIX (type/polarity change): 5
- KILL: 10
- ADD: 0

## WEIGHT OVERRIDES
```yaml
edges:
- from: childhood_malnutrition
  to: school_examinations
  weight: 0.60
```