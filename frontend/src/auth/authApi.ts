export type AuthUser = { user_id: string; phone_e164: string; phone_verified: true };
export type AuthSession = { user: AuthUser; csrf_token: string };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1/auth${path}`, {
    ...init,
    credentials: 'same-origin',
    headers: { ...(init?.body ? { 'Content-Type': 'application/json' } : {}), ...init?.headers },
  });
  if (response.status === 401) throw new AuthApiError('unauthenticated', 401);
  if (!response.ok) throw new AuthApiError('unavailable', response.status);
  if (response.status === 204) return undefined as T;
  return await response.json() as T;
}

export class AuthApiError extends Error {
  constructor(readonly kind: 'unauthenticated' | 'unavailable', readonly status: number) {
    super(kind);
  }
}

export const authApi = {
  me: () => request<AuthSession>('/me'),
  requestCode: (phone_number: string, locale: string) => request<{ challenge_id: string | null; status: string }>(
    '/otp/challenges', { method: 'POST', body: JSON.stringify({ phone_number, locale }) },
  ),
  verify: (challenge_id: string, code: string) => request<AuthSession>(
    '/otp/verify', { method: 'POST', body: JSON.stringify({ challenge_id, code }) },
  ),
  logout: (csrfToken: string) => request<void>('/logout', {
    method: 'POST', headers: { 'X-CSRF-Token': csrfToken },
  }),
};
