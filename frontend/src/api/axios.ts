import axios from 'axios';
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL, timeout: 30000 });
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    if (token)
        config.headers.Authorization = `Bearer ${token}`;
    return config;
});
api.interceptors.response.use(response => response, error => {
    const url = error.config?.url;
    if (error.response?.status === 401 && url !== '/auth/login' && url !== '/auth/register') {
        const currentToken = localStorage.getItem('access_token');
        // An older request must not invalidate a newly signed-in session.
        if (!currentToken || error.config?.headers?.Authorization === `Bearer ${currentToken}`) {
            localStorage.removeItem('access_token');
            window.dispatchEvent(new Event('session-expired'));
        }
    }
    return Promise.reject(error);
});
export function apiError(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
    if (axios.isAxiosError(error)) {
        if (!error.response)
            return 'We could not reach the server. Check your connection and try again.';
        const message = error.response.data?.message;
        if (typeof message === 'string')
            return message;
    }
    return fallback;
}
export default api;
