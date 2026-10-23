import React from 'react';
import { useInspection } from '../../context/useInspection';
import './Toast.css';

export default function Toast() {
  const { toast, closeToast } = useInspection();

  if (!toast) return null;

  const isSuccess = toast.type === 'success';
  const isError = toast.type === 'error';
  const isWarning = toast.type === 'warning';

  return (
    <div className="toast-container" role="status" aria-live="polite">
      <div className={`toast-message ${toast.type || 'info'}`}>
        <div className="toast-icon-box">
          {isSuccess && <span className="toast-check-icon">✓</span>}
          {isError && <span className="toast-err-icon">✕</span>}
          {isWarning && <span className="toast-warn-icon">!</span>}
          {!isSuccess && !isError && !isWarning && <span className="toast-info-icon">i</span>}
        </div>
        <span className="toast-text-body">{toast.message}</span>
        <button
          type="button"
          className="toast-dismiss-btn"
          onClick={closeToast}
          title="Dismiss notification"
          aria-label="Dismiss notification"
        >
          &times;
        </button>
      </div>
    </div>
  );
}
