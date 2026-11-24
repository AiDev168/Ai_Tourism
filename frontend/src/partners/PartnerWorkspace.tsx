import { useEffect, useState, type ReactNode } from 'react';
import type { Locale } from '../i18n/messages';
import { displayPartnerRequest } from './partnerRequestDisplay';
import { CompanyResponseActions } from './CompanyResponseActions';

type Org = { organization_id: string; legal_name: string; display_name: string; organization_type: string; registration_country: string; verification_status: string; participation_status: string; application_status: string; updated_at:string };
type Workspace = { services: Array<Record<string, unknown>>; schedules: Array<Record<string, unknown>>; offers: Array<Record<string, unknown>>; prices: Array<Record<string, unknown>>; availability: Array<Record<string, unknown>>; destinations: Array<Record<string, unknown>> };
type PublishedPlace = { destination_id: string; canonical_name: string; province_name: string; city_name: string | null };
type RequestInboxItem = { inbox_event_id: string; event_kind: 'request_shared'|'request_revised'; created_at: string; viewed_at: string|null; revision_id: string; share_id: string; revision_number: number; trip_version: number; request_snapshot: Record<string,unknown>; itinerary_snapshot: Record<string,unknown> };
type ReviewQueueItem = { case_id:string; organization_id:string; case_status:string; evidence_refs:string[]; legal_name:string; display_name:string; registration_country:string; application_status:string; verification_status:string; participation_status:string; created_by:string };
const copy: Record<Locale, Record<string,string>> = {
  'fa-IR': { title:'فضای کسب‌وکار', intro:'مشخصات شرکت را ثبت کنید، خدمت خود را معرفی کنید و سپس اطلاعات اختیاری قیمت و زمان را اضافه کنید. اطلاعات تا بررسی و فعال‌سازی خصوصی می‌ماند.', org:'شرکت', legal:'نام قانونی', display:'نام نمایشی', createOrg:'ثبت شرکت', service:'خدمت', serviceName:'نام خدمت', serviceDescription:'شرح کوتاه خدمت', serviceKey:'شناسه لاتین', serviceType:'نوع خدمت', createService:'ثبت خدمت', linkDestination:'اتصال خدمت به مقصد منتشرشده', destination:'مقصد کانونی', relation:'نوع ارتباط', evidenceNote:'یادداشت مدرک (اختیاری)', createLink:'ثبت ارتباط', schedule:'برنامه زمانی', scheduleType:'نوع برنامه', timezone:'منطقه زمانی', starts:'شروع (اختیاری)', ends:'پایان (اختیاری)', createSchedule:'ثبت برنامه', offer:'پیشنهاد', offerType:'عنوان پیشنهاد', createOffer:'ثبت پیشنهاد', price:'قیمت', amount:'مبلغ', currency:'کد ارز', denomination:'مقیاس مبلغ', unit:'مبنای قیمت', createPrice:'ثبت مشاهده قیمت', availability:'دسترسی', occurrence:'زمان ارائه', state:'وضعیت', createAvailability:'ثبت وضعیت', select:'انتخاب کنید', ok:'ذخیره شد', error:'ثبت اطلاعات انجام نشد.', requestInbox:'درخواست‌های مجاز', requestIntro:'درخواست فقط پس از تأیید مستقل شرکت و اجازهٔ صریح مسافر نمایش داده می‌شود.', shared:'درخواست تازه', revised:'نسخهٔ به‌روزشده', revision:'نسخه', viewRequest:'دیدن درخواست و برنامه', noRequests:'درخواستی برای شرکت انتخاب‌شده وجود ندارد.', trip:'سفر', origin:'مبدأ', duration:'مدت', travelers:'مسافران', budget:'بودجه', interests:'علایق', itinerary:'برنامه سفر', unverified:'اطلاعات منتشرنشده یا تأییدنشده را به‌عنوان واقعیت قطعی استفاده نکنید.', country:'کشور ثبت', edit:'ویرایش', save:'ذخیره تغییرات', submitReview:'ارسال برای بررسی', evidenceRefs:'ارجاع به مدرک (هر خط یک ارجاع)', reviewHint:'ثبت و ارسال به معنی تأیید یا فعال‌شدن شرکت نیست.', companyStatus:'وضعیت شرکت', profileSaved:'مشخصات شرکت ذخیره شد؛ وضعیت تأیید تغییر نکرد.', serviceHelp:'شناسه داخلی خدمت به‌صورت خودکار ساخته می‌شود.', firstService:'خدمت نخست', companyStep:'۱. ثبت شرکت', serviceStep:'۲. معرفی خدمت', nextStep:'قدم بعدی', reviewQueue:'صف بررسی شرکت‌ها', verification:'بررسی مدارک', approveApplication:'تأیید درخواست', activate:'فعال‌سازی دریافت درخواست', decisionReason:'دلیل تصمیم', reviewerOnly:'این بخش فقط برای بازبین مجاز نمایش داده می‌شود.', noReviewItems:'پرونده‌ای برای بررسی وجود ندارد.', addObservation:'ثبت مشاهده جدید', priceHistory:'مشاهده‌های قیمت', saved:'ذخیره شد', requestPending:'در انتظار بررسی مستقل', inactive:'غیرفعال', active:'فعال', verified:'تأییدشده', unverifiedOrg:'تأییدنشده', countryHelp:'کد دوحرفی کشور، مانند IR.' },
  'en-US': { title:'Partner workspace', intro:'Register your company, introduce a service, then add optional price and schedule details. Information stays private until it is reviewed and activated.', org:'Company', legal:'Legal name', display:'Display name', createOrg:'Register company', service:'Service', serviceName:'Service name', serviceDescription:'Short service description', serviceKey:'Service key', serviceType:'Service type', createService:'Save service', linkDestination:'Link service to a published destination', destination:'Published destination', relation:'Relationship', evidenceNote:'Evidence note (optional)', createLink:'Add destination link', schedule:'Schedule', scheduleType:'Schedule type', timezone:'Time zone', starts:'Starts (optional)', ends:'Ends (optional)', createSchedule:'Save schedule', offer:'Offer', offerType:'Offer title', createOffer:'Save offer', price:'Price', amount:'Amount', currency:'Currency code', denomination:'Amount denomination', unit:'Price basis', createPrice:'Add price observation', availability:'Availability', occurrence:'Service time', state:'Status', createAvailability:'Add availability observation', select:'Select', ok:'Saved', error:'Could not save this information.', requestInbox:'Eligible requests', requestIntro:'Requests appear only after independent company approval and traveler authorization.', shared:'New request', revised:'Updated revision', revision:'Revision', viewRequest:'View request and itinerary', noRequests:'No requests are available for this organization.', trip:'Trip', origin:'Origin', duration:'Duration', travelers:'Travelers', budget:'Budget', interests:'Interests', itinerary:'Itinerary', unverified:'Unpublished or unverified details are not established facts.', country:'Registration country', edit:'Edit', save:'Save changes', submitReview:'Submit for review', evidenceRefs:'Evidence references (one per line)', reviewHint:'Submission does not verify or activate the company.', companyStatus:'Company status', profileSaved:'Company profile saved; verification status is unchanged.', serviceHelp:'The internal service key is generated automatically.', firstService:'First service', companyStep:'1. Register company', serviceStep:'2. Add a service', nextStep:'Next step', reviewQueue:'Company review queue', verification:'Review evidence', approveApplication:'Approve application', activate:'Activate request intake', decisionReason:'Decision reason', reviewerOnly:'This section is only available to authorized reviewers.', noReviewItems:'No applications are waiting for review.', addObservation:'Add a new observation', priceHistory:'Price observations', saved:'Saved', requestPending:'Awaiting independent review', inactive:'Inactive', active:'Active', verified:'Verified', unverifiedOrg:'Not verified', countryHelp:'Two-letter country code, for example IR.' },
  ar: { title:'مساحة الشركاء', intro:'سجّل المؤسسة، أضف خدمتك الأولى، ثم أضف السعر والوقت عند الحاجة. تبقى البيانات خاصة حتى مراجعتها وتفعيلها.', org:'المؤسسة', legal:'الاسم القانوني', display:'الاسم الظاهر', createOrg:'تسجيل المؤسسة', service:'الخدمة', serviceName:'اسم الخدمة', serviceDescription:'وصف موجز للخدمة', serviceKey:'مفتاح الخدمة', serviceType:'نوع الخدمة', createService:'حفظ الخدمة', linkDestination:'ربط الخدمة بوجهة منشورة', destination:'وجهة منشورة', relation:'نوع العلاقة', evidenceNote:'ملاحظة الدليل (اختيارية)', createLink:'إضافة وجهة', schedule:'الجدول', scheduleType:'نوع الجدول', timezone:'المنطقة الزمنية', starts:'البداية (اختياري)', ends:'النهاية (اختياري)', createSchedule:'حفظ الجدول', offer:'العرض', offerType:'عنوان العرض', createOffer:'حفظ العرض', price:'السعر', amount:'المبلغ', currency:'رمز العملة', denomination:'مقياس المبلغ', unit:'أساس السعر', createPrice:'إضافة ملاحظة سعر', availability:'التوافر', occurrence:'وقت الخدمة', state:'الحالة', createAvailability:'إضافة ملاحظة توافر', select:'اختر', ok:'تم الحفظ', error:'تعذّر حفظ البيانات.', requestInbox:'الطلبات المؤهلة', requestIntro:'تظهر الطلبات بعد اعتماد المؤسسة وموافقة المسافر الصريحة.', shared:'طلب جديد', revised:'نسخة محدّثة', revision:'الإصدار', viewRequest:'عرض الطلب والخطة', noRequests:'لا توجد طلبات لهذه المؤسسة.', trip:'الرحلة', origin:'نقطة الانطلاق', duration:'المدة', travelers:'المسافرون', budget:'الميزانية', interests:'الاهتمامات', itinerary:'خطة الرحلة', unverified:'المعلومات غير المنشورة أو غير المتحقق منها ليست حقائق مؤكدة.', country:'بلد التسجيل', edit:'تعديل', save:'حفظ التغييرات', submitReview:'إرسال للمراجعة', evidenceRefs:'مراجع الأدلة (مرجع في كل سطر)', reviewHint:'الإرسال لا يعني التحقق من المؤسسة أو تفعيلها.', companyStatus:'حالة المؤسسة', profileSaved:'تم حفظ الملف؛ لم تتغير حالة التحقق.', serviceHelp:'يتم إنشاء المفتاح الداخلي للخدمة تلقائياً.', firstService:'الخدمة الأولى', companyStep:'١. تسجيل المؤسسة', serviceStep:'٢. إضافة خدمة', nextStep:'الخطوة التالية', reviewQueue:'قائمة مراجعة المؤسسات', verification:'مراجعة الأدلة', approveApplication:'اعتماد الطلب', activate:'تفعيل استقبال الطلبات', decisionReason:'سبب القرار', reviewerOnly:'هذا القسم للمراجعين المخولين فقط.', noReviewItems:'لا توجد طلبات قيد المراجعة.', addObservation:'إضافة ملاحظة جديدة', priceHistory:'ملاحظات الأسعار', saved:'تم الحفظ', requestPending:'بانتظار مراجعة مستقلة', inactive:'غير نشط', active:'نشط', verified:'تم التحقق', unverifiedOrg:'غير متحقق', countryHelp:'رمز الدولة من حرفين، مثل IR.' },
};

function statusLabel(status: string, locale: Locale): string {
  const states: Record<string, Record<Locale, string>> = {
    draft: { 'fa-IR': 'پیش‌نویس', 'en-US': 'Draft', ar: 'مسودة' },
    submitted: { 'fa-IR': 'ارسال‌شده برای بررسی', 'en-US': 'Submitted for review', ar: 'مُرسل للمراجعة' },
    needs_information: { 'fa-IR': 'نیازمند تکمیل اطلاعات', 'en-US': 'More information needed', ar: 'يلزم استكمال المعلومات' },
    approved: { 'fa-IR': 'درخواست تأیید شده', 'en-US': 'Application approved', ar: 'تم اعتماد الطلب' },
    rejected: { 'fa-IR': 'رد شده', 'en-US': 'Rejected', ar: 'مرفوض' },
    pending: { 'fa-IR': 'در انتظار بررسی', 'en-US': 'Pending review', ar: 'قيد المراجعة' },
    published: { 'fa-IR': 'منتشرشده', 'en-US': 'Published', ar: 'منشور' },
    withdrawn: { 'fa-IR': 'پس‌گرفته‌شده', 'en-US': 'Withdrawn', ar: 'مسحوب' },
    expired: { 'fa-IR': 'منقضی‌شده', 'en-US': 'Expired', ar: 'منتهٍ' },
    available: { 'fa-IR': 'قابل ارائه', 'en-US': 'Available', ar: 'متاح' },
    unavailable: { 'fa-IR': 'غیرقابل ارائه', 'en-US': 'Unavailable', ar: 'غير متاح' },
    limited: { 'fa-IR': 'محدود', 'en-US': 'Limited', ar: 'محدود' },
    unknown: { 'fa-IR': 'نامشخص', 'en-US': 'Unknown', ar: 'غير معروف' },
    conflicting: { 'fa-IR': 'متناقض', 'en-US': 'Conflicting', ar: 'متضارب' },
    not_applicable: { 'fa-IR': 'قابل اعمال نیست', 'en-US': 'Not applicable', ar: 'لا ينطبق' },
    verified: { 'fa-IR': 'احراز شده', 'en-US': 'Verified', ar: 'تم التحقق' },
    active: { 'fa-IR': 'فعال', 'en-US': 'Active', ar: 'نشط' },
    inactive: { 'fa-IR': 'غیرفعال', 'en-US': 'Inactive', ar: 'غير نشط' },
    suspended: { 'fa-IR': 'تعلیق‌شده', 'en-US': 'Suspended', ar: 'موقوف' },
  };
  return states[status]?.[locale] ?? status;
}

function scheduleTypeLabel(value: string, locale: Locale): string {
  const labels: Record<string, Record<Locale, string>> = {
    opening_window: { 'fa-IR': 'زمان ارائه خدمت', 'en-US': 'Service hours', ar: 'ساعات تقديم الخدمة' },
    departure: { 'fa-IR': 'حرکت', 'en-US': 'Departure', ar: 'المغادرة' },
    appointment: { 'fa-IR': 'قرار', 'en-US': 'Appointment', ar: 'موعد' },
    event: { 'fa-IR': 'رویداد', 'en-US': 'Event', ar: 'فعالية' },
    other: { 'fa-IR': 'سایر', 'en-US': 'Other', ar: 'أخرى' },
  };
  return labels[value]?.[locale] ?? value;
}

function localDateTimeValue(value: unknown, timeZone: string): string {
  if (typeof value !== 'string' || !value) return '';
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return '';
  try {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone, year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).formatToParts(date);
    const get = (name: string) => parts.find(part => part.type === name)?.value ?? '';
    return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}`;
  } catch {
    return '';
  }
}

function organizationTypeLabel(value: string, locale: Locale): string {
  const labels: Record<string, Record<Locale, string>> = {
    company: { 'fa-IR': 'شرکت', 'en-US': 'Company', ar: 'شركة' },
    individual_business: { 'fa-IR': 'کسب‌وکار فردی', 'en-US': 'Individual business', ar: 'عمل فردي' },
    nonprofit: { 'fa-IR': 'غیرانتفاعی', 'en-US': 'Nonprofit', ar: 'منظمة غير ربحية' },
    public_body: { 'fa-IR': 'نهاد عمومی', 'en-US': 'Public body', ar: 'جهة عامة' },
    other: { 'fa-IR': 'سایر', 'en-US': 'Other', ar: 'أخرى' },
  };
  return labels[value]?.[locale] ?? value;
}

function relationLabel(value: string, locale: Locale): string {
  const labels: Record<string, Record<Locale, string>> = {
    at: { 'fa-IR': 'در محل', 'en-US': 'At this place', ar: 'في هذا الموقع' },
    serves: { 'fa-IR': 'خدمت‌رسانی به', 'en-US': 'Serves this place', ar: 'يخدم هذا الموقع' },
    near: { 'fa-IR': 'نزدیک', 'en-US': 'Nearby', ar: 'بالقرب' },
    route_endpoint: { 'fa-IR': 'نقطهٔ مسیر', 'en-US': 'Route endpoint', ar: 'نقطة مسار' },
  };
  return labels[value]?.[locale] ?? value;
}

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
  const [reviewQueue,setReviewQueue]=useState<ReviewQueueItem[]>([]); const [reviewer,setReviewer]=useState(false);
  const [data,setData]=useState<Workspace>({services:[],schedules:[],offers:[],prices:[],availability:[],destinations:[]});
  const [publishedPlaces,setPublishedPlaces]=useState<PublishedPlace[]>([]);
  const [requestInbox,setRequestInbox]=useState<RequestInboxItem[]>([]);
  const linkedItem = isLinkView && orgId === requestedOrg
    ? requestInbox.find(item => item.share_id === requestedShare && item.revision_number === requestedRevision) : undefined;
  const [notice,setNotice]=useState(''); const [serviceId,setServiceId]=useState(''); const [editingServiceId,setEditingServiceId]=useState(''); const [scheduleId,setScheduleId]=useState(''); const [editingScheduleId,setEditingScheduleId]=useState(''); const [offerId,setOfferId]=useState(''); const [editingOfferId,setEditingOfferId]=useState('');
  const [destinationId,setDestinationId]=useState(''); const [destinationRelation,setDestinationRelation]=useState('at'); const [destinationEvidence,setDestinationEvidence]=useState('');
  const [serviceName,setServiceName]=useState(''); const [serviceType,setServiceType]=useState('tour');
  const [serviceDescription,setServiceDescription]=useState(''); const [orgType,setOrgType]=useState('company'); const [occurrence,setOccurrence]=useState('');
  const [scheduleType,setScheduleType]=useState<'opening_window'|'departure'|'appointment'|'event'|'other'>('opening_window'); const [scheduleTimezone,setScheduleTimezone]=useState('Asia/Tehran'); const [scheduleStarts,setScheduleStarts]=useState(''); const [scheduleEnds,setScheduleEnds]=useState('');
  const [offerType,setOfferType]=useState('tour');
  const [legal,setLegal]=useState(''); const [display,setDisplay]=useState(''); const [country,setCountry]=useState('IR');
  const [evidenceText,setEvidenceText]=useState(''); const [decisionReasons,setDecisionReasons]=useState<Record<string,string>>({});
  const selectedOrg=orgs.find(row=>row.organization_id===orgId);
  const api=async(path:string,body?:unknown,method?:'GET'|'POST'|'PUT')=>{const verb=method??(body?'POST':'GET');const r=await fetch(`/api/v1/partners${path}`,{method:verb,credentials:'same-origin',headers:{Accept:'application/json',...(body?{'Content-Type':'application/json','X-CSRF-Token':csrfToken}:{})},body:body?JSON.stringify(body):undefined,cache:'no-store'});const payload=await r.json().catch(()=>({}));if(!r.ok){const code=typeof payload.detail==='string'?payload.detail:`http_${r.status}`;throw new Error(code);}return payload;};
  const reload=async()=>{const r=await api('/organizations');const rows=Array.isArray(r.items)?r.items as Org[]:[];setOrgs(rows); if(!orgId&&rows[0])setOrgId(rows.find(row => row.organization_id === requestedOrg)?.organization_id ?? rows[0].organization_id);};
  useEffect(()=>{void reload().catch(()=>setNotice(t.error));},[]);
  useEffect(()=>{let active=true;void api('/platform/organization-review').then((result)=>{if(active){setReviewer(true);setReviewQueue(Array.isArray(result.items)?result.items as ReviewQueueItem[]:[]);}}).catch(error=>{if(active&&error instanceof Error&&error.message!=='partner_review_not_granted'){setReviewer(false);}});return()=>{active=false;};},[csrfToken]);
  useEffect(()=>{void fetch('/api/v2/catalog/destinations?limit=100',{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}}).then(async response=>response.ok?response.json():null).then(result=>setPublishedPlaces(Array.isArray(result?.items)?result.items:[])).catch(()=>setPublishedPlaces([]));},[]);
  const reloadWorkspace=async(id:string)=>{
    setInboxLoading(true);
    try {
      const [workspace,inbox]=await Promise.all([api(`/organizations/${id}/workspace?locale=${encodeURIComponent(locale)}`),api(`/organizations/${id}/requests`)]);
      setData(workspace as Workspace);setRequestInbox(Array.isArray(inbox.items)?inbox.items as RequestInboxItem[]:[]);
    } finally { setInboxLoading(false); }
  };
  useEffect(()=>{if(orgId&&!reviewer)void reloadWorkspace(orgId).catch(()=>{setData({services:[],schedules:[],offers:[],prices:[],availability:[],destinations:[]});setRequestInbox([]);setNotice(t.error);});},[orgId,locale,reviewer]);
  useEffect(()=>{if(selectedOrg){setLegal(selectedOrg.legal_name);setDisplay(selectedOrg.display_name);setCountry(selectedOrg.registration_country);}},[orgId,selectedOrg?.updated_at]);
  const submit=async(action:()=>Promise<unknown>,success=t.ok)=>{try{await action();setNotice(success);if(orgId&&!reviewer)await reloadWorkspace(orgId);await reload();if(reviewer){const queue=await api('/platform/organization-review');setReviewQueue(Array.isArray(queue.items)?queue.items as ReviewQueueItem[]:[]);}}catch(error){const code=error instanceof Error?error.message:'';const known:Record<string,Record<Locale,string>>={organization_not_verified:{'fa-IR':'ابتدا احراز مستقل سازمان لازم است.','en-US':'Independent organization verification is required first.','ar':'يلزم التحقق المستقل من المؤسسة أولاً.'},organization_must_be_verified_and_approved:{'fa-IR':'برای فعال‌سازی، احراز و تأیید مستقل لازم است.','en-US':'Independent verification and application approval are required before activation.','ar':'يلزم التحقق المستقل واعتماد الطلب قبل التفعيل.'},self_review_forbidden:{'fa-IR':'امکان بررسی درخواست خودتان وجود ندارد.','en-US':'You cannot review your own organization.','ar':'لا يمكنك مراجعة مؤسستك.'},organization_review_already_pending:{'fa-IR':'یک پروندهٔ بررسی در حال انجام است.','en-US':'A review is already in progress.','ar':'توجد مراجعة قيد المعالجة.'},organization_already_verified:{'fa-IR':'این سازمان قبلاً احراز شده است.','en-US':'This organization is already verified.','ar':'تم التحقق من المؤسسة مسبقاً.'}};setNotice(known[code]?.[locale]??t.error);}};
  const form=(title:string,children:ReactNode,onSubmit:()=>void,button:string,disabled=false)=><form className="partner-card" onSubmit={e=>{e.preventDefault();onSubmit();}}><h2>{title}</h2>{children}<button className="primary" type="submit" disabled={disabled}>{button}</button></form>;
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
          shareId={linkedItem.share_id} revisionId={linkedItem.revision_id}
          tripId={String(linkedItem.request_snapshot.trip_id ?? '')} />
      </>}
    </section>}

    <section className="partner-primary-organization" aria-label={t.org}>
      {!!orgs.length&&<label>{t.org}<select value={orgId} onChange={e=>setOrgId(e.target.value)}>{orgs.map(o=><option key={o.organization_id} value={o.organization_id}>{o.display_name} · {statusLabel(o.application_status,locale)}</option>)}</select></label>}
    </section>
    {orgId&&<section className="partner-request-inbox" aria-labelledby="partner-request-inbox-title">
      <h2 id="partner-request-inbox-title">{t.requestInbox}</h2><p>{t.requestIntro}</p>
      <p className="partner-inbox-help">{locale === 'fa-IR'
        ? '«درخواست سفر» نیازها و بودجهٔ گفته‌شدهٔ مسافر را نشان می‌دهد. «برنامهٔ سفر» روزها و توقف‌های پیشنهادی را نمایش می‌دهد. نسخه‌های جدید در همین صندوق ثبت می‌شوند؛ لینک‌ها فقط با ورود اعضای مجاز قابل مشاهده هستند.'
        : 'Request links contain traveler requirements; itinerary links show the planned days. New revisions appear here. Links require an authorized company login.'}</p>
      {!requestInbox.length&&<p role="status">{t.noRequests}</p>}
      {requestInbox.map(item=>{
        const request=(item.request_snapshot.requirements&&typeof item.request_snapshot.requirements==='object'?item.request_snapshot.requirements:{}) as Record<string,unknown>;
        const destinations=Array.isArray(request.destinations)?request.destinations.filter(value=>typeof value==='string').join(' → '):'';
        return <article className="partner-request-item" key={item.inbox_event_id}>
          <header><strong>{item.event_kind==='request_revised'?t.revised:t.shared} · {t.revision} {item.revision_number}</strong><small>{new Date(item.created_at).toLocaleString(locale)}</small></header>
          <p>{t.trip}: {destinations || (locale === 'fa-IR' ? 'مقصد مشخص نشده' : 'Destination not specified')}</p>
          <div className="partner-share-link-actions" aria-label={locale === 'fa-IR' ? 'لینک‌های محافظت‌شدهٔ سفر' : 'Protected trip links'}>
            <a className="partner-share-link" href={partnerShareViewPath(orgId,item.share_id,item.revision_number,'request')}>
              {locale === 'fa-IR' ? 'مشاهدهٔ لینک درخواست سفر' : locale === 'ar' ? 'رابط طلب السفر' : 'Open request link'}
            </a>
            <a className="partner-share-link" href={partnerShareViewPath(orgId,item.share_id,item.revision_number,'itinerary')}>
              {locale === 'fa-IR' ? 'مشاهدهٔ لینک برنامهٔ سفر' : locale === 'ar' ? 'رابط برنامج الرحلة' : 'Open itinerary link'}
            </a>
          </div>
          <p className="partner-request-link-note">
            {locale === 'fa-IR'
              ? 'برای مشاهدهٔ اطلاعات این نسخه، لینک درخواست یا برنامه را انتخاب کنید. اطلاعات فقط در حساب شرکتِ مجاز نمایش داده می‌شوند.'
              : 'Open the protected request or itinerary link to review this revision.'}
          </p>

        </article>;
      })}
    </section>}
    <section className="partner-onboarding" aria-label={locale==='fa-IR'?'مراحل راه‌اندازی شرکت':'Company setup steps'}>
      <ol className="partner-setup-progress"><li data-current={!orgId}>{t.companyStep}</li><li data-current={Boolean(orgId && data.services.length===0)}>{t.serviceStep}</li><li>{locale==='fa-IR'?'۳. تکمیل اختیاری قیمت و زمان':'3. Optional pricing and schedule'}</li><li>{locale==='fa-IR'?'۴. درخواست‌های مجاز پس از تأیید':'4. Eligible requests after approval'}</li></ol>
      {!orgId ? <>
        <h2>{t.companyStep}</h2>
        <p>{t.reviewHint}</p>
        {form(t.org,<><label>{t.legal}<input value={legal} onChange={e=>setLegal(e.target.value)} required maxLength={240}/></label><label>{t.display}<input value={display} onChange={e=>setDisplay(e.target.value)} required maxLength={240}/></label><label>{locale==='fa-IR'?'نوع فعالیت':locale==='ar'?'نوع النشاط':'Organization type'}<select value={orgType} onChange={e=>setOrgType(e.target.value)}><option value="company">{organizationTypeLabel('company',locale)}</option><option value="individual_business">{organizationTypeLabel('individual_business',locale)}</option><option value="nonprofit">{organizationTypeLabel('nonprofit',locale)}</option><option value="public_body">{organizationTypeLabel('public_body',locale)}</option><option value="other">{organizationTypeLabel('other',locale)}</option></select></label><label>{t.country}<input value={country} onChange={e=>setCountry(e.target.value.toUpperCase())} required minLength={2} maxLength={2} pattern="[A-Z]{2}" aria-describedby="partner-country-help"/></label><small id="partner-country-help">{t.countryHelp}</small></>,()=>void submit(async()=>{const created=await api('/organizations',{legal_name:legal,display_name:display,organization_type:orgType,registration_country:country});setOrgId(String(created.organization_id));setLegal('');setDisplay('');}),t.createOrg)}
      </> : <>
        <h2>{t.nextStep}</h2>
        <article className="partner-company-status" aria-live="polite"><strong>{selectedOrg?.display_name}</strong><span>{t.companyStatus}: {statusLabel(selectedOrg?.application_status??'draft',locale)}</span><span>{locale==='fa-IR'?'احراز':'Verification'}: {statusLabel(selectedOrg?.verification_status??'pending',locale)}</span><span>{locale==='fa-IR'?'دریافت درخواست':'Request intake'}: {statusLabel(selectedOrg?.participation_status??'inactive',locale)}</span></article>
        {selectedOrg && form(t.edit,<><label>{t.legal}<input value={legal} onChange={e=>setLegal(e.target.value)} required maxLength={240}/></label><label>{t.display}<input value={display} onChange={e=>setDisplay(e.target.value)} required maxLength={240}/></label><label>{locale==='fa-IR'?'نوع فعالیت':locale==='ar'?'نوع النشاط':'Organization type'}<select value={selectedOrg.organization_type} onChange={e=>setOrgs(rows=>rows.map(row=>row.organization_id===orgId?{...row,organization_type:e.target.value}:row))}><option value="company">{organizationTypeLabel('company',locale)}</option><option value="individual_business">{organizationTypeLabel('individual_business',locale)}</option><option value="nonprofit">{organizationTypeLabel('nonprofit',locale)}</option><option value="public_body">{organizationTypeLabel('public_body',locale)}</option><option value="other">{organizationTypeLabel('other',locale)}</option></select></label><label>{t.country}<input value={country} onChange={e=>setCountry(e.target.value.toUpperCase())} required minLength={2} maxLength={2} pattern="[A-Z]{2}"/></label></>,()=>void submit(async()=>{await api(`/organizations/${orgId}`,{legal_name:legal,display_name:display,organization_type:selectedOrg.organization_type,registration_country:country},'PUT');},t.profileSaved),t.save,!['draft','needs_information','withdrawn','rejected'].includes(selectedOrg.application_status)||!['pending','rejected'].includes(selectedOrg.verification_status)||selectedOrg.participation_status!=='inactive')}
        <form className="partner-card" onSubmit={e=>{e.preventDefault();void submit(async()=>{const refs=evidenceText.split(/\r?\n/).map(value=>value.trim()).filter(Boolean);await api(`/organizations/${orgId}/verification-cases`,{evidence_refs:refs});setEvidenceText('');},t.requestPending);}}>
          <h3>{t.submitReview}</h3><p>{t.reviewHint}</p><label>{t.evidenceRefs}<textarea value={evidenceText} onChange={e=>setEvidenceText(e.target.value)} minLength={1} maxLength={4000} required/></label><button className="primary" type="submit" disabled={!selectedOrg || ['submitted','approved'].includes(selectedOrg.application_status)}>{t.submitReview}</button>
        </form>
        <section className="partner-first-service" aria-labelledby="partner-first-service-title">
          <h3 id="partner-first-service-title">{data.services.length ? t.service : t.firstService}</h3><p>{t.serviceHelp}</p>
          {form(editingServiceId?t.edit:t.service,<><label>{t.serviceName}<input value={serviceName} onChange={e=>setServiceName(e.target.value)} required maxLength={240}/></label><label>{t.serviceDescription}<textarea value={serviceDescription} onChange={e=>setServiceDescription(e.target.value)} maxLength={4000}/></label><label>{t.serviceType}<input value={serviceType} onChange={e=>setServiceType(e.target.value)} required maxLength={80}/></label></>,()=>void submit(async()=>{if(editingServiceId){await api(`/organizations/${orgId}/services/${editingServiceId}`,{service_type:serviceType,display_name:serviceName,locale,description:serviceDescription||null},'PUT');}else{const result=await api(`/organizations/${orgId}/services`,{service_type:serviceType,display_name:serviceName,locale,description:serviceDescription||null});setServiceId(result.service_id);}setEditingServiceId('');setServiceName('');setServiceDescription('');},t.saved),editingServiceId?t.save:t.createService)}
          {!!data.services.length&&<ul className="partner-record-list">{data.services.map(service=><li key={String(service.service_id)}><span><strong>{String(service.display_name||service.service_type)}</strong><small>{statusLabel(String(service.status),locale)}</small></span><button type="button" className="secondary" disabled={!['draft','submitted'].includes(String(service.status))} title={!['draft','submitted'].includes(String(service.status))?(locale==='fa-IR'?'خدمت تأییدشده از این فرم قابل ویرایش نیست.':'Approved or published services are locked for editing here.'):undefined} onClick={()=>{setEditingServiceId(String(service.service_id));setServiceId(String(service.service_id));setServiceName(String(service.display_name||''));setServiceDescription(String(service.description||''));setServiceType(String(service.service_type||''));}}>{t.edit}</button></li>)}</ul>}
        </section>
      </>}
    </section>
    {reviewer && <section className="partner-review-queue" aria-labelledby="partner-review-queue-title">
      <h2 id="partner-review-queue-title">{t.reviewQueue}</h2><p>{t.reviewerOnly}</p>
      {reviewQueue.length===0?<p>{t.noReviewItems}</p>:reviewQueue.map(item=>{
        const reason=decisionReasons[item.case_id]??'';
        return <article className="partner-review-item" key={item.case_id}>
          <h3>{item.display_name}</h3><p>{item.legal_name} · {item.registration_country}</p>
          <p>{statusLabel(item.case_status,locale)} · {statusLabel(item.application_status,locale)} · {statusLabel(item.verification_status,locale)}</p>
          <h4>{locale==='fa-IR'?'مراجع ثبت‌شده':'Submitted evidence references'}</h4>
          <ul>{item.evidence_refs.map((ref,index)=><li key={`${index}-${ref}`}><span dir="auto">{ref}</span></li>)}</ul>
          <label>{t.decisionReason}<textarea value={reason} onChange={e=>setDecisionReasons(current=>({...current,[item.case_id]:e.target.value}))} minLength={10} maxLength={2000}/></label>
          {['submitted','needs_information'].includes(item.case_status)&&<div className="partner-review-actions">
            <button type="button" className="primary" disabled={reason.trim().length<10} onClick={()=>void submit(()=>api(`/platform/verification-cases/${item.case_id}/decision`,{decision:'verified',reason}))}>{t.verification}</button>
            <button type="button" className="secondary" disabled={reason.trim().length<10} onClick={()=>void submit(()=>api(`/platform/verification-cases/${item.case_id}/decision`,{decision:'needs_information',reason}))}>{locale==='fa-IR'?'درخواست تکمیل':'Request information'}</button>
            <button type="button" className="secondary" disabled={reason.trim().length<10} onClick={()=>void submit(()=>api(`/platform/verification-cases/${item.case_id}/decision`,{decision:'rejected',reason}))}>{locale==='fa-IR'?'رد احراز':'Reject verification'}</button>
          </div>}
          {item.case_status==='verified'&&item.application_status==='submitted'&&<div className="partner-review-actions">
            <button type="button" className="primary" disabled={reason.trim().length<10} onClick={()=>void submit(()=>api(`/platform/organizations/${item.organization_id}/application-decision`,{decision:'approve',reason}))}>{t.approveApplication}</button>
            <button type="button" className="secondary" disabled={reason.trim().length<10} onClick={()=>void submit(()=>api(`/platform/organizations/${item.organization_id}/application-decision`,{decision:'reject',reason}))}>{locale==='fa-IR'?'رد درخواست':'Reject application'}</button>
          </div>}
          {item.application_status==='approved'&&item.participation_status!=='active'&&<button type="button" className="primary" disabled={reason.trim().length<10} onClick={()=>void submit(()=>api(`/platform/organizations/${item.organization_id}/participation-decision`,{decision:'activate',reason}))}>{t.activate}</button>}
        </article>;
      })}
    </section>}
    <details className="partner-management-advanced">
      <summary>{locale === 'fa-IR' ? 'قیمت، زمان و اتصال به مقصد (اختیاری)' : locale === 'ar' ? 'السعر والجدول وربط الوجهة (اختياري)' : 'Optional pricing, schedule and destination details'}</summary>
      <p>{locale === 'fa-IR'
        ? 'اگر تازه ثبت‌نام کرده‌اید، ابتدا سازمان را بسازید. خدمات، ارتباط با مقصد، زمان‌بندی، پیشنهاد، قیمت و ظرفیت برای تکمیل اطلاعات عملیاتی شرکت هستند؛ هیچ‌کدام به‌تنهایی پیشنهاد مسافر را تأیید یا منتشر نمی‌کنند.'
        : 'Create an organization first if needed. Service, destination, schedule, offer, price and availability forms manage unpublished business records and do not accept a traveler request.'}</p>
      <dl className="partner-advanced-help">
        {(locale === 'fa-IR'
          ? [
            ['سازمان', 'مشخصات حقوقی و نام شرکت؛ نخستین بار ثبت می‌شود.'],
            ['خدمت', 'نوع خدمت شرکت مثل تور یا اقامت؛ اطلاعات اولیه و منتشرنشده.'],
            ['اتصال به مقصد', 'مشخص می‌کند خدمت به کدام مقصد تأییدشده مربوط است.'],
            ['برنامه زمانی', 'زمان حرکت، ملاقات یا ارائه خدمت.'],
            ['پیشنهاد و قیمت', 'بستهٔ خدماتی و هزینهٔ مربوط به همان بسته، با واحد پول مشخص.'],
            ['ظرفیت و دسترسی', 'آیا خدمت در یک تاریخ مشخص قابل ارائه است یا نه.'],
          ]
          : [
            ['Organization','Legal/company profile'],
            ['Service','Business service type and unpublished details'],
            ['Destination','Approved places served by the business'],
            ['Schedule','Departures, visits and service times'],
            ['Offer and price','Service package and stated currency/price'],
            ['Availability','Whether a service can be provided on a specified date'],
          ]
        ).map(([name,description]) => <div key={name}><dt>{name}</dt><dd>{description}</dd></div>)}
      </dl>
      {orgId&&<section className="partner-forms">
      <label>{t.service}<select data-testid="partner-service-select" value={serviceId} onChange={e=>setServiceId(e.target.value)}><option value="">{t.select}</option>{data.services.map(s=><option key={String(s.service_id)} value={String(s.service_id)}>{String(s.display_name||s.service_type)} · {statusLabel(String(s.status),locale)}</option>)}</select></label>
      {!data.services.length&&<p role="status">{locale==='fa-IR'?'برای افزودن زمان‌بندی، پیشنهاد یا قیمت، ابتدا خدمت نخست را ثبت کنید.':locale==='ar'?'أضف الخدمة الأولى قبل إدخال الجدول أو العرض أو السعر.':'Add your first service before creating schedules, offers or prices.'}</p>}
      <form className="partner-card" onSubmit={e=>{e.preventDefault();void submit(async()=>{if(!serviceId||!destinationId)throw new Error();await api(`/organizations/${orgId}/services/${serviceId}/destinations`,{destination_id:Number(destinationId),relation_type:destinationRelation,evidence_note:destinationEvidence||null});setDestinationEvidence('');});}}>
        <h2>{t.linkDestination}</h2>
        <label>{t.destination}<select value={destinationId} onChange={e=>setDestinationId(e.target.value)} required><option value="">{t.select}</option>{publishedPlaces.map(place=><option key={place.destination_id} value={place.destination_id}>{place.canonical_name} · {place.city_name||place.province_name}</option>)}</select></label>
        {publishedPlaces.length===0&&<p role="status">{locale==='fa-IR'?'مقصد منتشرشده‌ای برای اتصال در دسترس نیست.':'No published destinations are available to link.'}</p>}
        <label>{t.relation}<select value={destinationRelation} onChange={e=>setDestinationRelation(e.target.value)}><option value="at">{locale==='fa-IR'?'در محل':'At this place'}</option><option value="serves">{locale==='fa-IR'?'خدمت‌رسانی به':'Serves this place'}</option><option value="near">{locale==='fa-IR'?'نزدیک':'Nearby'}</option><option value="route_endpoint">{locale==='fa-IR'?'نقطه مسیر':'Route endpoint'}</option></select></label>
        <label>{t.evidenceNote}<input value={destinationEvidence} onChange={e=>setDestinationEvidence(e.target.value)} maxLength={1000}/></label>
        <button className="primary" type="submit" disabled={!serviceId||!destinationId}>{t.createLink}</button>
        {!!data.destinations.length&&<ul>{data.destinations.map((item,index)=><li key={`${item.service_id}-${item.destination_id}-${index}`}>{String(item.canonical_name)} · {relationLabel(String(item.relation_type),locale)} · {statusLabel(String(item.status),locale)}</li>)}</ul>}
      </form>
      {form(editingScheduleId?t.edit:t.schedule,<><label>{t.scheduleType}<select value={scheduleType} onChange={e=>setScheduleType(e.target.value as typeof scheduleType)}><option value="opening_window">{scheduleTypeLabel('opening_window',locale)}</option><option value="departure">{scheduleTypeLabel('departure',locale)}</option><option value="appointment">{scheduleTypeLabel('appointment',locale)}</option><option value="event">{scheduleTypeLabel('event',locale)}</option><option value="other">{scheduleTypeLabel('other',locale)}</option></select></label><label>{t.timezone}<input value={scheduleTimezone} onChange={e=>setScheduleTimezone(e.target.value)} maxLength={80}/></label><label>{t.starts}<input type="datetime-local" value={scheduleStarts} onChange={e=>setScheduleStarts(e.target.value)}/></label><label>{t.ends}<input type="datetime-local" value={scheduleEnds} onChange={e=>setScheduleEnds(e.target.value)}/></label></>,()=>void submit(async()=>{if(!serviceId)throw new Error();const current=data.schedules.find(item=>item.schedule_id===editingScheduleId);const body={service_id:serviceId,schedule_type:scheduleType,timezone:scheduleTimezone||null,starts_at:scheduleStarts?localScheduleInstant(scheduleStarts,scheduleTimezone):null,ends_at:scheduleEnds?localScheduleInstant(scheduleEnds,scheduleTimezone):null,recurrence:current?.recurrence??null,observed_at:new Date().toISOString(),valid_until:current?.valid_until??null};const r=editingScheduleId?await api(`/organizations/${orgId}/schedules/${editingScheduleId}`,body,'PUT'):await api(`/organizations/${orgId}/schedules`,body);setScheduleId(String(r.schedule_id));setEditingScheduleId('');},t.saved),editingScheduleId?t.save:t.createSchedule,!serviceId)}
      {!!data.schedules.length&&<ul className="partner-record-list">{data.schedules.map(schedule=><li key={String(schedule.schedule_id)}><span><strong>{scheduleTypeLabel(String(schedule.schedule_type),locale)}</strong><small>{statusLabel(String(schedule.status),locale)} · {typeof schedule.timezone==='string'?schedule.timezone:''}</small></span><button type="button" className="secondary" disabled={!['draft','submitted','withdrawn','expired'].includes(String(schedule.status))} title={!['draft','submitted','withdrawn','expired'].includes(String(schedule.status))?(locale==='fa-IR'?'زمان‌بندی تأییدشده از این فرم قابل ویرایش نیست.':'Approved schedules are locked for editing here.'):undefined} onClick={()=>{const tz=typeof schedule.timezone==='string'?schedule.timezone:'Asia/Tehran';setEditingScheduleId(String(schedule.schedule_id));setScheduleId(String(schedule.schedule_id));setServiceId(String(schedule.service_id));setScheduleType(String(schedule.schedule_type) as typeof scheduleType);setScheduleTimezone(tz);setScheduleStarts(localDateTimeValue(schedule.starts_at,tz));setScheduleEnds(localDateTimeValue(schedule.ends_at,tz));}}>{t.edit}</button></li>)}</ul>}
      <label>{t.schedule}<select data-testid="partner-schedule-select" value={scheduleId} onChange={e=>setScheduleId(e.target.value)}><option value="">{t.select}</option>{data.schedules.filter(s=>s.service_id===serviceId).map(s=><option key={String(s.schedule_id)} value={String(s.schedule_id)}>{scheduleTypeLabel(String(s.schedule_type),locale)} · {statusLabel(String(s.status),locale)}</option>)}</select></label>
      {form(editingOfferId?t.edit:t.offer,<label>{t.offerType}<input value={offerType} onChange={e=>setOfferType(e.target.value)} required maxLength={80}/></label>,()=>void submit(async()=>{if(!serviceId)throw new Error();const body={service_id:serviceId,schedule_id:scheduleId||null,offer_type:offerType};const r=editingOfferId?await api(`/organizations/${orgId}/offers/${editingOfferId}`,body,'PUT'):await api(`/organizations/${orgId}/offers`,body);setOfferId(String(r.offer_id));setEditingOfferId('');},t.saved),editingOfferId?t.save:t.createOffer,!serviceId)}
      {!!data.offers.length&&<ul className="partner-record-list">{data.offers.map(offer=><li key={String(offer.offer_id)}><span><strong>{String(offer.offer_type)}</strong><small>{statusLabel(String(offer.status),locale)}</small></span><button type="button" className="secondary" disabled={!['draft','submitted','withdrawn','rejected'].includes(String(offer.status))} title={!['draft','submitted','withdrawn','rejected'].includes(String(offer.status))?(locale==='fa-IR'?'پیشنهاد منتشرشده از این فرم قابل ویرایش نیست.':'Published offers are locked for editing here.'):undefined} onClick={()=>{setEditingOfferId(String(offer.offer_id));setOfferId(String(offer.offer_id));setServiceId(String(offer.service_id));setScheduleId(typeof offer.schedule_id==='string'?offer.schedule_id:'');setOfferType(String(offer.offer_type));}}>{t.edit}</button></li>)}</ul>}
      <label>{t.offer}<select data-testid="partner-offer-select" value={offerId} onChange={e=>setOfferId(e.target.value)}><option value="">{t.select}</option>{data.offers.filter(o=>o.service_id===serviceId).map(o=><option key={String(o.offer_id)} value={String(o.offer_id)}>{String(o.offer_type)} · {statusLabel(String(o.status),locale)}</option>)}</select></label>
      {form(t.price,<><label>{t.amount}<input id="partner-price-amount" type="number" min="0" step="0.01" required/></label><label>{t.currency}<input id="partner-price-currency" pattern="[A-Z]{3}" maxLength={3} required/></label><label>{t.denomination}<input id="partner-price-denomination" maxLength={80} required/></label><label>{t.unit}<input id="partner-price-unit" maxLength={80} required/></label><p>{locale==='fa-IR'?'ارز، مقیاس مبلغ و مبنای قیمت را دقیق وارد کنید؛ تومان و ریال به‌طور خودکار تبدیل نمی‌شوند.':locale==='ar'?'أدخل العملة ومقياس المبلغ وأساس التسعير بدقة؛ لا يتم التحويل التلقائي بين العملات.':'Enter the exact currency, denomination and pricing unit. Values are never converted implicitly.'}</p><p>{locale==='fa-IR'?'قیمت‌ها به‌صورت مشاهدهٔ تاریخ‌دار افزوده می‌شوند و سابقهٔ قبلی تغییر نمی‌کند.':locale==='ar'?'تُضاف الأسعار كملاحظات مؤرخة ولا تُستبدل السجلات السابقة.':'Prices are timestamped observations; previous observations remain in history.'}</p></>,()=>void submit(async()=>{if(!offerId)throw new Error();await api(`/organizations/${orgId}/prices`,{offer_id:offerId,price_state:'known',amount:Number((document.getElementById('partner-price-amount') as HTMLInputElement).value),currency:(document.getElementById('partner-price-currency') as HTMLInputElement).value,denomination:(document.getElementById('partner-price-denomination') as HTMLInputElement).value,unit:(document.getElementById('partner-price-unit') as HTMLInputElement).value,observed_at:new Date().toISOString()});}),t.addObservation,!offerId)}
      {!!data.prices.length&&<section aria-label={t.priceHistory}><h3>{t.priceHistory}</h3><ul>{data.prices.filter(price=>price.offer_id===offerId).map(price=><li key={String(price.price_id)}>{String(price.amount??'—')} {String(price.currency??'')} · {String(price.denomination??'')} / {String(price.unit??'')} · {typeof price.observed_at==='string'?new Date(price.observed_at).toLocaleString(locale):'—'} · {statusLabel(String(price.price_state),locale)}</li>)}</ul></section>}
      {form(t.availability,<><label>{t.occurrence}<input type="datetime-local" value={occurrence} onChange={e=>setOccurrence(e.target.value)} required/></label><label>{t.state}<select id="partner-availability-state"><option value="unknown">{statusLabel('unknown',locale)}</option><option value="available">{statusLabel('available',locale)}</option><option value="limited">{statusLabel('limited',locale)}</option><option value="unavailable">{statusLabel('unavailable',locale)}</option></select></label><p>{locale==='fa-IR'?'هر ثبت، مشاهده‌ای با زمان اعتبار محدود است؛ ظرفیت یا وضعیت آینده تضمین نمی‌شود.':locale==='ar'?'كل إدخال ملاحظة محدودة الصلاحية ولا يضمن التوافر المستقبلي.':'Each entry is a time-limited observation, not a guarantee of future availability.'}</p></>,()=>void submit(async()=>{if(!offerId||!scheduleId||!occurrence)throw new Error();const now=new Date().toISOString();await api(`/organizations/${orgId}/availability`,{offer_id:offerId,schedule_id:scheduleId,occurrence_starts_at:localScheduleInstant(occurrence,typeof data.schedules.find(item=>item.schedule_id===scheduleId)?.timezone==='string'?String(data.schedules.find(item=>item.schedule_id===scheduleId)?.timezone):'Asia/Tehran'),availability_state:(document.getElementById('partner-availability-state') as HTMLSelectElement).value,observed_at:now,valid_from:now,valid_until:new Date(Date.now()+86400000).toISOString()});setOccurrence('');}),t.addObservation,!offerId||!scheduleId)}
      {!!data.availability.length&&<section aria-label={t.availability}><h3>{t.availability}</h3><ul>{data.availability.filter(item=>item.offer_id===offerId).map(item=><li key={String(item.snapshot_id)}>{statusLabel(String(item.availability_state),locale)} · {typeof item.occurrence_starts_at==='string'?new Date(item.occurrence_starts_at).toLocaleString(locale):'—'} · {locale==='fa-IR'?'مشاهده':'Observed'} {typeof item.observed_at==='string'?new Date(item.observed_at).toLocaleString(locale):'—'} · {locale==='fa-IR'?'اعتبار تا':'Valid until'} {typeof item.valid_until==='string'?new Date(item.valid_until).toLocaleString(locale):'—'}</li>)}</ul></section>}
      </section>}
    </details>
  </main>;
}
