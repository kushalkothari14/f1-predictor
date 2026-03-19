// hooks/useF1Api.js
import { useState, useEffect } from "react";
import axios from "axios";

const BASE = process.env.REACT_APP_API_URL || "/api";

export function useSchedule(year) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);

  useEffect(() => {
    if (!year) return;
    setLoading(true);
    axios.get(`${BASE}/schedule/${year}`)
      .then(r => { setData(r.data); setError(null); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [year]);

  return { data, loading, error };
}

export function usePrediction(year, round) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState(null);

  useEffect(() => {
    if (!year || !round) return;
    setLoading(true);
    setData(null);
    setError(null);
    axios.get(`${BASE}/predict/${year}/${round}`)
      .then(r => { setData(r.data); })
      .catch(e => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, [year, round]);

  return { data, loading, error };
}

export function useHealth() {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    axios.get(`${BASE}/health`).then(r => setReady(r.data.modelsReady)).catch(() => setReady(false));
  }, []);
  return ready;
}
