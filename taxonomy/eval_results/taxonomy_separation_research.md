# Taxonomy vs Causal Edge Separation — Gemini Research

## Thinking

**My Thoughts on Building a News Impact Analysis System for India**

Okay, so the challenge is this: a News Impact Analysis system for India, using a knowledge graph, and the user's running into problems with mixed edge types and orphans. We’re aiming for a practical solution, given that it’s a solo developer working on it. I need to synthesize the best approach, given that I'm an expert in this field.

First, I need to break down the user's problem to identify the core issue. They've got a knowledge graph. But the issue is that ~29% of edges are taxonomic and it's causing pathfinding issues. Then there are those 558 leaf nodes with *only* taxonomic edges, and they become orphans if we ignore taxonomic edges during causal traversal. The user has proposed several solutions, each with its problems. And there are some important constraints in mind: real-time traversal, maintainability, accuracy, and entity matching.

I've got to consider what the big guys do: Neo4j, Wikidata, Google Knowledge Graph. They tend to use Property Graphs or RDF with strict edge typing. They filter by edge type at query time. Ontology or taxonomy is key for Entity Resolution. And they use causal/semantic edges for reasoning.

The problem with the orphan nodes, this is key. Is it a bug, or a feature? If an article mentions "basmati rice exports", and the system only knows about *rice*, how do we make that connection? I've got it. The taxonomic edges aren't about *horizontal* causality; they're for *vertical* inheritance. An event hitting `basmati_rice` can traverse *up* to `rice`, find causal edges, and propagate. And then we can go *down* again, specific to the `basmati_rice`.

So, evaluating the user's options is critical. Option B, query-time filtering, is a good idea. That’s standard for Neo4j. No need for two physical layers. We can just write queries like `MATCH (a)-[:AFFECTS|PRODUCES*]->(b)`. Option C, manually promoting leaves, is too much effort for a solo dev. Plus, `basmati_rice` is very likely to have the *same* causal effects as `rice`, just different magnitudes. Don't repeat edges. Option D, collapsing the taxonomy, is bad for NLP. We don't want to lose that granularity.

My solution is a "Hybrid Inheritance" approach. We’ll use Taxonomy for *Entity Resolution and Property Inheritance* and Causal edges for *Impact Propagation*.

1.  **NLP/Entity Matching**: "Basmati" -> `basmati_rice` node.
2.  **Causal Entry Point**:
    *   Does `basmati_rice` have causal edges? Yes, Traverse them.
    *   No, then Traverse `[:IS_A | :CONTAINS]` *upward* to `rice`. Does `rice` have causal edges? Yes. Traverse.

This solves the orphan problem. No new edges are needed and we keep our NLP detail.

So, addressing the user's specific questions.

*   **Best approach**: Option B (Query-time filtering) combined with this Hybrid logic. It’s maintainable.
*   **What big KG systems do**: They separate ontological and semantic edges. They filter at query time. They use inference engines with rules like: *If A is a subclass of B, and B affects C, then A affects C*.
*   **Are the leaf nodes needed?**: Yes, for NLP. Framework is:
    1.  *NLP Value*: Does news use this term?
    2.  *Causal Divergence*: Does `basmati_rice` have a *different* downstream effect than `rice`? If yes, new causal edge. If no, inherit.
*   **Concrete Architecture**: Single graph (Property Graph like Neo4j).
    *   **Edge Types**: `IS_A` (taxonomy), `AFFECTS/PRODUCES` (causal). Change `CONTAINS` to `IS_A` or `SUBCATEGORY_OF` for better accuracy.
    *   **Query Strategy**: "Elevator and Train" analogy. Up the taxonomy (elevator) to find a causal edge. Across the causal network (train). Down to specific impacted entities.
    *   **Migration Path**: Rename edges. Write the new Cypher/traversal query. Prune useless top-level containers.
*   **What are we missing**:
    *   Taxonomy directionality. Need bottom-up ( `IS_A` or `BELONGS_TO`).
    *   Edge weights/polarity. "+" or "-" on causal edges.

## Answer

As a solo developer building a practical, real-world system, you need an approach that maximizes automation and minimizes manual data entry, while keeping your NLP (Natural Language Processing) entity matching highly accurate. 

Here is the breakdown of how to solve this, drawing on industry best practices from systems like Neo4j, Wikidata, and Palantir.

---

### 1. Which approach is best? (The "Elevator and Train" Hybrid)

The best approach is a modified **Option B (Edge-type filtering at query time)** combined with **Taxonomic Inheritance**. 

Think of your graph as having **Elevators** (Taxonomy edges) and **Trains** (Causal edges). 
*   **Trains** move you horizontally across the economy (`crude_oil` → `transport_costs` → `food_prices`).
*   **Elevators** move you vertically between levels of specificity (`basmati_rice` ↑ `rice` ↑ `staple_grains`).

**How it works:**
When the news mentions "Basmati rice exports banned", your NLP matches the `basmati_rice` node. Because it's an orphan in the causal layer, you take the **Elevator UP** to `rice`. `Rice` has causal edges (Trains). You take the **Train ACROSS** to `food_inflation`. Finally, you can take the **Elevator DOWN** to see what specific things are affected (e.g., `consumer_wallet`).

This completely solves the pathfinding pollution (Trains never travel on Elevator shafts) AND solves the orphan problem (orphans are just entry/exit lobbies that use Elevators to reach the Trains).

### 2. What do Knowledge Graph systems do?

Large KGs (like Google's or Wikidata) use **Ontological Inference**. They strictly separate structural edges (`rdf:type`, `rdfs:subClassOf`) from semantic edges (`affects`, `produces`).

They do exactly what is described above using query-time filtering. In Neo4j (Cypher query language), a causal path trace looks like this:
`MATCH path = (startNode)-[:AFFECTS|PRODUCES|REGULATES*1..5]->(endNode)`

By explicitly naming the causal edge types in the query, the graph engine completely ignores the `CONTAINS` edges during the causal traversal. It costs zero extra processing time; graph databases are optimized for this.

### 3. Are the 558 leaf nodes needed? (The Framework)

Yes, they are highly valuable, but **not for causality—they are for Entity Resolution (NLP).** 

If you collapse `basmati_rice` into `rice`, and an article says "Basmati prices surge", your NLP might fail to trigger because the exact string is missing. 

**The Decision Framework for Leaf Nodes:**
Ask yourself: *Does this leaf node have a DIFFERENT causal chain than its parent?*
*   **Scenario A (Keep as pure taxonomy leaf):** `delhi_metro` and `mumbai_metro`. If power prices go up, both are affected exactly the same way as their parent node `public_transit`. Keep them as taxonomy leaves so your NLP can match them, but let them inherit causal edges from `public_transit`.
*   **Scenario B (Promote to Causal):** `basmati_rice` vs `non_basmati_rice`. In India, Basmati is heavily exported (affects `forex_reserves`), while non-Basmati is used for the PDS system (affects `domestic_food_security`). Because their causal impacts *diverge*, you should add specific causal edges to them.
*   **Scenario C (Collapse into Alias):** `petrol` and `gasoline`. They are the exact same thing. Store "gasoline" as an array of `aliases` inside the `petrol` node properties.

### 4. Concrete Architecture Recommendation

Here is your exact blueprint for implementation.

#### Graph Structure (Single Graph)
Keep everything in one graph. However, fix your taxonomy edge direction. `CONTAINS` is top-down, which makes upward traversal clunky. Rename/reverse them to `IS_A` or `SUBCATEGORY_OF` (bottom-up). 
*   *Old:* `rice -[CONTAINS]-> basmati`
*   *New:* `basmati -[IS_A]-> rice`

#### Node Granularity Rules
1.  Top-level containers (`energy_and_fuel`, `food_and_nutrition`) are useless for causality. Keep them ONLY if you use them to filter UI dashboards (e.g., "Show me all Energy impacts").
2.  Keep the 558 leaf nodes. They are your "NLP Catchers".

#### Query Strategy (The Algorithm)
When a news event hits a node (e.g., `basmati_rice`), run this logic:

**Step 1: Find the Causal Entry Point**
Does the triggered node have outgoing causal edges?
*   If YES: Start traversal from here.
*   If NO: Traverse `IS_A` edges upward until you hit a node with causal edges. (e.g., `basmati` ↑ `rice`). Start traversal from `rice`.

**Step 2: Causal Traversal**
Run a BFS/Dijkstra that *strictly filters* for causal edges (`AFFECTS`, `PRODUCES`, `INCREASES`, `DECREASES`). Limit the depth to 3 or 4 hops, otherwise, in an economy, everything eventually affects everything.

**Step 3: Downward Expansion (Optional but cool)**
If your causal chain hits `public_transit`, you can traverse `IS_A` edges *downward* to tell the user: *"This will impact Public Transit (including Delhi Metro, Mumbai Metro, etc.)"*.

#### Migration Path for you this weekend:
1.  **Script 1:** Rename/reverse your `CONTAINS` edges to `IS_A` (bottom-up).
2.  **Update your Traversal Code:** Modify your BFS/Dijkstra to only accept your specific causal edge labels.
3.  **Implement the "Elevator":** Write a simple recursive function: `def get_causal_parent(node):` that checks for causal edges, and if none exist, moves up the `IS_A` edge and checks again.

### 5. What are you missing?

**A. Edge Polarity (Crucial for News Impact)**
If the news says "Crude oil prices RISE", how does the system know if consumer wallet goes UP or DOWN? 
Your causal edges need a property, e.g., `correlation: "direct"` or `correlation: "inverse"`.
*   `crude_oil` --[AFFECTS {corr: direct}]--> `transport_costs` (Oil goes up, transport goes up).
*   `transport_costs` --[AFFECTS {corr: inverse}]--> `consumer_savings` (Transport goes up, savings go down).
Without this, your system can only say "X is affected", but cannot say *how*.

**B. The "Everything is connected" problem**
With 1,600 nodes, a 5-hop causal traversal will likely light up the entire graph. You need edge weights. 
*   `monsoon` --[AFFECTS {weight: 0.9}]--> `agriculture`
*   `monsoon` --[AFFECTS {weight: 0.2}]--> `umbrella_sales`
When traversing, multiply the weights. Drop paths where the cumulative weight falls below a certain threshold (e.g., 0.3) to filter out butterfly-effect noise.

**Summary:** Do not delete your taxonomy, and do not manually draw 500 new causal edges. Use taxonomy for NLP matching and inheritance, and strictly filter edge types during your causal pathfinding.
