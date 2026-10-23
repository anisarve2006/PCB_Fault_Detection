import React from 'react';
import './RightRail.css';

export default function RightRail({ onExpand }) {
  return (
    <aside className="right-boundary-rail" title="Right Sidebar Dock (Click any icon to expand)">
      {/* Top Expand Button */}
      <button
        type="button"
        className="rail-btn rail-expand-btn"
        onClick={onExpand}
        title="Expand Right Sidebar (Ctrl+])"
        aria-label="Expand Right Sidebar"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="16" height="16">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>

      <div className="rail-divider" />

      {/* 1. Verdict Banner */}
      <button
        type="button"
        className="rail-btn"
        onClick={onExpand}
        title="1. Inspection Result & IPC-A-610G Disposition"
        aria-label="1. Inspection Result"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      </button>

      {/* 2. Defect Summary */}
      <button
        type="button"
        className="rail-btn"
        onClick={onExpand}
        title="2. Defect Summary (Fatal, Major, Minor)"
        aria-label="2. Defect Summary"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
          <line x1="18" y1="20" x2="18" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" />
        </svg>
      </button>

      {/* 3. Defect Classes Detected */}
      <button
        type="button"
        className="rail-btn"
        onClick={onExpand}
        title="3. Defect Classes Detected (6/6)"
        aria-label="3. Defect Classes Detected"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
          <polygon points="12 2 2 7 12 12 22 7 12 2" />
          <polyline points="2 17 12 22 22 17" />
          <polyline points="2 12 12 17 22 12" />
        </svg>
      </button>

      {/* 4. Defect Details & Measurements Table */}
      <button
        type="button"
        className="rail-btn"
        onClick={onExpand}
        title="4. Defect Details & Measurements Table"
        aria-label="4. Defect Details Table"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
          <line x1="8" y1="6" x2="21" y2="6" />
          <line x1="8" y1="12" x2="21" y2="12" />
          <line x1="8" y1="18" x2="21" y2="18" />
          <line x1="3" y1="6" x2="3.01" y2="6" />
          <line x1="3" y1="12" x2="3.01" y2="12" />
          <line x1="3" y1="18" x2="3.01" y2="18" />
        </svg>
      </button>
    </aside>
  );
}
