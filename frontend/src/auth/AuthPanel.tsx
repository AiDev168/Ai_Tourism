import { useEffect, useState, type FormEvent } from 'react';
import type { Locale } from '../i18n/messages';
import { AuthApiError, authApi, type AuthSession } from './authApi';
import { authMessages } from './authMessages';

type Phase = 'phone' | 'code';

export function AuthPanel({ locale }: { locale: Locale }) {
  const copy = authMessages[locale];
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

  useEffect(() => {
    let active = true;
    void authApi.me().then(value => {
      if (!active) return;
      setSession(value);
      setCsrfToken(value.csrf_token);
    }).catch(errorValue => {
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
        setError(copy.rateLimited);
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
    } catch (errorValue) {
      setError(errorValue instanceof AuthApiError && errorValue.status === 401 ? copy.invalidCode : copy.genericError);
    } finally { setBusy(false); }
  };

  const signOut = async () => {
    setBusy(true); setError('');
    try {
      await authApi.logout(csrfToken);
      setSession(null); setCsrfToken(''); setPhase('phone'); setChallengeId(''); setCode('');
    } catch (errorValue) {
      if (errorValue instanceof AuthApiError && errorValue.status === 401) {
        setSession(null); setCsrfToken('');
      } else setError(copy.genericError);
    } finally { setBusy(false); }
  };

  return (
    <div className="auth-entry">
      {session ? (
        <div className="auth-signed-in" aria-live="polite">
          <span dir="ltr">{session.user.phone_e164}</span>
          <button type="button" onClick={() => void signOut()} disabled={busy}>{busy ? copy.loading : copy.signOut}</button>
        </div>
      ) : <button type="button" aria-expanded={open} onClick={() => setOpen(value => !value)}>{open ? copy.close : copy.signIn}</button>}
      {open && !session && (
        <section className="auth-panel" aria-label={copy.signIn}>
          {phase === 'phone' ? (
            <form onSubmit={event => void submitPhone(event)}>
              <label htmlFor="auth-phone">{copy.phone}</label>
              <input id="auth-phone" name="phone_number" type="tel" autoComplete="tel-national" inputMode="tel" required value={phone} onChange={event => setPhone(event.target.value)} aria-describedby="auth-phone-help" />
              <p id="auth-phone-help">{copy.phoneHelp}</p>
              <button type="submit" disabled={busy}>{busy ? copy.loading : copy.sendCode}</button>
            </form>
          ) : (
            <form onSubmit={event => void submitCode(event)}>
              <label htmlFor="auth-code">{copy.code}</label>
              <input id="auth-code" name="code" type="text" autoComplete="one-time-code" inputMode="numeric" pattern="[0-9۰-۹٠-٩]{4,8}" required value={code} onChange={event => setCode(event.target.value)} />
              <button type="submit" disabled={busy}>{busy ? copy.loading : copy.verify}</button>
              <button className="auth-back" type="button" onClick={() => { setPhase('phone'); setCode(''); setChallengeId(''); }}>{copy.back}</button>
            </form>
          )}
          {notice && <p role="status">{notice}</p>}
          {error && <p role="alert">{error}</p>}
        </section>
      )}
    </div>
  );
}
