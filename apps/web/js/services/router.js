/* ═══════════════════════════════════════════════════════════
   Vision 5D — Simple Event Emitter
   Used for cross-module communication without a state framework
   ═══════════════════════════════════════════════════════════ */

window.V5D = window.V5D || {};

V5D.Events = (() => {
  const _listeners = {};

  function on(event, fn) {
    if (!_listeners[event]) _listeners[event] = [];
    _listeners[event].push(fn);
    return () => off(event, fn);
  }

  function off(event, fn) {
    if (!_listeners[event]) return;
    _listeners[event] = _listeners[event].filter(f => f !== fn);
  }

  function emit(event, data) {
    if (!_listeners[event]) return;
    _listeners[event].forEach(fn => {
      try { fn(data); } catch (e) { console.error('[V5D.Events]', event, e); }
    });
  }

  return { on, off, emit };
})();

/* ═══════════════════════════════════════════════════════════
   Vision 5D — Router
   Simple hash-based router — no library dependency
   ═══════════════════════════════════════════════════════════ */

V5D.Router = (() => {
  const _routes = {};
  let _currentRoute = null;

  function register(path, handler) {
    _routes[path] = handler;
  }

  function navigate(path, data) {
    if (path === _currentRoute && !data) return;
    window.location.hash = '#' + path;
    _currentRoute = path;
    const handler = _routes[path];
    if (handler) {
      handler(data);
      V5D.Events.emit('route:changed', { path, data });
    }
    _updateSidebarActive(path);
  }

  function getCurrentRoute() { return _currentRoute; }

  function _updateSidebarActive(path) {
    document.querySelectorAll('.sidebar-link').forEach(el => {
      const route = el.getAttribute('data-route');
      el.classList.toggle('active', route === path);
    });
  }

  /* Listen for hash changes (browser back/forward) */
  window.addEventListener('hashchange', () => {
    const hash = window.location.hash.replace('#', '') || 'dashboard';
    if (hash !== _currentRoute) {
      navigate(hash);
    }
  });

  /* Initial load */
  function start() {
    const hash = window.location.hash.replace('#', '') || 'dashboard';
    navigate(hash);
  }

  return { register, navigate, getCurrentRoute, start };
})();
