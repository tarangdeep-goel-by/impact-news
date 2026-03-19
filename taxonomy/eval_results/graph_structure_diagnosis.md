# Graph Structure Diagnosis — Gemini 3.1 Pro

Date: 2026-03-19

This is a classic problem in causal knowledge graphs applied to news: **the graph is currently modeling academic macroeconomics, but the user experiences immediate microeconomic reality.** 

When Brent Crude spikes, the economic reality takes 5 hops (Trade Deficit → CAD → FX → Fuel), but the *news impact* reality takes 1 hop (Crude → Fuel). Furthermore, your PPR algorithm is treating structural taxonomy edges (`CONTAINS`) the same as causal edges (`AFFECTS`), which is destroying your signal.

Here is my expert assessment and actionable plan to fix your graph and push your NDCG > 0.5.

---

### 1. Scope of the Problem
This is a **deeper structural issue**, but it can be resolved with a **~50-100 edge fix** combined with a **PPR transition matrix adjustment**. 

You do not need to throw away the graph. The issue stems from three specific anti-patterns:
1. **The "Textbook" Anti-pattern:** Forcing real-world impacts to walk through slow, academic macro-indicators (Event 1, Event 5).
2. **The "Taxonomy Trap":** Allowing hierarchical `CONTAINS` edges to steal random-walk probability from causal `AFFECTS` edges (Event 2).
3. **Missing "Last-Mile" Lateral Edges:** Failing to connect I-world nodes to other I-world nodes (e.g., Fuel → Logistics → Onions).

### 2. Approach
You need a hybrid approach. I recommend executing these in order:

*   **First: Graph Restructure (PPR Math Fix).** You must alter how the random walk traverses edge types. Right now, `CONTAINS` and `IS_A` are acting as probability sinks. 
*   **Second: Trigger Granularity.** Split overly broad nodes like `meteorological_systems`.
*   **Third: Targeted Edge Addition.** Add "Fast-Track" T→I bridges for known, high-velocity economic realities.

### 3. Edge Addition Strategy
You need a mix of **Direct T→I bridges** and **Lateral I→I edges**. 

*   **Direct T→I Bridges ("Fast-Tracks"):** If a macro trigger hits a citizen's wallet or life in < 30 days, it gets a direct edge, bypassing the macro-economic intermediate nodes. *(e.g., `brent_crude` → `vehicle_fuel`)*.
*   **Lateral I→I Edges (Cascades):** Citizens experience cascading impacts. Fuel prices drive logistics, which drive vegetable prices. These must be connected in the I-world. *(e.g., `vehicle_fuel` → `delivery_and_logistics`)*.
*   **Do NOT add intermediate L3s** unless absolutely necessary. Every hop halves your PPR probability. Keep paths short.

### 4. Solving PPR Dilution (The RBI Problem)
The RBI node has massive fan-out. In a standard PPR, if a node has 20 outgoing edges, each gets 5% of the probability. Because `rbi` connects to `savings_and_deposits` (which `CONTAINS` 5 leaf nodes), the math overwhelmingly favors those leaves.

**The Fix: Edge-Type Biased Random Walk**
You must adjust the transition matrix of your PPR so the random walker prefers causal edges over structural ones. 
*   Assign a **Transition Weight Multiplier** to edge types.
*   `AFFECTS`, `DISRUPTS`, `PRODUCES` = **1.0** (High priority for the walker)
*   `REGULATES`, `MANAGES` = **0.5**
*   `CONTAINS`, `IS_A` = **0.1** (Low priority; prevents taxonomy from stealing signal)

If you implement this, the walker will naturally flow down the `rbi` → `home_loan_emi` (`AFFECTS`) path rather than bleeding out into the `CONTAINS` hierarchy of fixed deposits.

---

### 5. Priority Order: The "NDCG > 0.5" Minimum Fix List

To fix these 5 specific events and dramatically improve your NDCG, implement the following exact graph changes.

#### Event 1: Crude Oil Surge (Fixing the 5-hop problem)
*Add Fast-Track T→I bridges and I→I cascades.*
*   `brent_crude` → `vehicle_fuel` [Type: AFFECTS, Weight: 0.9, Polarity: +1, Delay: short]
*   `vehicle_fuel` → `delivery_and_logistics` [Type: AFFECTS, Weight: 0.8, Polarity: +1, Delay: short]
*   `vehicle_fuel` → `auto_rickshaw_fare` [Type: AFFECTS, Weight: 0.8, Polarity: +1, Delay: short]
*   `delivery_and_logistics` → `retail_onion` [Type: AFFECTS, Weight: 0.6, Polarity: +1, Delay: short] *(Note: You should actually point logistics to `fresh_produce` L3, and let CONTAINS push it to onion/tomato).*

#### Event 2: RBI Rate Hike (Fixing the Dilution)
*Do not add edges. Fix the PPR transition matrix as described in Section 4.* 
If you cannot change the PPR algorithm immediately, you must add direct, high-weight Fast-Tracks to force the math:
*   `rbi` → `home_loan_emi` [Type: AFFECTS, Weight: 0.95, Polarity: +1, Delay: short]
*   `rbi` → `personal_loan_emi` [Type: AFFECTS, Weight: 0.90, Polarity: +1, Delay: short]

#### Event 3: Monsoon Deficit (Fixing the Agriculture gap)
*Add direct T→I bridges for agriculture and rural economy.*
*   `southwest_monsoon` → `pulses_and_legumes` [Type: PRODUCES, Weight: 0.8, Polarity: -1, Delay: medium] *(Polarity -1: Monsoon deficit (down) means prices/scarcity (up))*
*   `southwest_monsoon` → `rural_unemployment_rate` [Type: AFFECTS, Weight: 0.7, Polarity: -1, Delay: medium]

#### Event 4: Delhi AQI (Fixing Trigger Granularity)
*You must create a new Trigger node. "Weather" is not "Pollution".*
*   **NEW NODE:** `air_quality_index` (World: T-world, Axis: AQI level).
*   `air_quality_index` → `respiratory_conditions` [Type: AFFECTS, Weight: 0.9, Polarity: +1, Delay: short]
*   `air_quality_index` → `school_education` [Type: DISRUPTS, Weight: 0.8, Polarity: -1, Delay: short]
*   `air_quality_index` → `recreational_facilities` [Type: DISRUPTS, Weight: 0.7, Polarity: -1, Delay: short]

#### Event 5: IT Layoffs via Fed (Fixing Global-to-Local bridges)
*Add Fast-Track bridges from global macro to local micro.*
*   `us_federal_reserve` → `startup_ecosystem` [Type: FUNDS, Weight: 0.8, Polarity: -1, Delay: medium] *(Polarity -1: Fed rates up → Startup funding down)*
*   `startup_ecosystem` → `gig_worker_payouts` [Type: EMPLOYS, Weight: 0.7, Polarity: +1, Delay: short]
*   `startup_ecosystem` → `commercial_office_rent` [Type: AFFECTS, Weight: 0.6, Polarity: +1, Delay: medium]

### Summary of Next Steps for your Engineering Team:
1. **Update the Graph:** Inject the 14 edges and 1 new node listed above.
2. **Update the PPR Engine:** Apply the `0.1` penalty multiplier to `CONTAINS`/`IS_A` edges during the random walk transition probability calculation.
3. **Re-run the Evaluation:** These two steps alone will push your NDCG@10 well past 0.50 for these event types.
