import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import type { Locale } from '../../i18n/messages';
import {
  providerAdminApi, ProviderAdminApiError, type ActiveRoute, type AdminAuditEvent, type AdminMe,
  type AdminUsage, type ConnectionTest, type ModelDiscovery, type ProviderCapability, type ProviderProfile,
  type ProviderRevision, type FallbackPolicy,
} from './api';
import './aiProviderAdmin.css';

const capabilities: ProviderCapability[] = ['chat', 'vision', 'embedding', 'reranking'];
const supportedCapabilities = new Set<ProviderCapability>(['chat']);
const words = {
  'fa-IR': { title: 'مدیریت ارائه‌دهندگان هوش مصنوعی', intro: 'تنظیمات این بخش فقط برای مدیر مجاز است و در مسیرهای مسافر نمایش داده نمی‌شود.', loading: 'در حال دریافت…', forbidden: 'این حساب مجوز مدیریت ارائه‌دهندگان را ندارد.', failed: 'ارتباط با پنل مدیریت برقرار نشد.', stepUp: 'برای عملیات حساس، کد یک‌بارمصرف برنامه احراز هویت را وارد کنید.', code: 'کد تأیید', verify: 'تأیید و ادامه', enroll: 'راه‌اندازی احراز هویت دومرحله‌ای', confirmEnroll: 'ثبت کد و فعال‌سازی', noProfiles: 'هنوز نمایه‌ای ثبت نشده است.', profiles: 'نمایه‌ها', add: 'افزودن نمایه', edit: 'ویرایش', name: 'نام نمایه', kind: 'نوع اتصال', local: 'LM Studio محلی', compatible: 'GapGPT', endpoint: 'نشانی پایه API', auth: 'شیوه احراز هویت', none: 'بدون کلید', bearer: 'Bearer', secret: 'کلید API (فقط یک‌بار وارد می‌شود)', keyConfigured: 'کلید در خزانه سرور ثبت شده است', timeout: 'مهلت (ثانیه)', concurrency: 'درخواست هم‌زمان', enabled: 'فعال', caps: 'قابلیت‌ها و مدل‌ها', model: 'شناسه مدل', maxTokens: 'حداکثر توکن', save: 'ذخیره', cancel: 'لغو', discover: 'یافتن مدل‌ها', test: 'آزمون اتصال بدون تولید متن', activate: 'فعال‌سازی', deactivate: 'غیرفعال‌سازی', archive: 'بایگانی', activeRoutes: 'مسیرهای فعال', revisions: 'نسخه‌های تأییدشده', rollback: 'بازگشت به نسخه', audit: 'رویدادهای ممیزی', usage: 'مصرف و زمان پاسخ', fallback: 'مسیر جایگزین به‌صورت پیش‌فرض خاموش است.', unsupported: 'پشتیبانی‌نشده', inactive: 'غیرفعال', noRoute: 'مسیر فعالی تنظیم نشده است.', success: 'عملیات با موفقیت انجام شد.', recovery: 'کدهای بازیابی را اکنون نگه دارید؛ دوباره نمایش داده نمی‌شوند.', closeRecovery: 'متوجه شدم', lmOffline: 'سرور محلی در دسترس نیست یا مدلی بارگذاری نشده است.', status: 'وضعیت', latency: 'زمان پاسخ', revision: 'نسخه', profile: 'نمایه', selectProfile: 'انتخاب نمایه', errorCode: 'خطا', back: 'بازگشت', selectModel: 'مدل را انتخاب کنید', emptyModels: 'مدلی پیدا نشد.', }
  , 'en-US': { title: 'AI provider administration', intro: 'Restricted to authorized administrators. Provider settings are never shown in traveler routes.', loading: 'Loading…', forbidden: 'This account is not authorized to manage providers.', failed: 'The administration service could not be reached.', stepUp: 'Enter your authenticator code for sensitive operations.', code: 'Verification code', verify: 'Verify and continue', enroll: 'Set up two-factor authentication', confirmEnroll: 'Verify and enable', noProfiles: 'No profiles have been added.', profiles: 'Profiles', add: 'Add profile', edit: 'Edit', name: 'Profile name', kind: 'Connection type', local: 'Local LM Studio', compatible: 'GapGPT', endpoint: 'API base URL', auth: 'Authentication', none: 'No key', bearer: 'Bearer', secret: 'API key (entered once)', keyConfigured: 'A key is stored in the server vault', timeout: 'Timeout (seconds)', concurrency: 'Concurrent requests', enabled: 'Enabled', caps: 'Capabilities and models', model: 'Model ID', maxTokens: 'Maximum tokens', save: 'Save', cancel: 'Cancel', discover: 'Discover models', test: 'Test connection (non-generative)', activate: 'Activate', deactivate: 'Deactivate', archive: 'Archive', activeRoutes: 'Active routes', revisions: 'Validated revisions', rollback: 'Roll back to revision', audit: 'Audit events', usage: 'Usage and latency', fallback: 'Fallback is off by default.', unsupported: 'Unsupported', inactive: 'Inactive', noRoute: 'No active route is configured.', success: 'Operation completed.', recovery: 'Save these recovery codes now. They will not be shown again.', closeRecovery: 'Done', lmOffline: 'The local server is unavailable or no model is loaded.', status: 'Status', latency: 'Latency', revision: 'Revision', profile: 'Profile', selectProfile: 'Choose a profile', errorCode: 'Error', back: 'Back', selectModel: 'Select a model', emptyModels: 'No models were found.' }
  , ar: { title: 'إدارة مزوّدي الذكاء الاصطناعي', intro: 'هذه الصفحة للمدير المخوّل فقط، ولا تعرض إعدادات المزوّد للمسافرين.', loading: 'جارٍ التحميل…', forbidden: 'هذا الحساب غير مخوّل لإدارة المزوّدين.', failed: 'تعذّر الوصول إلى خدمة الإدارة.', stepUp: 'أدخل رمز تطبيق المصادقة للعمليات الحساسة.', code: 'رمز التحقق', verify: 'تحقق وتابع', enroll: 'إعداد المصادقة الثنائية', confirmEnroll: 'تحقق وفعّل', noProfiles: 'لا توجد ملفات إعداد بعد.', profiles: 'الملفات', add: 'إضافة ملف', edit: 'تعديل', name: 'اسم الملف', kind: 'نوع الاتصال', local: 'LM Studio محلي', compatible: 'GapGPT', endpoint: 'عنوان API الأساسي', auth: 'المصادقة', none: 'بلا مفتاح', bearer: 'Bearer', secret: 'مفتاح API (يدخل مرة واحدة)', keyConfigured: 'المفتاح محفوظ في خزنة الخادم', timeout: 'المهلة (ثانية)', concurrency: 'الطلبات المتزامنة', enabled: 'مفعّل', caps: 'القدرات والنماذج', model: 'معرّف النموذج', maxTokens: 'الحد الأقصى للرموز', save: 'حفظ', cancel: 'إلغاء', discover: 'اكتشاف النماذج', test: 'اختبار الاتصال دون توليد', activate: 'تفعيل', deactivate: 'إلغاء التفعيل', archive: 'أرشفة', activeRoutes: 'المسارات النشطة', revisions: 'المراجعات المعتمدة', rollback: 'استعادة المراجعة', audit: 'أحداث التدقيق', usage: 'الاستخدام والكمون', fallback: 'التحويل الاحتياطي متوقف افتراضياً.', unsupported: 'غير مدعوم', inactive: 'غير نشط', noRoute: 'لا يوجد مسار نشط.', success: 'اكتملت العملية.', recovery: 'احفظ رموز الاسترداد الآن؛ لن تظهر مرة أخرى.', closeRecovery: 'تم', lmOffline: 'الخادم المحلي غير متاح أو لم يتم تحميل نموذج.', status: 'الحالة', latency: 'الكمون', revision: 'المراجعة', profile: 'الملف', selectProfile: 'اختر ملفاً', back: 'رجوع', selectModel: 'اختر نموذجاً', emptyModels: 'لم يتم العثور على نماذج.' }
} as const;

const supplementalWords: Record<Locale, { useRecovery: string; recoveryCode: string; unsupportedCapability: string; fallbackOrder: string; fallbackEnable: string; fallbackOn: string; fallbackOff: string; revisionPending: string; revisionValid: string; revisionInvalid: string; revisionUnavailable: string }> = {
  'fa-IR': { useRecovery: 'استفاده از کد بازیابی', recoveryCode: 'کد بازیابی یک‌بارمصرف', unsupportedCapability: 'این قابلیت در درگاه فعلی پشتیبانی نمی‌شود.', fallbackOrder: 'ترتیب مسیرهای جایگزین چت (حداکثر ۳ نسخه تأییدشده)', fallbackEnable: 'فعال‌کردن مسیر جایگزین چت؛ انتقال داده فقط پس از انتخاب صریح مدیر', fallbackOn: 'جایگزین چت فعال است', fallbackOff: 'جایگزین چت خاموش است', revisionPending: 'در انتظار اعتبارسنجی', revisionValid: 'اعتبارسنجی‌شده', revisionInvalid: 'نامعتبر', revisionUnavailable: 'آزمون نامتاح' },
  'en-US': { useRecovery: 'Use a recovery code', recoveryCode: 'One-time recovery code', unsupportedCapability: 'This capability is not implemented by the current gateway.', fallbackOrder: 'Chat fallback order (up to 3 validated revisions)', fallbackEnable: 'Enable Chat fallback; data transfer occurs only after explicit administrator configuration', fallbackOn: 'Chat fallback is enabled', fallbackOff: 'Chat fallback is disabled', revisionPending: 'Pending validation', revisionValid: 'Validated', revisionInvalid: 'Invalid', revisionUnavailable: 'Unavailable' },
  ar: { useRecovery: 'استخدم رمز استرداد', recoveryCode: 'رمز استرداد يُستخدم مرة واحدة', unsupportedCapability: 'هذه القدرة غير مدعومة في البوابة الحالية.', fallbackOrder: 'ترتيب البدائل للمحادثة (حتى ٣ مراجعات معتمدة)', fallbackEnable: 'تفعيل البديل للمحادثة؛ لا يتم التحويل إلا بإعداد صريح من المدير', fallbackOn: 'البديل للمحادثة مفعّل', fallbackOff: 'البديل للمحادثة متوقف', revisionPending: 'بانتظار التحقق', revisionValid: 'تم التحقق', revisionInvalid: 'غير صالح', revisionUnavailable: 'غير متاح' },
};

type Props = { locale: Locale; csrfToken: string; authMethod?: 'otp' | 'local_owner'; onRequireLocalOwnerLogin?: () => void };
type PanelState = { profiles: ProviderProfile[]; routes: ActiveRoute[]; revisions: ProviderRevision[]; audit: AdminAuditEvent[]; usage: AdminUsage[]; fallback: FallbackPolicy };
type FormState = { id?: string; version?: number; name: string; provider_kind: ProviderProfile['provider_kind']; base_url: string; auth_mode: ProviderProfile['auth_mode']; enabled: boolean; timeout_seconds: number; concurrency_limit: number; capabilities: Partial<Record<ProviderCapability, { model_id: string; max_tokens: number }>>; api_key: string };
const freshForm = (): FormState => ({ name: '', provider_kind: 'lm_studio', base_url: 'http://127.0.0.1:1234/v1', auth_mode: 'none', enabled: true, timeout_seconds: 15, concurrency_limit: 2, capabilities: {}, api_key: '' });
const emptyFallback: FallbackPolicy = { capability: 'chat', enabled: false, ordered_revision_ids: [] };
const emptyPanel: PanelState = { profiles: [], routes: [], revisions: [], audit: [], usage: [], fallback: emptyFallback };

export function AiProviderAdminPanel({ locale, csrfToken, authMethod, onRequireLocalOwnerLogin }: Props) {
  const copy = { ...words[locale], ...supplementalWords[locale] };
  const revisionStatusText = (status: ProviderRevision['validation_status']) => status === 'valid' ? copy.revisionValid : status === 'invalid' ? copy.revisionInvalid : status === 'unavailable' ? copy.revisionUnavailable : copy.revisionPending;
  const [me, setMe] = useState<AdminMe | null>(null);
  const [data, setData] = useState<PanelState>(emptyPanel);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [code, setCode] = useState('');
  const [recoveryMode, setRecoveryMode] = useState(false);
  const [enrollment, setEnrollment] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [form, setForm] = useState<FormState | null>(null);
  const [discovered, setDiscovered] = useState<Record<string, ModelDiscovery>>({});
  const [tests, setTests] = useState<Record<string, ConnectionTest>>({});
  const [fallbackDraft, setFallbackDraft] = useState<FallbackPolicy>(emptyFallback);

  const reload = useCallback(async () => {
    setBusy(true); setError('');
    try {
      const identity = await providerAdminApi.me(csrfToken);
      setMe(identity);
      if (!identity.admin) { setData(emptyPanel); return; }
      const [profiles, routes, revisions, audit, usage, fallback] = await Promise.all([
        providerAdminApi.profiles(csrfToken), providerAdminApi.routes(csrfToken), providerAdminApi.revisions(csrfToken), providerAdminApi.audit(csrfToken), providerAdminApi.usage(csrfToken), providerAdminApi.fallback(csrfToken),
      ]);
      setData({ profiles: profiles.profiles, routes: routes.routes, revisions: revisions.revisions, audit: audit.events, usage: usage.usage, fallback });
      setFallbackDraft(fallback);
    } catch (caught) {
      setMe(null); setData(emptyPanel);
      setError(caught instanceof ProviderAdminApiError && caught.status === 403 ? 'forbidden' : 'failed');
    } finally { setBusy(false); }
  }, [csrfToken]);

  useEffect(() => { void reload(); }, [reload]);

  const submitStepUp = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError('');
    try { await (recoveryMode ? providerAdminApi.recoveryStepUp(csrfToken, code) : providerAdminApi.stepUp(csrfToken, code)); setCode(''); setRecoveryMode(false); setNotice(copy.success); await reload(); }
    catch { setError(copy.failed); } finally { setBusy(false); }
  };
  const submitEnrollment = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const result = await providerAdminApi.verifyMfa(csrfToken, code);
      setRecoveryCodes(result.recovery_codes ?? []); setEnrollment(null); setCode(''); setNotice(copy.success); await reload();
    } catch { setError(copy.failed); } finally { setBusy(false); }
  };
  const saveProfile = async (event: FormEvent) => {
    event.preventDefault(); if (!form) return; setBusy(true); setError(''); setNotice('');
    try {
      const { id, version, api_key, ...profileInput } = form;
      if (id && version !== undefined) await providerAdminApi.updateProfile(csrfToken, id, { ...profileInput, ...(api_key ? { api_key } : {}), expected_version: version });
      else await providerAdminApi.createProfile(csrfToken, { ...profileInput, ...(api_key ? { api_key } : {}) });
      setForm(null); setNotice(copy.success); await reload();
    } catch { setError(copy.failed); } finally { setBusy(false); }
  };
  const changeCapability = (capability: ProviderCapability, checked: boolean) => {
    if (!supportedCapabilities.has(capability)) return;
    setForm(current => {
    if (!current) return current;
    const next = { ...current.capabilities };
    if (checked) next[capability] ??= { model_id: '', max_tokens: 800 };
    else delete next[capability];
    return { ...current, capabilities: next };
    });
  };
  const patchBinding = (capability: ProviderCapability, field: 'model_id' | 'max_tokens', value: string) => setForm(current => current ? ({ ...current, capabilities: { ...current.capabilities, [capability]: { ...current.capabilities[capability], model_id: current.capabilities[capability]?.model_id ?? '', max_tokens: current.capabilities[capability]?.max_tokens ?? 800, [field]: field === 'max_tokens' ? Number(value) : value } } }) : current);
  const startEdit = (profile: ProviderProfile) => setForm({ id: profile.id, version: profile.version, name: profile.name, provider_kind: profile.provider_kind, base_url: profile.base_url, auth_mode: profile.auth_mode, enabled: profile.enabled, timeout_seconds: profile.timeout_seconds, concurrency_limit: profile.concurrency_limit, capabilities: Object.fromEntries(Object.entries(profile.capabilities).map(([key, binding]) => [key, { model_id: binding?.model_id ?? '', max_tokens: binding?.max_tokens ?? 800 }])) as FormState['capabilities'], api_key: '' });
  const mutate = async (action: () => Promise<unknown>) => { setBusy(true); setError(''); setNotice(''); try { await action(); setNotice(copy.success); await reload(); } catch { setError(copy.failed); } finally { setBusy(false); } };
  const toggleFallbackRevision = (revisionId: string, checked: boolean) => setFallbackDraft(current => {
    const selected = current.ordered_revision_ids.filter(value => value !== revisionId);
    if (checked && selected.length < 3) selected.push(revisionId);
    return { capability: 'chat', enabled: current.enabled && selected.length > 0, ordered_revision_ids: selected };
  });
  const moveFallbackRevision = (revisionId: string, offset: -1 | 1) => setFallbackDraft(current => {
    const order = [...current.ordered_revision_ids]; const index = order.indexOf(revisionId); const target = index + offset;
    if (index < 0 || target < 0 || target >= order.length) return current;
    [order[index], order[target]] = [order[target], order[index]];
    return { ...current, ordered_revision_ids: order };
  });
  const saveFallback = async () => {
    setBusy(true); setError(''); setNotice('');
    try { const saved = await providerAdminApi.saveFallback(csrfToken, { ...fallbackDraft, capability: 'chat', ordered_revision_ids: fallbackDraft.enabled ? fallbackDraft.ordered_revision_ids.slice(0, 3) : [] }); setFallbackDraft(saved); setNotice(copy.success); await reload(); }
    catch { setError(copy.failed); } finally { setBusy(false); }
  };
  const routeByCapability = useMemo(() => Object.fromEntries(data.routes.map(route => [route.capability, route])) as Partial<Record<ProviderCapability, ActiveRoute>>, [data.routes]);
  const validatedChatRevisions = data.revisions.filter(revision => revision.capability === 'chat' && revision.validation_status === 'valid' && data.profiles.some(profile => profile.id === revision.profile_id && profile.enabled));

  if (busy && !me) return <main className="provider-admin" dir={locale === 'en-US' ? 'ltr' : 'rtl'}><p role="status">{copy.loading}</p></main>;
  if (error === 'forbidden' || (me && !me.admin)) return <main className="provider-admin" dir={locale === 'en-US' ? 'ltr' : 'rtl'}><h1>{copy.title}</h1><p role="alert">{copy.forbidden}</p>{authMethod !== 'local_owner' && onRequireLocalOwnerLogin && <button type="button" onClick={onRequireLocalOwnerLogin}>{locale === 'fa-IR' ? 'ورود مدیر محلی' : locale === 'ar' ? 'تسجيل دخول المدير المحلي' : 'Sign in as local owner'}</button>}</main>;
  return <main className="provider-admin" dir={locale === 'en-US' ? 'ltr' : 'rtl'}>
    <header><h1>{copy.title}</h1><p>{copy.intro}</p></header>
    {error && <p className="provider-admin-error" role="alert">{error === 'forbidden' ? copy.forbidden : copy.failed}</p>}
    {notice && <p className="provider-admin-notice" role="status">{notice}</p>}
    {recoveryCodes.length > 0 && <section className="provider-admin-card" role="alert"><h2>{copy.recovery}</h2><ul>{recoveryCodes.map(value => <li key={value}><code>{value}</code></li>)}</ul><button type="button" onClick={() => setRecoveryCodes([])}>{copy.closeRecovery}</button></section>}
    {me && !me.mfa_enrolled && <section className="provider-admin-card"><h2>{copy.enroll}</h2>{!enrollment ? <button type="button" disabled={busy} onClick={() => void providerAdminApi.enrollMfa(csrfToken).then(setEnrollment).catch(() => setError(copy.failed))}>{copy.enroll}</button> : <><p><code>{enrollment.secret}</code></p><p><a href={enrollment.otpauth_uri}>{enrollment.otpauth_uri}</a></p><form onSubmit={event => void submitEnrollment(event)}><label>{copy.code}<input autoComplete="one-time-code" inputMode="numeric" value={code} onChange={event => setCode(event.target.value)} required /></label><button disabled={busy}>{copy.confirmEnroll}</button></form></>}</section>}
    {me?.mfa_enrolled && !me.step_up_expires_at && <section className="provider-admin-card"><form onSubmit={event => void submitStepUp(event)}><p>{copy.stepUp}</p><button type="button" onClick={() => { setRecoveryMode(value => !value); setCode(''); }}>{recoveryMode ? copy.verify : copy.useRecovery}</button><label>{recoveryMode ? copy.recoveryCode : copy.code}<input autoComplete={recoveryMode ? 'off' : 'one-time-code'} inputMode={recoveryMode ? 'text' : 'numeric'} value={code} onChange={event => setCode(event.target.value)} required /></label><button disabled={busy}>{copy.verify}</button></form></section>}
    {me?.step_up_expires_at && <>
      <section className="provider-admin-card"><div className="provider-admin-heading"><h2>{copy.profiles}</h2><button type="button" onClick={() => setForm(freshForm())}>{copy.add}</button></div>
        {data.profiles.length === 0 ? <p>{copy.noProfiles}</p> : data.profiles.map(profile => <article className="provider-admin-profile" key={profile.id}>
          <div><strong>{profile.name}</strong><span>{profile.provider_kind} · v{profile.version}</span><span>{profile.secret_configured ? copy.keyConfigured : copy.none}</span></div>
          <div className="provider-admin-actions"><button type="button" onClick={() => startEdit(profile)}>{copy.edit}</button><button type="button" disabled={busy} onClick={() => void mutate(() => providerAdminApi.archiveProfile(csrfToken, profile.id))}>{copy.archive}</button><button type="button" disabled={busy} onClick={() => void providerAdminApi.discoverModels(csrfToken, profile.id).then(value => setDiscovered(current => ({ ...current, [profile.id]: value }))).catch(() => setError(copy.failed))}>{copy.discover}</button></div>
          {discovered[profile.id] && <p>{discovered[profile.id].models.length ? discovered[profile.id].models.join(', ') : copy.emptyModels}</p>}
          {capabilities.filter(capability => supportedCapabilities.has(capability) && profile.capabilities[capability]).map(capability => <div className="provider-admin-test" key={capability}><span>{capability}: {profile.capabilities[capability]?.model_id}</span><button type="button" disabled={busy} onClick={() => void providerAdminApi.testConnection(csrfToken, profile.id, capability, profile.capabilities[capability]!.model_id).then(async value => { setTests(current => ({ ...current, [`${profile.id}:${capability}`]: value })); if (value.success || value.status === 'validated') await reload(); }).catch(() => setTests(current => ({ ...current, [`${profile.id}:${capability}`]: { success: false, status: 'unavailable', latency_ms: null, capability, model_id: profile.capabilities[capability]!.model_id } })))}>{copy.test}</button>{tests[`${profile.id}:${capability}`] && <span role="status">{tests[`${profile.id}:${capability}`]!.status} {tests[`${profile.id}:${capability}`]!.latency_ms !== null && `· ${tests[`${profile.id}:${capability}`]!.latency_ms} ms`}</span>}</div>)}
          {form?.id !== profile.id && <button type="button" onClick={() => startEdit(profile)}>{copy.edit}</button>}
        </article>)}
        {form && <form className="provider-admin-form" onSubmit={event => void saveProfile(event)}>
          <h3>{form.id ? copy.edit : copy.add}</h3>
          <label>{copy.name}<input required maxLength={80} value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} /></label>
          <label>{copy.kind}<select disabled={Boolean(form.id)} value={form.provider_kind} onChange={event => { const provider_kind = event.target.value as FormState['provider_kind']; setForm({ ...form, provider_kind, base_url: provider_kind === 'lm_studio' ? 'http://127.0.0.1:1234/v1' : 'https://api.gapgpt.app/v1', auth_mode: provider_kind === 'lm_studio' ? 'none' : 'bearer' }); }}><option value="lm_studio">{copy.local}</option><option value="openai_compatible">{copy.compatible}</option></select></label>
          <label>{copy.endpoint}<input type="url" required value={form.base_url} onChange={event => setForm({ ...form, base_url: event.target.value })} /></label>
          <label>{copy.auth}<select value={form.auth_mode} onChange={event => setForm({ ...form, auth_mode: event.target.value as FormState['auth_mode'] })}><option value="none">{copy.none}</option><option value="bearer">{copy.bearer}</option></select></label>
          {form.auth_mode === 'bearer' && <label>{copy.secret}<input type="password" autoComplete="new-password" value={form.api_key} onChange={event => setForm({ ...form, api_key: event.target.value })} /></label>}
          <label>{copy.timeout}<input type="number" min={1} max={60} value={form.timeout_seconds} onChange={event => setForm({ ...form, timeout_seconds: Number(event.target.value) })} /></label>
          <label>{copy.concurrency}<input type="number" min={1} max={10} value={form.concurrency_limit} onChange={event => setForm({ ...form, concurrency_limit: Number(event.target.value) })} /></label>
          <fieldset><legend>{copy.caps}</legend>{capabilities.map(capability => <div key={capability}><label><input type="checkbox" checked={Boolean(form.capabilities[capability])} disabled={!supportedCapabilities.has(capability)} onChange={event => changeCapability(capability, event.target.checked)} />{capability}{!supportedCapabilities.has(capability) && <small>{copy.unsupportedCapability}</small>}</label>{form.capabilities[capability] && <><input aria-label={`${capability} ${copy.model}`} required maxLength={160} placeholder={copy.model} value={form.capabilities[capability]?.model_id ?? ''} onChange={event => patchBinding(capability, 'model_id', event.target.value)} /><input aria-label={`${capability} ${copy.maxTokens}`} type="number" min={1} max={8192} value={form.capabilities[capability]?.max_tokens ?? 800} onChange={event => patchBinding(capability, 'max_tokens', event.target.value)} /></>}</div>)}</fieldset>
          <p>{copy.fallback}</p><div className="provider-admin-actions"><button disabled={busy}>{copy.save}</button><button type="button" onClick={() => setForm(null)}>{copy.cancel}</button></div>
        </form>}
      </section>
      <section className="provider-admin-card"><h2>{copy.activeRoutes}</h2><p>{data.fallback.enabled ? copy.fallbackOn : copy.fallbackOff}{data.fallback.enabled ? ` · ${data.fallback.ordered_revision_ids.map(id => data.revisions.find(revision => revision.revision === id)?.profile_name ?? id).join(" → ")}` : ""}</p>{capabilities.map(capability => { const route = routeByCapability[capability]; return <div className="provider-admin-route" key={capability}><strong>{capability}</strong>{!supportedCapabilities.has(capability) && <span>{copy.unsupportedCapability}</span>}{route?.active ? <span>{route.profile_name} · {route.model_id} · {copy.revision} {route.revision}</span> : <span>{copy.noRoute}</span>}{route?.active ? <button type="button" disabled={busy || !supportedCapabilities.has(capability)} onClick={() => void mutate(() => providerAdminApi.deactivate(csrfToken, capability, route.version))}>{copy.deactivate}</button> : <><select disabled={!supportedCapabilities.has(capability)} aria-label={`${capability} ${copy.selectProfile}`} id={`activate-${capability}`} defaultValue=""><option value="">{copy.selectProfile}</option>{data.profiles.filter(profile => profile.enabled && profile.capabilities[capability]).map(profile => <option key={profile.id} value={profile.id}>{profile.name}</option>)}</select><button type="button" disabled={busy || !supportedCapabilities.has(capability)} onClick={() => { const select = document.getElementById(`activate-${capability}`) as HTMLSelectElement; const profile = data.profiles.find(item => item.id === select.value); const revision = data.revisions.find(item => item.profile_id === profile?.id && item.capability === capability && item.validation_status === "valid"); if (profile && revision) void mutate(() => providerAdminApi.activate(csrfToken, capability, profile.id, revision.revision, route?.version ?? 0)); else setError(copy.failed); }}>{copy.activate}</button></>}</div>; })}</section>
      <section className="provider-admin-card"><h2>{copy.fallbackOrder}</h2>
        <p>{fallbackDraft.enabled ? copy.fallbackOn : copy.fallbackOff}</p>
        <label><input type="checkbox" checked={fallbackDraft.enabled} disabled={busy || validatedChatRevisions.length === 0} onChange={event => setFallbackDraft(current => ({ ...current, enabled: event.target.checked, ordered_revision_ids: event.target.checked ? current.ordered_revision_ids : [] }))} />{copy.fallbackEnable}</label>
        {validatedChatRevisions.length === 0 ? <p>{copy.noRoute}</p> : validatedChatRevisions.map(revision => <label className="provider-admin-fallback-choice" key={revision.revision}>
          <input type="checkbox" checked={fallbackDraft.ordered_revision_ids.includes(revision.revision)} disabled={busy || (!fallbackDraft.ordered_revision_ids.includes(revision.revision) && fallbackDraft.ordered_revision_ids.length >= 3)} onChange={event => toggleFallbackRevision(revision.revision, event.target.checked)} />
          <span>{revision.profile_name} · {revision.model_id} · {revision.revision}</span>
          {fallbackDraft.ordered_revision_ids.includes(revision.revision) && <span className="provider-admin-order-controls"><span>{fallbackDraft.ordered_revision_ids.indexOf(revision.revision) + 1}</span><button type="button" disabled={busy || fallbackDraft.ordered_revision_ids.indexOf(revision.revision) === 0} onClick={() => moveFallbackRevision(revision.revision, -1)} aria-label={`Move ${revision.profile_name} fallback earlier`}>↑</button><button type="button" disabled={busy || fallbackDraft.ordered_revision_ids.indexOf(revision.revision) === fallbackDraft.ordered_revision_ids.length - 1} onClick={() => moveFallbackRevision(revision.revision, 1)} aria-label={`Move ${revision.profile_name} fallback later`}>↓</button></span>}
        </label>)}
        <button type="button" disabled={busy || (fallbackDraft.enabled && fallbackDraft.ordered_revision_ids.length === 0)} onClick={() => void saveFallback()}>{copy.save}</button>
      </section>
      <section className="provider-admin-card"><h2>{copy.revisions}</h2>{data.revisions.map(revision => <div className="provider-admin-row" key={revision.revision}><span>{revision.profile_name} · {revision.capability} · {revision.model_id} · {revision.revision} · {revisionStatusText(revision.validation_status)}</span>{!revision.active && revision.validation_status === 'valid' && <button type="button" disabled={busy || !supportedCapabilities.has(revision.capability)} onClick={() => { const route = routeByCapability[revision.capability]; void mutate(() => providerAdminApi.rollback(csrfToken, revision.capability, revision.revision, route?.version ?? 0)); }}>{copy.rollback}</button>}</div>)}</section>
      <section className="provider-admin-card"><h2>{copy.usage}</h2>{data.usage.length === 0 ? <p>—</p> : data.usage.map((item, index) => <p key={`${item.capability}-${index}`}>{item.capability}: {item.successes}/{item.calls} · {item.latency_ms_avg ?? '—'} ms</p>)}</section>
      <section className="provider-admin-card"><h2>{copy.audit}</h2>{data.audit.length === 0 ? <p>—</p> : data.audit.map((event, index) => <p key={`${event.created_at}-${index}`}>{event.created_at} · {event.action} · {event.result}</p>)}</section>
    </>}
  </main>;
}
