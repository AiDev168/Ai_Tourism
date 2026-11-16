import { useEffect, useState } from 'react';
import type { Locale } from '../../i18n/messages';

type Candidate = {
  candidate_id: string;
  candidate_kind: 'destination_identity' | 'discovery_lead';
  raw_record: Record<string, unknown>;
  raw_name: string | null;
  raw_province: string | null;
  raw_city: string | null;
  raw_coordinate_role: string | null;
  proposed_name_fa: string | null;
  proposed_destination_type: string | null;
  proposed_latitude: number | null;
  proposed_longitude: number | null;
  candidate_status: string;
  source_record_key: string;
};
type SourceCandidate = {
  source_candidate_id: string; proposed_source_key: string | null; proposed_source_name: string | null;
  proposed_publisher: string | null; proposed_source_type: string | null; proposed_url: string | null;
  proposed_license: string | null; raw_record: Record<string, unknown>; candidate_status: string;
};
type IdentityRelation = 'same_entity' | 'part_of_or_within' | 'nearby_distinct' | 'unresolved';
type Decision = 'accept' | 'approve_new_identity' | 'reject' | 'defer' | 'request_evidence';

const reviewLabels = {
    title: 'Catalogue candidate review', note: 'Records stay private and unpublished until source review and publication.',
    upload: 'Upload ZIP for review', reload: 'Reload queue', empty: 'No candidates to review.',
    name: 'Raw name', province: 'Province', city: 'City/county', coords: 'Proposed coordinates (unverified)',
    relation: 'Identity relation', target: 'Existing destination ID', reason: 'Decision reason', evidence: 'Evidence IDs/URLs, one per line',
    accept: 'Accept identity match', newIdentity: 'Explicitly approve as new identity', reject: 'Reject', defer: 'Defer',
    request: 'Request evidence', unresolved: 'Unresolved', same: 'Same entity', part: 'Part of / within',
    nearby: 'Nearby but distinct', kind: 'Record kind', identity: 'Canonical identity', lead: 'National lead',
    loadMore: 'Load more', back: 'Back', error: 'Request failed; check reviewer access.',
    placesTab: 'Place candidates', sourcesTab: 'Sources', sourceName: 'Source name', publisher: 'Publisher', sourceType: 'Source type', sourceUrl: 'Source URL', license: 'Stated license', registerPending: 'Register source as pending', status: 'Status', search: 'Search', all: 'All', rawRecord: 'Raw record',
  };
const faLabels: typeof reviewLabels = {
  title: 'بازبینی نامزدهای کاتالوگ', note: 'رکوردها تا پایان بررسی منبع و انتشار، خصوصی و منتشرنشده می‌مانند.',
  upload: 'بارگذاری ZIP برای بررسی', reload: 'بارگذاری دوباره', empty: 'نامزدی برای بررسی نیست.',
  name: 'نام خام', province: 'استان', city: 'شهر/شهرستان', coords: 'مختصات پیشنهادی (تأییدنشده)',
  relation: 'رابطه هویتی', target: 'شناسه مقصد موجود', reason: 'دلیل تصمیم', evidence: 'شناسه یا نشانی مدرک، هر مورد در یک خط',
  accept: 'تأیید تطبیق هویت', newIdentity: 'تأیید صریح هویت جدید', reject: 'رد', defer: 'تعویق',
  request: 'درخواست مدرک', unresolved: 'نامشخص', same: 'همان موجودیت', part: 'بخشی از / درون',
  nearby: 'نزدیک اما متمایز', kind: 'نوع رکورد', identity: 'هویت کانونی', lead: 'سرنخ ملی',
  loadMore: 'موارد بیشتر', back: 'بازگشت', error: 'درخواست انجام نشد؛ دسترسی بازبین را بررسی کنید.',
  placesTab: 'نامزدهای مکان', sourcesTab: 'منابع', sourceName: 'نام منبع', publisher: 'ناشر', sourceType: 'نوع منبع', sourceUrl: 'نشانی منبع', license: 'مجوز اعلام‌شده', registerPending: 'ثبت منبع در انتظار بررسی', status: 'وضعیت', search: 'جست‌وجو', all: 'همه', rawRecord: 'رکورد خام',
};
const arLabels: typeof reviewLabels = {
  title: 'مراجعة مرشحي الدليل', note: 'تبقى السجلات خاصة وغير منشورة إلى أن تكتمل مراجعة المصدر والنشر.',
  upload: 'تحميل ZIP للمراجعة', reload: 'إعادة تحميل القائمة', empty: 'لا توجد عناصر للمراجعة.',
  name: 'الاسم الخام', province: 'المحافظة', city: 'المدينة/القضاء', coords: 'إحداثيات مقترحة (غير متحققة)',
  relation: 'علاقة الهوية', target: 'معرّف الوجهة الموجودة', reason: 'سبب القرار', evidence: 'معرّفات أو روابط الأدلة، واحد في كل سطر',
  accept: 'قبول تطابق الهوية', newIdentity: 'اعتماد صريح كهوية جديدة', reject: 'رفض', defer: 'تأجيل',
  request: 'طلب أدلة', unresolved: 'غير محسوم', same: 'الكيان نفسه', part: 'جزء من / ضمن',
  nearby: 'قريب لكنه متميز', kind: 'نوع السجل', identity: 'هوية أساسية', lead: 'مرشح وطني',
  loadMore: 'تحميل المزيد', back: 'عودة', error: 'فشل الطلب؛ تحقق من صلاحية المراجع.',
  placesTab: 'مرشحو الأماكن', sourcesTab: 'المصادر', sourceName: 'اسم المصدر', publisher: 'الناشر', sourceType: 'نوع المصدر', sourceUrl: 'عنوان المصدر', license: 'الترخيص المعلن', registerPending: 'تسجيل المصدر بحالة معلّقة', status: 'الحالة', search: 'بحث', all: 'الكل', rawRecord: 'السجل الخام',
};
const labels: Record<Locale, typeof reviewLabels> = { 'fa-IR': faLabels, 'en-US': reviewLabels, ar: arLabels };

function CandidateCard({
  item, locale, busy, onDecision,
}: {
  item: Candidate; locale: Locale; busy: boolean;
  onDecision: (item: Candidate, decision: Decision, relation: IdentityRelation, target: string, reason: string, evidence: string[]) => Promise<void>;
}) {
  const t = labels[locale];
  const [target, setTarget] = useState('');
  const [reason, setReason] = useState('');
  const [evidence, setEvidence] = useState('');
  const [relation, setRelation] = useState<IdentityRelation>('unresolved');
  const evidenceRefs = evidence.split('\n').map(value => value.trim()).filter(Boolean);
  const ready = !busy && reason.trim().length > 0;
  const submit = (decision: Decision) => void onDecision(item, decision, relation, target, reason, evidenceRefs);
  return <article className="partner-card candidate-review-card" data-candidate-id={item.candidate_id}>
    <h2>{item.proposed_name_fa || item.raw_name || item.source_record_key}</h2>
    <p>{t.kind}: {item.candidate_kind === 'destination_identity' ? t.identity : t.lead} - {item.candidate_status}</p>
    <p>{t.name}: {item.raw_name || 'unknown'}</p>
    <p>{t.province}: {item.raw_province || 'unknown'} - {t.city}: {item.raw_city || 'unknown'}</p>
    <p>{t.coords}: {item.proposed_latitude ?? 'unknown'}, {item.proposed_longitude ?? 'unknown'} - {item.raw_coordinate_role || 'unknown'}</p>
    <details><summary>{t.rawRecord}</summary>
      <pre>{JSON.stringify(item.raw_record, null, 2)}</pre></details>
    <label>{t.relation}<select value={relation} onChange={event => setRelation(event.target.value as IdentityRelation)}>
      <option value="unresolved">{t.unresolved}</option><option value="same_entity">{t.same}</option>
      <option value="part_of_or_within">{t.part}</option><option value="nearby_distinct">{t.nearby}</option>
    </select></label>
    <label>{t.target}<input inputMode="numeric" value={target} onChange={event => setTarget(event.target.value.replace(/\D/g, ''))} /></label>
    <label>{t.reason}<input value={reason} onChange={event => setReason(event.target.value)} maxLength={2000} /></label>
    <label>{t.evidence}<textarea value={evidence} onChange={event => setEvidence(event.target.value)} maxLength={3000} /></label>
    <div className="candidate-review-actions">
      <button className="primary" disabled={!ready || relation === 'unresolved' || !target || !evidenceRefs.length}
        onClick={() => submit('accept')}>{t.accept}</button>
      <button disabled={!ready || relation !== 'unresolved' || !!target || !evidenceRefs.length}
        onClick={() => submit('approve_new_identity')}>{t.newIdentity}</button>
      <button disabled={!ready || !!target} onClick={() => submit('reject')}>{t.reject}</button>
      <button disabled={!ready || !!target} onClick={() => submit('defer')}>{t.defer}</button>
      <button disabled={!ready || !!target} onClick={() => submit('request_evidence')}>{t.request}</button>
    </div>
  </article>;
}

function SourceCandidateCard({
  item, locale, busy, onDecision,
}: {
  item: SourceCandidate; locale: Locale; busy: boolean;
  onDecision: (item: SourceCandidate, decision: 'register_pending' | 'reject' | 'defer' | 'request_evidence', reason: string, evidence: string[]) => Promise<void>;
}) {
  const t = labels[locale]; const [reason, setReason] = useState(''); const [evidence, setEvidence] = useState('');
  const refs = evidence.split('\n').map(value => value.trim()).filter(Boolean);
  const submit = (decision: 'register_pending' | 'reject' | 'defer' | 'request_evidence') => void onDecision(item, decision, reason, refs);
  return <article className="partner-card candidate-review-card" data-source-candidate-id={item.source_candidate_id}>
    <h2>{item.proposed_source_name || item.proposed_source_key || item.proposed_url || item.source_candidate_id}</h2>
    <p>{t.publisher}: {item.proposed_publisher || '—'} · {t.sourceType}: {item.proposed_source_type || '—'}</p>
    <p>{t.sourceUrl}: <code dir="ltr">{item.proposed_url || '—'}</code></p>
    <p>{t.license}: {item.proposed_license || '—'}</p>
    <p>{t.status}: {item.candidate_status}</p>
    <details><summary>{locale === 'fa-IR' ? 'رکورد خام' : locale === 'ar' ? 'السجل الخام' : 'Raw record'}</summary><pre>{JSON.stringify(item.raw_record,null,2)}</pre></details>
    <label>{t.reason}<input value={reason} onChange={event=>setReason(event.target.value)} maxLength={2000}/></label>
    <label>{t.evidence}<textarea value={evidence} onChange={event=>setEvidence(event.target.value)} maxLength={3000}/></label>
    <div className="candidate-review-actions">
      <button className="primary" disabled={busy||!reason.trim()||!refs.length||!item.proposed_source_name||!item.proposed_url}
        onClick={()=>submit('register_pending')}>{t.registerPending}</button>
      <button disabled={busy||!reason.trim()} onClick={()=>submit('reject')}>{t.reject}</button>
      <button disabled={busy||!reason.trim()} onClick={()=>submit('defer')}>{t.defer}</button>
      <button disabled={busy||!reason.trim()} onClick={()=>submit('request_evidence')}>{t.request}</button>
    </div>
  </article>;
}

export function CatalogueReviewPanel({ locale, csrfToken }: { locale: Locale; csrfToken: string }) {
  const t = labels[locale];
  const [items, setItems] = useState<Candidate[]>([]);
  const [sourceItems, setSourceItems] = useState<SourceCandidate[]>([]);
  const [error, setError] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [kind, setKind] = useState('');
  const [search, setSearch] = useState('');
  const [tab, setTab] = useState<'places'|'sources'>('places');
  const [sourceCursor, setSourceCursor] = useState<string | null>(null);
  const call = async (path: string, init: RequestInit = {}) => {
    const response = await fetch(`/api/v1/catalogue-review${path}`, {
      ...init, credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', ...(init.body ? { 'Content-Type': 'application/json' } : {}), 'X-CSRF-Token': csrfToken, ...init.headers },
    });
    if (!response.ok) throw new Error('request rejected');
    return response.json();
  };
  const load = async (after?: string, append = false) => {
    try {
      setError('');
      const params = new URLSearchParams({ limit: '50' });
      if (after) params.set('after', after);
      if (kind) params.set('kind', kind);
      if (search.trim()) params.set('q', search.trim().slice(0, 120));
      const result = await call(`/candidates?${params}`);
      setItems(current => append ? [...current, ...result.items] : result.items);
      setNextCursor(result.next_cursor);
    } catch { setError(t.error); }
  };
  const loadSources = async (after?: string, append = false) => {
    try {
      setError(''); const params = new URLSearchParams({limit:'50'});
      if(after)params.set('after',after); if(search.trim())params.set('q',search.trim().slice(0,120));
      const result=await call(`/sources?${params}`);
      setSourceItems(current=>append?[...current,...result.items]:result.items); setSourceCursor(result.next_cursor);
    } catch { setError(t.error); }
  };
  useEffect(() => { void load(); }, [kind]);
  useEffect(() => { if(tab==='sources')void loadSources(); }, [tab]);
  const upload = async () => {
    if (!file) return;
    setBusy(true);
    try {
      const result = await fetch('/api/v1/catalogue-review/archives', {
        method: 'POST', credentials: 'same-origin', cache: 'no-store',
        headers: { 'Content-Type': 'application/zip', 'X-Archive-Filename': file.name, 'X-CSRF-Token': csrfToken }, body: file,
      });
      if (!result.ok) throw new Error('upload rejected');
      await load(); setFile(null);
    } catch { setError(t.error); } finally { setBusy(false); }
  };
  const decide = async (item: Candidate, decision: Decision, relation: IdentityRelation, target: string, reason: string, evidence: string[]) => {
    setBusy(true);
    try {
      await call(`/candidates/${item.candidate_id}/decision`, {
        method: 'POST', body: JSON.stringify({
          decision, identity_relation: relation, target_destination_id: target ? Number(target) : null,
          reason, evidence_refs: evidence, policy_version: 'national-catalogue-review-v1',
        }),
      });
      setItems(current => current.filter(candidate => candidate.candidate_id !== item.candidate_id));
      await load();
    } catch { setError(t.error); } finally { setBusy(false); }
  };
  const decideSource = async (item: SourceCandidate, decision: 'register_pending'|'reject'|'defer'|'request_evidence', reason: string, evidence: string[]) => {
    setBusy(true);
    try {
      await call(`/sources/${item.source_candidate_id}/decision`,{method:'POST',body:JSON.stringify({decision,reason,evidence_refs:evidence,policy_version:'national-catalogue-source-review-v1'})});
      setSourceItems(current=>current.filter(candidate=>candidate.source_candidate_id!==item.source_candidate_id));
      await loadSources();
    } catch { setError(t.error); } finally { setBusy(false); }
  };
  return <main className="partner-workspace catalogue-review" dir={locale === 'en-US' ? 'ltr' : 'rtl'}>
     <header><h1>{t.title}</h1><p>{t.note}</p><a href="/">&lt;- {t.back}</a></header>
    <section className="partner-card">
      <div className="candidate-review-actions"><button type="button" aria-pressed={tab==='places'} onClick={()=>setTab('places')}>{t.placesTab}</button><button type="button" aria-pressed={tab==='sources'} onClick={()=>setTab('sources')}>{t.sourcesTab}</button></div>
      {tab==='places'&&<>
      <label>{t.upload}<input type="file" accept=".zip,application/zip" onChange={event => setFile(event.target.files?.[0] ?? null)} /></label>
      <button className="primary" disabled={!file || busy} onClick={() => void upload()}>{t.upload}</button>
      <label>{t.kind}<select value={kind} onChange={event => setKind(event.target.value)}>
        <option value="">{t.all}</option>
        <option value="destination_identity">{t.identity}</option><option value="discovery_lead">{t.lead}</option>
      </select></label>
      <label>{t.search}<input value={search} onChange={event => setSearch(event.target.value)} maxLength={120} /></label>
      <button type="button" disabled={busy} onClick={() => void load()}>{t.reload}</button>
      </>}
      {tab==='sources'&&<><label>{t.search}<input value={search} onChange={event=>setSearch(event.target.value)} maxLength={120}/></label><button type="button" disabled={busy} onClick={()=>void loadSources()}>{t.reload}</button></>}
    </section>
    {error && <p role="alert">{error}</p>}
    {tab==='places'&&(items.length === 0 ? <p role="status">{t.empty}</p> : items.map(item => <CandidateCard key={item.candidate_id}
      item={item} locale={locale} busy={busy} onDecision={decide} />))}
    {tab==='places'&&nextCursor && <button disabled={busy} onClick={() => void load(nextCursor, true)}>{t.loadMore}</button>}
    {tab==='sources'&&(sourceItems.length===0?<p role="status">{t.empty}</p>:sourceItems.map(item=><SourceCandidateCard key={item.source_candidate_id} item={item} locale={locale} busy={busy} onDecision={decideSource}/>))}
    {tab==='sources'&&sourceCursor&&<button disabled={busy} onClick={()=>void loadSources(sourceCursor,true)}>{t.loadMore}</button>}
  </main>;
}
