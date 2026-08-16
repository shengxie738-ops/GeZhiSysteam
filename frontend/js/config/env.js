const DEFAULT_API_ORIGIN = 'https://gezhisystem.com';
const LOCAL_DEV_API_ORIGIN = 'http://127.0.0.1:8516';

function normalizeApiOrigin(value) {
    const origin = String(value || '').trim().replace(/\/+$/, '');
    return origin.endsWith('/api') ? origin.slice(0, -4) : origin;
}

function readRuntimeApiOrigin() {
    const viteOrigin = import.meta.env?.VITE_API_ORIGIN || import.meta.env?.VITE_API_BASE_URL;
    if (viteOrigin) return viteOrigin;

    if (typeof window !== 'undefined') {
        return (
            window.__API_ORIGIN__ ||
            window.__API_BASE_URL__ ||
            window.localStorage?.getItem('apiOrigin') ||
            window.localStorage?.getItem('API_ORIGIN')
        );
    }

    return '';
}

function inferDefaultApiOrigin() {
    if (typeof window !== 'undefined') {
        const hostname = window.location?.hostname;
        if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1') {
            return LOCAL_DEV_API_ORIGIN;
        }
    }

    return DEFAULT_API_ORIGIN;
}

export const API_ORIGIN = normalizeApiOrigin(readRuntimeApiOrigin() || inferDefaultApiOrigin());
export const API_BASE_URL = `${API_ORIGIN}/api`;

export function toBackendAssetUrl(path) {
    if (!path) return '';
    if (/^https?:\/\//i.test(path)) return path;
    return path.startsWith('/') ? `${API_ORIGIN}${path}` : path;
}
