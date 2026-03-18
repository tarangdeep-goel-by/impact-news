# T→I Bridge Audit — Gemini 3.1 Pro

Here is the audit of the 305 T→I bridge edges based on the provided causal graph rules. 

### Executive Summary
**Quality Score: 7.5 / 10**
The graph demonstrates excellent causal reasoning and rich, descriptive justifications. However, it heavily violates **Rule 18 (Homogeneity Principle)** in the Energy, Infrastructure, and Health sectors by targeting broad L2 categories where the causal mechanism only applies to specific L3 children. Additionally, there are a few critical polarity inversions and an over-reliance on `AFFECTS` where `SUPPLIES` is semantically required.

---

### 1. L2 Target Audit (Rule 18 Violations)
Per Rule 18, T→I bridges targeting an I-world L2 are only valid if the trigger affects **ALL** L3 children equally. The following edges fail the Homogeneity Test and must be decomposed:

**Energy & Power Mismatches**
*   **FLAGGED:** `coal_power_plants(T4-L3) → household_energy(I2-L2)`
*   **FLAGGED:** `national_power_grid(T4-L3) → household_energy(I2-L2)`
*   **FLAGGED:** `nuclear_power_plants(T4-L3) → household_energy(I2-L2)`
*   **FLAGGED:** `renewable_energy_parks(T4-L3) → household_energy(I2-L2)`
    *   *Rationale:* These triggers supply electricity. They do not supply the other L3 child of `household_energy`, which is `cooking_fuel` (LPG/firewood). 
    *   *Fix:* Change target to `residential_electricity(I2-L3)`.
*   **FLAGGED:** `oil_gas_pipelines(T4-L3) → household_energy(I2-L2)`
    *   *Rationale:* Conversely, pipelines supply `cooking_fuel(I2-L3)` (PNG/LPG), but do not supply `residential_electricity(I2-L3)`.
    *   *Fix:* Change target to `cooking_fuel(I2-L3)`.

**Health & Sanitation Mismatches**
*   **FLAGGED:** `civic_urban_infrastructure(T4-L2) → infectious_diseases(I6-L2)`
*   **FLAGGED:** `meteorological_systems(T1-L2) → infectious_diseases(I6-L2)`
    *   *Rationale:* Sewage, drainage, and monsoons directly impact `vector_borne_diseases` (mosquitoes) and `water_and_food_borne_diseases` (cholera). They have zero direct causal effect on the third L3 child, `respiratory_infections` (COVID/flu), which is driven by winter smog and crowding.
    *   *Fix:* Decompose into two edges targeting `vector_borne_diseases(I6-L3)` and `water_and_food_borne_diseases(I6-L3)`.

**Regulatory & Economic Mismatches**
*   **FLAGGED:** `indian_regulatory_bodies(T2-L2) → education_economics(I7-L2)`
    *   *Rationale:* The description cites "UGC and AICTE fee cap directives". These bodies only regulate `college_university_fees(I7-L3)`. They have no jurisdiction over `school_fees` (State Boards) or `coaching_fees` (unregulated private sector).
    *   *Fix:* Change target to `college_university_fees(I7-L3)`.
*   **FLAGGED:** `indian_statutory_frameworks_and_councils(T2-L2) → household_energy(I2-L2)`
    *   *Rationale:* The GST Council and Petroleum Ministry set prices for `cooking_fuel(I2-L3)` (LPG). They do not set tariffs for `residential_electricity(I2-L3)`, which is handled by State Electricity Regulatory Commissions (SERCs).
    *   *Fix:* Change target to `cooking_fuel(I2-L3)`.
*   **FLAGGED:** `agricultural_commodities(T3-L3) → edible_oils(I1-L2)`
    *   *Rationale:* Global commodity prices (palm/soybean) dictate the cost of imported `palm_oil` and `sunflower_oil`. They have a vastly different (or non-existent) mechanism/weight on locally milled `mustard_oil` or `coconut_oil`.
    *   *Fix:* Decompose to target `palm_oil(I1-L3)` and `sunflower_oil(I1-L3)`.

---

### 2. Invalid Edges (Polarity, Factual, & Structural Errors)

*   **INVALID POLARITY:** `usd_inr_exchange(T3-L4) → vehicle_fuel(I3-L3) (AFFECTS, w=0.8, p=-1, d=SHORT_TERM)`
    *   *Error:* The description states "Rupee depreciation increases crude oil import costs, pushing up petrol... prices." If USD-INR goes *up* (depreciation), fuel prices go *up*. Polarity must be **`p=1`**.
*   **INVALID POLARITY:** `us_federal_reserve(T2-L4) → it_sector_salary(I4-L4) (AFFECTS, w=0.7, p=1, d=MEDIUM_TERM)`
    *   *Error:* The description states "US Fed rate *cuts* lower the cost of capital... driving *up* hiring budgets". If the trigger goes *down*, the impact goes *up*. This is an inverse relationship. Polarity must be **`p=-1`**.
*   **SEMANTIC CONTRADICTION:** `marine_fish_stocks(T1-L4) → marine_fish(I1-L3) (SUPPLIES, w=0.8, p=-1, d=MEDIUM_TERM)`
    *   *Error:* You cannot have `SUPPLIES` with `p=-1`. `SUPPLIES` inherently means A provides physical goods to B (positive correlation). If the target node represents retail *price* going down, the verb must be `AFFECTS`. If the target represents physical *availability* going up, it must be `SUPPLIES` with `p=1`.
*   **CROSS-WORLD VIOLATION:** `cyclonic_storm_systems(T1-L4) → marine_fish_stocks(T1-L4) (DISRUPTS, w=0.85, p=-1, d=IMMEDIATE)`
    *   *Error:* This is a **T→T edge** (Trigger to Trigger), not a T→I bridge. It belongs in the Trigger world graph, not the Bridge graph.

---

### 3. Edge Type Upgrades (Rule 12b)
`AFFECTS` is overused (Priority 10 fallback). Per Rule 12b, if a physical good, raw material, or vital input is provided, `SUPPLIES` (Priority 2) must be used.

**Upgrade `AFFECTS` to `SUPPLIES`:**
*   `agricultural_commodities(T3-L3) → edible_oils(I1-L2)` *(Once decomposed to L3s)*
*   `energy_commodities(T3-L3) → household_energy(I2-L2)` *(Once decomposed to cooking_fuel)*
*   `energy_commodities(T3-L3) → vehicle_fuel(I3-L3)`
*   `southwest_monsoon(T1-L4) → staple_grains(I1-L2)` *(Rainwater is a physical input for crops)*
*   `southwest_monsoon(T1-L4) → vegetables(I1-L3)`
*   `transport_logistics_infrastructure(T4-L2) → fresh_produce(I1-L2)` *(Logistics physically supplies/delivers the goods to market)*

**Upgrade `AFFECTS` to `PRODUCES`:**
*   `autumn_festive_season(T5-L4) → retail_sugar(I1-L3)` -> Change to `PRODUCES` (The season literally generates the demand spike).

### Summary of Action Items
1. Run a script to bulk-repoint the `household_energy` and `infectious_diseases` L2 targets to their correct L3 children.
2. Fix the two `p=-1` / `p=1` polarity inversions.
3. Delete the rogue T→T edge (`cyclonic_storm_systems → marine_fish_stocks`) from the bridge file.
4. Upgrade the 6 identified `AFFECTS` edges to `SUPPLIES`.