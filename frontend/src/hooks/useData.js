import { useCallback, useEffect, useRef, useState } from 'react';
import { api, getErrorMessage } from '../api';
export function useData(url) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(Boolean(url));
  const [error, setError] = useState('');
  const current = useRef(0);
  const reload = useCallback(async () => {
    const generation = ++current.current;
    if (!url) { setData(null); setLoading(false); return; }
    setLoading(true); setError('');
    try { const response = await api.get(url); if (current.current === generation) setData(response.data); }
    catch (e) { if (current.current === generation) setError(getErrorMessage(e)); }
    finally { if (current.current === generation) setLoading(false); }
  }, [url]);
  useEffect(() => { setData(null); reload(); return () => { current.current++; }; }, [reload]);
  return { data, setData, loading, error, reload };
}
