import React from 'react';
import './StatusPill.css';

export default function StatusPill({ label, value, dotColor = 'green', title }) {
  return (
    <div className="status-pill" title={title || `${label} ${value}`}>
      {dotColor && <span className={`pill-dot ${dotColor}`} />}
      {label && <span className="pill-label">{label}:</span>}
      <span className="pill-val">{value}</span>
    </div>
  );
}
