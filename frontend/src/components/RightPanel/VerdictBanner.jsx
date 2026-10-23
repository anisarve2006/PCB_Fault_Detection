import React from 'react';
import { useInspection } from '../../context/useInspection';
import './VerdictBanner.css';

export default function VerdictBanner() {
  const { verdict, verdictDesc, isLoading, loadingText, rawResult } = useInspection();

  if (isLoading || verdict === 'ANALYZING') {
    return (
      <div className="google-verdict-box scanning">
        <div className="verdict-icon-col">
          <div className="verdict-icon-scanning">
            <span className="scanning-spinner" />
          </div>
        </div>
        <div className="verdict-text-col">
          <div className="verdict-status-title">Inspection Status: IN PROGRESS...</div>
          <div className="verdict-status-desc">
            {loadingText || 'Executing optical inspection & micro-dimensional geometry measurements...'}
          </div>
        </div>
      </div>
    );
  }

  if (verdict === 'PENDING' || !rawResult) {
    return (
      <div className="google-verdict-box pending">
        <div className="verdict-icon-col">
          <div className="verdict-icon-pending">○</div>
        </div>
        <div className="verdict-text-col">
          <div className="verdict-status-title">Inspection Status: AWAITING SCAN</div>
          <div className="verdict-status-desc">
            {verdictDesc || 'Click "Run AOI Inspection" to evaluate manufacturing conformance against IPC-A-610.'}
          </div>
        </div>
      </div>
    );
  }

  const isCritical = verdict === 'CRITICAL';
  const isMajor = verdict === 'MAJOR';
  const isReview = verdict === 'REVIEW';

  let boxClass = 'pass';
  let title = 'Conformance: APPROVED (PASS)';
  let icon = <div className="verdict-icon-pass">✓</div>;

  if (isCritical) {
    boxClass = 'reject';
    title = 'Non-Conformance: REJECT';
    icon = <div className="verdict-icon-reject">✕</div>;
  } else if (isMajor) {
    boxClass = 'major';
    title = 'Non-Conformance: REJECT (MAJOR)';
    icon = <div className="verdict-icon-major">!</div>;
  } else if (isReview) {
    boxClass = 'review';
    title = 'Disposition: OPERATOR REVIEW';
    icon = <div className="verdict-icon-review">⚠</div>;
  }

  return (
    <div className={`google-verdict-box ${boxClass}`}>
      <div className="verdict-icon-col">{icon}</div>
      <div className="verdict-text-col">
        <div className="verdict-status-title">{title}</div>
        <div className="verdict-status-desc">{verdictDesc}</div>
      </div>
    </div>
  );
}
