/**
 * Defect categories, color mapping, and pattern filters
 */

export const TARGET_PATTERN_MAP = {
  all_defects_panel: {
    name: 'All Defects (Full Inspection)',
    classes: ['mouse_bite', 'spur', 'missing_hole', 'short', 'open_circuit', 'spurious_copper'],
    severity: 'CRITICAL',
    description: 'Full concurrent scan across all 6 IPC defect classes.',
  },
  critical_dual_fault: {
    name: 'Critical Electrical Faults',
    classes: ['short', 'open_circuit'],
    severity: 'CRITICAL',
    description: 'Isolate and highlight Shorts & Open Circuit trace breaks.',
  },
  structural_geometric: {
    name: 'Structural Geometry Flaws',
    classes: ['missing_hole', 'mouse_bite', 'spur'],
    severity: 'MAJOR',
    description: 'Isolate via drill hole flaws, edge bites, and copper whiskers.',
  },
  copper_isolation: {
    name: 'Copper & Trace Anomalies',
    classes: ['short', 'spur', 'spurious_copper'],
    severity: 'CRITICAL',
    description: 'Isolate stray etched copper, bridging, and whiskers.',
  },
  short: {
    name: 'Short Circuit (Trace Bridge)',
    classes: ['short'],
    severity: 'CRITICAL',
    description: 'Isolate and inspect conductor-to-conductor short circuit bridges.',
  },
  open_circuit: {
    name: 'Open Circuit (Broken Trace)',
    classes: ['open_circuit'],
    severity: 'CRITICAL',
    description: 'Isolate and inspect trace breaks and conductivity discontinuities.',
  },
  missing_hole: {
    name: 'Missing Hole (Via Fault)',
    classes: ['missing_hole'],
    severity: 'MAJOR',
    description: 'Isolate and inspect missing or blocked via drill holes.',
  },
  mouse_bite: {
    name: 'Mouse Bite (Edge Erosion)',
    classes: ['mouse_bite'],
    severity: 'MINOR',
    description: 'Isolate and inspect conductor edge tearing and copper nibbling.',
  },
  spur: {
    name: 'Spur (Copper Whisker)',
    classes: ['spur'],
    severity: 'MINOR',
    description: 'Isolate and inspect copper whiskers and narrow trace protrusions.',
  },
  spurious_copper: {
    name: 'Spurious Copper (Stray Etch)',
    classes: ['spurious_copper'],
    severity: 'MINOR',
    description: 'Isolate and inspect isolated stray etched copper residues.',
  },
};

export const CLASS_COLORS = {
  short: '#EA4335',
  open_circuit: '#EA4335',
  missing_hole: '#FBBC04',
  spur: '#1A73E8',
  spurious_copper: '#FB8C00',
  mouse_bite: '#5E35B1',
  multi: '#188038',
};
