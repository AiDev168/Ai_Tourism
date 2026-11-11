import { useEffect, useState, type FormEvent } from 'react';
import type { Locale } from '../i18n/messages';
import { AuthApiError, authApi, type AuthSession } from './authApi';
import { authMessages } from './authMessages';
import { localOwnerMessages } from './localOwnerMessages';

type Phase = 'phone' | 'code';

export function AuthPanel({ locale, onSessionChange }: { locale: Locale; onSessionChange?: (session: AuthSession | null) => void }) {
  const copy = authMessages[locale];
  const localCopy = localOwnerMessages[locale];
  const [session, setSession] = useState<AuthSession | null>(null);
  const [csrfToken, setCsrfToken] = useState('');
  const [phase, setPhase] = useState<Phase>('phone');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [challengeId, setChallengeId] = useState('');
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [method, setMethod] = useState<'disabled' | 'otp' | 'local_owner' | null>(null);
  const [loginName, setLoginName] = useState('');
  const [password, setPassword] = useState('');

  useEffect(() => {
    let active = true;
    void authApi.method().then(value => {
      if (active) setMethod(value.method);
    }).catch(() => {
      if (active) setMethod('disabled');
    });
    void authApi.me().then(value => {
      if (!active) return;
      setSession(value);
      setCsrfToken(value.csrf_token);
      onSessionChange?.(value);
    }).catch(errorValue => {
      if (active && errorValue instanceof AuthApiError && errorValue.status === 401) onSessionChange?.(null);
      if (active && !(errorValue instanceof AuthApiError && errorValue.status === 401)) {
        // Public browsing remains available if authentication is disabled/offline.
      }
    });
    return () => { active = false; };
  }, []);

  const submitPhone = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError(''); setNotice('');
    try {
      const result = await authApi.requestCode(phone, locale);
      if (!result.challenge_id) {
        setError(copy.requestUnavailable);
      } else {
        setChallengeId(result.challenge_id); setPhase('code'); setNotice(copy.codeSent);
      }
    } catch {
      setError(copy.genericError);
    } finally { setBusy(false); }
  };

  const submitCode = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const value = await authApi.verify(challengeId, code);
      setSession(value); setCsrfToken(value.csrf_token); setCode(''); setOpen(false);
      onSessionChange?.(value);
    } catch (errorValue) {
      setError(errorValue instanceof AuthApiError && errorValue.status === 401 ? copy.invalidCode : copy.genericError);
    } finally { setBusy(false); }
  };

  const submitLocalOwner = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const value = await authApi.loginLocalOwner(loginName, password);
      setSession(value); setCsrfToken(value.csrf_token); setPassword(''); setOpen(false);
      onSessionChange?.(value);
    } catch (errorValue) {
      setPassword('');
      setError(errorValue instanceof AuthApiError && errorValue.status === 401 ? localCopy.invalidCredentials : copy.genericError);
    } finally { setBusy(false); }
  };

  const signOut = async () => {
    setBusy(true); setError('');
    try {
      await authApi.logout(csrfToken);
      setSession(null); setCsrfToken(''); setPhase('phone'); setChallengeId(''); setCode('');
      onSessionChange?.(null);
    } catch (errorValue) {
      if (errorValue instanceof AuthApiError && errorValue.status === 401) {
        setSession(null); setCsrfToken(''); onSessionChange?.(null);
      } else setError(copy.genericError);
    } finally { setBusy(false); }
  };

  const deleteAccount = async () => {
    if (!window.confirm(copy.confirmDeleteAccount)) return;
    setBusy(true); setError('');
    try {
      await authApi.deleteAccount(csrfToken);
      setSession(null); setCsrfToken(''); setPhase('phone'); setChallengeId(''); setCode('');
      onSessionChange?.(null);
    } catch (errorValue) {
      if (errorValue instanceof AuthApiError && errorValue.status === 401) {
        setSession(null); setCsrfToken(''); onSessionChange?.(null);
      } else setError(copy.genericError);
    } finally { setBusy(false); }
  };

  return (
    <div className="auth-entry">
      {session ? (
        <div className="auth-signed-in" aria-live="polite">
          <span dir={session.user.phone_e164 ? 'ltr' : 'auto'}>{session.user.phone_e164 ?? localCopy.ownerAccount}</span>
          <button type="button" onClick={() => void signOut()} disabled={busy}>{busy ? copy.loading : copy.signOut}</button>
          <button type="button" onClick={() => void deleteAccount()} disabled={busy}>{copy.deleteAccount}</button>
        </div>
      ) : <button type="button" aria-expanded={open} disabled={method === null}
        onClick={() => setOpen(value => !value)}>{open ? copy.close : copy.signIn}</button>}
      {open && !session && (
        <section className="auth-panel" aria-label={copy.signIn}>
          {method === 'local_owner' ? (
            <form onSubmit={event => void submitLocalOwner(event)}>
              <h2>{localCopy.title}</h2>
              <label htmlFor="auth-local-login">{localCopy.loginName}</label>
              <input id="auth-local-login" name="username" autoComplete="username" required
                minLength={3} maxLength={40} value={loginName} onChange={event => setLoginName(event.target.value)} />
              <label htmlFor="auth-local-password">{localCopy.password}</label>
              <input id="auth-local-password" name="password" type="password" autoComplete="current-password"
                required minLength={1} maxLength={256} value={password} onChange={event => setPassword(event.target.value)} />
              <button type="submit" disabled={busy}>{busy ? copy.loading : copy.signIn}</button>
            </form>
          ) : method === 'otp' && phase === 'phone' ? (
            <form onSubmit={event => void submitPhone(event)}>
              <label htmlFor="auth-phone">{copy.phone}</label>
              <input id="auth-phone" name="phone_number" type="tel" autoComplete="tel-national" inputMode="tel" required value={phone} onChange={event => setPhone(event.target.value)} aria-describedby="auth-phone-help" />
              <p id="auth-phone-help">{copy.phoneHelp}</p>
              <button type="submit" disabled={busy}>{busy ? copy.loading : copy.sendCode}</button>
            </form>
          ) : method === 'otp' ? (
            <form onSubmit={event => void submitCode(event)}>
              <label htmlFor="auth-code">{copy.code}</label>
              <input id="auth-code" name="code" type="text" autoComplete="one-time-code" inputMode="numeric" pattern="[0-9۰-۹٠-٩]{4,8}" required value={code} onChange={event => setCode(event.target.value)} />
              <button type="submit" disabled={busy}>{busy ? copy.loading : copy.verify}</button>
              <button className="auth-back" type="button" onClick={() => { setPhase('phone'); setCode(''); setChallengeId(''); }}>{copy.back}</button>
            </form>
          ) : <p role="status">{copy.requestUnavailable}</p>}
          {notice && <p role="status">{notice}</p>}
          {error && <p role="alert">{error}</p>}
        </section>
      )}
    </div>
  );
}
