// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AiProviderAdminPanel } from './AiProviderAdminPanel';

let root: Root;
let host: HTMLDivElement;
function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }); }
async function settle() { await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); }); }

beforeEach(() => { (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true; host = document.createElement('div'); document.body.append(host); root = createRoot(host); });
afterEach(() => { act(() => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('AI provider admin panel', () => {
  it('shows a real localized authorization denial and does not load profile data', async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({ admin: false, mfa_enrolled: false, step_up_expires_at: null, provisioned: true })); vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AiProviderAdminPanel locale="fa-IR" csrfToken="csrf" />); }); await settle();
    expect(host.textContent).toContain('مدیریت ارائه‌دهندگان هوش مصنوعی');
    expect(host.textContent).toContain('این حساب مجوز مدیریت ارائه‌دهندگان را ندارد.');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('renders English step-up and empty-profile states from backend data', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith('/me')) return Promise.resolve(json({ admin: true, mfa_enrolled: true, step_up_expires_at: null, provisioned: true }));
      return Promise.resolve(json({ profiles: [], routes: [], revisions: [], events: [], usage: [] }));
    }); vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AiProviderAdminPanel locale="en-US" csrfToken="csrf" />); }); await settle();
    expect(host.textContent).toContain('Enter your authenticator code');
    expect(host.querySelector('input[autocomplete="one-time-code"]')).not.toBeNull();
  });

  it('renders Arabic RTL admin copy and no configured profile empty state after step-up', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith('/me')) return Promise.resolve(json({ admin: true, mfa_enrolled: true, step_up_expires_at: '2099-01-01T00:00:00Z', provisioned: true }));
      if (url.endsWith('/profiles')) return Promise.resolve(json({ profiles: [] }));
      if (url.endsWith('/routes')) return Promise.resolve(json({ routes: [] }));
      if (url.endsWith('/revisions')) return Promise.resolve(json({ revisions: [] }));
      if (url.endsWith('/audit')) return Promise.resolve(json({ events: [] }));
      if (url.endsWith('/fallback')) return Promise.resolve(json({ capability: 'chat', enabled: false, ordered_revision_ids: [] }));
      return Promise.resolve(json({ usage: [] }));
    }); vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AiProviderAdminPanel locale="ar" csrfToken="csrf" />); }); await settle();
    expect(host.querySelector('main')?.getAttribute('dir')).toBe('rtl');
    expect(host.textContent).toContain('لا توجد ملفات إعداد بعد.');
    expect(host.textContent).toContain('المسارات النشطة');
    expect(host.textContent).toContain('البديل للمحادثة متوقف');
    await act(async () => { host.querySelector<HTMLButtonElement>('.provider-admin-heading button')?.click(); });
    const capabilityToggles = [...host.querySelectorAll<HTMLInputElement>('fieldset input[type="checkbox"]')];
    expect(capabilityToggles).toHaveLength(4);
    expect(capabilityToggles[0].disabled).toBe(false);
    expect(capabilityToggles.slice(1).every(toggle => toggle.disabled)).toBe(true);
  });

  it('selects the documented GapGPT host without running a test or selecting a model', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith('/me')) return Promise.resolve(json({ admin: true, mfa_enrolled: true, step_up_expires_at: '2099-01-01T00:00:00Z', provisioned: true }));
      if (url.endsWith('/profiles')) return Promise.resolve(json({ profiles: [] }));
      if (url.endsWith('/routes')) return Promise.resolve(json({ routes: [] }));
      if (url.endsWith('/revisions')) return Promise.resolve(json({ revisions: [] }));
      if (url.endsWith('/audit')) return Promise.resolve(json({ events: [] }));
      if (url.endsWith('/fallback')) return Promise.resolve(json({ capability: 'chat', enabled: false, ordered_revision_ids: [] }));
      return Promise.resolve(json({ usage: [] }));
    }); vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AiProviderAdminPanel locale="en-US" csrfToken="csrf" />); }); await settle();
    await act(async () => { host.querySelector<HTMLButtonElement>('.provider-admin-heading button')?.click(); });
    const selects = host.querySelectorAll<HTMLSelectElement>('.provider-admin-form select');
    const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value')?.set;
    await act(async () => { setter?.call(selects[0], 'openai_compatible'); selects[0].dispatchEvent(new Event('change', { bubbles: true })); });
    expect((host.querySelector('input[type="url"]') as HTMLInputElement).value).toBe('https://api.gapgpt.app/v1');
    expect(host.textContent).toContain('This capability is not implemented by the current gateway.');
    expect(fetchMock.mock.calls.some(call => String(call[0]).endsWith('/test'))).toBe(false);
  });

  it('saves an explicit ordered Chat fallback policy through the protected API', async () => {
    const profile = { id: 'p1', name: 'Local test profile', provider_kind: 'lm_studio', base_url: 'http://127.0.0.1:1234/v1', auth_mode: 'none', enabled: true, capabilities: { chat: { model_id: 'loaded-model' } }, timeout_seconds: 10, concurrency_limit: 1, version: 2, secret_configured: false };
    const revision = { revision: 'rev-chat-1', profile_id: 'p1', profile_name: 'Local test profile', capability: 'chat', model_id: 'loaded-model', validation_status: 'valid', validated_at: '2026-11-11T00:00:00Z', active: false };
    const unavailableRevision = { ...revision, revision: 'rev-chat-pending', validation_status: 'unavailable', validated_at: null };
    let revisionLoads = 0;
    let fallbackPolicy = { capability: 'chat', enabled: false, ordered_revision_ids: [] as string[] };
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (url.endsWith('/me')) return Promise.resolve(json({ admin: true, mfa_enrolled: true, step_up_expires_at: '2099-01-01T00:00:00Z', provisioned: true }));
      if (url.endsWith('/profiles')) return Promise.resolve(json({ profiles: [profile] }));
      if (url.endsWith('/routes')) return Promise.resolve(json({ routes: [] }));
      if (url.endsWith('/revisions')) { revisionLoads += 1; return Promise.resolve(json({ revisions: [revision, unavailableRevision] })); }
      if (url.endsWith('/audit')) return Promise.resolve(json({ events: [] }));
      if (url.endsWith('/usage')) return Promise.resolve(json({ usage: [] }));
      if (url.endsWith('/test')) return Promise.resolve(json({ success: true, status: 'validated', latency_ms: 15, capability: 'chat', model_id: 'loaded-model' }));
      if (url.endsWith('/fallback') && init?.method === 'PUT') { fallbackPolicy = JSON.parse(String(init.body)); return Promise.resolve(json(fallbackPolicy)); }
      if (url.endsWith('/fallback')) return Promise.resolve(json(fallbackPolicy));
      return Promise.resolve(json({}));
    }); vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AiProviderAdminPanel locale="en-US" csrfToken="csrf" />); }); await settle();
    const testButton = [...host.querySelectorAll<HTMLButtonElement>('button')].find(button => button.textContent === 'Test connection (non-generative)')!;
    await act(async () => { testButton.click(); }); await settle();
    expect(revisionLoads).toBe(2);
    const fallbackCard = [...host.querySelectorAll<HTMLElement>('.provider-admin-card')].find(card => card.textContent?.includes('Chat fallback order'))!;
    const switches = fallbackCard.querySelectorAll<HTMLInputElement>('input[type="checkbox"]');
    expect(switches).toHaveLength(2);
    expect(host.textContent).toContain('Unavailable');
    await act(async () => { switches[0].click(); switches[1].click(); });
    const save = [...fallbackCard.querySelectorAll<HTMLButtonElement>('button')].find(button => button.textContent === 'Save')!;
    await act(async () => { save.click(); }); await settle();
    const putCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/fallback') && (call[1] as RequestInit).method === 'PUT')!;
    expect(JSON.parse(String((putCall[1] as RequestInit).body))).toEqual({ capability: 'chat', enabled: true, ordered_revision_ids: ['rev-chat-1'] });
    expect(((putCall[1] as RequestInit).headers as Record<string, string>)['X-CSRF-Token']).toBe('csrf');

    const refreshedFallbackCard = [...host.querySelectorAll<HTMLElement>('.provider-admin-card')].find(card => card.textContent?.includes('Chat fallback order'))!;
    const fallbackEnabled = refreshedFallbackCard.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
    await act(async () => { fallbackEnabled.click(); });
    const disableSave = [...refreshedFallbackCard.querySelectorAll<HTMLButtonElement>('button')].find(button => button.textContent === 'Save')!;
    await act(async () => { disableSave.click(); }); await settle();
    const putCalls = fetchMock.mock.calls.filter(call => String(call[0]).endsWith('/fallback') && (call[1] as RequestInit).method === 'PUT');
    expect(putCalls).toHaveLength(2);
    expect(JSON.parse(String((putCalls[1]![1] as RequestInit).body))).toEqual({ capability: 'chat', enabled: false, ordered_revision_ids: [] });
  });
});
