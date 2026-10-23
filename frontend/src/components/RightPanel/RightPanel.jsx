import React from 'react';
import VerdictBanner from './VerdictBanner';
import SeveritySummaryGrid from './SeveritySummaryGrid';
import ClassesDetectedBar from './ClassesDetectedBar';
import DefectsList from './DefectsList';
import './RightPanel.css';

export default function RightPanel({ width, onCollapse }) {
  return (
    <aside className="right-panel" style={width ? { width: `${width}px` } : undefined}>
      {/* 1. Inspection Result */}
      <div className="right-panel-section">
        <div className="right-section-header-row">
          <div className="right-section-title">Inspection Result</div>
          {onCollapse && (
            <button
              type="button"
              className="btn-panel-collapse"
              onClick={onCollapse}
              title="Collapse Right Sidebar to boundary dock"
              aria-label="Collapse Right Sidebar"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="13" height="13">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          )}
        </div>
        <VerdictBanner />
      </div>

      {/* 2. Defect Summary */}
      <div className="right-panel-section">
        <div className="right-section-title">Defect Summary</div>
        <SeveritySummaryGrid />
      </div>

      {/* 3. Defect Classes Detected */}
      <div className="right-panel-section">
        <ClassesDetectedBar />
      </div>

      {/* 4. Defect Details & Measurements */}
      <div className="right-panel-section defects-table-section">
        <DefectsList />
      </div>
    </aside>
  );
}
