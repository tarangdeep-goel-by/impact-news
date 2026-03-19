// view3d.js — Solar System 3D view with edge filter toggles

import { formatNodeLabel, getNodeById } from './data.js';

const CATEGORY_COLORS = {
  t1: '#4FC3F7', t2: '#7986CB', t3: '#4DD0E1', t4: '#90A4AE', t5: '#80CBC4',
  i1: '#66BB6A', i2: '#EC407A', i3: '#26C6DA', i4: '#AB47BC', i5: '#42A5F5',
  i6: '#EF5350', i7: '#FFA726', i8: '#FF7043', i9: '#26A69A', i10: '#7E57C2', i11: '#78909C',
};

// Edge filter categories
const EDGE_FILTERS = {
  hierarchy: { label: 'Hierarchy', desc: 'CONTAINS / IS_A (parent→child)', color: '#888' },
  tt: { label: 'T→T', desc: 'Trigger to Trigger (lateral)', color: '#4DD0E1' },
  ti: { label: 'T→I', desc: 'Trigger to Impact (bridges)', color: '#FFD700' },
  it: { label: 'I→T', desc: 'Impact to Trigger (feedback)', color: '#FF9800' },
};

let _graph = null;
let _graphData = null;
let _allLinks = [];
let _allNodes = [];
let _active = false;
let _onSelectNode = null;
let _activeFilter = null; // null = show all, or 'hierarchy'|'tt'|'ti'|'it'
let _activeL1 = null; // null = all L1s, or specific L1 id like 't3'

export function init(graphData) {
  _graphData = graphData;
}

export function setCallbacks({ onSelectNode }) {
  _onSelectNode = onSelectNode;
}

export function activate() {
  const container = document.getElementById('cy3d');
  container.style.display = 'block';
  document.body.classList.add('view-3d');
  _active = true;

  const { nodes, links } = _buildGraph();
  _allNodes = nodes;
  _allLinks = links;

  if (_graph) {
    _graph._destructor();
    _graph = null;
    container.innerHTML = '';
  }

  _graph = ForceGraph3D()(container)
    .graphData({ nodes: [...nodes], links: _getFilteredLinks() })
    .backgroundColor('#0a0a0f')
    .nodeColor(n => n.color)
    .nodeVal(n => n.size)
    .nodeOpacity(0.9)
    .nodeLabel(n => {
      const cat = _graphData.categories?.[n.category]?.name || n.category.toUpperCase();
      const deg = n.degree;
      return `<div style="background:rgba(0,0,0,0.92);padding:8px 12px;border-radius:4px;font-family:Inter,sans-serif;font-size:12px;max-width:260px;border:1px solid ${n.color}40;">
        <div style="font-weight:700;margin-bottom:3px;color:#fff;">${n.label}</div>
        <div style="color:${n.color};font-size:10px;">L${n.level} · ${cat}</div>
        <div style="color:rgba(255,255,255,0.5);font-size:10px;margin-top:3px;">In: ${deg.in} · Out: ${deg.out} · Causal: ${deg.causal_out}</div>
        ${n.aliases.length > 0 ? `<div style="color:rgba(255,255,255,0.35);font-size:10px;margin-top:2px;">${n.aliases.slice(0,3).join(', ')}</div>` : ''}
      </div>`;
    })
    .linkColor(l => l.color)
    .linkWidth(l => l.__w || 0.5)
    .linkOpacity(l => l.__o || 0.15)
    .linkDirectionalArrowLength(l => l.isHierarchy ? 0 : 2)
    .linkDirectionalArrowRelPos(1)
    .linkDirectionalArrowColor(l => l.color)
    .linkLabel(l => l.__label || '')
    .linkThreeObjectExtend(false)
    .d3AlphaDecay(0.015)
    .d3VelocityDecay(0.25)
    .warmupTicks(300)
    .cooldownTicks(500)
    .onNodeClick(node => {
      if (_onSelectNode) {
        _onSelectNode(node.id, getNodeById(node.id));
      }
      const distance = node.level === 1 ? 250 : node.level === 2 ? 120 : 60;
      const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
      _graph.cameraPosition(
        { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
        { x: node.x, y: node.y, z: node.z },
        800
      );
    })
    .onNodeHover(node => {
      container.style.cursor = node ? 'pointer' : 'default';
    });

  // Solar system forces
  _graph.d3Force('charge').strength(node => {
    if (node.level === 1) return -3000;
    if (node.level === 2) return -300;
    return -30;
  });
  _graph.d3Force('link')
    .distance(link => link.isHierarchy ? 20 : 150)
    .strength(link => link.isHierarchy ? 1.0 : 0.02);

  setTimeout(() => {
    _graph.cameraPosition({ x: 0, y: 300, z: 700 }, { x: 0, y: 0, z: 0 }, 0);
  }, 100);
}

export function deactivate() {
  _active = false;
  document.body.classList.remove('view-3d');
  document.getElementById('cy3d').style.display = 'none';
  if (_graph) _graph.pauseAnimation();
}

export function isActive() { return _active; }

export function focusNode(nodeId) {
  if (!_graph) return;
  const node = _graph.graphData().nodes.find(n => n.id === nodeId);
  if (!node) return;
  const distance = node.level === 1 ? 300 : node.level === 2 ? 150 : 80;
  const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
  _graph.cameraPosition(
    { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
    { x: node.x, y: node.y, z: node.z },
    1000
  );
}

export function destroy() {
  if (_graph) {
    _graph._destructor();
    _graph = null;
    document.getElementById('cy3d').innerHTML = '';
  }
  _active = false;
  document.body.classList.remove('view-3d');
}

/**
 * Toggle an edge filter. If same filter clicked again, deactivate (show all).
 */
export function setFilter(filter, l1Id = undefined) {
  if (l1Id === undefined && _activeFilter === filter) {
    // Simple toggle off
    _activeFilter = null;
    _activeL1 = null;
  } else {
    _activeFilter = filter;
    _activeL1 = l1Id || null;
  }
  _applyFilter();
  return { filter: _activeFilter, l1: _activeL1 };
}

export function getFilter() {
  return { filter: _activeFilter, l1: _activeL1 };
}

// --- Filter helpers ---

function _getLinkFilter(link) {
  if (link.isHierarchy) return 'hierarchy';
  const srcWorld = link.srcWorld;
  const tgtWorld = link.tgtWorld;
  if (srcWorld === 'T' && tgtWorld === 'T') return 'tt';
  if (srcWorld === 'T' && tgtWorld === 'I') return 'ti';
  if (srcWorld === 'I' && tgtWorld === 'T') return 'it';
  return 'other';
}

function _getLinkColor(link) {
  if (!_activeFilter) return link.baseColor;
  if (_isLinkMatch(link)) return link.activeColor;
  return 'rgba(50,50,50,0.1)';
}

function _getLinkWidth(link) {
  if (!_activeFilter) {
    return link.isHierarchy ? 0.3 : Math.max(0.4, link.weight * 0.8);
  }
  if (_isLinkMatch(link)) {
    return link.isHierarchy ? 1.5 : Math.max(2, link.weight * 4);
  }
  return 0.1;
}

function _getFilteredLinks() {
  // Always include all links — visibility controlled by opacity/width
  return [..._allLinks];
}

function _isLinkMatch(l) {
  if (!_activeFilter) return false;
  if (_getLinkFilter(l) !== _activeFilter) return false;
  if (!_activeL1) return true; // no L1 scope = all match
  // Check if either endpoint belongs to the selected L1
  const srcCat = l.srcCat || (typeof l.source === 'object' ? l.source.category : '') || '';
  const tgtCat = l.tgtCat || (typeof l.target === 'object' ? l.target.category : '') || '';
  return srcCat === _activeL1 || tgtCat === _activeL1;
}

function _applyFilter() {
  if (!_graph) return;
  const gd = _graph.graphData();
  for (const l of gd.links) {
    const isMatch = _isLinkMatch(l);
    l.color = _getLinkColor(l);
    l.__w = _getLinkWidth(l);
    l.__o = _activeFilter ? (isMatch ? 0.8 : 0.008) : 0.15;
    l.__label = isMatch ? `${l.edgeType} ${l.weight}` : '';
  }
  // Force 3d-force-graph to re-read by resetting graphData (preserves node positions via fx/fy/fz)
  // Freeze node positions first
  for (const n of gd.nodes) {
    n.fx = n.x; n.fy = n.y; n.fz = n.z;
  }
  _graph.graphData({ nodes: gd.nodes, links: gd.links });
  // Unfreeze after re-render
  setTimeout(() => {
    for (const n of _graph.graphData().nodes) {
      n.fx = undefined; n.fy = undefined; n.fz = undefined;
    }
  }, 100);
}

// --- Build graph data ---
function _buildGraph() {
  const nodes = [];
  const links = [];
  const nodeMap = {};

  for (const node of _graphData.nodes) {
    nodeMap[node.id] = node;
  }

  for (const node of _graphData.nodes) {
    const cat = (node.category || '').toLowerCase();
    const level = node.level || 4;
    nodes.push({
      id: node.id,
      label: formatNodeLabel(node.id, _graphData),
      category: cat,
      level: level,
      isCategory: !!node.is_category,
      color: CATEGORY_COLORS[cat] || '#888',
      size: level === 1 ? 200 : level === 2 ? 30 : level === 3 ? 6 : 2,
      aliases: node.aliases || [],
      degree: node.degree || { in: 0, out: 0, causal_out: 0 },
    });
  }

  for (const edge of _graphData.edges) {
    const isHierarchy = edge.is_structural || edge.type === 'CONTAINS' || edge.type === 'IS_A';
    const polarity = edge.polarity || 0;
    const srcCat = (nodeMap[edge.source]?.category || '').toLowerCase();
    const tgtCat = (nodeMap[edge.target]?.category || '').toLowerCase();
    const srcWorld = srcCat.startsWith('t') ? 'T' : 'I';
    const tgtWorld = tgtCat.startsWith('t') ? 'T' : 'I';

    // Colors for each filter state
    let baseColor, activeColor;
    if (isHierarchy) {
      baseColor = (CATEGORY_COLORS[srcCat] || '#444') + '25';
      activeColor = CATEGORY_COLORS[srcCat] || '#888';
    } else if (srcWorld === 'T' && tgtWorld === 'I') {
      baseColor = 'rgba(255,215,0,0.25)';
      activeColor = '#FFD700';
    } else if (srcWorld === 'I' && tgtWorld === 'T') {
      baseColor = 'rgba(255,152,0,0.25)';
      activeColor = '#FF9800';
    } else if (srcWorld === 'T' && tgtWorld === 'T') {
      baseColor = 'rgba(77,208,225,0.25)';
      activeColor = '#4DD0E1';
    } else {
      baseColor = 'rgba(100,100,100,0.15)';
      activeColor = '#888';
    }

    links.push({
      source: edge.source,
      target: edge.target,
      edgeType: edge.type || '',
      weight: edge.weight || 0.5,
      polarity: polarity,
      isHierarchy: isHierarchy,
      srcWorld: srcWorld,
      tgtWorld: tgtWorld,
      baseColor: baseColor,
      activeColor: activeColor,
      srcCat: srcCat,
      tgtCat: tgtCat,
      color: baseColor,
      __w: isHierarchy ? 0.3 : Math.max(0.4, (edge.weight || 0.5) * 0.8),
      __o: 0.15,
    });
  }

  return { nodes, links };
}
