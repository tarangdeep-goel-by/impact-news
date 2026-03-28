Here is the analysis and specific recommendation for your causal scoring engine. 

### The Root Cause: You are "Squaring" the Probability
Your intuition is entirely correct: the hub penalty is crushing multi-hop paths. But the mathematical flaw is actually deeper than just the hub penalty. 

Because your edge weights are row-normalized (they sum to 1), they act as transition probabilities. 
1. **PPR** calculates the probability of reaching a node.
2. **Magnitude** (product of edge weights along the path) *also* calculates the probability of that specific path.
3. By multiplying `PPR × Magnitude`, you are effectively **squaring the probability**. 

Fractions multiplied by fractions decay exponentially. Squaring them causes a catastrophic collapse of multi-hop signals. Adding a hub penalty on top of this is a triple-penalty.

Here are the direct answers to your questions, followed by the specific implementation recommendation.

---

### Answers to Your Questions

**1. What is the theoretically correct approach for this type of causal propagation graph?**
In causal graphs, **Probability** (PPR) and **Causal Strength** (Magnitude) are two different dimensions. 
*   **Probability** (PPR) answers: *"How likely is the signal to reach this node given the network topology?"* (Naturally decays with distance and hubs).
*   **Causal Strength** answers: *"If the signal reaches this node, how strong is the effect?"* In causal chains, strength does not inherently decay just because a path is long. A 3-hop chain of strong causal links (e.g., A causes B, B causes C, C causes D) results in a strong effect. The theoretically correct way to measure path strength is the **Bottleneck (Minimum) Edge Weight** along the path, not the product.

**2. Is the hub penalty fundamentally wrong, or just miscalibrated?**
It is **fundamentally wrong** in this specific architecture. PPR's random surfer model *inherently* penalizes hubs because the probability mass is divided among the outgoing edges. By adding a hub penalty to the magnitude, you are double-counting the dilution.

**3. Should magnitude factor into ranking at all, or should it be metadata only?**
It should factor into ranking, but **not as a decaying product**. If you only use PPR (Option B), 1-hop nodes will still naturally dominate because of the 0.20 restart probability (20% decay per hop). You need Magnitude to act as a "quality multiplier" for the path, independent of length.

**4. For the crop_damage → retail_rice chain: new node or direct edge?**
**Create a new node:** `domestic_agricultural_supply`. 
Direct edges from `crop_damage` to `retail_rice` violate causal ontology rules (often called "teleporting"). You must preserve the mechanism: *Event → Supply/Demand Shock → Price Impact*. 
*   **Correct Chain:** `agricultural_crop_damage` → `domestic_agricultural_supply` → `retail_rice` (and `retail_onion`). 
*   This also allows you to route domestic policies (like export bans) through the same supply node.

**5. What's the simplest change that would fix the most canaries without breaking the ones that already pass?**
**Option C combined with Option B's philosophy.** Remove the hub penalty entirely, change Magnitude to use the `min()` edge weight along the path, and keep the CIS formula multiplicative.

---

### The Recommended Solution (Code / Formula Changes)

Implement the following changes to your scoring engine. This will immediately fix the RBI and Monsoon canaries without artificially boosting irrelevant long paths.

#### 1. Redefine Magnitude (The "Bottleneck" Method)
Stop multiplying edge weights. Instead, find the "weakest link" in the dominant path. If a path consists of strong causal links, the magnitude remains high regardless of hop count.

```python
# OLD MAGNITUDE
# magnitude = product of (edge_weight * (1/log2(out_degree + 1))) along path

# NEW MAGNITUDE
# Find the dominant path (the path that contributed the most to the node's PPR)
def calculate_magnitude(dominant_path_edges):
    if not dominant_path_edges:
        return 0.0
    
    # The strength of a causal chain is its weakest link
    # No hub penalty. PPR already handled the hubs.
    return min(edge.weight for edge in dominant_path_edges)
```
*(Note: If you want a slightly softer approach than `min`, use the `mean` of the edge weights along the path. But `min` is theoretically superior for causal chains).*

#### 2. Keep the CIS Formula Multiplicative
Because Magnitude is no longer an exponentially decaying fraction, it is safe to multiply it by PPR.

```python
# CIS Formula remains structurally the same, but the inputs are fixed
CIS = ppr_probability * magnitude * world_boost * leaf_boost
```

#### Why this fixes your Canaries:

**Example: RBI → MPC → home_loan_emi**
*   *Old System:* PPR decayed. Magnitude decayed to ~0.02 due to hub penalties and fraction multiplication. CIS was crushed.
*   *New System:* PPR still decays slightly (correctly reflecting distance). But Magnitude is now `min(weight_rbi_mpc, weight_mpc_emi)`. If both are strong edges (e.g., 0.8), Magnitude is 0.8. 
*   The `world_boost` and `leaf_boost` applied to `home_loan_emi` will now easily overpower the 1-hop `india_forex_reserves` (which gets no citizen/leaf boosts), pushing EMI to the top 5.

**Example: southwest_monsoon → ... → retail_rice**
*   *Old System:* Monsoon's out-degree of 8 triggered a massive hub penalty, crushing all downstream paths.
*   *New System:* Hub penalty is gone. PPR distributes probability across the 8 edges. The path to `retail_rice` via `domestic_agricultural_supply` will have a high bottleneck magnitude. The `leaf_boost` and `world_boost` on `retail_rice` will elevate it above the 1-hop intermediate nodes like `stagnant_water` (which might be L3 and lack the leaf boost).

### Summary of Action Plan
1. **Drop the hub penalty** from the codebase entirely.
2. **Change Magnitude** from `product()` to `min()` along the dominant path.
3. **Add `domestic_agricultural_supply`** to fix the ontology for Indian domestic produce. 
4. Run the 10 failing canaries. You should see an immediate inversion where L4 citizen impacts rise to the top.