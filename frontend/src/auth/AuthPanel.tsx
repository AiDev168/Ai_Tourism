import { useEffect, useState, type FormEvent } from 'react';
import type { Locale } from '../i18n/messages';
import { AuthApiError, authApi, type AuthCapabilities, type AuthSession } from './authApi';
import { authMessages } from './authMessages';
import { localOwnerMessages } from './localOwnerMessages';

type Phase = 'phone' | 'code';
type StagingMode = 'login' | 'redeem';

const stagingCopy = {
  'fa-IR': { account: 'ورود آزمایشی', email: 'ایمیل', password: 'گذرواژه (حداقل ۱۶ نویسه)', invite: 'کد دعوت', redeem: 'فعال‌سازی دعوت', switchToRedeem: 'کد دعوت دارید؟ ایجاد حساب', switchToLogin: 'بازگشت به ورود', invalid: 'ورود یا کد دعوت معتبر نیست.', smsUnavailable: 'ارسال پیامک در این محیط تنظیم نشده است؛ کد ورود پیامکی ارسال نمی‌شود.' },
  'en-US': { account: 'Private pilot sign in', email: 'Email', password: 'Password (at least 16 characters)', invite: 'Invitation code', redeem: 'Activate invitation', switchToRedeem: 'Have an invitation? Create account', switchToLogin: 'Back to sign in', invalid: 'The sign-in details or invitation are invalid.', smsUnavailable: 'SMS delivery is not configured in this environment. No OTP will be sent.' },
  ar: { account: 'تسجيل دخول تجريبي خاص', email: 'البريد الإلكتروني', password: 'كلمة المرور (16 حرفًا على الأقل)', invite: 'رمز الدعوة', redeem: 'تفعيل الدعوة', switchToRedeem: 'لديك دعوة؟ إنشاء حساب', switchToLogin: 'العودة إلى تسجيل الدخول', invalid: 'بيانات الدخول أو الدعوة غير صالحة.', smsUnavailable: 'إرسال الرسائل النصية غير مُعدّ في هذه البيئة؛ لن يُرسل رمز تحقق.' },
} as const;

export function AuthPanel({ locale, onSessionChange }: { locale: Locale; onSessionChange?: (session: AuthSession | null) => void }) {
  const copy = authMessages[locale];
  const localCopy = localOwnerMessages[locale];
  const stageCopy = stagingCopy[locale];
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
  const [capabilities, setCapabilities] = useState<AuthCapabilities | null>(null);
  const [ownerMode, setOwnerMode] = useState(false);
  const [loginName, setLoginName] = useState('');
  const [password, setPassword] = useState('');
  const [stagingMode, setStagingMode] = useState<StagingMode>('login');
  const [stagingEmail, setStagingEmail] = useState('');
  const [stagingPassword, setStagingPassword] = useState('');
  const [inviteCode, setInviteCode] = useState('');

  useEffect(() => {
    let active = true;
    void authApi.method().then(value => {
      if (active) setCapabilities(value);
    }).catch(() => {
      if (active) setCapabilities({ methods: [], otp_delivery: 'unavailable' });
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
      setError(copy.smsUnavailable);
      } else {
        setChallengeId(result.challenge_id); setPhase('code'); setNotice(copy.codeSent);
      }
    } catch (errorValue) {
      setError(errorValue instanceof AuthApiError && errorValue.status === 503 ? copy.smsUnavailable : copy.genericError);
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

  const submitStaging = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const value = stagingMode === 'login'
        ? await authApi.stagingLogin(stagingEmail, stagingPassword)
        : await authApi.redeemStagingInvite(inviteCode, stagingEmail, stagingPassword);
      setSession(value); setCsrfToken(value.csrf_token); setStagingPassword(''); setInviteCode(''); setOpen(false);
      onSessionChange?.(value);
    } catch (errorValue) {
      setStagingPassword('');
      setError(errorValue instanceof AuthApiError && errorValue.status === 401 ? stageCopy.invalid : copy.genericError);
    } finally { setBusy(false); }
  };

  const signOut = async () => {
    setBusy(true); setError('');
    try {
      await authApi.logout(csrfToken);
      setSession(null); setCsrfToken(''); setPhase('phone'); setChallengeId(''); setCode(''); setOwnerMode(false);
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
      setSession(null); setCsrfToken(''); setPhase('phone'); setChallengeId(''); setCode(''); setOwnerMode(false);
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
          <span dir={session.user.phone_e164 ? 'ltr' : 'auto'}>{session.user.phone_e164 ?? (session.user.auth_method === 'staging_invite' ? stageCopy.account : localCopy.ownerAccount)}</span>
          <button type="button" onClick={() => void signOut()} disabled={busy}>{busy ? copy.loading : copy.signOut}</button>
          <button type="button" onClick={() => void deleteAccount()} disabled={busy}>{copy.deleteAccount}</button>
        </div>
      ) : <button type="button" aria-expanded={open} disabled={capabilities === null || capabilities.methods.length === 0}
        onClick={() => setOpen(value => !value)}>{open ? copy.close : copy.signIn}</button>}
      {open && !session && (
        <section className="auth-panel" aria-label={copy.signIn}>
          {capabilities?.methods.includes('local_owner') && (
            <button type="button" className="auth-owner-choice" aria-pressed={ownerMode}
              onClick={() => { setOwnerMode(value => !value); setError(''); setNotice(''); }}>
              {ownerMode ? localCopy.backToTraveler : localCopy.ownerChoice}
            </button>
          )}
          {ownerMode && capabilities?.methods.includes('local_owner') ? (
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
          ) : capabilities?.methods.includes('staging_invite') ? (
            <section aria-label={stageCopy.account}>
              <p role="note">{stageCopy.smsUnavailable}</p>
              <button type="button" className="auth-owner-choice" onClick={() => { setStagingMode(value => value === 'login' ? 'redeem' : 'login'); setError(''); setNotice(''); setStagingPassword(''); }}>
                {stagingMode === 'login' ? stageCopy.switchToRedeem : stageCopy.switchToLogin}
              </button>
              <form onSubmit={event => void submitStaging(event)}>
                <h2>{stagingMode === 'login' ? stageCopy.account : stageCopy.redeem}</h2>
                {stagingMode === 'redeem' && <>
                  <label htmlFor="auth-stage-invite">{stageCopy.invite}</label>
                  <input id="auth-stage-invite" name="invite_code" autoComplete="one-time-code" required minLength={32} maxLength={128} value={inviteCode} onChange={event => setInviteCode(event.target.value)} />
                </>}
                <label htmlFor="auth-stage-email">{stageCopy.email}</label>
                <input id="auth-stage-email" name="email" type="email" autoComplete="email" required maxLength={254} value={stagingEmail} onChange={event => setStagingEmail(event.target.value)} />
                <label htmlFor="auth-stage-password">{stageCopy.password}</label>
                <input id="auth-stage-password" name="password" type="password" autoComplete={stagingMode === 'login' ? 'current-password' : 'new-password'} required minLength={stagingMode === 'login' ? 1 : 16} maxLength={256} value={stagingPassword} onChange={event => setStagingPassword(event.target.value)} />
                <button type="submit" disabled={busy}>{busy ? copy.loading : stagingMode === 'login' ? copy.signIn : stageCopy.redeem}</button>
              </form>
            </section>
          ) : capabilities?.methods.includes('otp') && phase === 'phone' ? (
            <form onSubmit={event => void submitPhone(event)}>
              <h2>{copy.travelerSignIn}</h2>
              <label htmlFor="auth-phone">{copy.phone}</label>
              <input id="auth-phone" name="phone_number" type="tel" autoComplete="tel-national" inputMode="tel" required value={phone} onChange={event => setPhone(event.target.value)} aria-describedby="auth-phone-help" />
              <p id="auth-phone-help">{copy.phoneHelp}</p>
              {capabilities.otp_delivery === 'unavailable' && <p role="status">{copy.smsUnavailable}</p>}
              <button type="submit" disabled={busy || capabilities.otp_delivery !== 'available'}>{busy ? copy.loading : copy.sendCode}</button>
            </form>
          ) : capabilities?.methods.includes('otp') ? (
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
