import { useState } from 'react';
import { api, clearTokens, getErrorMessage } from '../api';
import { useAuth } from '../context/AuthContext';
import { PageTitle, ErrorBox } from '../components/UI';
export default function SettingsPage() {
  const { user, notify } = useAuth();
  const [current, setCurrent] = useState(''),
    [password, setPassword] = useState(''),
    [confirm, setConfirm] = useState(''),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setError('');
    if (password !== confirm) {
      setError('The new passwords do not match.');
      return;
    }
    setBusy(true);
    try {
      await api.patch('/auth/me/', { current_password: current, new_password: password });
      clearTokens();
      window.dispatchEvent(new Event('connect-session-ended'));
      notify('Password changed. Sign in with your new password.');
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageTitle title="Account settings">{user.email}</PageTitle>
      <form className="card form-grid form-width" onSubmit={submit}>
        <h2 className="full">Change password</h2>
        <p className="full muted">Changing your password signs you out on all devices.</p>
        <label className="full">
          Current password
          <input
            required
            type="password"
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
          />
        </label>
        <label>
          New password
          <input
            required
            type="password"
            minLength={8}
            maxLength={128}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <label>
          Confirm new password
          <input
            required
            type="password"
            minLength={8}
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        </label>
        <div className="full">
          <ErrorBox message={error} />
          <button className="primary" disabled={busy}>
            Change password
          </button>
        </div>
      </form>
    </>
  );
}
