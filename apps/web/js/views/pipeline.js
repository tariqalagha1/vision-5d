/* ═══════════════════════════════════════════════════════════
   Vision 5D — Pipeline Orchestration (Full Photo → Video)
   ═══════════════════════════════════════════════════════════ */

V5D.Pipeline = (() => {
  const C = V5D.Components;
  const P = V5D.Projects;
  const API = V5D.API;

  /* State machine */
  const STAGES = [
    "PROJECT_CREATED","SOURCE_UPLOADED","UNDERSTANDING_PENDING","UNDERSTANDING_READY",
    "UNDERSTANDING_APPROVED","GEOMETRY_PENDING","GEOMETRY_READY","PASCAL_PENDING",
    "PASCAL_READY","PASCAL_EDITED","REVISION_CREATED","SCENE3D_PENDING","SCENE3D_READY",
    "DESIGN_PENDING","DESIGN_READY","CINEMATIC_PENDING","CINEMATIC_READY",
    "RENDER_PENDING","RENDERING","RENDER_COMPLETE"
  ];

  const STAGE_INFO = {
    PROJECT_CREATED:      { icon:'📁', label:'Project Created',      desc:'Create a project to begin.',          action:'start' },
    SOURCE_UPLOADED:      { icon:'📤', label:'Photo Uploaded',       desc:'Photo ready for analysis.',            action:'understand' },
    UNDERSTANDING_PENDING:{ icon:'⏳', label:'Analyzing Photo...',    desc:'AI is analyzing the photo.',            action:null },
    UNDERSTANDING_READY:  { icon:'🧠', label:'AI Understanding Done',desc:'Review what the AI detected.',          action:'approve' },
    UNDERSTANDING_APPROVED:{ icon:'✅', label:'Understanding Approved',desc:'Proceed to geometry generation.',      action:'geometry' },
    GEOMETRY_PENDING:     { icon:'⏳', label:'Generating Geometry...',desc:'Building walls and furniture.',         action:null },
    GEOMETRY_READY:       { icon:'📐', label:'Geometry Ready',       desc:'Walls and furniture generated.',        action:'pascal' },
    PASCAL_PENDING:       { icon:'⏳', label:'Creating Pascal...',    desc:'Building semantic scene.',              action:null },
    PASCAL_READY:         { icon:'🏗️', label:'Pascal Scene Ready',   desc:'Semantic scene created.',               action:'revision' },
    PASCAL_EDITED:        { icon:'✏️', label:'Pascal Edited',        desc:'Corrections applied.',                  action:'revision' },
    REVISION_CREATED:     { icon:'📝', label:'Revision Saved',       desc:'Immutable revision created.',           action:'scene3d' },
    SCENE3D_PENDING:      { icon:'⏳', label:'Building 3D Scene...', desc:'Creating GLB model.',                   action:null },
    SCENE3D_READY:        { icon:'🎬', label:'3D Scene Ready',       desc:'GLB model exported.',                   action:'design' },
    DESIGN_PENDING:       { icon:'🎨', label:'Applying Design...',   desc:'Materials and lighting set.',           action:null },
    DESIGN_READY:         { icon:'✨', label:'Design Complete',       desc:'Ready for cinematic setup.',            action:'cinematic' },
    CINEMATIC_PENDING:    { icon:'⏳', label:'Setting Up Cameras...',desc:'Configuring shots.',                     action:null },
    CINEMATIC_READY:      { icon:'🎥', label:'Cinematic Ready',      desc:'Camera and lighting configured.',       action:'render' },
    RENDER_PENDING:       { icon:'⏳', label:'Rendering...',         desc:'Encoding video frames.',                action:null },
    RENDERING:            { icon:'🔥', label:'Rendering in Progress',desc:'Generating final video.',               action:null },
    RENDER_COMPLETE:      { icon:'🎉', label:'Video Ready!',         desc:'MP4 video rendered successfully.',      action:'done' },
    FAILED:               { icon:'❌', label:'Failed',               desc:'An error occurred.',                    action:'retry' },
    CANCELLED:            { icon:'🚫', label:'Cancelled',            desc:'Pipeline was cancelled.',               action:'restart' },
  };

  /* ── State ── */
  let _projectId = null;
  let _workspaceId = null;
  let _uploadedFile = null;
  let _lastResult = null;
  let _autoAdvance = true;

  /* ── API Client ── */
  async function _call(method, path, body) {
    return API[method](path, body);
  }

  /* ── Render ── */
  async function render() {
    const header = document.getElementById('app-header');
    header.innerHTML = C.Header('Pipeline: Photo → Video', V5D.Auth.isAuthenticated() ? 'connected' : 'disconnected');

    const content = document.getElementById('app-content');

    /* Discover workspace */
    try { _workspaceId = await P.getWorkspaceId(); } catch(e) { _workspaceId = null; }

    /* Load project list */
    let projects = [];
    try { const d = await P.listProjects(_workspaceId); projects = d || []; } catch(e) {}

    let html = '<div class="pipeline-container">';

    /* Project picker */
    html += '<div class="card"><div class="card-header"><span class="card-title">🎯 Select Project</span></div>';
    html += '<div class="project-picker">';
    html += '<select id="pipeline-project-select" onchange="V5D.Pipeline._onProjectChange()">';
    html += '<option value="">-- Choose a project --</option>';
    projects.forEach(p => {
      const sel = p.project_id === _projectId ? ' selected' : '';
      html += '<option value="' + p.project_id + '"' + sel + '>' + p.name + ' (' + p.state + ')</option>';
    });
    html += '</select>';
    html += '<button class="action-btn primary" onclick="V5D.Pipeline._createAndSelect()">+ New</button>';
    html += '</div></div>';

    /* Upload zone */
    html += '<div class="card" id="upload-card">';
    html += '<div class="card-header"><span class="card-title">📸 Upload Photo</span></div>';
    html += '<div class="upload-zone" id="upload-zone" onclick="document.getElementById(\'pipeline-file-input\').click()"';
    html += ' ondragover="event.preventDefault();this.classList.add(\'dragover\')"';
    html += ' ondragleave="this.classList.remove(\'dragover\')"';
    html += ' ondrop="V5D.Pipeline._onDrop(event)">';
    html += '<input type="file" id="pipeline-file-input" accept="image/*" style="display:none" onchange="V5D.Pipeline._onFileSelect(event)">';
    html += '<div id="upload-preview-area">';
    html += '<div style="font-size:36px;margin-bottom:8px">🖼️</div>';
    html += '<div style="font-weight:600;margin-bottom:4px">Drop a photo here or click to browse</div>';
    html += '<div style="font-size:12px;color:var(--v5d-text-secondary)">JPG, PNG, WebP images only — for DWG / DXF / 3D files, use the CAD Viewer</div>';
    html += '<button class="btn btn-sm" style="margin-top:8px" onclick="V5D.Router.navigate(\'cad\')">📐 Open CAD Viewer (DWG · DXF · 3D)</button>';
    html += '</div></div></div>';

    /* Pipeline stages */
    html += '<div class="card" id="pipeline-stages-card">';
    html += '<div class="card-header"><span class="card-title">⚙️ Pipeline Stages</span>';
    html += '<label style="font-size:12px;margin-left:12px;display:flex;align-items:center;gap:4px;cursor:pointer">';
    html += '<input type="checkbox" id="auto-advance-check" checked onchange="V5D.Pipeline._toggleAutoAdvance()"> Auto-advance';
    html += '</label></div>';
    html += '<div id="pipeline-stages"><div style="padding:20px;text-align:center;color:var(--v5d-text-secondary)">Select a project and upload a photo to begin.</div></div>';
    html += '</div>';

    /* Artifacts */
    html += '<div class="card" id="artifacts-card" style="display:none">';
    html += '<div class="card-header"><span class="card-title">📦 Artifacts</span></div>';
    html += '<div id="artifacts-list"></div></div>';

    html += '</div>'; /* pipeline-container */

    content.innerHTML = html;

    /* If project already selected, refresh pipeline view */
    if (_projectId) {
      document.getElementById('pipeline-project-select').value = _projectId;
      await refreshPipelineView();
    }
  }

  /* ── Pipeline Refresh ── */
  async function refreshPipelineView() {
    if (!_projectId) return;
    let state = 'PROJECT_CREATED';
    try {
      const r = await _call('get', '/api/v1/projects/' + _projectId + '/workflow');
      state = r.current_state || 'PROJECT_CREATED';
    } catch(e) {
      console.warn('[Pipeline] Could not get workflow state:', e.message);
    }

    renderStages(state);
    loadArtifacts();
  }

  function renderStages(currentState) {
    const container = document.getElementById('pipeline-stages');
    if (!container) return;

    const displayStages = [
      'PROJECT_CREATED','SOURCE_UPLOADED','UNDERSTANDING_READY','UNDERSTANDING_APPROVED',
      'GEOMETRY_READY','PASCAL_READY','REVISION_CREATED','SCENE3D_READY',
      'DESIGN_READY','CINEMATIC_READY','RENDER_COMPLETE'
    ];

    const currentIdx = STAGES.indexOf(currentState);
    let html = '';

    displayStages.forEach(stageKey => {
      const info = STAGE_INFO[stageKey] || { icon:'•', label:stageKey, desc:'', action:null };
      const stageIdx = STAGES.indexOf(stageKey);
      let cls = 'pending';

      if (stageKey === currentState) cls = 'active';
      else if (stageIdx < currentIdx && currentState !== 'FAILED') cls = 'completed';
      else if (currentState === 'FAILED' && stageIdx <= currentIdx) cls = 'failed';

      let actionsHtml = '';
      if (cls === 'active' && info.action) {
        actionsHtml = _buildActionButtons(stageKey, info.action);
      } else if (currentState === 'FAILED' && stageIdx === currentIdx) {
        actionsHtml = '<button class="action-btn" onclick="V5D.Pipeline._retry()">🔄 Retry Last Step</button>';
      }

      let resultHtml = '';
      if (cls === 'active' && _lastResult) {
        resultHtml = '<div class="stage-result">' + JSON.stringify(_lastResult, null, 2) + '</div>';
      }

      html += '<div class="pipeline-stage ' + cls + '">' +
        '<div class="stage-icon">' + (cls === 'completed' ? '✅' : cls === 'failed' ? '❌' : cls === 'active' ? '🔄' : info.icon) + '</div>' +
        '<div class="stage-body">' +
        '<div class="stage-title">' + info.label + '</div>' +
        '<div class="stage-desc">' + info.desc + '</div>' +
        '<div class="stage-actions">' + actionsHtml + '</div>' +
        resultHtml +
        '</div></div>';
    });

    container.innerHTML = html;
  }

  function _buildActionButtons(stageKey, action) {
    var btns = '';
    switch(action) {
      case 'start':
        btns += '<button class="action-btn primary" onclick="V5D.Pipeline._startPipeline()" id="btn-start">▶ Start Pipeline</button>';
        break;
      case 'understand':
        btns += '<button class="action-btn primary" onclick="V5D.Pipeline.runUnderstanding()">🧠 Analyze Photo</button>';
        break;
      case 'approve':
        btns += '<button class="action-btn primary" onclick="V5D.Pipeline.approve()">✅ Approve & Continue</button>';
        btns += '<button class="action-btn" onclick="V5D.Pipeline.reject()">🔄 Re-analyze</button>';
        break;
      case 'geometry':
        btns += '<button class="action-btn primary" onclick="V5D.Pipeline.runGeometry()">📐 Generate Geometry</button>';
        break;
      case 'pascal':
        btns += '<button class="action-btn primary" onclick="V5D.Pipeline.createPascal()">🏗️ Create Pascal Scene</button>';
        break;
      case 'revision':
        btns += '<button class="action-btn primary" onclick="V5D.Pipeline.createRevision()">📝 Save Revision</button>';
        break;
      case 'scene3d':
        btns += '<button class="action-btn primary" onclick="V5D.Pipeline.runScene3D()">🎬 Build 3D Scene</button>';
        break;
      case 'design':
        btns += '<button class="action-btn primary" onclick="V5D.Pipeline.applyDesign()">🎨 Apply Default Design</button>';
        break;
      case 'cinematic':
        btns += '<button class="action-btn primary" onclick="V5D.Pipeline.setupCinematic()">🎥 Setup Cinematic</button>';
        break;
      case 'render':
        btns += '<button class="action-btn primary" onclick="V5D.Pipeline.renderVideo()">🎬 Render Video</button>';
        btns += '<button class="action-btn" onclick="V5D.Pipeline.renderTourVideo()">📸 AI Photo Tour</button>';
        break;
      case 'done':
        btns += '<button class="action-btn primary" onclick="V5D.Pipeline.renderVideo()">🔄 Re-render</button>';
        btns += '<button class="action-btn" onclick="V5D.Pipeline.renderTourVideo()">📸 AI Photo Tour</button>';
        break;
      case 'retry':
        btns += '<button class="action-btn" onclick="V5D.Pipeline._retry()">🔄 Retry</button>';
        break;
    }
    return btns;
  }

  /* ── Upload ── */
  function _onFileSelect(event) {
    var file = event.target.files[0];
    if (file) _setUploadedFile(file);
  }

  function _onDrop(event) {
    event.preventDefault();
    event.target.classList.remove('dragover');
    var file = event.dataTransfer.files[0];
    if (file) _setUploadedFile(file);
  }

  function _setUploadedFile(file) {
    _uploadedFile = file;
    var preview = document.getElementById('upload-preview-area');
    var reader = new FileReader();
    reader.onload = function(e) {
      preview.innerHTML = '<img src="' + e.target.result + '" class="upload-preview" alt="Preview">' +
        '<div style="font-weight:600">' + file.name + '</div>' +
        '<div style="font-size:12px;color:var(--v5d-text-secondary)">' + (file.size/1024).toFixed(1) + ' KB</div>' +
        '<button class="action-btn" style="margin-top:8px" onclick="V5D.Pipeline._clearUpload()">Remove</button>';
    };
    reader.readAsDataURL(file);
    /* Update start button text */
    var btn = document.getElementById('btn-start');
    if (btn) { btn.textContent = '▶ Start Pipeline (with photo)'; }
  }

  function _clearUpload() {
    _uploadedFile = null;
    var preview = document.getElementById('upload-preview-area');
    preview.innerHTML = '<div style="font-size:36px;margin-bottom:8px">🖼️</div><div style="font-weight:600;margin-bottom:4px">Drop a photo here or click to browse</div><div style="font-size:12px;color:var(--v5d-text-secondary)">JPG, PNG, WebP images only — for DWG / DXF / 3D files, use the CAD Viewer</div>';
    var btn = document.getElementById('btn-start');
    if (btn) { btn.textContent = '▶ Start Pipeline'; }
  }

  /* ── Pipeline Actions ── */
  async function _startPipeline() {
    if (!_projectId) {
      alert('Select a project first.');
      return;
    }

    /* Reset workflow to allow re-running with a new photo */
    try {
      await _call('post', '/api/v1/projects/' + _projectId + '/workflow/reset');
      setStatus('pipeline-stages-card', '🔄 Workflow reset for new pipeline run');
    } catch(e) {
      console.warn('[Pipeline] Reset failed, continuing anyway:', e.message);
    }

    /* If photo uploaded, try to upload it; otherwise skip to understanding */
    if (_uploadedFile) {
      setStatus('upload-card', '⏳ Uploading photo...');
      try {
        var formData = new FormData();
        formData.append('file', _uploadedFile);
        formData.append('name', _uploadedFile.name.replace(/\.[^.]+$/, ''));
        var upResult = await API.upload('/api/v1/assets/upload-photo', formData);
        setStatus('upload-card', '✅ Photo uploaded: ' + (upResult.filename || _uploadedFile.name));
      } catch(e) {
        setStatus('upload-card', '⚠️ Upload skipped (endpoint unavailable). Using backend fallback.');
      }
    } else {
      setStatus('upload-card', 'ℹ️ No photo uploaded. Backend will use test photo if available.');
    }

    await _runStage('Understanding', function() { return _call('post', '/api/v1/projects/' + _projectId + '/understand'); });
  }

  async function runUnderstanding() {
    /* Reset workflow first if we're past understanding stage */
    try {
      var s = await _getState();
      if (s && s !== 'UNDERSTANDING_READY' && s !== 'PROJECT_CREATED' && s !== 'SOURCE_UPLOADED' && s !== 'UNDERSTANDING_PENDING') {
        await _call('post', '/api/v1/projects/' + _projectId + '/workflow/reset');
      }
    } catch(e) { /* non-fatal */ }
    await _runStage('Understanding', function() { return _call('post', '/api/v1/projects/' + _projectId + '/understand'); });
  }

  async function approve() {
    await _runStage('Approve', function() { return _call('post', '/api/v1/projects/' + _projectId + '/understanding/approve'); }, 'geometry');
  }

  async function reject() {
    await _runStage('Reject', function() { return _call('post', '/api/v1/projects/' + _projectId + '/understanding/reject'); });
  }

  async function runGeometry() {
    await _runStage('Geometry', function() { return _call('post', '/api/v1/projects/' + _projectId + '/geometry'); }, 'pascal');
  }

  async function createPascal() {
    await _runStage('Pascal', function() { return _call('post', '/api/v1/projects/' + _projectId + '/pascal'); }, 'revision');
  }

  async function createRevision() {
    await _runStage('Revision', function() { return _call('post', '/api/v1/projects/' + _projectId + '/pascal/import', {corrections: []}); }, 'scene3d');
  }

  async function runScene3D() {
    await _runStage('Scene3D', function() { return _call('post', '/api/v1/projects/' + _projectId + '/scene3d'); }, 'design');
  }

  async function applyDesign() {
    try {
      await _call('put', '/api/v1/projects/' + _projectId + '/materials', {
        floor:'wood_light', wall:'paint_white', ceiling:'paint_white', door:'wood_dark', window_frame:'aluminum'
      });
    } catch(e) { console.warn('Materials update failed:', e.message); }
    await _runStage('Design', async function() { return {state:'DESIGN_READY'}; }, 'cinematic');
  }

  async function setupCinematic() {
    await _runStage('Cinematic', function() { return _call('put', '/api/v1/projects/' + _projectId + '/cinematic', {
      camera:'orbit', fov:60, duration:30, shots:['orbit','walkthrough','reveal']
    }); }, 'render');
  }

  async function renderVideo() {
    await _runStage('Render', function() { return _call('post', '/api/v1/projects/' + _projectId + '/render'); }, 'artifacts');
  }

  async function renderTourVideo() {
    if (!_projectId) { alert('Select a project first.'); return; }
    setStatus('pipeline-stages-card', '📸 Generating AI Photo Tour (Ken Burns + crossfade)...');
    try {
      _lastResult = await _call('post', '/api/v1/projects/' + _projectId + '/tour-video');
      setStatus('pipeline-stages-card', '✅ AI Photo Tour complete: ' + _lastResult.scene_count + ' scenes, ' + _lastResult.duration_s + 's');
      await refreshPipelineView();
      await loadArtifacts();
    } catch(e) {
      _lastResult = { error: e.message, code: e.code };
      setStatus('pipeline-stages-card', '❌ AI Photo Tour failed: ' + e.message);
      await refreshPipelineView();
    }
  }

  /* ── Core Runner ── */
  async function _runStage(name, fn, nextStage) {
    setStatus('pipeline-stages-card', '⏳ Running ' + name + '...');
    try {
      _lastResult = await fn();
      await refreshPipelineView();
      setStatus('pipeline-stages-card', '✅ ' + name + ' complete');

      if (_autoAdvance && nextStage) {
        setTimeout(async function() {
          var state = await _getState();
          if (nextStage === 'pascal' && (state === 'GEOMETRY_READY' || state === 'PASCAL_PENDING')) {
            await createPascal();
          } else if (nextStage === 'revision' && state === 'PASCAL_READY') {
            await createRevision();
          } else if (nextStage === 'scene3d' && state === 'REVISION_CREATED') {
            await runScene3D();
          } else if (nextStage === 'design' && state === 'SCENE3D_READY') {
            await applyDesign();
          } else if (nextStage === 'cinematic' && state === 'DESIGN_READY') {
            await setupCinematic();
          } else if (nextStage === 'render' && state === 'CINEMATIC_READY') {
            await renderVideo();
          } else if (nextStage === 'artifacts') {
            await loadArtifacts();
          }
        }, 800);
      }
    } catch(e) {
      _lastResult = { error: e.message, code: e.code };
      setStatus('pipeline-stages-card', '❌ ' + name + ' failed: ' + e.message);
      await refreshPipelineView();
    }
  }

  async function _retry() {
    refreshPipelineView();
  }

  async function _getState() {
    try {
      var r = await _call('get', '/api/v1/projects/' + _projectId + '/workflow');
      return r.current_state;
    } catch(e) { return 'PROJECT_CREATED'; }
  }

  /* ── Artifacts ── */
  async function loadArtifacts() {
    if (!_projectId) return;
    var card = document.getElementById('artifacts-card');
    var list = document.getElementById('artifacts-list');
    if (!card || !list) return;

    try {
      var r = await _call('get', '/api/v1/projects/' + _projectId + '/artifacts');
      var artifacts = r.artifacts || [];
      if (artifacts.length === 0) return;

      card.style.display = 'block';
      list.innerHTML = artifacts.map(function(a) {
        var sizeStr = a.size_bytes > 1048576 ? (a.size_bytes/1048576).toFixed(1) + ' MB'
          : a.size_bytes > 1024 ? (a.size_bytes/1024).toFixed(1) + ' KB'
          : a.size_bytes + ' B';
        var typeIcon = a.type === 'render_mp4' ? '🎬' : a.type === 'render_thumbnail' ? '🖼️' :
          a.type === 'scene3d_glb' ? '🧊' : '📄';

        var previewHtml = '';
        if (a.type === 'render_mp4') {
          previewHtml = '<video class="video-preview" controls src="/api/v1/assets/download?key=' + encodeURIComponent(a.storage_key) + '" style="margin-top:8px"></video>';
        } else if (a.type === 'render_thumbnail') {
          previewHtml = '<img src="/api/v1/assets/download?key=' + encodeURIComponent(a.storage_key) + '" style="max-width:320px;border-radius:6px;margin-top:8px">';
        }

        return '<div class="artifact-card">' +
          '<div class="artifact-row"><span>' + typeIcon + ' <strong>' + a.type + '</strong></span><span>' + sizeStr + '</span></div>' +
          (a.content_hash ? '<div class="artifact-row"><span style="color:var(--v5d-text-secondary)">SHA-256</span><span style="font-family:monospace;font-size:11px">' + a.content_hash.substring(0,16) + '...</span></div>' : '') +
          previewHtml +
          '</div>';
      }).join('');
    } catch(e) {
      console.warn('[Pipeline] Artifacts load failed:', e.message);
    }
  }

  /* ── Project Selection ── */
  function _onProjectChange() {
    var sel = document.getElementById('pipeline-project-select');
    _projectId = sel.value || null;
    if (_projectId) refreshPipelineView();
  }

  async function _createAndSelect() {
    /* Check auth first */
    if (!V5D.Auth.isAuthenticated()) {
      alert('Please sign in first. Click Sign In in the sidebar.');
      return;
    }
    var name = prompt('Project name:', 'Pipeline-' + Date.now().toString(36));
    if (!name) return;
    var type = prompt('Type (residential/commercial/industrial):', 'residential');
    if (!type) type = 'residential';
    try {
      var wsId = _workspaceId || await P.getWorkspaceId();
      var proj = await P.createProject(wsId, name, type);
      _projectId = proj.project_id;
      render();
    } catch(e) {
      var detail = JSON.stringify({code: e.code, status: e.status, message: e.message, data: e.data}, null, 2);
      if (e.code === 'AUTH_EXPIRED') {
        alert('Session expired. Please sign in again.\n\n' + detail);
      } else if (e.code === 'NETWORK_ERROR') {
        alert('Cannot reach the backend. Is the server running on port 8000?\n\n' + detail);
      } else if (e.code === 'WORKSPACE_ERROR') {
        alert('Workspace error: ' + e.message + '\n\n' + detail);
      } else {
        alert('Failed to create project:\n\n' + detail);
      }
    }
  }

  function _toggleAutoAdvance() {
    _autoAdvance = document.getElementById('auto-advance-check').checked;
  }

  /* ── Status Helper ── */
  function setStatus(cardId, msg) {
    var card = document.getElementById(cardId);
    if (!card) return;
    var statusEl = card.querySelector('.card-status');
    if (!statusEl) {
      statusEl = document.createElement('div');
      statusEl.className = 'card-status';
      statusEl.style.cssText = 'font-size:12px;color:var(--v5d-text-secondary);margin-top:4px;';
      card.querySelector('.card-header').appendChild(statusEl);
    }
    statusEl.textContent = msg;
  }

  return {
    render: render, refreshPipelineView: refreshPipelineView,
    runUnderstanding: runUnderstanding, approve: approve, reject: reject,
    runGeometry: runGeometry, createPascal: createPascal, createRevision: createRevision,
    runScene3D: runScene3D, applyDesign: applyDesign, setupCinematic: setupCinematic,
    renderVideo: renderVideo, renderTourVideo: renderTourVideo, loadArtifacts: loadArtifacts,
    _onProjectChange: _onProjectChange, _createAndSelect: _createAndSelect,
    _onFileSelect: _onFileSelect, _onDrop: _onDrop,
    _clearUpload: _clearUpload, _startPipeline: _startPipeline,
    _toggleAutoAdvance: _toggleAutoAdvance, _retry: _retry
  };
})();
