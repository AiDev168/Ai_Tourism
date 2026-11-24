// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CompanyReviewQueue } from './CompanyReviewQueue';

let root: Root; let host: HTMLDivElement;
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
async function settle() { await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); }); }
beforeEach(() => { (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true; host = document.createElement('div'); document.body.append(host); root = createRoot(host); });
afterEach(() => { act(() => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('shared company review queue', () => {
  it('loads the existing queue and records an audited decision through existing APIs', async () => {
    const item = { case_id: 'case-1', organization_id: 'org-1', case_status: 'submitted', evidence_refs: ['https://example.org/evidence'], legal_name: 'Example LLC', display_name: 'Example', registration_country: 'IR', application_status: 'submitted', verification_status: 'pending', participation_status: 'inactive' };
    const fetchMock = vi.fn().mockImplementation((_url: string, init?: RequestInit) => Promise.resolve(response(init?.method === 'POST' ? { status: 'verified' } : { items: [item] })));
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<CompanyReviewQueue locale="en-US" csrfToken="csrf-token" />); }); await settle();
    expect(host.textContent).toContain('Example');
    const reason = host.querySelector('textarea')!;
    await act(async () => { Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set?.call(reason, 'Evidence was inspected independently.'); reason.dispatchEvent(new Event('input', { bubbles: true })); });
    await settle();
    const verify = [...host.querySelectorAll('button')].find(button => button.textContent === 'Verify evidence')!;
    await act(async () => { verify.click(); }); await settle();
    expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/platform/verification-cases/case-1/decision') && (init as RequestInit).headers && ((init as RequestInit).headers as Record<string,string>)['X-CSRF-Token'] === 'csrf-token')).toBe(true);
  });

  it('does not show review data or controls when the server denies the grant', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail: 'partner_review_not_granted' }, 403)));
    await act(async () => { root.render(<CompanyReviewQueue locale="en-US" csrfToken="csrf" />); }); await settle();
    expect(host.querySelector('.partner-review-queue')).toBeNull();
    expect(host.querySelector('button')).toBeNull();
  });

  it('shows the queue read-only when privileged step-up is unavailable', async () => {
    const item = { case_id: 'case-2', organization_id: 'org-2', case_status: 'submitted', evidence_refs: [], legal_name: 'Private Example LLC', display_name: 'Example', registration_country: 'IR', application_status: 'submitted', verification_status: 'pending', participation_status: 'inactive' };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ items: [item] })));
    await act(async () => { root.render(<CompanyReviewQueue locale="en-US" csrfToken="csrf" allowDecisions={false} />); }); await settle();
    expect(host.textContent).toContain('Reviewer decisions are disabled');
    expect(host.textContent).toContain('Example');
    expect([...host.querySelectorAll('button')].some(button => button.textContent === 'Verify evidence')).toBe(false);
  });

  it('loads capability-protected audit history without exposing reviewer identifiers', async () => {
    const event = { display_name: 'Reviewed Company', entity_type: 'verification_case', decision: 'approve', reason: 'Evidence was reviewed independently.', policy_version: 'partner-verification-v1', occurred_at: '2026-11-24T12:00:00Z' };
    const fetchMock = vi.fn().mockImplementation((url: string) => Promise.resolve(response(String(url).includes('/review-events') ? { items: [event] } : { items: [] })));
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<CompanyReviewQueue locale="en-US" csrfToken="csrf" allowDecisions={false} />); }); await settle();
    await act(async () => { host.querySelector<HTMLButtonElement>('button[aria-expanded="false"]')!.click(); }); await settle();
    expect(host.textContent).toContain('Evidence was reviewed independently.');
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/platform/review-events?limit=50'))).toBe(true);
    expect(host.textContent).not.toContain('reviewer_user_id');
  });
});
