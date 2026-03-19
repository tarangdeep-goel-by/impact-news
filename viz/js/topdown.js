// topdown.js — Top-down (cose-bilkent) view with compound nodes

import { buildProgressiveElements, buildTreeElements, buildElements, formatNodeLabel, getEdgesFor, getNodeById } from './data.js';
import { categoryColor, nodeStyle, edgeStyle, COLORS } from './theme.js';

let _cy = null;
let _graphData = null;
let _expandedL2s = new Set();
let _spotlightNode = null;
let _zoomRAF = null;
let _viewMode = 'map'; // 'map' | 'tree'

// Callbacks set by app.js
let _onSelectNode = null;
let _onDeselectNode = null;

export function setCallbacks({ onSelectNode, onDeselectNode }) {
  _onSelectNode = onSelectNode;
  _onDeselectNode = onDeselectNode;
}

export function init(cy, graphData) {
  _cy = cy;
  _graphData = graphData;
  _buildSidebar();
}

export function activate() {
  _rebuildGraph();
}

export function deactivate() {
  _spotlightNode = null;
}

export function getExpandedL2s() {
  return _expandedL2s;
}

export function setViewMode(mode) {
  _viewMode = mode;
  _rebuildGraph();
}

export function getViewMode() {
  return _viewMode;
}

/**
 * Focus on a specific node in the top-down view.
 */
export function focusNode(nodeId) {
  // Make sure the node's L2 parent is expanded if it's a leaf
  const nodeData = getNodeById(nodeId);
  if (nodeData && nodeData.level > 2 && !nodeData.is_category && nodeData.parent) {
    if (!_expandedL2s.has(nodeData.parent)) {
      _expandedL2s.add(nodeData.parent);
      _rebuildGraph();
    }
  }

  // Wait for layout to settle, then spotlight
  setTimeout(() => {
    const cyNode = _cy.getElementById(nodeId);
    if (cyNode.length) {
      _spotlight(cyNode);
      _cy.animate({
        center: { eles: cyNode },
        zoom: 1.5,
        duration: 400,
      });
    }
  }, 300);
}

/**
 * Zoom to an L1 category cluster.
 */
export function zoomToCategory(catId) {
  const catLower = catId.toLowerCase();
  const catNodes = _cy.nodes().filter(n => {
    const nc = n.data('category');
    return nc === catLower;
  });
  if (catNodes.length > 0) {
    _cy.animate({
      fit: { eles: catNodes, padding: 60 },
      duration: 400,
    });
  }
}

function _rebuildGraph() {
  if (!_cy || !_graphData) return;

  let elements;
  if (_viewMode === 'tree') {
    elements = buildTreeElements(_graphData);
  } else {
    elements = buildProgressiveElements(_graphData, _expandedL2s);
  }

  _cy.batch(() => {
    _cy.elements().remove();
    _cy.add(elements);
  });

  _applyStyles();
  _runLayout();
  _wireEvents();
}

function _applyStyles() {
  _cy.style()
    .selector('node')
    .style({
      'background-color': (ele) => categoryColor(ele.data('category')),
      'width': (ele) => {
        const level = ele.data('level');
        return level === 1 ? 50 : level === 2 ? 25 : 12;
      },
      'height': (ele) => {
        const level = ele.data('level');
        return level === 1 ? 50 : level === 2 ? 25 : 12;
      },
      'label': 'data(label)',
      'font-size': (ele) => ele.data('level') === 1 ? 11 : ele.data('level') === 2 ? 8 : 6,
      'font-weight': (ele) => ele.data('level') === 1 ? 'bold' : 'normal',
      'color': '#e0e0e0',
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 4,
      'text-wrap': 'ellipsis',
      'text-max-width': (ele) => ele.data('level') === 1 ? 150 : ele.data('level') === 2 ? 90 : 50,
      'text-outline-color': '#0a0a0f',
      'text-outline-width': 1.5,
      'border-width': (ele) => ele.data('level') === 1 ? 3 : ele.data('level') === 2 ? 2 : 0,
      'border-color': (ele) => categoryColor(ele.data('category')),
      'border-opacity': 0.6,
      'overlay-opacity': 0,
    })
    .selector('node:parent')
    .style({
      'background-color': (ele) => categoryColor(ele.data('category')),
      'background-opacity': 0.06,
      'shape': 'round-rectangle',
      'border-width': 1.5,
      'border-color': (ele) => categoryColor(ele.data('category')),
      'border-opacity': 0.25,
      'border-style': 'dashed',
      'label': 'data(label)',
      'font-size': 10,
      'font-weight': 'bold',
      'color': (ele) => categoryColor(ele.data('category')),
      'text-opacity': 0.6,
      'text-valign': 'top',
      'text-halign': 'center',
      'text-margin-y': -8,
      'text-outline-color': '#0a0a0f',
      'text-outline-width': 2,
      'padding': 20,
    })
    // Real causal edges
    .selector('edge[!isAggregated]')
    .style({
      'line-color': (ele) => {
        const p = ele.data('polarity');
        return p === 1 ? COLORS.positive : p === -1 ? COLORS.negative : COLORS.neutral;
      },
      'target-arrow-color': (ele) => {
        const p = ele.data('polarity');
        return p === 1 ? COLORS.positive : p === -1 ? COLORS.negative : COLORS.neutral;
      },
      'width': (ele) => Math.max(1, (ele.data('weight') || 0.5) * 3),
      'opacity': 0.3,
      'curve-style': 'bezier',
      'target-arrow-shape': 'triangle',
      'arrow-scale': 0.5,
      'line-style': (ele) => ele.data('delay') === 'IMMEDIATE' ? 'solid' : 'dashed',
      'line-dash-pattern': (ele) => {
        switch (ele.data('delay')) {
          case 'SHORT_TERM': return [8, 4];
          case 'MEDIUM_TERM': return [12, 6];
          case 'LONG_TERM': return [4, 4];
          default: return [1, 0];
        }
      },
    })
    // Aggregated edges — opacity scales with count
    .selector('edge[?isAggregated]')
    .style({
      'line-color': '#FFD700',
      'target-arrow-color': '#FFD700',
      'width': (ele) => {
        const c = ele.data('count') || 1;
        return Math.min(8, 1 + c * 0.4);
      },
      'opacity': (ele) => {
        const c = ele.data('count') || 1;
        if (c >= 5) return 0.5;
        if (c >= 3) return 0.3;
        return 0.12;
      },
      'curve-style': 'bezier',
      'target-arrow-shape': 'triangle',
      'arrow-scale': 0.5,
      'label': (ele) => {
        const c = ele.data('count') || 1;
        return c >= 3 ? String(c) : '';
      },
      'font-size': 8,
      'color': '#FFD700',
      'text-outline-color': '#0a0a0f',
      'text-outline-width': 1,
      'text-rotation': 'autorotate',
    })
    // Structural edges (CONTAINS/IS_A) — visible in tree mode, hidden in map mode
    .selector('edge[edgeType = "CONTAINS"], edge[edgeType = "IS_A"]')
    .style({
      'visibility': _viewMode === 'tree' ? 'visible' : 'hidden',
      'line-color': (ele) => categoryColor(ele.source().data('category')),
      'target-arrow-color': (ele) => categoryColor(ele.source().data('category')),
      'width': 0.8,
      'opacity': 0.2,
      'target-arrow-shape': 'none',
      'line-style': 'solid',
      'label': '',
    })
    .update();
}

function _runLayout() {
  if (_viewMode === 'tree') {
    _cy.layout({
      name: 'cose-bilkent',
      animate: false,
      quality: 'default',
      nodeDimensionsIncludeLabels: false,
      fit: true,
      padding: 30,
      nodeRepulsion: 4000,
      idealEdgeLength: 60,
      edgeElasticity: 0.2,
      nestingFactor: 0.2,
      gravity: 0.3,
      gravityRange: 3,
      gravityCompound: 1.5,
      gravityRangeCompound: 2.0,
      numIter: 3000,
      tile: true,
      tilingPaddingVertical: 15,
      tilingPaddingHorizontal: 15,
    }).run();
  } else {
    _cy.layout({
      name: 'cose-bilkent',
      animate: false,
      quality: 'default',
      nodeDimensionsIncludeLabels: true,
      fit: true,
      padding: 40,
      nodeRepulsion: 10000,
      idealEdgeLength: 150,
      edgeElasticity: 0.3,
      nestingFactor: 0.15,
      gravity: 0.15,
      gravityRange: 4,
      gravityCompound: 1.2,
      gravityRangeCompound: 2.0,
      numIter: 3000,
      tile: true,
      tilingPaddingVertical: 25,
      tilingPaddingHorizontal: 25,
    }).run();
  }
}

function _wireEvents() {
  // Shared tooltip element (used by both node and edge hover)
  let tooltipEl = document.querySelector('.cy-tooltip');
  if (!tooltipEl) {
    tooltipEl = document.createElement('div');
    tooltipEl.className = 'cy-tooltip';
    tooltipEl.style.display = 'none';
    document.body.appendChild(tooltipEl);
  }

  // Click node
  _cy.on('tap', 'node', (evt) => {
    const node = evt.target;
    const nodeId = node.data('id');
    const level = node.data('level');
    const isCat = node.data('isCategory');

    // L2 expand/collapse
    if (level === 2 || (isCat && level > 1)) {
      if (_expandedL2s.has(nodeId)) {
        // Already expanded — spotlight instead (collapse on double-click)
        _spotlight(node);
      } else {
        _expandedL2s.add(nodeId);
        _rebuildGraph();
      }
      return;
    }

    // L1 — just spotlight
    if (level === 1) {
      _spotlight(node);
      return;
    }

    // L3/L4 — spotlight
    _spotlight(node);
  });

  // Double-click to collapse
  _cy.on('dbltap', 'node', (evt) => {
    const nodeId = evt.target.data('id');
    if (_expandedL2s.has(nodeId)) {
      _expandedL2s.delete(nodeId);
      _rebuildGraph();
    }
  });

  // Click background to clear spotlight
  _cy.on('tap', (evt) => {
    if (evt.target === _cy) {
      _clearSpotlight();
    }
  });

  // Right-click context menu
  _cy.on('cxttap', 'node', (evt) => {
    const node = evt.target;
    const pos = evt.renderedPosition || evt.position;
    _showContextMenu(node.data('id'), pos.x, pos.y);
    evt.originalEvent.preventDefault();
  });

  // Node hover tooltip
  _cy.on('mouseover', 'node', (evt) => {
    const node = evt.target;
    const d = node.data();
    const pos = evt.renderedPosition;
    const deg = d.degree || { in: 0, out: 0, causal_out: 0 };
    const catName = _graphData.categories?.[d.category]?.name || d.category.toUpperCase();

    tooltipEl.innerHTML = `
      <div class="tt-title">${d.label}</div>
      <div class="tt-row"><span class="tt-label">Category</span><span class="tt-value">${catName}</span></div>
      <div class="tt-row"><span class="tt-label">In / Out</span><span class="tt-value">${deg.in} / ${deg.out}</span></div>
      ${d.aliases && d.aliases.length > 0 ? '<div class="tt-row"><span class="tt-label">Aliases</span><span class="tt-value">' + d.aliases.slice(0, 3).join(', ') + '</span></div>' : ''}
    `;

    const cyRect = _cy.container().getBoundingClientRect();
    tooltipEl.style.left = (cyRect.left + pos.x + 15) + 'px';
    tooltipEl.style.top = (cyRect.top + pos.y - 10) + 'px';
    tooltipEl.style.display = 'block';
  });

  _cy.on('mouseout', 'node', () => {
    tooltipEl.style.display = 'none';
  });

  // Edge hover tooltip
  _cy.on('mouseover', 'edge', (evt) => {
    const edge = evt.target;
    const d = edge.data();
    const pos = evt.renderedPosition;

    if (d.isAggregated) {
      tooltipEl.innerHTML = `
        <div class="tt-title">${d.count} causal connections</div>
        <div class="tt-row"><span class="tt-label">Max Weight</span><span class="tt-value">${(d.maxWeight || 0).toFixed(2)}</span></div>
        <div class="tt-row"><span class="tt-label">Click to expand endpoints</span></div>
      `;
    } else {
      tooltipEl.innerHTML = `
        <div class="tt-row"><span class="tt-label">Type</span><span class="tt-value">${d.edgeType}</span></div>
        <div class="tt-row"><span class="tt-label">Weight</span><span class="tt-value">${d.weight}</span></div>
        <div class="tt-row"><span class="tt-label">Polarity</span><span class="tt-value">${d.polarity > 0 ? '+1' : d.polarity < 0 ? '-1' : '0'}</span></div>
        <div class="tt-row"><span class="tt-label">Delay</span><span class="tt-value">${d.delay}</span></div>
        ${d.description ? '<div class="tt-row"><span class="tt-label">Desc</span><span class="tt-value">' + d.description + '</span></div>' : ''}
      `;
    }

    const cyRect = _cy.container().getBoundingClientRect();
    tooltipEl.style.left = (cyRect.left + pos.x + 12) + 'px';
    tooltipEl.style.top = (cyRect.top + pos.y - 10) + 'px';
    tooltipEl.style.display = 'block';
  });

  _cy.on('mouseout', 'edge', () => {
    tooltipEl.style.display = 'none';
  });

  // Semantic zoom
  _cy.on('zoom', _handleZoom);
  _handleZoom(); // apply once on load
}

function _handleZoom() {
  if (_zoomRAF) return;
  _zoomRAF = requestAnimationFrame(() => {
    _zoomRAF = null;
    _applySemanticZoom();
  });
}

function _applySemanticZoom() {
  const z = _cy.zoom();
  _cy.batch(() => {
    _cy.nodes().forEach(n => {
      if (n.isParent()) return; // Compound parents styled separately
      const level = n.data('level');
      if (level === 2) {
        n.style('label', z >= 0.3 ? n.data('label') : '');
      } else if (level >= 3) {
        n.style('label', z >= 0.6 ? n.data('label') : '');
      }
    });

    // Aggregated edge labels
    _cy.edges('[?isAggregated]').forEach(e => {
      e.style('label', z >= 0.4 ? String(e.data('count') || '') : '');
    });

    // Causal edge opacity (skip during spotlight)
    if (!_spotlightNode) {
      _cy.edges('[!isAggregated]').forEach(e => {
        const et = e.data('edgeType');
        if (et === 'CONTAINS' || et === 'IS_A') return;
        e.style('opacity', z < 0.3 ? 0.1 : z < 0.6 ? 0.2 : 0.3);
      });
    }
  });

  const pct = Math.round(z * 100);
  const indicator = document.getElementById('zoom-indicator');
  if (indicator) {
    indicator.textContent = z < 0.5 ? pct + '% — zoom in for detail' : pct + '%';
  }
}

function _spotlight(cyNode) {
  _spotlightNode = cyNode.data('id');

  const connected = cyNode.connectedEdges().connectedNodes();
  const highlighted = connected.union(cyNode);
  const connectedEdges = cyNode.connectedEdges();

  _cy.batch(() => {
    // Dim everything
    _cy.elements().style('opacity', 0.12);
    // Highlight connected
    highlighted.style('opacity', 1);
    connectedEdges.style('opacity', 0.7);
  });

  // Notify app for detail panel
  if (_onSelectNode) {
    const nodeData = getNodeById(cyNode.data('id'));
    _onSelectNode(cyNode.data('id'), nodeData);
  }
}

function _clearSpotlight() {
  _spotlightNode = null;
  _cy.batch(() => {
    _cy.elements().removeStyle('opacity');
  });
  if (_onDeselectNode) _onDeselectNode();
}

function _showContextMenu(nodeId, x, y) {
  const menu = document.getElementById('context-menu');
  const cyRect = _cy.container().getBoundingClientRect();
  menu.style.left = (cyRect.left + x) + 'px';
  menu.style.top = (cyRect.top + y) + 'px';
  menu.classList.remove('hidden');
  menu.dataset.nodeId = nodeId;
}

/**
 * Build the left sidebar category tree.
 */
function _buildSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar || !_graphData) return;

  const cats = _graphData.categories || {};
  const hierarchy = _graphData.hierarchy || {};

  // Group by world
  const triggers = [];
  const impacts = [];

  for (const [catId, catData] of Object.entries(cats)) {
    const entry = { id: catId, ...catData };
    if (catData.world === 'trigger') triggers.push(entry);
    else impacts.push(entry);
  }

  // Sort by ID
  triggers.sort((a, b) => a.id.localeCompare(b.id));
  impacts.sort((a, b) => a.id.localeCompare(b.id));

  let html = '';

  const renderSection = (title, items) => {
    html += `<div class="sidebar-section">`;
    html += `<div class="sidebar-section-title">${title}</div>`;
    for (const cat of items) {
      const l2s = (hierarchy[cat.id] || []);
      html += `<div class="sidebar-l1" data-cat="${cat.id}">`;
      html += `<span class="sidebar-l1-dot" style="color: ${cat.color}; background: ${cat.color};"></span>`;
      html += `<span class="sidebar-l1-name">${cat.name}</span>`;
      if (l2s.length) html += `<span class="sidebar-l1-chevron">&#9654;</span>`;
      html += `</div>`;

      if (l2s.length) {
        html += `<div class="sidebar-l2-list">`;
        for (const l2Id of l2s) {
          html += `<div class="sidebar-l2" data-node="${l2Id}">${formatNodeLabel(l2Id, _graphData)}</div>`;
        }
        html += `</div>`;
      }
    }
    html += `</div>`;
  };

  renderSection('Triggers', triggers);
  renderSection('Impacts', impacts);

  sidebar.innerHTML = html;

  // Wire sidebar events
  sidebar.querySelectorAll('.sidebar-l1').forEach(el => {
    el.addEventListener('click', () => {
      const catId = el.dataset.cat;
      // Toggle expand
      el.classList.toggle('expanded');
      // Zoom to category
      zoomToCategory(catId);
    });
  });

  sidebar.querySelectorAll('.sidebar-l2').forEach(el => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      const nodeId = el.dataset.node;
      focusNode(nodeId);
    });
  });
}
