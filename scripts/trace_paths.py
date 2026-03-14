import yaml, networkx as nx

with open("/app/data/merged_graph.yaml") as f:
    data = yaml.safe_load(f)

G = nx.DiGraph()
for n in data["nodes"]:
    nid = n["id"]
    attrs = {k: v for k, v in n.items() if k != "id"}
    G.add_node(nid, **attrs)
for e in data["edges"]:
    attrs = {k: v for k, v in e.items() if k not in ("from", "to")}
    G.add_edge(e["from"], e["to"], **attrs)

print("=== UNION BUDGET TREE ===")
def print_tree(node, depth=0):
    for child in G.successors(node):
        etype = G.edges[node, child].get("type", "")
        if etype == "CONTAINS":
            print("  " * depth + child)
            print_tree(child, depth + 1)
print_tree("union_budget_framework")

print("\n=== NON-CONTAINS EDGES FROM budget subtree ===")
def get_descendants(node):
    desc = set()
    for child in G.successors(node):
        if G.edges[node, child].get("type") == "CONTAINS":
            desc.add(child)
            desc.update(get_descendants(child))
    return desc

budget_nodes = {"union_budget_framework"} | get_descendants("union_budget_framework")
for n in sorted(budget_nodes):
    for succ in G.successors(n):
        etype = G.edges[n, succ].get("type", "")
        if etype != "CONTAINS":
            cat = G.nodes.get(succ, {}).get("category", "?")
            print(f"  {n} --{etype}--> {succ} [{cat}]")

print("\n=== ALL EDGES TO lpg_cylinder ===")
for pred in G.predecessors("lpg_cylinder"):
    etype = G.edges[pred, "lpg_cylinder"].get("type", "")
    cat = G.nodes.get(pred, {}).get("category", "?")
    print(f"  {pred} --{etype}--> lpg_cylinder [{cat}]")

print("\n=== PATHS: budget -> lpg_cylinder (max 6 hops) ===")
paths = list(nx.all_simple_paths(G, "union_budget_framework", "lpg_cylinder", cutoff=6))
for p in paths[:10]:
    steps = []
    for i in range(len(p) - 1):
        etype = G.edges[p[i], p[i+1]].get("type", "")
        steps.append(f"{p[i]} --{etype}--> {p[i+1]}")
    print("  " + "\n    ".join(steps))
    print()
if not paths:
    print("  NO PATH FOUND")
else:
    print(f"  Total paths: {len(paths)}")
