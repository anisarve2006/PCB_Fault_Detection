import React from 'react';
import { useInspection } from '../../context/useInspection';
import './VerdictBanner.css';

export default function VerdictBanner() {
  const { verdict, verdictDesc } = useInspection();

  const isReject = verdict !== 'PASS';

  return (
    <div className={`google-verdict-box ${isReject ? 'reject' : 'pass'}`}>
      <div className="verdict-icon-col">
        {isReject ? (
          <div className="verdict-icon-reject">✕</div>
        ) : (
          <div className="verdict-icon-pass">✓</div>
        )}
      </div>
      <div className="verdict-text-col">
        <div className="verdict-status-title">
          {isReject ? 'Non-Conformance: REJECT' : 'Conformance: APPROVED (PASS)'}
        </div>
        <div className="verdict-status-desc">
          {verdictDesc || 'Fatal electrical defect detected (Short Circuit or Trace Break). Route PCB to disposition / scrap.'}
        </div>
      </div>
    </div>
  );
}
