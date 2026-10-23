import React from 'react';
import './SeverityCard.css';

export default function SeverityCard({ count, label, subtitle, type }) {
  return (
    <div className={`severity-card ${type}`}>
      <div className="severity-num">{count}</div>
      <div className="severity-label">{label}</div>
      <div className="severity-sub">{subtitle}</div>
    </div>
  );
}
