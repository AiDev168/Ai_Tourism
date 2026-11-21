import { useEffect, useState } from 'react';
import type { Locale } from '../i18n/messages';

type CompanyReply = {
  response_id: string;
  organization_id: string;
  display_name: string;
  response_kind: 'accepted_as_requested' | 'counter_offer';
  message: string;
  proposed_price_toman: number | string | null;
  proposed_start_date: string | null;
  proposed_end_date: string | null;
  proposed_schedule_notes: string;
  traveler_decision: 'pending' | 'accepted' | 'declined';
  created_at: string;
};

export function TravelerCompanyResponses({ locale, csrfToken, tripId }: {
  locale: Locale; csrfToken: string; tripId: string;
}) {
  const [replies, setReplies] = useState<CompanyReply[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const reload = async () => {
    const result = await fetch(`/api/v1/partners/trips/${encodeURIComponent(tripId)}/company-responses`,
      { credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' } });
    if (!result.ok) throw new Error('company_response_inbox_unavailable');
    const data = await result.json() as { items?: CompanyReply[] };
    setReplies(Array.isArray(data.items) ? data.items : []);
  };

  useEffect(() => { void reload().catch(() => { /* Older database has no response inbox until migration 0023. */ }); }, [tripId]);
  const decide = async (responseId: string, decision: 'accepted' | 'declined') => {
    const accepted = window.confirm(locale === 'fa-IR'
      ? (decision === 'accepted' ? 'این پیشنهاد شرکت را برای بررسی بعدی می‌پذیرید؟ برنامهٔ اصلی سفر خودکار تغییر نمی‌کند.' : 'این پاسخ شرکت را رد می‌کنید؟')
      : 'Confirm decision? The traveler itinerary is not modified automatically.');
    if (!accepted) return;
    setBusy(true); setNotice('');
    try {
      const response = await fetch(
        `/api/v1/partners/trips/${encodeURIComponent(tripId)}/company-responses/${encodeURIComponent(responseId)}/decision`,
        { method: 'POST', credentials: 'same-origin', cache: 'no-store',
          headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
          body: JSON.stringify({ decision }) });
      if (!response.ok) throw new Error(response.status === 409 ? 'stale' : 'unavailable');
      await reload();
      setNotice(locale === 'fa-IR' ? 'تصمیم شما ثبت شد. برنامهٔ شخصی سفر بدون تغییر باقی مانده است.' : 'Decision recorded. The itinerary remains unchanged.');
    } catch (error) {
      setNotice(error instanceof Error && error.message === 'stale'
        ? (locale === 'fa-IR' ? 'این پیشنهاد قدیمی، لغوشده یا قبلاً بررسی شده است. آخرین نسخهٔ سفر را بررسی کنید.' : 'This offer is stale, revoked, or already decided.')
        : (locale === 'fa-IR' ? 'ثبت تصمیم ممکن نبود؛ اتصال و مجوزها را بررسی کنید.' : 'Could not save the decision.'));
    } finally { setBusy(false); }
  };
  return <section className="traveler-company-responses" aria-labelledby="traveler-responses-heading">
    <div className="traveler-company-responses-heading">
      <h3 id="traveler-responses-heading">{locale === 'fa-IR' ? 'پاسخ‌ها و پیشنهادهای شرکت‌ها' : 'Company replies and offers'}</h3>
      <button type="button" disabled={busy} onClick={() => void reload().catch(() => setNotice(
        locale === 'fa-IR' ? 'صندوق پاسخ‌ها فعلاً در دسترس نیست.' : 'Response inbox unavailable.'))}>
        {locale === 'fa-IR' ? 'به‌روزرسانی پاسخ‌ها' : 'Refresh replies'}
      </button>
    </div>
    <p>{locale === 'fa-IR'
      ? 'پاسخ شرکت‌ها فقط در همین صندوق داخلی ثبت می‌شود. پیشنهاد اصلاح‌شده، برنامهٔ اصلی شما را تغییر نمی‌دهد و پذیرش آن به‌تنهایی قرارداد قطعی نیست.'
      : 'Responses are private in-app records. Accepting a counter-offer does not automatically edit your itinerary or constitute a final contract.'}</p>
    {!replies.length && <p role="status">{locale === 'fa-IR' ? 'هنوز پاسخی از شرکت‌ها ثبت نشده است.' : 'No company replies yet.'}</p>}
    {notice && <p role="status">{notice}</p>}
    {replies.map(reply => <article className="traveler-company-response" key={reply.response_id}>
      <header><strong>{reply.display_name}</strong>
        <span>{reply.response_kind === 'accepted_as_requested'
          ? (locale === 'fa-IR' ? 'پذیرش درخواست بدون تغییر' : 'Accepted as requested')
          : (locale === 'fa-IR' ? 'پیشنهاد اصلاح‌شدهٔ شرکت' : 'Company counter-offer')}</span></header>
      {reply.message && <p dir="auto">{reply.message}</p>}
      {reply.proposed_price_toman !== null && <p>{locale === 'fa-IR' ? 'قیمت پیشنهادی:' : 'Proposed price:'}
        {' '}{String(reply.proposed_price_toman)} {locale === 'fa-IR' ? 'تومان' : 'TOMAN'}</p>}
      {reply.proposed_start_date && reply.proposed_end_date && <p>{locale === 'fa-IR' ? 'زمان‌بندی پیشنهادی:' : 'Proposed dates:'}
        {' '}{reply.proposed_start_date} – {reply.proposed_end_date}</p>}
      {reply.proposed_schedule_notes && <p dir="auto">{reply.proposed_schedule_notes}</p>}
      <p>{locale === 'fa-IR' ? 'وضعیت بررسی:' : 'Decision status:'}
        {' '}{reply.traveler_decision === 'pending' ? (locale === 'fa-IR' ? 'در انتظار شما' : 'Pending')
          : reply.traveler_decision === 'accepted' ? (locale === 'fa-IR' ? 'پذیرفته شده' : 'Accepted')
            : (locale === 'fa-IR' ? 'رد شده' : 'Declined')}</p>
      {reply.traveler_decision === 'pending' && <div className="traveler-company-response-actions">
        <button type="button" disabled={busy} onClick={() => void decide(reply.response_id,'accepted')}>
          {locale === 'fa-IR' ? 'پذیرش پاسخ شرکت' : 'Accept response'}
        </button>
        <button type="button" disabled={busy} onClick={() => void decide(reply.response_id,'declined')}>
          {locale === 'fa-IR' ? 'رد پاسخ شرکت' : 'Decline response'}
        </button>
      </div>}
    </article>)}
  </section>;
}
