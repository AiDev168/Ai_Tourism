// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminControlCenter } from './AdminControlCenter';

let root: Root; let host: HTMLDivElement;
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
async function settle() { await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); }); }
beforeEach(() => { (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true; host = document.createElement('div'); document.body.append(host); root = createRoot(host); });
afterEach(() => { act(() => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('admin control center capability navigation', () => {
  it('shows only server-authorized sections and identifies AI administration as local-pilot-only', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => String(url).endsWith('/capabilities')
      ? Promise.resolve(response({ sections: { companies: true, destinations: false, users: false, system: false }, company_capabilities: { organization_review: true, service_review: false, offer_review: false }, catalogue_capabilities: { candidate_review: false, source_review: false, catalogue_publish: false }, ai_admin: { available: false, scope: 'local_pilot_only' }, privileged_writes_available: true }))
      : Promise.resolve(response({ companies: { organization_count: 2, awaiting_application: 1, awaiting_verification: 1 }, ai_admin: { available: false, scope: 'local_pilot_only' } }))));
    await act(async () => { root.render(<AdminControlCenter locale="en-US" csrfToken="csrf" />); }); await settle();
    expect(host.textContent).toContain('Company governance');
    expect(host.textContent).toContain('Provider administration is restricted');
    expect(host.textContent).not.toContain('Users and access');
    expect(host.querySelector('.admin-control-nav button[aria-current="page"]')?.textContent).toBe('Overview');
  });

  it('renders a clear denial instead of an owner console for a user without grants', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ error: { code: 'request_rejected' } }, 403)));
    await act(async () => { root.render(<AdminControlCenter locale="fa-IR" csrfToken="csrf" />); }); await settle();
    expect(host.textContent).toContain('این حساب دسترسی مدیریتی ندارد.');
    expect(host.querySelector('.admin-control-nav')).toBeNull();
  });

  it('keeps the company queue read-only unless the server explicitly allows step-up writes', async () => {
    const item = { case_id: 'case-3', organization_id: 'org-3', case_status: 'submitted', evidence_refs: [], legal_name: 'Example LLC', display_name: 'Example', registration_country: 'IR', application_status: 'submitted', verification_status: 'pending', participation_status: 'inactive' };
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
      if (String(url).endsWith('/capabilities')) return Promise.resolve(response({ sections: { companies: true, destinations: false, users: false, system: false }, company_capabilities: { organization_review: true, service_review: false, offer_review: false }, catalogue_capabilities: { candidate_review: false, source_review: false, catalogue_publish: false }, ai_admin: { available: false, scope: 'local_pilot_only' }, privileged_writes_available: false }));
      if (String(url).endsWith('/overview')) return Promise.resolve(response({ companies: { organization_count: 1, awaiting_application: 1, awaiting_verification: 1 } }));
      return Promise.resolve(response({ items: [item] }));
    }));
    await act(async () => { root.render(<AdminControlCenter locale="en-US" csrfToken="csrf" />); }); await settle();
    const companyNav = [...host.querySelectorAll<HTMLButtonElement>('.admin-control-nav button')].find(button => button.textContent === 'Company governance')!;
    await act(async () => { companyNav.click(); }); await settle();
    expect(host.textContent).toContain('Example');
    expect(host.textContent).toContain('Reviewer decisions are disabled');
    expect([...host.querySelectorAll('button')].some(button => button.textContent === 'Verify evidence')).toBe(false);
  });
});
