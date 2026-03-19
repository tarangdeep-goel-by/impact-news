// theme.js — Color scheme, node/edge style generators

export const COLORS = {
  bg: '#0a0a0f',
  text: '#e0e0e0',
  dimmed: 'rgba(255,255,255,0.15)',
  accent: '#FFD700',
  accentDim: 'rgba(255,215,0,0.3)',
  positive: '#4CAF50',
  negative: '#EF5350',
  neutral: '#666',
  panel: '#12121a',
  panelBorder: 'rgba(255,255,255,0.08)',
};

// Category colors from the data; fallback
const CATEGORY_COLORS = {
  t1: '#4FC3F7',
  t2: '#7986CB',
  t3: '#4DD0E1',
  t4: '#90A4AE',
  t5: '#80CBC4',
  i1: '#66BB6A',
  i2: '#EC407A',
  i3: '#26C6DA',
  i4: '#AB47BC',
  i5: '#42A5F5',
  i6: '#EF5350',
  i7: '#FFA726',
  i8: '#FF7043',
  i9: '#26A69A',
  i10: '#7E57C2',
  i11: '#78909C',
};

let _categoryData = null;

/**
 * Provide the categories dict from graph data so colors can be looked up dynamically.
 */
export function setCategoryData(categories) {
  _categoryData = categories;
}

/**
 * Return hex color for a category ID (case-insensitive).
 */
export function categoryColor(catId) {
  const key = (catId || '').toLowerCase();
  if (_categoryData && _categoryData[key]) return _categoryData[key].color;
  return CATEGORY_COLORS[key] || '#888';
}

/**
 * Delay → dash pattern
 */
function delayDash(delay) {
  switch (delay) {
    case 'IMMEDIATE': return 'solid';
    case 'SHORT_TERM': return '8 4';
    case 'MEDIUM_TERM': return '12 6';
    case 'LONG_TERM': return '4 4';
    default: return 'solid';
  }
}

/**
 * Returns Cytoscape style properties for a node.
 */
export function nodeStyle(category, level, isCategory) {
  const color = categoryColor(category);
  const size = level === 1 ? 50 : (level === 2 || isCategory) ? 30 : 15;

  const base = {
    'background-color': color,
    'width': size,
    'height': size,
    'label': 'data(label)',
    'font-size': level === 1 ? 10 : level === 2 ? 8 : 6,
    'color': '#e0e0e0',
    'text-valign': 'bottom',
    'text-halign': 'center',
    'text-margin-y': 4,
    'text-wrap': 'ellipsis',
    'text-max-width': size * 3,
    'border-width': 0,
    'border-color': color,
    'overlay-opacity': 0,
    'text-outline-color': '#0a0a0f',
    'text-outline-width': 1.5,
  };

  // Category nodes get glow border
  if (isCategory || level <= 2) {
    base['border-width'] = 2;
    base['border-opacity'] = 0.6;
    base['border-color'] = color;
  }

  // L1 nodes are extra prominent
  if (level === 1) {
    base['border-width'] = 3;
    base['font-weight'] = 'bold';
    base['font-size'] = 11;
    base['text-outline-width'] = 2;
  }

  return base;
}

/**
 * Returns Cytoscape style properties for an edge.
 */
export function edgeStyle(type, weight, polarity, delay) {
  const color = polarity === 1 ? COLORS.positive
    : polarity === -1 ? COLORS.negative
    : COLORS.neutral;

  const dash = delayDash(delay);
  const w = Math.max(1, (weight || 0.5) * 4);

  return {
    'line-color': color,
    'target-arrow-color': color,
    'width': w,
    'opacity': 0.5,
    'curve-style': 'bezier',
    'target-arrow-shape': 'triangle',
    'arrow-scale': 0.6,
    'line-style': dash === 'solid' ? 'solid' : 'dashed',
    'line-dash-pattern': dash === 'solid' ? undefined : dash.split(' ').map(Number),
    'line-dash-offset': 0,
  };
}
