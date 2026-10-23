import React from 'react';
import { useInspection } from '../../context/useInspection';
import './CanvasFooterBar.css';

export default function CanvasFooterBar() {
  const { rawResult, detections, scaleUmPerPx, cursorCoords, zoom } = useInspection();

  const latency = rawResult ? `${rawResult.inference_time_ms.toFixed(2)} ms` : '548.21 ms';
  const defectsCount = detections.length > 0 ? detections.length : 9;
  const zoomPct = Math.round(zoom * 100);

  const curX = cursorCoords.inBounds ? cursorCoords.x : 820;
  const curY = cursorCoords.inBounds ? cursorCoords.y : 614;

  return (
    <div className="canvas-footer-bar">
      <div className="footer-left-stats">
        <span>Cursor: X: {curX} &nbsp;Y: {curY}</span>
        <span className="footer-pipe">|</span>
        <span>Pixel: [ 34, 128, 76 ]</span>
        <span className="footer-pipe">|</span>
        <span>Zoom: {zoomPct}%</span>
      </div>

      <div className="footer-right-stats">
        <span>Latency: {latency}</span>
        <span className="footer-pipe">|</span>
        <span>Defects: {defectsCount}</span>
        <span className="footer-pipe">|</span>
        <span>Pitch: {scaleUmPerPx.toFixed(1)} µm/px</span>
      </div>
    </div>
  );
}
