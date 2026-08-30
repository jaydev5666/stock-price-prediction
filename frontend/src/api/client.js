const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export async function searchTickers(query) {
  const res = await fetch(`${API_BASE}/tickers?query=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error(`Failed to search tickers: ${res.statusText}`);
  return res.json();
}

export async function fetchStockHistory(ticker, range = '1y') {
  const res = await fetch(`${API_BASE}/stock/${encodeURIComponent(ticker)}/history?range=${range}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch history for ${ticker}`);
  }
  return res.json();
}

export async function requestPrediction(ticker, horizonDays = 7, forceRetrain = false) {
  const res = await fetch(`${API_BASE}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ticker,
      horizon_days: horizonDays,
      force_retrain: forceRetrain
    })
  });

  const data = await res.json();
  if (res.status === 200 || res.status === 202) {
    return data;
  }
  throw new Error(data.detail || `Prediction request failed: ${res.statusText}`);
}

export async function checkJobStatus(jobId) {
  const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch job status for ${jobId}`);
  }
  return res.json();
}

export async function fetchCachedPrediction(ticker, horizonDays = 7) {
  const res = await fetch(`${API_BASE}/predict/${encodeURIComponent(ticker)}?horizon_days=${horizonDays}`);
  if (!res.ok) return null;
  return res.json();
}
