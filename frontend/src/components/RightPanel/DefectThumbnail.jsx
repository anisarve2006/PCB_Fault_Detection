import React, { useRef, useEffect } from 'react';

export default function DefectThumbnail({ currentImage, bbox }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (currentImage && bbox && currentImage.naturalWidth > 0) {
      const { x1, y1, width_px, height_px } = bbox;
      const padX = Math.max(10, width_px * 0.4);
      const padY = Math.max(10, height_px * 0.4);
      const srcX = Math.max(0, x1 - padX);
      const srcY = Math.max(0, y1 - padY);
      const srcW = Math.min(currentImage.naturalWidth - srcX, width_px + padX * 2);
      const srcH = Math.min(currentImage.naturalHeight - srcY, height_px + padY * 2);

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      try {
        ctx.drawImage(currentImage, srcX, srcY, srcW, srcH, 0, 0, canvas.width, canvas.height);
      } catch {
        ctx.fillStyle = '#15803D';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }
    } else {
      ctx.fillStyle = '#15803D';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
  }, [currentImage, bbox]);

  return (
    <canvas
      ref={canvasRef}
      width={28}
      height={18}
      className="defect-mini-preview"
      style={{ width: '28px', height: '18px', display: 'block', backgroundColor: '#15803D' }}
    />
  );
}
