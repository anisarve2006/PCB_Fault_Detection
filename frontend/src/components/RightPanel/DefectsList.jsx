import React from 'react';
import { useInspection } from '../../context/useInspection';
import { CLASS_COLORS } from '../../constants/defectConstants';
import DefectThumbnail from './DefectThumbnail';
import './DefectsList.css';

export default function DefectsList() {
  const {
    detections,
    selectedDefectIndex,
    setSelectedDefectIndex,
    setHoveredDefectIndex,
    zoomToDefect,
    currentImage,
  } = useInspection();

  const handleRowClick = (defect, idx) => {
    setSelectedDefectIndex(idx);
    zoomToDefect(defect);
  };

  const formatCleanName = (cname) => {
    if (!cname) return '';
    return cname.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  };

  const getMeasurementText = (defect) => {
    if (!defect || !defect.physical) return '—';
    const cname = defect.class_name;
    const { width_um, height_um, area_um2 } = defect.physical;

    if (cname === 'open_circuit' || cname === 'spur') {
      const l = Math.max(width_um, height_um);
      return `L: ${l.toFixed(1)} µm`;
    }
    if (cname === 'short') {
      const w = Math.min(width_um, height_um);
      return `W: ${w.toFixed(1)} µm`;
    }
    if (cname === 'missing_hole') {
      const d = (width_um + height_um) / 2;
      return `D: ${d.toFixed(1)} µm`;
    }
    if (cname === 'spurious_copper' || cname === 'mouse_bite') {
      return `A: ${area_um2.toFixed(1)} µm²`;
    }
    return `${width_um.toFixed(1)} µm`;
  };

  const formatConfidence = (conf) => {
    if (conf === undefined || conf === null) return '0.80';
    const num = parseFloat(conf);
    if (isNaN(num)) return '0.80';
    const val = num > 1 ? num / 100 : num;
    return val.toFixed(2);
  };

  return (
    <div className="defects-table-wrapper">
      <div className="defects-table-header-row">
        <div className="defects-table-title">Defect Details & Measurements</div>
        <div className="defects-records-count">{detections.length} records</div>
      </div>

      <div className="table-scroll-container">
        <table className="google-defects-table">
          <thead>
            <tr>
              <th className="th-num">#</th>
              <th className="th-class">Class</th>
              <th className="th-measure">Measurement</th>
              <th className="th-conf">Confidence</th>
              <th className="th-preview">Preview</th>
            </tr>
          </thead>
          <tbody>
            {detections.length === 0 ? (
              <tr>
                <td colSpan={5} className="empty-table-cell">
                  No defects identified. PCB complies with nominal IPC tolerances.
                </td>
              </tr>
            ) : (
              detections.map((defect, idx) => {
                const isSelected = selectedDefectIndex === idx;
                const color = CLASS_COLORS[defect.class_name] || '#EA4335';
                const measureText = getMeasurementText(defect);
                const confText = formatConfidence(defect.confidence);

                return (
                  <tr
                    key={`${defect.class_name}_${idx}`}
                    className={`defect-tr ${isSelected ? 'is-selected' : ''}`}
                    onClick={() => handleRowClick(defect, idx)}
                    onMouseEnter={() => setHoveredDefectIndex(idx)}
                    onMouseLeave={() => setHoveredDefectIndex(-1)}
                  >
                    <td className="td-num">{idx + 1}</td>
                    <td className="td-class">
                      <span className="defect-color-sq" style={{ backgroundColor: color }} />
                      <span className="defect-name-text">{formatCleanName(defect.class_name)}</span>
                    </td>
                    <td className="td-measure">{measureText}</td>
                    <td className="td-conf">{confText}</td>
                    <td className="td-preview">
                      <DefectThumbnail currentImage={currentImage} bbox={defect.bbox} />
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
