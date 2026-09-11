/* ═══════════════════════════════════════════════════════════
   Vision 5D — AI Configuration View
   Provider selection, model selection, API key management,
   connection testing, credential status display.
   SECURITY: Raw API keys cleared from memory after save.
   ═══════════════════════════════════════════════════════════ */

V5D.Views.renderAIConfig = (() => {
  const AI = V5D.AIProviders;
  const C = V5D.Components;
  const P = V5D.Projects;

  let _currentProviderId = null;
  let _currentProviderType = null;
  let _wsId = null;

  async function _getWS() {
    if (!_wsId) _wsId = await P.getWorkspaceId();
    return _wsId;
  }

  async function render() {
    const header = document.getElementById('app-header');
    header.innerHTML = C.Header('AI Configuration', V5D.Auth.isAuthenticated() ? 'connected' : 'disconnected');

    const content = document.getElementById('app-content');

    /* Show sign-in prompt if not authenticated */
    if (!V5D.Auth.isAuthenticated()) {
      content.innerHTML = C.EmptyState('🔑', 'Sign In Required',
        'You need to sign in before configuring AI providers.',
        'Sign In', "V5D.Auth.login().then(function(){ V5D.Views.renderAIConfig.render(); })");
      return;
    }

    content.innerHTML = `
      <div class="page-header">
        <h1>AI Provider Configuration</h1>
        <p>Connect Vision 5D to LLM providers for AI-powered design proposals, analysis, and automation.</p>
      </div>

      <div class="content-grid">
        <div>
          <!-- Provider Selector -->
          <div class="card">
            <div class="card-header"><span class="card-title">Select Provider</span></div>
            <div id="provider-selector">${C.LoadingSkeleton('text')}</div>
          </div>

          <!-- Provider Details -->
          <div class="card" id="provider-details-card" style="display:none">
            <div class="card-header"><span class="card-title">Provider Details</span></div>
            <div id="provider-details"></div>
          </div>

          <!-- Credential Management -->
          <div class="card" id="credential-card" style="display:none">
            <div class="card-header"><span class="card-title">API Credentials</span><span id="cred-status-badge"></span></div>
            <div id="credential-form"></div>
          </div>
        </div>

        <div>
          <!-- Security Notice -->
          <div class="card">
            <div class="card-header"><span class="card-title">🔒 Security</span></div>
            <div style="font-size:13px;color:var(--v5d-text-secondary);line-height:1.6">
              <p>API keys are encrypted with AES-256-GCM before storage.</p>
              <p>Keys are <strong>never</strong> returned to the browser after saving.</p>
              <p>Keys are <strong>never</strong> stored in localStorage, sessionStorage, or cookies.</p>
              <p>Keys are <strong>never</strong> committed to source code or logs.</p>
              <p>All provider requests are proxied through the Vision 5D backend.</p>
            </div>
          </div>

          <!-- Connection Status -->
          <div class="card" id="connection-card" style="display:none">
            <div class="card-header"><span class="card-title">Connection Status</span></div>
            <div id="connection-status"></div>
          </div>
        </div>
      </div>`;

    /* Load provider types */
    _renderProviderSelector();
  }

  function _renderProviderSelector() {
    const providers = AI.getProviderTypes();
    const container = document.getElementById('provider-selector');
    container.innerHTML = providers.map(p => `
      <div class="provider-option" onclick="V5D.Views.renderAIConfig._selectProvider('${p.id}')"
           style="display:flex;align-items:center;gap:12px;padding:12px;border:1px solid var(--v5d-border-light);border-radius:8px;margin-bottom:8px;cursor:pointer;transition:all 150ms"
           onmouseover="this.style.borderColor='var(--v5d-accent)'" onmouseout="this.style.borderColor='var(--v5d-border-light)'"
           role="button" tabindex="0" aria-label="Select ${p.name}"
           onkeydown="if(event.key==='Enter')V5D.Views.renderAIConfig._selectProvider('${p.id}')">
        <span style="font-size:24px">${p.icon}</span>
        <div style="flex:1">
          <div style="font-weight:600">${p.name}</div>
          <div style="font-size:12px;color:var(--v5d-text-secondary)">${p.capabilities.join(', ')}</div>
        </div>
        <span style="font-size:20px;color:var(--v5d-text-tertiary)">→</span>
      </div>
    `).join('');
  }

  async function _selectProvider(providerType) {
    _currentProviderType = providerType;
    const cfg = AI.getProviderConfig(providerType);
    if (!cfg) return;

    /* Check auth first */
    if (!V5D.Auth.isAuthenticated()) {
      _showError('Please sign in first to configure providers.');
      return;
    }

    /* Try to find existing provider in workspace, or create one */
    let providerId = null;
    try {
      const wsId = await _getWS();
      const existing = await AI.listProviders(wsId);
      const found = existing.find(p => p.provider_type === providerType);
      if (found) {
        providerId = found.provider_id;
      }
    } catch(e) {
      if (e.code === 'AUTH_EXPIRED') {
        _showError('Session expired. Please sign in again.');
        return;
      }
      console.warn('[AI Config] List providers failed:', e.message);
    }

    if (!providerId) {
      try {
        const wsId2 = await _getWS();
        const created = await AI.createProvider(wsId2, providerType);
        providerId = created.provider_id;
      } catch(e) {
        if (e.code === 'AUTH_EXPIRED') {
          _showError('Session expired. Please sign in again.');
        } else {
          _showError('Could not create provider: ' + (e.message || 'Unknown error'));
        }
        return;
      }
    }

    _currentProviderId = providerId;
    await _renderProviderDetails(providerId, cfg);
    await _renderCredentialForm(providerId);
    await _renderConnectionStatus(providerId);
  }

  async function _renderProviderDetails(providerId, cfg) {
    const card = document.getElementById('provider-details-card');
    card.style.display = 'block';

    /* Get backend status */
    let backendStatus = null;
    try {
      backendStatus = await AI.getCredentialStatus(providerId);
    } catch(e) { /* ignore */ }

    const details = document.getElementById('provider-details');
    details.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px">
        <div style="color:var(--v5d-text-secondary)">Provider</div><div style="font-weight:500">${cfg.name}</div>
        <div style="color:var(--v5d-text-secondary)">API Base</div><div style="font-family:monospace;font-size:12px">${cfg.base_url}</div>
        <div style="color:var(--v5d-text-secondary)">Capabilities</div><div>${cfg.capabilities.join(', ')}</div>
        <div style="color:var(--v5d-text-secondary)">Default Model</div><div>${cfg.default_model}</div>
        <div style="color:var(--v5d-text-secondary)">Credentials</div>
        <div>${backendStatus && backendStatus.configured
          ? C.StatusBadge('Configured', 'success')
          : C.StatusBadge('Not Configured', 'warning')}</div>
      </div>

      <div style="margin-top:16px"><strong style="font-size:13px">Available Models</strong></div>
      <div id="model-list" style="margin-top:8px;display:flex;flex-direction:column;gap:6px">
        ${cfg.models.map(m => `
          <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:var(--v5d-bg-secondary);border-radius:6px;font-size:13px">
            <div>
              <span style="font-weight:500">${m.name}</span>
              <span style="color:var(--v5d-text-secondary);font-size:11px;margin-left:8px">${(m.context/1000).toFixed(0)}K ctx</span>
            </div>
            <div>
              <span style="font-size:11px;color:var(--v5d-text-tertiary);margin-right:8px">${m.capabilities.slice(0,3).join(', ')}</span>
              <button class="btn btn-sm btn-secondary"
                onclick="V5D.Views.renderAIConfig._setDefaultModel('${m.id}')"
                ${cfg.default_model === m.id ? 'style="background:var(--v5d-accent);color:#fff"' : ''}>
                ${cfg.default_model === m.id ? 'Default' : 'Set Default'}
              </button>
            </div>
          </div>
        `).join('')}
      </div>`;
  }

  function _renderCredentialForm(providerId) {
    const card = document.getElementById('credential-card');
    card.style.display = 'block';

    const form = document.getElementById('credential-form');

    /* Load current status */
    AI.getCredentialStatus(providerId).then(status => {
      const configured = status.configured;
      form.innerHTML = `
        <div style="margin-bottom:12px">
          <label style="font-size:13px;font-weight:500;display:block;margin-bottom:4px">API Key</label>
          <div style="display:flex;gap:8px">
            <input type="password" id="api-key-input"
              placeholder="${configured ? '•••••••• (enter new key to replace)' : 'Enter API key'}"
              style="flex:1;padding:8px 12px;border:1px solid var(--v5d-border);border-radius:6px;font-size:13px;font-family:monospace"
              aria-label="API Key input">
            <button class="btn btn-primary" id="save-key-btn"
              onclick="V5D.Views.renderAIConfig._saveCredentials()">
              ${configured ? 'Replace' : 'Save'}
            </button>
          </div>
          <div style="font-size:11px;color:var(--v5d-text-tertiary);margin-top:4px">
            Your key is encrypted with AES-256-GCM and never stored in plaintext.
          </div>
        </div>

        <div style="display:flex;gap:8px">
          <button class="btn btn-secondary" id="test-btn"
            onclick="V5D.Views.renderAIConfig._testConnection()"
            ${!configured ? 'disabled style="opacity:0.5"' : ''}>
            🔍 Test Connection
          </button>
          ${configured ? `
            <button class="btn btn-danger" onclick="V5D.Views.renderAIConfig._deleteCredentials()">
              🗑️ Remove Credentials
            </button>
          ` : ''}
        </div>
        <div id="cred-feedback" style="margin-top:8px;font-size:13px"></div>
      `;
    }).catch(() => {
      form.innerHTML = C.ErrorState('⚠️', 'Could not load credential status', 'Backend may be unavailable');
    });
  }

  async function _saveCredentials() {
    const input = document.getElementById('api-key-input');
    const feedback = document.getElementById('cred-feedback');
    const key = input.value.trim();

    if (!key) {
      feedback.innerHTML = C.StatusBadge('Please enter an API key', 'warning');
      return;
    }

    if (key.length < 10) {
      feedback.innerHTML = C.StatusBadge('API key appears too short', 'warning');
      return;
    }

    feedback.innerHTML = C.StatusBadge('Saving...', 'info');
    const saveBtn = document.getElementById('save-key-btn');
    saveBtn.disabled = true;

    try {
      await AI.saveCredentials(_currentProviderId, key, 'default');
      feedback.innerHTML = C.StatusBadge('✓ Saved securely', 'success');
      /* CRITICAL: Clear key from memory */
      input.value = '';
      /* Overwrite with placeholder to prevent browser autofill retention */
      setTimeout(() => { input.value = ''; }, 100);
      setTimeout(() => { input.value = ''; }, 500);
    } catch(e) {
      feedback.innerHTML = C.StatusBadge('Save failed: ' + (e.message || 'Unknown error'), 'error');
    } finally {
      saveBtn.disabled = false;
      /* Re-render to show updated state */
      setTimeout(() => _renderCredentialForm(_currentProviderId), 1000);
    }
  }

  async function _testConnection() {
    const feedback = document.getElementById('cred-feedback');
    const testBtn = document.getElementById('test-btn');
    feedback.innerHTML = C.StatusBadge('Testing connection...', 'info');
    testBtn.disabled = true;

    try {
      const result = await AI.testProvider(_currentProviderId);
      if (result.result_code === 'SUCCESS') {
        feedback.innerHTML = C.StatusBadge(`✓ Connected — ${result.latency_ms}ms — ${result.model_tested || ''}`, 'success');
      } else if (result.result_code === 'INVALID_CREDENTIAL') {
        feedback.innerHTML = C.StatusBadge('✗ Invalid API key', 'error');
      } else if (result.result_code === 'NETWORK_TIMEOUT') {
        feedback.innerHTML = C.StatusBadge('✗ Connection timed out', 'error');
      } else if (result.result_code === 'PROVIDER_UNAVAILABLE') {
        feedback.innerHTML = C.StatusBadge('✗ Provider unavailable', 'error');
      } else {
        feedback.innerHTML = C.StatusBadge('✗ ' + (result.result_code || 'Unknown error'), 'error');
      }
      _renderConnectionStatus(_currentProviderId);
    } catch(e) {
      if (e.code === 'RATE_LIMITED') {
        feedback.innerHTML = C.StatusBadge('⏳ Rate limited — please wait', 'warning');
      } else {
        feedback.innerHTML = C.StatusBadge('Test failed: ' + (e.message || 'Network error'), 'error');
      }
    } finally {
      testBtn.disabled = false;
    }
  }

  async function _deleteCredentials() {
    if (!confirm('Remove API credentials for this provider? This cannot be undone.')) return;

    const feedback = document.getElementById('cred-feedback');
    feedback.innerHTML = C.StatusBadge('Removing...', 'info');

    try {
      await AI.deleteCredentials(_currentProviderId);
      feedback.innerHTML = C.StatusBadge('✓ Credentials removed', 'success');
      setTimeout(() => _renderCredentialForm(_currentProviderId), 500);
      setTimeout(() => _renderConnectionStatus(_currentProviderId), 500);
    } catch(e) {
      feedback.innerHTML = C.StatusBadge('Failed: ' + (e.message || 'Unknown error'), 'error');
    }
  }

  async function _setDefaultModel(modelId) {
    if (!_currentProviderId) return;
    try {
      await AI.setDefaultModel(_currentProviderId, modelId);
      /* Re-render model list */
      const cfg = AI.getProviderConfig(_currentProviderType);
      await _renderProviderDetails(_currentProviderId, cfg);
    } catch(e) {
      _showError('Failed to set default model: ' + (e.message || ''));
    }
  }

  async function _renderConnectionStatus(providerId) {
    const card = document.getElementById('connection-card');
    const statusDiv = document.getElementById('connection-status');

    try {
      const status = await AI.getCredentialStatus(providerId);
      card.style.display = 'block';

      const online = status.connection_status === 'HEALTHY';
      statusDiv.innerHTML = `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
          <div style="width:10px;height:10px;border-radius:50%;background:${online ? 'var(--v5d-success)' : 'var(--v5d-text-tertiary)'}"></div>
          <span style="font-weight:500;font-size:14px">${online ? 'Connected' : 'Not Connected'}</span>
        </div>
        <div style="font-size:13px;color:var(--v5d-text-secondary)">
          <div>Credentials: ${status.configured ? C.StatusBadge('Configured', 'success') : C.StatusBadge('Not Configured', 'warning')}</div>
          ${status.masked_key ? `<div style="margin-top:4px">Key: <span style="font-family:monospace">${status.masked_key}</span></div>` : ''}
          ${status.last_tested_at ? `<div style="margin-top:4px">Last tested: ${new Date(status.last_tested_at).toLocaleString()}</div>` : ''}
        </div>
      `;
    } catch(e) {
      card.style.display = 'block';
      statusDiv.innerHTML = `<div class="state-description">Connection status unavailable</div>`;
    }
  }

  function _showError(msg) {
    /* Try credential feedback first, then provider selector */
    var feedback = document.getElementById('cred-feedback');
    if (feedback) {
      feedback.innerHTML = C.StatusBadge(msg, 'error');
    } else {
      var selector = document.getElementById('provider-selector');
      if (selector) {
        var errEl = document.createElement('div');
        errEl.style.cssText = 'margin-top:8px;font-size:13px;color:var(--v5d-error);padding:8px 12px;background:var(--v5d-error-bg);border-radius:6px;';
        errEl.textContent = msg;
        selector.appendChild(errEl);
      }
    }
    console.error('[AI Config]', msg);
  }

  /* Expose methods globally for onclick handlers */
  return { render, _selectProvider, _saveCredentials, _testConnection, _deleteCredentials, _setDefaultModel };
})();
