/* ═══════════════════════════════════════════════════════════
   Vision 5D — Auth Service
   Login, logout, session check, session persistence
   ═══════════════════════════════════════════════════════════ */

V5D.Auth = (() => {
  let _user = null;
  let _tenant = null;
  let _authenticated = false;
  let _ready = false;

  const listeners = [];

  function onChange(fn) { listeners.push(fn); }
  function _notify() { listeners.forEach(fn => fn({ user: _user, tenant: _tenant, authenticated: _authenticated })); }

  async function checkSession() {
    try {
      const d = await V5D.API.post('/api/v1/auth/refresh');
      _user = { id: d.user_id, tenant_id: d.tenant_id };
      _tenant = { id: d.tenant_id };
      _authenticated = true;
    } catch (e) {
      _user = null;
      _tenant = null;
      _authenticated = false;
    }
    _ready = true;
    _notify();
    return _authenticated;
  }

  async function login(provider) {
    const d = await V5D.API.post('/api/v1/auth/login', {
      provider: provider || 'google',
      oauth_token: 'demo'
    });
    _user = { id: d.user_id, tenant_id: d.tenant_id };
    _tenant = { id: d.tenant_id };
    _authenticated = true;
    _notify();
    V5D.Events.emit('auth:login', _user);
    return _user;
  }

  async function logout() {
    try { await V5D.API.post('/api/v1/auth/logout'); } catch (e) { /* ignore */ }
    _user = null;
    _tenant = null;
    _authenticated = false;
    _notify();
    V5D.Events.emit('auth:logout');
  }

  function getUser() { return _user; }
  function getTenant() { return _tenant; }
  function isAuthenticated() { return _authenticated; }
  function isReady() { return _ready; }

  return { checkSession, login, logout, getUser, getTenant, isAuthenticated, isReady, onChange };
})();
