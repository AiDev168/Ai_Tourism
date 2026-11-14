export type AuthUser = {
  user_id: string;
  phone_e164: string | null;
  phone_verified: boolean | null;
  auth_method?: 'otp' | 'local_owner' | 'staging_invite';
};
export type AuthSession = { user: AuthUser; csrf_token: string };
export type AuthCapabilities = {
  methods: Array<'otp' | 'local_owner' | 'staging_invite'>;
  otp_delivery: 'available' | 'unavailable';
};

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
  method: () => request<AuthCapabilities>('/method'),
  me: () => request<AuthSession>('/me'),
  loginLocalOwner: (login_name: string, password: string) => request<AuthSession>(
    '/local-owner/login', { method: 'POST', body: JSON.stringify({ login_name, password }) },
  ),
  stagingLogin: (email: string, password: string) => request<AuthSession>(
    '/staging/login', { method: 'POST', body: JSON.stringify({ email, password }) },
  ),
  redeemStagingInvite: (invite_code: string, email: string, password: string) => request<AuthSession>(
    '/staging/redeem', { method: 'POST', body: JSON.stringify({ invite_code, email, password }) },
  ),
  requestCode: (phone_number: string, locale: string) => request<{
    challenge_id: string | null; status: 'accepted' | 'unavailable'; message: string;
  }>(
    '/otp/challenges', { method: 'POST', body: JSON.stringify({ phone_number, locale }) },
  ),
  verify: (challenge_id: string, code: string) => request<AuthSession>(
    '/otp/verify', { method: 'POST', body: JSON.stringify({ challenge_id, code }) },
  ),
  logout: (csrfToken: string) => request<void>('/logout', {
    method: 'POST', headers: { 'X-CSRF-Token': csrfToken },
  }),
  deleteAccount: (csrfToken: string) => request<void>('/me', {
    method: 'DELETE', headers: { 'X-CSRF-Token': csrfToken },
  }),
};
