# Implementation Plan — V5D-FRONTEND-INVENTORY-001
**Date:** 2026-07-31

---

## Phase 1: Dashboard Foundation (Mission DASHBOARD-FOUNDATION-001)

**DO:** Extend `apps/web/index.html` with modular JS service layer while preserving existing HTML architecture.

**DO NOT:** Create a new framework, introduce npm, replace the current approach.

### Architecture Decision

Vision 5D has NO frontend framework, NO build system, NO package manager. The dashboard operates as pure HTML served directly by the FastAPI backend. This is intentional for Phase 1 — zero-build deployment.

**Approach:** Enhance the existing pure-HTML architecture with:
1. Extracted CSS into a shared stylesheet
2. JS service modules loaded via script tags
3. Component-pattern JS for tab views
4. No build step required

### File Structure

```
apps/web/
  css/
    dashboard.css          — shared design tokens + styles
  js/
    services/
      api.js               — base fetch wrapper
      auth.js              — login, logout, session
      projects.js          — project CRUD
      ai-providers.js      — provider management
    components/
      sidebar.js           — navigation
      header.js            — status bar + title
      project-card.js      — project list item
      job-list.js          — job status table
      status-badge.js      — colored status pill
    views/
      dashboard.js         — overview tab
      projects.js          — project list
      project-detail.js    — single project tabs
      ai-configuration.js  — AI provider settings
    app.js                 — bootstrap + routing
  index.html               — modified shell
```

### Phase Sequence

| Mission | Scope | Files |
|---------|-------|-------|
| 2. DASHBOARD-FOUNDATION-001 | Shell + nav + auth + overview | index.html, app.js, api.js, auth.js, sidebar.js, header.js, dashboard.js, dashboard.css |
| 3. AI-CONFIGURATION-001 | AI provider CRUD UI | ai-providers.js, ai-configuration.js |
| 4. DASHBOARD-DATA-INTEGRATION-001 | Project/scene/job data | projects.js, project-detail.js, job-list.js |
| 5. FRONTEND-QUALITY-GATE-001 | Tests, linting, validation | — |
| 6. FRONTEND-STAGING-ACCEPTANCE-001 | Staging deploy + verify | — |
| 7. FRONTEND-PRODUCTION-MERGE-001 | Merge to production | — |
| 8. FRONTEND-PRODUCTION-DEPLOYMENT-001 | Deploy + monitor | — |

### Non-Negotiables

1. No npm/pnpm/yarn — pure HTML/JS
2. No new framework (React, Vue, Svelte, etc.)
3. No router library — manual hash-based routing
4. No state management library — service modules with closures
5. API keys NEVER in browser storage
6. Pascal credentials ALWAYS server-side
7. Pascal adapter NEVER modified
8. Pascal schemas NEVER modified
9. Vision 5D revisions NEVER overwritten
10. Existing design system EXTENDED, not replaced
