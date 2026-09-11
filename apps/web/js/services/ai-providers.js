/* ═══════════════════════════════════════════════════════════
   Vision 5D — AI Providers Service
   Provider CRUD, credential management, model discovery, testing
   SECURITY: Raw API keys are NEVER stored in browser memory
             after save. Keys are sent to backend immediately
             and cleared from the input field.
   ═══════════════════════════════════════════════════════════ */

V5D.AIProviders = (() => {

  /* ── Configuration-driven provider registry ── */
  const PROVIDER_REGISTRY = {
    openai: {
      name: 'OpenAI', icon: '🤖',
      base_url: 'https://api.openai.com/v1',
      capabilities: ['chat', 'vision', 'structured_output', 'tool_calling', 'reasoning'],
      default_model: 'gpt-4o',
      models: [
        { id: 'gpt-4o', name: 'GPT-4o', context: 128000, capabilities: ['chat','vision','structured_output','tool_calling'] },
        { id: 'gpt-4o-mini', name: 'GPT-4o Mini', context: 128000, capabilities: ['chat','vision','structured_output'] },
        { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', context: 128000, capabilities: ['chat','vision'] },
      ]
    },
    anthropic: {
      name: 'Anthropic', icon: '🧠',
      base_url: 'https://api.anthropic.com/v1',
      capabilities: ['chat', 'vision', 'tool_calling'],
      default_model: 'claude-sonnet-4-20250514',
      models: [
        { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4', context: 200000, capabilities: ['chat','vision','tool_calling'] },
        { id: 'claude-opus-4-20250514', name: 'Claude Opus 4', context: 200000, capabilities: ['chat','vision','tool_calling','reasoning'] },
        { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku', context: 200000, capabilities: ['chat','vision'] },
      ]
    },
    google: {
      name: 'Google AI', icon: '\uD83C\uDF10',
      base_url: 'https://generativelanguage.googleapis.com/v1beta',
      capabilities: ['chat', 'vision', 'structured_output'],
      default_model: 'gemini-2.0-flash',
      models: [
        { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', context: 1048576, capabilities: ['chat','vision','structured_output'] },
        { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro', context: 1048576, capabilities: ['chat','vision','structured_output','reasoning'] },
        { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', context: 1048576, capabilities: ['chat','vision'] },
      ]
    },
    nvidia: {
      name: 'NVIDIA NIM', icon: '\uD83D\uDD35',
      base_url: 'https://integrate.api.nvidia.com/v1',
      capabilities: ['chat', 'vision', 'structured_output'],
      default_model: 'meta/llama-3.2-11b-vision-instruct',
      models: [
        { id: 'meta/llama-3.2-11b-vision-instruct', name: 'Llama 3.2 11B Vision', context: 128000, capabilities: ['chat','vision','structured_output'] },
        { id: 'nvidia/llama-3.1-nemotron-70b-instruct', name: 'Nemotron 70B', context: 128000, capabilities: ['chat','structured_output','reasoning'] },
      ]
    },
    deepseek: {
      name: 'DeepSeek', icon: '🔍',
      base_url: 'https://api.deepseek.com/v1',
      capabilities: ['chat', 'tool_calling'],
      default_model: 'deepseek-chat',
      models: [
        { id: 'deepseek-chat', name: 'DeepSeek Chat', context: 128000, capabilities: ['chat','tool_calling'] },
        { id: 'deepseek-reasoner', name: 'DeepSeek Reasoner', context: 128000, capabilities: ['chat','reasoning'] },
      ]
    },
    mistral: {
      name: 'Mistral AI', icon: '🌪️',
      base_url: 'https://api.mistral.ai/v1',
      capabilities: ['chat', 'tool_calling'],
      default_model: 'mistral-large-latest',
      models: [
        { id: 'mistral-large-latest', name: 'Mistral Large', context: 128000, capabilities: ['chat','tool_calling'] },
        { id: 'mistral-small-latest', name: 'Mistral Small', context: 32000, capabilities: ['chat'] },
      ]
    },
  };

  /* ── Public API ── */

  function getProviderTypes() {
    return Object.keys(PROVIDER_REGISTRY).map(key => ({
      id: key,
      name: PROVIDER_REGISTRY[key].name,
      icon: PROVIDER_REGISTRY[key].icon,
      capabilities: PROVIDER_REGISTRY[key].capabilities,
    }));
  }

  function getProviderConfig(providerType) {
    return PROVIDER_REGISTRY[providerType] || null;
  }

  function getModels(providerType) {
    const cfg = PROVIDER_REGISTRY[providerType];
    return cfg ? cfg.models : [];
  }

  /* ── Backend API calls ── */

  async function listProviders(workspaceId) {
    const d = await V5D.API.get(`/api/v1/workspaces/${workspaceId}/providers`);
    return d.providers || [];
  }

  async function createProvider(workspaceId, providerType, displayName, baseUrl) {
    const cfg = PROVIDER_REGISTRY[providerType];
    return V5D.API.post(`/api/v1/workspaces/${workspaceId}/providers`, {
      workspace_id: workspaceId,
      provider_type: providerType,
      display_name: displayName || cfg.name,
      base_url: baseUrl || cfg.base_url,
      default_model_id: cfg.default_model,
    });
  }

  async function getCredentialStatus(providerId) {
    return V5D.API.get(`/api/v1/providers/${providerId}/credentials`);
  }

  async function saveCredentials(providerId, apiKey, keyLabel) {
    const result = await V5D.API.post(`/api/v1/providers/${providerId}/credentials`, {
      provider_id: providerId,
      api_key: apiKey,
      key_label: keyLabel || 'default',
    });
    return result;
  }

  async function deleteCredentials(providerId) {
    return V5D.API.delete(`/api/v1/providers/${providerId}/credentials`);
  }

  async function testProvider(providerId, modelId) {
    return V5D.API.post(`/api/v1/providers/${providerId}/test`, {
      model_id: modelId,
      timeout_seconds: 15,
    });
  }

  async function discoverModels(providerId) {
    return V5D.API.get(`/api/v1/providers/${providerId}/models`);
  }

  async function setDefaultModel(providerId, modelId) {
    return V5D.API.put(`/api/v1/providers/${providerId}/default-model`, {
      provider_id: providerId,
      model_id: modelId,
    });
  }

  return {
    PROVIDER_REGISTRY,
    getProviderTypes, getProviderConfig, getModels,
    listProviders, createProvider,
    getCredentialStatus, saveCredentials, deleteCredentials,
    testProvider, discoverModels, setDefaultModel,
  };
})();
