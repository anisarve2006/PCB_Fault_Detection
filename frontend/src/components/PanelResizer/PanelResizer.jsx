import React, { useState, useEffect, useRef, useCallback } from 'react';
import './PanelResizer.css';

export default function PanelResizer({
  side, // 'left' | 'right'
  currentWidth,
  minWidth = 200,
  maxWidth = 700,
  onResize,
  onReset,
}) {
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef({ startX: 0, startWidth: 0 });

  const handleMouseDown = useCallback((e) => {
    // Only primary mouse button
    if (e.button !== 0) return;
    e.preventDefault();
    setIsDragging(true);
    dragRef.current = {
      startX: e.clientX,
      startWidth: currentWidth,
    };
    document.body.classList.add('is-resizing-panel');
  }, [currentWidth]);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e) => {
      const deltaX = e.clientX - dragRef.current.startX;
      let newWidth;
      if (side === 'left') {
        newWidth = dragRef.current.startWidth + deltaX;
      } else {
        // Dragging right splitter left increases right panel width
        newWidth = dragRef.current.startWidth - deltaX;
      }
      newWidth = Math.max(minWidth, Math.min(maxWidth, Math.round(newWidth)));
      onResize(newWidth);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      document.body.classList.remove('is-resizing-panel');
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.classList.remove('is-resizing-panel');
    };
  }, [isDragging, side, minWidth, maxWidth, onResize]);

  return (
    <div
      className={`panel-resizer panel-resizer-${side} ${isDragging ? 'is-active' : ''}`}
      onMouseDown={handleMouseDown}
      onDoubleClick={onReset}
      title={`Drag left/right to resize ${side} sidebar. Double-click to reset width.`}
      role="separator"
      aria-orientation="vertical"
      aria-valuenow={currentWidth}
      aria-valuemin={minWidth}
      aria-valuemax={maxWidth}
    >
      <div className="resizer-track" />
      <div className="resizer-handle-grip">
        <span className="resizer-pip" />
        <span className="resizer-pip" />
        <span className="resizer-pip" />
      </div>
    </div>
  );
}
