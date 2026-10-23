import React from 'react';
import { useInspection } from '../../context/useInspection';
import './DefectListHeader.css';

export default function DefectListHeader() {
  const { detections, exportReport, exportCsv } = useInspection();

  return (
    <div className="defects-list-header">
      <div className="title-with-badge">
        <span>METROLOGY LEDGER</span>
        <span className="badge-count">{detections.length} RECORDS</span>
      </div>
      <div style={{ display: 'flex', gap: '4px' }}>
        <button
          type="button"
          className="btn-export-small"
          onClick={exportCsv}
          title="Export CSV telemetry for statistical process control"
        >
          CSV
        </button>
        <button
          type="button"
          className="btn-export-small"
          onClick={exportReport}
          title="Export JSON inspection report"
        >
          JSON
        </button>
      </div>
    </div>
  );
}
