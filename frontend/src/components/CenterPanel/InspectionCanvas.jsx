import React, { useRef, useEffect, useCallback } from 'react';
import { useInspection } from '../../context/useInspection';
import CanvasPlaceholder from './CanvasPlaceholder';
import LoadingScanner from './LoadingScanner';
import './InspectionCanvas.css';

export default function InspectionCanvas() {
  const {
    currentImage,
    detections,
    selectedDefectIndex,
    setSelectedDefectIndex,
    hoveredDefectIndex,
    setHoveredDefectIndex,
    setCursorCoords,
    scaleUmPerPx,
    stageTheme,
    zoom,
    setZoom,
    panX,
    setPanX,
    panY,
    setPanY,
    showBoxes,
    showDimensions,
    showCrosshair,
    canvasContainerRef,
    resetZoom,
  } = useInspection();

  const canvasRef = useRef(null);
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });

  // Reset zoom on initial image load
  useEffect(() => {
    if (currentImage) {
      resetZoom();
    }
  }, [currentImage, resetZoom]);

  // Main Canvas Render
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    // Viewport background
    ctx.fillStyle = '#F8F9FA';
    ctx.fillRect(0, 0, width, height);

    if (!currentImage) return;

    ctx.save();
    // Apply pan & zoom transforms
    ctx.translate(panX, panY);
    ctx.scale(zoom, zoom);

    // Board drop shadow / border on stage
    const imgW = currentImage.naturalWidth;
    const imgH = currentImage.naturalHeight;

    ctx.drawImage(currentImage, 0, 0);

    // Board outer boundary frame
    ctx.strokeStyle = stageTheme === 'dark' ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.15)';
    ctx.lineWidth = 1 / zoom;
    ctx.strokeRect(0, 0, imgW, imgH);

    // Crosshair alignment lines
    if (showCrosshair) {
      ctx.save();
      ctx.strokeStyle = '#16A34A';
      ctx.lineWidth = 1 / zoom;
      ctx.setLineDash([4 / zoom, 4 / zoom]);

      const cx = imgW / 2;
      const cy = imgH / 2;

      ctx.beginPath();
      ctx.moveTo(cx, 0);
      ctx.lineTo(cx, imgH);
      ctx.moveTo(0, cy);
      ctx.lineTo(imgW, cy);
      ctx.stroke();
      ctx.restore();
    }

    // Draw Detections
    if (showBoxes && detections && detections.length > 0) {
      detections.forEach((defect, idx) => {
        const { x1, y1, width_px, height_px } = defect.bbox;
        const isHovered = hoveredDefectIndex === idx;
        const isSelected = selectedDefectIndex === idx;
        const color = defect.color || '#16A34A';

        ctx.save();

        // Stroke
        ctx.strokeStyle = color;
        ctx.lineWidth = (isSelected ? 2.8 : isHovered ? 2.2 : 1.5) / Math.max(1, zoom * 0.7);

        if (isSelected) {
          ctx.fillStyle = 'rgba(22, 163, 74, 0.18)';
          ctx.fillRect(x1, y1, width_px, height_px);

          // Animated / target pulse corners
          const extLen = Math.min(10, width_px / 2, height_px / 2);
          ctx.lineWidth = 2.5 / Math.max(1, zoom * 0.7);
          ctx.beginPath();
          ctx.moveTo(x1 - 2, y1 + extLen); ctx.lineTo(x1 - 2, y1 - 2); ctx.lineTo(x1 + extLen, y1 - 2);
          ctx.moveTo(x1 + width_px + 2 - extLen, y1 - 2); ctx.lineTo(x1 + width_px + 2, y1 - 2); ctx.lineTo(x1 + width_px + 2, y1 + extLen);
          ctx.moveTo(x1 - 2, y1 + height_px + 2 - extLen); ctx.lineTo(x1 - 2, y1 + height_px + 2); ctx.lineTo(x1 + extLen, y1 + height_px + 2);
          ctx.moveTo(x1 + width_px + 2 - extLen, y1 + height_px + 2); ctx.lineTo(x1 + width_px + 2, y1 + height_px + 2); ctx.lineTo(x1 + width_px + 2, y1 + height_px + 2 - extLen);
          ctx.stroke();
        } else if (isHovered) {
          ctx.fillStyle = 'rgba(255, 255, 255, 0.08)';
          ctx.fillRect(x1, y1, width_px, height_px);
        }

        // Bounding Box on Board
        ctx.strokeRect(x1, y1, width_px, height_px);

        if (isSelected) {
          ctx.fillStyle = 'rgba(24, 128, 56, 0.12)';
          ctx.fillRect(x1, y1, width_px, height_px);
        } else if (isHovered) {
          ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
          ctx.fillRect(x1, y1, width_px, height_px);
        }

        // Format clean class name and dimension
        const cleanName = defect.class_name
          .replace(/_/g, ' ')
          .replace(/\b\w/g, (l) => l.toUpperCase());

        let dimText = '';
        if (defect.class_name === 'open_circuit' || defect.class_name === 'spur') {
          const lVal = Math.max(defect.physical.width_um, defect.physical.height_um);
          dimText = `L: ${lVal.toFixed(1)} µm`;
        } else if (defect.class_name === 'short') {
          const wVal = Math.min(defect.physical.width_um, defect.physical.height_um);
          dimText = `W: ${wVal.toFixed(1)} µm`;
        } else if (defect.class_name === 'missing_hole') {
          const dVal = (defect.physical.width_um + defect.physical.height_um) / 2;
          dimText = `D: ${dVal.toFixed(1)} µm`;
        } else if (defect.class_name === 'spurious_copper' || defect.class_name === 'mouse_bite') {
          dimText = `A: ${defect.physical.area_um2.toFixed(1)} µm²`;
        } else {
          dimText = `${defect.physical.width_um.toFixed(1)} µm`;
        }

        if (showDimensions) {
          const titleFontPx = Math.max(10, 11 / Math.max(0.6, zoom * 0.6));
          const dimFontPx = Math.max(9, 10 / Math.max(0.6, zoom * 0.6));

          ctx.font = `700 ${titleFontPx}px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`;
          const m1 = ctx.measureText(cleanName);
          ctx.font = `500 ${dimFontPx}px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`;
          const m2 = ctx.measureText(dimText);

          const padX = 6 / Math.max(1, zoom * 0.7);
          const padY = 4 / Math.max(1, zoom * 0.7);
          const tagW = Math.max(m1.width, m2.width) + padX * 2 + 4;
          const tagH = titleFontPx + dimFontPx + padY * 2 + 2;

          // Position callout tag near defect
          let tagX = x1 + width_px + 8;
          let tagY = y1 - 2;

          if (tagX + tagW > imgW) {
            tagX = Math.max(0, x1 - tagW - 8);
          }
          if (tagY + tagH > imgH) {
            tagY = Math.max(0, imgH - tagH - 4);
          }
          if (tagY < 0) tagY = 0;

          // Subtle connector line from defect to tag
          ctx.beginPath();
          ctx.moveTo(x1 + width_px / 2, y1 + height_px / 2);
          ctx.lineTo(tagX > x1 ? tagX : tagX + tagW, tagY + tagH / 2);
          ctx.strokeStyle = color;
          ctx.lineWidth = 1.2 / Math.max(1, zoom * 0.7);
          ctx.stroke();

          // White background box
          ctx.fillStyle = '#FFFFFF';
          ctx.fillRect(tagX, tagY, tagW, tagH);

          // Colored border
          ctx.strokeStyle = color;
          ctx.lineWidth = (isSelected ? 2.5 : 1.8) / Math.max(1, zoom * 0.7);
          ctx.strokeRect(tagX, tagY, tagW, tagH);

          // Line 1: Class Name in bold dark-gray
          ctx.fillStyle = '#202124';
          ctx.font = `700 ${titleFontPx}px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`;
          ctx.fillText(cleanName, tagX + padX, tagY + padY + titleFontPx - 1);

          // Line 2: Dimension
          ctx.fillStyle = '#3C4043';
          ctx.font = `500 ${dimFontPx}px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`;
          ctx.fillText(dimText, tagX + padX, tagY + padY + titleFontPx + dimFontPx + 1);
        }

        ctx.restore();
      });
    }

    ctx.restore();
  }, [
    currentImage,
    panX,
    panY,
    zoom,
    stageTheme,
    showCrosshair,
    showBoxes,
    detections,
    hoveredDefectIndex,
    selectedDefectIndex,
    showDimensions,
  ]);

  // Sync canvas dimensions with viewport container
  useEffect(() => {
    const container = canvasContainerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const updateSize = () => {
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
      render();
    };

    updateSize();

    const resizeObserver = new ResizeObserver(() => {
      updateSize();
    });
    resizeObserver.observe(container);

    return () => resizeObserver.disconnect();
  }, [canvasContainerRef, render]);

  useEffect(() => {
    render();
  }, [render]);

  // Mouse Handlers
  const handleMouseDown = (e) => {
    if (e.button !== 0) return;
    isDraggingRef.current = true;
    dragStartRef.current = {
      x: e.clientX - panX,
      y: e.clientY - panY,
    };
  };

  const handleMouseMove = (e) => {
    if (isDraggingRef.current) {
      setPanX(e.clientX - dragStartRef.current.x);
      setPanY(e.clientY - dragStartRef.current.y);
      return;
    }

    if (!canvasContainerRef.current || !currentImage) return;
    const rect = canvasContainerRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const imgX = (mouseX - panX) / zoom;
    const imgY = (mouseY - panY) / zoom;

    const inBounds = imgX >= 0 && imgX <= currentImage.naturalWidth && imgY >= 0 && imgY <= currentImage.naturalHeight;

    setCursorCoords({
      x: Math.round(imgX),
      y: Math.round(imgY),
      x_um: Math.round(imgX * scaleUmPerPx),
      y_um: Math.round(imgY * scaleUmPerPx),
      inBounds,
    });

    // Hover hit test
    let foundIdx = -1;
    for (let i = detections.length - 1; i >= 0; i--) {
      const d = detections[i];
      if (
        imgX >= d.bbox.x1 &&
        imgX <= d.bbox.x2 &&
        imgY >= d.bbox.y1 &&
        imgY <= d.bbox.y2
      ) {
        foundIdx = i;
        break;
      }
    }
    setHoveredDefectIndex(foundIdx);
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const handleClick = (e) => {
    if (!canvasContainerRef.current || !currentImage) return;
    const rect = canvasContainerRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const imgX = (mouseX - panX) / zoom;
    const imgY = (mouseY - panY) / zoom;

    let foundIdx = -1;
    for (let i = detections.length - 1; i >= 0; i--) {
      const d = detections[i];
      if (
        imgX >= d.bbox.x1 &&
        imgX <= d.bbox.x2 &&
        imgY >= d.bbox.y1 &&
        imgY <= d.bbox.y2
      ) {
        foundIdx = i;
        break;
      }
    }
    setSelectedDefectIndex(foundIdx);
  };

  const transformRef = useRef({ zoom, panX, panY });

  useEffect(() => {
    transformRef.current = { zoom, panX, panY };
  }, [zoom, panX, panY]);

  useEffect(() => {
    const container = canvasContainerRef.current;
    if (!container) return;

    const onWheel = (e) => {
      e.preventDefault();
      const rect = container.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const { zoom: curZoom, panX: curPanX, panY: curPanY } = transformRef.current;
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
      const newZoom = Math.max(0.15, Math.min(8.0, curZoom * zoomFactor));

      const mouseImgX = (mouseX - curPanX) / curZoom;
      const mouseImgY = (mouseY - curPanY) / curZoom;

      setZoom(newZoom);
      setPanX(mouseX - mouseImgX * newZoom);
      setPanY(mouseY - mouseImgY * newZoom);
    };

    container.addEventListener('wheel', onWheel, { passive: false });
    return () => {
      container.removeEventListener('wheel', onWheel);
    };
  }, [canvasContainerRef, setZoom, setPanX, setPanY]);

  return (
    <div
      ref={canvasContainerRef}
      className="canvas-viewport"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={() => {
        handleMouseUp();
        setCursorCoords((c) => ({ ...c, inBounds: false }));
      }}
      onClick={handleClick}
    >
      <canvas ref={canvasRef} className="inspection-canvas-element" />
      {!currentImage && <CanvasPlaceholder />}
      <LoadingScanner />
    </div>
  );
}
