import { useState } from 'react';
import type { Locale } from '../i18n/messages';

type Status = { available: boolean; enrolled: boolean; step_up_expires_at: string | null };
type Props = { locale: Locale; csrfToken: string; status: Status; onChanged: () => void };

const labels: Record<Locale, Record<string, string>> = {
  'fa-IR': {
    title: 'تأیید دومرحله‌ای مدیر', ready: 'برای تغییرات مدیریتی، تأیید دومرحله‌ای لازم است.', setupPending: 'برای فعال‌کردن تغییرات مدیریتی، برنامهٔ کدساز را راه‌اندازی کنید.', active: 'تأیید مدیریتی این نشست فعال است.',
    missing: 'زیرساخت تأیید دومرحله‌ای آماده نیست؛ مدیر سامانه باید کلیدهای سرور و مهاجرت را تنظیم کند.',
    enroll: 'راه‌اندازی برنامهٔ کدساز', verify: 'تأیید و فعال‌سازی', step: 'تأیید برای ۵ دقیقه', recover: 'استفاده از کد بازیابی', reset: 'بازنشانی کدساز با نشست تأییدشده',
    code: 'کد شش‌رقمی', recovery: 'کد بازیابی', saveSecret: 'این کلید را در برنامهٔ کدساز ثبت کنید. فقط در همین صفحه نمایش داده می‌شود.',
    saveRecovery: 'کدهای بازیابی را در جای امن ذخیره کنید. هر کد فقط یک‌بار قابل استفاده است.', done: 'ذخیره شد', busy: 'در حال انجام…',
    errors: 'درخواست انجام نشد. دوباره تلاش کنید یا با مدیر سامانه تماس بگیرید.', denied: 'این حساب مجوز مدیریتی ندارد.', invalid: 'کد معتبر نیست یا قبلاً استفاده شده است.', required: 'ابتدا تأیید دومرحله‌ای را فعال کنید.',
  },
  'en-US': {
    title: 'Administrator two-step verification', ready: 'Two-step verification is required for administrative changes.', setupPending: 'Set up an authenticator app to enable administrative changes.', active: 'Administrative step-up is active for this session.',
    missing: 'Two-step verification is unavailable. An operator must configure server keys and the database migration.',
    enroll: 'Set up authenticator app', verify: 'Verify and enable', step: 'Verify for 5 minutes', recover: 'Use a recovery code', reset: 'Reset authenticator from verified session',
    code: 'Six-digit code', recovery: 'Recovery code', saveSecret: 'Add this key to your authenticator app. It is shown only on this page.',
    saveRecovery: 'Store these recovery codes securely. Each code works once.', done: 'Saved', busy: 'Working…',
    errors: 'The request failed. Try again or contact the system operator.', denied: 'This account has no administrative grant.', invalid: 'The code is invalid or already used.', required: 'Enable two-step verification first.',
  },
  ar: {
    title: 'التحقق الثنائي للمسؤول', ready: 'يلزم التحقق الثنائي لإجراء التغييرات الإدارية.', setupPending: 'أعد تطبيق المصادقة لتفعيل التغييرات الإدارية.', active: 'التحقق الإداري نشط لهذه الجلسة.',
    missing: 'التحقق الثنائي غير متاح. يجب على المشغل إعداد مفاتيح الخادم وترحيل قاعدة البيانات.',
    enroll: 'إعداد تطبيق المصادقة', verify: 'تحقق وفعّل', step: 'تحقق لمدة خمس دقائق', recover: 'استخدم رمز استرداد', reset: 'إعادة إعداد المصادقة بعد التحقق',
    code: 'رمز من ستة أرقام', recovery: 'رمز الاسترداد', saveSecret: 'أضف هذا المفتاح إلى تطبيق المصادقة. يظهر في هذه الصفحة فقط.',
    saveRecovery: 'احفظ رموز الاسترداد بأمان. يمكن استخدام كل رمز مرة واحدة.', done: 'تم الحفظ', busy: 'جارٍ التنفيذ…',
    errors: 'تعذر تنفيذ الطلب. حاول مجدداً أو اتصل بمشغل النظام.', denied: 'لا يملك هذا الحساب صلاحية إدارية.', invalid: 'الرمز غير صالح أو سبق استخدامه.', required: 'فعّل التحقق الثنائي أولاً.',
  },
};

export function PlatformAdminMfaPanel({ locale, csrfToken, status, onChanged }: Props) {
  const t = labels[locale];
  const [secret, setSecret] = useState<string | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [code, setCode] = useState('');
  const [recovery, setRecovery] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  async function request(path: string, body?: unknown) {
    setBusy(true); setMessage('');
    try {
      const response = await fetch(`/api/v1/admin/mfa/${path}`, {
        method: 'POST', credentials: 'same-origin', cache: 'no-store',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      const result = await response.json().catch(() => ({})) as Record<string, unknown>;
      if (!response.ok) {
        const error = typeof result.detail === 'string' ? result.detail
          : typeof result.error === 'object' && result.error !== null && 'code' in result.error
            ? String((result.error as { code: unknown }).code) : '';
        setMessage(error === 'admin_capability_required' ? t.denied
          : error.includes('invalid') || error.includes('replayed') ? t.invalid
            : error === 'mfa_required' ? t.required : t.errors);
        return null;
      }
      return result;
    } catch {
      setMessage(t.errors); return null;
    } finally { setBusy(false); }
  }

  async function startEnrollment() {
    const result = await request('enroll');
    if (result && typeof result.secret === 'string') {
      setSecret(result.secret);
    }
  }
  async function verify(path: 'verify' | 'step-up') {
    const result = await request(path, { code });
    if (!result) return;
    setCode('');
    if (Array.isArray(result.recovery_codes)) setCodes(result.recovery_codes.map(String));
    setSecret(null); onChanged();
  }
  async function recover() {
    const result = await request('recovery', { code: recovery });
    if (result) { setRecovery(''); onChanged(); }
  }
  async function reset() {
    const result = await request('reset');
    if (result) { setCodes(null); setSecret(null); onChanged(); }
  }

  return <section className="admin-control-section admin-mfa-panel" aria-labelledby="admin-mfa-title">
    <h2 id="admin-mfa-title">{t.title}</h2>
    {!status.available ? <p role="status">{t.missing}</p> : <>
      <p role="status">{status.step_up_expires_at ? t.active : status.enrolled ? t.ready : t.setupPending}</p>
      {!status.enrolled && !secret && <button type="button" className="primary" disabled={busy} onClick={() => void startEnrollment()}>{busy ? t.busy : t.enroll}</button>}
      {secret && <div className="admin-mfa-secret" aria-live="polite"><p>{t.saveSecret}</p><code>{secret}</code>
        <label>{t.code}<input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={event => setCode(event.target.value.replace(/\D/g, ''))} /></label>
        <button type="button" className="primary" disabled={busy || code.length !== 6} onClick={() => void verify('verify')}>{busy ? t.busy : t.verify}</button>
      </div>}
      {status.enrolled && !status.step_up_expires_at && <div className="admin-mfa-actions">
        <label>{t.code}<input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={event => setCode(event.target.value.replace(/\D/g, ''))} /></label>
        <button type="button" className="primary" disabled={busy || code.length !== 6} onClick={() => void verify('step-up')}>{busy ? t.busy : t.step}</button>
        <label>{t.recovery}<input autoComplete="off" value={recovery} onChange={event => setRecovery(event.target.value)} /></label>
        <button type="button" className="secondary" disabled={busy || recovery.length < 12} onClick={() => void recover()}>{t.recover}</button>
      </div>}
      {status.enrolled && status.step_up_expires_at && <button type="button" className="secondary" disabled={busy} onClick={() => void reset()}>{t.reset}</button>}
      {codes && <div className="admin-mfa-recovery" role="alert"><p>{t.saveRecovery}</p>{codes.map(value => <code key={value}>{value}</code>)}<button type="button" className="secondary" onClick={() => setCodes(null)}>{t.done}</button></div>}
      {message && <p role="alert">{message}</p>}
    </>}
  </section>;
}
