import React from 'react';
import { useInspection } from '../../context/useInspection';
import './LoadingScanner.css';

export default function LoadingScanner() {
  const { isLoading, loadingText } = useInspection();

  if (!isLoading) return null;

  return (
    <div className="loading-overlay">
      <div className="scanner-laser" />
      <div className="scanner-spinner" />
      <div className="loading-text">{loadingText}</div>
    </div>
  );
}
