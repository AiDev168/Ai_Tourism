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
      .mockResolvedValueOnce(response({ methods: ['otp'], otp_delivery: 'available' }))
      .mockResolvedValueOnce(response({ error: { code: 'unauthenticated' } }, 401))
      .mockResolvedValueOnce(response({ challenge_id: null, status: 'unavailable' }, 202));
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AuthPanel locale="en-US" />); });
    await settle();
    await act(async () => { (document.querySelector('button') as HTMLButtonElement).click(); });
    const phone = document.querySelector<HTMLInputElement>('#auth-phone')!;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
    await act(async () => {
      setter?.call(phone, '09121234567');
      phone.dispatchEvent(new Event('input', { bubbles: true }));
      document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    await settle();
    expect(document.body.textContent).toContain(authMessages['en-US'].smsUnavailable);
    expect(document.querySelector('#auth-code')).toBeNull();
    expect(document.body.textContent).not.toMatch(/rate limit|too many requests/i);
  });

  it('uses invitation sign-in for staging and clearly states that SMS is unavailable', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ methods: ['otp', 'staging_invite'], otp_delivery: 'unavailable' }))
      .mockResolvedValueOnce(response({ error: { code: 'unauthenticated' } }, 401))
      .mockResolvedValueOnce(response({ user: { user_id: 'user-1', phone_e164: null,
        phone_verified: null, auth_method: 'staging_invite' }, csrf_token: 'csrf' }));
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AuthPanel locale="en-US" />); });
    await settle();
    await act(async () => { (document.querySelector('button') as HTMLButtonElement).click(); });
    expect(document.body.textContent).toContain('SMS delivery is not configured');
    const email = document.querySelector<HTMLInputElement>('#auth-stage-email')!;
    const password = document.querySelector<HTMLInputElement>('#auth-stage-password')!;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
    await act(async () => {
      setter?.call(email, 'traveler@example.test'); email.dispatchEvent(new Event('input', { bubbles: true }));
      setter?.call(password, 'a-long-staging-password'); password.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => {
      document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    await settle();
    expect(fetchMock.mock.calls[2][0]).toContain('/staging/login');
    expect(document.body.textContent).toContain('Private pilot sign in');
  });

  it('offers staging email registration in a viewport-level dialog and creates a session', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ methods: ['otp', 'staging_invite'], otp_delivery: 'unavailable', staging_email_signup: true }))
      .mockResolvedValueOnce(response({ error: { code: 'unauthenticated' } }, 401))
      .mockResolvedValueOnce(response({ user: { user_id: 'new-user', phone_e164: null,
        phone_verified: null, auth_method: 'staging_invite' }, csrf_token: 'csrf' }));
    const onSessionChange = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AuthPanel locale="en-US" onSessionChange={onSessionChange} />); });
    await settle();
    await act(async () => { (host.querySelector('.auth-entry > button') as HTMLButtonElement).click(); });
    expect(document.querySelector('[role="dialog"][aria-modal="true"]')).not.toBeNull();
    expect(document.body.textContent).not.toContain('SMS delivery is not configured');
    const register = [...document.querySelectorAll('button')].find(button => button.textContent === 'Create a pilot email account')!;
    await act(async () => { register.click(); });
    const email = document.querySelector<HTMLInputElement>('#auth-stage-email')!;
    const password = document.querySelector<HTMLInputElement>('#auth-stage-password')!;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
    await act(async () => {
      setter?.call(email, 'new@example.test'); email.dispatchEvent(new Event('input', { bubbles: true }));
      setter?.call(password, 'ژ'.repeat(8)); password.dispatchEvent(new Event('input', { bubbles: true }));
      document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    await settle();
    expect(String(fetchMock.mock.calls[2][0])).toContain('/staging/register');
    expect(JSON.parse(String(fetchMock.mock.calls[2][1]?.body))).toEqual({ email: 'new@example.test', password: 'ژ'.repeat(8) });
    expect(document.querySelector('[role="dialog"]')).toBeNull();
    expect(onSessionChange).toHaveBeenCalledWith(expect.objectContaining({ user: expect.objectContaining({ user_id: 'new-user' }) }));
  });

  it('offers invitation redemption without exposing open signup when the server flag is off', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ methods: ['otp', 'staging_invite'], otp_delivery: 'unavailable', staging_email_signup: false }))
      .mockResolvedValueOnce(response({ error: { code: 'unauthenticated' } }, 401))
      .mockResolvedValueOnce(response({ user: { user_id: 'invite-fixture', phone_e164: null,
        phone_verified: null, auth_method: 'staging_invite' }, csrf_token: 'csrf' }));
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AuthPanel locale="en-US" />); });
    await settle();
    await act(async () => { (host.querySelector('.auth-entry > button') as HTMLButtonElement).click(); });
    expect(document.body.textContent).not.toContain('Create a pilot email account');
    const invite = [...document.querySelectorAll('button')]
      .find(button => button.textContent === 'Have an invitation? Create account')!;
    await act(async () => { invite.click(); });
    const password = document.querySelector<HTMLInputElement>('#auth-stage-password')!;
    expect(password.minLength).toBe(8);
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
    await act(async () => {
      for (const [input, value] of [
        [document.querySelector('#auth-stage-email'), 'invited@example.test'],
        [document.querySelector('#auth-stage-invite'), 'a'.repeat(32)],
        [password, '🌿'.repeat(7)],
      ] as const) {
        setter?.call(input, value);
        input!.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });
    await act(async () => {
      document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(document.body.textContent).toContain('Use between 8 and 256 characters');
    await act(async () => {
      setter?.call(password, '🌿'.repeat(257));
      password.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => {
      document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    await act(async () => {
      setter?.call(password, '🌿'.repeat(256));
      password.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => {
      document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    await settle();
    expect(String(fetchMock.mock.calls[2][0])).toContain('/staging/redeem');
    expect(JSON.parse(String(fetchMock.mock.calls[2][1]?.body)).password).toBe('🌿'.repeat(256));
  });

  it('keeps OTP as primary when live SMS is available and exposes invitation fallback', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ methods: ['otp', 'staging_invite'], otp_delivery: 'available' }))
      .mockResolvedValueOnce(response({ error: { code: 'unauthenticated' } }, 401));
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AuthPanel locale="en-US" />); });
    await settle();
    await act(async () => { (document.querySelector('button') as HTMLButtonElement).click(); });
    expect(document.querySelector('#auth-phone')).not.toBeNull();
    expect(document.querySelector('#auth-stage-email')).toBeNull();
    expect(document.body.textContent).toContain('Use invitation sign-in');
    expect(document.body.textContent).not.toContain('SMS delivery is not configured');

    const buttons = [...document.querySelectorAll('button')];
    await act(async () => { buttons.find(button => button.textContent === 'Use invitation sign-in')!.click(); });
    expect(document.querySelector('#auth-stage-email')).not.toBeNull();
    expect(document.body.textContent).toContain('Use SMS sign-in');
    await act(async () => { [...document.querySelectorAll('button')].find(button => button.textContent === 'Use SMS sign-in')!.click(); });
    expect(document.querySelector('#auth-phone')).not.toBeNull();
    expect(document.querySelector('#auth-stage-email')).toBeNull();
  });
});
