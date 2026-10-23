import React from 'react';
import { useInspection } from '../../context/useInspection';
import './PatternPresets.css';

const PRESET_ITEMS = [
  {
    id: 'all_defects_panel',
    title: 'Full Multi-Defect Panel',
    subtitle: 'Short, Open, Missing Hole, Spur, Mouse Bite, Copper',
  },
  {
    id: 'critical_dual_fault',
    title: 'Dual Critical Faults',
    subtitle: 'Conductor bridge and open circuit (short)',
  },
  {
    id: 'structural_geometric',
    title: 'Multi-Defect Geometry',
    subtitle: 'Via hole, edge mouse bite, copper spur',
  },
  {
    id: 'copper_isolation',
    title: 'Conductor & Copper Cluster',
    subtitle: 'Etching/isolation failures, short circuit, spur',
  },
];

export default function PatternPresets() {
  const { activeTargetPattern, selectSample } = useInspection();

  return (
    <div className="pattern-presets-list">
      {PRESET_ITEMS.map((item) => {
        const isChecked = activeTargetPattern === item.id;
        return (
          <div
            key={item.id}
            className={`pattern-checkbox-row ${isChecked ? 'is-checked' : ''}`}
            onClick={() => selectSample(item.id, item.title)}
            role="checkbox"
            aria-checked={isChecked}
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === ' ' || e.key === 'Enter') {
                e.preventDefault();
                selectSample(item.id, item.title);
              }
            }}
          >
            <div className={`square-checkbox ${isChecked ? 'checked' : ''}`}>
              {isChecked && (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" width="12" height="12">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              )}
            </div>
            <div className="pattern-row-text">
              <div className="pattern-row-title">{item.title}</div>
              <div className="pattern-row-subtitle">{item.subtitle}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
