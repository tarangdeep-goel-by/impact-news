"""Bridge coverage analysis — T-L2 outgoing and I-L2 incoming bridge counts."""

import yaml
import glob
import networkx as nx


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

    # T-L2 bridge coverage
    print("=== T-L2 bridge coverage ===")
    t_l2s = [(n, G.nodes[n]) for n in G.nodes()
             if G.nodes[n].get('category', '').startswith('T') and G.nodes[n].get('level') == 2]
    for nid, nd in sorted(t_l2s, key=lambda x: x[0]):
        bridge_count = 0
        for _, v, d in G.out_edges(nid, data=True):
            if d.get('type') not in ('CONTAINS', 'IS_A') and G.nodes.get(v, {}).get('category', '').startswith('I'):
                bridge_count += 1
        l3_bridges = 0
        for _, child, cd in G.out_edges(nid, data=True):
            if cd.get('type') == 'CONTAINS':
                for _, v2, d2 in G.out_edges(child, data=True):
                    if d2.get('type') not in ('CONTAINS', 'IS_A') and G.nodes.get(v2, {}).get('category', '').startswith('I'):
                        l3_bridges += 1
        cat = nd.get('category', '')
        print(f"  {nid:45s} ({cat}) L2-bridges={bridge_count:2d}  L3-child-bridges={l3_bridges:2d}")

    # I-L2 bridge reception
    print("\n=== I-L2 bridge reception ===")
    i_l2s = [(n, G.nodes[n]) for n in G.nodes()
             if G.nodes[n].get('category', '').startswith('I') and G.nodes[n].get('level') == 2]
    no_bridges = []
    for nid, nd in sorted(i_l2s, key=lambda x: x[0]):
        incoming = 0
        for u, _, d in G.in_edges(nid, data=True):
            if d.get('type') not in ('CONTAINS', 'IS_A') and G.nodes.get(u, {}).get('category', '').startswith('T'):
                incoming += 1
        l3_incoming = 0
        for _, child, cd in G.out_edges(nid, data=True):
            if cd.get('type') == 'CONTAINS':
                for u2, _, d2 in G.in_edges(child, data=True):
                    if d2.get('type') not in ('CONTAINS', 'IS_A') and G.nodes.get(u2, {}).get('category', '').startswith('T'):
                        l3_incoming += 1
        cat = nd.get('category', '')
        status = "OK" if (incoming + l3_incoming) > 0 else "NO BRIDGES"
        if status == "NO BRIDGES":
            no_bridges.append(nid)
        print(f"  {nid:45s} ({cat:3s}) L2-in={incoming:2d}  L3-in={l3_incoming:2d}  [{status}]")

    if no_bridges:
        print(f"\n=== {len(no_bridges)} I-L2s with NO bridges ===")
        for nid in no_bridges:
            print(f"  - {nid}")


if __name__ == '__main__':
    main()
