"""Dump node adjacency list for LLM review.

Generates a YAML file showing every node with causal edges and its
immediate connections. Always reads from the merged graph, so it
stays in sync with taxonomy changes.

Usage:
    python3 scripts/dump_adjacency.py                    # Full dump to taxonomy/eval_results/adjacency.yaml
    python3 scripts/dump_adjacency.py --chunk 50         # Also split into 50-node chunks for Gemini review
    python3 scripts/dump_adjacency.py --node brent_crude # Single node inspect
    python3 scripts/dump_adjacency.py --l1 T3            # Dump one L1 only
"""

import argparse
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from graph.merge import TaxonomyMerger
from graph.migrate_weights import apply_defaults

CAUSAL_TYPES = {
    "AFFECTS", "PRODUCES", "REGULATES", "DISRUPTS", "SUPPLIES",
    "DEPENDS_ON", "FUNDS", "COMPETES_WITH", "EMPLOYS", "MANAGES",
}

OUTPUT_DIR = PROJECT_ROOT / "taxonomy" / "eval_results"


def build_adjacency(G) -> list[dict]:
    """Build adjacency list for all nodes with causal edges."""
    entries = []

    # Collect causal edges
    causal_out: dict[str, list] = {}
    causal_in: dict[str, list] = {}
    for u, v, d in G.edges(data=True):
        if d.get("type") not in CAUSAL_TYPES:
            continue
        causal_out.setdefault(u, []).append((v, d))
        causal_in.setdefault(v, []).append((u, d))

    causal_nodes = sorted(set(causal_out) | set(causal_in))

    for nid in causal_nodes:
        nd = G.nodes.get(nid, {})
        entry = {
            "node": nid,
            "level": nd.get("level", "?"),
            "category": nd.get("category", "?"),
            "aliases": nd.get("aliases", [])[:3],
        }

        # Parent (CONTAINS)
        for pred in G.predecessors(nid):
            if G.edges[pred, nid].get("type") == "CONTAINS":
                entry["parent"] = pred
                break

        # Outgoing causal
        out_edges = causal_out.get(nid, [])
        if out_edges:
            entry["out"] = []
            for tgt, d in sorted(out_edges, key=lambda x: -x[1].get("weight", 0)):
                tgt_cat = G.nodes.get(tgt, {}).get("category", "?")
                entry["out"].append({
                    "to": tgt,
                    "to_cat": tgt_cat,
                    "type": d.get("type", "?"),
                    "w": round(d.get("weight", 0), 2),
                    "pol": d.get("polarity", "?"),
                    "delay": d.get("delay", "?"),
                    "desc": d.get("description", ""),
                })

        # Incoming causal
        in_edges = causal_in.get(nid, [])
        if in_edges:
            entry["in"] = []
            for src, d in sorted(in_edges, key=lambda x: -x[1].get("weight", 0)):
                src_cat = G.nodes.get(src, {}).get("category", "?")
                entry["in"].append({
                    "from": src,
                    "from_cat": src_cat,
                    "type": d.get("type", "?"),
                    "w": round(d.get("weight", 0), 2),
                    "pol": d.get("polarity", "?"),
                    "delay": d.get("delay", "?"),
                    "desc": d.get("description", ""),
                })

        entries.append(entry)

    return entries


def write_yaml(entries: list[dict], path: Path) -> None:
    path.write_text(
        yaml.dump({"nodes": entries, "count": len(entries)},
                  default_flow_style=False, sort_keys=False, allow_unicode=True)
    )


def chunk_entries(entries: list[dict], chunk_size: int) -> list[list[dict]]:
    """Split into chunks, keeping same-L1 nodes together."""
    # Group by category
    by_cat: dict[str, list] = {}
    for e in entries:
        cat = e.get("category", "?")
        by_cat.setdefault(cat, []).append(e)

    chunks = []
    current = []
    for cat in sorted(by_cat):
        for e in by_cat[cat]:
            current.append(e)
            if len(current) >= chunk_size:
                chunks.append(current)
                current = []
    if current:
        chunks.append(current)

    return chunks


def print_node(entry: dict) -> None:
    """Pretty-print one node's connections."""
    print(f"\n{'='*60}")
    print(f"{entry['node']} (L{entry['level']}, {entry['category']})")
    aliases = ", ".join(entry.get("aliases", []))
    if aliases:
        print(f"  aliases: {aliases}")
    if entry.get("parent"):
        print(f"  parent: {entry['parent']}")

    out = entry.get("out", [])
    if out:
        print(f"\n  OUT ({len(out)} edges):")
        for e in out:
            print(f"    →[{e['type']} w={e['w']} pol={e['pol']} {e['delay']}]→ {e['to']} ({e['to_cat']})")
            print(f"      {e['desc'][:90]}")

    inp = entry.get("in", [])
    if inp:
        print(f"\n  IN ({len(inp)} edges):")
        for e in inp:
            print(f"    {e['from']} ({e['from_cat']}) →[{e['type']} w={e['w']} pol={e['pol']} {e['delay']}]→")
            print(f"      {e['desc'][:90]}")


def main():
    parser = argparse.ArgumentParser(description="Dump node adjacency for review")
    parser.add_argument("--chunk", type=int, default=0, help="Split into N-node chunks")
    parser.add_argument("--node", type=str, help="Inspect a single node")
    parser.add_argument("--l1", type=str, help="Dump one L1 category only")
    args = parser.parse_args()

    merger = TaxonomyMerger()
    G = merger.merge()
    apply_defaults(G)

    entries = build_adjacency(G)

    # Single node inspect
    if args.node:
        matches = [e for e in entries if e["node"] == args.node]
        if not matches:
            print(f"Node '{args.node}' not found or has no causal edges")
            sys.exit(1)
        print_node(matches[0])
        return

    # Filter by L1
    if args.l1:
        entries = [e for e in entries if e.get("category") == args.l1.upper()]
        if not entries:
            print(f"No nodes found for {args.l1}")
            sys.exit(1)

    # Write full dump
    out_path = OUTPUT_DIR / "adjacency.yaml"
    write_yaml(entries, out_path)
    print(f"Written {len(entries)} nodes to {out_path}")

    # Stats
    from collections import Counter
    cats = Counter(e["category"] for e in entries)
    print(f"\nBy L1:")
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count} nodes")

    total_out = sum(len(e.get("out", [])) for e in entries)
    total_in = sum(len(e.get("in", [])) for e in entries)
    print(f"\nTotal out-edges: {total_out}")
    print(f"Total in-edges: {total_in}")

    # Chunk if requested
    if args.chunk > 0:
        chunks = chunk_entries(entries, args.chunk)
        chunk_dir = OUTPUT_DIR / "adjacency_chunks"
        chunk_dir.mkdir(exist_ok=True)
        for i, chunk in enumerate(chunks):
            chunk_path = chunk_dir / f"chunk_{i+1:02d}.yaml"
            write_yaml(chunk, chunk_path)
        print(f"\nSplit into {len(chunks)} chunks in {chunk_dir}/")


if __name__ == "__main__":
    main()
