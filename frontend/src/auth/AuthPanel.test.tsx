// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthPanel } from './AuthPanel';

const user = { user_id: 'u-1', phone_e164: '+989121234567', phone_verified: true as const, auth_method: 'otp' as const };
const session = { user, csrf_token: 'csrf-memory-only' };
let root: Root;
let host: HTMLDivElement;

function response(body: unknown, status = 200) {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status, headers: { 'Content-Type': 'application/json' },
  });
}

async function settle() {
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
}

function setInput(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
  setter?.call(input, value);
  input.dispatchEvent(new Event('input', { bubbles: true }));
}

beforeEach(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  host = document.createElement('div'); document.body.append(host); root = createRoot(host);
});

afterEach(() => { act(() => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('localized OTP panel', () => {
  it('requests a code, verifies it, restores session, and logs out with in-memory CSRF', async () => {
    const storageWrite = vi.fn();
    vi.stubGlobal('localStorage', { setItem: storageWrite });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ methods: ['otp'], otp_delivery: 'available' }))
      .mockResolvedValueOnce(response({ error: { code: 'unauthenticated' } }, 401))
      .mockResolvedValueOnce(response({ challenge_id: 'challenge-1', status: 'accepted' }, 202))
      .mockResolvedValueOnce(response(session))
      .mockResolvedValueOnce(response(undefined, 204));
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AuthPanel locale="fa-IR" />); }); await settle();
    await act(async () => { (host.querySelector('button') as HTMLButtonElement).click(); });
    const phone = host.querySelector<HTMLInputElement>('#auth-phone')!;
    await act(async () => {
      setInput(phone, '۰۹۱۲۱۲۳۴۵۶۷');
      host.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    }); await settle();
    expect(host.textContent).toContain('کد پیامک‌شده');
    const code = host.querySelector<HTMLInputElement>('#auth-code')!;
    await act(async () => {
      setInput(code, '123456');
      host.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    }); await settle();
    expect(host.textContent).toContain('+989121234567');
    const verifyCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/otp/verify'))!;
    expect(JSON.parse(String(verifyCall[1]?.body))).toEqual({ challenge_id: 'challenge-1', code: '123456' });
    const logoutButton = [...host.querySelectorAll('button')].find(button => button.textContent === 'خروج')!;
    await act(async () => { logoutButton.click(); }); await settle();
    const logoutCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/logout'))!;
    expect((logoutCall[1]?.headers as Record<string, string>)['X-CSRF-Token']).toBe('csrf-memory-only');
    expect(storageWrite).not.toHaveBeenCalled();
  });

  it('restores an existing cookie session', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ methods: ['otp'], otp_delivery: 'available' }))
      .mockResolvedValueOnce(response(session));
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AuthPanel locale="ar" />); }); await settle();
    expect(host.textContent).toContain('+989121234567');
  });

  it('renders a localized invalid or expired OTP error', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ methods: ['otp'], otp_delivery: 'available' }))
      .mockResolvedValueOnce(response({ error: { code: 'unauthenticated' } }, 401))
      .mockResolvedValueOnce(response({ challenge_id: 'c-1', status: 'accepted' }, 202))
      .mockResolvedValueOnce(response({ error: { code: 'invalid_or_expired_code' } }, 401));
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AuthPanel locale="ar" />); }); await settle();
    await act(async () => { (host.querySelector('button') as HTMLButtonElement).click(); });
    const phone = host.querySelector<HTMLInputElement>('#auth-phone')!;
    await act(async () => {
      setInput(phone, '09121234567');
      host.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    }); await settle();
    const code = host.querySelector<HTMLInputElement>('#auth-code')!;
    await act(async () => {
      setInput(code, '000000');
      host.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    }); await settle();
    expect(host.textContent).toContain('الرمز غير صحيح أو انتهت صلاحيته.');
  });

  it('uses local owner login without persisting the password and clears it after success', async () => {
    const localSession = { user: { user_id: 'owner-1', phone_e164: null, phone_verified: null, auth_method: 'local_owner' }, csrf_token: 'csrf-local' };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ methods: ['otp', 'local_owner'], otp_delivery: 'unavailable' }))
      .mockResolvedValueOnce(response({ error: { code: 'unauthenticated' } }, 401))
      .mockResolvedValueOnce(response(localSession));
    const storageWrite = vi.fn();
    vi.stubGlobal('localStorage', { setItem: storageWrite });
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AuthPanel locale="en-US" />); }); await settle();
    await act(async () => { (host.querySelector('button') as HTMLButtonElement).click(); });
    expect(host.querySelector('#auth-phone')).not.toBeNull();
    const ownerChoice = [...host.querySelectorAll('button')].find(button => button.textContent === 'Local owner sign in')!;
    await act(async () => { ownerChoice.click(); });
    const login = host.querySelector<HTMLInputElement>('#auth-local-login')!;
    const password = host.querySelector<HTMLInputElement>('#auth-local-password')!;
    await act(async () => {
      setInput(login, 'owner'); setInput(password, 'test-only strong password 123!');
      host.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    }); await settle();
    expect(host.textContent).toContain('Local owner account');
    expect(host.querySelector('#auth-local-password')).toBeNull();
    const loginCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/local-owner/login'))!;
    expect(JSON.parse(String(loginCall[1]?.body))).toEqual({ login_name: 'owner', password: 'test-only strong password 123!' });
    expect(storageWrite).not.toHaveBeenCalled();
  });

  it('keeps traveler OTP visible but unavailable without SMS delivery, without requesting or fabricating a code', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ methods: ['otp', 'local_owner'], otp_delivery: 'unavailable' }))
      .mockResolvedValueOnce(response({ error: { code: 'unauthenticated' } }, 401));
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => { root.render(<AuthPanel locale="en-US" />); }); await settle();
    await act(async () => { (host.querySelector('button') as HTMLButtonElement).click(); });
    expect(host.querySelector('#auth-phone')).not.toBeNull();
    expect(host.textContent).toContain('SMS delivery is unavailable');
    expect(host.querySelector<HTMLButtonElement>('button[type="submit"]')?.disabled).toBe(true);
    expect(host.querySelector('#auth-code')).toBeNull();
    expect(fetchMock.mock.calls.some(call => String(call[0]).endsWith('/otp/challenges'))).toBe(false);
  });
});
