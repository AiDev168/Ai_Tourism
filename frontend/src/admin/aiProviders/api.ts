export type ProviderCapability = 'chat' | 'vision' | 'embedding' | 'reranking';
export type CapabilitySupport = 'supported' | 'unsupported' | 'unknown';
export type CapabilitySupportMap = Record<ProviderCapability, CapabilitySupport>;
export type CapabilityBinding = { model_id: string; max_tokens?: number };
export type ProviderProfile = {
  id: string; name: string; provider_kind: 'lm_studio' | 'openai_compatible'; base_url: string;
  auth_mode: 'none' | 'bearer'; enabled: boolean; capabilities: Partial<Record<ProviderCapability, CapabilityBinding>>;
  timeout_seconds: number; concurrency_limit: number; version: number; secret_configured: boolean;
};
export type ProfileInput = Omit<ProviderProfile, 'id' | 'version' | 'secret_configured'> & { api_key?: string };
export type ProviderRevision = { revision: string; profile_id: string; profile_name: string; capability: ProviderCapability; model_id: string; validation_status: 'pending' | 'valid' | 'invalid' | 'unavailable'; validated_at: string | null; active: boolean };
export type ActiveRoute = { capability: ProviderCapability; profile_id: string | null; profile_name: string | null; revision: string | null; model_id: string | null; active: boolean; version: number };
export type AdminMe = { admin: boolean; mfa_enrolled: boolean; step_up_expires_at: string | null; provisioned: boolean };
export type AdminAuditEvent = { action: string; actor: string; target: string | null; result: string; created_at: string };
export type AdminUsage = { capability: ProviderCapability; calls: number; successes: number; failures: number; latency_ms_avg: number | null; period_start: string };
export type ModelDiscovery = { models: string[]; status: 'reachable' | 'unavailable'; capability_support: CapabilitySupportMap };
export type ConnectionTestStatus = 'models_catalog_reachable' | 'inference_passed' | 'model_not_found' | 'unsupported' | 'authentication_failed' | 'unavailable';
export type ConnectionTestKind = 'discovery' | 'inference';
export type ConnectionTest = {
  success: boolean; status: ConnectionTestStatus; latency_ms: number | null; model_id: string;
  capability: ProviderCapability; test_kind: ConnectionTestKind;
  models_catalog_reachable: boolean; model_selected: boolean; capability_verified: boolean;
  actual_inference_passed: boolean;
};
export type FallbackPolicy = { capability: ProviderCapability; enabled: boolean; ordered_revision_ids: string[] };

export class ProviderAdminApiError extends Error {
  constructor(readonly status: number, readonly code: string) { super(code); }
}

async function request<T>(csrfToken: string, path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1/admin/ai-providers${path}`, {
    ...init, credentials: 'same-origin', cache: 'no-store',
    headers: {
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(init.method && init.method !== 'GET' ? { 'X-CSRF-Token': csrfToken } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    let code = response.status === 401 ? 'unauthenticated' : response.status === 403 ? 'forbidden' : 'request_failed';
    try { code = (await response.json() as { error?: { code?: string } }).error?.code ?? code; } catch { /* safe generic code */ }
    throw new ProviderAdminApiError(response.status, code);
  }
  if (response.status === 204) return undefined as T;
  return await response.json() as T;
}

const json = (body: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(body) });

export const providerAdminApi = {
  me: (csrf = '') => request<AdminMe>(csrf, '/me'),
  enrollMfa: (csrf: string) => request<{ secret: string; otpauth_uri: string }>(csrf, '/mfa/enroll', json({})),
  verifyMfa: (csrf: string, code: string) => request<{ mfa_enrolled: boolean; recovery_codes: string[] }>(csrf, '/mfa/verify', json({ code })),
  stepUp: (csrf: string, code: string) => request<{ step_up_expires_at: string }>(csrf, '/mfa/step-up', json({ code })),
  recoveryStepUp: (csrf: string, code: string) => request<{ step_up_expires_at: string }>(csrf, '/mfa/recovery', json({ code })),
  profiles: (csrf: string) => request<{ profiles: ProviderProfile[] }>(csrf, '/profiles'),
  createProfile: (csrf: string, input: ProfileInput) => request<ProviderProfile>(csrf, '/profiles', json(input)),
  updateProfile: (csrf: string, id: string, input: Partial<ProfileInput> & { expected_version: number }) => request<ProviderProfile>(csrf, `/profiles/${encodeURIComponent(id)}`, { ...json(input), method: 'PATCH' }),
  archiveProfile: (csrf: string, id: string) => request<void>(csrf, `/profiles/${encodeURIComponent(id)}/archive`, json({})),
  discoverModels: (csrf: string, id: string) => request<ModelDiscovery>(csrf, `/profiles/${encodeURIComponent(id)}/discover-models`, json({})),
  testConnection: (csrf: string, id: string, capability: ProviderCapability, model_id: string) => request<ConnectionTest>(csrf, `/profiles/${encodeURIComponent(id)}/test`, json({ capability, model_id, test_kind: 'discovery' })),
  testInference: (csrf: string, id: string, capability: ProviderCapability, model_id: string, max_output_tokens = 32) => {
    if (!Number.isInteger(max_output_tokens) || max_output_tokens < 1 || max_output_tokens > 64) throw new RangeError('max_output_tokens must be an integer from 1 to 64');
    return request<ConnectionTest>(csrf, `/profiles/${encodeURIComponent(id)}/test`, json({ capability, model_id, test_kind: 'inference', max_output_tokens }));
  },
  routes: (csrf: string) => request<{ routes: ActiveRoute[] }>(csrf, '/routes'),
  activate: (csrf: string, capability: ProviderCapability, profile_id: string, revision: string, expected_version: number) => request<ActiveRoute>(csrf, `/routes/${capability}/activate`, json({ profile_id, revision, expected_version })),
  deactivate: (csrf: string, capability: ProviderCapability, expected_version: number) => request<ActiveRoute>(csrf, `/routes/${capability}/deactivate`, json({ expected_version })),
  rollback: (csrf: string, capability: ProviderCapability, revision: string, expected_version: number) => request<ActiveRoute>(csrf, `/routes/${capability}/rollback`, json({ revision, expected_version })),
  revisions: (csrf: string) => request<{ revisions: ProviderRevision[] }>(csrf, '/revisions'),
  audit: (csrf: string) => request<{ events: AdminAuditEvent[] }>(csrf, '/audit'),
  usage: (csrf: string) => request<{ usage: AdminUsage[] }>(csrf, '/usage'),
  fallbacks: (csrf: string) => request<{ policies: FallbackPolicy[] }>(csrf, '/fallback'),
  saveFallback: (csrf: string, policy: FallbackPolicy) => request<FallbackPolicy>(csrf, `/fallback/${policy.capability}`, { method: 'PUT', body: JSON.stringify({ enabled: policy.enabled, ordered_revision_ids: policy.ordered_revision_ids }) }),
};
