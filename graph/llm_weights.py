"""Use Gemini to classify weight/polarity/delay for AFFECTS edges."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path

from google import genai

from graph.merge import TaxonomyMerger, export_graph
from graph.migrate_weights import apply_defaults

log = logging.getLogger(__name__)

BATCH_SIZE = 50
VALID_WEIGHTS = {0.2, 0.4, 0.7, 0.9}
VALID_POLARITIES = {-1, 0, 1}
VALID_DELAYS = {"IMMEDIATE", "SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"}

PROMPT_TEMPLATE = """You are an expert Indian macroeconomist. For each causal edge below, assign:

1. "weight": Shock transfer strength — what fraction of a shock in the source passes through to the target.
   STRICTLY choose one of: 0.9 (Critical/direct), 0.7 (Strong), 0.4 (Moderate), 0.2 (Weak/indirect)

2. "polarity": Direction of correlation.
   1 = direct (A↑ → B↑), -1 = inverse (A↑ → B↓), 0 = complex/unclear

3. "delay": Time for impact to manifest.
   "IMMEDIATE" (days), "SHORT_TERM" (weeks), "MEDIUM_TERM" (months), "LONG_TERM" (years)

Context: Indian economy. Consider local mechanisms, regulations, and market structure.

Edges to classify:
{edges_json}

Output ONLY a JSON array. Each element: {{"from": "...", "to": "...", "weight": 0.X, "polarity": N, "delay": "..."}}
No explanation, no markdown, just the JSON array."""


def get_affects_edges(G):
    """Get all AFFECTS edges that need LLM classification."""
    edges = []
    for src, dst, attrs in G.edges(data=True):
        if attrs.get("type") == "AFFECTS":
            edges.append({
                "from": src,
                "to": dst,
                "description": attrs.get("description", ""),
            })
    return edges


def classify_batch(client, batch):
    """Send one batch to Gemini, return parsed results."""
    edges_json = json.dumps(batch, indent=2)
    prompt = PROMPT_TEMPLATE.format(edges_json=edges_json)

    response = client.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=prompt,
        config=genai.types.GenerateContentConfig(temperature=0.2),
    )

    text = response.text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    results = json.loads(text)

    # Validate
    validated = []
    for r in results:
        if r.get("weight") not in VALID_WEIGHTS:
            r["weight"] = 0.4  # fallback
        if r.get("polarity") not in VALID_POLARITIES:
            r["polarity"] = 0
        if r.get("delay") not in VALID_DELAYS:
            r["delay"] = "SHORT_TERM"
        validated.append(r)

    return validated


def main():
    parser = argparse.ArgumentParser(description="LLM batch weight classification for AFFECTS edges")
    parser.add_argument("--apply", action="store_true", help="Apply saved results from data/llm_weights.json")
    parser.add_argument("--classify", action="store_true", help="Run LLM classification (calls Gemini API)")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Load and apply rule-based defaults first
    merger = TaxonomyMerger(root=args.root)
    G = merger.merge()
    apply_defaults(G)

    out_path = args.root / "data" / "llm_weights.json"

    if args.apply:
        # Apply from saved JSON — no API calls
        if not out_path.exists():
            log.error("No saved weights at %s — run with --classify first", out_path)
            return
        all_results = json.loads(out_path.read_text())
        print(f"Loaded {len(all_results)} saved classifications from {out_path}")
    else:
        # Classify via Gemini API
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            from config import settings
            api_key = settings.gemini_api_key
        if not api_key:
            log.error("GEMINI_API_KEY not set")
            return

        client = genai.Client(api_key=api_key)

        affects_edges = get_affects_edges(G)
        print(f"Found {len(affects_edges)} AFFECTS edges to classify")

        all_results = []
        batches = [affects_edges[i:i+BATCH_SIZE] for i in range(0, len(affects_edges), BATCH_SIZE)]

        for i, batch in enumerate(batches):
            print(f"Batch {i+1}/{len(batches)} ({len(batch)} edges)...")
            try:
                results = classify_batch(client, batch)
                all_results.extend(results)
                print(f"  → Got {len(results)} classifications")
            except Exception as e:
                log.error("Batch %d failed: %s", i+1, e)
                for edge in batch:
                    all_results.append({
                        "from": edge["from"], "to": edge["to"],
                        "weight": 0.4, "polarity": 0, "delay": "SHORT_TERM",
                    })

            if i < len(batches) - 1:
                time.sleep(2)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(all_results, indent=2))
        print(f"\nSaved {len(all_results)} classifications to {out_path}")

    # Print summary
    from collections import Counter
    w_dist = Counter(r["weight"] for r in all_results)
    p_dist = Counter(r["polarity"] for r in all_results)
    d_dist = Counter(r["delay"] for r in all_results)
    print(f"\nWeight distribution: {dict(sorted(w_dist.items()))}")
    print(f"Polarity distribution: {dict(sorted(p_dist.items()))}")
    print(f"Delay distribution: {dict(sorted(d_dist.items()))}")

    if args.apply or args.classify:
        # Apply to graph
        result_map = {(r["from"], r["to"]): r for r in all_results}
        applied = 0
        for src, dst, attrs in G.edges(data=True):
            key = (src, dst)
            if key in result_map:
                r = result_map[key]
                attrs["weight"] = r["weight"]
                attrs["polarity"] = r["polarity"]
                attrs["delay"] = r["delay"]
                applied += 1

        export_path = args.root / "data" / "merged_graph.yaml"
        export_graph(G, export_path)
        print(f"\nApplied {applied} LLM weights → {export_path}")


if __name__ == "__main__":
    main()
