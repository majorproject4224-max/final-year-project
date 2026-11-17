import axios from 'axios';

export const API_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');
export const WS_URL = (import.meta.env.VITE_WS_URL || window.location.origin.replace(/^http/, 'ws')).replace(/\/$/, '');
export const api = axios.create({ baseURL: API_URL, timeout: 90000 });
let refreshing = null;

export function saveTokens(tokens) {
  sessionStorage.setItem('connect.access', tokens.access);
  sessionStorage.setItem('connect.refresh', tokens.refresh);
}
export function clearTokens() {
  sessionStorage.removeItem('connect.access');
  sessionStorage.removeItem('connect.refresh');
  // Remove credentials left by the earlier prototype.
  localStorage.removeItem('connect.access');
  localStorage.removeItem('connect.refresh');
}
api.interceptors.request.use(config => {
  const access = sessionStorage.getItem('connect.access');
  if (access && !config.skipAuth) config.headers.Authorization = `Bearer ${access}`;
  return config;
});
api.interceptors.response.use(response => response, async error => {
  const config = error.config;
  if (!config || config.skipAuth || config._retried || error.response?.status !== 401) throw error;
  const refresh = sessionStorage.getItem('connect.refresh');
  if (!refresh) throw error;
  config._retried = true;
  try {
    if (!refreshing) {
      refreshing = axios.post(`${API_URL}/auth/token/refresh/`, { refresh }, { timeout: 90000 })
        .then(({ data }) => { saveTokens(data); return data; })
        .finally(() => { refreshing = null; });
    }
    const tokens = await refreshing;
    config.headers.Authorization = `Bearer ${tokens.access}`;
    return api.request(config);
  } catch (refreshError) {
    if ([400, 401, 403].includes(refreshError.response?.status)) {
      clearTokens();
      window.dispatchEvent(new Event('connect-session-ended'));
    }
    throw refreshError;
  }
});
export const authenticatedRequest = config => api.request(config);
export function getErrorMessage(error) {
  const data = error.response?.data;
  if (!data) return 'The backend could not be reached. A sleeping free server can take about a minute to wake up. Try again.';
  if (typeof data === 'string') return data.startsWith('<') ? 'The server is starting or temporarily unavailable. Please retry.' : data;
  if (data.detail) return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
  return Object.entries(data).filter(([key]) => key !== 'code').map(([key, value]) => `${key.replaceAll('_', ' ')}: ${Array.isArray(value) ? value.join(' ') : String(value)}`).join(' ');
}
