"""Apply rule-based weight defaults to all edges based on edge type."""

from __future__ import annotations

import argparse
import logging
from collections import Counter
from pathlib import Path

from graph.merge import TaxonomyMerger, export_graph

log = logging.getLogger(__name__)

STRUCTURAL_DEFAULTS = {
    "CONTAINS":   {"weight": 0.9, "polarity": 1, "delay": "IMMEDIATE"},
    "IS_A":       {"weight": 0.2, "polarity": 1, "delay": "IMMEDIATE"},
    "PRODUCES":   {"weight": 0.9, "polarity": 1, "delay": "IMMEDIATE"},
    "SUPPLIES":   {"weight": 0.7, "polarity": 1, "delay": "SHORT_TERM"},
    "REGULATES":  {"weight": 0.8, "polarity": 1, "delay": "SHORT_TERM"},
    "DISRUPTS":   {"weight": 0.8, "polarity": -1, "delay": "IMMEDIATE"},
    "DEPENDS_ON": {"weight": 0.7, "polarity": 1, "delay": "SHORT_TERM"},
    "AFFECTS":    {"weight": 0.4, "polarity": 0, "delay": "SHORT_TERM"},
}

# Nodes exempt from fan-out penalty
MACRO_HUBS = {
    "crude_oil", "rbi_repo_rate", "monsoon", "nifty_50", "usd_inr",
    "cpi_inflation", "gdp_growth", "it_services_sector", "agriculture_sector",
    "electricity_tariff", "real_estate_prices",
}

FAN_OUT_THRESHOLD = 15
FAN_OUT_CAP = 0.4


def apply_defaults(G):
    """Fill missing edge properties from structural defaults.

    Only sets weight/polarity/delay when the YAML source did not provide them.
    YAML-authored values are never overwritten.
    """
    filled = 0
    type_counts = Counter()

    for src, dst, attrs in G.edges(data=True):
        edge_type = attrs.get("type", "")
        type_counts[edge_type] += 1

        defaults = STRUCTURAL_DEFAULTS.get(edge_type, {
            "weight": 0.4, "polarity": 0, "delay": "SHORT_TERM",
        })

        changed = False
        for key in ("weight", "polarity", "delay"):
            if key not in attrs or attrs[key] is None:
                attrs[key] = defaults[key]
                changed = True
        if changed:
            filled += 1

    return filled, type_counts


def apply_fan_out_penalty(G):
    """Cap weight on high-fan-out nodes not in MACRO_HUBS."""
    penalized = 0

    for node in G.nodes():
        if node in MACRO_HUBS:
            continue

        out_affects = [
            (node, succ) for succ in G.successors(node)
            if G.edges[node, succ].get("type") == "AFFECTS"
        ]

        if len(out_affects) > FAN_OUT_THRESHOLD:
            for src, dst in out_affects:
                if G.edges[src, dst]["weight"] > FAN_OUT_CAP:
                    G.edges[src, dst]["weight"] = FAN_OUT_CAP
                    penalized += 1
            log.info("Fan-out penalty: %s has %d AFFECTS edges, capped %d",
                     node, len(out_affects), penalized)

    return penalized


def print_stats(G, type_counts):
    """Print weight distribution stats."""
    from collections import Counter as C

    weight_dist = C()
    polarity_dist = C()
    delay_dist = C()

    for _, _, attrs in G.edges(data=True):
        w = attrs.get("weight", 1.0)
        weight_dist[w] += 1
        polarity_dist[attrs.get("polarity", 0)] += 1
        delay_dist[attrs.get("delay", "SHORT_TERM")] += 1

    print("\n=== Edge Type Distribution ===")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t or '(empty)'}: {count}")

    print("\n=== Weight Distribution ===")
    for w, count in sorted(weight_dist.items()):
        print(f"  {w}: {count}")

    print("\n=== Polarity Distribution ===")
    for p, count in sorted(polarity_dist.items()):
        label = {1: "+1 (direct)", -1: "-1 (inverse)", 0: "0 (complex)"}
        print(f"  {label.get(p, str(p))}: {count}")

    print("\n=== Delay Distribution ===")
    for d, count in sorted(delay_dist.items()):
        print(f"  {d}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Apply rule-based weight defaults")
    parser.add_argument("--dry-run", action="store_true", help="Print stats only, don't write")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    merger = TaxonomyMerger(root=args.root)
    G = merger.merge()

    print(f"Loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    updated, type_counts = apply_defaults(G)
    penalized = apply_fan_out_penalty(G)

    print(f"\nUpdated {updated} edges with structural defaults")
    print(f"Penalized {penalized} edges via fan-out cap")

    print_stats(G, type_counts)

    if not args.dry_run:
        out = args.root / "data" / "merged_graph.yaml"
        export_graph(G, out)
        print(f"\nExported to {out}")
    else:
        print("\n(dry run — no file written)")


if __name__ == "__main__":
    main()
