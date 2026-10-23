import React from 'react';
import Dropzone from './Dropzone';
import PatternPresets from './PatternPresets';
import CalibrationControls from './CalibrationControls';
import ModelSelector from './ModelSelector';
import InspectButton from './InspectButton';
import './LeftPanel.css';

export default function LeftPanel({ width, onCollapse }) {
  return (
    <aside className="left-panel" style={width ? { width: `${width}px` } : undefined}>
      {/* 1. PCB Image Source */}
      <div className="left-panel-section">
        <div className="section-header-row">
          <div className="section-title-label">1. PCB IMAGE SOURCE</div>
          {onCollapse && (
            <button
              type="button"
              className="btn-panel-collapse"
              onClick={onCollapse}
              title="Collapse Left Sidebar to boundary dock"
              aria-label="Collapse Left Sidebar"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="13" height="13">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
          )}
        </div>
        <Dropzone />
      </div>

      {/* 2. Target Defect Patterns */}
      <div className="left-panel-section">
        <div className="section-title-label">2. TARGET DEFECT PATTERNS</div>
        <PatternPresets />
      </div>

      {/* 3. Optical Calibration */}
      <div className="left-panel-section">
        <div className="section-title-label">3. OPTICAL CALIBRATION</div>
        <CalibrationControls />
      </div>

      {/* 4. Detection Model */}
      <div className="left-panel-section">
        <div className="section-title-label">4. DETECTION MODEL</div>
        <ModelSelector />
        <InspectButton />
      </div>
    </aside>
  );
}
