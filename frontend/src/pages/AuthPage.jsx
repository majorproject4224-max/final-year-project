import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ErrorBox } from '../components/UI';
import { getErrorMessage } from '../api';
export default function AuthPage({ register = false }) {
  const { user, authenticate } = useAuth();
  const [mode, setMode] = useState(register ? 'register' : 'login');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  if (user) return <Navigate to="/" replace />;
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try { await authenticate(mode, Object.fromEntries(new FormData(event.currentTarget))); }
    catch (e) { setError(getErrorMessage(e)); }
    finally { setBusy(false); }
  }
  return <main className="auth-page"><section className="auth-story"><LinkBrand /><p className="eyebrow">A CAMPUS FULL OF POSSIBILITIES</p><h1>Good projects<br />start with<br /><em>good people.</em></h1><p>Find your people. Share your skills.<br />Build something that matters.</p><div className="auth-note">connecT AI · University collaboration</div></section><section className="auth-panel"><div className="auth-form"><p className="eyebrow">YOUR NEXT CHAPTER</p><h2>{mode === 'login' ? 'Welcome back.' : 'Find your community.'}</h2><div className="tabs"><button className={mode === 'login' ? 'active' : ''} onClick={() => { setMode('login'); setError(''); }}>Sign in</button><button className={mode === 'register' ? 'active' : ''} onClick={() => { setMode('register'); setError(''); }}>Join campus</button></div><ErrorBox message={error} /><form onSubmit={submit}>{mode === 'register' && <label>Your name<input name="name" required maxLength={80} autoComplete="name" /></label>}<label>Email<input name="email" type="email" required autoComplete="email" /></label><label>Password<input name="password" type="password" required minLength={8} maxLength={128} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} /></label>{mode === 'register' && <p className="muted">Use at least 8 characters. Avoid common or entirely numeric passwords.</p>}<button className="primary full" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in →' : 'Create account →'}</button></form><p className="fine-print">Made for respectful academic collaboration.<br />A free backend may take a minute to wake up.</p></div></section></main>;
}
function LinkBrand() { return <div className="brand">connecT<span>.</span></div>; }
