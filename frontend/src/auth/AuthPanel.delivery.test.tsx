// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthPanel } from './AuthPanel';
import { authMessages } from './authMessages';

let root: Root;
let host: HTMLDivElement;

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

async function settle() {
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
}

beforeEach(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  host = document.createElement('div');
  document.body.append(host);
  root = createRoot(host);
});

afterEach(() => {
  act(() => root.unmount());
  host.remove();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('OTP delivery failure UX', () => {
  it('shows a generic retry state without opening code entry when no usable challenge is returned', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ error: { code: 'unauthenticated' } }, 401))
      .mockResolvedValueOnce(response({ challenge_id: null, status: 'unavailable' }, 202));
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AuthPanel locale="en-US" />); });
    await settle();
    await act(async () => { (host.querySelector('button') as HTMLButtonElement).click(); });
    const phone = host.querySelector<HTMLInputElement>('#auth-phone')!;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
    await act(async () => {
      setter?.call(phone, '09121234567');
      phone.dispatchEvent(new Event('input', { bubbles: true }));
      host.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    await settle();
    expect(host.textContent).toContain(authMessages['en-US'].requestUnavailable);
    expect(host.querySelector('#auth-code')).toBeNull();
    expect(host.textContent).not.toMatch(/rate limit|too many requests/i);
  });
});
