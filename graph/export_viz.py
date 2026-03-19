"""Export impact graph to JSON for Cytoscape.js visualizer."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from graph.merge import TaxonomyMerger
from graph.migrate_weights import apply_defaults
from graph.markov_engine import CAUSAL_TYPES, CausalMarkovEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# L1 category metadata
# ---------------------------------------------------------------------------

CATEGORIES = {
    "t1": {"name": "Natural & Planetary Systems", "world": "trigger"},
    "t2": {"name": "Institutional & Sovereign Entities", "world": "trigger"},
    "t3": {"name": "Macroeconomic & Global Markets", "world": "trigger"},
    "t4": {"name": "Technological & Physical Infrastructure", "world": "trigger"},
    "t5": {"name": "Social, Demographic & Cultural Forces", "world": "trigger"},
    "i1": {"name": "Food & Nutrition", "world": "impact"},
    "i2": {"name": "Housing & Utilities", "world": "impact"},
    "i3": {"name": "Transport & Mobility", "world": "impact"},
    "i4": {"name": "Livelihood & Employment", "world": "impact"},
    "i5": {"name": "Personal Finance & Wealth", "world": "impact"},
    "i6": {"name": "Health & Physiology", "world": "impact"},
    "i7": {"name": "Education & Human Capital", "world": "impact"},
    "i8": {"name": "Safety & Security", "world": "impact"},
    "i9": {"name": "Local Environmental Quality", "world": "impact"},
    "i10": {"name": "Digital Life & Connectivity", "world": "impact"},
    "i11": {"name": "Leisure, Culture & Community", "world": "impact"},
}

CATEGORY_COLORS = {
    "t1": "#4FC3F7",
    "t2": "#7986CB",
    "t3": "#4DD0E1",
    "t4": "#90A4AE",
    "t5": "#80CBC4",
    "i1": "#66BB6A",
    "i2": "#EC407A",
    "i3": "#26C6DA",
    "i4": "#AB47BC",
    "i5": "#42A5F5",
    "i6": "#EF5350",
    "i7": "#FFA726",
    "i8": "#FF7043",
    "i9": "#26A69A",
    "i10": "#7E57C2",
    "i11": "#78909C",
}

# Top 20 trigger nodes by causal out-degree (pre-selected)
PPR_CACHE_TRIGGERS = [
    "municipal_corporations",
    "southwest_monsoon",
    "cyclonic_storm_systems",
    "autumn_festive_season",
    "state_governments",
    "rbi",
    "urban_population_density",
    "national_unemployment_rate",
    "upi_platform",
    "ambient_aqi",
    "ministry_of_finance",
    "national_power_grid",
    "outdoor_heat",
    "urban_unemployment_rate",
    "brent_crude",
    "food_delivery_services",
    "gst_council",
    "highway_network",
    "minimum_wage",
    "retail_diesel",
]


def get_parent(G, node_id: str) -> str | None:
    """Find CONTAINS parent of a node."""
    for pred in G.predecessors(node_id):
        if G[pred][node_id].get("type") == "CONTAINS":
            return pred
    return None


def build_export(G) -> dict:
    """Build the full export dict."""
    # -- categories --
    categories = {}
    for cat_id, meta in CATEGORIES.items():
        categories[cat_id] = {
            "name": meta["name"],
            "world": meta["world"],
            "color": CATEGORY_COLORS[cat_id],
        }

    # -- nodes --
    nodes = []
    for nid, data in G.nodes(data=True):
        causal_out = sum(
            1 for _, _, d in G.out_edges(nid, data=True)
            if d.get("type") in CAUSAL_TYPES
        )
        nodes.append({
            "id": nid,
            "aliases": data.get("aliases", []),
            "category": data.get("category", ""),
            "level": data.get("level"),
            "is_category": data.get("is_category", False),
            "port": data.get("port", False),
            "portal": data.get("portal", False),
            "parent": get_parent(G, nid),
            "degree": {
                "in": G.in_degree(nid),
                "out": G.out_degree(nid),
                "causal_out": causal_out,
            },
        })

    # -- edges --
    edges = []
    for u, v, data in G.edges(data=True):
        edge_type = data.get("type", "AFFECTS")
        is_structural = edge_type in ("CONTAINS", "IS_A")
        edges.append({
            "id": f"{u}->{v}",
            "source": u,
            "target": v,
            "type": edge_type,
            "weight": data.get("weight", 0.5),
            "polarity": data.get("polarity", 0),
            "delay": data.get("delay", "SHORT_TERM"),
            "description": data.get("description", ""),
            "is_structural": is_structural,
        })

    # -- hierarchy (L1 → direct L2 children) --
    hierarchy = {}
    for cat_id in CATEGORIES:
        if cat_id in G:
            children = [
                v for _, v, d in G.out_edges(cat_id, data=True)
                if d.get("type") == "CONTAINS"
            ]
            hierarchy[cat_id] = sorted(children)

    # -- ppr_cache --
    logger.info("Building PPR cache for %d triggers...", len(PPR_CACHE_TRIGGERS))
    engine = CausalMarkovEngine(G)
    ppr_cache = {}

    for i, trigger in enumerate(PPR_CACHE_TRIGGERS, 1):
        if trigger not in G:
            logger.warning("Skipping PPR for '%s' — not in graph", trigger)
            continue
        print(f"  PPR [{i}/{len(PPR_CACHE_TRIGGERS)}] {trigger}...")
        results = engine.evaluate_impact(
            trigger,
            event_direction=1,
            restart_prob=0.20,
            prob_threshold=0.005,
        )
        # Top 50 by probability
        top = results[:50]
        ppr_cache[trigger] = [
            {
                "node": r["node"],
                "probability": round(r["probability"], 6),
                "magnitude": round(r["magnitude"], 6),
                "path": r["path"],
            }
            for r in top
        ]

    # -- stats --
    causal_edge_count = sum(
        1 for _, _, d in G.edges(data=True)
        if d.get("type") in CAUSAL_TYPES
    )
    stats = {
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "causal_edge_count": causal_edge_count,
        "category_count": len(CATEGORIES),
    }

    return {
        "categories": categories,
        "nodes": nodes,
        "edges": edges,
        "hierarchy": hierarchy,
        "ppr_cache": ppr_cache,
        "stats": stats,
    }


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    merger = TaxonomyMerger()
    G = merger.merge()
    apply_defaults(G)

    print(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    data = build_export(G)

    out = Path("viz/data/graph.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nExported {len(data['nodes'])} nodes, {len(data['edges'])} edges")
    print(f"PPR cache: {len(data['ppr_cache'])} triggers")
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
