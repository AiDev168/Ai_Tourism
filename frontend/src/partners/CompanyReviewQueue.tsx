import { useEffect, useState } from 'react';
import type { Locale } from '../i18n/messages';

type QueueItem = {
  case_id: string; organization_id: string; case_status: string; evidence_refs: string[];
  legal_name: string; display_name: string; registration_country: string;
  application_status: string; verification_status: string; participation_status: string;
};
type AuditItem = { display_name: string; entity_type: string; decision: string; reason: string; policy_version: string; occurred_at: string };

const words: Record<Locale, Record<string, string>> = {
  'fa-IR': {
    title: 'صف بررسی شرکت‌ها', intro: 'بررسی مدارک، تأیید درخواست و فعال‌سازی دریافت درخواست سه تصمیم جداگانه‌اند.',
    audit: "\u062a\u0627\u0631\u06cc\u062e\u0686\u0647 \u062a\u0635\u0645\u06cc\u0645\u200c\u0647\u0627", hideAudit: "\u0628\u0633\u062a\u0646 \u062a\u0627\u0631\u06cc\u062e\u0686\u0647", auditFailed: "\u0628\u0627\u0631\u06af\u06cc\u0631\u06cc \u062a\u0627\u0631\u06cc\u062e\u0686\u0647 \u0646\u0627\u0645\u0648\u0641\u0642 \u0628\u0648\u062f.",
    empty: 'پرونده‌ای برای بررسی وجود ندارد.', reason: 'دلیل تصمیم', verify: 'بررسی مدارک', more: 'درخواست تکمیل', rejectVerify: 'رد احراز', approve: 'تأیید درخواست', reject: 'رد درخواست', activate: 'فعال‌سازی دریافت درخواست', evidence: 'مراجع ثبت‌شده', denied: 'این حساب دسترسی بازبینی شرکت ندارد.', failed: 'صف بررسی بارگیری نشد.',
  },
  'en-US': {
    title: 'Company review queue', intro: 'Evidence verification, application approval and request-intake activation are separate decisions.',
    audit: "Decision history", hideAudit: "Hide history", auditFailed: "Could not load the review history.",
    empty: 'No company cases are waiting for review.', reason: 'Decision reason', verify: 'Verify evidence', more: 'Request information', rejectVerify: 'Reject verification', approve: 'Approve application', reject: 'Reject application', activate: 'Activate request intake', evidence: 'Submitted evidence references', denied: 'This account does not have company-review access.', failed: 'The review queue could not be loaded.',
  },
  ar: {
    title: 'قائمة مراجعة المؤسسات', intro: 'التحقق من الأدلة واعتماد الطلب وتفعيل استقبال الطلبات قرارات منفصلة.',
    audit: "\u0633\u062c\u0644 \u0627\u0644\u0642\u0631\u0627\u0631\u0627\u062a", hideAudit: "\u0625\u062e\u0641\u0627\u0621 \u0627\u0644\u0633\u062c\u0644", auditFailed: "\u062a\u0639\u0630\u0631 \u062a\u062d\u0645\u064a\u0644 \u0627\u0644\u0633\u062c\u0644.",
    empty: 'لا توجد ملفات قيد المراجعة.', reason: 'سبب القرار', verify: 'التحقق من الأدلة', more: 'طلب معلومات إضافية', rejectVerify: 'رفض التحقق', approve: 'اعتماد الطلب', reject: 'رفض الطلب', activate: 'تفعيل استقبال الطلبات', evidence: 'مراجع الأدلة المقدمة', denied: 'لا يملك هذا الحساب صلاحية مراجعة المؤسسات.', failed: 'تعذر تحميل قائمة المراجعة.',
  },
};

function status(value: string, locale: Locale): string {
  const labels: Record<string, Record<Locale, string>> = {
    submitted: { 'fa-IR': 'ارسال‌شده', 'en-US': 'Submitted', ar: 'مُرسل' },
    needs_information: { 'fa-IR': 'نیازمند اطلاعات', 'en-US': 'Needs information', ar: 'يحتاج معلومات' },
    verified: { 'fa-IR': 'احراز شده', 'en-US': 'Verified', ar: 'تم التحقق' },
    pending: { 'fa-IR': 'در انتظار', 'en-US': 'Pending', ar: 'قيد الانتظار' },
    approved: { 'fa-IR': 'تأیید شده', 'en-US': 'Approved', ar: 'معتمد' },
    active: { 'fa-IR': 'فعال', 'en-US': 'Active', ar: 'نشط' },
    inactive: { 'fa-IR': 'غیرفعال', 'en-US': 'Inactive', ar: 'غير نشط' },
    rejected: { 'fa-IR': 'رد شده', 'en-US': 'Rejected', ar: 'مرفوض' },
  };
  return labels[value]?.[locale] ?? value.replaceAll('_', ' ');
}

export function CompanyReviewQueue({ locale, csrfToken, allowDecisions = true }: { locale: Locale; csrfToken: string; allowDecisions?: boolean }) {
  const t = words[locale];
  const stepUp = locale === 'fa-IR'
    ? '\u062a\u0635\u0645\u06cc\u0645\u200c\u0647\u0627\u06cc \u0645\u062f\u06cc\u0631\u06cc\u062a\u06cc \u062a\u0627 \u0641\u0639\u0627\u0644\u200c\u0634\u062f\u0646 \u0627\u062d\u0631\u0627\u0632 \u0686\u0646\u062f\u0645\u0631\u062d\u0644\u0647\u200c\u0627\u06cc \u0628\u0627\u0632\u0628\u06cc\u0646 \u062f\u0631 \u0627\u06cc\u0646 \u0645\u062d\u06cc\u0637 \u063a\u06cc\u0631\u0641\u0639\u0627\u0644\u200c\u0627\u0646\u062f.'
    : locale === 'ar'
      ? '\u062a\u0639\u0637\u0644 \u0642\u0631\u0627\u0631\u0627\u062a \u0627\u0644\u0645\u0631\u0627\u062c\u0639\u064a\u0646 \u0647\u0646\u0627 \u062d\u062a\u0649 \u064a\u062a\u0648\u0641\u0631 \u062a\u062d\u0642\u0642 \u0625\u0636\u0627\u0641\u064a \u0644\u0644\u0645\u0631\u0627\u062c\u0639\u064a\u0646.'
      : 'Reviewer decisions are disabled here until a platform MFA step-up is available.';
  const [items, setItems] = useState<QueueItem[]>([]);
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [notice, setNotice] = useState('');
  const [auditItems, setAuditItems] = useState<AuditItem[]>([]);
  const [auditOpen, setAuditOpen] = useState(false);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [pending, setPending] = useState(false);

  const request = async (path: string, body?: unknown) => {
    const response = await fetch(`/api/v1/partners${path}`, {
      method: body ? 'POST' : 'GET', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
    const payload = await response.json().catch(() => ({})) as {
      detail?: string; items?: unknown[]; error?: { code?: string };
    };
    if (!response.ok) {
      const code = payload.detail ?? payload.error?.code ?? `http_${response.status}`;
      const error = new Error(code);
      Object.assign(error, { status: response.status });
      throw error;
    }
    return payload;
  };

  const reload = async () => {
    const result = await request('/platform/organization-review');
    setItems(Array.isArray(result.items) ? result.items as QueueItem[] : []);
    setAuthorized(true);
  };

  useEffect(() => {
    let active = true;
    void request('/platform/organization-review').then(result => {
      if (active) { setItems(Array.isArray(result.items) ? result.items as QueueItem[] : []); setAuthorized(true); }
    }).catch(error => {
      if (!active) return;
      if (error instanceof Error && (error.message === 'partner_review_not_granted'
          || (error as Error & { status?: number }).status === 403)) setAuthorized(false);
      else { setAuthorized(false); setNotice(t.failed); }
    });
    return () => { active = false; };
  }, [csrfToken, locale]);

  const toggleAudit = async () => {
    if (auditOpen) { setAuditOpen(false); return; }
    setPending(true);
    try {
      const result = await request('/platform/review-events?limit=50');
      setAuditItems(Array.isArray(result.items) ? result.items as AuditItem[] : []);
      setAuditOpen(true);
    } catch { setNotice(t.auditFailed); }
    finally { setPending(false); }
  };

  const decide = async (path: string, decision: string, reason: string) => {
    setPending(true);
    try {
      await request(path, { decision, reason });
      setNotice(locale === 'fa-IR' ? 'تصمیم ثبت و ممیزی شد.' : locale === 'ar' ? 'تم تسجيل القرار وتدقيقه.' : 'Decision recorded and audited.');
      await reload();
    } catch {
      setNotice(t.failed);
    } finally { setPending(false); }
  };

  if (authorized !== true) return notice ? <p className="admin-inline-notice" role="status">{notice}</p> : null;

  return <section className="partner-review-queue admin-review-queue" aria-labelledby="admin-company-review-title">
    <h2 id="admin-company-review-title">{t.title}</h2><p>{t.intro}</p>
    {!allowDecisions && <p role="note" className="admin-inline-notice">{stepUp}</p>}
    <button type="button" className="secondary" disabled={pending} aria-expanded={auditOpen} onClick={() => void toggleAudit()}>{auditOpen ? t.hideAudit : t.audit}</button>
    {auditOpen && <section className="admin-review-audit" aria-label={t.audit}>
      <h3>{t.audit}</h3>
      {!auditItems.length ? <p role="status">{t.empty}</p> : <ol>{auditItems.map((item,index) => <li key={`${item.occurred_at}:${index}`}><strong>{item.display_name}</strong><span>{status(item.entity_type,locale)} ? {status(item.decision,locale)} ? {new Date(item.occurred_at).toLocaleString(locale)}</span><p>{item.reason}</p></li>)}</ol>}
    </section>}
    {notice && <p role="status">{notice}</p>}
    {!items.length ? <p>{t.empty}</p> : items.map(item => {
      const reason = reasons[item.case_id] ?? '';
      return <article className="partner-review-item" key={item.case_id}>
        <h3>{item.display_name}</h3><p>{item.legal_name} · {item.registration_country}</p>
        <p>{status(item.case_status, locale)} · {status(item.application_status, locale)} · {status(item.verification_status, locale)} · {status(item.participation_status, locale)}</p>
        <h4>{t.evidence}</h4><ul>{item.evidence_refs.map((ref, index) => <li key={`${index}-${ref}`}><span dir="auto">{ref}</span></li>)}</ul>
        <label>{t.reason}<textarea value={reason} onChange={event => setReasons(current => ({ ...current, [item.case_id]: event.target.value }))} minLength={10} maxLength={2000} /></label>
        {allowDecisions && ['submitted', 'needs_information'].includes(item.case_status) && <div className="partner-review-actions">
          <button type="button" className="primary" disabled={pending || reason.trim().length < 10} onClick={() => void decide(`/platform/verification-cases/${item.case_id}/decision`, 'verified', reason)}>{t.verify}</button>
          <button type="button" className="secondary" disabled={pending || reason.trim().length < 10} onClick={() => void decide(`/platform/verification-cases/${item.case_id}/decision`, 'needs_information', reason)}>{t.more}</button>
          <button type="button" className="secondary" disabled={pending || reason.trim().length < 10} onClick={() => void decide(`/platform/verification-cases/${item.case_id}/decision`, 'rejected', reason)}>{t.rejectVerify}</button>
        </div>}
        {allowDecisions && item.case_status === 'verified' && item.application_status === 'submitted' && <div className="partner-review-actions">
          <button type="button" className="primary" disabled={pending || reason.trim().length < 10} onClick={() => void decide(`/platform/organizations/${item.organization_id}/application-decision`, 'approve', reason)}>{t.approve}</button>
          <button type="button" className="secondary" disabled={pending || reason.trim().length < 10} onClick={() => void decide(`/platform/organizations/${item.organization_id}/application-decision`, 'reject', reason)}>{t.reject}</button>
        </div>}
        {allowDecisions && item.application_status === 'approved' && item.participation_status !== 'active' && <button type="button" className="primary" disabled={pending || reason.trim().length < 10} onClick={() => void decide(`/platform/organizations/${item.organization_id}/participation-decision`, 'activate', reason)}>{t.activate}</button>}
      </article>;
    })}
  </section>;
}
