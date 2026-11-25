import { useEffect, useState } from 'react';
import type { Locale } from '../i18n/messages';
import { CatalogueReviewPanel } from './catalogue/CatalogueReviewPanel';
import { CompanyReviewQueue } from '../partners/CompanyReviewQueue';
import { PlatformAdminMfaPanel } from './PlatformAdminMfaPanel';
import './adminControlCenter.css';

type CapabilityReply = {
  sections: { companies: boolean; destinations: boolean; users: boolean; system: boolean };
  company_capabilities: Record<string, boolean>;
  catalogue_capabilities: Record<string, boolean>;
  ai_admin: { available: boolean; scope: string };
  privileged_writes_available?: boolean;
  privileged_step_up?: { available: boolean; required: boolean; enrolled: boolean; step_up_expires_at: string | null };
};
type Overview = {
  release?: { commit?: string };
  system?: { api?: string; database: string; postgres_major: number; migration_count: number; latest_migration: string | null; backup_evidence: string };
  users?: { account_count: number };
  access?: { grant_counts: Array<{ domain: string; capability: string; active_count: number }> };
  companies?: { organization_count: number; awaiting_application: number; awaiting_verification: number; share_eligible_count?: number };
  destinations?: { published_count: number };
  ai_admin?: { available: boolean; scope: string };
};
type Section = 'home' | 'companies' | 'destinations' | 'users' | 'system';

const words: Record<Locale, Record<string, string>> = {
  'fa-IR': {
    title: 'مرکز راهبری رهگرد', intro: 'نمای کلی مجوزهای همین حساب. هر تصمیم فقط از مسیر API و مجوز مستقل همان بخش انجام می‌شود.', loading: 'در حال بررسی دسترسی…', denied: 'این حساب دسترسی مدیریتی ندارد.', failed: 'اطلاعات مرکز راهبری بارگیری نشد.', home: 'نمای کلی', companies: 'مدیریت شرکت‌ها', destinations: 'مدیریت مقصدها', users: 'کاربران و دسترسی', system: 'سلامت سامانه', review: 'صف بررسی شرکت‌ها', catalogue: 'بازبینی کاتالوگ', provider: 'مدیریت هوش مصنوعی', aiLocal: 'مدیریت مدل فقط در پایلوت محلی، با مالک مجاز و تأیید دومرحله‌ای فعال است؛ در این محیط عمومی غیرفعال است.', accounts: 'حساب‌های کاربری', organizations: 'شرکت‌ها', awaitingApplication: 'در انتظار تصمیم درخواست', awaitingVerification: 'در انتظار بررسی مدارک', eligible: 'شرکت واجد شرایط اشتراک', destinationsCount: 'مقصد منتشرشده', database: 'پایگاه داده', pg: 'نسخه PostgreSQL', migrations: 'تعداد تغییرات ثبت‌شده', latest: 'آخرین تغییر', backup: 'وضعیت مدرک پشتیبان', unavailable: 'از برنامه قابل مشاهده نیست', release: 'نسخه برنامه', capabilities: 'مجوزهای فعال این حساب', noCapability: 'هیچ اختیار تغییردهنده‌ای از این صفحه اعطا نمی‌شود.', publicOnly: 'این نمایه فقط وضعیت‌های تجمیعی را نشان می‌دهد؛ اطلاعات هویتی کاربران و تنظیمات محرمانه نمایش داده نمی‌شوند.', back: 'بازگشت به سفر', companyHint: 'پرونده‌ها با بازبین مستقل بررسی می‌شوند. درخواست بررسی خود شخص ثبت‌کننده رد خواهد شد.', grants: 'تعداد مجوزهای فعال به تفکیک حوزه',
    api: "\u067e\u0627\u0633\u062e\u200c\u06af\u0648",
  },
  'en-US': {
    title: 'Rahgard owner control center', intro: 'Overview of this account’s explicit grants. Each decision continues through its existing API and independent capability check.', loading: 'Checking administrator access…', denied: 'This account has no administrative capability.', failed: 'The control-center information could not be loaded.', home: 'Overview', companies: 'Company governance', destinations: 'Destination governance', users: 'Users and access', system: 'System health', review: 'Company review queue', catalogue: 'Catalogue review', provider: 'AI provider administration', aiLocal: 'Provider administration is restricted to an authorized local pilot owner with MFA. It is unavailable in this public environment.', accounts: 'User accounts', organizations: 'Organizations', awaitingApplication: 'Applications awaiting decision', awaitingVerification: 'Evidence reviews pending', eligible: 'Share-eligible companies', destinationsCount: 'Published destinations', database: 'Database', pg: 'PostgreSQL major', migrations: 'Recorded migrations', latest: 'Latest migration', backup: 'Backup evidence', unavailable: 'Not available to the application', release: 'Application release', capabilities: 'This account’s active grants', noCapability: 'This page cannot grant or change privileges.', publicOnly: 'Only aggregate status is shown. User identities and confidential settings are not exposed.', back: 'Back to trip planning', companyHint: 'Cases remain independently reviewed. A submitter cannot review their own organization.', grants: 'Active grant counts by area',
    api: "Responding",
  },
  ar: {
    title: 'مركز إدارة رهگرد', intro: 'نظرة على الصلاحيات الصريحة لهذا الحساب. يظل كل قرار خاضعاً لواجهة برمجية وفحص صلاحيات مستقل.', loading: 'جارٍ التحقق من صلاحيات الإدارة…', denied: 'لا يملك هذا الحساب صلاحية إدارية.', failed: 'تعذر تحميل معلومات مركز الإدارة.', home: 'نظرة عامة', companies: 'حوكمة المؤسسات', destinations: 'حوكمة الوجهات', users: 'المستخدمون والصلاحيات', system: 'حالة النظام', review: 'قائمة مراجعة المؤسسات', catalogue: 'مراجعة الدليل', provider: 'إدارة مزودي الذكاء الاصطناعي', aiLocal: 'إدارة المزود محصورة بمالك مخول في بيئة تجريبية محلية مع تحقق متعدد العوامل، وهي غير متاحة هنا.', accounts: 'حسابات المستخدمين', organizations: 'المؤسسات', awaitingApplication: 'طلبات بانتظار القرار', awaitingVerification: 'مراجعات أدلة معلقة', eligible: 'المؤسسات المؤهلة للمشاركة', destinationsCount: 'وجهات منشورة', database: 'قاعدة البيانات', pg: 'إصدار PostgreSQL الرئيسي', migrations: 'عمليات الترحيل المسجلة', latest: 'آخر ترحيل', backup: 'دليل النسخ الاحتياطي', unavailable: 'غير متاح للتطبيق', release: 'إصدار التطبيق', capabilities: 'صلاحيات الحساب النشطة', noCapability: 'لا يمكن منح الصلاحيات أو تغييرها من هذه الصفحة.', publicOnly: 'تعرض هذه الصفحة حالة إجمالية فقط ولا تكشف هويات المستخدمين أو الإعدادات السرية.', back: 'العودة إلى التخطيط', companyHint: 'تُراجع الحالات بصورة مستقلة، ولا يمكن لصاحب المؤسسة مراجعة ملف مؤسسته.', grants: 'أعداد الصلاحيات النشطة حسب المجال',
    api: "\u064a\u0633\u062a\u062c\u064a\u0628",
  },
};

export function AdminControlCenter({ locale, csrfToken }: { locale: Locale; csrfToken: string }) {
  const t = words[locale];
  const [capabilities, setCapabilities] = useState<CapabilityReply | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [section, setSection] = useState<Section>('home');
  const [state, setState] = useState<'loading' | 'ready' | 'denied' | 'error'>('loading');
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const response = await fetch('/api/v1/admin/capabilities', { credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' } });
        if (response.status === 401 || response.status === 403) { if (active) setState('denied'); return; }
        if (!response.ok) throw new Error();
        const access = await response.json() as CapabilityReply;
        const summaryResponse = await fetch('/api/v1/admin/overview', { credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' } });
        if (!summaryResponse.ok) throw new Error();
        const summary = await summaryResponse.json() as Overview;
        if (active) { setCapabilities(access); setOverview(summary); setState('ready'); }
      } catch { if (active) setState('error'); }
    })();
    return () => { active = false; };
  }, [csrfToken, refresh]);

  const nav: Array<[Section, string, boolean]> = [
    ['home', t.home, true], ['companies', t.companies, !!capabilities?.sections.companies],
    ['destinations', t.destinations, !!capabilities?.sections.destinations], ['users', t.users, !!capabilities?.sections.users],
    ['system', t.system, !!capabilities?.sections.system],
  ];
  const metric = (label: string, value: string | number | undefined) => <article className="admin-metric" key={label}><span>{label}</span><strong>{value ?? '—'}</strong></article>;

  if (state === 'loading') return <main className="admin-control" dir={locale === 'en-US' ? 'ltr' : 'rtl'}><p role="status">{t.loading}</p></main>;
  if (state === 'denied') return <main className="admin-control" dir={locale === 'en-US' ? 'ltr' : 'rtl'}><h1>{t.title}</h1><p role="alert">{t.denied}</p><a className="admin-back" href="/">{t.back}</a></main>;
  if (state === 'error' || !capabilities || !overview) return <main className="admin-control" dir={locale === 'en-US' ? 'ltr' : 'rtl'}><h1>{t.title}</h1><p role="alert">{t.failed}</p><button type="button" className="secondary" onClick={() => setRefresh(value => value + 1)}>{locale === 'fa-IR' ? 'تلاش دوباره' : locale === 'ar' ? 'إعادة المحاولة' : 'Retry'}</button></main>;

  return <main className="admin-control" dir={locale === 'en-US' ? 'ltr' : 'rtl'}>
    <header className="admin-control-header"><div><p className="eyebrow">Rahgard · Admin</p><h1>{t.title}</h1><p>{t.intro}</p></div><a className="admin-back" href="/">{t.back}</a></header>
    {capabilities.privileged_step_up?.required && <PlatformAdminMfaPanel
      locale={locale} csrfToken={csrfToken} status={capabilities.privileged_step_up}
      onChanged={() => setRefresh(value => value + 1)}
    />}
    <nav className="admin-control-nav" aria-label={t.title}>{nav.filter(([, , visible]) => visible).map(([key, label]) => <button key={key} type="button" className={section === key ? 'active' : ''} aria-current={section === key ? 'page' : undefined} onClick={() => setSection(key)}>{label}</button>)}</nav>
    {section === 'home' && <>
      <section className="admin-control-cards" aria-label={t.home}>
        {capabilities.sections.companies && <button type="button" className="admin-control-card" onClick={() => setSection('companies')}><span>{t.companies}</span><strong>{overview.companies?.organization_count ?? '—'}</strong><small>{t.awaitingApplication}: {overview.companies?.awaiting_application ?? '—'}</small></button>}
        {capabilities.sections.destinations && <button type="button" className="admin-control-card" onClick={() => setSection('destinations')}><span>{t.destinations}</span><strong>{overview.destinations?.published_count ?? '—'}</strong><small>{t.destinationsCount}</small></button>}
        {capabilities.sections.users && <button type="button" className="admin-control-card" onClick={() => setSection('users')}><span>{t.users}</span><strong>{overview.users?.account_count ?? '—'}</strong><small>{t.publicOnly}</small></button>}
        {capabilities.sections.system && <button type="button" className="admin-control-card" onClick={() => setSection('system')}><span>{t.system}</span><strong>{overview.system?.database ?? '—'}</strong><small>{t.release}: {overview.release?.commit ?? '—'}</small></button>}
      </section>
      <section className="admin-capability-summary"><h2>{t.capabilities}</h2><ul>
        {Object.entries({ ...capabilities.company_capabilities, ...capabilities.catalogue_capabilities }).map(([key, allowed]) => <li key={key} data-enabled={allowed}>{key.replaceAll('_', ' ')} · {allowed ? '✓' : '—'}</li>)}
        <li data-enabled="false">AI provider administration · {t.aiLocal}</li>
      </ul><p>{t.noCapability}</p></section>
    </>}
    {section === 'companies' && capabilities.sections.companies && <section className="admin-control-section"><h2>{t.companies}</h2><p>{t.companyHint}</p>
      <div className="admin-metrics">{metric(t.organizations, overview.companies?.organization_count)}{metric(t.awaitingApplication, overview.companies?.awaiting_application)}{metric(t.awaitingVerification, overview.companies?.awaiting_verification)}{metric(t.eligible, overview.companies?.share_eligible_count)}</div>
      {capabilities.company_capabilities.organization_review ? <CompanyReviewQueue locale={locale} csrfToken={csrfToken} allowDecisions={capabilities.privileged_writes_available === true} /> : <p>{t.noCapability}</p>}
    </section>}
    {section === 'destinations' && capabilities.sections.destinations && <section className="admin-control-section"><h2>{t.destinations}</h2><p>{t.destinationsCount}: {overview.destinations?.published_count ?? '—'}</p><CatalogueReviewPanel locale={locale} csrfToken={csrfToken} readOnly={capabilities.privileged_writes_available !== true} /></section>}
    {section === 'users' && capabilities.sections.users && <section className="admin-control-section"><h2>{t.users}</h2><p>{t.publicOnly}</p><div className="admin-metrics">{metric(t.accounts, overview.users?.account_count)}</div><h3>{t.grants}</h3><ul className="admin-grant-counts">{(overview.access?.grant_counts ?? []).map(grant => <li key={`${grant.domain}:${grant.capability}`}><span>{grant.domain} · {grant.capability.replaceAll('_', ' ')}</span><strong>{grant.active_count}</strong></li>)}</ul><p>{t.noCapability}</p></section>}
    {section === 'system' && capabilities.sections.system && <section className="admin-control-section"><h2>{t.system}</h2><div className="admin-metrics">
      {metric(t.api, overview.system?.api)}{metric(t.database, overview.system?.database)}{metric(t.pg, overview.system?.postgres_major)}{metric(t.migrations, overview.system?.migration_count)}{metric(t.latest, overview.system?.latest_migration ?? undefined)}{metric(t.backup, t.unavailable)}{metric(t.release, overview.release?.commit)}
    </div><p>{t.aiLocal}</p></section>}
    <section className="admin-ai-restriction"><h2>{t.provider}</h2><p>{t.aiLocal}</p></section>
  </main>;
}
