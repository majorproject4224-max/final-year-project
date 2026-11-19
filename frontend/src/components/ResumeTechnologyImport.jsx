import { useState } from 'react';
import { api, getErrorMessage } from '../api';
import { ErrorBox } from './UI';

export default function ResumeTechnologyImport({ options, onApply }) {
  const [suggestions, setSuggestions] = useState(null), [busy, setBusy] = useState(false), [error, setError] = useState('');
  async function read(e) {
    const file = e.target.files[0]; if (!file) return;
    setError(''); setSuggestions(null);
    if (file.size > 5 * 1024 * 1024) { setError('Choose a file smaller than 5 MB.'); return; }
    setBusy(true);
    try {
      const body = new FormData(); body.append('resume', file);
      const { data } = await api.post('/profiles/resume-suggestions/', body);
      const found = new Set((data.suggestions.skills || []).map(value => value.trim().toLowerCase()));
      const mapped = Object.fromEntries(['languages', 'databases', 'frameworks', 'platforms'].map(key => [key, (options?.[key] || []).filter(value => found.has(value))]));
      setSuggestions(mapped);
    } catch (e) { setError(getErrorMessage(e)); } finally { setBusy(false); e.target.value = ''; }
  }
  return <details className="resume-panel"><summary>Import from Resume</summary><div className="resume-content">
    <p>Optional: suggest used technologies from a PDF or DOCX. We do not infer future interests or coding years from a resume.</p>
    <label className="file-picker">Choose Resume<input aria-label="Choose Resume" type="file" accept=".pdf,.docx" onChange={read} disabled={busy || !options} /></label>
    {busy && <p role="status">Reading your resume…</p>}<ErrorBox message={error} />
    {suggestions && <><h3>Review suggestions</h3><p>{Object.values(suggestions).flat().join(', ') || 'No supported technologies found. Add your answers manually.'}</p><button type="button" onClick={() => { onApply(suggestions); setSuggestions(null); }}>Use these suggestions</button></>}
  </div></details>;
}
