import React from 'react';
import { useInspection } from '../../context/useInspection';
import './SeveritySummaryGrid.css';

export default function SeveritySummaryGrid() {
  const { summary } = useInspection();

  const cCount = summary.critical_count !== undefined ? summary.critical_count : 4;
  const mCount = summary.major_count !== undefined ? summary.major_count : 2;
  const minCount = summary.minor_count !== undefined ? summary.minor_count : 4;

  return (
    <div className="severity-three-col-grid">
      <div className="severity-col">
        <div className="severity-num critical">{cCount}</div>
        <div className="severity-label">Class 3 (Fatal)</div>
        <div className="severity-sub">Short / Open Circuit</div>
      </div>

      <div className="severity-col">
        <div className="severity-num major">{mCount}</div>
        <div className="severity-label">Class 2 (Major)</div>
        <div className="severity-sub">Via / Hole Discontinuity</div>
      </div>

      <div className="severity-col">
        <div className="severity-num minor">{minCount}</div>
        <div className="severity-label">Class 1 (Minor)</div>
        <div className="severity-sub">Spur / Bite / Residue</div>
      </div>
    </div>
  );
}
