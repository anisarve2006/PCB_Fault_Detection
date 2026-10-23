import React from 'react';
import { useInspection } from '../../context/useInspection';
import './Header.css';

export default function Header() {
  const { systemStatus, setIsBenchmarkOpen, exportCsv, scaleUmPerPx, backendHealth, checkHealth } = useInspection();

  const hwDesc = systemStatus?.hardware
    ? (systemStatus.hardware.includes('CPU') ? 'Intel i7 CPU' : systemStatus.hardware)
    : 'Intel i7 CPU';
  const modelDesc = systemStatus?.active_model || 'Phase 5 Champion (98.81%)';

  return (
    <header className="app-header">
      {/* Left Branding */}
      <div className="header-brand-group">
        <div className="brand-logo-badge">AOI</div>
        <div className="brand-titles">
          <div className="brand-title">
            PCBVISION <span className="brand-title-accent">AOI-7000</span>
          </div>
          <div className="brand-subtitle">Industrial Machine Vision</div>
        </div>
      </div>

      {/* Middle Telemetry Row */}
      <div className="header-telemetry-row">
        {/* Live Backend Connection Indicator */}
        <div
          className={`telemetry-pill telemetry-health-pill status-${backendHealth?.status || 'checking'}`}
          onClick={() => checkHealth(true)}
          title={`Backend Endpoint: ${backendHealth?.url || '/api'}\nStatus: ${(backendHealth?.status || 'checking').toUpperCase()}${backendHealth?.latencyMs ? ` (${backendHealth.latencyMs}ms latency)` : ''}${backendHealth?.error ? `\nError: ${backendHealth.error}` : ''}\nClick to re-ping connection`}
        >
          <span className={`telemetry-dot dot-${backendHealth?.status || 'checking'}`} />
          <div className="telemetry-text">
            <span className="telemetry-lbl">API Server</span>
            <span className="telemetry-val">
              {backendHealth?.status === 'online' && (
                <>
                  <span className="health-txt-online">Online</span>
                  {backendHealth.latencyMs !== null && (
                    <span className="health-txt-latency"> · {backendHealth.latencyMs}ms</span>
                  )}
                </>
              )}
              {backendHealth?.status === 'checking' && (
                <span className="health-txt-checking">Connecting...</span>
              )}
              {backendHealth?.status === 'offline' && (
                <span className="health-txt-offline">Offline ↺</span>
              )}
            </span>
          </div>
        </div>

        <div className="telemetry-separator" />

        <div className="telemetry-pill" title="Compute Engine / Hardware Execution Acceleration">
          <span className="telemetry-dot" />
          <div className="telemetry-text">
            <span className="telemetry-lbl">Engine</span>
            <span className="telemetry-val">{hwDesc}</span>
          </div>
        </div>

        <div className="telemetry-separator" />

        <div className="telemetry-pill" title="Active Model Weights Checkpoint (98.81% mAP@50)">
          <span className="telemetry-dot" />
          <div className="telemetry-text">
            <span className="telemetry-lbl">Model</span>
            <span className="telemetry-val">{modelDesc}</span>
          </div>
        </div>

        <div className="telemetry-separator" />

        <div className="telemetry-pill" title="IPC-A-610G Industrial Acceptability Standard (Class 2 & 3)">
          <span className="telemetry-dot" />
          <div className="telemetry-text">
            <span className="telemetry-lbl">IPC Standard</span>
            <span className="telemetry-val">IPC-A-610G Class 2/3</span>
          </div>
        </div>

        <div className="telemetry-separator" />

        <div className="telemetry-pill" title="Microscope Telecentric Optical Calibration Pitch">
          <span className="telemetry-dot" />
          <div className="telemetry-text">
            <span className="telemetry-lbl">Calibration Scale</span>
            <span className="telemetry-val">{scaleUmPerPx.toFixed(2)} µm/px</span>
          </div>
        </div>
      </div>

      {/* Right Actions */}
      <div className="header-actions-group">
        <button
          type="button"
          className="btn-header-secondary"
          onClick={() => setIsBenchmarkOpen(true)}
          title="Open Sequential Training & Validation Progression Matrix"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
            <path d="M18 20V10M12 20V4M6 20v-6" />
          </svg>
          <span>Training Matrix</span>
        </button>

        <button
          type="button"
          className="btn-header-primary"
          onClick={exportCsv}
          title="Export CSV telemetry for statistical process control (SPC)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
          </svg>
          <span>Export CSV</span>
        </button>
      </div>
    </header>
  );
}
