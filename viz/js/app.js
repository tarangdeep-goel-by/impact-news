// app.js — Boot/router module for Impact Atlas

import { loadGraph, searchNodes, formatNodeLabel, getEdgesFor, getNodeById, getCategoryPath } from './data.js';
import { setCategoryData, categoryColor, COLORS } from './theme.js';
import * as topdown from './topdown.js';
import * as streetview from './streetview.js';
import * as ppr from './ppr.js';
import * as view3d from './view3d.js';

// ---- Shared State ----
let currentView = null; // 'topdown' | 'street' (null until first activation)
let is3D = false;
let selectedNode = null;
let cy = null;
let graphData = null;

// ---- Boot ----

// Register cose-bilkent layout plugin (loaded via CDN as UMD global)
if (window.cytoscapeCoseBilkent && window.cytoscape) {
  window.cytoscape.use(window.cytoscapeCoseBilkent);
}

async function boot() {
  try {
    console.log('Boot starting...');
    // Load data
    graphData = await loadGraph();
    setCategoryData(graphData.categories);

    // Create Cytoscape instance
    cy = cytoscape({
      container: document.getElementById('cy'),
      style: [],
      elements: [],
      minZoom: 0.1,
      maxZoom: 5,
      wheelSensitivity: 0.8,
      boxSelectionEnabled: false,
      selectionType: 'single',
    });

    // Initialize modules
    topdown.init(cy, graphData);
    topdown.setCallbacks({ onSelectNode: _handleSelectNode, onDeselectNode: _handleDeselectNode });

    streetview.init(cy, graphData);
    streetview.setCallbacks({
      onSelectNode: _handleSelectNode,
      onDeselectNode: _handleDeselectNode,
      onSwitchToTopdown: (catId) => { switchView('topdown'); topdown.zoomToCategory(catId); },
    });

    ppr.init(cy, graphData);
    ppr.setCallbacks({ onSelectNode: _handleSelectNode });

    view3d.init(graphData);
    view3d.setCallbacks({ onSelectNode: _handleSelectNode });

    // Update stats bar
    _updateStats();

    // Wire up controls
    _wireSearch();
    _wireViewToggle();
    _wireKeyboard();
    _wireContextMenu();

    // Boot straight into 3D
    _build3DSidebar();
    currentView = '3d';
    view3d.activate();

    // Hide loading
    const loading = document.getElementById('loading');
    loading.classList.add('fade-out');
    setTimeout(() => loading.style.display = 'none', 400);

    // Show onboarding hint
    const hint = document.getElementById('onboarding-hint');
    hint.classList.remove('hidden');
    const dismissHint = () => {
      hint.classList.add('fade-out');
      setTimeout(() => { hint.style.display = 'none'; }, 400);
    };
    setTimeout(dismissHint, 5000);
    ['click', 'wheel', 'keydown'].forEach(evt =>
      document.addEventListener(evt, dismissHint, { once: true })
    );

  } catch (err) {
    console.error('BOOT FAILED:', err, err.stack);
    const loading = document.getElementById('loading');
    loading.querySelector('p').textContent = `Error: ${err.message}`;
    loading.querySelector('.spinner').style.display = 'none';
  }
}

// ---- View Switching ----

function switchView(view, focalNodeId) {
  if (view === currentView && view === 'topdown' && cy.elements().length > 0) return;

  // Deactivate current (skip on first call when currentView is null)
  if (currentView === 'topdown') {
    topdown.deactivate();
  } else if (currentView === 'street') {
    streetview.deactivate();
  }

  ppr.deactivate();
  currentView = view;

  // Remove all cytoscape event handlers before switching
  cy.off('tap');
  cy.off('dbltap');
  cy.off('cxttap');
  cy.off('mouseover');
  cy.off('mouseout');
  cy.off('tap.ppr');

  // Update body class
  document.body.classList.toggle('street-view', view === 'street');

  // Update view button group active state
  if (view === 'topdown') {
    const mode = topdown.getViewMode();
    document.getElementById('btn-map').classList.toggle('btn-active', mode === 'map');
    document.getElementById('btn-tree').classList.toggle('btn-active', mode === 'tree');
    document.getElementById('btn-street').classList.remove('btn-active');
  } else if (view === 'street') {
    document.getElementById('btn-map').classList.remove('btn-active');
    document.getElementById('btn-tree').classList.remove('btn-active');
    document.getElementById('btn-street').classList.add('btn-active');
  }

  // Re-activate 3D if toggle is on
  if (is3D) {
    setTimeout(() => _activate3D(), 100);
  }

  // Update URL hash
  if (view === 'topdown') {
    window.location.hash = 'topdown';
  }

  // Activate new view
  if (view === 'topdown') {
    topdown.activate();
    _handleDeselectNode();
  } else {
    const focal = focalNodeId || selectedNode || _getDefaultNode();
    streetview.activate(focal);
  }
}

function _getDefaultNode() {
  // Pick a well-connected node as default
  if (graphData.nodes && graphData.nodes.length > 0) {
    // Sort by total degree and pick top one
    const sorted = [...graphData.nodes].sort((a, b) => {
      const da = (a.degree?.in || 0) + (a.degree?.out || 0);
      const db = (b.degree?.in || 0) + (b.degree?.out || 0);
      return db - da;
    });
    return sorted[0].id;
  }
  return 'crude_oil';
}

// ---- Node Selection / Detail Panel ----

function _handleSelectNode(nodeId, nodeData) {
  selectedNode = nodeId;
  _renderDetailPanel(nodeId, nodeData);
}

function _handleDeselectNode() {
  selectedNode = null;
  const panel = document.getElementById('detail-panel');
  panel.classList.remove('visible');
  panel.classList.add('hidden');
}

function _renderDetailPanel(nodeId, nodeData) {
  const panel = document.getElementById('detail-panel');
  if (!nodeData) {
    nodeData = getNodeById(nodeId);
  }
  if (!nodeData) return;

  const cat = (nodeData.category || '').toLowerCase();
  const catInfo = graphData.categories?.[cat];
  const catName = catInfo?.name || cat.toUpperCase();
  const catCol = categoryColor(cat);

  const edges = getEdgesFor(nodeId);
  const outEdges = edges.filter(e => e.source === nodeId);
  const inEdges = edges.filter(e => e.target === nodeId);

  // Build hierarchy path
  const path = getCategoryPath(nodeId);
  let hierarchyHtml = '';
  if (currentView === 'street') {
    hierarchyHtml = '<div class="hierarchy-path">';
    for (let i = 0; i < path.length; i++) {
      if (i > 0) hierarchyHtml += '<span class="sep">\u203A</span>';
      const pId = path[i];
      const label = formatNodeLabel(pId, graphData);
      hierarchyHtml += `<span data-path-node="${pId}">${label}</span>`;
    }
    hierarchyHtml += '</div>';
  }

  let html = `
    <button class="detail-close">&times;</button>
    ${hierarchyHtml}
    <div class="detail-name">${formatNodeLabel(nodeId, graphData)}</div>
    <div class="detail-badges">
      <span class="badge badge-category" style="background: ${catCol}40; color: ${catCol}; border: 1px solid ${catCol}60;">${catName}</span>
      ${nodeData.port ? '<span class="badge badge-port">PORT</span>' : ''}
      ${nodeData.portal ? '<span class="badge badge-portal">PORTAL</span>' : ''}
    </div>
  `;

  // Aliases
  if (nodeData.aliases && nodeData.aliases.length > 0) {
    html += `<div class="detail-section">
      <div class="detail-section-title">Aliases</div>
      <div class="detail-aliases">
        ${nodeData.aliases.map(a => `<span class="alias-tag">${a}</span>`).join('')}
      </div>
    </div>`;
  }

  // Degree stats
  const degree = nodeData.degree || { in: 0, out: 0, causal_out: 0 };
  html += `<div class="detail-section">
    <div class="detail-section-title">Connections</div>
    <div class="detail-stats">
      <div class="stat-box">
        <div class="stat-value">${degree.in || 0}</div>
        <div class="stat-label">In</div>
      </div>
      <div class="stat-box">
        <div class="stat-value">${degree.out || 0}</div>
        <div class="stat-label">Out</div>
      </div>
      <div class="stat-box">
        <div class="stat-value">${degree.causal_out || 0}</div>
        <div class="stat-label">Causal</div>
      </div>
    </div>
  </div>`;

  // PPR Shockwave button (only in topdown view)
  if (currentView === 'topdown') {
    html += `<div class="detail-section">
      <button class="btn-shockwave" id="btn-shockwave" data-node="${nodeId}">
        Run PPR Shockwave
      </button>
    </div>`;
  }

  // PPR results if available
  const pprResults = ppr.getPprResults();
  if (pprResults && pprResults.length > 0) {
    html += ppr.renderPprList(pprResults, graphData);
  }

  // Outgoing edges
  if (outEdges.length > 0) {
    html += `<div class="detail-section">
      <div class="detail-section-title">Outgoing Edges (${outEdges.length})</div>
      <ul class="detail-edges-list">
        ${outEdges.map(e => _renderEdgeItem(e, 'out')).join('')}
      </ul>
    </div>`;
  }

  // Incoming edges
  if (inEdges.length > 0) {
    html += `<div class="detail-section">
      <div class="detail-section-title">Incoming Edges (${inEdges.length})</div>
      <ul class="detail-edges-list">
        ${inEdges.map(e => _renderEdgeItem(e, 'in')).join('')}
      </ul>
    </div>`;
  }

  panel.innerHTML = html;
  panel.classList.remove('hidden');
  panel.classList.add('visible');

  // Wire close button
  panel.querySelector('.detail-close').addEventListener('click', () => {
    _handleDeselectNode();
    if (currentView === 'topdown') {
      cy.batch(() => cy.elements().removeStyle('opacity'));
    }
  });

  // Wire shockwave button
  const shockBtn = panel.querySelector('#btn-shockwave');
  if (shockBtn) {
    shockBtn.addEventListener('click', () => {
      const nId = shockBtn.dataset.node;
      const results = ppr.runShockwave(nId);
      // Re-render panel to show PPR list
      setTimeout(() => _renderDetailPanel(nId, nodeData), 3200);
    });
  }

  // Wire edge item clicks (navigate to target/source)
  panel.querySelectorAll('.detail-edge-item').forEach(item => {
    item.addEventListener('click', () => {
      const targetId = item.dataset.target;
      if (targetId) {
        if (currentView === 'street') {
          streetview.walkTo(targetId);
        } else {
          topdown.focusNode(targetId);
        }
      }
    });
  });

  // Wire hierarchy path clicks (switch to topdown zoomed to category)
  panel.querySelectorAll('[data-path-node]').forEach(el => {
    el.addEventListener('click', () => {
      const pId = el.dataset.pathNode;
      switchView('topdown');
      setTimeout(() => topdown.zoomToCategory(pId), 300);
    });
  });

  // Wire PPR list item clicks
  panel.querySelectorAll('.ppr-item').forEach(item => {
    item.addEventListener('click', () => {
      const nId = item.dataset.node;
      if (currentView === 'street') {
        streetview.walkTo(nId);
      } else {
        topdown.focusNode(nId);
      }
    });
  });
}

function _renderEdgeItem(edge, direction) {
  const targetId = direction === 'out' ? edge.target : edge.source;
  const polClass = edge.polarity === 1 ? 'positive' : edge.polarity === -1 ? 'negative' : 'neutral';
  const arrow = direction === 'out' ? '\u2192' : '\u2190';

  return `<li class="detail-edge-item" data-target="${targetId}">
    <span class="edge-polarity ${polClass}"></span>
    <span class="edge-type-badge">${edge.type}</span>
    <span class="edge-target-name">${formatNodeLabel(targetId, graphData)}</span>
    <span class="edge-weight">${(edge.weight || 0).toFixed(2)}</span>
    <span class="edge-direction">${arrow}</span>
  </li>`;
}

// ---- Search ----

function _wireSearch() {
  const input = document.getElementById('search-input');
  const results = document.getElementById('search-results');

  input.addEventListener('input', () => {
    const q = input.value.trim();
    if (q.length < 1) {
      results.classList.remove('visible');
      results.innerHTML = '';
      return;
    }

    const matches = searchNodes(q, graphData, 10);
    if (matches.length === 0) {
      results.classList.remove('visible');
      results.innerHTML = '';
      return;
    }

    results.innerHTML = matches.map(m => {
      const catCol = categoryColor(m.category);
      const alias = m.matchType.includes('alias') ? `(alias match)` : '';
      return `<div class="search-result-item" data-node="${m.id}">
        <span class="result-category" style="background: ${catCol}30; color: ${catCol}">${m.category.toUpperCase()}</span>
        <span class="result-id">${m.label}</span>
        <span class="result-alias">${alias}</span>
      </div>`;
    }).join('');

    results.classList.add('visible');

    // Wire clicks
    results.querySelectorAll('.search-result-item').forEach(item => {
      item.addEventListener('click', () => {
        const nodeId = item.dataset.node;
        input.value = '';
        results.classList.remove('visible');
        results.innerHTML = '';

        if (currentView === 'topdown') {
          topdown.focusNode(nodeId);
        } else {
          streetview.walkTo(nodeId);
        }
      });
    });
  });

  // Close results on click outside
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#search-container')) {
      results.classList.remove('visible');
    }
  });

  // Close on Escape
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      input.blur();
      results.classList.remove('visible');
    }
    if (e.key === 'Enter') {
      const first = results.querySelector('.search-result-item');
      if (first) first.click();
    }
  });
}

// ---- View Toggle ----

function _wireViewToggle() {
  // Wire the fixed edge filter panel buttons
  _wireFilterButtons();
}

function _wireFilterButtons() {
  const cats = graphData.categories || {};

  // Populate L1 lists for each filter group
  document.querySelectorAll('.filter-l1-list').forEach(list => {
    const group = list.dataset.group;
    // For T→T: show trigger L1s. For T→I: show trigger L1s. For I→T: show impact L1s.
    const sourceWorld = group === 'it' ? 'impact' : 'trigger';
    let html = `<div class="filter-l1-item" data-l1="all"><span class="l1-dot" style="background:#fff;"></span>All</div>`;
    for (const [catId, catData] of Object.entries(cats)) {
      if (catData.world === sourceWorld) {
        html += `<div class="filter-l1-item" data-l1="${catId}"><span class="l1-dot" style="background:${catData.color};"></span>${catData.name}</div>`;
      }
    }
    list.innerHTML = html;
  });

  // Hierarchy button — simple toggle, no L1 drill-down
  const hierarchyBtn = document.querySelector('.filter-btn[data-filter="hierarchy"]');
  if (hierarchyBtn) {
    hierarchyBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const result = view3d.setFilter('hierarchy');
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.filter-l1-list').forEach(l => l.classList.add('hidden'));
      document.querySelectorAll('.filter-l1-item').forEach(i => i.classList.remove('active'));
      if (result.filter) hierarchyBtn.classList.add('active');
    });
  }

  // Group filter buttons — toggle L1 dropdown
  document.querySelectorAll('.filter-group-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const filter = btn.dataset.filter;
      const list = btn.parentElement.querySelector('.filter-l1-list');

      // Toggle this dropdown, close others
      document.querySelectorAll('.filter-l1-list').forEach(l => {
        if (l !== list) l.classList.add('hidden');
      });
      list.classList.toggle('hidden');

      // If opening, apply "All" by default
      if (!list.classList.contains('hidden')) {
        const result = view3d.setFilter(filter, null);
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        // Mark "All" as active
        list.querySelectorAll('.filter-l1-item').forEach(i => i.classList.remove('active'));
        list.querySelector('[data-l1="all"]')?.classList.add('active');
      } else {
        // Closing — clear filter
        view3d.setFilter(filter); // toggle off
        btn.classList.remove('active');
      }
    });
  });

  // L1 item clicks
  document.querySelectorAll('.filter-l1-list').forEach(list => {
    list.addEventListener('click', (e) => {
      e.stopPropagation();
      const item = e.target.closest('.filter-l1-item');
      if (!item) return;

      const l1 = item.dataset.l1;
      const group = list.dataset.group;
      const l1Id = l1 === 'all' ? null : l1;

      view3d.setFilter(group, l1Id);

      // Update active states
      list.querySelectorAll('.filter-l1-item').forEach(i => i.classList.remove('active'));
      item.classList.add('active');
    });
  });
}

// ---- Keyboard Shortcuts ----

function _wireKeyboard() {
  document.addEventListener('keydown', (e) => {
    // Don't capture when typing in search
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    switch (e.key) {
      case 'Escape':
        _handleDeselectNode();
        ppr.cancelAnimation();
        if (currentView === 'topdown') {
          cy.batch(() => cy.elements().removeStyle('opacity'));
        }
        // Close context menu
        document.getElementById('context-menu').classList.add('hidden');
        break;

      case 'Tab':
        e.preventDefault();
        break;

      case '/':
        e.preventDefault();
        document.getElementById('search-input').focus();
        break;

      case 'ArrowUp':
        e.preventDefault();
        cy.panBy({ x: 0, y: 50 });
        break;
      case 'ArrowDown':
        e.preventDefault();
        cy.panBy({ x: 0, y: -50 });
        break;
      case 'ArrowLeft':
        e.preventDefault();
        cy.panBy({ x: 50, y: 0 });
        break;
      case 'ArrowRight':
        e.preventDefault();
        cy.panBy({ x: -50, y: 0 });
        break;
      case '+':
      case '=':
        e.preventDefault();
        cy.zoom({ level: cy.zoom() * 1.2, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
        break;
      case '-':
      case '_':
        e.preventDefault();
        cy.zoom({ level: cy.zoom() / 1.2, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
        break;

      default:
        // 1-9: zoom to L1 category by index
        if (e.key >= '1' && e.key <= '9' && currentView === 'topdown') {
          const cats = Object.keys(graphData.categories || {}).sort();
          const idx = parseInt(e.key) - 1;
          if (idx < cats.length) {
            topdown.zoomToCategory(cats[idx]);
          }
        }
        break;
    }
  });
}

// ---- Context Menu ----

function _wireContextMenu() {
  const menu = document.getElementById('context-menu');

  // Hide on click anywhere
  document.addEventListener('click', () => {
    menu.classList.add('hidden');
  });

  // Enter Street View
  document.getElementById('ctx-street-view').addEventListener('click', (e) => {
    e.stopPropagation();
    const nodeId = menu.dataset.nodeId;
    menu.classList.add('hidden');
    if (nodeId) {
      switchView('street', nodeId);
    }
  });

  // Run PPR Shockwave
  document.getElementById('ctx-shockwave').addEventListener('click', (e) => {
    e.stopPropagation();
    const nodeId = menu.dataset.nodeId;
    menu.classList.add('hidden');
    if (nodeId) {
      const results = ppr.runShockwave(nodeId);
      const nodeData = getNodeById(nodeId);
      setTimeout(() => _renderDetailPanel(nodeId, nodeData), 3200);
    }
  });

  // Prevent default context menu on cy container
  document.getElementById('cy').addEventListener('contextmenu', (e) => {
    e.preventDefault();
  });
}

// ---- Stats Bar ----

function _updateStats() {
  const stats = graphData.stats || {};
  const text = [
    `${stats.node_count || graphData.nodes?.length || 0} nodes`,
    `${stats.edge_count || graphData.edges?.length || 0} edges`,
    `${stats.causal_edge_count || '?'} causal`,
    `${stats.category_count || Object.keys(graphData.categories || {}).length} categories`,
  ].join(' \u00B7 ');

  document.getElementById('stats-text').textContent = text;
}

// ---- 3D Sidebar ----

function _build3DSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar || !graphData) return;

  const cats = graphData.categories || {};
  const hierarchy = graphData.hierarchy || {};

  const triggers = [];
  const impacts = [];

  for (const [catId, catData] of Object.entries(cats)) {
    const entry = { id: catId, ...catData };
    if (catData.world === 'trigger') triggers.push(entry);
    else impacts.push(entry);
  }
  triggers.sort((a, b) => a.id.localeCompare(b.id));
  impacts.sort((a, b) => a.id.localeCompare(b.id));

  let html = '';

  const renderSection = (title, items) => {
    html += `<div class="sidebar-section">`;
    html += `<div class="sidebar-section-title">${title}</div>`;
    for (const cat of items) {
      const l2s = hierarchy[cat.id] || [];
      html += `<div class="sidebar-l1" data-node="${cat.id}">`;
      html += `<span class="sidebar-l1-dot" style="color: ${cat.color}; background: ${cat.color};"></span>`;
      html += `<span class="sidebar-l1-name">${cat.name}</span>`;
      if (l2s.length) html += `<span class="sidebar-l1-chevron">&#9654;</span>`;
      html += `</div>`;

      if (l2s.length) {
        html += `<div class="sidebar-l2-list">`;
        for (const l2Id of l2s) {
          html += `<div class="sidebar-l2" data-node="${l2Id}">${formatNodeLabel(l2Id, graphData)}</div>`;
        }
        html += `</div>`;
      }
    }
    html += `</div>`;
  };

  // Edge filter toggles at top of sidebar
  html += `<div class="sidebar-section sidebar-filters">
    <div class="sidebar-section-title">Edge Filters</div>
    <div class="filter-btn-group">
      <button class="filter-btn" data-filter="hierarchy">
        <span class="filter-dot" style="background:#888;"></span>Hierarchy
      </button>
      <button class="filter-btn" data-filter="tt">
        <span class="filter-dot" style="background:#4DD0E1;"></span>T→T
      </button>
      <button class="filter-btn" data-filter="ti">
        <span class="filter-dot" style="background:#FFD700;"></span>T→I
      </button>
      <button class="filter-btn" data-filter="it">
        <span class="filter-dot" style="background:#FF9800;"></span>I→T
      </button>
    </div>
  </div>`;

  renderSection('Triggers', triggers);
  renderSection('Impacts', impacts);

  sidebar.innerHTML = html;

  // Wire clicks — fly camera to node in 3D
  sidebar.querySelectorAll('.sidebar-l1').forEach(el => {
    el.addEventListener('click', () => {
      el.classList.toggle('expanded');
      const nodeId = el.dataset.node;
      view3d.focusNode(nodeId);
    });
  });

  sidebar.querySelectorAll('.sidebar-l2').forEach(el => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      view3d.focusNode(el.dataset.node);
    });
  });

  // Wire filter buttons (now inside sidebar)
  _wireFilterButtons();
}

// ---- Start ----
boot();
