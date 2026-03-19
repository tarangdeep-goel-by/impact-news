# Graph Fixes Review — Gemini 3.1 Pro

Date: 2026-03-19

This is a classic knowledge graph tuning scenario. You are hitting the exact tension point between **causal rigor** (which demands long, accurate chains) and **ranking utility** (which demands short paths to prevent probability decay). 

Here is my expert review of your proposed fixes, evaluated against your Taxonomy Constitution and information-theoretic principles.

---

### 1. Review of Proposed Edges (Problem 1)

Adding "wormholes" (direct edges that skip intermediate nodes) is highly risky. It improves NDCG for known events but often destroys precision by creating false positives. 

**Crude Oil Event**
*   `brent_crude` → `vehicle_fuel` | **MODIFY** | *Reason:* Rule 3 (Bridge Edge). Indian fuel prices are deregulated but managed by OMCs. It is not `IMMEDIATE`. Change delay to `SHORT_TERM` and weight to `0.7` to reflect OMC buffering. 
*   `vehicle_fuel` → `delivery_and_logistics` | **APPROVE** | *Reason:* Strong, direct covariation.
*   `vehicle_fuel` → `auto_rickshaw_fare` | **MODIFY** | *Reason:* Rickshaw fares are highly regulated and "sticky." They do not covary smoothly with fuel; they step-function after union strikes. Reduce weight to `0.4`, delay to `MEDIUM_TERM`.
*   `delivery_and_logistics` → `retail_onion` | **REJECT** | *Reason:* Overfitting. Freight affects all goods. Target the parent category: `delivery_and_logistics` → `fresh_produce` [AFFECTS, w=0.6]. Let CONTAINS propagate it to onions, tomatoes, etc.

**RBI Event**
*   `rbi` → `home_loan_emi` | **REJECT** | *Reason:* Violates causal reality. RBI does not set EMIs; it sets the repo rate via the MPC, which banks use to set lending rates. Bypassing `monetary_policy_committee` and `repo_rate` breaks the graph's integrity. If the current path (`rbi` → `mpc` → `repo_rate` → `home_loan_emi`) yields low probability, **increase the weights on that specific chain** rather than short-circuiting it.

**Monsoon Event**
*   `southwest_monsoon` → `pulses_and_legumes` | **APPROVE** | *Reason:* Direct production relationship.
*   `southwest_monsoon` → `rural_unemployment_rate` | **APPROVE** | *Reason:* Valid Rule 1 covariation (Polarity -1).

**AQI Event**
*   `air_quality_index` (New Node) | **APPROVE placement** | *Reason:* Place under `meteorological_systems` (T1). It is a Trigger (system-level metric) that causes Impacts.
*   `air_quality_index` → `respiratory_conditions` | **APPROVE** | *Reason:* Classic Rule 3 Bridge edge.
*   `air_quality_index` → `school_education` | **APPROVE** | *Reason:* Valid DISRUPTS edge.
*   `air_quality_index` → `recreational_facilities` | **APPROVE** | *Reason:* Valid DISRUPTS edge.

**IT Layoffs Event**
*   `us_federal_reserve` → `startup_ecosystem` | **APPROVE** | *Reason:* Macro-trigger to macro-trigger.
*   `startup_ecosystem` → `gig_worker_payouts` | **MODIFY** | *Reason:* "Startup ecosystem" is too broad. If you have a node like `quick_commerce` or `platform_economy`, route it there first. If not, approve as a temporary fix, but it's borderline Rule 5 (too abstract).

---

### 2. Review of CONTAINS Propagation Flooding (Problem 2)

Your diagnosis is correct: standard PPR excludes CONTAINS, making the post-PPR downward propagation an artificial multiplier that floods the top-K with siblings. 

However, **pure division by $N$ is mathematically flawed.** In information theory, "impact" is not a conserved fluid. If a fire destroys a house, the living room and the kitchen are both 100% destroyed; the destruction isn't divided by the number of rooms. 

**The Fix: Square Root Penalty ($\sqrt{N}$)**
Change your propagation formula to:
`child_prob = parent_prob × (edge_weight / sqrt(num_siblings))`

*   **Why $\sqrt{N}$?** It provides a "soft penalty." If a category has 4 children, each gets divided by 2 (not 4). This prevents massive families (like 15 savings schemes) from dominating, without crushing small families (like 3 staple grains).
*   **Will it break the Monsoon case?** No. Rice, wheat, and millets ($N=3$) will be divided by ~1.73. Their *absolute* probability will drop, but because this penalty applies system-wide, their *relative* rank against non-monsoon nodes will remain intact.

**Alternative (and better) approach: MMR Reranking**
Instead of altering the graph probabilities, fix this in the **CIS reranking phase** using Maximal Marginal Relevance (MMR). 
1. Sort nodes by CIS score.
2. Pick the top node.
3. For the next node, penalize its score based on its *graph distance* (or shared parent) to nodes already in the top list. 
*Result:* If `fixed_deposits` is #1, `recurring_deposits` gets heavily penalized, allowing `home_loan_emi` to rise to #2. This solves the flooding without messing with the causal math.

---

### 3. Risks & Blindspots

*   **The "Sticky Node" Problem:** You are treating all edges equally. A 10% jump in crude oil immediately impacts wholesale inflation (WPI), but it takes a massive, sustained jump to change an `auto_rickshaw_fare`. Your graph currently lacks **inertia weights**. 
*   **Delay Ignorance:** You have `delay=IMMEDIATE` vs `SHORT_TERM` in your schema, but you didn't mention using them in the PPR math. **You should.** Modify the PPR transition matrix so that `IMMEDIATE` edges have a higher transition probability than `MEDIUM_TERM` edges during the random walk.
*   **Overfitting to NDCG@10:** By adding direct edges to push specific nodes into the top 10, you risk creating a "hairball" graph. If everything is connected to everything via 1 hop, PPR degrades into simple degree-centrality.

---

### 4. Prioritization: What to do first?

**Do the CONTAINS fix (Problem 2) FIRST.**
*   **Why?** It is a systemic, mathematical fix. Flooding is suppressing the true causal signals your PPR is already finding. If you implement the $\sqrt{N}$ penalty (or MMR), you will likely find that `home_loan_emi` naturally rises to the top 10 for the RBI event *without* needing to add a fake bypass edge.
*   **Next:** Add the AQI and Monsoon edges, as those represent genuinely missing causal links in the Indian context.
*   **Last:** Add the Crude Oil bypass edges, but only if the mathematical fixes fail to surface them. 

**Summary Recommendation:** Implement `child_prob = parent_prob × (edge_weight / sqrt(num_siblings))` today. Run your NDCG eval. I estimate this alone will push you from 0.34 to ~0.42 by unburying diverse impacts. Then, add the genuinely missing nodes (AQI) to cross the 0.50 threshold.
