"""Ask Gemini 3.1 Pro about taxonomy vs causal edge separation strategies.

Usage:
    GEMINI_API_KEY=xxx python -m audit.research_taxonomy_separation
"""

import os
import sys
import time

from google import genai
from google.genai import types

PROMPT = """\
I'm building a NEWS IMPACT ANALYSIS system for India. When a news headline says "crude oil prices rise", the system traces ALL downstream effects on citizens' daily lives using a causal knowledge graph.

## Current Architecture Problem

My graph has 1,629 nodes and 2,585 edges. But ~29% of edges (729) are CONTAINS/LOCATED_IN (taxonomy edges), not causal edges. They come from a hierarchical tree that organizes nodes into categories:

```
food_and_nutrition (CONTAINS) → staple_grains (CONTAINS) → rice (CONTAINS) → basmati_rice
energy_and_fuel (CONTAINS) → fossil_fuels (CONTAINS) → crude_oil
```

The causal edges (AFFECTS, PRODUCES, REGULATES, etc.) connect nodes ACROSS this hierarchy:
```
crude_oil --AFFECTS--> petrol --AFFECTS--> consumer
monsoon --AFFECTS--> rice_production --AFFECTS--> food_inflation
```

### The Problem:
1. **558 leaf nodes (34%) connect ONLY via CONTAINS** — they have no causal edges. Examples: `basmati_rice`, `delhi_metro`, specific disease names. If I remove CONTAINS edges, 34% of nodes become orphans.

2. **Pathfinding pollution**: When tracing "crude_oil → consumer impact", BFS/Dijkstra traverses CONTAINS edges and finds paths like `crude_oil → energy_and_fuel → fossil_fuels → coal` which is taxonomic, not causal.

3. **Container nodes are noise**: `energy_and_fuel`, `food_and_nutrition`, `natural_disasters` etc. are pure category labels with 0 causal significance. They appear in paths but add nothing.

### My Options (as I see them):

**Option A: Dual-layer graph**
- Layer 1: Taxonomy (CONTAINS, IS_A) — for categorization/UI only
- Layer 2: Causal (AFFECTS, PRODUCES, etc.) — for impact propagation
- Pathfinding ONLY uses Layer 2
- Challenge: 558 nodes become orphans in Layer 2

**Option B: Edge-type filtering at query time**
- Keep single graph, but exclude CONTAINS/LOCATED_IN during traversal
- Simpler architecture, same orphan problem

**Option C: Promote leaf nodes**
- For each taxonomy-only leaf node, add at least 1 causal edge connecting it to the network
- e.g., `basmati_rice --AFFECTS--> rice_export_revenue`
- Eliminates orphans but requires 500+ new edges (many might be forced/artificial)

**Option D: Collapse taxonomy**
- Merge leaf nodes into their nearest causally-connected ancestor
- e.g., `basmati_rice` → store as alias of `rice` (which has causal edges)
- Reduces node count but loses granularity

**Option E: Hybrid**
- Some combination of above

## What I Need From You

1. **Which approach is best for a news impact system?** Consider: real-time traversal performance, maintainability, accuracy of impact chains, ability to match news article entities to graph nodes.

2. **What do knowledge graph systems (Google KG, Wikidata, Neo4j best practices) do?** How do they handle mixed taxonomy+causal edges?

3. **For the 558 taxonomy-only leaf nodes — are they actually needed?** Would a news impact system ever need `basmati_rice` as a separate node, or is `rice` sufficient? Give me a framework for deciding which leaf nodes to keep vs collapse.

4. **Concrete architecture recommendation** with:
   - Graph structure (single vs multi-layer)
   - Query strategy (how to traverse for impact)
   - Node granularity rules (when to keep leaf nodes vs collapse)
   - Migration path from current state

5. **What am I missing?** Any approaches or considerations I haven't thought of?

Be specific and practical. I'm a solo developer, not a team of 10. The system needs to work, not be academically perfect.
"""


def main():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    print("Sending to Gemini 3.1 Pro (thinking=high)...")
    print(f"Prompt size: {len(PROMPT)} chars")

    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-pro-preview",
                contents=PROMPT,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_level="high",
                        include_thoughts=True,
                    ),
                    temperature=0.4,
                ),
            )
            break
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e) or "429" in str(e):
                wait = 30 * (attempt + 1)
                print(f"Retry {attempt + 1}/{max_retries} — waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    else:
        print(f"FAILED after {max_retries} retries")
        sys.exit(1)

    thinking_text = ""
    answer_text = ""
    for part in response.candidates[0].content.parts:
        if part.thought:
            thinking_text += part.text + "\n"
        else:
            answer_text += part.text + "\n"

    usage = response.usage_metadata
    print(f"Thinking tokens: {usage.thoughts_token_count}")
    print(f"Output tokens: {usage.candidates_token_count}")
    print(f"Total tokens: {usage.total_token_count}")

    out_path = "taxonomy/eval_results/taxonomy_separation_research.md"
    with open(out_path, "w") as f:
        f.write("# Taxonomy vs Causal Edge Separation — Gemini Research\n\n")
        if thinking_text:
            f.write("## Thinking\n\n")
            f.write(thinking_text.strip() + "\n\n")
        f.write("## Answer\n\n")
        f.write(answer_text.strip() + "\n")

    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
