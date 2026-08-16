/**
 * API Client Configuration
 * Handles JWT injection and transparent token refreshing.
 */

const getBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;
  if (envUrl) {
    const cleanUrl = envUrl.replace(/\/+$/, '');
    return cleanUrl.endsWith('/api/v1') ? cleanUrl : `${cleanUrl}/api/v1`;
  }
  return '/api/v1';
};

export const API_BASE = getBaseUrl();

// Internal state
let accessToken = localStorage.getItem('access_token');
let refreshToken = localStorage.getItem('refresh_token');

export const setTokens = (access, refresh) => {
  accessToken = access;
  refreshToken = refresh;
  if (access) localStorage.setItem('access_token', access);
  else localStorage.removeItem('access_token');
  
  if (refresh) localStorage.setItem('refresh_token', refresh);
  else localStorage.removeItem('refresh_token');
};

export const clearTokens = () => setTokens(null, null);

export const isAuthenticated = () => !!accessToken;

let isRefreshing = false;
let refreshSubscribers = [];

const onRefreshed = (newAccessToken) => {
  refreshSubscribers.forEach((cb) => cb(newAccessToken));
  refreshSubscribers = [];
};

const addRefreshSubscriber = (cb) => {
  refreshSubscribers.push(cb);
};

export const api = async (endpoint, options = {}) => {
  const url = `${API_BASE}${endpoint}`;
  
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  if (accessToken) {
    defaultHeaders['Authorization'] = `Bearer ${accessToken}`;
  }

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }

  let response = await fetch(url, config);

  // If 401 Unauthorized, attempt to refresh token
  if (response.status === 401 && refreshToken) {
    if (!isRefreshing) {
      isRefreshing = true;
      try {
        const refreshResponse = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshResponse.ok) {
          const data = await refreshResponse.json();
          setTokens(data.access_token, data.refresh_token);
          isRefreshing = false;
          onRefreshed(data.access_token);
          
          // Retry the original request for the caller that initiated the refresh
          config.headers['Authorization'] = `Bearer ${data.access_token}`;
          return fetch(url, config);
        } else {
          // Refresh failed, clear tokens and redirect to login
          clearTokens();
          isRefreshing = false;
          window.dispatchEvent(new CustomEvent('unauthorized'));
          return Promise.reject(new Error('Session expired'));
        }
      } catch (err) {
        clearTokens();
        isRefreshing = false;
        window.dispatchEvent(new CustomEvent('unauthorized'));
        return Promise.reject(err);
      }
    }

    // Wait for the refresh to complete, then retry the original request
    return new Promise((resolve, reject) => {
      addRefreshSubscriber((newToken) => {
        if (newToken) {
          config.headers['Authorization'] = `Bearer ${newToken}`;
          resolve(fetch(url, config));
        } else {
          reject(new Error('Session expired'));
        }
      });
    });
  }

  return response;
};
