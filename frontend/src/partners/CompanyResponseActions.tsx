import { useEffect, useState } from 'react';
import type { Locale } from '../i18n/messages';

type PartnerResponse = {
  response_id: string;
  response_kind: 'accepted_as_requested' | 'counter_offer';
  message: string;
  proposed_price_toman: string | number | null;
  proposed_start_date: string | null;
  proposed_end_date: string | null;
  proposed_schedule_notes: string;
  traveler_decision: 'pending' | 'accepted' | 'declined';
  created_at: string;
};

export function CompanyResponseActions({ locale, csrfToken, organizationId, shareId, revisionId }: {
  locale: Locale; csrfToken: string; organizationId: string; shareId: string; revisionId: string;
}) {
  const [responseKind, setResponseKind] = useState<'accepted_as_requested'|'counter_offer'>('accepted_as_requested');
  const [message, setMessage] = useState('');
  const [price, setPrice] = useState('');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [scheduleNotes, setScheduleNotes] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [items, setItems] = useState<PartnerResponse[]>([]);

  const path = `/api/v1/partners/organizations/${encodeURIComponent(organizationId)}/requests/${encodeURIComponent(shareId)}/responses`;
  const reload = async () => {
    const result = await fetch(path, { credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' } });
    if (!result.ok) throw new Error('company_responses_unavailable');
    const json = await result.json() as { items?: PartnerResponse[] };
    setItems(Array.isArray(json.items) ? json.items : []);
  };
  useEffect(() => { void reload().catch(() => { /* Optional 0023 migration is not yet active. */ }); }, [organizationId,shareId]);

  const invalidDates = (start === '' && end !== '') || (start !== '' && end === '')
    || (start !== '' && end !== '' && end < start);
  const amountValid = !price.trim() || (/^\d{1,12}(?:\.\d{1,2})?$/.test(price.trim()) && Number.isFinite(Number(price)));
  const changed = price.trim() !== '' || start !== '' || scheduleNotes.trim() !== '';
  const maySend = !busy && amountValid && !invalidDates && (
    responseKind === 'accepted_as_requested' || changed
  );

  const submit = async () => {
    if (!maySend) return;
    setBusy(true); setNotice('');
    try {
      const payload = {
        client_request_id: crypto.randomUUID(), revision_id: revisionId,
        response_kind: responseKind, message: message.trim(),
        proposed_price_toman: responseKind === 'counter_offer' && price.trim() ? Number(price) : null,
        proposed_start_date: responseKind === 'counter_offer' && start ? start : null,
        proposed_end_date: responseKind === 'counter_offer' && end ? end : null,
        proposed_schedule_notes: responseKind === 'counter_offer' ? scheduleNotes.trim() : '',
      };
      const res = await fetch(path, {
        method: 'POST', credentials: 'same-origin', cache: 'no-store',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken, Accept: 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(res.status === 409 ? 'stale' : 'unavailable');
      setNotice(locale === 'fa-IR'
        ? 'پاسخ در صندوق داخلی مسافر ثبت شد. ارسال پیامک یا ایمیل انجام نشده است.'
        : 'Response recorded in the traveler’s private inbox. No SMS or email was sent.');
      setMessage(''); setPrice(''); setStart(''); setEnd(''); setScheduleNotes('');
      await reload();
    } catch (error) {
      setNotice(error instanceof Error && error.message === 'stale'
        ? (locale === 'fa-IR' ? 'نسخهٔ درخواست تغییر کرده است؛ صفحه را به‌روز کنید.' : 'The request revision is stale. Reload.')
        : (locale === 'fa-IR' ? 'ثبت پاسخ ممکن نیست؛ وضعیت دسترسی و فعال‌بودن نسخهٔ آزمایشی ۰۰۲۳ را بررسی کنید.' : 'Could not submit. Check permissions and migration 0023.'));
    } finally { setBusy(false); }
  };

  return <section className="partner-response-actions" aria-labelledby="partner-response-title">
    <h3 id="partner-response-title">{locale === 'fa-IR' ? 'پاسخ شرکت به این سفر' : 'Company response to this trip'}</h3>
    <p>{locale === 'fa-IR'
      ? 'پذیرش بدون تغییر یعنی آمادگی برای اجرای همین درخواست؛ برای تعهد مالی نهایی، قیمت و خدمات باید جداگانه قرارداد شوند. پیشنهاد جدید فقط پاسخ مستقل شرکت است و برنامهٔ اصلی مسافر را عوض نمی‌کند.'
      : 'Accept as requested does not change the itinerary; final contractual terms require separate agreement. A counter-offer is a separate response.'}</p>
    <div className="partner-response-mode">
      <button type="button" aria-pressed={responseKind === 'accepted_as_requested'}
        onClick={() => { setResponseKind('accepted_as_requested'); setPrice(''); setStart(''); setEnd(''); setScheduleNotes(''); }}>
        {locale === 'fa-IR' ? 'پذیرش بدون تغییر' : 'Accept as requested'}
      </button>
      <button type="button" aria-pressed={responseKind === 'counter_offer'} onClick={() => setResponseKind('counter_offer')}>
        {locale === 'fa-IR' ? 'ارائهٔ پیشنهاد اصلاح‌شده' : 'Send counter-offer'}
      </button>
    </div>
    {responseKind === 'counter_offer' && <div className="partner-proposed-changes">
      <label>{locale === 'fa-IR' ? 'قیمت پیشنهادی (تومان، اختیاری)' : 'Proposed price (TOMAN)'}
        <input inputMode="decimal" value={price} onChange={event => setPrice(event.target.value)} aria-invalid={!amountValid} placeholder="25000000" />
      </label>
      <label>{locale === 'fa-IR' ? 'تاریخ شروع پیشنهادی' : 'Proposed start date'}
        <input type="date" value={start} onChange={event => setStart(event.target.value)} aria-invalid={invalidDates} />
      </label>
      <label>{locale === 'fa-IR' ? 'تاریخ پایان پیشنهادی' : 'Proposed end date'}
        <input type="date" value={end} onChange={event => setEnd(event.target.value)} aria-invalid={invalidDates} />
      </label>
      <label className="partner-response-wide">{locale === 'fa-IR' ? 'تغییرات زمان‌بندی یا خدمات' : 'Schedule/service changes'}
        <textarea maxLength={1500} rows={3} value={scheduleNotes} onChange={event => setScheduleNotes(event.target.value)} />
      </label>
      {!changed && <p role="status">{locale === 'fa-IR' ? 'برای پیشنهاد جدید، دست‌کم قیمت، تاریخ یا تغییر زمان‌بندی را مشخص کنید.' : 'Specify at least one changed term.'}</p>}
    </div>}
    <label>{locale === 'fa-IR' ? 'توضیحات همراه پاسخ (اختیاری)' : 'Message to traveler (optional)'}
      <textarea maxLength={2000} rows={3} value={message} onChange={event => setMessage(event.target.value)} />
    </label>
    <button className="primary partner-response-send" disabled={!maySend} type="button" onClick={() => void submit()}>
      {busy ? (locale === 'fa-IR' ? 'در حال ثبت…' : 'Saving…')
        : responseKind === 'accepted_as_requested'
          ? (locale === 'fa-IR' ? 'ارسال تأییدیه به صندوق مسافر' : 'Send acceptance to traveler')
          : (locale === 'fa-IR' ? 'ارسال پیشنهاد جدید به مسافر' : 'Send counter-offer')}
    </button>
    {notice && <p role="status">{notice}</p>}
    {!!items.length && <details className="partner-response-history">
      <summary>{locale === 'fa-IR' ? 'تاریخچهٔ پاسخ‌های این شرکت' : 'Company response history'} ({items.length})</summary>
      <ul>{items.map(item => <li key={item.response_id}>
        <strong>{item.response_kind === 'accepted_as_requested'
          ? (locale === 'fa-IR' ? 'پذیرش بدون تغییر' : 'Accepted as requested')
          : (locale === 'fa-IR' ? 'پیشنهاد اصلاح‌شده' : 'Counter-offer')}</strong>
        {' · '}{locale === 'fa-IR' ? 'وضعیت مسافر:' : 'Traveler decision:'} {item.traveler_decision === 'pending'
          ? (locale === 'fa-IR' ? 'در انتظار بررسی' : 'Pending')
          : item.traveler_decision === 'accepted' ? (locale === 'fa-IR' ? 'پذیرفته' : 'Accepted') : (locale === 'fa-IR' ? 'ردشده' : 'Declined')}
      </li>)}</ul>
    </details>}
  </section>;
}
