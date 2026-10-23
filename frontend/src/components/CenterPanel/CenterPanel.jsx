import React from 'react';
import CanvasToolbar from './CanvasToolbar';
import InspectionCanvas from './InspectionCanvas';
import CanvasFooterBar from './CanvasFooterBar';
import './CenterPanel.css';

export default function CenterPanel() {
  return (
    <section className="center-panel">
      <CanvasToolbar />
      <InspectionCanvas />
      <CanvasFooterBar />
    </section>
  );
}
