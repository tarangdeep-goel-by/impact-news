// streetview.js — Concentric street-view exploration

import { buildStreetElements, formatNodeLabel, getCategoryPath, getNodeById, getEdgesFor } from './data.js';
import { categoryColor, COLORS } from './theme.js';

let _cy = null;
let _graphData = null;
let _focalNode = null;
let _breadcrumbs = [];

// Callbacks set by app.js
let _onSelectNode = null;
let _onDeselectNode = null;
let _onSwitchToTopdown = null;

export function setCallbacks({ onSelectNode, onDeselectNode, onSwitchToTopdown }) {
  _onSelectNode = onSelectNode;
  _onDeselectNode = onDeselectNode;
  _onSwitchToTopdown = onSwitchToTopdown;
}

export function init(cy, graphData) {
  _cy = cy;
  _graphData = graphData;
}

export function activate(focalNodeId) {
  if (!focalNodeId) return;
  _focalNode = focalNodeId;
  _rebuildView(focalNodeId, false);
  _updateBreadcrumbs();

  // Update URL hash
  window.location.hash = `street/${focalNodeId}`;
}

export function deactivate() {
  _clearBreadcrumbs();
  _focalNode = null;
}

export function getFocalNode() {
  return _focalNode;
}

/**
 * Navigate to a new focal node (used for walk navigation).
 */
export function walkTo(nodeId) {
  // Add to breadcrumbs
  if (_focalNode && _focalNode !== nodeId) {
    _breadcrumbs.push(_focalNode);
    if (_breadcrumbs.length > 10) _breadcrumbs.shift();
  }

  _focalNode = nodeId;

  // Animate transition
  const cyNode = _cy.getElementById(nodeId);
  if (cyNode.length) {
    _cy.animate({
      center: { eles: cyNode },
      duration: 300,
      complete: () => {
        _rebuildView(nodeId, true);
        _updateBreadcrumbs();
      },
    });
  } else {
    _rebuildView(nodeId, false);
    _updateBreadcrumbs();
  }

  // Update URL hash
  window.location.hash = `street/${nodeId}`;
}

function _rebuildView(focalId, animated) {
  const { elements, ring1, ring2 } = buildStreetElements(_graphData, focalId);
  if (elements.length === 0) return;

  _cy.batch(() => {
    _cy.elements().remove();
    _cy.add(elements);
  });

  _applyStreetStyles(focalId);
  _runConcentricLayout(focalId);
  _wireEvents(focalId);
  _renderHierarchyPath(focalId);

  // Select focal node for detail panel
  if (_onSelectNode) {
    const nodeData = getNodeById(focalId);
    _onSelectNode(focalId, nodeData);
  }
}

function _applyStreetStyles(focalId) {
  _cy.style()
    .selector('node')
    .style({
      'background-color': (ele) => categoryColor(ele.data('category')),
      'width': (ele) => {
        const ring = ele.data('ring');
        return ring === 0 ? 60 : ring === 1 ? 30 : 15;
      },
      'height': (ele) => {
        const ring = ele.data('ring');
        return ring === 0 ? 60 : ring === 1 ? 30 : 15;
      },
      'label': 'data(label)',
      'font-size': (ele) => {
        const ring = ele.data('ring');
        return ring === 0 ? 12 : ring === 1 ? 9 : 6;
      },
      'font-weight': (ele) => ele.data('ring') === 0 ? 'bold' : 'normal',
      'color': '#e0e0e0',
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 5,
      'text-wrap': 'ellipsis',
      'text-max-width': (ele) => {
        const ring = ele.data('ring');
        return ring === 0 ? 180 : ring === 1 ? 100 : 50;
      },
      'text-outline-color': '#0a0a0f',
      'text-outline-width': 1.5,
      'opacity': (ele) => ele.data('ring') === 2 ? 0.5 : 1,
      'border-width': (ele) => {
        if (ele.data('ring') === 0) return 4;
        return ele.data('ring') === 1 ? 2 : 0;
      },
      'border-color': (ele) => {
        if (ele.data('ring') === 0) return COLORS.accent;
        return categoryColor(ele.data('category'));
      },
      'border-opacity': 0.8,
      'overlay-opacity': 0,
    })
    .selector('edge')
    .style({
      'line-color': (ele) => {
        const p = ele.data('polarity');
        return p === 1 ? COLORS.positive : p === -1 ? COLORS.negative : COLORS.neutral;
      },
      'target-arrow-color': (ele) => {
        const p = ele.data('polarity');
        return p === 1 ? COLORS.positive : p === -1 ? COLORS.negative : COLORS.neutral;
      },
      'width': (ele) => Math.max(1, (ele.data('weight') || 0.5) * 4),
      'opacity': 0.5,
      'curve-style': 'bezier',
      'target-arrow-shape': 'triangle',
      'arrow-scale': 0.6,
      'label': (ele) => `${ele.data('edgeType')} ${ele.data('weight')}`,
      'font-size': 7,
      'color': 'rgba(255,255,255,0.3)',
      'text-rotation': 'autorotate',
      'text-outline-color': '#0a0a0f',
      'text-outline-width': 1,
      'line-style': (ele) => {
        const d = ele.data('delay');
        return d === 'IMMEDIATE' ? 'solid' : 'dashed';
      },
      'line-dash-pattern': (ele) => {
        const d = ele.data('delay');
        switch (d) {
          case 'SHORT_TERM': return [8, 4];
          case 'MEDIUM_TERM': return [12, 6];
          case 'LONG_TERM': return [4, 4];
          default: return [1, 0];
        }
      },
    })
    .update();
}

function _runConcentricLayout(focalId) {
  _cy.layout({
    name: 'concentric',
    animate: false,
    fit: true,
    padding: 50,
    startAngle: -Math.PI / 2,
    concentric: (node) => {
      const ring = node.data('ring');
      return ring === 0 ? 3 : ring === 1 ? 2 : 1;
    },
    levelWidth: () => 1,
    minNodeSpacing: 30,
  }).run();
}

function _wireEvents(focalId) {
  // Click ring 1 neighbor to walk
  _cy.on('tap', 'node', (evt) => {
    const node = evt.target;
    const nodeId = node.data('id');
    const ring = node.data('ring');

    if (ring === 1) {
      walkTo(nodeId);
    } else if (ring === 2) {
      walkTo(nodeId);
    }
    // Ring 0 (focal) — already selected
  });

  // Background click
  _cy.on('tap', (evt) => {
    if (evt.target === _cy) {
      // Don't deselect in street view — focal is always selected
    }
  });

  // Edge hover tooltip
  let tooltipEl = document.querySelector('.cy-tooltip');
  if (!tooltipEl) {
    tooltipEl = document.createElement('div');
    tooltipEl.className = 'cy-tooltip';
    tooltipEl.style.display = 'none';
    document.body.appendChild(tooltipEl);
  }

  _cy.on('mouseover', 'edge', (evt) => {
    const edge = evt.target;
    const d = edge.data();
    const pos = evt.renderedPosition;

    tooltipEl.innerHTML = `
      <div class="tt-row"><span class="tt-label">Type</span><span class="tt-value">${d.edgeType}</span></div>
      <div class="tt-row"><span class="tt-label">Weight</span><span class="tt-value">${d.weight}</span></div>
      <div class="tt-row"><span class="tt-label">Polarity</span><span class="tt-value">${d.polarity > 0 ? '+1' : d.polarity < 0 ? '-1' : '0'}</span></div>
      <div class="tt-row"><span class="tt-label">Delay</span><span class="tt-value">${d.delay}</span></div>
      ${d.description ? `<div class="tt-row"><span class="tt-label">Desc</span><span class="tt-value">${d.description}</span></div>` : ''}
    `;

    const cyRect = _cy.container().getBoundingClientRect();
    tooltipEl.style.left = (cyRect.left + pos.x + 12) + 'px';
    tooltipEl.style.top = (cyRect.top + pos.y - 10) + 'px';
    tooltipEl.style.display = 'block';
  });

  _cy.on('mouseout', 'edge', () => {
    tooltipEl.style.display = 'none';
  });
}

function _renderHierarchyPath(nodeId) {
  const path = getCategoryPath(nodeId);
  const panel = document.getElementById('detail-panel');
  if (!panel) return;

  // The hierarchy path will be rendered as part of the detail panel by app.js
  // Store it for access
  _cy._hierarchyPath = path;
}

function _updateBreadcrumbs() {
  const container = document.getElementById('breadcrumbs');
  if (!container) return;

  container.innerHTML = '';

  const allCrumbs = [..._breadcrumbs];
  if (_focalNode) allCrumbs.push(_focalNode);

  for (let i = 0; i < allCrumbs.length; i++) {
    const crumbId = allCrumbs[i];
    const isActive = i === allCrumbs.length - 1;

    if (i > 0) {
      const sep = document.createElement('span');
      sep.className = 'breadcrumb-sep';
      sep.textContent = '\u203A';
      container.appendChild(sep);
    }

    const pill = document.createElement('span');
    pill.className = `breadcrumb-pill${isActive ? ' active' : ''}`;
    pill.textContent = formatNodeLabel(crumbId, _graphData);
    pill.title = crumbId;

    if (!isActive) {
      pill.addEventListener('click', () => {
        // Jump back: remove everything after this crumb
        const idx = _breadcrumbs.indexOf(crumbId);
        if (idx >= 0) {
          _breadcrumbs = _breadcrumbs.slice(0, idx);
        }
        _focalNode = crumbId;
        _rebuildView(crumbId, false);
        _updateBreadcrumbs();
        window.location.hash = `street/${crumbId}`;
      });
    }

    container.appendChild(pill);
  }
}

function _clearBreadcrumbs() {
  _breadcrumbs = [];
  const container = document.getElementById('breadcrumbs');
  if (container) container.innerHTML = '';
}
