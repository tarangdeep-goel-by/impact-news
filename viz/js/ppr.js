// ppr.js — PPR shockwave animation on top-down view

import { getNodeById, getEdgesFor, formatNodeLabel } from './data.js';
import { COLORS, categoryColor } from './theme.js';

let _cy = null;
let _graphData = null;
let _animating = false;
let _animationTimer = null;
let _pprResults = null;

// Callbacks
let _onSelectNode = null;

export function setCallbacks({ onSelectNode }) {
  _onSelectNode = onSelectNode;
}

export function init(cy, graphData) {
  _cy = cy;
  _graphData = graphData;
}

export function activate() {}
export function deactivate() {
  cancelAnimation();
}

/**
 * Check if a node has PPR data available.
 */
export function hasPprData(nodeId) {
  return !!(_graphData.ppr_cache && _graphData.ppr_cache[nodeId]);
}

/**
 * Cancel any running animation.
 */
export function cancelAnimation() {
  if (_animationTimer) {
    clearTimeout(_animationTimer);
    _animationTimer = null;
  }
  _animating = false;
  _pprResults = null;

  // Restore styles
  if (_cy) {
    _cy.batch(() => {
      _cy.elements().removeStyle('opacity background-color border-color border-width');
    });
  }
}

/**
 * Run shockwave animation from a trigger node.
 */
export function runShockwave(triggerId) {
  if (_animating) cancelAnimation();
  _animating = true;

  let results;
  if (_graphData.ppr_cache && _graphData.ppr_cache[triggerId]) {
    results = _graphData.ppr_cache[triggerId];
  } else {
    // Client-side BFS approximation
    results = _approximateBFS(triggerId);
  }

  _pprResults = results;

  // Build lookup: node -> probability, magnitude
  const probMap = {};
  const magMap = {};
  const pathMap = {};
  let maxProb = 0;

  for (const r of results) {
    probMap[r.node] = r.probability;
    magMap[r.node] = r.magnitude || 0;
    pathMap[r.node] = r.path || [];
    if (r.probability > maxProb) maxProb = r.probability;
  }

  // Categorize nodes by hop distance from paths
  const hop1 = new Set();
  const hop2 = new Set();
  const allReached = new Set();

  for (const r of results) {
    allReached.add(r.node);
    const path = r.path || [];
    if (path.length === 2) hop1.add(r.node);
    else if (path.length > 2) hop2.add(r.node);
    // Also add intermediates
    for (let i = 1; i < path.length; i++) {
      allReached.add(path[i]);
      if (i === 1) hop1.add(path[i]);
      else hop2.add(path[i]);
    }
  }

  // Phase 1: Dim everything
  _cy.batch(() => {
    _cy.elements().style('opacity', 0.1);
    // Trigger node white pulse
    const trigNode = _cy.getElementById(triggerId);
    if (trigNode.length) {
      trigNode.style({
        'opacity': 1,
        'background-color': '#ffffff',
        'border-color': '#ffffff',
        'border-width': 4,
      });
    }
  });

  // Phase 2 (T=500ms): Light up hop 1
  _animationTimer = setTimeout(() => {
    _cy.batch(() => {
      for (const nId of hop1) {
        const cyNode = _cy.getElementById(nId);
        if (!cyNode.length) continue;
        const prob = probMap[nId] || 0.01;
        const color = _heatColor(prob, maxProb);
        cyNode.style({
          'opacity': 0.6 + (prob / maxProb) * 0.4,
          'background-color': color,
          'border-color': color,
          'border-width': 2,
        });
      }
      // Light up edges from trigger to hop1
      _cy.edges().forEach(e => {
        const src = e.data('source');
        const tgt = e.data('target');
        if (src === triggerId && hop1.has(tgt) || tgt === triggerId && hop1.has(src)) {
          e.style({ 'opacity': 0.7, 'line-color': '#FF9800', 'target-arrow-color': '#FF9800' });
        }
      });
    });

    // Phase 3 (T=1500ms): Light up hop 2
    _animationTimer = setTimeout(() => {
      _cy.batch(() => {
        for (const nId of hop2) {
          if (hop1.has(nId)) continue; // Already lit
          const cyNode = _cy.getElementById(nId);
          if (!cyNode.length) continue;
          const prob = probMap[nId] || 0.005;
          const color = _heatColor(prob, maxProb);
          cyNode.style({
            'opacity': 0.5 + (prob / maxProb) * 0.5,
            'background-color': color,
            'border-color': color,
            'border-width': 2,
          });
        }
        // Light up relevant edges
        _cy.edges().forEach(e => {
          const src = e.data('source');
          const tgt = e.data('target');
          if ((hop1.has(src) && hop2.has(tgt)) || (hop1.has(tgt) && hop2.has(src))) {
            e.style({ 'opacity': 0.5, 'line-color': '#FFA726', 'target-arrow-color': '#FFA726' });
          }
        });
      });

      // Phase 4 (T=3000ms): Settle
      _animationTimer = setTimeout(() => {
        _animating = false;
        _animationTimer = null;

        // Final heat map
        _cy.batch(() => {
          for (const nId of allReached) {
            const cyNode = _cy.getElementById(nId);
            if (!cyNode.length) continue;
            const prob = probMap[nId] || 0.005;
            const color = _heatColor(prob, maxProb);
            cyNode.style({
              'opacity': 0.6 + (prob / maxProb) * 0.4,
              'background-color': color,
              'border-color': color,
              'border-width': 2,
            });
          }
        });

        // Wire click on lit nodes to show path
        _cy.off('tap.ppr');
        _cy.on('tap.ppr', 'node', (evt) => {
          const nodeId = evt.target.data('id');
          if (allReached.has(nodeId)) {
            _highlightPath(triggerId, nodeId, pathMap[nodeId] || []);
          }
        });

      }, 1500);
    }, 1000);
  }, 500);

  return results;
}

/**
 * Get current PPR results for rendering in detail panel.
 */
export function getPprResults() {
  return _pprResults;
}

/**
 * Highlight a specific path from trigger to target.
 */
function _highlightPath(triggerId, targetId, path) {
  if (!path || path.length < 2) return;

  _cy.batch(() => {
    // Reset edge styles for PPR
    _cy.edges().style({
      'line-color': (ele) => {
        const p = ele.data('polarity');
        return p === 1 ? COLORS.positive : p === -1 ? COLORS.negative : COLORS.neutral;
      },
      'target-arrow-color': (ele) => {
        const p = ele.data('polarity');
        return p === 1 ? COLORS.positive : p === -1 ? COLORS.negative : COLORS.neutral;
      },
      'width': (ele) => Math.max(1, (ele.data('weight') || 0.5) * 4),
      'opacity': 0.15,
    });

    // Highlight path edges in gold
    for (let i = 0; i < path.length - 1; i++) {
      const src = path[i];
      const tgt = path[i + 1];
      // Try both directions
      const edgeId1 = `${src}->${tgt}`;
      const edgeId2 = `${tgt}->${src}`;
      let edge = _cy.getElementById(edgeId1);
      if (!edge.length) edge = _cy.getElementById(edgeId2);
      if (edge.length) {
        edge.style({
          'line-color': COLORS.accent,
          'target-arrow-color': COLORS.accent,
          'width': 4,
          'opacity': 1,
        });
      }
    }

    // Highlight path nodes
    for (const nId of path) {
      const cyNode = _cy.getElementById(nId);
      if (cyNode.length) {
        cyNode.style({ 'opacity': 1, 'border-color': COLORS.accent, 'border-width': 3 });
      }
    }
  });
}

/**
 * Map a probability to a heat color.
 * highest = white, high = red, medium = orange, low = yellow
 */
function _heatColor(prob, maxProb) {
  const ratio = maxProb > 0 ? prob / maxProb : 0;
  if (ratio > 0.8) return '#ffffff';
  if (ratio > 0.5) return '#EF5350';
  if (ratio > 0.2) return '#FF9800';
  return '#FFD54F';
}

/**
 * Approximate BFS for nodes without PPR cache.
 * Start from trigger with score=1.0.
 * Each hop: multiply by edge weight, decay by 0.5.
 */
function _approximateBFS(triggerId) {
  const results = [];
  const visited = new Set([triggerId]);
  const queue = [{ node: triggerId, score: 1.0, path: [triggerId], hops: 0 }];
  const maxHops = 3;

  while (queue.length > 0) {
    const { node, score, path, hops } = queue.shift();
    if (hops >= maxHops) continue;

    const edges = getEdgesFor(node);
    for (const edge of edges) {
      const neighbor = edge.source === node ? edge.target : edge.source;
      if (visited.has(neighbor)) continue;
      visited.add(neighbor);

      const newScore = score * (edge.weight || 0.5) * 0.5;
      if (newScore < 0.001) continue;

      const newPath = [...path, neighbor];
      results.push({
        node: neighbor,
        probability: newScore,
        magnitude: newScore * (edge.weight || 0.5),
        path: newPath,
        approximate: true,
      });

      queue.push({ node: neighbor, score: newScore, path: newPath, hops: hops + 1 });
    }
  }

  // Sort by probability desc
  results.sort((a, b) => b.probability - a.probability);
  return results.slice(0, 50);
}

/**
 * Render the top-20 impacted list in the detail panel.
 * Returns HTML string.
 */
export function renderPprList(results, graphData) {
  if (!results || results.length === 0) return '';

  const top20 = results.slice(0, 20);
  const isApprox = top20[0] && top20[0].approximate;

  let html = `<div class="detail-section">`;
  html += `<div class="detail-section-title">Top ${Math.min(20, top20.length)} Impacted${isApprox ? ' (approximate)' : ''}</div>`;
  html += `<ul class="ppr-list">`;

  for (let i = 0; i < top20.length; i++) {
    const r = top20[i];
    html += `<li class="ppr-item" data-node="${r.node}">`;
    html += `<span class="ppr-rank">${i + 1}</span>`;
    html += `<span class="ppr-node-name">${formatNodeLabel(r.node, graphData)}</span>`;
    html += `<span class="ppr-prob">${r.probability.toFixed(3)}</span>`;
    html += `<span class="ppr-mag">${(r.magnitude || 0).toFixed(2)}</span>`;
    html += `</li>`;
  }

  html += `</ul></div>`;
  return html;
}
