"""Regenerate eval chunks from the patched merged graph.

Usage:
    python -m audit.generate_chunks
"""

import json
from pathlib import Path

from graph.merge import TaxonomyMerger

EVAL_DIR = Path("taxonomy/eval_chunks")

# Map categories to eval domains
CATEGORY_TO_DOMAIN = {
    # Energy
    "energy": "energy",
    "energy_policy": "energy",
    "fossil_fuels": "energy",
    "renewable_energy": "energy",
    "energy_distribution": "energy",
    "electricity": "energy",
    "energy_markets": "energy",
    "coal": "energy",
    "oil_and_gas": "energy",
    "nuclear": "energy",
    # Financial
    "financial": "financial",
    "financial_system": "financial",
    "banking": "financial",
    "insurance": "financial",
    "capital_markets": "financial",
    "personal_finance": "financial",
    "taxation": "financial",
    "monetary_policy": "financial",
    "fintech": "financial",
    "credit": "financial",
    "investments": "financial",
    # Food & Agriculture
    "food": "food_agriculture",
    "agriculture": "food_agriculture",
    "agriculture_and_farming": "food_agriculture",
    "food_and_agriculture": "food_agriculture",
    "crops": "food_agriculture",
    "livestock": "food_agriculture",
    "food_supply": "food_agriculture",
    "food_processing": "food_agriculture",
    "irrigation": "food_agriculture",
    "fisheries": "food_agriculture",
    # Macro & Geopolitics
    "macro": "macro_geopolitics",
    "geopolitics": "macro_geopolitics",
    "macro_and_geopolitics": "macro_geopolitics",
    "international_trade": "macro_geopolitics",
    "global_economy": "macro_geopolitics",
    "foreign_policy": "macro_geopolitics",
    # Employment
    "employment": "employment",
    "employment_and_income": "employment",
    "jobs": "employment",
    "labor": "employment",
    "startups": "employment",
    "it_sector": "employment",
    "gig_economy": "employment",
    "skills": "employment",
    # Governance
    "governance": "governance",
    "governance_and_regulation": "governance",
    "local_governance": "governance",
    "regulation": "governance",
    "policy": "governance",
    "elections": "governance",
    "judiciary": "governance",
    "disaster_management": "governance",
    # Infrastructure
    "infrastructure": "infrastructure",
    "transport": "infrastructure",
    "transport_and_mobility": "infrastructure",
    "utilities": "infrastructure",
    "water_infrastructure": "infrastructure",
    "water_systems": "infrastructure",
    "telecom": "infrastructure",
    "urban_planning": "infrastructure",
    "logistics": "infrastructure",
    # Consumer Life
    "consumer": "consumer_life",
    "consumer_life": "consumer_life",
    "housing": "consumer_life",
    "housing_and_shelter": "consumer_life",
    "health": "consumer_life",
    "healthcare": "consumer_life",
    "education": "consumer_life",
    "recreation": "consumer_life",
    "recreation_and_culture": "consumer_life",
    "environment": "consumer_life",
    "environment_and_climate": "consumer_life",
    "climate": "consumer_life",
    "safety": "consumer_life",
    "digital_life": "consumer_life",
    "clothing_and_personal_care": "consumer_life",
    "communication_and_information": "infrastructure",
    "cross_domain": "macro_geopolitics",
    "demographics_and_social": "macro_geopolitics",
    "education_and_learning": "consumer_life",
    "energy_and_fuel": "energy",
    "food_and_nutrition": "food_agriculture",
    "food_policy": "food_agriculture",
    "global_macro_and_geopolitics": "macro_geopolitics",
    "health_and_healthcare": "consumer_life",
    "industrial_metals_and_materials": "energy",
    "law_order": "governance",
    "municipal_governance": "governance",
    "property_land": "consumer_life",
    "safety_and_security": "governance",
    "state_policy": "governance",
    "technology": "employment",
    "technology_and_innovation": "employment",
    "user": "consumer_life",
    # v4 taxonomy L1 category codes
    "i1": "food_agriculture",
    "i2": "consumer_life",       # Housing & Shelter
    "i3": "infrastructure",      # Transport & Mobility
    "i4": "employment",          # Livelihood & Employment
    "i5": "financial",           # Personal Finance
    "i6": "consumer_life",       # Health & Healthcare
    "i7": "consumer_life",       # Education & Learning
    "i8": "governance",          # Safety & Security
    "i9": "consumer_life",       # Environment & Climate
    "i10": "consumer_life",      # Digital Life & Connectivity
    "i11": "consumer_life",      # Recreation & Culture
    "t1": "consumer_life",       # Natural & Environmental Systems
    "t2": "governance",          # Institutional & Sovereign Entities
    "t3": "macro_geopolitics",   # Macro-Economic Forces
    "t4": "infrastructure",      # Physical Infrastructure
    "t5": "macro_geopolitics",   # Social, Demographic & Cultural Forces
}

DEFAULT_DOMAIN = "consumer_life"


def main():
    merger = TaxonomyMerger()
    G = merger.merge(apply_patches=True)
    print(f"Patched graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Assign nodes to domains
    domain_nodes: dict[str, list] = {d: [] for d in set(CATEGORY_TO_DOMAIN.values())}
    unmapped_cats = set()

    for nid, attrs in G.nodes(data=True):
        cat = attrs.get("category", "").lower().strip()
        domain = CATEGORY_TO_DOMAIN.get(cat)
        if not domain:
            unmapped_cats.add(cat)
            domain = DEFAULT_DOMAIN
        domain_nodes[domain].append({
            "id": nid,
            "aliases": attrs.get("aliases", []),
            "category": attrs.get("category", ""),
        })

    if unmapped_cats:
        print(f"Unmapped categories (→ {DEFAULT_DOMAIN}): {sorted(unmapped_cats)}")

    # Build domain chunks with edges
    EVAL_DIR.mkdir(exist_ok=True)

    for domain, nodes in sorted(domain_nodes.items()):
        node_ids = {n["id"] for n in nodes}

        # Internal edges: both endpoints in this domain
        internal_edges = []
        # Cross-domain edges: one endpoint in this domain
        cross_edges = []

        for src, dst, attrs in G.edges(data=True):
            src_in = src in node_ids
            dst_in = dst in node_ids

            edge_data = {
                "from": src,
                "to": dst,
                "type": attrs.get("type", ""),
                "description": attrs.get("description", ""),
            }

            if src_in and dst_in:
                internal_edges.append(edge_data)
            elif src_in or dst_in:
                # Find cross category
                cross_node = dst if src_in else src
                cross_cat = G.nodes[cross_node].get("category", "") if G.has_node(cross_node) else ""
                cross_domain = CATEGORY_TO_DOMAIN.get(cross_cat.lower().strip(), "unknown")
                edge_data["cross"] = cross_domain
                cross_edges.append(edge_data)

        all_edges = internal_edges + cross_edges

        chunk = {
            "domain": domain,
            "node_count": len(nodes),
            "edge_count": len(all_edges),
            "internal_edge_count": len(internal_edges),
            "cross_domain_edge_count": len(cross_edges),
            "nodes": sorted(nodes, key=lambda n: n["id"]),
            "edges": all_edges,
        }

        out_path = EVAL_DIR / f"{domain}.json"
        out_path.write_text(json.dumps(chunk, indent=2, ensure_ascii=False))
        print(f"  {domain}: {len(nodes)} nodes, {len(all_edges)} edges ({len(cross_edges)} cross-domain)")


if __name__ == "__main__":
    main()
