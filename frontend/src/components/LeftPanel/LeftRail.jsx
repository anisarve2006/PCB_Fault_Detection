import React from 'react';
import './LeftRail.css';

export default function LeftRail({ onExpand }) {
  return (
    <aside className="left-boundary-rail" title="Left Sidebar Dock (Click any icon to expand)">
      {/* Top Expand Button */}
      <button
        type="button"
        className="rail-btn rail-expand-btn"
        onClick={onExpand}
        title="Expand Left Sidebar (Ctrl+[)"
        aria-label="Expand Left Sidebar"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="16" height="16">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>

      <div className="rail-divider" />

      {/* 1. PCB Source */}
      <button
        type="button"
        className="rail-btn"
        onClick={onExpand}
        title="1. PCB Image Source / Upload"
        aria-label="1. PCB Image Source"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
        </svg>
      </button>

      {/* 2. Target Defect Patterns */}
      <button
        type="button"
        className="rail-btn"
        onClick={onExpand}
        title="2. Target Defect Patterns (IPC-A-610)"
        aria-label="2. Target Defect Patterns"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
          <rect x="3" y="3" width="7" height="7" />
          <rect x="14" y="3" width="7" height="7" />
          <rect x="14" y="14" width="7" height="7" />
          <rect x="3" y="14" width="7" height="7" />
        </svg>
      </button>

      {/* 3. Optical Calibration */}
      <button
        type="button"
        className="rail-btn"
        onClick={onExpand}
        title="3. Optical Calibration & Pitch"
        aria-label="3. Optical Calibration"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
          <line x1="4" y1="21" x2="4" y2="14" />
          <line x1="4" y1="10" x2="4" y2="3" />
          <line x1="12" y1="21" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12" y2="3" />
          <line x1="20" y1="21" x2="20" y2="16" />
          <line x1="20" y1="12" x2="20" y2="3" />
          <line x1="1" y1="14" x2="7" y2="14" />
          <line x1="9" y1="8" x2="15" y2="8" />
          <line x1="17" y1="16" x2="23" y2="16" />
        </svg>
      </button>

      {/* 4. Detection Model */}
      <button
        type="button"
        className="rail-btn"
        onClick={onExpand}
        title="4. YOLO Detection Model & Run Inspection"
        aria-label="4. Detection Model"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
          <rect x="4" y="4" width="16" height="16" rx="0" />
          <rect x="9" y="9" width="6" height="6" />
          <line x1="9" y1="1" x2="9" y2="4" />
          <line x1="15" y1="1" x2="15" y2="4" />
          <line x1="9" y1="20" x2="9" y2="23" />
          <line x1="15" y1="20" x2="15" y2="23" />
          <line x1="20" y1="9" x2="23" y2="9" />
          <line x1="20" y1="14" x2="23" y2="14" />
          <line x1="1" y1="9" x2="4" y2="9" />
          <line x1="1" y1="14" x2="4" y2="14" />
        </svg>
      </button>
    </aside>
  );
}
