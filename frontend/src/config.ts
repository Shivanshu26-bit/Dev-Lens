/**
 * Frontend application configuration.
 *
 * Resolves the backend API base URL:
 * - If VITE_API_URL is explicitly set (e.g. 'https://api.devlens.example.com' or '' for same-origin proxy), use it.
 * - If VITE_API_URL is undefined, default to 'http://localhost:8000' for local development.
 */
export const API_BASE_URL: string =
  typeof import.meta.env.VITE_API_URL === 'string'
    ? import.meta.env.VITE_API_URL
    : 'http://localhost:8000';
