"""Evaluate taxonomy graph domains using Gemini 3.1 Pro with max thinking.

Usage:
    python -m audit.eval_graph <domain>              # Evaluate one domain
    python -m audit.eval_graph all                    # Evaluate all domains sequentially
    python -m audit.eval_graph energy financial       # Evaluate specific domains
    python -m audit.eval_graph --list                 # List available domains

Examples:
    GEMINI_API_KEY=xxx python -m audit.eval_graph energy
    GEMINI_API_KEY=xxx python -m audit.eval_graph all
"""

import json
import os
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types

EVAL_DIR = Path("taxonomy/eval_chunks")
OUTPUT_DIR = Path("taxonomy/eval_results")

DOMAINS = [
    "energy",
    "financial",
    "food_agriculture",
    "macro_geopolitics",
    "employment",
    "governance",
    "infrastructure",
    "consumer_life",
]

PROMPT = """\
You are a ruthlessly critical expert on Indian economics, governance, infrastructure, and daily life. You are auditing a causal knowledge graph that powers a NEWS IMPACT SYSTEM — when a news article mentions "crude oil prices rise", the system must trace ALL downstream effects on Indian citizens' daily lives (fuel prices → transport costs → food delivery prices → restaurant bills, etc.).

THE STANDARD IS PERFECTION. A score of 7 means "barely usable." A score of 9 means "production-ready with minor gaps." Only give 10 if you genuinely cannot find a single missing chain. Be brutally honest. If the graph would fail to explain a front-page Times of India story to a common citizen, that's a critical gap.

The JSON below contains one domain of the graph with:
- **nodes**: Things that exist (e.g., crude_oil, repo_rate, monsoon)
- **edges**: Causal relationships between them (from → to, with type and description)
- **cross-domain edges**: Marked with "cross" field showing the external category

## YOUR EVALUATION CRITERIA

### 1. IMPACT CHAIN COMPLETENESS (Most Important)
Test these scenarios mentally. For EACH, trace the chain from trigger to citizen impact. If any link is missing, report it as P0:

**Economic triggers:** RBI rate hike, rupee depreciation, crude oil spike, stock market crash, GST rate change, budget announcement
**Climate triggers:** Weak monsoon, cyclone, heatwave, floods, El Niño
**Policy triggers:** Farm bill, labor code change, import/export ban, FDI policy, demonetization-scale disruption
**Infra triggers:** Power grid failure, water crisis, telecom outage, highway toll hike
**Global triggers:** US Fed rate hike, China trade war, Russia-Ukraine conflict, OPEC cut

For EACH missing link in any chain, report:
- from: <existing_node_id or new_node_id>
- to: <existing_node_id or new_node_id>
- type: AFFECTS|PRODUCES|REGULATES|DISRUPTS|DEPENDS_ON|SUPPLIES
- description: Why this edge matters (India-specific, cite mechanisms)
- severity: P0 (chain broken) / P1 (chain weak) / P2 (nice to have)

### 2. NODE DEFINITION AUDIT
For EVERY node in this domain, check:
- Is the node too vague? (e.g., "economy" is useless — what specifically?)
- Is the node too granular? (e.g., "onion_price_mandi_lasalgaon" should be "onion_wholesale_price")
- Are aliases comprehensive? Would a journalist's headline match? (e.g., "repo rate" node should have aliases ["policy rate", "benchmark rate", "RBI rate"])
- Are there nodes that exist but serve no purpose — no meaningful edges, no news would reference them?

List ALL definition problems, not just a sample.

### 3. INCORRECT/MISLEADING EDGES
- Wrong causal direction (A doesn't cause B, B causes A)
- Wrong relationship type
- Factually incorrect description
- Too indirect (should be 2+ edges with intermediate nodes)
- CONTAINS edges used where causal edges are needed (this is a causal graph, not a taxonomy)

### 4. MISSING NODES — COVERAGE GAPS
What real-world concepts are MISSING that would prevent the system from explaining news impacts?
Think about:
- What makes front-page news in India that this graph can't explain?
- What do citizens actually worry about that has no representation?
- What government schemes/policies affect millions but are absent?
- What economic indicators do analysts track that are missing?

### 5. DUPLICATE/REDUNDANT NODES
Node pairs representing the same concept. Be thorough.

### 6. DESCRIPTION QUALITY
- Count edges with empty descriptions (these are BROKEN — a causal graph without explanations is useless)
- Flag descriptions that are:
  - Copy-pasted / generic (not India-specific)
  - Factually wrong
  - Missing the actual causal mechanism
  - Too vague to be useful ("X affects Y" without saying HOW)

### 7. CROSS-DOMAIN GAPS
- What connections to other domains are completely missing?
- Think about a citizen who reads news about this domain — what other life areas would they wonder about?

### 8. SCORING (BE HARSH)
Rate 1-10, with this calibration:
- **1-3**: Fundamentally broken, missing most important chains
- **4-5**: Major gaps, would fail on common news stories
- **6-7**: Functional but incomplete, misses many second-order effects
- **8**: Good coverage, minor gaps, production-viable with fixes
- **9**: Excellent, only edge cases missing
- **10**: Cannot find a gap (virtually never appropriate)

Score on:
- **completeness**: Can every major news trigger be traced to citizen impact?
- **accuracy**: Are the causal directions and mechanisms correct?
- **granularity**: Right level of detail for news impact analysis?
- **india_specificity**: Does it capture Indian-specific dynamics (not generic economics)?
- **description_quality**: Do descriptions explain the actual causal mechanism?
- **overall**: Geometric mean of above, rounded to 1 decimal

### OUTPUT FORMAT
Return ONLY structured YAML (no prose outside the YAML block):

```yaml
missing_edges:
  - from: node_a
    to: node_b
    type: AFFECTS
    description: "..."
    severity: P0

incorrect_edges:
  - from: node_a
    to: node_b
    issue: "..."

node_definition_issues:
  - id: node_id
    issue: "Too vague / aliases incomplete / serves no purpose"
    fix: "Rename to X / add aliases [a, b] / delete"

missing_nodes:
  - id: suggested_id
    aliases: ["..."]
    category: "..."
    why: "..."

duplicate_nodes:
  - keep: node_a
    merge: node_b

description_issues:
  - from: node_a
    to: node_b
    issue: "..."

cross_domain_gaps:
  - from_domain: this_domain
    to_domain: other_domain
    missing_link: "Description of what connection is missing"

scores:
  completeness: 6
  accuracy: 7
  granularity: 6
  india_specificity: 7
  description_quality: 3
  overall: 5.5
```

Here is the graph domain to evaluate:

"""


def evaluate_domain(client, domain: str) -> str:
    """Evaluate a single domain chunk."""
    chunk_path = EVAL_DIR / f"{domain}.json"
    if not chunk_path.exists():
        print(f"  ERROR: {chunk_path} not found")
        return ""

    graph_data = chunk_path.read_text()
    full_prompt = PROMPT + graph_data

    print(f"  Sending to Gemini 3.1 Pro (thinking=high)...")
    print(f"  Input size: {len(graph_data) / 1024:.0f} KB")

    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-pro-preview",
                contents=full_prompt,
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
                print(f"  Retry {attempt + 1}/{max_retries} — server busy, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    else:
        print(f"  FAILED after {max_retries} retries")
        return ""

    # Extract thinking and answer
    thinking_text = ""
    answer_text = ""
    for part in response.candidates[0].content.parts:
        if part.thought:
            thinking_text += part.text + "\n"
        else:
            answer_text += part.text + "\n"

    # Token usage
    usage = response.usage_metadata
    print(f"  Thinking tokens: {usage.thoughts_token_count}")
    print(f"  Output tokens: {usage.candidates_token_count}")
    print(f"  Total tokens: {usage.total_token_count}")

    return answer_text.strip()


def main():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable")
        sys.exit(1)

    args = sys.argv[1:]

    if not args or "--help" in args:
        print(__doc__)
        sys.exit(0)

    if "--list" in args:
        print("Available domains:")
        for d in DOMAINS:
            chunk = EVAL_DIR / f"{d}.json"
            if chunk.exists():
                data = json.loads(chunk.read_text())
                print(f"  {d}: {data['node_count']} nodes, {data['edge_count']} edges")
            else:
                print(f"  {d}: (file missing)")
        sys.exit(0)

    # Determine which domains to evaluate
    if "all" in args:
        domains = DOMAINS
    else:
        domains = [d for d in args if d in DOMAINS]
        unknown = [d for d in args if d not in DOMAINS and not d.startswith("-")]
        if unknown:
            print(f"Unknown domains: {unknown}")
            print(f"Available: {DOMAINS}")
            sys.exit(1)

    if not domains:
        print("No domains specified. Use --list to see available domains.")
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)

    client = genai.Client(api_key=api_key)

    for i, domain in enumerate(domains, 1):
        print(f"\n[{i}/{len(domains)}] Evaluating: {domain}")
        result = evaluate_domain(client, domain)

        if result:
            out_path = OUTPUT_DIR / f"{domain}_eval.md"
            out_path.write_text(result)
            print(f"  Saved to {out_path}")
        else:
            print(f"  No result for {domain}")

    print(f"\nDone. Results in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
