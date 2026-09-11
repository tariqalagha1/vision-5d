/* ═══════════════════════════════════════════════════════════
   Vision 5D — Dashboard Views (Live Data)
   Connected to authenticated backend. Handles all states:
   loading, empty, error, partial, stale, unavailable.
   ═══════════════════════════════════════════════════════════ */

V5D.Views = (() => {
  const C = V5D.Components;
  const P = V5D.Projects;

  /* ── Dashboard View ── */
  async function renderDashboard() {
    const header = document.getElementById('app-header');
    const online = V5D.Auth.isAuthenticated();
    header.innerHTML = C.Header('Dashboard', online ? 'connected' : 'disconnected');

    const content = document.getElementById('app-content');

    /* Quick Actions */
    let html = '<div class="quick-actions">';
    html += C.QuickAction('➕', 'New Project', "V5D.Views.showCreateProjectDialog()", true);
    html += C.QuickAction('🎬', 'Photo → Video', "V5D.Router.navigate('pipeline')", true);
    html += C.QuickAction('📥', 'Import CAD', "V5D.Router.navigate('files')");
    html += C.QuickAction('🏗️', 'Open Studio', "window.open('studio.html','v5d_studio','width=1400,height=900')");
    html += C.QuickAction('⚙️', 'AI Settings', "window.open('ai-setup.html','v5d_ai','width=550,height=700')");
    html += '</div>';

    /* Stats */
    html += '<div id="dashboard-stats">' + C.LoadingSkeleton('stats') + '</div>';

    /* Two-column */
    html += '<div class="content-grid">';
    html += '<div>';
    html += '<div class="card"><div class="card-header"><span class="card-title">Recent Projects</span><button class="btn btn-sm btn-secondary" onclick="V5D.Router.navigate(\'projects\')">View All</button></div>';
    html += '<div id="dashboard-projects">' + C.LoadingSkeleton('projects') + '</div></div>';
    html += '</div>';
    html += '<div>';
    html += '<div class="card"><div class="card-header"><span class="card-title">System Health</span></div>';
    html += '<div id="system-health">' + C.LoadingSkeleton('text') + '</div></div>';
    html += '<div class="card" style="margin-top:16px"><div class="card-header"><span class="card-title">Recent Activity</span></div>';
    html += '<div id="dashboard-activity" class="activity-feed">' + C.LoadingSkeleton('text') + '</div></div>';
    html += '</div>';
    html += '</div>';

    content.innerHTML = html;

    /* Safety: replace skeletons after 10s if data hasn't loaded */
    const skeletonTimeout = setTimeout(() => {
      ['dashboard-stats', 'dashboard-projects', 'system-health', 'dashboard-activity'].forEach(id => {
        const el = document.getElementById(id);
        if (el && el.querySelector('.skeleton')) {
          el.innerHTML = V5D.Components.ErrorState('⏱️', 'Loading timed out',
            'The dashboard data could not be loaded. The API may be unavailable.',
            'V5D.Views.renderDashboard()');
        }
      });
    }, 10000);

    /* Load async — each section clears its own skeleton */
    _loadStats();
    _loadProjects();
    _loadHealth();
    _loadActivity();
  }

  async function _loadStats() {
    const container = document.getElementById('dashboard-stats');
    if (!container) return;

    try {
      const stats = await P.getStats();

      if (stats._error && stats.total_projects === 0) {
        container.innerHTML = C.ErrorState('⚠️', 'Could not load statistics', stats._error, 'V5D.Views.renderDashboard()');
        return;
      }

      container.innerHTML = '<div class="stats-grid">' +
        C.StatCard('📁', stats.total_projects, 'Total Projects', null, null, 'var(--v5d-accent-light)') +
        C.StatCard('✅', stats.active_projects, 'Active', null, null, 'var(--v5d-success-bg)') +
        C.StatCard('🏗️', stats.total_scenes, '3D Scenes', null, null, 'var(--v5d-warning-bg)') +
        C.StatCard('📝', stats.total_revisions, 'Revisions', stats.conflict_count > 0 ? `${stats.conflict_count} conflicts` : null, stats.conflict_count > 0 ? 'down' : null, 'var(--v5d-info-bg)') +
        C.StatCard('⚠️', stats.failed_sync_count || 0, 'Failed Syncs', stats.failed_sync_count > 0 ? 'Attention' : null, stats.failed_sync_count > 0 ? 'down' : null, 'var(--v5d-error-bg)') +
        '</div>';
    } catch (e) {
      container.innerHTML = C.ErrorState('⚠️', 'Statistics unavailable', 'Backend may be offline', 'V5D.Views.renderDashboard()');
    }
  }

  async function _loadProjects() {
    const container = document.getElementById('dashboard-projects');
    if (!container) return;

    try {
      const wsId = await _getWorkspaceId();
      const projects = await P.listProjects(wsId);

      if (projects.length === 0) {
        container.innerHTML = C.EmptyState('📁', 'No projects yet', 'Create your first architectural project to get started.', 'Create Project', "V5D.Views.showCreateProjectDialog()");
        return;
      }

      container.innerHTML = '<div class="project-grid">' + projects.slice(0, 6).map(p => C.ProjectCard(p)).join('') + '</div>';
    } catch (e) {
      if (e.code === 'AUTH_EXPIRED') {
        container.innerHTML = C.EmptyState('🔑', 'Session expired', 'Please sign in again.');
      } else {
        container.innerHTML = C.ErrorState('⚠️', 'Could not load projects', e.message || 'API unavailable', 'V5D.Views.renderDashboard()');
      }
    }
  }

  async function _loadHealth() {
    const container = document.getElementById('system-health');
    if (!container) return;

    let html = '<div style="display:flex;flex-direction:column;gap:8px;font-size:13px">';

    /* AI Status */
    try {
      const stats = await P.getStats();
      const aiOk = stats.ai_healthy > 0;
      html += `<div style="display:flex;align-items:center;gap:8px">
        <div style="width:8px;height:8px;border-radius:50%;background:${aiOk ? 'var(--v5d-success)' : 'var(--v5d-text-tertiary)'}"></div>
        <span>AI Providers: ${aiOk ? C.StatusBadge(stats.ai_healthy + ' healthy', 'success') : C.StatusBadge('Not configured', 'warning')}</span>
      </div>`;
    } catch(e) {
      html += '<div>AI: ' + C.StatusBadge('Unknown', 'neutral') + '</div>';
    }

    /* Pascal Status */
    try {
      const pascal = await P.getPascalHealth();
      const pascalOk = pascal.status === 'operational';
      html += `<div style="display:flex;align-items:center;gap:8px">
        <div style="width:8px;height:8px;border-radius:50%;background:${pascalOk ? 'var(--v5d-success)' : 'var(--v5d-error)'}"></div>
        <span>Pascal Integration: ${pascalOk ? C.StatusBadge('Live v' + pascal.pascal_version, 'success') : C.StatusBadge('Unavailable', 'error')}</span>
      </div>`;
    } catch(e) {
      html += '<div>Pascal: ' + C.StatusBadge('Unavailable', 'warning') + '</div>';
    }

    /* Sync Health */
    try {
      const stats = await P.getStats();
      html += `<div style="display:flex;align-items:center;gap:8px">
        <div style="width:8px;height:8px;border-radius:50%;background:${stats.sync_health === 'healthy' ? 'var(--v5d-success)' : 'var(--v5d-warning)'}"></div>
        <span>Synchronization: ${C.StatusBadge(stats.sync_health, stats.sync_health === 'healthy' ? 'success' : 'warning')}</span>
      </div>`;
    } catch(e) {
      html += '<div>Sync: ' + C.StatusBadge('Unknown', 'neutral') + '</div>';
    }

    html += '</div>';
    container.innerHTML = html;
  }

  async function _loadActivity() {
    const container = document.getElementById('dashboard-activity');
    if (!container) return;

    try {
      const activity = await P.getActivity(8);
      if (activity.length === 0) {
        container.innerHTML = '<div class="state-container"><div class="state-description">No recent activity. Create a project to get started.</div></div>';
        return;
      }
      container.innerHTML = activity.map(a => C.ActivityItem(a)).join('');
    } catch (e) {
      container.innerHTML = '<div class="state-container"><div class="state-description">Activity feed unavailable</div></div>';
    }
  }

  /* ── Projects List View ── */
  async function renderProjects() {
    const header = document.getElementById('app-header');
    header.innerHTML = C.Header('Projects', V5D.Auth.isAuthenticated() ? 'connected' : 'disconnected');

    const content = document.getElementById('app-content');
    content.innerHTML = `
      <div class="page-header">
        <h1>Projects</h1>
        <p>Manage your architectural projects</p>
      </div>
      <div class="quick-actions">
        ${C.QuickAction('➕', 'New Project', "V5D.Views.showCreateProjectDialog()", true)}
      </div>
      <div id="projects-list">${C.LoadingSkeleton('projects')}</div>`;

    try {
      const wsId = await _getWorkspaceId();
      const projects = await P.listProjects(wsId);
      const container = document.getElementById('projects-list');
      if (projects.length === 0) {
        container.innerHTML = C.EmptyState('📁', 'No projects', 'Create your first architectural project.', 'Create Project', "V5D.Views.showCreateProjectDialog()");
        return;
      }
      container.innerHTML = '<div class="project-grid">' + projects.map(p => C.ProjectCard(p)).join('') + '</div>';
    } catch (e) {
      document.getElementById('projects-list').innerHTML = C.ErrorState('⚠️', 'Could not load projects', e.message || 'API error', 'V5D.Views.renderProjects()');
    }
  }

  /* ── Project Detail ── */
  async function renderProjectDetail(projectId) {
    const header = document.getElementById('app-header');
    header.innerHTML = C.Header('Project', V5D.Auth.isAuthenticated() ? 'connected' : 'disconnected');
    const content = document.getElementById('app-content');

    content.innerHTML = `
      <div class="page-header"><h1>Project Detail</h1><p>Loading...</p></div>
      <div class="stats-grid">${C.LoadingSkeleton('stats')}</div>`;

    try {
      /* Try to get scene data for stats */
      let sceneStats = { rooms: 0, walls: 0 };
      try {
        const scene = await P.getScene(projectId);
        const s = scene.statistics || {};
        sceneStats = { rooms: s.room_count || 0, walls: s.wall_count || 0 };
      } catch(e) { /* scene may not exist yet */ }

      content.innerHTML = `
        <div class="page-header">
          <h1>Project</h1>
          <p>${C.StatusBadge('Active', 'success')} • ${new Date().toLocaleDateString()}</p>
        </div>
        <div class="stats-grid">
          ${C.StatCard('🚪', sceneStats.rooms, 'Rooms')}
          ${C.StatCard('🧱', sceneStats.walls, 'Walls')}
          ${C.StatCard('🎬', '—', 'Scenes')}
          ${C.StatCard('📝', '—', 'Revisions')}
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">Actions</span></div>
          <div class="quick-actions">
            ${C.QuickAction('🏗️', 'Open Studio', "window.open('studio.html','v5d_studio')")}
            ${C.QuickAction('📊', 'View Scenes', "V5D.Router.navigate('scenes')")}
          </div>
        </div>`;
    } catch(e) {
      content.innerHTML = C.ErrorState('⚠️', 'Could not load project', e.message || '', "V5D.Router.navigate('dashboard')");
    }
  }

  /* ── Create Project Dialog ── */
  function showCreateProjectDialog() {
    const name = prompt('Project name:', 'My New Project');
    if (!name || !name.trim()) return;
    const type = prompt('Project type (residential, commercial, industrial, other):', 'residential');
    _getWorkspaceId().then(wsId => {
      P.createProject(wsId, name.trim(), type || 'residential').then(project => {
        V5D.Router.navigate('project', project.project_id);
      }).catch(err => {
        alert('Failed to create project: ' + (err.message || 'Unknown error'));
      });
    });
  }

  function handleSearch(query) {
    if (!query || query.length < 2) {
      if (V5D.Router.getCurrentRoute() === 'dashboard') renderDashboard();
      else if (V5D.Router.getCurrentRoute() === 'projects') renderProjects();
      return;
    }
    V5D.Router.navigate('projects');
    _getWorkspaceId().then(wsId => {
      P.listProjects(wsId).then(projects => {
        const filtered = projects.filter(p => p.name.toLowerCase().includes(query.toLowerCase()));
        const container = document.getElementById('projects-list');
        if (container) {
          container.innerHTML = filtered.length
            ? '<div class="project-grid">' + filtered.map(p => C.ProjectCard(p)).join('') + '</div>'
            : C.EmptyState('🔍', 'No matching projects', `No projects found for "${query}".`);
        }
      });
    });
  }

  /* ── Helper ── */
  async function _getWorkspaceId() {
    return await P.getWorkspaceId();
  }

  return {
    renderDashboard, renderProjects, renderProjectDetail,
    showCreateProjectDialog, handleSearch,
  };
})();
