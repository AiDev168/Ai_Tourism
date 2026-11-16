import { useEffect, useState, type FormEvent } from 'react';
import { createPortal } from 'react-dom';
import type { Locale } from '../i18n/messages';
import { AuthApiError, authApi, type AuthCapabilities, type AuthSession } from './authApi';
import { authMessages } from './authMessages';
import { localOwnerMessages } from './localOwnerMessages';

type Phase = 'phone' | 'code';
type StagingMode = 'login' | 'register' | 'redeem';

const stagingCopy = {
  'fa-IR': { account: 'ورود آزمایشی', email: 'ایمیل', password: 'گذرواژه (حداقل ۸ نویسه)', invite: 'کد دعوت', redeem: 'فعال‌سازی دعوت', switchToRedeem: 'کد دعوت دارید؟ ایجاد حساب', switchToLogin: 'بازگشت به ورود', invalid: 'ورود یا کد دعوت معتبر نیست.', smsUnavailable: 'ارسال پیامک در این محیط تنظیم نشده است؛ کد ورود پیامکی ارسال نمی‌شود.' },
  'en-US': { account: 'Private pilot sign in', email: 'Email', password: 'Password (at least 8 characters)', invite: 'Invitation code', redeem: 'Activate invitation', switchToRedeem: 'Have an invitation? Create account', switchToLogin: 'Back to sign in', invalid: 'The sign-in details or invitation are invalid.', smsUnavailable: 'SMS delivery is not configured in this environment. No OTP will be sent.' },
  ar: { account: 'تسجيل دخول تجريبي خاص', email: 'البريد الإلكتروني', password: 'كلمة المرور (8 أحرف على الأقل)', invite: 'رمز الدعوة', redeem: 'تفعيل الدعوة', switchToRedeem: 'لديك دعوة؟ إنشاء حساب', switchToLogin: 'العودة إلى الدخول', invalid: 'بيانات الدخول أو الدعوة غير صالحة.', smsUnavailable: 'إرسال الرسائل النصية غير مُعدّ في هذه البيئة؛ لن يُرسل رمز تحقق.' },
} as const;

const stagingMethodCopy = {
  'fa-IR': { useOtp: '\u0648\u0631\u0648\u062f \u0628\u0627 \u067e\u06cc\u0627\u0645\u06a9', useInvite: '\u0648\u0631\u0648\u062f \u0628\u0627 \u062f\u0639\u0648\u062a' },
  'en-US': { useOtp: 'Use SMS sign-in', useInvite: 'Use invitation sign-in' },
  ar: { useOtp: '\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644 \u0628\u0631\u0633\u0627\u0644\u0629 SMS', useInvite: '\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644 \u0628\u0631\u0645\u0632 \u0627\u0644\u062f\u0639\u0648\u0629' },
} as const;

const stagingEmailCopy = {
  'fa-IR': {
    login: '\u0648\u0631\u0648\u062f \u0628\u0627 \u0627\u06cc\u0645\u06cc\u0644',
    register: '\u0627\u06cc\u062c\u0627\u062f \u062d\u0633\u0627\u0628 \u0622\u0632\u0645\u0627\u06cc\u0634\u06cc \u0628\u0627 \u0627\u06cc\u0645\u06cc\u0644',
    invite: '\u0648\u0631\u0648\u062f \u0628\u0627 \u062f\u0639\u0648\u062a',
    registerTitle: '\u0627\u06cc\u062c\u0627\u062f \u062d\u0633\u0627\u0628 \u0622\u0632\u0645\u0627\u06cc\u0634\u06cc',
    unverified: '\u0627\u06cc\u0645\u06cc\u0644 \u062a\u0623\u06cc\u06cc\u062f \u0646\u0645\u06cc\u200c\u0634\u0648\u062f\u061b \u0646\u0634\u0627\u0646\u06cc \u0627\u06cc\u0645\u06cc\u0644 \u062a\u0623\u06cc\u06cc\u062f\u0646\u0634\u062f\u0647 \u0628\u0627\u0642\u06cc \u0645\u06cc\u200c\u0645\u0627\u0646\u062f.',
    failed: '\u062d\u0633\u0627\u0628 \u0622\u0632\u0645\u0627\u06cc\u0634\u06cc \u0633\u0627\u062e\u062a\u0647 \u0646\u0634\u062f. \u0648\u0631\u0648\u062f\u06cc\u200c\u0647\u0627 \u0631\u0627 \u0628\u0631\u0631\u0633\u06cc \u06a9\u0646\u06cc\u062f \u0648 \u062f\u0648\u0628\u0627\u0631\u0647 \u0628\u06a9\u0648\u0634\u06cc\u062f.',
    close: '\u0628\u0633\u062a\u0646',
  },
  'en-US': {
    login: 'Email sign in', register: 'Create a pilot email account', invite: 'Use an invitation',
    registerTitle: 'Create a pilot account',
    unverified: 'No verification email is sent. This address remains unverified.',
    failed: 'The pilot account could not be created. Check the entries and try again.', close: 'Close',
  },
  ar: {
    login: '\u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644 \u0628\u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a',
    register: '\u0625\u0646\u0634\u0627\u0621 \u062d\u0633\u0627\u0628 \u062a\u062c\u0631\u064a\u0628\u064a \u0628\u0627\u0644\u0628\u0631\u064a\u062f',
    invite: '\u0627\u0644\u062f\u062e\u0648\u0644 \u0628\u062f\u0639\u0648\u0629',
    registerTitle: '\u0625\u0646\u0634\u0627\u0621 \u062d\u0633\u0627\u0628 \u062a\u062c\u0631\u064a\u0628\u064a',
    unverified: '\u0644\u0627 \u062a\u064f\u0631\u0633\u0644 \u0631\u0633\u0627\u0644\u0629 \u062a\u0623\u0643\u064a\u062f. \u0633\u064a\u0628\u0642\u0649 \u0627\u0644\u0628\u0631\u064a\u062f \u063a\u064a\u0631 \u0645\u0624\u0643\u062f.',
    failed: '\u062a\u0639\u0630\u0631 \u0625\u0646\u0634\u0627\u0621 \u0627\u0644\u062d\u0633\u0627\u0628. \u062a\u062d\u0642\u0642 \u0645\u0646 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u0648\u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.',
    close: '\u0625\u063a\u0644\u0627\u0642',
  },
} as const;

export function AuthPanel({ locale, onSessionChange }: { locale: Locale; onSessionChange?: (session: AuthSession | null) => void }) {
  const copy = authMessages[locale];
  const localCopy = localOwnerMessages[locale];
  const stageCopy = stagingCopy[locale];
  const methodCopy = stagingMethodCopy[locale];
  const emailCopy = stagingEmailCopy[locale];
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
  const [stagingFallback, setStagingFallback] = useState(false);
  const [stagingEmail, setStagingEmail] = useState('');
  const [stagingPassword, setStagingPassword] = useState('');
  const [inviteCode, setInviteCode] = useState('');

  useEffect(() => {
    let active = true;
    void authApi.method().then(value => {
      if (active) {
        setCapabilities(value);
        setStagingFallback(value.methods.includes('staging_invite') && value.otp_delivery !== 'available');
      }
    }).catch(() => {
      if (active) setCapabilities({ methods: [], otp_delivery: 'unavailable', staging_email_signup: false });
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

  useEffect(() => {
    if (!open || session) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', closeOnEscape);
    };
  }, [open, session]);

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
        : stagingMode === 'register'
          ? await authApi.registerStagingEmail(stagingEmail, stagingPassword)
          : await authApi.redeemStagingInvite(inviteCode, stagingEmail, stagingPassword);
      setSession(value); setCsrfToken(value.csrf_token); setStagingPassword(''); setInviteCode(''); setOpen(false);
      onSessionChange?.(value);
    } catch (errorValue) {
      setStagingPassword('');
      setError(stagingMode === 'register'
        ? emailCopy.failed
        : errorValue instanceof AuthApiError && errorValue.status === 401 ? stageCopy.invalid : copy.genericError);
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
      {open && !session && createPortal((
        <div className="auth-overlay" onMouseDown={event => { if (event.target === event.currentTarget) setOpen(false); }}>
        <section className="auth-panel" role="dialog" aria-modal="true" aria-label={copy.signIn}>
          <button type="button" className="auth-dialog-close" onClick={() => setOpen(false)} aria-label={emailCopy.close}>×</button>
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
          ) : capabilities?.methods.includes('staging_invite') && stagingFallback ? (
            <section aria-label={stageCopy.account}>
              {capabilities.otp_delivery !== 'available' && !capabilities.staging_email_signup && <p role="note">{stageCopy.smsUnavailable}</p>}
              {capabilities.otp_delivery === 'available' && <button type="button" className="auth-owner-choice" onClick={() => { setStagingFallback(false); setStagingMode('login'); setPhase('phone'); setChallengeId(''); setCode(''); setError(''); setNotice(''); }}>{methodCopy.useOtp}</button>}
              {capabilities.staging_email_signup ? <nav className="auth-mode-switch" aria-label={stageCopy.account}>
                <button type="button" aria-pressed={stagingMode === 'login'} onClick={() => { setStagingMode('login'); setError(''); setStagingPassword(''); }}>{emailCopy.login}</button>
                <button type="button" aria-pressed={stagingMode === 'register'} onClick={() => { setStagingMode('register'); setError(''); setStagingPassword(''); }}>{emailCopy.register}</button>
                <button type="button" aria-pressed={stagingMode === 'redeem'} onClick={() => { setStagingMode('redeem'); setError(''); setStagingPassword(''); }}>{emailCopy.invite}</button>
              </nav> : <button type="button" className="auth-owner-choice" onClick={() => { setStagingMode(value => value === 'login' ? 'redeem' : 'login'); setError(''); setNotice(''); setStagingPassword(''); }}>
                {stagingMode === 'login' ? stageCopy.switchToRedeem : stageCopy.switchToLogin}
              </button>}
              <form onSubmit={event => void submitStaging(event)}>
                <h2>{stagingMode === 'register' ? emailCopy.registerTitle : stagingMode === 'login' ? stageCopy.account : stageCopy.redeem}</h2>
                {stagingMode === 'register' && <p role="note">{emailCopy.unverified}</p>}
                {stagingMode === 'redeem' && <>
                  <label htmlFor="auth-stage-invite">{stageCopy.invite}</label>
                  <input id="auth-stage-invite" name="invite_code" autoComplete="one-time-code" required minLength={32} maxLength={128} value={inviteCode} onChange={event => setInviteCode(event.target.value)} />
                </>}
                <label htmlFor="auth-stage-email">{stageCopy.email}</label>
                <input id="auth-stage-email" name="email" type="email" autoComplete="email" required maxLength={254} value={stagingEmail} onChange={event => setStagingEmail(event.target.value)} />
                <label htmlFor="auth-stage-password">{stageCopy.password}</label>
                <input id="auth-stage-password" name="password" type="password" autoComplete={stagingMode === 'login' ? 'current-password' : 'new-password'} required minLength={stagingMode === 'login' ? 1 : 8} maxLength={256} value={stagingPassword} onChange={event => setStagingPassword(event.target.value)} />
                <button type="submit" disabled={busy}>{busy ? copy.loading : stagingMode === 'login' ? copy.signIn : stagingMode === 'register' ? emailCopy.registerTitle : stageCopy.redeem}</button>
              </form>
            </section>
          ) : capabilities?.methods.includes('otp') && phase === 'phone' ? (
            <section aria-label={copy.travelerSignIn}>
            <form onSubmit={event => void submitPhone(event)}>
              <h2>{copy.travelerSignIn}</h2>
              <label htmlFor="auth-phone">{copy.phone}</label>
              <input id="auth-phone" name="phone_number" type="tel" autoComplete="tel-national" inputMode="tel" required value={phone} onChange={event => setPhone(event.target.value)} aria-describedby="auth-phone-help" />
              <p id="auth-phone-help">{copy.phoneHelp}</p>
              {capabilities.otp_delivery === 'unavailable' && <p role="status">{copy.smsUnavailable}</p>}
              <button type="submit" disabled={busy || capabilities.otp_delivery !== 'available'}>{busy ? copy.loading : copy.sendCode}</button>
            </form>
            {capabilities.methods.includes('staging_invite') && capabilities.otp_delivery === 'available' && <button type="button" className="auth-owner-choice" onClick={() => { setStagingFallback(true); setStagingMode('login'); setPhase('phone'); setChallengeId(''); setCode(''); setError(''); setNotice(''); }}>{methodCopy.useInvite}</button>}
            </section>
          ) : capabilities?.methods.includes('otp') ? (
            <section aria-label={copy.travelerSignIn}>
            <form onSubmit={event => void submitCode(event)}>
              <label htmlFor="auth-code">{copy.code}</label>
              <input id="auth-code" name="code" type="text" autoComplete="one-time-code" inputMode="numeric" pattern="[0-9۰-۹٠-٩]{4,8}" required value={code} onChange={event => setCode(event.target.value)} />
              <button type="submit" disabled={busy}>{busy ? copy.loading : copy.verify}</button>
              <button className="auth-back" type="button" onClick={() => { setPhase('phone'); setCode(''); setChallengeId(''); }}>{copy.back}</button>
            </form>
            {capabilities.methods.includes('staging_invite') && capabilities.otp_delivery === 'available' && <button type="button" className="auth-owner-choice" onClick={() => { setStagingFallback(true); setStagingMode('login'); setPhase('phone'); setChallengeId(''); setCode(''); setError(''); setNotice(''); }}>{methodCopy.useInvite}</button>}
            </section>
          ) : <p role="status">{copy.requestUnavailable}</p>}
          {notice && <p role="status">{notice}</p>}
          {error && <p role="alert">{error}</p>}
        </section>
        </div>
      ), document.body)}
    </div>
  );
}
