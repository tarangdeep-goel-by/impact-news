"""Visualize the full impact taxonomy — L1 domains → L2 groups → leaf nodes.

Layout: YOU at center, 21 L1 domains in the inner ring, L2 groups in the middle ring,
leaf nodes in the outer ring. Also shows graph edges (PRODUCES, AFFECTS, etc.) between
nodes across domains.
"""

import json
import math
from collections import defaultdict

from pyvis.network import Network

from graph.graph import ImpactGraph

# --- Category → color mapping ---
DOMAIN_COLORS = {
    "food_and_nutrition": "#4CAF50",
    "energy_and_fuel": "#FF9800",
    "financial_system": "#2196F3",
    "employment_and_income": "#9C27B0",
    "governance_and_regulation": "#795548",
    "local_governance": "#8D6E63",
    "transport_and_mobility": "#00BCD4",
    "water_infrastructure": "#0097A7",
    "housing_and_shelter": "#E91E63",
    "health_and_healthcare": "#F44336",
    "education_and_learning": "#FF5722",
    "technology_and_innovation": "#673AB7",
    "agriculture_and_farming": "#8BC34A",
    "environment_and_climate": "#009688",
    "communication_and_information": "#3F51B5",
    "global_macro_and_geopolitics": "#607D8B",
    "industrial_metals_and_materials": "#78909C",
    "demographics_and_social": "#AB47BC",
    "safety_and_security": "#EF5350",
    "recreation_and_culture": "#26A69A",
    "clothing_and_personal_care": "#EC407A",
}

NICE_NAMES = {
    "food_and_nutrition": "Food & Nutrition",
    "energy_and_fuel": "Energy & Fuel",
    "financial_system": "Financial System",
    "employment_and_income": "Employment & Income",
    "governance_and_regulation": "Governance",
    "local_governance": "Local Governance",
    "transport_and_mobility": "Transport",
    "water_infrastructure": "Water",
    "housing_and_shelter": "Housing & Shelter",
    "health_and_healthcare": "Health & Healthcare",
    "education_and_learning": "Education",
    "technology_and_innovation": "Technology",
    "agriculture_and_farming": "Agriculture",
    "environment_and_climate": "Environment & Climate",
    "communication_and_information": "Communication",
    "global_macro_and_geopolitics": "Global & Geopolitics",
    "industrial_metals_and_materials": "Industrial Materials",
    "demographics_and_social": "Demographics",
    "safety_and_security": "Safety & Security",
    "recreation_and_culture": "Recreation & Culture",
    "clothing_and_personal_care": "Clothing & Personal Care",
}


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def darken(hex_color: str, factor: float = 0.7) -> str:
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    r, g, b = int(r * factor), int(g * factor), int(b * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def build_visualization():
    graph = ImpactGraph("data/merged_graph.yaml")
    graph.load()

    # --- Discover the tree hierarchy ---
    # L1: root category nodes (is_category=True, no parents via CONTAINS)
    all_nodes = dict(graph.g.nodes(data=True))
    l1_roots = []
    for nid, attrs in all_nodes.items():
        if attrs.get("is_category") and graph.g.in_degree(nid) == 0:
            l1_roots.append(nid)
    l1_roots.sort()

    # Build hierarchy: L1 → L2 (categories) → leaves
    hierarchy = {}  # l1 → {l2 → [leaf_ids]}
    node_to_l1 = {}  # node_id → l1 domain
    node_to_l2 = {}  # node_id → l2 group
    node_layer = {}  # node_id → layer (1=L1, 2=L2, 3=leaf)

    for l1 in l1_roots:
        node_layer[l1] = 1
        node_to_l1[l1] = l1
        hierarchy[l1] = {}
        for l2 in graph.g.successors(l1):
            l2_attrs = all_nodes.get(l2, {})
            node_layer[l2] = 2
            node_to_l1[l2] = l1
            node_to_l2[l2] = l2
            leaves = []
            for child in graph.g.successors(l2):
                child_attrs = all_nodes.get(child, {})
                if child_attrs.get("is_category"):
                    # L3 category → collect its children as leaves
                    node_layer[child] = 2  # treat as L2-equivalent
                    node_to_l1[child] = l1
                    node_to_l2[child] = l2
                    for grandchild in graph.g.successors(child):
                        leaves.append(grandchild)
                        node_layer[grandchild] = 3
                        node_to_l1[grandchild] = l1
                        node_to_l2[grandchild] = l2
                else:
                    leaves.append(child)
                    node_layer[child] = 3
                    node_to_l1[child] = l1
                    node_to_l2[child] = l2
            hierarchy[l1][l2] = leaves

    # Also collect non-tree nodes (from flat graph files, not in tree hierarchy)
    # Map them to domains by category
    CATEGORY_TO_DOMAIN = {}
    for l1 in l1_roots:
        short = l1.replace("_and_", "_").replace("_", " ")
        CATEGORY_TO_DOMAIN[l1] = l1
    # Manual category → domain mappings for flat file categories
    CAT_MAP = {
        "food": "food_and_nutrition", "food_policy": "food_and_nutrition",
        "energy": "energy_and_fuel", "energy_policy": "energy_and_fuel",
        "financial": "financial_system", "monetary_policy": "financial_system",
        "banking": "financial_system", "macro": "global_macro_and_geopolitics",
        "employment": "employment_and_income",
        "transport": "transport_and_mobility",
        "water_systems": "water_infrastructure",
        "municipal_governance": "local_governance",
        "state_policy": "local_governance",
        "law_order": "safety_and_security",
        "property_land": "housing_and_shelter",
        "utilities": "housing_and_shelter",
        "environment": "environment_and_climate",
        "climate": "environment_and_climate",
        "healthcare": "health_and_healthcare",
        "education": "education_and_learning",
        "technology": "technology_and_innovation",
        "infrastructure": "transport_and_mobility",
        "geopolitics": "global_macro_and_geopolitics",
        "cross_domain": "governance_and_regulation",
        "insurance": "financial_system",
        "tax": "financial_system",
        "regulation": "governance_and_regulation",
        "telecom": "communication_and_information",
    }

    flat_nodes_by_domain = defaultdict(list)
    for nid, attrs in all_nodes.items():
        if nid not in node_layer:
            cat = attrs.get("category", "")
            domain = CAT_MAP.get(cat)
            if domain:
                flat_nodes_by_domain[domain].append(nid)
                node_to_l1[nid] = domain
                node_layer[nid] = 3  # treat as leaf level

    # --- Count totals per domain for sidebar ---
    domain_stats = {}
    for l1 in l1_roots:
        l2_count = len(hierarchy[l1])
        leaf_count = sum(len(leaves) for leaves in hierarchy[l1].values())
        flat_count = len(flat_nodes_by_domain.get(l1, []))
        domain_stats[l1] = {
            "l2": l2_count,
            "leaves": leaf_count,
            "flat": flat_count,
            "total": l2_count + leaf_count + flat_count,
        }

    # --- Build pyvis network ---
    net = Network(
        height="100vh", width="100%", bgcolor="#0a0a0a", font_color="#ffffff",
        directed=True, select_menu=False, filter_menu=False,
    )

    net.set_options(json.dumps({
        "physics": {
            "enabled": True,
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
                "gravitationalConstant": -200,
                "centralGravity": 0.008,
                "springLength": 180,
                "springConstant": 0.03,
                "damping": 0.9,
                "avoidOverlap": 0.5,
            },
            "stabilization": {"enabled": True, "iterations": 400, "fit": True},
            "maxVelocity": 25,
            "minVelocity": 0.75,
        },
        "nodes": {
            "font": {"face": "Inter, system-ui, sans-serif", "strokeWidth": 3, "strokeColor": "#0a0a0a"},
            "borderWidth": 2, "borderWidthSelected": 4,
        },
        "edges": {
            "font": {"size": 8, "face": "Inter, system-ui, sans-serif", "color": "#555",
                     "strokeWidth": 0, "align": "middle"},
            "smooth": {"type": "continuous", "roundness": 0.12},
            "arrows": {"to": {"enabled": True, "scaleFactor": 0.35}},
        },
        "interaction": {"hover": True, "tooltipDelay": 100, "zoomView": True, "dragView": True,
                        "navigationButtons": True, "multiselect": True},
    }))

    # --- Add YOU node ---
    net.add_node("__USER__", label="YOU", size=70,
                 color={"background": "#FFD700", "border": "#FFA000",
                        "highlight": {"background": "#FFEB3B", "border": "#FF8F00"}},
                 font={"size": 24, "color": "#000000", "bold": True},
                 shape="dot", mass=8, level=0,
                 title="Everything in your life that news can affect")

    added = {"__USER__"}

    # --- Add L1 domain nodes (inner ring) ---
    for l1 in l1_roots:
        color = DOMAIN_COLORS.get(l1, "#9E9E9E")
        nice = NICE_NAMES.get(l1, l1.replace("_", " ").title())
        stats = domain_stats[l1]
        net.add_node(l1, label=nice, size=35,
                     color={"background": color, "border": darken(color),
                            "highlight": {"background": color, "border": "#fff"}},
                     font={"size": 13, "color": "#fff", "bold": True},
                     shape="dot", mass=4, level=1,
                     title=f"<b>{nice}</b><br>{stats['l2']} groups · {stats['leaves'] + stats['flat']} nodes")
        added.add(l1)
        # Edge: YOU → L1
        net.add_edge("__USER__", l1, width=1.5, color=rgba("#FFD700", 0.3),
                     smooth={"type": "continuous"})

    # --- Add L2 group nodes (middle ring) ---
    for l1 in l1_roots:
        color = DOMAIN_COLORS.get(l1, "#9E9E9E")
        for l2, leaves in hierarchy[l1].items():
            nice_l2 = l2.replace("_", " ").title()
            if len(nice_l2) > 20:
                nice_l2 = nice_l2[:18] + "…"
            net.add_node(l2, label=nice_l2, size=20,
                         color={"background": rgba(color, 0.8), "border": rgba(color, 0.9),
                                "highlight": {"background": color, "border": "#fff"}},
                         font={"size": 10, "color": rgba("#fff", 0.85)},
                         shape="dot", mass=2, level=2,
                         title=f"<b>{l2}</b><br>Domain: {NICE_NAMES.get(l1, l1)}<br>{len(leaves)} nodes")
            added.add(l2)
            # L1 → L2 edge
            net.add_edge(l1, l2, width=1.0, color=rgba(color, 0.25))

    # --- Add leaf nodes (outer ring) ---
    for l1 in l1_roots:
        color = DOMAIN_COLORS.get(l1, "#9E9E9E")
        for l2, leaves in hierarchy[l1].items():
            for leaf_id in leaves:
                if leaf_id in added:
                    continue
                attrs = all_nodes.get(leaf_id, {})
                aliases = attrs.get("aliases", [])
                alias_str = ", ".join(aliases[:3]) if aliases else "—"
                label = leaf_id.replace("_", " ").title()
                if len(label) > 20:
                    label = label[:18] + "…"
                net.add_node(leaf_id, label="", size=8,
                             color={"background": rgba(color, 0.4), "border": rgba(color, 0.5),
                                    "highlight": {"background": color, "border": "#fff"}},
                             font={"size": 8, "color": rgba("#fff", 0.5)},
                             shape="dot", mass=0.5, level=3,
                             title=f"<b>{leaf_id}</b><br>Aliases: {alias_str}<br>Group: {l2}")
                added.add(leaf_id)
                # L2 → leaf edge
                net.add_edge(l2, leaf_id, width=0.5, color=rgba(color, 0.12))

        # Flat nodes (from domain graph files, not in tree)
        for flat_id in flat_nodes_by_domain.get(l1, []):
            if flat_id in added:
                continue
            attrs = all_nodes.get(flat_id, {})
            aliases = attrs.get("aliases", [])
            alias_str = ", ".join(aliases[:3]) if aliases else "—"
            cat = attrs.get("category", "")
            net.add_node(flat_id, label="", size=8,
                         color={"background": rgba(color, 0.4), "border": rgba(color, 0.5),
                                "highlight": {"background": color, "border": "#fff"}},
                         font={"size": 8, "color": rgba("#fff", 0.5)},
                         shape="dot", mass=0.5, level=3,
                         title=f"<b>{flat_id}</b><br>Category: {cat}<br>Aliases: {alias_str}")
            added.add(flat_id)
            # Connect to L1 directly (no L2 parent)
            net.add_edge(l1, flat_id, width=0.3, color=rgba(color, 0.08))

    # --- Add cross-domain graph edges (PRODUCES, AFFECTS, etc.) ---
    # Only edges where both endpoints are in our visualization
    cross_edge_count = 0
    for u, v, data in graph.g.edges(data=True):
        if u not in added or v not in added:
            continue
        edge_type = data.get("type", "")
        if edge_type == "CONTAINS":
            continue  # Skip hierarchy edges, already added
        description = data.get("description", "")

        # Only show cross-domain edges or important within-domain edges
        u_l1 = node_to_l1.get(u)
        v_l1 = node_to_l1.get(v)

        u_layer = node_layer.get(u, 3)
        v_layer = node_layer.get(v, 3)

        # Show edges where at least one side is L2 or higher, or cross-domain
        if u_l1 != v_l1 or min(u_layer, v_layer) <= 2:
            alpha = 0.35 if u_l1 != v_l1 else 0.15
            width = 1.0 if u_l1 != v_l1 else 0.5
            edge_label = edge_type.lower().replace("_", " ") if u_l1 != v_l1 else ""

            net.add_edge(u, v, label=edge_label, width=width,
                         color=rgba("#FFD700" if u_l1 != v_l1 else "#888", alpha),
                         title=f"{edge_type}: {description}" if description else edge_type)
            cross_edge_count += 1

    # --- Save and inject sidebar ---
    output = "data/impact_graph.html"
    net.save_graph(output)

    with open(output, "r") as f:
        html = f.read()

    # Build sidebar data: per-domain, per-L2, all leaves
    sidebar_data = {}
    for l1 in l1_roots:
        color = DOMAIN_COLORS.get(l1, "#9E9E9E")
        nice = NICE_NAMES.get(l1, l1.replace("_", " ").title())
        groups = []
        for l2, leaves in sorted(hierarchy[l1].items()):
            leaf_items = []
            for leaf_id in sorted(leaves):
                attrs = all_nodes.get(leaf_id, {})
                aliases = attrs.get("aliases", [])[:3]
                leaf_items.append({"id": leaf_id, "label": leaf_id.replace("_", " ").title(), "aliases": aliases})
            groups.append({"id": l2, "label": l2.replace("_", " ").title(), "nodes": leaf_items})

        # Flat nodes
        flat_items = []
        for flat_id in sorted(flat_nodes_by_domain.get(l1, [])):
            attrs = all_nodes.get(flat_id, {})
            aliases = attrs.get("aliases", [])[:3]
            flat_items.append({"id": flat_id, "label": flat_id.replace("_", " ").title(), "aliases": aliases})
        if flat_items:
            groups.append({"id": f"{l1}_graph_nodes", "label": "Graph Nodes", "nodes": flat_items})

        sidebar_data[l1] = {"name": nice, "color": color, "groups": groups, "stats": domain_stats[l1]}

    sidebar_json = json.dumps(sidebar_data)

    ui_html = """
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
      * { box-sizing: border-box; }
      body { margin: 0; overflow: hidden; }

      #sidebar {
        position: fixed; top: 0; left: 0; width: 360px; height: 100vh; z-index: 1000;
        font-family: Inter, system-ui, sans-serif; background: #0d0d0d;
        border-right: 1px solid #1a1a1a; display: flex; flex-direction: column; color: #fff;
      }
      #sidebar-header {
        padding: 20px 20px 12px; flex-shrink: 0; border-bottom: 1px solid #1a1a1a;
      }
      #sidebar-header h1 { font-size: 18px; font-weight: 700; color: #FFD700; margin: 0 0 2px; }
      #sidebar-header .subtitle { font-size: 11px; color: #555; }

      #domain-list {
        flex-shrink: 0; overflow-x: auto; overflow-y: hidden; padding: 12px 16px 8px;
        display: flex; gap: 6px; border-bottom: 1px solid #1a1a1a;
        scrollbar-width: none;
      }
      #domain-list::-webkit-scrollbar { display: none; }
      .domain-chip {
        flex-shrink: 0; padding: 6px 12px; border-radius: 20px; font-size: 11px; font-weight: 500;
        cursor: pointer; transition: all 0.15s; border: 1px solid #222; background: #111; color: #888;
        white-space: nowrap;
      }
      .domain-chip:hover { border-color: #444; color: #ccc; }
      .domain-chip.active { color: #fff; }

      #search-box {
        margin: 10px 16px 6px; padding: 8px 12px; background: #111; border: 1px solid #222;
        border-radius: 8px; color: #fff; font-size: 12px; font-family: Inter, system-ui, sans-serif;
        outline: none; width: calc(100% - 32px);
      }
      #search-box::placeholder { color: #444; }
      #search-box:focus { border-color: #FFD700; }

      #node-panel { flex: 1; overflow-y: auto; padding: 4px 12px 20px; }
      #node-panel::-webkit-scrollbar { width: 3px; }
      #node-panel::-webkit-scrollbar-thumb { background: #222; border-radius: 3px; }

      .group-section { margin-bottom: 8px; }
      .group-header {
        font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em;
        color: #444; padding: 6px 8px 2px; cursor: pointer; display: flex; align-items: center; gap: 6px;
      }
      .group-header:hover { color: #888; }
      .group-header .arrow { font-size: 8px; transition: transform 0.15s; }
      .group-header .arrow.open { transform: rotate(90deg); }
      .group-header .badge {
        font-size: 9px; background: #1a1a1a; color: #555; padding: 1px 6px; border-radius: 10px;
        margin-left: auto; font-weight: 400;
      }

      .group-nodes { padding-left: 4px; }
      .group-nodes.collapsed { display: none; }

      .node-row {
        display: flex; align-items: center; gap: 8px; padding: 5px 8px; border-radius: 6px;
        cursor: pointer; transition: all 0.1s; border: 1px solid transparent;
      }
      .node-row:hover { background: rgba(255,255,255,0.04); border-color: #222; }
      .node-row.active { background: rgba(255,215,0,0.08); border-color: rgba(255,215,0,0.25); }
      .node-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
      .node-label { font-size: 12px; color: #bbb; flex: 1; min-width: 0; overflow: hidden;
                     text-overflow: ellipsis; white-space: nowrap; }
      .node-row:hover .node-label { color: #fff; }
      .node-aliases { font-size: 9px; color: #444; overflow: hidden; text-overflow: ellipsis;
                       white-space: nowrap; max-width: 120px; flex-shrink: 0; text-align: right; }

      #stats-footer {
        flex-shrink: 0; padding: 10px 20px; border-top: 1px solid #1a1a1a;
        font-size: 10px; color: #333; display: flex; justify-content: space-between;
      }

      #mynetwork { margin-left: 360px !important; width: calc(100% - 360px) !important; }
    </style>

    <div id="sidebar">
      <div id="sidebar-header">
        <h1>Impact News — Full Taxonomy</h1>
        <div class="subtitle">21 domains · TOTAL_NODES nodes · CROSS_EDGES cross-domain edges</div>
      </div>

      <div id="domain-list"></div>

      <input type="text" id="search-box" placeholder="Search any node..." oninput="filterAll()">

      <div id="node-panel"></div>

      <div id="stats-footer">
        <span>Click a node to focus in graph</span>
        <span>Click a domain to filter</span>
      </div>
    </div>

    <script>
    const DATA = SIDEBAR_JSON;
    const domainKeys = Object.keys(DATA).sort((a, b) => DATA[a].name.localeCompare(DATA[b].name));
    let activeDomain = null;
    let collapsedGroups = new Set();

    function init() {
      // Render domain chips
      const chipContainer = document.getElementById('domain-list');
      let chipHtml = '<div class="domain-chip active" data-domain="__all__" onclick="selectDomain(null)" style="border-color:#FFD700;color:#FFD700;">All</div>';
      domainKeys.forEach(dk => {
        const d = DATA[dk];
        chipHtml += '<div class="domain-chip" data-domain="' + dk + '" onclick="selectDomain(\\'' + dk + '\\')" style="--c:' + d.color + ';">' + d.name + '</div>';
      });
      chipContainer.innerHTML = chipHtml;
      renderAll();
    }

    function selectDomain(domain) {
      activeDomain = domain;
      document.querySelectorAll('.domain-chip').forEach(c => {
        const d = c.dataset.domain;
        if (d === '__all__' && !domain) {
          c.classList.add('active');
          c.style.borderColor = '#FFD700'; c.style.color = '#FFD700';
        } else if (d === domain) {
          c.classList.add('active');
          c.style.borderColor = DATA[d].color; c.style.color = DATA[d].color;
        } else {
          c.classList.remove('active');
          c.style.borderColor = '#222'; c.style.color = '#888';
        }
      });
      document.getElementById('search-box').value = '';
      renderAll();

      // Also highlight the domain in the graph
      if (domain && window.network) {
        try {
          window.network.focus(domain, { scale: 0.8, animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
          window.network.selectNodes([domain]);
        } catch(e) {}
      } else if (!domain && window.network) {
        try { window.network.fit({ animation: { duration: 500 } }); } catch(e) {}
      }
    }

    function filterAll() {
      renderAll();
    }

    function renderAll() {
      const panel = document.getElementById('node-panel');
      const search = document.getElementById('search-box').value.toLowerCase().trim();
      const domains = activeDomain ? [activeDomain] : domainKeys;
      let html = '';

      domains.forEach(dk => {
        const d = DATA[dk];
        let domainHasMatch = false;
        let groupsHtml = '';

        d.groups.forEach(g => {
          let nodes = g.nodes;
          if (search) {
            nodes = nodes.filter(n =>
              n.label.toLowerCase().includes(search) ||
              n.id.toLowerCase().includes(search) ||
              (n.aliases && n.aliases.some(a => a.toLowerCase().includes(search)))
            );
          }
          if (nodes.length === 0) return;
          domainHasMatch = true;

          const groupKey = dk + ':' + g.id;
          const collapsed = collapsedGroups.has(groupKey);

          groupsHtml += '<div class="group-section">';
          groupsHtml += '<div class="group-header" onclick="toggleGroup(\\'' + groupKey + '\\')">';
          groupsHtml += '<span class="arrow ' + (collapsed ? '' : 'open') + '">▶</span>';
          groupsHtml += g.label;
          groupsHtml += '<span class="badge">' + nodes.length + '</span>';
          groupsHtml += '</div>';
          groupsHtml += '<div class="group-nodes ' + (collapsed ? 'collapsed' : '') + '">';

          nodes.forEach(n => {
            const aliasText = n.aliases && n.aliases.length > 0 ? n.aliases.slice(0, 2).join(', ') : '';
            groupsHtml += '<div class="node-row" data-nid="' + n.id + '" onclick="focusNode(\\'' + n.id + '\\', this)">';
            groupsHtml += '<div class="node-dot" style="background:' + d.color + ';"></div>';
            groupsHtml += '<div class="node-label">' + n.label + '</div>';
            if (aliasText) groupsHtml += '<div class="node-aliases">' + aliasText + '</div>';
            groupsHtml += '</div>';
          });

          groupsHtml += '</div></div>';
        });

        if (domainHasMatch) {
          if (!activeDomain) {
            html += '<div style="font-size:11px;font-weight:700;padding:10px 8px 4px;color:' + d.color + ';cursor:pointer;" onclick="selectDomain(\\'' + dk + '\\')">';
            html += d.name + '</div>';
          }
          html += groupsHtml;
        }
      });

      if (!html) {
        html = '<div style="padding:30px;text-align:center;color:#333;font-size:12px;">No nodes found</div>';
      }
      panel.innerHTML = html;
    }

    function toggleGroup(groupKey) {
      if (collapsedGroups.has(groupKey)) {
        collapsedGroups.delete(groupKey);
      } else {
        collapsedGroups.add(groupKey);
      }
      renderAll();
    }

    function focusNode(nodeId, el) {
      document.querySelectorAll('.node-row').forEach(r => r.classList.remove('active'));
      if (el) el.classList.add('active');
      if (window.network) {
        try {
          window.network.focus(nodeId, { scale: 1.8, animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
          window.network.selectNodes([nodeId]);
        } catch(e) {}
      }
    }

    // Hook into vis.js network clicks
    document.addEventListener('DOMContentLoaded', () => {
      const check = setInterval(() => {
        if (window.network) {
          window.network.on('click', (params) => {
            if (params.nodes.length > 0) {
              const nid = params.nodes[0];
              document.querySelectorAll('.node-row').forEach(r => {
                if (r.dataset.nid === nid) {
                  r.classList.add('active');
                  r.scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                  r.classList.remove('active');
                }
              });
            }
          });
          clearInterval(check);
        }
      }, 300);
    });

    init();
    </script>
    """

    total_nodes = len(added)
    ui_html = ui_html.replace("SIDEBAR_JSON", sidebar_json)
    ui_html = ui_html.replace("TOTAL_NODES", str(total_nodes))
    ui_html = ui_html.replace("CROSS_EDGES", str(cross_edge_count))

    html = html.replace("<body>", f"<body>\n{ui_html}")

    with open(output, "w") as f:
        f.write(html)

    print(f"\nVisualization saved to {output}")
    print(f"  L1 domains: {len(l1_roots)}")
    print(f"  Total nodes: {total_nodes}")
    print(f"  Cross-domain edges: {cross_edge_count}")
    print(f"  Total edges: {len(net.edges)}")


if __name__ == "__main__":
    build_visualization()
