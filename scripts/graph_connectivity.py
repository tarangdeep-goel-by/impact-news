"""Graph connectivity analysis — edge types, bridge levels, T→I coverage matrix."""

import yaml
import glob
import networkx as nx
from collections import defaultdict


def build_graph():
    G = nx.DiGraph()
    for yf in glob.glob('taxonomy/[TI]*.yaml'):
        with open(yf) as f:
            d = yaml.safe_load(f)
        for n in d.get('nodes', []):
            attrs = {k: v for k, v in n.items() if k != 'id'}
            G.add_node(n['id'], **attrs)
        for e in d.get('edges', []):
            attrs = {k: v for k, v in e.items() if k not in ('from', 'to')}
            G.add_edge(e['from'], e['to'], **attrs)

    with open('taxonomy/bridge_edges.yaml') as f:
        bd = yaml.safe_load(f)
    for e in bd.get('edges', []):
        attrs = {k: v for k, v in e.items() if k not in ('from', 'to')}
        G.add_edge(e['from'], e['to'], **attrs)

    for pf in glob.glob('taxonomy/patches/*.yaml'):
        with open(pf) as f:
            pd = yaml.safe_load(f)
        if isinstance(pd, dict):
            for e in pd.get('edges', []):
                if 'from' in e and 'to' in e:
                    attrs = {k: v for k, v in e.items() if k not in ('from', 'to')}
                    G.add_edge(e['from'], e['to'], **attrs)
    return G


def main():
    G = build_graph()
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges\n")

    # Edge type breakdown
    type_counts = defaultdict(int)
    for _, _, d in G.edges(data=True):
        type_counts[d.get('type', '?')] += 1
    print("=== Edge types ===")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t:20s} {c:5d}")

    # Cross-world bridge analysis
    print("\n=== Cross-world bridges (T→I, excluding CONTAINS/IS_A) ===")
    bridge_types = defaultdict(int)
    bridge_levels = defaultdict(int)
    t_l1_to_i_l1 = defaultdict(int)
    for u, v, d in G.edges(data=True):
        etype = d.get('type', '')
        if etype in ('CONTAINS', 'IS_A'):
            continue
        u_cat = G.nodes.get(u, {}).get('category', '')
        v_cat = G.nodes.get(v, {}).get('category', '')
        if u_cat.startswith('T') and v_cat.startswith('I'):
            bridge_types[etype] += 1
            ul = G.nodes.get(u, {}).get('level', '?')
            vl = G.nodes.get(v, {}).get('level', '?')
            bridge_levels[f"L{ul}->L{vl}"] += 1
            t_l1_to_i_l1[f"{u_cat}->{v_cat}"] += 1

    print(f"  Total T->I bridges: {sum(bridge_types.values())}")
    print(f"\n  By type:")
    for t, c in sorted(bridge_types.items(), key=lambda x: -x[1]):
        print(f"    {t:20s} {c:4d}")
    print(f"\n  By level:")
    for t, c in sorted(bridge_levels.items(), key=lambda x: -x[1]):
        print(f"    {t:10s} {c:4d}")

    # Same-world causal edges
    print("\n=== Same-world causal edges ===")
    tt_count = 0
    ii_count = 0
    for u, v, d in G.edges(data=True):
        etype = d.get('type', '')
        if etype in ('CONTAINS', 'IS_A'):
            continue
        u_cat = G.nodes.get(u, {}).get('category', '')
        v_cat = G.nodes.get(v, {}).get('category', '')
        if u_cat.startswith('T') and v_cat.startswith('T'):
            tt_count += 1
        elif u_cat.startswith('I') and v_cat.startswith('I'):
            ii_count += 1
    print(f"  T->T (trigger laterals): {tt_count}")
    print(f"  I->I (impact laterals):  {ii_count}")

    # T-L1 → I-L1 coverage matrix
    t_cats = sorted(set(c.split('->')[0] for c in t_l1_to_i_l1))
    i_cats = sorted(set(c.split('->')[1] for c in t_l1_to_i_l1))
    # Ensure all I categories show
    for n, nd in G.nodes(data=True):
        cat = nd.get('category', '')
        if cat.startswith('I') and nd.get('level') == 1 and cat not in i_cats:
            i_cats.append(cat)
    i_cats = sorted(set(i_cats))

    print(f"\n=== T-L1 -> I-L1 bridge coverage ===")
    hdr = f"{'':6s}"
    for ic in i_cats:
        hdr += f" {ic:>4s}"
    print(hdr)
    print("-" * (6 + 5 * len(i_cats)))
    for tc in t_cats:
        row = f"{tc:6s}"
        for ic in i_cats:
            count = t_l1_to_i_l1.get(f"{tc}->{ic}", 0)
            row += f" {count:4d}" if count > 0 else "    ."
        print(row)


if __name__ == '__main__':
    main()
