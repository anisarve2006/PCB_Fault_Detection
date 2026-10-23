import React from 'react';
import './BenchmarkChart.css';

export default function BenchmarkChart() {
  const metricsToChart = [
    {
      name: 'Overall mAP@50',
      category: 'IPC Acceptability Threshold',
      s1: 79.2,
      s5: 98.8,
      color: '#188038',
    },
    {
      name: 'Short Circuit Recall',
      category: 'Fatal Conductor Bridge Discontinuity',
      s1: 79.5,
      s5: 98.4,
      color: '#EA4335',
    },
    {
      name: 'Open Circuit Recall',
      category: 'Fatal Trace Disconnection / Break',
      s1: 80.5,
      s5: 99.6,
      color: '#EA4335',
    },
    {
      name: 'Spur Protrusion Recall',
      category: 'Copper Whisker & Trace Narrowing',
      s1: 30.4,
      s5: 97.8,
      color: '#1A73E8',
    },
    {
      name: 'Mouse Bite Recall',
      category: 'Conductor Edge Nick & Erosion',
      s1: 59.1,
      s5: 98.5,
      color: '#5E35B1',
    },
  ];

  return (
    <div className="modal-metrics-chart-box">
      <div className="chart-header-row">
        <div className="chart-title-group">
          <div className="chart-title">Defect Recall Progression (Baseline vs. Phase 5 Champion)</div>
          <div className="chart-subtitle">
            Cumulative evaluation against the untouched held-out benchmark test set (Board 09 — 1,056 frames)
          </div>
        </div>
        <div className="chart-legend-row">
          <div className="legend-item">
            <span className="legend-marker champion-marker" />
            <span>Phase 5 Champion Score</span>
          </div>
        </div>
      </div>

      <div className="chart-bars-container">
        {metricsToChart.map((m) => {
          const delta = (m.s5 - m.s1).toFixed(1);
          return (
            <div key={m.name} className="metric-bar-group">
              <div className="metric-bar-labels">
                <div className="metric-name-col">
                  <span className="metric-name">{m.name}</span>
                  <span className="metric-category">· {m.category}</span>
                </div>
                <div className="metric-values-col">
                  <span className="val-baseline">Baseline: {m.s1}%</span>
                  <span className="val-arrow">➔</span>
                  <span className="val-champion">Phase 5: {m.s5}%</span>
                  <span className="val-delta-badge">+{delta}%</span>
                </div>
              </div>

              <div className="bar-track">
                {/* Phase 5 Filled Progress */}
                <div
                  className="bar-fill"
                  style={{
                    width: `${m.s5}%`,
                    backgroundColor: m.color,
                  }}
                  title={`Phase 5 Champion: ${m.s5}%`}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
