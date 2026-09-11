/* ═══════════════════════════════════════════════════════════
   Vision 5D — Base API Client
   Shared fetch wrapper with auth, error handling, retries
   ═══════════════════════════════════════════════════════════ */

const V5D = window.V5D || {};

V5D.API = (() => {
  const BASE = window.V5D_API_BASE || window.location.origin;

  async function request(method, path, body) {
    const headers = { 'Content-Type': 'application/json' };
    const opts = { method, headers, credentials: 'include' };
    if (body) opts.body = JSON.stringify(body);

    let response;
    try {
      response = await fetch(BASE + path, opts);
    } catch (err) {
      throw { code: 'NETWORK_ERROR', message: 'Cannot reach Vision 5D API. Make sure the backend is running on port 8000.' };
    }

    if (response.status === 401) {
      V5D.Events.emit('auth:expired');
      throw { code: 'AUTH_EXPIRED', message: 'Session expired. Please sign in again.' };
    }

    if (response.status === 429) {
      const retryAfter = response.headers.get('Retry-After') || 30;
      throw { code: 'RATE_LIMITED', message: `Rate limited. Retry after ${retryAfter}s.` };
    }

    if (response.status === 404) {
      throw { code: 'NOT_FOUND', message: 'Resource not found.' };
    }

    if (response.status === 403) {
      throw { code: 'FORBIDDEN', message: 'You do not have access to this resource.' };
    }

    let data;
    try {
      data = await response.json();
    } catch {
      data = {};
    }

    if (!response.ok) {
      throw { code: 'API_ERROR', status: response.status, message: data.message || data.detail || 'API error', data };
    }

    return data;
  }

  return {
    BASE,
    get: (path) => request('GET', path),
    post: (path, body) => request('POST', path, body),
    patch: (path, body) => request('PATCH', path, body),
    put: (path, body) => request('PUT', path, body),
    delete: (path) => request('DELETE', path),
    upload: async (path, formData) => {
      const opts = { method: 'POST', body: formData, credentials: 'include' };
      const r = await fetch(BASE + path, opts);
      if (!r.ok) throw { code: 'UPLOAD_ERROR', message: 'Upload failed' };
      return r.json();
    }
  };
})();
