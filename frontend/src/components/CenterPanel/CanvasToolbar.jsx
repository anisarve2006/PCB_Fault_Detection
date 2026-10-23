import React from 'react';
import { useInspection } from '../../context/useInspection';
import './CanvasToolbar.css';

const PRESET_OPTIONS = [
  { id: 'all_defects_panel', label: 'Full Multi-Defect Panel' },
  { id: 'critical_dual_fault', label: 'Dual Critical Faults' },
  { id: 'structural_geometric', label: 'Multi-Defect Geometry' },
  { id: 'copper_isolation', label: 'Conductor & Copper Cluster' },
];

export default function CanvasToolbar() {
  const {
    zoom,
    zoomIn,
    zoomOut,
    resetZoom,
    showBoxes,
    setShowBoxes,
    showDimensions,
    setShowDimensions,
    showCrosshair,
    setShowCrosshair,
    detections,
    selectedDefectIndex,
    nextDefect,
    prevDefect,
    activeTargetPattern,
    selectSample,
  } = useInspection();

  const totalDefects = detections.length;
  const currentStep = selectedDefectIndex >= 0 ? selectedDefectIndex + 1 : (totalDefects > 0 ? 1 : 0);

  return (
    <div className="canvas-toolbar-container">
      <div className="canvas-toolbar-title">PCB Inspection View</div>
      <div className="canvas-toolbar-controls">
        {/* Sample Preset Dropdown */}
        <select
          className="toolbar-select"
          value={activeTargetPattern}
          onChange={(e) => selectSample(e.target.value)}
          aria-label="Inspection Pattern Preset"
        >
          {PRESET_OPTIONS.map((opt) => (
            <option key={opt.id} value={opt.id}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Defect Stepper Navigator: [ < ] 1 / 9 [ > ] */}
        <div className="stepper-group">
          <button
            type="button"
            className="stepper-btn"
            onClick={prevDefect}
            disabled={totalDefects === 0}
            title="Previous defect [K or ←]"
          >
            &lt;
          </button>
          <span className="stepper-display">
            {totalDefects > 0 ? `${currentStep} / ${totalDefects}` : '0 / 0'}
          </span>
          <button
            type="button"
            className="stepper-btn"
            onClick={nextDefect}
            disabled={totalDefects === 0}
            title="Next defect [J or →]"
          >
            &gt;
          </button>
        </div>

        {/* Zoom Controls: [ - ] 41% [ + ] [ Fit ] */}
        <div className="zoom-group">
          <button
            type="button"
            className="zoom-btn"
            onClick={zoomOut}
            title="Zoom Out (-)"
          >
            -
          </button>
          <span className="zoom-display">{Math.round(zoom * 100)}%</span>
          <button
            type="button"
            className="zoom-btn"
            onClick={zoomIn}
            title="Zoom In (+)"
          >
            +
          </button>
          <button
            type="button"
            className="fit-btn"
            onClick={resetZoom}
            title="Fit to Viewport [F]"
          >
            Fit
          </button>
        </div>

        {/* Checkbox Toggles */}
        <label className="toolbar-checkbox-label" title="Toggle defect bounding boxes [B]">
          <span className={`toolbar-checkbox ${showBoxes ? 'checked' : ''}`}>
            {showBoxes && (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" width="10" height="10">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            )}
          </span>
          <input
            type="checkbox"
            checked={showBoxes}
            onChange={(e) => setShowBoxes(e.target.checked)}
            className="visually-hidden"
          />
          <span>Boxes</span>
        </label>

        <label className="toolbar-checkbox-label" title="Toggle physical micron callout tags [M]">
          <span className={`toolbar-checkbox ${showDimensions ? 'checked' : ''}`}>
            {showDimensions && (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" width="10" height="10">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            )}
          </span>
          <input
            type="checkbox"
            checked={showDimensions}
            onChange={(e) => setShowDimensions(e.target.checked)}
            className="visually-hidden"
          />
          <span>µm Tags</span>
        </label>

        <label className="toolbar-checkbox-label" title="Toggle reticle crosshair [C]">
          <span className={`toolbar-checkbox ${showCrosshair ? 'checked' : ''}`}>
            {showCrosshair && (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" width="10" height="10">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            )}
          </span>
          <input
            type="checkbox"
            checked={showCrosshair}
            onChange={(e) => setShowCrosshair(e.target.checked)}
            className="visually-hidden"
          />
          <span>Crosshair</span>
        </label>
      </div>
    </div>
  );
}
