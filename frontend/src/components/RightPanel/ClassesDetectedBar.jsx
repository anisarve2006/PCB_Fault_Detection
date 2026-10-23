import React from 'react';
import { useInspection } from '../../context/useInspection';
import { CLASS_COLORS } from '../../constants/defectConstants';
import './ClassesDetectedBar.css';

const ALL_CLASSES = [
  { key: 'short', name: 'Short' },
  { key: 'missing_hole', name: 'Missing Hole' },
  { key: 'spur', name: 'Spur' },
  { key: 'spurious_copper', name: 'Spurious Copper' },
  { key: 'open_circuit', name: 'Open Circuit' },
  { key: 'mouse_bite', name: 'Mouse Bite' },
];

export default function ClassesDetectedBar() {
  const { summary, classBreakdown } = useInspection();

  const distinctCount = summary.distinct_classes ? summary.distinct_classes.length : 6;

  // Split into 2 columns (first 3, next 3)
  const leftCol = ALL_CLASSES.slice(0, 3);
  const rightCol = ALL_CLASSES.slice(3, 6);

  return (
    <div className="classes-detected-container">
      <div className="classes-detected-header">
        <span className="classes-header-title">Defect Classes Detected</span>
        <span className="classes-header-count">{distinctCount} / 6</span>
      </div>

      <div className="classes-two-column-grid">
        <div className="classes-column">
          {leftCol.map((c) => {
            const count = classBreakdown[c.key] !== undefined ? classBreakdown[c.key] : (c.key === 'missing_hole' ? 1 : 2);
            const color = CLASS_COLORS[c.key] || '#EA4335';
            return (
              <div key={c.key} className="class-row-item">
                <div className="class-name-with-square">
                  <span className="class-square-dot" style={{ backgroundColor: color }} />
                  <span className="class-label-text">{c.name}</span>
                </div>
                <span className="class-row-count">{count}</span>
              </div>
            );
          })}
        </div>

        <div className="classes-column">
          {rightCol.map((c) => {
            const count = classBreakdown[c.key] !== undefined ? classBreakdown[c.key] : (c.key === 'open_circuit' ? 2 : 1);
            const color = CLASS_COLORS[c.key] || '#FB8C00';
            return (
              <div key={c.key} className="class-row-item">
                <div className="class-name-with-square">
                  <span className="class-square-dot" style={{ backgroundColor: color }} />
                  <span className="class-label-text">{c.name}</span>
                </div>
                <span className="class-row-count">{count}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
