import React from 'react';
import { useInspection } from '../../context/useInspection';
import './InspectButton.css';

export default function InspectButton() {
  const { runInspection, isLoading, currentImage } = useInspection();

  return (
    <button
      type="button"
      className="btn-run-inspection"
      onClick={() => runInspection()}
      disabled={isLoading || !currentImage}
      title="Execute automated optical inspection (Shortcut: Ctrl+Enter)"
    >
      <svg viewBox="0 0 24 24" fill="currentColor" width="13" height="13" style={{ marginRight: '6px' }}>
        <polygon points="5 3 19 12 5 21 5 3" />
      </svg>
      <span>{isLoading ? 'Analyzing PCB...' : 'Run AOI Inspection'}</span>
    </button>
  );
}
