import React from 'react';
import './DefectCard.css';

export default function DefectCard({
  defect,
  index,
  isSelected,
  onSelect,
  onMouseEnter,
  onMouseLeave,
}) {
  const formatClassName = (name) => {
    if (!name) return '';
    return name.replace(/_/g, ' ').toUpperCase();
  };

  return (
    <div
      className={`defect-card ${isSelected ? 'selected' : ''}`}
      style={{ '--defect-color': defect.color || '#16A34A' }}
      onClick={onSelect}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <div className="defect-card-header">
        <div className="defect-card-name">
          <span style={{ color: defect.color, fontSize: '11px' }}>■</span>
          <span>
            #{index + 1} {formatClassName(defect.class_name)}
          </span>
        </div>
        <span className="defect-card-conf">{defect.confidence}% CONF</span>
      </div>

      <div className="defect-diag-box">
        <span className="diag-lbl">{defect.diagnostic.label}:</span>
        <span className="diag-val">{defect.diagnostic.value}</span>
      </div>

      <div className="defect-dims-grid">
        <div className="dim-item">
          <span>W:</span> {defect.physical.width_um} µm ({defect.bbox.width_px}px)
        </div>
        <div className="dim-item">
          <span>H:</span> {defect.physical.height_um} µm ({defect.bbox.height_px}px)
        </div>
        <div className="dim-item">
          <span>Area:</span> {defect.physical.area_um2} µm²
        </div>
        <div className="dim-item">
          <span>Sev:</span> <strong>{defect.severity}</strong>
        </div>
      </div>

      <div className="defect-ipc-rule">IPC RULE: {defect.diagnostic.ipc_rule}</div>
    </div>
  );
}
