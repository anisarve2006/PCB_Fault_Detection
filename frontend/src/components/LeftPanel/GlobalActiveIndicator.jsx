import React from 'react';
import { useInspection } from '../../context/useInspection';
import './GlobalActiveIndicator.css';

export default function GlobalActiveIndicator() {
  const { isUserGlobalActive, userGlobalName, clearGlobalUserImage } = useInspection();

  if (!isUserGlobalActive) return null;

  return (
    <div className="global-image-indicator">
      <div className="global-indicator-header">
        <div className="global-indicator-status">
          <span className="status-dot-pulse" />
          <span className="global-indicator-title">GLOBAL USER IMAGE ACTIVE</span>
        </div>
        <button
          type="button"
          className="btn-clear-global"
          onClick={clearGlobalUserImage}
          title="Clear uploaded image and return to sample library"
        >
          &times; Clear
        </button>
      </div>
      <div className="global-indicator-name">{userGlobalName}</div>
      <div className="global-indicator-tip">All 1-Click defect patterns below inspect this image</div>
    </div>
  );
}
