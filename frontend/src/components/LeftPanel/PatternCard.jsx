import React from 'react';
import './PatternCard.css';

export default function PatternCard({ name, severity, description, isMulti, isActive, onClick }) {
  const getSeverityColor = (sev) => {
    if (sev === 'CRITICAL') return '#DC2626';
    if (sev === 'MAJOR') return '#D97706';
    return '#16A34A';
  };

  const tagText = isMulti ? 'MULTI-DEFECT' : severity;
  const tagClass = isMulti ? 'critical' : severity.toLowerCase();

  return (
    <div
      className={`pattern-card ${isActive ? 'active' : ''}`}
      style={{ '--card-accent': getSeverityColor(severity) }}
      onClick={onClick}
    >
      <div className="pattern-header">
        <span className="pattern-name">{name}</span>
        <span className={`pattern-tag ${tagClass}`}>{tagText}</span>
      </div>
      <div className="pattern-desc">{description}</div>
    </div>
  );
}
