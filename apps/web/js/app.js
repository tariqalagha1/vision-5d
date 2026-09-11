/* ═══════════════════════════════════════════════════════════
   Vision 5D — Application Bootstrap
   ═══════════════════════════════════════════════════════════ */

(function() {
  'use strict';
  V5D.Router.register('dashboard', V5D.Views.renderDashboard);
  V5D.Router.register('projects', V5D.Views.renderProjects);
  V5D.Router.register('project', V5D.Views.renderProjectDetail);
  V5D.Router.register('ai-config', function(){ if(V5D.Views.renderAIConfig && V5D.Views.renderAIConfig.render) V5D.Views.renderAIConfig.render(); });
  V5D.Router.register('pipeline', function(){ 
    if (!V5D.Auth.isAuthenticated()) {
      V5D.Auth.login('google').then(function() {
        if (V5D.Pipeline && V5D.Pipeline.render) V5D.Pipeline.render();
      }).catch(function() {
        if (V5D.Pipeline && V5D.Pipeline.render) V5D.Pipeline.render();
      });
    } else {
      if (V5D.Pipeline && V5D.Pipeline.render) V5D.Pipeline.render();
    }
  });

  V5D.Router.register('cad', function(){
    if (V5D.CADViewer && V5D.CADViewer.render) V5D.CADViewer.render();
  });

  V5D.Router.register('files', function(){
    var hdr = document.getElementById('app-header');
    var content = document.getElementById('app-content');
    if (hdr) hdr.innerHTML = V5D.Components.Header('Import CAD', V5D.Auth.isAuthenticated() ? 'connected' : 'disconnected');
    if (content) content.innerHTML =
      '<div class="state-container" role="status">' +
      '<div class="state-icon">📥</div>' +
      '<div class="state-title">Import CAD</div>' +
      '<div class="state-description">Upload DXF, DWG, or PDF files to start a new project.</div>' +
      '<input type="file" id="cad-file-input" accept=".dxf,.dwg,.pdf" style="display:none">' +
      '<button class="btn btn-primary" onclick="document.getElementById(\'cad-file-input\').click()">Select File</button>' +
      '<div id="upload-status" style="margin-top:16px;display:none"></div>' +
      '</div>';

    document.getElementById('cad-file-input').onchange = function(){
      var file = this.files[0];
      if (!file) return;
      var statusEl = document.getElementById('upload-status');
      statusEl.style.display = 'block';
      statusEl.innerHTML = '<div class="state-icon">⏳</div><div class="state-description">Uploading ' + file.name + '...</div>';

      var formData = new FormData();
      formData.append('file', file);
      formData.append('name', file.name.replace(/\.[^.]+$/, ''));

      fetch(V5D.API.BASE + '/api/v1/assets/upload-cad', {
        method: 'POST',
        body: formData,
        credentials: 'include'
      }).then(function(r){
        if (!r.ok) throw new Error('Upload failed: ' + r.status);
        return r.json();
      }).then(function(data){
        statusEl.innerHTML = '<div class="state-icon">✅</div>' +
          '<div class="state-title">Upload Complete</div>' +
          '<div class="state-description">' + file.name + ' uploaded successfully.</div>' +
          (data.project_id ? '<button class="btn btn-primary" style="margin-top:12px" onclick="V5D.Router.navigate(\'project\',\'' + data.project_id + '\')">Open Project</button>' : '');
      }).catch(function(err){
        statusEl.innerHTML = V5D.Components.ErrorState('❌', 'Upload Failed', err.message, 'document.getElementById(\'cad-file-input\').click()');
      });
    };
  });

  V5D.Router.register('scenes', function(){
    var hdr = document.getElementById('app-header');
    var content = document.getElementById('app-content');
    if (hdr) hdr.innerHTML = V5D.Components.Header('Scenes', V5D.Auth.isAuthenticated() ? 'connected' : 'disconnected');
    if (content) content.innerHTML = V5D.Components.EmptyState("🏗️", "3D Scenes",
      "No scenes have been generated yet. Create a project and generate geometry to see scenes here.");
  });

  V5D.toggleSidebar = function(){
    document.getElementById('app-sidebar').classList.toggle('open');
  };

  V5D.Auth.onChange(function(state){
    var sidebar = document.getElementById('app-sidebar');
    var items = state.authenticated ? [
      { route: 'dashboard', label: 'Dashboard', icon: "\uD83D\uDCCA" },
      { route: 'pipeline', label: 'Photo → Video', icon: "\uD83C\uDFAC" },
      { route: 'projects', label: 'Projects', icon: "\uD83D\uDCC1" },
      { section: 'WORKSPACE' },
      { route: 'scenes', label: 'Scenes', icon: "\uD83C\uDFD7\uFE0F" },
      { route: 'files', label: 'Files', icon: "\uD83D\uDCC4" },
      { route: 'cad', label: 'CAD Viewer', icon: "\uD83D\uDCD0" },
      { section: 'SETTINGS' },
      { route: 'ai-config', label: 'AI Configuration', icon: "\uD83E\uDD16" },
      { label: 'Sign Out', icon: "\uD83D\uDEAA", route: 'logout' }
    ] : [
      { route: 'dashboard', label: 'Vision 5D', icon: "\uD83C\uDFDB\uFE0F" },
      { section: ' ' },
      { label: 'Sign In', icon: "🔑", route: 'login' }
    ];
    sidebar.innerHTML = V5D.Components.Sidebar(items);
    sidebar.querySelectorAll('.sidebar-link').forEach(function(link){
      link.addEventListener('click', function(e){
        var route = this.getAttribute('data-route');
        if (route === 'logout') { e.preventDefault(); V5D.Auth.logout().then(function(){ V5D.Router.navigate('dashboard'); }); }
        else if (route === 'login') { e.preventDefault(); V5D.Auth.login().then(function(){ V5D.Views.renderDashboard(); }); }
      });
    });
    // Re-render the current view so the header/status/content reflect the new auth state.
    // (navigate() short-circuits when already on the route, so render directly here.)
    var current = V5D.Router.getCurrentRoute();
    if (current === 'dashboard' && V5D.Views.renderDashboard) V5D.Views.renderDashboard();
    else if (current === 'projects' && V5D.Views.renderProjects) V5D.Views.renderProjects();
  });

  var _initialSessionCheck = true;
  V5D.Events.on('auth:expired', function(){
    if (_initialSessionCheck) return;
    if (!V5D.Auth.isAuthenticated()) return;
    V5D.Auth.logout().then(function(){ V5D.Router.navigate('dashboard'); });
  });

  function boot(){
    document.addEventListener('click', function(e){
      var sidebar = document.getElementById('app-sidebar');
      if (window.innerWidth <= 768 && !sidebar.contains(e.target) && !e.target.classList.contains('mobile-menu-btn')){
        sidebar.classList.remove('open');
      }
    });

    // Resolve the auth session BEFORE the first route render. Without this, the
    // router renders the dashboard unauthenticated (header "Disconnected" + a
    // cascade of "Session expired / Could not load statistics" error panels),
    // then re-renders it a moment later once the demo auto-login completes —
    // a visible flicker of wrong status flags. Deferring the first render keeps
    // the static "Connecting…" skeleton on screen until auth is settled.
    // (checkSession() never rejects — it returns true/false — so no try/catch
    // is needed around it; only login() is guarded in case the backend is down.)
    V5D.Auth.checkSession().then(function(authed){
      if (!authed) {
        return V5D.Auth.login('google').catch(function(){ /* backend down — render unauthenticated */ });
      }
    }).catch(function(){
      // fallthrough in the unlikely case checkSession rejects
      return V5D.Auth.login('google').catch(function(){});
    }).then(function(){
      _initialSessionCheck = false;
      V5D.Router.start();
    });
  }

  boot();
})();
