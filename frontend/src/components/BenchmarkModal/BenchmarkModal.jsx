import React from 'react';
import { useInspection } from '../../context/useInspection';
import BenchmarkTable from './BenchmarkTable';
import BenchmarkChart from './BenchmarkChart';
import './BenchmarkModal.css';

export default function BenchmarkModal() {
  const { isBenchmarkOpen, setIsBenchmarkOpen, metrics } = useInspection();

  if (!isBenchmarkOpen) return null;

  return (
    <div className="modal-backdrop" onClick={() => setIsBenchmarkOpen(false)}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            <span>SEQUENTIAL MODEL EVALUATION MATRIX · IPC BENCHMARK</span>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={() => setIsBenchmarkOpen(false)}
            title="Close modal [Esc]"
          >
            &times;
          </button>
        </div>

        <div className="modal-body">
          <div className="modal-intro">
            Cumulative data batch evaluation against the <strong>untouched held-out benchmark test set (Board 09 — 1,056 frames)</strong>:
          </div>

          <BenchmarkTable stages={metrics} />
          <BenchmarkChart />
        </div>
      </div>
    </div>
  );
}
