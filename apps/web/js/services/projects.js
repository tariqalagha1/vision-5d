/* ═══════════════════════════════════════════════════════════
   Vision 5D — Projects & Dashboard Data Service
   Uses LIVE authenticated API. NO production fixtures.
   ═══════════════════════════════════════════════════════════ */

V5D.Projects = (() => {

  /* ── Projects ── */

  async function listProjects(workspaceId) {
    const d = await V5D.API.get(`/api/v1/workspaces/${workspaceId}/projects`);
    return (d.projects || []).map(p => ({
      project_id: p.project_id,
      workspace_id: p.workspace_id,
      name: p.name,
      state: p.state,
      project_type: p.project_type || 'other',
      created_at: p.created_at,
      rooms: 0, walls: 0, scenes: 0, /* populated on detail */
    }));
  }

  async function createProject(workspaceId, name, projectType) {
    const p = await V5D.API.post(`/api/v1/workspaces/${workspaceId}/projects`, {
      workspace_id: workspaceId,
      name,
      project_type: projectType || 'other'
    });
    return {
      project_id: p.project_id,
      workspace_id: p.workspace_id,
      name: p.name,
      state: p.state,
      project_type: p.project_type,
      created_at: p.created_at,
      rooms: 0, walls: 0, scenes: 0,
    };
  }

  async function getProject(projectId) {
    /* No single-project GET — use list and filter */
    return null; /* Future: GET /api/v1/projects/{id} */
  }

  /* ── Dashboard Stats ── */

  async function getStats() {
    try {
      const d = await V5D.API.get('/api/v1/dashboard/stats');
      return {
        total_projects: d.total_projects || 0,
        active_projects: d.active_projects || 0,
        total_scenes: d.total_scenes || 0,
        total_revisions: d.total_revisions || 0,
        conflict_count: d.conflict_count || 0,
        failed_sync_count: d.failed_sync_count || 0,
        sync_health: d.sync_health || 'unknown',
        ai_configured: d.ai_providers_configured || 0,
        ai_healthy: d.ai_providers_healthy || 0,
      };
    } catch (e) {
      console.warn('[V5D.Projects] Stats unavailable:', e.message);
      return {
        total_projects: 0, active_projects: 0, total_scenes: 0,
        total_revisions: 0, conflict_count: 0, failed_sync_count: 0,
        sync_health: 'unavailable', ai_configured: 0, ai_healthy: 0,
        _error: e.message
      };
    }
  }

  /* ── Activity Feed ── */

  async function getActivity(limit = 10) {
    try {
      const d = await V5D.API.get(`/api/v1/dashboard/activity?limit=${limit}`);
      return (d.activity || []).map(a => ({
        id: a.id,
        type: a.type,
        project_id: a.project_id,
        project: a.project_name || a.project || a.project_id || '',
        title: a.title,
        state: a.state,
        time: a.time,
        icon: a.icon || '•'
      }));
    } catch (e) {
      console.warn('[V5D.Projects] Activity unavailable:', e.message);
      return [];
    }
  }

  /* ── Pascal Health ── */

  async function getPascalHealth() {
    try {
      return await V5D.API.get('/api/v1/dashboard/pascal-health');
    } catch (e) {
      return {
        status: 'unavailable', adapter_installed: false,
        integration_status: 'unknown', credentials_exposed_to_browser: false,
        _error: e.message
      };
    }
  }

  /* ── Scene Data ── */

  async function getScene(projectId) {
    return V5D.API.get(`/api/v4/projects/${projectId}/scene`);
  }

  async function getSceneVersions(projectId) {
    return V5D.API.get(`/api/v4/projects/${projectId}/scene/versions`);
  }

  /* ── Workspace Discovery (survives server restarts) ── */

  let _cachedWorkspaceId = null;

  async function getWorkspaceId() {
    if (_cachedWorkspaceId) return _cachedWorkspaceId;

    /* Try sessionStorage (survives page reloads) */
    try {
      const cached = sessionStorage.getItem('v5d_workspace_id');
      if (cached) { _cachedWorkspaceId = cached; return cached; }
    } catch(e) { /* sessionStorage unavailable */ }

    /* Auto-discover from backend */
    try {
      const d = await V5D.API.get('/api/v1/workspaces');
      if (d.default_workspace_id) {
        _cachedWorkspaceId = d.default_workspace_id;
        try { sessionStorage.setItem('v5d_workspace_id', d.default_workspace_id); } catch(e) {}
        return d.default_workspace_id;
      }
      /* Use first workspace from list */
      if (d.workspaces && d.workspaces.length > 0) {
        _cachedWorkspaceId = d.workspaces[0].workspace_id;
        try { sessionStorage.setItem('v5d_workspace_id', _cachedWorkspaceId); } catch(e) {}
        return _cachedWorkspaceId;
      }
    } catch(e) {
      /* Propagate AUTH_EXPIRED so caller can show login prompt */
      if (e.code === 'AUTH_EXPIRED') throw e;
      console.warn('[V5D.Projects] Workspace discovery failed:', e.message);
    }

    /* Ultimate fallback — auto-create a workspace */
    try {
      const ws = await V5D.API.post('/api/v1/workspaces', {
        name: 'Default Workspace', description: 'Auto-created workspace'
      });
      _cachedWorkspaceId = ws.workspace_id;
      try { sessionStorage.setItem('v5d_workspace_id', ws.workspace_id); } catch(e) {}
      return ws.workspace_id;
    } catch(e) {
      if (e.code === 'AUTH_EXPIRED') throw e;
      console.error('[V5D.Projects] Workspace creation failed:', e.message);
      throw { code: 'WORKSPACE_ERROR', message: 'Could not discover or create workspace' };
    }
  }

  function clearWorkspaceCache() {
    _cachedWorkspaceId = null;
    try { sessionStorage.removeItem('v5d_workspace_id'); } catch(e) {}
  }

  function useFixtures() { return false; }

  return {
    listProjects, createProject, getProject,
    getStats, getActivity, getPascalHealth,
    getScene, getSceneVersions,
    getWorkspaceId, clearWorkspaceCache,
    useFixtures
  };
})();
