import React, { useRef, useState } from 'react';
import { useInspection } from '../../context/useInspection';
import './Dropzone.css';

export default function Dropzone() {
  const { loadUserFile } = useInspection();
  const fileInputRef = useRef(null);
  const [isDragActive, setIsDragActive] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragActive(true);
  };

  const handleDragLeave = () => {
    setIsDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      loadUserFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      loadUserFile(e.target.files[0]);
    }
  };

  return (
    <div
      className={`upload-dropzone ${isDragActive ? 'drag-active' : ''}`}
      onClick={() => fileInputRef.current?.click()}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      title="Upload PCB image (JPG, PNG, BMP)"
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleChange}
        accept="image/*"
        className="file-input-hidden"
      />
      <div className="dropzone-icon-box">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" width="18" height="18">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
        </svg>
      </div>
      <div className="dropzone-main-text">
        Drop PCB image here or <span className="browse-link">Browse</span>
      </div>
      <div className="dropzone-sub-text">Supports JPG, PNG, BMP (up to 6000×4000)</div>
    </div>
  );
}
