import axios from 'axios';

// Create a custom Axios instance pointing to your Django server
const api = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Automatically attach the token to outgoing requests
api.interceptors.request.use(
  (config) => {
    // We will store the token in localStorage upon successful login
    const token = localStorage.getItem('access');
    if (token) {
      // Your backend uses 'JWT' instead of 'Bearer'
      config.headers.Authorization = `JWT ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Catch global authentication errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // If the backend rejects the token (e.g., token version changed, expired)
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access');
      localStorage.removeItem('refresh');
      // Force the user back to the login page
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;