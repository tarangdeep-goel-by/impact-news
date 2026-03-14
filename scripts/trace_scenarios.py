"""Trace broken/partial scenarios through the merged graph."""
import yaml
import networkx as nx

with open("data/merged_graph.yaml") as f:
    data = yaml.safe_load(f)

G = nx.DiGraph()
for n in data["nodes"]:
    nid = n["id"]
    attrs = {k: v for k, v in n.items() if k != "id"}
    G.add_node(nid, **attrs)
for e in data["edges"]:
    attrs = {k: v for k, v in e.items() if k not in ("from", "to")}
    G.add_edge(e["from"], e["to"], **attrs)

scenarios = [
    ("gst_council", "biscuits_and_snacks", "GST -> snacks"),
    ("us_government", "factory_worker_jobs", "US tariffs -> factory jobs"),
    ("it_sector_jobs", "credit_card_dues", "IT layoffs -> credit cards"),
    ("smartphone_device", "upi_transaction_success", "smartphone -> UPI"),
    ("ambient_aqi", "government_schools", "AQI -> school closures"),
    ("outdoor_heat", "hospital_beds", "heatwave -> hospitals"),
    ("nifty_50", "nps_portfolio", "nifty -> NPS"),
    ("union_budget_framework", "lpg_cylinder", "budget -> LPG"),
    ("russian_government", "global_food_grain_supply", "Russia -> grain"),
    ("cyclonic_storm_systems", "marine_fish_stocks", "cyclone -> fish"),
    ("farm_labor_wages", "rural_unemployment_rate", "farm wages -> unemployment"),
    ("himalayan_river_systems", "retail_rice", "rivers -> rice"),
    ("aadhaar_authentication", "senior_citizen_savings_scheme", "aadhaar -> SCSS"),
    ("mgnrega_wages", "kirana_store_income", "MGNREGA -> kirana"),
    ("india_trade_deficit", "small_factory_owner_income", "trade deficit -> MSME"),
    ("aggregate_consumer_confidence", "kirana_store_income", "consumer confidence -> kirana"),
    ("retail_tomato", "savings_account_balance", "tomato -> savings"),
]

for src, dst, label in scenarios:
    print(f"=== {label}: {src} -> {dst} ===")

    if src not in G:
        print(f"  SOURCE MISSING: {src}")
        print()
        continue
    if dst not in G:
        print(f"  DEST MISSING: {dst}")
        print()
        continue

    # Tree children
    children = [c for c in G.successors(src) if G.edges[src, c].get("type") == "CONTAINS"]
    non_contains = [(s, G.edges[src, s].get("type", "")) for s in G.successors(src) if G.edges[src, s].get("type") != "CONTAINS"]
    print(f"  {src}: {len(children)} tree children, {len(non_contains)} lateral/bridge edges")

    # Find paths
    paths = list(nx.all_simple_paths(G, src, dst, cutoff=6))
    if paths:
        print(f"  PATHS FOUND: {len(paths)}")
        for p in paths[:3]:
            steps = []
            for i in range(len(p) - 1):
                etype = G.edges[p[i], p[i + 1]].get("type", "")
                steps.append(f"{p[i]} --{etype}--> {p[i+1]}")
            print("    " + "\n    ".join(steps))
            print()
    else:
        print("  NO PATH")
        print()
