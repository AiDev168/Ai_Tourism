import { afterEach, describe, expect, it, vi } from 'vitest';
import { providerAdminApi } from './api';

afterEach(() => vi.unstubAllGlobals());

describe('provider administration client', () => {
  it('uses same-origin cookies, no-store, and CSRF only on mutations', async () => {
    const fetchMock = vi.fn().mockImplementation(() => new Response(JSON.stringify({ profiles: [] }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    await providerAdminApi.profiles('csrf-in-memory');
    await providerAdminApi.createProfile('csrf-in-memory', {
      name: 'Local', provider_kind: 'lm_studio', base_url: 'http://127.0.0.1:1234/v1', auth_mode: 'none',
      enabled: true, capabilities: { chat: { model_id: 'loaded-model', max_tokens: 50 } }, timeout_seconds: 10,
      concurrency_limit: 1, api_key: '',
    });
    const getOptions = fetchMock.mock.calls[0][1] as RequestInit;
    const postOptions = fetchMock.mock.calls[1][1] as RequestInit;
    expect(getOptions.credentials).toBe('same-origin');
    expect(getOptions.cache).toBe('no-store');
    expect((getOptions.headers as Record<string, string>)['X-CSRF-Token']).toBeUndefined();
    expect((postOptions.headers as Record<string, string>)['X-CSRF-Token']).toBe('csrf-in-memory');
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/v1/admin/ai-providers/profiles');
    expect(JSON.parse(String(postOptions.body)).api_key).toBe('');
  });

  it('maps denied access to a typed error without echoing response text', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: 'forbidden' }, secret: 'must-not-leak' }), { status: 403 })));
    await expect(providerAdminApi.me()).rejects.toMatchObject({ status: 403, code: 'forbidden' });
  });

  it('submits recovery codes only to the one-time recovery step-up endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ step_up_expires_at: '2099-01-01T00:00:00Z' }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    await providerAdminApi.recoveryStepUp('csrf-memory', 'one-time-test-code');
    expect(String(fetchMock.mock.calls[0][0])).toContain('/mfa/recovery');
    expect(JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body))).toEqual({ code: 'one-time-test-code' });
    expect(((fetchMock.mock.calls[0][1] as RequestInit).headers as Record<string, string>)['X-CSRF-Token']).toBe('csrf-memory');
  });

  it('keeps discovery distinct from bounded explicit inference and uses per-capability fallback routes', async () => {
    const fetchMock = vi.fn().mockImplementation((_url: string, init?: RequestInit) => new Response(JSON.stringify(init?.method === 'PUT' ? { capability: 'vision', enabled: true, ordered_revision_ids: ['rev-v'] } : { status: 'reachable', models: ['vision-model'], capability_support: { chat: 'unknown', vision: 'supported', embedding: 'unsupported', reranking: 'unknown' } }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    await providerAdminApi.discoverModels('csrf', 'profile/one');
    await providerAdminApi.testConnection('csrf', 'profile/one', 'vision', 'vision-model');
    await providerAdminApi.testInference('csrf', 'profile/one', 'vision', 'vision-model');
    await providerAdminApi.saveFallback('csrf', { capability: 'vision', enabled: true, ordered_revision_ids: ['rev-v'] });
    expect(String(fetchMock.mock.calls[0][0])).toContain('/profiles/profile%2Fone/discover-models');
    expect(JSON.parse(String((fetchMock.mock.calls[1][1] as RequestInit).body))).toEqual({ capability: 'vision', model_id: 'vision-model', test_kind: 'discovery' });
    expect(JSON.parse(String((fetchMock.mock.calls[2][1] as RequestInit).body))).toEqual({ capability: 'vision', model_id: 'vision-model', test_kind: 'inference', max_output_tokens: 32 });
    expect(String(fetchMock.mock.calls[3][0])).toContain('/fallback/vision');
    expect(JSON.parse(String((fetchMock.mock.calls[3][1] as RequestInit).body))).toEqual({ enabled: true, ordered_revision_ids: ['rev-v'] });
    expect(() => providerAdminApi.testInference('csrf', 'p', 'chat', 'm', 65)).toThrow(RangeError);
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });
});
