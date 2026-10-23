import React, { useState, useCallback } from 'react';
import { useInspection } from '../../context/useInspection';
import './CalibrationControls.css';

export default function CalibrationControls() {
  const {
    scaleUmPerPx,
    updateScale,
    confidence,
    setConfidence,
    runInspection,
    currentImage,
  } = useInspection();

  // Transient values during dragging (null when user is not dragging)
  const [draggingScale, setDraggingScale] = useState(null);
  const [draggingConf, setDraggingConf] = useState(null);

  const activeScale = draggingScale !== null ? draggingScale : scaleUmPerPx;
  const activeConf = draggingConf !== null ? draggingConf : confidence;

  // Commit scale calculation only when user releases hand/pointer
  const commitScale = useCallback((val) => {
    const num = Math.max(1, Math.min(100, parseFloat(val) || 15.0));
    setDraggingScale(null);
    updateScale(num);
  }, [updateScale]);

  // Commit confidence and trigger inference only when user releases hand/pointer
  const commitConfidence = useCallback((val) => {
    const confVal = Math.max(0.05, Math.min(0.95, parseFloat(val) || 0.35));
    setDraggingConf(null);
    setConfidence(confVal);
    if (currentImage) {
      runInspection(null, null, activeScale, confVal);
    }
  }, [activeScale, currentImage, runInspection, setConfidence]);

  return (
    <div className="calibration-controls-group">
      {/* 1. Optical Scale Factor */}
      <div className="calib-control-item">
        <div className="calib-label-row">
          <span className="calib-label">Optical Scale Factor</span>
          <span className="calib-val-green">{Number(activeScale).toFixed(2)} µm/px</span>
        </div>
        <div className="calib-inputs-row">
          <input
            type="range"
            min="5"
            max="30"
            step="0.5"
            value={activeScale}
            onChange={(e) => setDraggingScale(parseFloat(e.target.value))}
            onMouseUp={(e) => commitScale(e.target.value)}
            onTouchEnd={(e) => commitScale(e.target.value)}
            onKeyUp={(e) => commitScale(e.target.value)}
            className="google-range-slider"
            title="Drag to adjust. Calculation applies on release."
          />
          <input
            type="number"
            min="1"
            max="100"
            step="1"
            value={Math.round(activeScale)}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              if (!isNaN(v)) setDraggingScale(v);
            }}
            onBlur={() => commitScale(activeScale)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.target.blur();
                commitScale(activeScale);
              }
            }}
            className="square-number-box"
            title="Enter scale factor and press Enter"
          />
        </div>
      </div>

      {/* 2. Confidence Threshold */}
      <div className="calib-control-item">
        <div className="calib-label-row">
          <span className="calib-label">Confidence Threshold</span>
          <span className="calib-val-green">{Math.round(activeConf * 100)}%</span>
        </div>
        <div className="calib-inputs-row">
          <input
            type="range"
            min="0.10"
            max="0.90"
            step="0.05"
            value={activeConf}
            onChange={(e) => setDraggingConf(parseFloat(e.target.value))}
            onMouseUp={(e) => commitConfidence(e.target.value)}
            onTouchEnd={(e) => commitConfidence(e.target.value)}
            onKeyUp={(e) => commitConfidence(e.target.value)}
            className="google-range-slider"
            title="Drag to adjust. Inference applies on release."
          />
          <input
            type="number"
            min="10"
            max="90"
            step="1"
            value={Math.round(activeConf * 100)}
            onChange={(e) => {
              const v = parseInt(e.target.value, 10);
              if (!isNaN(v)) setDraggingConf(v / 100);
            }}
            onBlur={() => commitConfidence(activeConf)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.target.blur();
                commitConfidence(activeConf);
              }
            }}
            className="square-number-box"
            title="Enter confidence percentage and press Enter"
          />
        </div>
      </div>
    </div>
  );
}
