/**
 * PCBVision AOI API Client Service
 */

const rawEnvUrl = import.meta.env.VITE_API_URL || '';
const trimmedUrl = rawEnvUrl ? rawEnvUrl.replace(/\/+$/, '') : '';
const API_BASE = trimmedUrl
  ? (trimmedUrl.endsWith('/api') ? trimmedUrl : `${trimmedUrl}/api`)
  : '/api';

export function getApiBaseUrl() {
  return API_BASE;
}

export async function checkBackendHealth() {
  const startTime = performance.now();
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);
    const res = await fetch(`${API_BASE}/status`, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const latencyMs = Math.round(performance.now() - startTime);
    return {
      status: 'online',
      latencyMs,
      data,
      url: API_BASE,
    };
  } catch (err) {
    return {
      status: 'offline',
      latencyMs: null,
      error: err.name === 'AbortError' ? 'Timeout (6s)' : (err.message || 'Connection failed'),
      url: API_BASE,
    };
  }
}

function handleFetchError(err) {
  const msg = err?.message || String(err);
  if (
    msg.includes('Failed to fetch') ||
    msg.includes('NetworkError') ||
    msg.includes('CONNECTION_REFUSED') ||
    msg.includes('Load failed') ||
    err?.name === 'TypeError'
  ) {
    throw new Error(
      `AOI Inference Server unreachable (${API_BASE}). If hosted on Render, please allow ~30-50s for initial free-tier spin-up.`
    );
  }
  throw err;
}

export async function fetchSystemStatus() {
  try {
    const res = await fetch(`${API_BASE}/status`);
    if (!res.ok) throw new Error(`Status fetch failed: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    handleFetchError(err);
  }
}

export async function fetchSamples() {
  try {
    const res = await fetch(`${API_BASE}/samples`);
    if (!res.ok) throw new Error(`Samples fetch failed: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    handleFetchError(err);
  }
}

export function getSampleImageUrl(sampleId) {
  return `${API_BASE}/samples/${sampleId}/image?t=${Date.now()}`;
}

export async function fetchMetrics() {
  try {
    const res = await fetch(`${API_BASE}/metrics`);
    if (!res.ok) throw new Error(`Metrics fetch failed: ${res.statusText}`);
    return await res.json();
  } catch (err) {
    handleFetchError(err);
  }
}

export async function runDetection({ file, sampleId, confidence = 0.35, scaleUm = 15.0, modelChoice = 'champion' }) {
  const formData = new FormData();
  if (file) {
    formData.append('file', file, file.name || 'pcb_image.jpg');
  } else if (sampleId) {
    formData.append('sample_id', sampleId);
  } else {
    throw new Error('Must provide either a file or a sample ID for inspection');
  }

  formData.append('confidence', confidence);
  formData.append('scale_um', scaleUm);
  formData.append('model_choice', modelChoice);

  try {
    const res = await fetch(`${API_BASE}/detect`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(errorText || `Detection error ${res.status}`);
    }

    return await res.json();
  } catch (err) {
    handleFetchError(err);
  }
}
