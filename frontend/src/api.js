import axios from 'axios';

export const api = axios.create({ baseURL: '/api' });
let accessToken = localStorage.getItem('connect.access');

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

export function saveTokens(tokens) {
  accessToken = tokens.access;
  localStorage.setItem('connect.access', tokens.access);
  localStorage.setItem('connect.refresh', tokens.refresh);
}

export function clearTokens() {
  accessToken = null;
  localStorage.removeItem('connect.access');
  localStorage.removeItem('connect.refresh');
}

export async function authenticatedRequest(config) {
  try {
    return await api.request(config);
  } catch (error) {
    const refresh = localStorage.getItem('connect.refresh');
    if (error.response?.status !== 401 || !refresh || config._retried) throw error;
    config._retried = true;
    const refreshed = await axios.post('/api/auth/token/refresh/', { refresh });
    accessToken = refreshed.data.access;
    localStorage.setItem('connect.access', accessToken);
    config.headers = { ...config.headers, Authorization: `Bearer ${accessToken}` };
    return api.request(config);
  }
}

export function getErrorMessage(error) {
  const data = error.response?.data;
  if (!data) return 'The server could not be reached.';
  if (typeof data === 'string') {
    if (data.trimStart().startsWith('<')) {
      return 'The server returned an unexpected error page. Check the API server and MongoDB connection.';
    }
    return data;
  }
  if (data.detail) return data.detail;
  return Object.values(data).flat().join(' ');
}
