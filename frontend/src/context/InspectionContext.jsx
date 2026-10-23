import React, { createContext, useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  fetchSystemStatus,
  fetchSamples,
  getSampleImageUrl,
  fetchMetrics,
  runDetection,
  getApiBaseUrl,
  checkBackendHealth,
} from '../services/api';
import { TARGET_PATTERN_MAP, CLASS_COLORS } from '../constants/defectConstants';

const InspectionContext = createContext(null);

export { TARGET_PATTERN_MAP, CLASS_COLORS };

export function InspectionProvider({ children }) {
  // Backend Connection Health State
  const [backendHealth, setBackendHealth] = useState({
    status: 'checking',
    latencyMs: null,
    url: getApiBaseUrl(),
    error: null,
    lastChecked: null,
  });

  // System State
  const [systemStatus, setSystemStatus] = useState(null);
  const [samples, setSamples] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [isBenchmarkOpen, setIsBenchmarkOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('Acquiring frame...');
  const [toast, setToast] = useState(null);

  // Optical & Model Config
  const [scaleUmPerPx, setScaleUmPerPx] = useState(15.0);
  const [confidence, setConfidence] = useState(0.35);
  const [modelChoice, setModelChoice] = useState('champion');
  const [stageTheme, setStageTheme] = useState('dark'); // 'dark' (optical microscope stage) | 'light'

  // Active Board / Image State
  const [currentImage, setCurrentImage] = useState(null);
  const [currentImageName, setCurrentImageName] = useState('No board loaded');
  const [currentBlob, setCurrentBlob] = useState(null);
  const [currentSampleId, setCurrentSampleId] = useState(null);

  // Global User Upload Lock
  const [isUserGlobalActive, setIsUserGlobalActive] = useState(false);
  const [userGlobalBlob, setUserGlobalBlob] = useState(null);
  const [userGlobalName, setUserGlobalName] = useState('');

  // Target Pattern filter
  const [activeTargetPattern, setActiveTargetPattern] = useState('all_defects_panel');

  // Detection Results
  const [rawResult, setRawResult] = useState(null);
  const [allRawDetections, setAllRawDetections] = useState([]);
  const [selectedDefectIndex, setSelectedDefectIndex] = useState(-1);
  const [hoveredDefectIndex, setHoveredDefectIndex] = useState(-1);

  // Cursor coordinates in image & physical units
  const [cursorCoords, setCursorCoords] = useState({ x: 0, y: 0, x_um: 0, y_um: 0, inBounds: false });

  // Canvas Viewport Controls
  const [zoom, setZoom] = useState(1.0);
  const [panX, setPanX] = useState(0);
  const [panY, setPanY] = useState(0);
  const [showBoxes, setShowBoxes] = useState(true);
  const [showDimensions, setShowDimensions] = useState(true);
  const [showCrosshair, setShowCrosshair] = useState(true);

  const canvasContainerRef = useRef(null);

  const showToast = useCallback((message, type = 'info') => {
    const id = Date.now();
    setToast({ message, type, id });
    setTimeout(() => {
      setToast((curr) => (curr?.id === id ? null : curr));
    }, 3200);
  }, []);

  const closeToast = useCallback(() => {
    setToast(null);
  }, []);

  // Filter raw detections when activeTargetPattern changes
  const detections = useMemo(() => {
    if (!allRawDetections || allRawDetections.length === 0) {
      return [];
    }
    const targetConfig = TARGET_PATTERN_MAP[activeTargetPattern];
    const targetClasses = targetConfig ? targetConfig.classes : null;

    if (!targetClasses || targetClasses.length === 6) {
      return allRawDetections;
    }
    return allRawDetections.filter((d) => targetClasses.includes(d.class_name));
  }, [activeTargetPattern, allRawDetections]);

  // Recalculate physical dimensions when optical scale slider changes
  const updateScale = useCallback((newScale) => {
    const scale = Math.max(1, Math.min(100, parseFloat(newScale) || 15.0));
    setScaleUmPerPx(scale);

    setAllRawDetections((prev) =>
      prev.map((d) => {
        const w_um = Math.round(d.bbox.width_px * scale * 100) / 100;
        const h_um = Math.round(d.bbox.height_px * scale * 100) / 100;
        const area_um2 = Math.round(d.bbox.area_px * (scale ** 2) * 100) / 100;

        let diag_value = d.diagnostic.value;
        if (d.class_name === 'open_circuit' || d.class_name === 'short' || d.class_name === 'mouse_bite') {
          diag_value = `${Math.min(w_um, h_um)} µm`;
        } else if (d.class_name === 'spur') {
          diag_value = `${Math.max(w_um, h_um)} µm`;
        } else if (d.class_name === 'missing_hole') {
          diag_value = `${Math.round(((w_um + h_um) / 2.0) * 100) / 100} µm`;
        } else if (d.class_name === 'spurious_copper') {
          diag_value = `${area_um2} µm²`;
        }

        return {
          ...d,
          physical: {
            ...d.physical,
            width_um: w_um,
            height_um: h_um,
            area_um2: area_um2,
            scale_um_per_px: scale,
          },
          diagnostic: {
            ...d.diagnostic,
            value: diag_value,
          },
        };
      })
    );
  }, []);

  // Run Inspection via API
  const runInspection = useCallback(async (customFile = null, customSampleId = null, overrideScale = null, overrideConf = null, overrideModel = null) => {
    setIsLoading(true);
    setLoadingText('Executing YOLO inference & geometric metrology...');

    const fileToUse = customFile !== null ? customFile : (isUserGlobalActive && userGlobalBlob ? userGlobalBlob : currentBlob);
    const sampleToUse = customSampleId !== null ? customSampleId : (!fileToUse ? currentSampleId : null);
    const scaleToUse = overrideScale !== null ? overrideScale : scaleUmPerPx;
    const confToUse = overrideConf !== null ? overrideConf : confidence;
    const modelToUse = overrideModel !== null ? overrideModel : modelChoice;

    if (!fileToUse && !sampleToUse) {
      setIsLoading(false);
      showToast('No board image loaded for inspection', 'warning');
      return;
    }

    try {
      const result = await runDetection({
        file: fileToUse,
        sampleId: sampleToUse,
        confidence: confToUse,
        scaleUm: scaleToUse,
        modelChoice: modelToUse,
      });

      setRawResult(result);
      setAllRawDetections(result.detections || []);
      showToast(`Scan complete: ${result.summary.total_defects} defect(s) detected in ${result.inference_time_ms}ms`, 'success');
    } catch (err) {
      console.error('Detection failed:', err);
      showToast(`Inspection failure: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [isUserGlobalActive, userGlobalBlob, currentBlob, currentSampleId, scaleUmPerPx, confidence, modelChoice, showToast]);

  // Select Sample Pattern
  const selectSample = useCallback((sampleId, sampleName = '') => {
    if (isUserGlobalActive && userGlobalBlob) {
      setActiveTargetPattern(sampleId);
      return;
    }

    setCurrentSampleId(sampleId);
    setCurrentBlob(null);
    setActiveTargetPattern(sampleId);
    setCurrentImageName(sampleName || sampleId);

    setIsLoading(true);
    setLoadingText(`Loading sample: ${sampleName || sampleId}...`);

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      setCurrentImage(img);
      setIsLoading(false);
      runInspection(null, sampleId);
    };
    img.onerror = () => {
      setIsLoading(false);
      showToast(`Failed loading sample image: ${sampleId}`, 'error');
    };
    img.src = getSampleImageUrl(sampleId);
  }, [isUserGlobalActive, userGlobalBlob, runInspection, showToast]);

  // Live Backend Health Check
  const checkHealth = useCallback(async (notify = false) => {
    setBackendHealth((prev) => ({
      ...prev,
      status: prev.status === 'online' ? 'online' : 'checking',
    }));
    const result = await checkBackendHealth();
    setBackendHealth({
      status: result.status,
      latencyMs: result.latencyMs,
      url: result.url,
      error: result.error || null,
      lastChecked: new Date(),
    });

    if (result.status === 'online' && result.data) {
      setSystemStatus((prev) => prev || result.data);
      if (notify) {
        showToast(`Backend connection healthy (${result.latencyMs}ms)`, 'success');
      }
    } else if (result.status === 'offline' && notify) {
      showToast(`Backend unreachable (${result.error || 'Server sleeping or offline'})`, 'error');
    }
    return result;
  }, [showToast]);

  // Initial Load of Status, Samples, Metrics & Auto-recovery Polling
  useEffect(() => {
    async function init() {
      try {
        const healthResult = await checkHealth();
        const [samplesData, metricsData] = await Promise.all([
          fetchSamples().catch(() => []),
          fetchMetrics().catch(() => ({ stages: [] })),
        ]);
        if (healthResult?.data) setSystemStatus(healthResult.data);
        if (samplesData && samplesData.length > 0) setSamples(samplesData);
        if (metricsData && metricsData.stages) setMetrics(metricsData.stages);

        if (samplesData && samplesData.length > 0) {
          const defaultSample = samplesData.find((s) => s.id === 'all_defects_panel') || samplesData[0];
          selectSample(defaultSample.id, defaultSample.name);
        }
      } catch (err) {
        console.error('AOI workstation initialization failure:', err);
      }
    }
    init();

    // Health check polling every 25 seconds (keeps Render warm or detects wake-up)
    const interval = setInterval(() => {
      checkHealth();
    }, 25000);

    return () => clearInterval(interval);
  }, [selectSample, checkHealth]);

  // Load User File
  const loadUserFile = useCallback((file) => {
    if (!file || !file.type.startsWith('image/')) {
      showToast('Invalid file format. Upload JPG, PNG, or BMP image.', 'warning');
      return;
    }

    setIsLoading(true);
    setLoadingText(`Ingesting frame: ${file.name}...`);

    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        setIsUserGlobalActive(true);
        setUserGlobalBlob(file);
        setUserGlobalName(file.name);

        setCurrentImage(img);
        setCurrentBlob(file);
        setCurrentSampleId(null);
        setCurrentImageName(file.name);
        setActiveTargetPattern('all_defects_panel');

        setIsLoading(false);
        showToast(`Loaded board: ${file.name}`, 'info');

        runInspection(file, null);
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  }, [runInspection, showToast]);

  // Clear Global User Image
  const clearGlobalUserImage = useCallback(() => {
    setIsUserGlobalActive(false);
    setUserGlobalBlob(null);
    setUserGlobalName('');
    showToast('User frame cleared. Reset to sample library.', 'info');

    if (samples.length > 0) {
      selectSample(samples[0].id, samples[0].name);
    }
  }, [samples, selectSample, showToast]);

  // Zoom helpers
  const zoomIn = () => setZoom((z) => Math.min(8.0, z * 1.25));
  const zoomOut = () => setZoom((z) => Math.max(0.15, z / 1.25));
  const setZoomLevel = (targetZoom) => setZoom(Math.max(0.15, Math.min(8.0, targetZoom)));

  const resetZoom = useCallback(() => {
    if (!currentImage || !canvasContainerRef.current) return;
    const viewW = canvasContainerRef.current.clientWidth;
    const viewH = canvasContainerRef.current.clientHeight;
    const imgW = currentImage.naturalWidth;
    const imgH = currentImage.naturalHeight;

    const scale = Math.min((viewW - 40) / imgW, (viewH - 40) / imgH, 1.0);
    setZoom(scale);
    setPanX((viewW - imgW * scale) / 2);
    setPanY((viewH - imgH * scale) / 2);
  }, [currentImage]);

  const zoomToDefect = useCallback((defect) => {
    if (!defect || !canvasContainerRef.current) return;
    const { x1, y1, width_px, height_px } = defect.bbox;
    const viewW = canvasContainerRef.current.clientWidth;
    const viewH = canvasContainerRef.current.clientHeight;

    const targetZoom = Math.min(3.5, (viewW * 0.35) / Math.max(width_px, 30));
    const defectCenterX = x1 + width_px / 2;
    const defectCenterY = y1 + height_px / 2;

    setZoom(targetZoom);
    setPanX(viewW / 2 - defectCenterX * targetZoom);
    setPanY(viewH / 2 - defectCenterY * targetZoom);
  }, []);

  // Jump to next / prev defect (Operator inspection flow)
  const nextDefect = useCallback(() => {
    if (detections.length === 0) return;
    const nextIdx = (selectedDefectIndex + 1) % detections.length;
    setSelectedDefectIndex(nextIdx);
    zoomToDefect(detections[nextIdx]);
  }, [detections, selectedDefectIndex, zoomToDefect]);

  const prevDefect = useCallback(() => {
    if (detections.length === 0) return;
    const prevIdx = selectedDefectIndex <= 0 ? detections.length - 1 : selectedDefectIndex - 1;
    setSelectedDefectIndex(prevIdx);
    zoomToDefect(detections[prevIdx]);
  }, [detections, selectedDefectIndex, zoomToDefect]);

  // Keyboard navigation shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger if user is typing in an input
      if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) return;

      if (e.key === 'j' || e.key === 'J' || e.key === 'ArrowRight') {
        e.preventDefault();
        nextDefect();
      } else if (e.key === 'k' || e.key === 'K' || e.key === 'ArrowLeft') {
        e.preventDefault();
        prevDefect();
      } else if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        resetZoom();
      } else if (e.key === 'b' || e.key === 'B') {
        e.preventDefault();
        setShowBoxes((v) => !v);
      } else if (e.key === 'm' || e.key === 'M') {
        e.preventDefault();
        setShowDimensions((v) => !v);
      } else if (e.key === 'c' || e.key === 'C') {
        e.preventDefault();
        setShowCrosshair((v) => !v);
      } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        runInspection();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [nextDefect, prevDefect, resetZoom, runInspection]);

  // Export inspection report as JSON
  const exportReport = useCallback(() => {
    if (!currentImage || detections.length === 0) {
      showToast('No inspection telemetry available to export', 'warning');
      return;
    }

    const report = {
      system: 'PCBVision AOI Optical Quality Verification System',
      audit_standard: 'IPC-A-610G Class 2 / Class 3 Bare Board Criteria',
      timestamp: new Date().toISOString(),
      inspected_board: currentImageName,
      calibrated_optical_scale_um_per_px: scaleUmPerPx,
      model_evaluated: modelChoice,
      summary: {
        total_defects_found: detections.length,
        critical_violations: detections.filter((d) => d.severity === 'CRITICAL').length,
        major_defects: detections.filter((d) => d.severity === 'MAJOR').length,
        minor_tolerances: detections.filter((d) => d.severity === 'MINOR').length,
      },
      defect_inventory: detections.map((d, i) => ({
        index: i + 1,
        class: d.class_name,
        severity: d.severity,
        confidence: `${d.confidence}%`,
        bounding_box_pixels: d.bbox,
        calibrated_dimensions_um: d.physical,
        defect_measurement: {
          diagnostic: d.diagnostic.label,
          measured_value: d.diagnostic.value,
          ipc_standard_rule: d.diagnostic.ipc_rule,
        },
      })),
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `AOI_Report_${currentImageName.replace(/[^a-zA-Z0-9]/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('AOI Report (JSON) exported', 'success');
  }, [currentImage, detections, currentImageName, scaleUmPerPx, modelChoice, showToast]);

  // Export CSV
  const exportCsv = useCallback(() => {
    if (detections.length === 0) {
      showToast('No defect data available for CSV export', 'warning');
      return;
    }

    const headers = ['Index', 'Class', 'Severity', 'Confidence(%)', 'X1_px', 'Y1_px', 'Width_um', 'Height_um', 'Area_um2', 'Diagnostic_Value', 'IPC_Rule'];
    const rows = detections.map((d, i) => [
      i + 1,
      `"${d.class_name}"`,
      `"${d.severity}"`,
      d.confidence,
      d.bbox.x1,
      d.bbox.y1,
      d.physical.width_um,
      d.physical.height_um,
      d.physical.area_um2,
      `"${d.diagnostic.value}"`,
      `"${d.diagnostic.ipc_rule}"`,
    ]);

    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `AOI_Telemetry_${currentImageName.replace(/[^a-zA-Z0-9]/g, '_')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Inspection telemetry (CSV) exported', 'success');
  }, [detections, currentImageName, showToast]);

  // Derived filtered results summary
  const summary = useMemo(() => ({
    total_defects: detections.length,
    critical_count: detections.filter((d) => d.severity === 'CRITICAL').length,
    major_count: detections.filter((d) => d.severity === 'MAJOR').length,
    minor_count: detections.filter((d) => d.severity === 'MINOR').length,
    distinct_classes: [...new Set(detections.map((d) => d.class_name))],
  }), [detections]);

  const classBreakdown = useMemo(() => {
    const counts = {};
    detections.forEach((d) => {
      counts[d.class_name] = (counts[d.class_name] || 0) + 1;
    });
    return counts;
  }, [detections]);

  let verdict = 'PASS';
  let verdictBadge = 'IPC-A-610 PASS';
  let verdictDesc = 'No manufacturing non-conformances identified. Conductor geometry within IPC nominal specification.';
  let verdictColor = '#16A34A';

  if (summary.critical_count > 0) {
    verdict = 'CRITICAL';
    verdictBadge = 'REJECT · CLASS 3';
    verdictColor = '#DC2626';
    verdictDesc = 'Fatal electrical defect detected (Short Circuit or Trace Break). Route PCB to disposition / scrap.';
  } else if (summary.major_count > 0) {
    verdict = 'MAJOR';
    verdictBadge = 'REJECT · CLASS 2';
    verdictColor = '#D97706';
    verdictDesc = 'Interlayer connection anomaly (Missing or blocked via). Second-pass drill station or rework required.';
  } else if (summary.minor_count > 0) {
    verdict = 'REVIEW';
    verdictBadge = 'OPERATOR AUDIT';
    verdictColor = '#16A34A';
    verdictDesc = 'Surface copper tolerance imperfection (Spur/Bite/Residue). Verify dielectric spacing allowance.';
  }

  const value = {
    backendHealth,
    checkHealth,
    systemStatus,
    samples,
    metrics,
    isBenchmarkOpen,
    setIsBenchmarkOpen,
    isLoading,
    loadingText,
    toast,
    setToast,
    showToast,
    closeToast,

    scaleUmPerPx,
    updateScale,
    confidence,
    setConfidence,
    modelChoice,
    setModelChoice,
    stageTheme,
    setStageTheme,

    currentImage,
    currentImageName,
    currentBlob,
    currentSampleId,
    isUserGlobalActive,
    userGlobalBlob,
    userGlobalName,
    loadUserFile,
    clearGlobalUserImage,
    selectSample,

    activeTargetPattern,
    setActiveTargetPattern,

    rawResult,
    allRawDetections,
    detections,
    summary,
    classBreakdown,
    verdict,
    verdictBadge,
    verdictColor,
    verdictDesc,

    selectedDefectIndex,
    setSelectedDefectIndex,
    hoveredDefectIndex,
    setHoveredDefectIndex,
    cursorCoords,
    setCursorCoords,

    zoom,
    setZoom,
    setZoomLevel,
    panX,
    setPanX,
    panY,
    setPanY,
    showBoxes,
    setShowBoxes,
    showDimensions,
    setShowDimensions,
    showCrosshair,
    setShowCrosshair,
    canvasContainerRef,

    zoomIn,
    zoomOut,
    resetZoom,
    zoomToDefect,
    nextDefect,
    prevDefect,
    runInspection,
    exportReport,
    exportCsv,
  };

  return <InspectionContext.Provider value={value}>{children}</InspectionContext.Provider>;
}

export { InspectionContext };
