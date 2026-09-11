/* ═══════════════════════════════════════════════════════════
   Vision 5D — UI Components
   Sidebar, Header, StatCard, ProjectCard, ActivityItem,
   QuickAction, LoadingSkeleton, EmptyState, ErrorState
   ═══════════════════════════════════════════════════════════ */

V5D.Components = (() => {

  /* ── Sidebar ── */
  function Sidebar(items) {
    let html = '<div class="sidebar-logo" role="banner">Vision 5D</div>';
    html += '<nav class="sidebar-nav" role="navigation" aria-label="Main navigation"><ul>';

    let currentSection = '';
    items.forEach(item => {
      if (item.section && item.section !== currentSection) {
        currentSection = item.section;
        html += `<li class="sidebar-section">${currentSection}</li>`;
      }
      // Section-only placeholders ({ section: '…' }) have no route/label — skip
      // them so they don't render as a literal "undefined" nav link.
      if (!item.route && !item.label) return;
      const badge = item.badge ? `<span class="badge ${item.badgeType || 'count'}">${item.badge}</span>` : '';
      html += `<li><a class="sidebar-link" data-route="${item.route}" href="#${item.route}" role="menuitem" aria-label="${item.label}">
        <span aria-hidden="true">${item.icon || '•'}</span> ${item.label}${badge}
      </a></li>`;
    });

    html += '</ul></nav>';
    html += '<div class="sidebar-footer">Vision 5D v0.1.0</div>';
    return html;
  }

  /* ── Header ── */
  function Header(title, status) {
    const online = status === 'connected';
    return `
      <button class="mobile-menu-btn" onclick="V5D.toggleSidebar()" aria-label="Toggle navigation menu">☰</button>
      <h1 class="header-title">${title}</h1>
      <div class="header-spacer"></div>
      <input class="header-search" type="search" placeholder="Search projects..." aria-label="Search projects" oninput="V5D.Views.handleSearch(this.value)">
      <div class="header-status">
        <span class="dot ${online ? 'online' : 'offline'}" aria-hidden="true"></span>
        <span>${online ? 'Connected' : 'Disconnected'}</span>
      </div>`;
  }

  /* ── Stat Card ── */
  function StatCard(icon, value, label, change, changeType, bg) {
    const changeHtml = change ? `<div class="stat-change ${changeType}">${change}</div>` : '';
    return `
      <div class="stat-card">
        <div class="stat-icon" style="background:${bg || 'var(--v5d-accent-light)'}">${icon}</div>
        <div class="stat-value">${value}</div>
        <div class="stat-label">${label}</div>
        ${changeHtml}
      </div>`;
  }

  /* ── Project Card ── */
  function ProjectCard(project) {
    const date = new Date(project.created_at).toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' });
    return `
      <div class="project-card" onclick="V5D.Router.navigate('project', '${project.project_id}')" 
           role="button" tabindex="0" aria-label="Open project: ${project.name}"
           onkeydown="if(event.key==='Enter')V5D.Router.navigate('project','${project.project_id}')">
        <div class="project-type">${project.project_type}</div>
        <div class="project-name">${project.name}</div>
        <div class="project-meta">Created ${date} • <span class="status-badge ${project.state === 'ACTIVE' ? 'success' : 'warning'}">${project.state}</span></div>
        <div class="project-stats">
          <div class="project-stat">Rooms <strong>${project.rooms || 0}</strong></div>
          <div class="project-stat">Walls <strong>${project.walls || 0}</strong></div>
          <div class="project-stat">Scenes <strong>${project.scenes || 0}</strong></div>
        </div>
      </div>`;
  }

  /* ── Activity Item ── */
  function ActivityItem(item) {
    const time = _formatTime(item.time);
    const bgColors = { scene_export: 'var(--v5d-success-bg)', geometry_complete: 'var(--v5d-info-bg)', project_created: 'var(--v5d-accent-light)', scene_created: 'var(--v5d-warning-bg)', cad_imported: 'var(--v5d-bg-tertiary)' };
    return `
      <div class="activity-item">
        <div class="activity-icon" style="background:${bgColors[item.type] || 'var(--v5d-bg-tertiary)'}">${item.icon}</div>
        <div class="activity-body">
          <div class="activity-title">${item.title}</div>
          <div class="activity-detail">${item.project}</div>
          <div class="activity-time">${time}</div>
        </div>
      </div>`;
  }

  /* ── Quick Action ── */
  function QuickAction(icon, label, onClick, primary) {
    return `<button class="quick-action${primary ? ' primary' : ''}" onclick="${onClick}" aria-label="${label}">
      <span aria-hidden="true">${icon}</span> ${label}
    </button>`;
  }

  /* ── Loading Skeleton ── */
  function LoadingSkeleton(type) {
    if (type === 'stats') {
      return '<div class="stats-grid">' + Array(4).fill('<div class="stat-card"><div class="skeleton skeleton-stat"></div></div>').join('') + '</div>';
    }
    if (type === 'projects') {
      return '<div class="project-grid">' + Array(3).fill('<div class="project-card"><div class="skeleton skeleton-card"></div></div>').join('') + '</div>';
    }
    return '<div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text short"></div><div class="skeleton skeleton-text"></div>';
  }

  /* ── Empty State ── */
  function EmptyState(icon, title, description, actionLabel, actionHandler) {
    const action = actionLabel ? `<button class="btn btn-primary" onclick="${actionHandler}">${actionLabel}</button>` : '';
    return `<div class="state-container" role="status">
      <div class="state-icon" aria-hidden="true">${icon}</div>
      <div class="state-title">${title}</div>
      <div class="state-description">${description}</div>
      ${action}
    </div>`;
  }

  /* ── Error State ── */
  function ErrorState(icon, title, description, retryHandler) {
    return `<div class="state-container" role="alert">
      <div class="state-icon" aria-hidden="true">${icon}</div>
      <div class="state-title">${title}</div>
      <div class="state-description">${description}</div>
      <button class="btn btn-secondary" onclick="${retryHandler}">Try Again</button>
    </div>`;
  }

  /* ── Status Badge ── */
  function StatusBadge(text, type) {
    return `<span class="status-badge ${type || 'neutral'}">${text}</span>`;
  }

  /* ── Helpers ── */
  function _formatTime(ts) {
    const d = new Date(ts);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return Math.floor(diff/60000) + 'm ago';
    if (diff < 86400000) return Math.floor(diff/3600000) + 'h ago';
    return d.toLocaleDateString();
  }

  return { Sidebar, Header, StatCard, ProjectCard, ActivityItem, QuickAction, LoadingSkeleton, EmptyState, ErrorState, StatusBadge };
})();
