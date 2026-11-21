import { useEffect, useState, type ReactNode } from 'react';
import type { Locale } from '../i18n/messages';
import { displayPartnerRequest } from './partnerRequestDisplay';
import { CompanyResponseActions } from './CompanyResponseActions';

type Org = { organization_id: string; display_name: string; organization_type: string; application_status: string };
type Workspace = { services: Array<Record<string, unknown>>; schedules: Array<Record<string, unknown>>; offers: Array<Record<string, unknown>>; prices: Array<Record<string, unknown>>; availability: Array<Record<string, unknown>>; destinations: Array<Record<string, unknown>> };
type PublishedPlace = { destination_id: string; canonical_name: string; province_name: string; city_name: string | null };
type RequestInboxItem = { inbox_event_id: string; event_kind: 'request_shared'|'request_revised'; created_at: string; viewed_at: string|null; revision_id: string; share_id: string; revision_number: number; trip_version: number; request_snapshot: Record<string,unknown>; itinerary_snapshot: Record<string,unknown> };
const copy: Record<Locale, Record<string,string>> = {
  'fa-IR': { title:'فضای کسب‌وکار', intro:'اطلاعات سازمان و خدمات خود را برای بازبینی ثبت کنید. ثبت اطلاعات به‌معنای انتشار عمومی نیست.', org:'سازمان', legal:'نام قانونی', display:'نام نمایشی', createOrg:'ثبت سازمان', service:'خدمت', serviceName:'نام خدمت', serviceDescription:'شرح خدمت', serviceKey:'شناسه لاتین', serviceType:'نوع خدمت', createService:'ثبت خدمت', linkDestination:'اتصال خدمت به مقصد منتشرشده', destination:'مقصد کانونی', relation:'نوع ارتباط', evidenceNote:'یادداشت مدرک (اختیاری)', createLink:'ثبت ارتباط', schedule:'برنامه زمانی', scheduleType:'نوع برنامه', timezone:'منطقه زمانی', starts:'شروع (اختیاری)', ends:'پایان (اختیاری)', createSchedule:'ثبت برنامه', offer:'پیشنهاد', offerType:'نوع پیشنهاد', createOffer:'ثبت پیشنهاد', price:'قیمت', amount:'مبلغ', currency:'کد ارز', denomination:'واحد اسمی', unit:'مبنای قیمت', createPrice:'ثبت قیمت', availability:'وضعیت دسترسی', occurrence:'زمان رخداد', state:'وضعیت', createAvailability:'ثبت وضعیت', select:'انتخاب کنید', ok:'ثبت شد؛ در انتظار بازبینی', error:'ثبت اطلاعات انجام نشد.', requestInbox:'درخواست‌های مسافرها', requestIntro:'درخواست‌ها فقط پس از اجازهٔ مسافر برای سازمان تأییدشده نمایش داده می‌شوند.', shared:'درخواست تازه', revised:'نسخهٔ به‌روزشده', revision:'نسخه', viewRequest:'دیدن درخواست و برنامه', noRequests:'درخواستی برای سازمان انتخاب‌شده وجود ندارد.', trip:'سفر', origin:'مبدأ', duration:'مدت', travelers:'مسافران', budget:'بودجه', interests:'علایق', itinerary:'برنامه سفر', unverified:'اطلاعات عملیاتی منتشرنشده است و نباید به‌عنوان واقعیت قطعی استفاده شود.' },
  'en-US': { title:'Partner workspace', intro:'Submit organization and service details for review. Submission does not publish them publicly.', org:'Organization', legal:'Legal name', display:'Display name', createOrg:'Create organization', service:'Service', serviceName:'Service name', serviceDescription:'Service description', serviceKey:'Service key', serviceType:'Service type', createService:'Create service', linkDestination:'Link service to a published destination', destination:'Canonical destination', relation:'Relationship', evidenceNote:'Evidence note (optional)', createLink:'Add destination link', schedule:'Schedule', scheduleType:'Schedule type', timezone:'Time zone', starts:'Starts (optional)', ends:'Ends (optional)', createSchedule:'Create schedule', offer:'Offer', offerType:'Offer type', createOffer:'Create offer', price:'Price', amount:'Amount', currency:'Currency code', denomination:'Denomination', unit:'Price unit', createPrice:'Add price', availability:'Availability', occurrence:'Occurrence time', state:'State', createAvailability:'Add availability', select:'Select', ok:'Saved for review', error:'Could not save this information.', requestInbox:'Traveler request inbox', requestIntro:'Requests appear only after a traveler authorizes sharing with a verified organization.', shared:'New request', revised:'Updated revision', revision:'Revision', viewRequest:'View request and itinerary', noRequests:'No requests are available for this organization.', trip:'Trip', origin:'Origin', duration:'Duration', travelers:'Travelers', budget:'Budget', interests:'Interests', itinerary:'Itinerary', unverified:'Unverified operational details must not be treated as established facts.' },
  ar: { title:'مساحة الشركاء', intro:'قدّم بيانات المؤسسة والخدمات للمراجعة. الإرسال لا يعني النشر العام.', org:'المؤسسة', legal:'الاسم القانوني', display:'الاسم الظاهر', createOrg:'إنشاء مؤسسة', service:'الخدمة', serviceName:'اسم الخدمة', serviceDescription:'وصف الخدمة', serviceKey:'معرّف الخدمة', serviceType:'نوع الخدمة', createService:'إنشاء خدمة', linkDestination:'اربط الخدمة بوجهة منشورة', destination:'الوجهة الأساسية', relation:'نوع العلاقة', evidenceNote:'ملاحظة الدليل (اختيارية)', createLink:'إضافة رابط الوجهة', schedule:'الجدول', scheduleType:'نوع الجدول', timezone:'المنطقة الزمنية', starts:'البداية (اختياري)', ends:'النهاية (اختياري)', createSchedule:'إنشاء جدول', offer:'العرض', offerType:'نوع العرض', createOffer:'إنشاء عرض', price:'السعر', amount:'المبلغ', currency:'رمز العملة', denomination:'الفئة', unit:'وحدة السعر', createPrice:'إضافة سعر', availability:'التوافر', occurrence:'وقت الواقعة', state:'الحالة', createAvailability:'إضافة التوافر', select:'اختر', ok:'حُفظت البيانات للمراجعة', error:'تعذّر حفظ البيانات.', requestInbox:'صندوق طلبات المسافرين', requestIntro:'تظهر الطلبات بعد موافقة المسافر على مشاركتها مع مؤسسة معتمدة.', shared:'طلب جديد', revised:'نسخة محدّثة', revision:'الإصدار', viewRequest:'عرض الطلب وخطة الرحلة', noRequests:'لا توجد طلبات لهذه المؤسسة.', trip:'الرحلة', origin:'نقطة الانطلاق', duration:'المدة', travelers:'المسافرون', budget:'الميزانية', interests:'الاهتمامات', itinerary:'خطة الرحلة', unverified:'يجب عدم التعامل مع المعلومات التشغيلية غير المتحقق منها كحقائق.' },
};

/** Authenticated deep links: no bearer tokens; access is checked again via the organization inbox API. */
export function partnerShareViewPath(organizationId: string, shareId: string, revision: number, view: 'request' | 'itinerary'): string {
  const query = new URLSearchParams({ org: organizationId, share: shareId, revision: String(revision), view });
  return `/partners?${query.toString()}`;
}

export function localScheduleInstant(value:string,timeZone:string):string{
  const match=/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
  if(!match)throw new Error('invalid local date');
  const wanted=match.slice(1).map(Number); const target=Date.UTC(wanted[0],wanted[1]-1,wanted[2],wanted[3],wanted[4]); let epoch=target;
  const formatter=new Intl.DateTimeFormat('en-CA',{timeZone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
  for(let i=0;i<4;i++){const parts=formatter.formatToParts(new Date(epoch));const read=(type:string)=>Number(parts.find(p=>p.type===type)?.value);const shown=[read('year'),read('month'),read('day'),read('hour'),read('minute')];const represented=Date.UTC(shown[0],shown[1]-1,shown[2],shown[3],shown[4]);const delta=target-represented;if(!delta)break;epoch+=delta;}
  const parts=formatter.formatToParts(new Date(epoch));const read=(type:string)=>Number(parts.find(p=>p.type===type)?.value);
  if(read('year')!==wanted[0]||read('month')!==wanted[1]||read('day')!==wanted[2]||read('hour')!==wanted[3]||read('minute')!==wanted[4])throw new Error('local time is invalid in selected time zone');
  return new Date(epoch).toISOString();
}

export function PartnerWorkspace({ locale, csrfToken }: { locale: Locale; csrfToken: string }) {
  const t=copy[locale];
  const linkParams = new URLSearchParams(window.location.search);
  const requestedOrg = linkParams.get('org') || '';
  const requestedShare = linkParams.get('share') || '';
  const requestedRevision = Number(linkParams.get('revision'));
  const requestedView = linkParams.get('view');
  const isLinkView = !!requestedOrg && !!requestedShare && Number.isSafeInteger(requestedRevision)
    && requestedRevision > 0 && (requestedView === 'request' || requestedView === 'itinerary');
  const [orgs,setOrgs]=useState<Org[]>([]); const [orgId,setOrgId]=useState('');
  const [inboxLoading,setInboxLoading]=useState(false);
  const [data,setData]=useState<Workspace>({services:[],schedules:[],offers:[],prices:[],availability:[],destinations:[]});
  const [publishedPlaces,setPublishedPlaces]=useState<PublishedPlace[]>([]);
  const [requestInbox,setRequestInbox]=useState<RequestInboxItem[]>([]);
  const linkedItem = isLinkView && orgId === requestedOrg
    ? requestInbox.find(item => item.share_id === requestedShare && item.revision_number === requestedRevision) : undefined;
  const [notice,setNotice]=useState(''); const [serviceId,setServiceId]=useState(''); const [scheduleId,setScheduleId]=useState(''); const [offerId,setOfferId]=useState('');
  const [destinationId,setDestinationId]=useState(''); const [destinationRelation,setDestinationRelation]=useState('at'); const [destinationEvidence,setDestinationEvidence]=useState('');
  const [serviceName,setServiceName]=useState(''); const [serviceKey,setServiceKey]=useState(''); const [serviceType,setServiceType]=useState('tour');
  const [serviceDescription,setServiceDescription]=useState(''); const [orgType,setOrgType]=useState('company'); const [occurrence,setOccurrence]=useState('');
  const [legal,setLegal]=useState(''); const [display,setDisplay]=useState('');
  const api=async(path:string,body?:unknown)=>{const r=await fetch(`/api/v1/partners${path}`,{method:body?'POST':'GET',credentials:'same-origin',headers:{Accept:'application/json',...(body?{'Content-Type':'application/json','X-CSRF-Token':csrfToken}:{})},body:body?JSON.stringify(body):undefined,cache:'no-store'}); if(!r.ok) throw new Error('request failed'); return r.json();};
  const reload=async()=>{const r=await api('/organizations');const rows=Array.isArray(r.items)?r.items as Org[]:[];setOrgs(rows); if(!orgId&&rows[0])setOrgId(rows.find(row => row.organization_id === requestedOrg)?.organization_id ?? rows[0].organization_id);};
  useEffect(()=>{void reload().catch(()=>setNotice(t.error));},[]);
  useEffect(()=>{void fetch('/api/v2/catalog/destinations?limit=100',{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}}).then(async response=>response.ok?response.json():null).then(result=>setPublishedPlaces(Array.isArray(result?.items)?result.items:[])).catch(()=>setPublishedPlaces([]));},[]);
  const reloadWorkspace=async(id:string)=>{
    setInboxLoading(true);
    try {
      const [workspace,inbox]=await Promise.all([api(`/organizations/${id}/workspace`),api(`/organizations/${id}/requests`)]);
      setData(workspace as Workspace);setRequestInbox(Array.isArray(inbox.items)?inbox.items as RequestInboxItem[]:[]);
    } finally { setInboxLoading(false); }
  };
  useEffect(()=>{if(orgId)void reloadWorkspace(orgId).catch(()=>{setData({services:[],schedules:[],offers:[],prices:[],availability:[],destinations:[]});setRequestInbox([]);setNotice(t.error);});},[orgId]);
  const submit=async(action:()=>Promise<unknown>)=>{try{await action();setNotice(t.ok);if(orgId)await reloadWorkspace(orgId);await reload();}catch{setNotice(t.error);}};
  const form=(title:string,children:ReactNode,onSubmit:()=>void,button:string)=><form className="partner-card" onSubmit={e=>{e.preventDefault();onSubmit();}}><h2>{title}</h2>{children}<button className="primary" type="submit">{button}</button></form>;
  return <main className="partner-workspace" dir={locale==='en-US'?'ltr':'rtl'}><header><p className="eyebrow">Rahgard</p><h1>{t.title}</h1><p>{t.intro}</p><a href="/">← {locale==='fa-IR'?'بازگشت به سفر':'Back to travel planning'}</a></header>
    {notice&&<p role="status">{notice}</p>}
    {isLinkView && <section className="partner-linked-view" aria-labelledby="partner-linked-view-title" data-view={requestedView}>
      <a className="partner-back-link" href="/partners">{locale === 'fa-IR' ? 'بازگشت به صندوق درخواست‌ها' : locale === 'ar' ? 'العودة إلى صندوق الطلبات' : 'Back to inbox'}</a>
      <h2 id="partner-linked-view-title">{requestedView === 'request'
        ? (locale === 'fa-IR' ? 'درخواست سفر مسافر' : locale === 'ar' ? 'طلب المسافر' : 'Traveler request')
        : (locale === 'fa-IR' ? 'برنامهٔ سفر مشترک' : locale === 'ar' ? 'برنامج الرحلة' : 'Shared itinerary')}</h2>
      {inboxLoading && <p role="status">{locale === 'fa-IR' ? 'در حال بررسی اجازهٔ دسترسی…' : 'Checking access…'}</p>}
      {!inboxLoading && !linkedItem && <p role="alert">{locale === 'fa-IR'
        ? 'این لینک در دسترس نیست؛ ممکن است مجوز اشتراک لغو شده باشد یا نسخه متعلق به شرکت دیگری باشد.'
        : 'This protected link is unavailable, revoked, or belongs to another organization.'}</p>}
      {!inboxLoading && linkedItem && <>
        <p>{t.revision} {linkedItem.revision_number} · {linkedItem.event_kind === 'request_revised' ? t.revised : t.shared}</p>
        {requestedView === 'request' ? <dl className="partner-readable-request">
          {displayPartnerRequest(
            linkedItem.request_snapshot.requirements && typeof linkedItem.request_snapshot.requirements === 'object'
              ? linkedItem.request_snapshot.requirements as Record<string,unknown> : {},
            locale,
          ).map(field => <div key={field.key} data-provided={field.provided}>
            <dt>{field.label}</dt><dd dir="auto">{field.text}</dd>
          </div>)}
          {typeof linkedItem.request_snapshot.original_request === 'string' && <div><dt>{locale === 'fa-IR' ? 'متن اصلی درخواست (با اجازهٔ مسافر)' : 'Original request with consent'}</dt><dd dir="auto">{linkedItem.request_snapshot.original_request}</dd></div>}
        </dl> : <div className="partner-readable-itinerary">
          {Array.isArray(linkedItem.itinerary_snapshot.published_itineraries)
            && linkedItem.itinerary_snapshot.published_itineraries.map((plan,index) => {
              const planData = plan as Record<string,unknown>;
              const stops = Array.isArray(planData.stops) ? planData.stops as Array<Record<string,unknown>> : [];
              return <article className="partner-shared-plan" key={String(planData.itinerary_id ?? index)}>
                <h3>{String(planData.title || t.itinerary)}</h3>
                <ol>{stops.map((stop,position)=><li key={position} dir="auto">
                  {locale === 'fa-IR' ? 'روز' : 'Day'} {String(stop.day_number ?? '—')}
                  {' · '}{locale === 'fa-IR' ? 'مقصد ثبت‌شده' : 'Recorded stop'}
                  {typeof stop.notes_fa === 'string' && stop.notes_fa.trim() !== '' && <p>{stop.notes_fa}</p>}
                </li>)}</ol>
                {!stops.length && <p>{locale === 'fa-IR' ? 'هنوز توقفی ثبت نشده است.' : 'No stops saved yet.'}</p>}
              </article>;
            })}
          {Boolean(linkedItem.itinerary_snapshot.provisional) && typeof linkedItem.itinerary_snapshot.provisional === 'object'
            && <article className="partner-shared-plan">
              <strong className="partner-unverified-label">{locale === 'fa-IR' ? 'برنامهٔ موقت — تأییدنشده' : t.unverified}</strong>
              {(Array.isArray((linkedItem.itinerary_snapshot.provisional as Record<string,unknown>).days)
                ? (linkedItem.itinerary_snapshot.provisional as Record<string,unknown>).days as Array<Record<string,unknown>>
                : []).map((day,index) => {
                  const stops = Array.isArray(day.stops) ? day.stops as Array<Record<string,unknown>> : [];
                  return <section className="partner-shared-day" key={index}>
                    <h4>{locale === 'fa-IR' ? 'روز' : 'Day'} {String(day.day_number ?? index+1)}</h4>
                    {stops.length ? <ul>{stops.map((stop,position) => {
                      const notes = stop.notes_by_locale && typeof stop.notes_by_locale === 'object'
                        ? stop.notes_by_locale as Record<string,unknown> : {};
                      return <li key={position} dir="auto"><strong>{String(stop.name ?? '—')}</strong>
                        {typeof notes[locale] === 'string' && <p>{String(notes[locale])}</p>}</li>;
                    })}</ul> : <p>{locale === 'fa-IR' ? 'هنوز برنامه‌ای برای این روز ثبت نشده است.' : 'No stops planned for this day.'}</p>}
                  </section>;
                })}
              <p>{t.unverified}</p>
            </article>}
          {!(Array.isArray(linkedItem.itinerary_snapshot.published_itineraries) && linkedItem.itinerary_snapshot.published_itineraries.length)
            && !linkedItem.itinerary_snapshot.provisional
            && <p>{locale === 'fa-IR' ? 'برنامه‌ای برای این نسخه به اشتراک گذاشته نشده است.' : 'No itinerary has been shared in this revision.'}</p>}
        </div>}
        <CompanyResponseActions locale={locale} csrfToken={csrfToken} organizationId={orgId}
          shareId={linkedItem.share_id} revisionId={linkedItem.revision_id} />
      </>}
    </section>}

    <section className="partner-primary-organization" aria-label={t.org}>
      {!!orgs.length&&<label>{t.org}<select value={orgId} onChange={e=>setOrgId(e.target.value)}>{orgs.map(o=><option key={o.organization_id} value={o.organization_id}>{o.display_name} · {o.application_status}</option>)}</select></label>}
    </section>
    {orgId&&<section className="partner-request-inbox" aria-labelledby="partner-request-inbox-title">
      <h2 id="partner-request-inbox-title">{t.requestInbox}</h2><p>{t.requestIntro}</p>
      <p className="partner-inbox-help">{locale === 'fa-IR'
        ? '«درخواست سفر» نیازها و بودجهٔ گفته‌شدهٔ مسافر را نشان می‌دهد. «برنامهٔ سفر» روزها و توقف‌های پیشنهادی را نمایش می‌دهد. نسخه‌های جدید در همین صندوق ثبت می‌شوند؛ لینک‌ها فقط با ورود اعضای مجاز قابل مشاهده هستند.'
        : 'Request links contain traveler requirements; itinerary links show the planned days. New revisions appear here. Links require an authorized company login.'}</p>
      {!requestInbox.length&&<p role="status">{t.noRequests}</p>}
      {requestInbox.map(item=>{
        const request=(item.request_snapshot.requirements&&typeof item.request_snapshot.requirements==='object'?item.request_snapshot.requirements:{}) as Record<string,unknown>;
        const itinerary=item.itinerary_snapshot as Record<string,unknown>;
        const published=Array.isArray(itinerary.published_itineraries)?itinerary.published_itineraries as Array<Record<string,unknown>>:[];
        const provisional=itinerary.provisional&&typeof itinerary.provisional==='object'?itinerary.provisional as Record<string,unknown>:null;
        const destinations=Array.isArray(request.destinations)?request.destinations.filter(value=>typeof value==='string').join(' → '):'';
        return <article className="partner-request-item" key={item.inbox_event_id}>
          <header><strong>{item.event_kind==='request_revised'?t.revised:t.shared} · {t.revision} {item.revision_number}</strong><small>{new Date(item.created_at).toLocaleString(locale)}</small></header>
          <p>{t.trip}: {destinations||String(request.trip_id??'')}</p>
          <div className="partner-share-link-actions" aria-label={locale === 'fa-IR' ? 'لینک‌های محافظت‌شدهٔ سفر' : 'Protected trip links'}>
            <a className="partner-share-link" href={partnerShareViewPath(orgId,item.share_id,item.revision_number,'request')}>
              {locale === 'fa-IR' ? 'مشاهدهٔ لینک درخواست سفر' : locale === 'ar' ? 'رابط طلب السفر' : 'Open request link'}
            </a>
            <a className="partner-share-link" href={partnerShareViewPath(orgId,item.share_id,item.revision_number,'itinerary')}>
              {locale === 'fa-IR' ? 'مشاهدهٔ لینک برنامهٔ سفر' : locale === 'ar' ? 'رابط برنامج الرحلة' : 'Open itinerary link'}
            </a>
          </div>
          <details><summary>{t.viewRequest}</summary>
            <dl className="partner-readable-request">
              {displayPartnerRequest(request,locale).map(field =>
                <div key={field.key} data-provided={field.provided}><dt>{field.label}</dt><dd dir="auto">{field.text}</dd></div>)}
            </dl>
            {typeof item.request_snapshot.original_request==='string'&&<blockquote dir="auto">{item.request_snapshot.original_request}</blockquote>}
            <h3>{t.itinerary}</h3>
            {published.map((plan,index)=><div key={String(plan.itinerary_id??index)}><strong>{String(plan.title??t.itinerary)}</strong><pre>{JSON.stringify(plan.stops??[],null,2)}</pre></div>)}
            {provisional&&<div><strong>{String(provisional.status??'provisional_unverified')}</strong><pre>{JSON.stringify(provisional.days??[],null,2)}</pre><p>{t.unverified}</p></div>}
          </details>
        </article>;
      })}
    </section>}
    <details className="partner-management-advanced" open={!orgs.length}>
      <summary>{locale === 'fa-IR' ? 'تنظیمات شرکت و خدمات تخصصی (اختیاری)' : locale === 'ar' ? 'إعدادات المؤسسة والخدمات المتقدمة (اختياري)' : 'Organization setup and advanced services (optional)'}</summary>
      <p>{locale === 'fa-IR'
        ? 'اگر تازه ثبت‌نام کرده‌اید، ابتدا سازمان را بسازید. خدمات، ارتباط با مقصد، زمان‌بندی، پیشنهاد، قیمت و ظرفیت برای تکمیل اطلاعات عملیاتی شرکت هستند؛ هیچ‌کدام به‌تنهایی پیشنهاد مسافر را تأیید یا منتشر نمی‌کنند.'
        : 'Create an organization first if needed. Service, destination, schedule, offer, price and availability forms manage unpublished business records and do not accept a traveler request.'}</p>
      {form(t.org,<><label>{t.legal}<input value={legal} onChange={e=>setLegal(e.target.value)} required maxLength={240}/></label><label>{t.display}<input value={display} onChange={e=>setDisplay(e.target.value)} required maxLength={240}/></label><select aria-label={t.org} value={orgType} onChange={e=>setOrgType(e.target.value)}><option value="company">Company</option><option value="individual_business">Individual business</option><option value="nonprofit">Nonprofit</option><option value="public_body">Public body</option><option value="other">Other</option></select></>,()=>void submit(async()=>{await api('/organizations',{legal_name:legal,display_name:display,organization_type:orgType,registration_country:'IR'});setLegal('');setDisplay('');}),t.createOrg)}
      {orgId&&<section className="partner-forms">
      {form(t.service,<><label>{t.serviceName}<input value={serviceName} onChange={e=>setServiceName(e.target.value)} required maxLength={240}/></label><label>{t.serviceDescription}<textarea value={serviceDescription} onChange={e=>setServiceDescription(e.target.value)} maxLength={4000}/></label><label>{t.serviceKey}<input value={serviceKey} onChange={e=>setServiceKey(e.target.value)} required pattern="[a-z0-9][a-z0-9_-]*" maxLength={160}/></label><label>{t.serviceType}<input value={serviceType} onChange={e=>setServiceType(e.target.value)} required maxLength={80}/></label></>,()=>void submit(async()=>{const r=await api(`/organizations/${orgId}/services`,{service_type:serviceType,service_key:serviceKey,display_name:serviceName,locale,description:serviceDescription||null});setServiceId(r.service_id);setServiceName('');setServiceKey('');setServiceDescription('');}),t.createService)}
      <label>{t.service}<select data-testid="partner-service-select" value={serviceId} onChange={e=>setServiceId(e.target.value)}><option value="">{t.select}</option>{data.services.map(s=><option key={String(s.service_id)} value={String(s.service_id)}>{String(s.service_key)} · {String(s.status)}</option>)}</select></label>
      <form className="partner-card" onSubmit={e=>{e.preventDefault();void submit(async()=>{if(!serviceId||!destinationId)throw new Error();await api(`/organizations/${orgId}/services/${serviceId}/destinations`,{destination_id:Number(destinationId),relation_type:destinationRelation,evidence_note:destinationEvidence||null});setDestinationEvidence('');});}}>
        <h2>{t.linkDestination}</h2>
        <label>{t.destination}<select value={destinationId} onChange={e=>setDestinationId(e.target.value)} required><option value="">{t.select}</option>{publishedPlaces.map(place=><option key={place.destination_id} value={place.destination_id}>{place.canonical_name} · {place.city_name||place.province_name}</option>)}</select></label>
        {publishedPlaces.length===0&&<p role="status">{locale==='fa-IR'?'مقصد منتشرشده‌ای برای اتصال در دسترس نیست.':'No published destinations are available to link.'}</p>}
        <label>{t.relation}<select value={destinationRelation} onChange={e=>setDestinationRelation(e.target.value)}><option value="at">at</option><option value="serves">serves</option><option value="near">near</option><option value="route_endpoint">route_endpoint</option></select></label>
        <label>{t.evidenceNote}<input value={destinationEvidence} onChange={e=>setDestinationEvidence(e.target.value)} maxLength={1000}/></label>
        <button className="primary" type="submit" disabled={!serviceId||!destinationId}>{t.createLink}</button>
        {!!data.destinations.length&&<ul>{data.destinations.map((item,index)=><li key={`${item.service_id}-${item.destination_id}-${index}`}>{String(item.canonical_name)} · {String(item.relation_type)} · {String(item.status)}</li>)}</ul>}
      </form>
      {form(t.schedule,<><label>{t.scheduleType}<select id="partner-schedule-type"><option value="opening_window">opening_window</option><option value="departure">departure</option><option value="appointment">appointment</option><option value="event">event</option><option value="other">other</option></select></label><label>{t.timezone}<input id="partner-timezone" defaultValue="Asia/Tehran"/></label><label>{t.starts}<input id="partner-schedule-start" type="datetime-local"/></label><label>{t.ends}<input id="partner-schedule-end" type="datetime-local"/></label></>,()=>void submit(async()=>{if(!serviceId)throw new Error();const start=(document.getElementById('partner-schedule-start') as HTMLInputElement).value;const end=(document.getElementById('partner-schedule-end') as HTMLInputElement).value;const r=await api(`/organizations/${orgId}/schedules`,{service_id:serviceId,schedule_type:(document.getElementById('partner-schedule-type') as HTMLSelectElement).value,timezone:(document.getElementById('partner-timezone') as HTMLInputElement).value,starts_at:start?localScheduleInstant(start,(document.getElementById('partner-timezone') as HTMLInputElement).value):null,ends_at:end?localScheduleInstant(end,(document.getElementById('partner-timezone') as HTMLInputElement).value):null,observed_at:new Date().toISOString()});setScheduleId(r.schedule_id);}),t.createSchedule)}
      <label>{t.schedule}<select data-testid="partner-schedule-select" value={scheduleId} onChange={e=>setScheduleId(e.target.value)}><option value="">{t.select}</option>{data.schedules.map(s=><option key={String(s.schedule_id)} value={String(s.schedule_id)}>{String(s.schedule_type)} · {String(s.status)}</option>)}</select></label>
      {form(t.offer,<label>{t.offerType}<input id="partner-offer-type" defaultValue="tour" maxLength={80}/></label>,()=>void submit(async()=>{if(!serviceId)throw new Error();const r=await api(`/organizations/${orgId}/offers`,{service_id:serviceId,schedule_id:scheduleId||null,offer_type:(document.getElementById('partner-offer-type') as HTMLInputElement).value});setOfferId(r.offer_id);}),t.createOffer)}
      <label>{t.offer}<select data-testid="partner-offer-select" value={offerId} onChange={e=>setOfferId(e.target.value)}><option value="">{t.select}</option>{data.offers.map(o=><option key={String(o.offer_id)} value={String(o.offer_id)}>{String(o.offer_type)} · {String(o.status)}</option>)}</select></label>
      {form(t.price,<><label>{t.amount}<input id="partner-price-amount" type="number" min="0" step="0.01" required/></label><label>{t.currency}<input id="partner-price-currency" defaultValue="IRR" pattern="[A-Z]{3}" required/></label><label>{t.denomination}<input id="partner-price-denomination" defaultValue="Rial" required/></label><label>{t.unit}<input id="partner-price-unit" defaultValue="per_person" required/></label></>,()=>void submit(async()=>{if(!offerId)throw new Error();await api(`/organizations/${orgId}/prices`,{offer_id:offerId,price_state:'known',amount:Number((document.getElementById('partner-price-amount') as HTMLInputElement).value),currency:(document.getElementById('partner-price-currency') as HTMLInputElement).value,denomination:(document.getElementById('partner-price-denomination') as HTMLInputElement).value,unit:(document.getElementById('partner-price-unit') as HTMLInputElement).value,observed_at:new Date().toISOString()});}),t.createPrice)}
      {form(t.availability,<><label>{t.occurrence}<input type="datetime-local" value={occurrence} onChange={e=>setOccurrence(e.target.value)} required/></label><label>{t.state}<select id="partner-availability-state"><option value="unknown">unknown</option><option value="available">available</option><option value="limited">limited</option><option value="unavailable">unavailable</option></select></label></>,()=>void submit(async()=>{if(!offerId||!scheduleId||!occurrence)throw new Error();const now=new Date().toISOString();await api(`/organizations/${orgId}/availability`,{offer_id:offerId,schedule_id:scheduleId,occurrence_starts_at:localScheduleInstant(occurrence,typeof data.schedules.find(item=>item.schedule_id===scheduleId)?.timezone==='string'?String(data.schedules.find(item=>item.schedule_id===scheduleId)?.timezone):'Asia/Tehran'),availability_state:(document.getElementById('partner-availability-state') as HTMLSelectElement).value,observed_at:now,valid_from:now,valid_until:new Date(Date.now()+86400000).toISOString()});setOccurrence('');}),t.createAvailability)}
      </section>}
    </details>
  </main>;
}
