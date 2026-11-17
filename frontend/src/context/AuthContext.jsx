import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api, clearTokens, getErrorMessage, saveTokens } from '../api';
const Context = createContext(null);
export const useAuth = () => useContext(Context);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      if (!sessionStorage.getItem('connect.access')) {
        setUser(null);
        return;
      }
      const account = await api.get('/auth/me/');
      setUser(account.data);
      try {
        setProfile((await api.get('/profiles/me/')).data);
      } catch (e) {
        if (e.response?.status === 404) setProfile(null);
        else throw e;
      }
    } catch (e) {
      if (e.response?.status === 401) {
        clearTokens();
        setUser(null);
      } else setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    const ended = () => {
      setUser(null);
      setProfile(null);
      setToast('Your session ended. Please sign in again.');
    };
    window.addEventListener('connect-session-ended', ended);
    return () => window.removeEventListener('connect-session-ended', ended);
  }, []);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(''), 6500);
    return () => clearTimeout(timer);
  }, [toast]);
  async function authenticate(mode, values) {
    const { data } = await api.post(`/auth/${mode}/`, values, { skipAuth: true });
    saveTokens(data.tokens);
    setUser(data.user);
    try {
      setProfile((await api.get('/profiles/me/')).data);
    } catch (e) {
      if (e.response?.status === 404) setProfile(null);
      else throw e;
    }
  }
  async function logout() {
    try {
      await api.post('/auth/logout/');
    } catch (e) {
      setToast(getErrorMessage(e));
      return;
    }
    clearTokens();
    setUser(null);
    setProfile(null);
  }
  return (
    <Context.Provider
      value={{
        user,
        profile,
        setProfile,
        setUser,
        loading,
        error,
        retry: load,
        authenticate,
        logout,
        notify: setToast,
      }}
    >
      {children}
      {toast && (
        <div role="status" className="toast">
          <span>{toast}</span>
          <button aria-label="Dismiss notification" onClick={() => setToast('')}>
            ×
          </button>
        </div>
      )}
    </Context.Provider>
  );
}
