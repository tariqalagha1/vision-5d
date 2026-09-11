/* ═══════════════════════════════════════════════════════════
   Vision 5D — CAD Viewer (2D DWG/DXF view + edit · 3D mesh view)
   Integrated route: #cad. Upload a CAD file and view/edit it in-app.
   ═══════════════════════════════════════════════════════════ */

V5D.CADViewer = (() => {
  'use strict';
  const API = V5D.API;

  /* ── State ── */
  let mode = null;            // '2d' | '3d' | null
  let entities = [];
  let layers = [];
  let layerVisible = {};
  let bounds = null;
  let sourceFormat = '';
  let fileName = '';

  // 2D transform
  let scale = 1, offsetX = 0, offsetY = 0;
  let canvas = null, ctx = null;
  let selectedIdx = -1;
  let drag = null;            // {kind:'vertex'|'entity'|'pan', idx, vi, startX, startY, moved}
  let tool = 'select';        // 'select' | 'pan'

  // 3D
  let three = null;           // {scene, camera, renderer, controls, container}
  let _threeLoaded = false;

  const MESH_EXTS = ['stl', 'glb', 'gltf', 'obj', '3ds'];

  /* ─────────────────────────────────────────────────────────
     RENDER (entry point)
  ───────────────────────────────────────────────────────── */
  function render() {
    const header = document.getElementById('app-header');
    if (header) header.innerHTML = V5D.Components.Header('CAD Viewer', V5D.Auth.isAuthenticated() ? 'connected' : 'disconnected');

    const content = document.getElementById('app-content');
    if (!content) return;

    content.innerHTML =
      '<div style="display:flex;flex-direction:column;gap:12px;height:calc(100vh - 130px)">' +
        '<div class="card" style="flex:0 0 auto">' +
          '<div class="card-header"><span class="card-title">📐 Open CAD / 3D file</span>' +
            '<span id="cad-file-label" style="font-size:12px;color:var(--v5d-text-secondary)"></span></div>' +
          '<div style="padding:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">' +
            '<input type="file" id="cad-file-input" accept=".dxf,.dwg,.stl,.glb,.gltf,.obj,.3ds" style="display:none">' +
            '<button class="btn btn-primary" onclick="V5D.CADViewer._browse()">📂 Choose File</button>' +
            '<button class="btn" onclick="V5D.CADViewer._dropHint()" title="Drag & drop anywhere below">💡 Tip</button>' +
            '<span style="font-size:12px;color:var(--v5d-text-secondary)">DXF · DWG (2D) — STL · GLB · OBJ · 3DS (3D)</span>' +
          '</div>' +
          '<div id="cad-drop-zone" style="margin:0 12px 12px;padding:26px;border:2px dashed #3a4150;border-radius:10px;text-align:center;color:var(--v5d-text-secondary);cursor:pointer">' +
            '<div style="font-size:32px">📥</div>' +
            '<div style="font-weight:600;margin:4px 0">Drop a DWG, DXF, STL, GLB or OBJ here — or click to browse</div>' +
            '<div style="font-size:12px">2D drawings open in an editable vector viewer · 3D meshes open in an orbit viewer</div>' +
          '</div>' +
        '</div>' +

        '<div class="card" style="flex:1 1 auto;display:flex;flex-direction:column;min-height:0;position:relative">' +
          '<div id="cad-toolbar" style="display:none;gap:6px;padding:8px 10px;border-bottom:1px solid #232b36;flex-wrap:wrap;align-items:center">' +
            '<button class="btn btn-sm" onclick="V5D.CADViewer._fit()">⤢ Fit</button>' +
            '<button class="btn btn-sm" onclick="V5D.CADViewer._zoom(1.25)">➕</button>' +
            '<button class="btn btn-sm" onclick="V5D.CADViewer._zoom(0.8)">➖</button>' +
            '<span class="sep" style="width:1px;height:18px;background:#3a4150"></span>' +
            '<button class="btn btn-sm" id="cad-tool-select" onclick="V5D.CADViewer._setTool(\'select\')">👆 Select</button>' +
            '<button class="btn btn-sm" id="cad-tool-pan" onclick="V5D.CADViewer._setTool(\'pan\')">✋ Pan</button>' +
            '<span class="sep" style="width:1px;height:18px;background:#3a4150"></span>' +
            '<button class="btn btn-sm" id="cad-btn-delete" onclick="V5D.CADViewer._deleteSelected()" disabled>🗑 Delete</button>' +
            '<button class="btn btn-sm" id="cad-btn-export" onclick="V5D.CADViewer._exportDxf()" disabled>💾 Export DXF</button>' +
            '<span style="margin-left:auto;font-size:12px;color:var(--v5d-text-secondary)" id="cad-status"></span>' +
          '</div>' +
          '<div id="cad-stage" style="flex:1 1 auto;min-height:0;position:relative;background:#0f141a;overflow:hidden">' +
            '<canvas id="cad-canvas" style="position:absolute;inset:0;display:none;background:#11161d"></canvas>' +
            '<div id="cad-3d" style="position:absolute;inset:0;display:none"></div>' +
            '<div id="cad-empty" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#5b6673">Upload a file to begin</div>' +
          '</div>' +
          '<div id="cad-layers" style="display:none;max-height:130px;overflow:auto;padding:8px 12px;border-top:1px solid #232b36;flex-wrap:wrap;gap:4px"></div>' +
        '</div>' +
      '</div>';

    canvas = document.getElementById('cad-canvas');
    ctx = canvas.getContext('2d');

    // Drop zone events
    const dz = document.getElementById('cad-drop-zone');
    dz.addEventListener('click', () => document.getElementById('cad-file-input').click());
    dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.style.borderColor = '#4d9fff'; });
    dz.addEventListener('dragleave', () => { dz.style.borderColor = '#3a4150'; });
    dz.addEventListener('drop', (e) => {
      e.preventDefault(); dz.style.borderColor = '#3a4150';
      const f = e.dataTransfer.files[0];
      if (f) _loadFile(f);
    });
    document.getElementById('cad-file-input').addEventListener('change', (e) => {
      if (e.target.files[0]) _loadFile(e.target.files[0]);
    });

    // Canvas events
    canvas.addEventListener('mousedown', _onMouseDown);
    canvas.addEventListener('mousemove', _onMouseMove);
    canvas.addEventListener('mouseup', _onMouseUp);
    canvas.addEventListener('wheel', _onWheel, { passive: false });
    window.addEventListener('resize', _onResize);

    _updateStatus(mode ? ('Loaded ' + fileName) : '');
  }

  /* ─────────────────────────────────────────────────────────
     FILE LOADING
  ───────────────────────────────────────────────────────── */
  function _browse() { document.getElementById('cad-file-input').click(); }
  function _dropHint() { alert('Drop a .dxf/.dwg (2D) or .stl/.glb/.obj (3D) file onto the dashed area below.'); }

  async function _loadFile(file) {
    const ext = (file.name.split('.').pop() || '').toLowerCase();
    document.getElementById('cad-file-label').textContent = '⏳ Parsing ' + file.name + '…';
    _updateStatus('Uploading & parsing…');

    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await API.upload('/api/v1/cad/parse', fd);
      _applyResult(r, file.name);
    } catch (e) {
      _updateStatus('❌ ' + (e.message || 'Upload failed'));
      document.getElementById('cad-file-label').textContent = '';
      alert('Failed to parse file: ' + (e.message || 'Unknown error'));
    }
  }

  function _applyResult(r, name) {
    fileName = name;
    sourceFormat = r.source_format || '';
    document.getElementById('cad-file-label').textContent =
      '📄 ' + name + ' · ' + sourceFormat.toUpperCase() + (r.mode === '3d' ? ' (3D)' : '');

    if (r.mode === '3d') {
      mode = '3d';
      _show3D();
      _init3D(V5D.API.BASE + r.download_url, sourceFormat);
      _updateStatus('Loaded 3D model — drag to orbit, scroll to zoom');
    } else {
      mode = '2d';
      entities = r.entities || [];
      layers = r.layers || [];
      bounds = r.bounds || { min_x: 0, min_y: 0, max_x: 1000, max_y: 1000 };
      layerVisible = {};
      layers.forEach(l => layerVisible[l] = true);
      selectedIdx = -1;
      _show2D();
      _renderLayersPanel();
      _fit();
      _updateStatus((r.entity_count || entities.length) + ' entities · ' + layers.length + ' layers' +
        (r.truncated ? ' · (truncated)' : ''));
      if (r.warnings && r.warnings.length) console.warn('[CAD]', r.warnings);
    }
  }

  function _show2D() {
    document.getElementById('cad-toolbar').style.display = 'flex';
    document.getElementById('cad-layers').style.display = 'flex';
    document.getElementById('cad-canvas').style.display = 'block';
    document.getElementById('cad-3d').style.display = 'none';
    document.getElementById('cad-empty').style.display = 'none';
    document.getElementById('cad-btn-export').disabled = false;
    _sizeCanvas();
  }
  function _show3D() {
    document.getElementById('cad-toolbar').style.display = 'flex';
    document.getElementById('cad-layers').style.display = 'none';
    document.getElementById('cad-canvas').style.display = 'none';
    document.getElementById('cad-3d').style.display = 'block';
    document.getElementById('cad-empty').style.display = 'none';
    document.getElementById('cad-btn-export').disabled = true;
  }

  function _updateStatus(msg) {
    const el = document.getElementById('cad-status');
    if (el) el.textContent = msg;
  }

  /* ─────────────────────────────────────────────────────────
     2D TRANSFORM
  ───────────────────────────────────────────────────────── */
  function _sizeCanvas() {
    const stage = document.getElementById('cad-stage');
    if (!stage || !canvas) return;
    canvas.width = stage.clientWidth;
    canvas.height = stage.clientHeight;
    if (mode === '2d') _draw();
  }
  function _onResize() { _sizeCanvas(); if (mode === '3d' && three) _threeResize(); }

  function _worldToScreen(x, y) {
    return [offsetX + x * scale, offsetY - y * scale];   // Y-flip
  }
  function _screenToWorld(sx, sy) {
    return [(sx - offsetX) / scale, (offsetY - sy) / scale];
  }

  function _fit() {
    if (mode !== '2d' || !bounds) return;
    const w = canvas.width, h = canvas.height;
    const bw = (bounds.max_x - bounds.min_x) || 1;
    const bh = (bounds.max_y - bounds.min_y) || 1;
    const margin = 40;
    scale = Math.min((w - 2 * margin) / bw, (h - 2 * margin) / bh);
    const cx = (bounds.min_x + bounds.max_x) / 2;
    const cy = (bounds.min_y + bounds.max_y) / 2;
    offsetX = w / 2 - cx * scale;
    offsetY = h / 2 + cy * scale;
    _draw();
  }

  function _zoom(factor) {
    if (mode !== '2d') return;
    const cx = canvas.width / 2, cy = canvas.height / 2;
    const [wx, wy] = _screenToWorld(cx, cy);
    scale *= factor;
    offsetX = cx - wx * scale;
    offsetY = cy + wy * scale;
    _draw();
  }

  function _onWheel(e) {
    if (mode !== '2d') return;
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const cx = e.clientX - rect.left, cy = e.clientY - rect.top;
    const [wx, wy] = _screenToWorld(cx, cy);
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    scale *= factor;
    offsetX = cx - wx * scale;
    offsetY = cy + wy * scale;
    _draw();
  }

  function _setTool(t) {
    tool = t;
    const s = document.getElementById('cad-tool-select');
    const p = document.getElementById('cad-tool-pan');
    if (s) s.style.background = t === 'select' ? '#2ea043' : '';
    if (p) p.style.background = t === 'pan' ? '#2ea043' : '';
  }

  /* ─────────────────────────────────────────────────────────
     2D DRAWING
  ───────────────────────────────────────────────────────── */
  function _draw() {
    if (!ctx || !canvas) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Grid
    ctx.strokeStyle = 'rgba(120,140,160,0.08)';
    ctx.lineWidth = 1;
    const gs = 50;
    for (let gx = offsetX % gs; gx < canvas.width; gx += gs) { ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, canvas.height); ctx.stroke(); }
    for (let gy = offsetY % gs; gy < canvas.height; gy += gs) { ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(canvas.width, gy); ctx.stroke(); }

    // Draw entities in order, selection last
    entities.forEach((e, i) => { if (i !== selectedIdx) _drawEntity(e, false); });
    if (selectedIdx >= 0 && entities[selectedIdx]) _drawEntity(entities[selectedIdx], true);
  }

  function _drawEntity(e, isSel) {
    if (!layerVisible[e.layer]) return;
    const color = isSel ? '#ff6b6b' : _layerColor(e.layer, e.color);
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = isSel ? 2 : 1;
    ctx.font = '12px ui-monospace, monospace';

    switch (e.type) {
      case 'LINE': {
        if (e.points.length < 2) return;
        const [x1, y1] = _worldToScreen(e.points[0][0], e.points[0][1]);
        const [x2, y2] = _worldToScreen(e.points[1][0], e.points[1][1]);
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
        break;
      }
      case 'LWPOLYLINE':
      case 'POLYLINE': {
        if (e.points.length < 2) return;
        ctx.beginPath();
        e.points.forEach((p, i) => {
          const [sx, sy] = _worldToScreen(p[0], p[1]);
          i === 0 ? ctx.moveTo(sx, sy) : ctx.lineTo(sx, sy);
        });
        if (e.closed) ctx.closePath();
        ctx.stroke();
        break;
      }
      case 'CIRCLE': {
        const c = e.points[0]; if (!c) return;
        const [sx, sy] = _worldToScreen(c[0], c[1]);
        ctx.beginPath(); ctx.arc(sx, sy, e.radius * scale, 0, Math.PI * 2); ctx.stroke();
        break;
      }
      case 'ARC': {
        const c = e.points[0]; if (!c) return;
        const [sx, sy] = _worldToScreen(c[0], c[1]);
        const a0 = e.rotation || 0;
        const a1 = (e.props && e.props.end_angle != null) ? e.props.end_angle : Math.PI * 2;
        ctx.beginPath();
        // Canvas angles are measured clockwise from +x with Y-down; world is Y-up.
        ctx.arc(sx, sy, e.radius * scale, -a0, -a1, a0 < a1);
        ctx.stroke();
        break;
      }
      case 'TEXT':
      case 'MTEXT': {
        const c = e.points[0]; if (!c) return;
        const [sx, sy] = _worldToScreen(c[0], c[1]);
        ctx.fillText(e.text || '', sx, sy);
        break;
      }
      case 'INSERT': {
        const c = e.points[0]; if (!c) return;
        const [sx, sy] = _worldToScreen(c[0], c[1]);
        ctx.strokeStyle = isSel ? '#ff6b6b' : '#8fa3b8';
        ctx.beginPath();
        ctx.moveTo(sx - 6, sy); ctx.lineTo(sx + 6, sy);
        ctx.moveTo(sx, sy - 6); ctx.lineTo(sx, sy + 6);
        ctx.stroke();
        break;
      }
    }

    // Vertex handles when selected
    if (isSel) {
      ctx.fillStyle = '#ffffff';
      e.points.forEach(p => {
        const [sx, sy] = _worldToScreen(p[0], p[1]);
        ctx.fillRect(sx - 3, sy - 3, 6, 6);
      });
    }
  }

  const LAYER_COLORS = ['#7ec8e3', '#f4a261', '#8ed081', '#e6b8ff', '#ffd166', '#ff8fa3', '#9ee6d8', '#b8c4ff', '#ffb27d', '#9dd9ff'];
  function _layerColor(layer, entityColor) {
    const idx = layers.indexOf(layer);
    return LAYER_COLORS[idx % LAYER_COLORS.length];
  }

  function _renderLayersPanel() {
    const el = document.getElementById('cad-layers');
    if (!el) return;
    el.innerHTML = '<span style="font-size:11px;color:var(--v5d-text-secondary);margin-right:4px">Layers:</span>' +
      layers.map(l => {
        const on = layerVisible[l] !== false;
        return '<label style="display:inline-flex;align-items:center;gap:4px;font-size:11px;cursor:pointer;padding:2px 6px;border:1px solid #2a3442;border-radius:4px;background:' + (on ? '#1a2330' : 'transparent') + '">' +
          '<input type="checkbox" ' + (on ? 'checked' : '') + ' onchange="V5D.CADViewer._toggleLayer(\'' + l.replace(/'/g, "\\'") + '\')">' +
          '<span style="width:8px;height:8px;border-radius:2px;background:' + _layerColor(l) + '"></span>' + l +
          '</label>';
      }).join(' ');
  }

  function _toggleLayer(l) {
    layerVisible[l] = !layerVisible[l];
    _draw();
  }

  /* ─────────────────────────────────────────────────────────
     2D SELECTION + EDITING
  ───────────────────────────────────────────────────────── */
  function _onMouseDown(ev) {
    if (mode !== '2d') return;
    const rect = canvas.getBoundingClientRect();
    const sx = ev.clientX - rect.left, sy = ev.clientY - rect.top;
    const [wx, wy] = _screenToWorld(sx, sy);

    if (tool === 'pan' || ev.button === 1) {
      drag = { kind: 'pan', startX: sx, startY: sy, moved: false };
      return;
    }

    // Vertex handle grab on current selection first
    if (selectedIdx >= 0 && entities[selectedIdx]) {
      const vi = _hitVertex(entities[selectedIdx], wx, wy);
      if (vi >= 0) {
        drag = { kind: 'vertex', idx: selectedIdx, vi, moved: false };
        return;
      }
    }

    const hit = _hitEntity(wx, wy);
    if (hit >= 0) {
      selectedIdx = hit;
      document.getElementById('cad-btn-delete').disabled = false;
      const ent = entities[hit];
      _updateStatus(ent.type + ' · layer "' + ent.layer + '" · ' + ent.points.length + ' pts' +
        ' (drag a vertex to edit, Shift+drag to move)');
      if (ev.shiftKey) { drag = { kind: 'entity', idx: hit, startWX: wx, startWY: wy, moved: false, snapshot: null }; }
      _draw();
    } else {
      selectedIdx = -1;
      document.getElementById('cad-btn-delete').disabled = true;
      _updateStatus('');
      _draw();
    }
  }

  function _onMouseMove(ev) {
    if (mode !== '2d' || !drag) return;
    const rect = canvas.getBoundingClientRect();
    const sx = ev.clientX - rect.left, sy = ev.clientY - rect.top;
    const [wx, wy] = _screenToWorld(sx, sy);

    if (drag.kind === 'pan') {
      offsetX += (sx - drag.startX); offsetY += (sy - drag.startY);
      drag.startX = sx; drag.startY = sy;
      _draw(); return;
    }
    drag.moved = true;

    const ent = entities[drag.idx];
    if (!ent) return;

    if (drag.kind === 'vertex') {
      ent.points[drag.vi] = [wx, wy];
    } else if (drag.kind === 'entity') {
      if (!drag.snapshot) drag.snapshot = ent.points.map(p => [p[0], p[1]]);
      ent.points.forEach((p, i) => {
        p[0] = drag.snapshot[i][0] + (wx - drag.startWX);
        p[1] = drag.snapshot[i][1] + (wy - drag.startWY);
      });
    }
    _draw();
  }

  function _onMouseUp() {
    if (drag && drag.kind !== 'pan' && drag.moved) {
      _updateStatus('✏️ Edited ' + entities[drag.idx].type + ' — Export DXF to save changes');
    }
    drag = null;
  }

  function _hitVertex(e, wx, wy) {
    const tol = 8 / scale;
    for (let i = 0; i < e.points.length; i++) {
      const d = Math.hypot(e.points[i][0] - wx, e.points[i][1] - wy);
      if (d < tol) return i;
    }
    return -1;
  }

  function _hitEntity(wx, wy) {
    const tol = 8 / scale;
    let best = -1, bestD = tol;
    for (let i = 0; i < entities.length; i++) {
      const e = entities[i];
      if (!layerVisible[e.layer]) continue;
      const d = _distToEntity(e, wx, wy);
      if (d < bestD) { bestD = d; best = i; }
    }
    return best;
  }

  function _distToEntity(e, wx, wy) {
    if (e.type === 'CIRCLE') {
      const c = e.points[0]; if (!c) return Infinity;
      return Math.abs(Math.hypot(c[0] - wx, c[1] - wy) - e.radius);
    }
    if (e.type === 'ARC') {
      const c = e.points[0]; if (!c) return Infinity;
      return Math.abs(Math.hypot(c[0] - wx, c[1] - wy) - e.radius);
    }
    if (e.type === 'TEXT' || e.type === 'MTEXT' || e.type === 'INSERT') {
      const c = e.points[0]; if (!c) return Infinity;
      return Math.hypot(c[0] - wx, c[1] - wy);
    }
    // Polyline / LINE segments
    let min = Infinity;
    for (let i = 0; i < e.points.length - 1; i++) {
      min = Math.min(min, _distToSegment(wx, wy, e.points[i], e.points[i + 1]));
    }
    if (e.closed && e.points.length > 2) {
      min = Math.min(min, _distToSegment(wx, wy, e.points[e.points.length - 1], e.points[0]));
    }
    return min;
  }

  function _distToSegment(px, py, a, b) {
    const dx = b[0] - a[0], dy = b[1] - a[1];
    const len2 = dx * dx + dy * dy;
    if (len2 === 0) return Math.hypot(px - a[0], py - a[1]);
    let t = ((px - a[0]) * dx + (py - a[1]) * dy) / len2;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(px - (a[0] + t * dx), py - (a[1] + t * dy));
  }

  function _deleteSelected() {
    if (selectedIdx < 0) return;
    entities.splice(selectedIdx, 1);
    selectedIdx = -1;
    document.getElementById('cad-btn-delete').disabled = true;
    _updateStatus('🗑 Deleted entity');
    _draw();
  }

  /* ─────────────────────────────────────────────────────────
     EXPORT DXF
  ───────────────────────────────────────────────────────── */
  function _exportDxf() {
    if (mode !== '2d' || !entities.length) return;
    const lines = ['0', 'SECTION', '2', 'ENTITIES'];
    entities.forEach(e => {
      const L = e.layer || '0';
      if (e.type === 'LINE' && e.points.length >= 2) {
        lines.push('0', 'LINE', '8', L,
          '10', String(e.points[0][0]), '20', String(e.points[0][1]),
          '11', String(e.points[1][0]), '21', String(e.points[1][1]));
      } else if (e.type === 'CIRCLE' && e.points[0]) {
        lines.push('0', 'CIRCLE', '8', L,
          '10', String(e.points[0][0]), '20', String(e.points[0][1]), '40', String(e.radius || 0));
      } else if (e.type === 'ARC' && e.points[0]) {
        lines.push('0', 'ARC', '8', L,
          '10', String(e.points[0][0]), '20', String(e.points[0][1]), '40', String(e.radius || 0),
          '50', String(((e.rotation || 0) * 180 / Math.PI).toFixed(4)),
          '51', String((((e.props && e.props.end_angle) || Math.PI * 2) * 180 / Math.PI).toFixed(4)));
      } else if (e.type === 'TEXT' && e.points[0]) {
        lines.push('0', 'TEXT', '8', L,
          '10', String(e.points[0][0]), '20', String(e.points[0][1]), '40', '100', '1', e.text || '');
      } else if ((e.type === 'LWPOLYLINE' || e.type === 'POLYLINE') && e.points.length >= 2) {
        lines.push('0', 'LWPOLYLINE', '8', L, '90', String(e.points.length), '70', e.closed ? '1' : '0');
        e.points.forEach(p => lines.push('10', String(p[0]), '20', String(p[1])));
      }
    });
    lines.push('0', 'ENDSEC', '0', 'EOF');

    const blob = new Blob([lines.join('\n')], { type: 'application/dxf' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = (fileName || 'drawing').replace(/\.[^.]+$/, '') + '_edited.dxf';
    a.click();
    _updateStatus('💾 Exported ' + a.download);
  }

  /* ─────────────────────────────────────────────────────────
     3D VIEWER (three.js, lazy ES-module load)
  ───────────────────────────────────────────────────────── */
  async function _init3D(url, fmt) {
    const container = document.getElementById('cad-3d');
    if (!container) return;
    try {
      const THREE = await _loadThree();
      const { OrbitControls } = await import('three/addons/controls/OrbitControls.js');

      const W = container.clientWidth, H = container.clientHeight;
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x1a1a2e);
      const camera = new THREE.PerspectiveCamera(55, W / H, 0.1, 100000);
      camera.position.set(5, 4, 8);

      const renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(W, H);
      renderer.setPixelRatio(window.devicePixelRatio || 1);
      container.appendChild(renderer.domElement);

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;

      scene.add(new THREE.AmbientLight(0xffffff, 0.7));
      const dir = new THREE.DirectionalLight(0xffffff, 1.2);
      dir.position.set(8, 12, 6);
      scene.add(dir);

      const grid = new THREE.GridHelper(20, 20, 0x444466, 0x222233);
      scene.add(grid);

      // Load model by format
      let obj = null;
      if (fmt === 'stl') {
        const { STLLoader } = await import('three/addons/loaders/STLLoader.js');
        const geo = await new STLLoader().loadAsync(url);
        obj = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: 0xd4c5b9, roughness: 0.6, metalness: 0.05 }));
      } else if (fmt === 'glb' || fmt === 'gltf') {
        const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
        const gltf = await new GLTFLoader().loadAsync(url);
        obj = gltf.scene;
      } else if (fmt === 'obj') {
        const { OBJLoader } = await import('three/addons/loaders/OBJLoader.js');
        obj = await new OBJLoader().loadAsync(url);
      } else {
        throw new Error('3D format "' + fmt + '" not supported by the viewer');
      }

      if (obj) {
        // Normalize size + center
        const box = new THREE.Box3().setFromObject(obj);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z) || 1;
        const s = 5 / maxDim;
        obj.scale.setScalar(s);
        box.setFromObject(obj);
        const c2 = box.getCenter(new THREE.Vector3());
        obj.position.sub(c2);
        scene.add(obj);
      }

      three = { scene, camera, renderer, controls, container };
      _threeResize();

      (function animate() {
        if (!three || three.container !== container) return;
        requestAnimationFrame(animate);
        three.controls.update();
        three.renderer.render(three.scene, three.camera);
      })();
    } catch (e) {
      container.innerHTML = '<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#ff8a8a;text-align:center;padding:20px">3D view failed: ' +
        (e && e.message ? e.message : e) + '<br><span style="font-size:12px;color:#5b6673">(3D needs internet access to load three.js from CDN)</span></div>';
      _updateStatus('❌ 3D load failed');
    }
  }

  function _loadThree() {
    if (_threeLoaded) return import('three');
    return new Promise((resolve, reject) => {
      // Inject importmap so bare 'three' / 'three/addons/' resolve from CDN.
      if (!document.querySelector('script[type="importmap"]')) {
        const im = document.createElement('script');
        im.type = 'importmap';
        im.textContent = JSON.stringify({
          imports: {
            'three': 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js',
            'three/addons/': 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/'
          }
        });
        document.head.appendChild(im);
      }
      // Give the importmap a tick to register, then import.
      setTimeout(() => {
        import('three').then(m => { _threeLoaded = true; resolve(m); }).catch(reject);
      }, 0);
    });
  }

  function _threeResize() {
    if (!three) return;
    const W = three.container.clientWidth, H = three.container.clientHeight;
    three.camera.aspect = W / H;
    three.camera.updateProjectionMatrix();
    three.renderer.setSize(W, H);
  }

  /* ── Public API ── */
  return {
    render, _browse, _dropHint, _fit, _zoom, _setTool,
    _toggleLayer, _deleteSelected, _exportDxf,
  };
})();
