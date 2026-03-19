// data.js — Graph data loading and Cytoscape element building

let _graphData = null;
let _nodeMap = {};
let _edgeIndex = {}; // nodeId -> [edges]
let _lastAncestorMap = {};

/**
 * Fetch and parse graph.json.
 */
export async function loadGraph() {
  const resp = await fetch('data/graph.json');
  if (!resp.ok) throw new Error(`Failed to load graph data: ${resp.status}`);
  _graphData = await resp.json();

  // Build lookup maps
  _nodeMap = {};
  _edgeIndex = {};
  for (const n of _graphData.nodes) {
    _nodeMap[n.id] = n;
  }
  for (const e of _graphData.edges) {
    if (!_edgeIndex[e.source]) _edgeIndex[e.source] = [];
    if (!_edgeIndex[e.target]) _edgeIndex[e.target] = [];
    _edgeIndex[e.source].push(e);
    _edgeIndex[e.target].push(e);
  }

  return _graphData;
}

/**
 * Format a node ID as a display label.
 */
export function formatNodeLabel(id, graphData) {
  // For L1 category nodes, use the category name
  if (graphData && graphData.categories) {
    const lower = id.toLowerCase();
    if (graphData.categories[lower]) {
      return graphData.categories[lower].name;
    }
  }
  // Otherwise: replace _ with space, title case
  return id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Build Cytoscape elements from graphData.
 *
 * Options:
 *   showLeaves:      bool (default false) — include L3+ leaf nodes
 *   structuralEdges: bool (default false) — include CONTAINS/IS_A edges
 *   onlyBridges:     bool (default true)  — only cross-category causal edges
 *   expandedL2s:     Set   — which L2 nodes are expanded (show their children)
 */
export function buildElements(graphData, options = {}) {
  const {
    showLeaves = false,
    structuralEdges = false,
    onlyBridges = true,
    expandedL2s = new Set(),
  } = options;

  const elements = [];
  const includedNodeIds = new Set();

  // Determine which nodes to include
  for (const node of graphData.nodes) {
    const level = node.level || 99;
    const cat = (node.category || '').toLowerCase();

    // Always include L1 and L2
    if (level <= 2 || node.is_category) {
      includedNodeIds.add(node.id);
      continue;
    }

    // Include leaves if showLeaves or if their L2 parent is expanded
    if (showLeaves) {
      includedNodeIds.add(node.id);
    } else if (node.parent && expandedL2s.has(node.parent)) {
      includedNodeIds.add(node.id);
    }
  }

  // Build node elements
  for (const node of graphData.nodes) {
    if (!includedNodeIds.has(node.id)) continue;

    const level = node.level || 99;
    const cat = (node.category || '').toLowerCase();

    const data = {
      id: node.id,
      label: formatNodeLabel(node.id, graphData),
      category: cat,
      level: level,
      isCategory: !!node.is_category,
      port: !!node.port,
      portal: !!node.portal,
      aliases: node.aliases || [],
      degree: node.degree || { in: 0, out: 0, causal_out: 0 },
    };

    // No compound nesting — CONTAINS edges handle clustering via force layout

    elements.push({ group: 'nodes', data });
  }

  // Build edge elements
  const addedEdges = new Set();

  for (const edge of graphData.edges) {
    // Both endpoints must be included
    if (!includedNodeIds.has(edge.source) || !includedNodeIds.has(edge.target)) continue;

    // Skip structural edges unless requested
    if (!structuralEdges && edge.is_structural) continue;
    if (!structuralEdges && (edge.type === 'CONTAINS' || edge.type === 'IS_A')) continue;

    // If onlyBridges, only show cross-category edges
    if (onlyBridges) {
      const srcNode = _nodeMap[edge.source];
      const tgtNode = _nodeMap[edge.target];
      if (srcNode && tgtNode) {
        const srcCat = (srcNode.category || '').toLowerCase();
        const tgtCat = (tgtNode.category || '').toLowerCase();
        if (srcCat === tgtCat) continue;
      }
    }

    const edgeId = edge.id || `${edge.source}->${edge.target}`;
    if (addedEdges.has(edgeId)) continue;
    addedEdges.add(edgeId);

    elements.push({
      group: 'edges',
      data: {
        id: edgeId,
        source: edge.source,
        target: edge.target,
        edgeType: edge.type,
        weight: edge.weight || 0.5,
        polarity: edge.polarity || 0,
        delay: edge.delay || 'IMMEDIATE',
        description: edge.description || '',
        isStructural: !!edge.is_structural,
      },
    });
  }

  return elements;
}

/**
 * Build elements for street view centered on a focal node.
 * Returns { elements, ring1, ring2 }
 */
export function buildStreetElements(graphData, focalId) {
  const focalNode = _nodeMap[focalId];
  if (!focalNode) return { elements: [], ring1: [], ring2: [] };

  const elements = [];
  const ring1 = new Set();
  const ring2 = new Set();
  const includedEdges = new Set();

  // Get all direct edges
  const focalEdges = _edgeIndex[focalId] || [];

  // Ring 1: immediate neighbors
  for (const edge of focalEdges) {
    if (edge.is_structural || edge.type === 'CONTAINS' || edge.type === 'IS_A') continue;
    const neighbor = edge.source === focalId ? edge.target : edge.source;
    ring1.add(neighbor);
    includedEdges.add(edge.id || `${edge.source}->${edge.target}`);
  }

  // Ring 2: 2-hop neighbors
  for (const r1Id of ring1) {
    const r1Edges = _edgeIndex[r1Id] || [];
    for (const edge of r1Edges) {
      if (edge.is_structural || edge.type === 'CONTAINS' || edge.type === 'IS_A') continue;
      const neighbor = edge.source === r1Id ? edge.target : edge.source;
      if (neighbor !== focalId && !ring1.has(neighbor)) {
        ring2.add(neighbor);
        includedEdges.add(edge.id || `${edge.source}->${edge.target}`);
      }
    }
  }

  // Add focal node
  const fCat = (focalNode.category || '').toLowerCase();
  elements.push({
    group: 'nodes',
    data: {
      id: focalNode.id,
      label: formatNodeLabel(focalNode.id, graphData),
      category: fCat,
      level: focalNode.level || 1,
      isCategory: !!focalNode.is_category,
      ring: 0,
      aliases: focalNode.aliases || [],
      degree: focalNode.degree || { in: 0, out: 0, causal_out: 0 },
    },
  });

  // Add ring 1 nodes
  for (const nId of ring1) {
    const n = _nodeMap[nId];
    if (!n) continue;
    const cat = (n.category || '').toLowerCase();
    elements.push({
      group: 'nodes',
      data: {
        id: n.id,
        label: formatNodeLabel(n.id, graphData),
        category: cat,
        level: n.level || 3,
        isCategory: !!n.is_category,
        ring: 1,
        aliases: n.aliases || [],
        degree: n.degree || { in: 0, out: 0, causal_out: 0 },
      },
    });
  }

  // Add ring 2 nodes
  for (const nId of ring2) {
    const n = _nodeMap[nId];
    if (!n) continue;
    const cat = (n.category || '').toLowerCase();
    elements.push({
      group: 'nodes',
      data: {
        id: n.id,
        label: formatNodeLabel(n.id, graphData),
        category: cat,
        level: n.level || 3,
        isCategory: !!n.is_category,
        ring: 2,
        aliases: n.aliases || [],
        degree: n.degree || { in: 0, out: 0, causal_out: 0 },
      },
    });
  }

  // Add edges
  const allNodes = new Set([focalId, ...ring1, ...ring2]);
  for (const edge of graphData.edges) {
    if (edge.is_structural || edge.type === 'CONTAINS' || edge.type === 'IS_A') continue;
    if (!allNodes.has(edge.source) || !allNodes.has(edge.target)) continue;

    elements.push({
      group: 'edges',
      data: {
        id: edge.id || `${edge.source}->${edge.target}`,
        source: edge.source,
        target: edge.target,
        edgeType: edge.type,
        weight: edge.weight || 0.5,
        polarity: edge.polarity || 0,
        delay: edge.delay || 'IMMEDIATE',
        description: edge.description || '',
        isStructural: false,
      },
    });
  }

  return { elements, ring1: [...ring1], ring2: [...ring2] };
}

/**
 * Build ancestor map: every node ID → its nearest visible ancestor.
 * Walks up the parent chain until a visible node is found.
 */
function _buildAncestorMap(graphData, visibleIds) {
  const map = {};
  for (const node of graphData.nodes) {
    if (visibleIds.has(node.id)) {
      map[node.id] = node.id;
    } else {
      // Walk up parent chain
      let cur = node.id;
      let found = false;
      while (cur) {
        if (visibleIds.has(cur)) {
          map[node.id] = cur;
          found = true;
          break;
        }
        const n = _nodeMap[cur];
        if (!n || !n.parent) break;
        cur = n.parent;
      }
      if (!found) map[node.id] = null;
    }
  }
  return map;
}

/**
 * Build Cytoscape elements with progressive disclosure.
 *
 * Visible: all L1s (compound parents), all L2s (children of L1),
 * and children of any expanded L2. Hidden nodes' edges are
 * aggregated to their nearest visible ancestor.
 */
export function buildProgressiveElements(graphData, expandedL2s = new Set()) {
  const elements = [];
  const visibleIds = new Set();

  // --- Determine visible nodes ---
  for (const node of graphData.nodes) {
    const level = node.level || 99;

    // L1 nodes — always visible (compound parents)
    if (level === 1) {
      visibleIds.add(node.id);
      continue;
    }

    // L2 nodes (or is_category with level > 1)
    if (level === 2 || (node.is_category && level > 1)) {
      visibleIds.add(node.id);
      continue;
    }

    // Children of expanded L2s
    if (node.parent && expandedL2s.has(node.parent)) {
      visibleIds.add(node.id);
    }
  }

  // --- Build ancestor map ---
  const ancestorMap = _buildAncestorMap(graphData, visibleIds);
  _lastAncestorMap = ancestorMap;

  // --- Build node elements ---
  for (const node of graphData.nodes) {
    if (!visibleIds.has(node.id)) continue;

    const level = node.level || 99;
    const cat = (node.category || '').toLowerCase();

    const data = {
      id: node.id,
      label: formatNodeLabel(node.id, graphData),
      category: cat,
      level: level,
      isCategory: !!node.is_category,
      port: !!node.port,
      portal: !!node.portal,
      aliases: node.aliases || [],
      degree: node.degree || { in: 0, out: 0, causal_out: 0 },
    };

    // Compound parents: L2 nodes nest inside their L1
    if (level === 2 || (node.is_category && level > 1)) {
      const l1 = cat; // category field lowercase = L1 id
      if (l1 && visibleIds.has(l1)) data.parent = l1;
    }

    // Children of expanded L2s nest inside their L2 parent
    if (level > 2 && !node.is_category && node.parent && expandedL2s.has(node.parent) && visibleIds.has(node.parent)) {
      data.parent = node.parent;
    }

    elements.push({ group: 'nodes', data });
  }

  // --- Build edges with aggregation ---
  const addedRealEdges = new Set();
  const aggEdges = {};

  for (const edge of graphData.edges) {
    // Skip structural edges
    if (edge.is_structural || edge.type === 'CONTAINS' || edge.type === 'IS_A') continue;

    const visSource = ancestorMap[edge.source];
    const visTarget = ancestorMap[edge.target];

    // Skip if either endpoint has no visible ancestor
    if (!visSource || !visTarget) continue;

    // Skip if both map to the same compound (internal edge)
    if (visSource === visTarget) continue;

    // Real edge: both endpoints are directly visible
    if (visibleIds.has(edge.source) && visibleIds.has(edge.target) &&
        visSource === edge.source && visTarget === edge.target) {
      const edgeId = edge.id || `${edge.source}->${edge.target}`;
      if (addedRealEdges.has(edgeId)) continue;
      addedRealEdges.add(edgeId);

      elements.push({
        group: 'edges',
        data: {
          id: edgeId,
          source: edge.source,
          target: edge.target,
          edgeType: edge.type,
          weight: edge.weight || 0.5,
          polarity: edge.polarity || 0,
          delay: edge.delay || 'IMMEDIATE',
          description: edge.description || '',
          isStructural: false,
          isAggregated: false,
        },
      });
      continue;
    }

    // Aggregated edge: accumulate into bucket
    const canonKey = visSource < visTarget
      ? `${visSource}->${visTarget}`
      : `${visTarget}->${visSource}`;

    if (!aggEdges[canonKey]) {
      aggEdges[canonKey] = {
        source: visSource < visTarget ? visSource : visTarget,
        target: visSource < visTarget ? visTarget : visSource,
        count: 0,
        maxWeight: 0,
        positiveCount: 0,
        negativeCount: 0,
      };
    }
    aggEdges[canonKey].count++;
    aggEdges[canonKey].maxWeight = Math.max(aggEdges[canonKey].maxWeight, edge.weight || 0.5);
    if ((edge.polarity || 0) > 0) aggEdges[canonKey].positiveCount++;
    if ((edge.polarity || 0) < 0) aggEdges[canonKey].negativeCount++;
  }

  // Emit all aggregated edges
  for (const [key, bucket] of Object.entries(aggEdges)) {
    elements.push({
      group: 'edges',
      data: {
        id: `agg_${bucket.source}->${bucket.target}`,
        source: bucket.source,
        target: bucket.target,
        edgeType: 'AGGREGATED',
        count: bucket.count,
        maxWeight: bucket.maxWeight,
        polarity: bucket.positiveCount > bucket.negativeCount ? 1 : bucket.negativeCount > bucket.positiveCount ? -1 : 0,
        isAggregated: true,
        isStructural: false,
        weight: bucket.maxWeight,
        delay: 'SHORT_TERM',
        description: '',
      },
    });
  }

  return elements;
}

/**
 * Return the ancestor map from the last buildProgressiveElements() call.
 * Maps every node ID → its nearest visible ancestor ID (or null).
 */
export function getAncestorMap() {
  return _lastAncestorMap;
}

/**
 * Build elements for tree view — all nodes with compound nesting,
 * CONTAINS edges visible, intra-category causal edges visible,
 * no cross-category edges.
 */
export function buildTreeElements(graphData) {
  const elements = [];

  // Add ALL nodes with compound parents via parent chain
  for (const node of graphData.nodes) {
    const cat = (node.category || '').toLowerCase();

    const data = {
      id: node.id,
      label: formatNodeLabel(node.id, graphData),
      category: cat,
      level: node.level || 99,
      isCategory: !!node.is_category,
      port: !!node.port,
      portal: !!node.portal,
      aliases: node.aliases || [],
      degree: node.degree || { in: 0, out: 0, causal_out: 0 },
    };

    // Set compound parent from the CONTAINS parent
    if (node.parent) {
      data.parent = node.parent;
    }

    elements.push({ group: 'nodes', data });
  }

  // Add edges
  for (const edge of graphData.edges) {
    const srcNode = _nodeMap[edge.source];
    const tgtNode = _nodeMap[edge.target];
    if (!srcNode || !tgtNode) continue;

    const srcCat = (srcNode.category || '').toLowerCase();
    const tgtCat = (tgtNode.category || '').toLowerCase();

    const isStructural = edge.is_structural || edge.type === 'CONTAINS' || edge.type === 'IS_A';

    // Include: CONTAINS edges (tree structure) + same-category causal edges (lateral)
    if (isStructural) {
      // CONTAINS/IS_A — show as tree backbone
      elements.push({
        group: 'edges',
        data: {
          id: edge.id || `${edge.source}->${edge.target}`,
          source: edge.source,
          target: edge.target,
          edgeType: edge.type,
          weight: edge.weight || 0.5,
          polarity: edge.polarity || 0,
          delay: edge.delay || 'IMMEDIATE',
          description: edge.description || '',
          isStructural: true,
          isAggregated: false,
        },
      });
    } else if (srcCat === tgtCat) {
      // Same-category causal edge (lateral branch)
      elements.push({
        group: 'edges',
        data: {
          id: edge.id || `${edge.source}->${edge.target}`,
          source: edge.source,
          target: edge.target,
          edgeType: edge.type,
          weight: edge.weight || 0.5,
          polarity: edge.polarity || 0,
          delay: edge.delay || 'IMMEDIATE',
          description: edge.description || '',
          isStructural: false,
          isAggregated: false,
        },
      });
    }
    // Skip cross-category causal edges
  }

  return elements;
}

/**
 * Lookup a node by ID.
 */
export function getNodeById(id) {
  return _nodeMap[id] || null;
}

/**
 * Get all edges involving a node.
 */
export function getEdgesFor(nodeId) {
  return (_edgeIndex[nodeId] || []).filter(
    e => !e.is_structural && e.type !== 'CONTAINS' && e.type !== 'IS_A'
  );
}

/**
 * Get the category path for a node by walking up CONTAINS parents.
 * Returns array like ["t3", "oil_and_gas", "crude_oil"].
 */
export function getCategoryPath(nodeId) {
  const path = [nodeId];
  let current = _nodeMap[nodeId];
  const visited = new Set([nodeId]);

  while (current && current.parent && !visited.has(current.parent)) {
    visited.add(current.parent);
    path.unshift(current.parent);
    current = _nodeMap[current.parent];
  }

  // If we haven't reached the L1, add the category
  if (current) {
    const cat = (current.category || '').toLowerCase();
    if (cat && !visited.has(cat)) {
      path.unshift(cat);
    }
  }

  return path;
}

/**
 * Fuzzy search nodes by ID and aliases.
 * Returns array of { id, label, category, matchType } sorted by relevance.
 */
export function searchNodes(query, graphData, maxResults = 10) {
  if (!query || query.length < 1) return [];
  const q = query.toLowerCase();
  const results = [];

  for (const node of graphData.nodes) {
    let score = 0;
    let matchType = '';

    // ID match
    const id = node.id.toLowerCase();
    if (id === q) {
      score = 100;
      matchType = 'exact';
    } else if (id.startsWith(q)) {
      score = 80;
      matchType = 'prefix';
    } else if (id.includes(q)) {
      score = 60;
      matchType = 'contains';
    }

    // Alias match
    if (node.aliases) {
      for (const alias of node.aliases) {
        const a = alias.toLowerCase();
        if (a === q) {
          score = Math.max(score, 95);
          matchType = matchType || 'alias-exact';
        } else if (a.startsWith(q)) {
          score = Math.max(score, 75);
          matchType = matchType || 'alias-prefix';
        } else if (a.includes(q)) {
          score = Math.max(score, 55);
          matchType = matchType || 'alias';
        }
      }
    }

    if (score > 0) {
      results.push({
        id: node.id,
        label: formatNodeLabel(node.id, graphData),
        category: (node.category || '').toLowerCase(),
        matchType,
        score,
      });
    }
  }

  results.sort((a, b) => b.score - a.score);
  return results.slice(0, maxResults);
}
