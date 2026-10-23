import React from 'react';
import './CanvasPlaceholder.css';

export default function CanvasPlaceholder() {
  return (
    <div className="canvas-placeholder">
      <div className="placeholder-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="30" height="30">
          <circle cx="12" cy="12" r="9" strokeDasharray="3 3" />
          <line x1="12" y1="2" x2="12" y2="22" />
          <line x1="2" y1="12" x2="22" y2="12" />
          <circle cx="12" cy="12" r="2" fill="currentColor" />
        </svg>
      </div>
      <div className="placeholder-title">AOI OPTICAL STAGE · IDLE</div>
      <div className="placeholder-sub">
        Awaiting PCB frame acquisition. Ingest local board image (Section 01) or load reference IPC-A-610 sample (Section 02).
      </div>
    </div>
  );
}
