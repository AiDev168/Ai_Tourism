import type { Locale } from '../i18n/messages';

export type Field<T> = { value: T | null; status: 'extracted' | 'unknown' | 'ambiguous'; evidence: string | null; candidates?: T[] };
export type TripRequirements = {
  requestText: string; locale: Locale; destinations: Field<string[]>; origin: Field<string>; durationDays: Field<number>;
  relativeStartDate: Field<{ offset_days: number; anchor_date: string | null; timezone: string | null }>;
  travelDates: Field<{ start: string; end: string }>; travelerCount: Field<number>;
  accessibility: Field<Array<'wheelchair_access' | 'step_free_access'>>;
  budget: Field<{ amount: number; currency: string | null; unit: string; raw: string; scale?: string | null; currency_status?: 'known' | 'unknown' | 'ambiguous' }>;
  interests: Field<string[]>; softPreferences: Field<string[]>; constraints: Field<string[]>; extractionStatus: 'ready' | 'needs_clarification';
  missingRequired: Array<'destination' | 'duration'>; ambiguousRequired: Array<'destination' | 'duration'>;
  clarificationFields?: string[]; confirmationRequired: string[]; destinationVerification: 'user_input_unverified';
};

type RequirementEnvelope<T> = { status?: 'known' | 'missing' | 'ambiguous'; value?: T | null; evidence_span?: { start: number; end: number; text: string } | null; candidates?: T[] };
export type TripRequirementsV1 = {
  contract_version: 'trip-requirements-v1'; original_text: string; locale: Locale;
  fields: {
    destination: RequirementEnvelope<string>; origin: RequirementEnvelope<string>;
    relative_start_date: RequirementEnvelope<{ offset_days: number; anchor_date: string | null; timezone: string | null }>;
    duration_days: RequirementEnvelope<number>; travel_dates: RequirementEnvelope<{ start: string; end: string }>;
    travelers: RequirementEnvelope<number>; budget: RequirementEnvelope<{ amount: string; scale: string | null; currency: string | null; currency_status: 'known' | 'unknown' | 'ambiguous'; raw: string }>;
    interests: RequirementEnvelope<string[]>; hard_constraints: RequirementEnvelope<string[]>; accessibility: RequirementEnvelope<string[]>;
  };
  clarification: { missing_fields: string[]; ambiguous_fields: string[]; question_fields: string[] };
};

/** Convert the server-authoritative typed contract without reinterpreting text. */
export function tripRequirementsV1ToTripRequirements(value: TripRequirementsV1): TripRequirements {
  const project = <T, U = T>(field: RequirementEnvelope<T>, mapValue: (input: T) => U = (input => input as unknown as U), mapCandidates: (input: T) => U = mapValue): Field<U> => ({
    value: field.value === undefined || field.value === null ? null : mapValue(field.value),
    status: field.status === 'known' ? 'extracted' : field.status === 'ambiguous' ? 'ambiguous' : 'unknown',
    evidence: field.evidence_span?.text ?? null,
    ...(field.candidates?.length ? { candidates: field.candidates.map(mapCandidates) } : {}),
  });
  const fields = value.fields;
  const toBudget = (money: NonNullable<typeof fields.budget.value>) => ({
    amount: Number(money.amount), currency: money.currency,
    unit: money.scale ?? 'unit', raw: money.raw,
    scale: money.scale, currency_status: money.currency_status,
  });
  const budget = project(fields.budget, toBudget);
  const missingRequired = value.clarification.missing_fields.flatMap(field => field === 'duration_days' ? ['duration' as const] : field === 'destination' ? ['destination' as const] : []);
  const ambiguousRequired = value.clarification.ambiguous_fields.flatMap(field => field === 'duration_days' ? ['duration' as const] : field === 'destination' ? ['destination' as const] : []);
  return {
    requestText: value.original_text, locale: value.locale,
    destinations: project(fields.destination, name => [name], name => [name]),
    origin: project(fields.origin), relativeStartDate: project(fields.relative_start_date),
    durationDays: project(fields.duration_days),
    travelDates: project(fields.travel_dates), travelerCount: project(fields.travelers),
    accessibility: project(fields.accessibility) as TripRequirements['accessibility'],
    budget, interests: project(fields.interests), softPreferences: { value: null, status: 'unknown', evidence: null },
    constraints: project(fields.hard_constraints),
    extractionStatus: value.clarification.question_fields.length ? 'needs_clarification' : 'ready',
    missingRequired, ambiguousRequired, clarificationFields: value.clarification.question_fields,
    confirmationRequired: [], destinationVerification: 'user_input_unverified',
  };
}
const configuredDurationLimit = Number(import.meta.env?.VITE_MAX_TRIP_DURATION_DAYS);
export const MAX_TRIP_DURATION_DAYS = Number.isInteger(configuredDurationLimit) && configuredDurationLimit > 0 ? configuredDurationLimit : 365;
export type TripIntakeResult = { kind: 'invalid'; reason: 'request-required' | 'request-too-long' | 'duration-too-long' } | { kind: 'clarification'; requirements: TripRequirements } | { kind: 'ready'; requirements: TripRequirements };

const digits: Record<string,string> = Object.fromEntries([...Array(10)].flatMap((_,i)=>[[String.fromCharCode(0x06f0+i),String(i)],[String.fromCharCode(0x0660+i),String(i)]]));
const normalize = (s:string) => Array.from(s,c=>digits[c]??c).join('').replace(/[\u0640\u200c]/g,' ').replace(/[\u064B-\u065F\u0670]/g,'').replace(/يوما(?=$|[^\p{L}])/gu,'يوم').normalize('NFC').replace(/\s+/g,' ');
const words: Record<string,number> = {
  one:1,two:2,three:3,four:4,five:5,six:6,seven:7,eight:8,nine:9,ten:10,eleven:11,twelve:12,thirteen:13,fourteen:14,fifteen:15,sixteen:16,seventeen:17,eighteen:18,nineteen:19,twenty:20,thirty:30,forty:40,fifty:50,sixty:60,seventy:70,eighty:80,ninety:90,
  'یک':1,'دو':2,'سه':3,'چهار':4,'پنج':5,'شش':6,'شیش':6,'هفت':7,'هشت':8,'نه':9,'ده':10,'یازده':11,'دوازده':12,'سیزده':13,'چهارده':14,'پانزده':15,'شانزده':16,'هفده':17,'هجده':18,'نوزده':19,'بیست':20,'سی':30,'چهل':40,'پنجاه':50,'شصت':60,'هفتاد':70,'هشتاد':80,'نود':90,'صد':100,
  واحد:1,واحداً:1,واحدا:1,اثنان:2,اثنين:2,اثنتين:2,ثلاث:3,ثلاثة:3,أربعة:4,اربعة:4,أربع:4,اربعه:4,خمسة:5,خمس:5,ستة:6,ست:6,سبعة:7,سبع:7,ثمانية:8,ثمان:8,تسعة:9,تسع:9,عشرة:10,عشر:10,أحد:1,احد:1,عشرون:20,ثلاثون:30,أربعون:40,اربعون:40,خمسون:50,ستون:60,سبعون:70,ثمانون:80,تسعون:90,مائة:100,مئة:100,
};
const arabicObliqueNumberWords: Record<string, number> = { عشرين:20, ثلاثين:30, اربعين:40, أربعين:40, خمسين:50, ستين:60, سبعين:70, ثمانين:80, تسعين:90 };
function numberValue(raw:string):number|null {
  const value=normalize(raw).trim().toLocaleLowerCase(); if (/^\d+$/.test(value)) return Number(value);
  if (value==='أسبوعين'||value==='اسبوعين') return 2;
  const tokens=value.split(/[\s-]+/); let total=0, current=0;
  for (const rawToken of tokens) { if(rawToken==='and'||rawToken==='و')continue;const withoutConjunction=rawToken.startsWith('و')?rawToken.slice(1):rawToken;const token=words[withoutConjunction]!==undefined||arabicObliqueNumberWords[withoutConjunction]!==undefined?withoutConjunction:rawToken;const n=words[token]??arabicObliqueNumberWords[token]; if(n===undefined)return null; if(n===100){current=(current||1)*100;} else if(n>=20&&n<100){current+=n;} else current+=n; }
  total+=current; return total||null;
}
const numberWordPattern=[...new Set([...Object.keys(words),...Object.keys(arabicObliqueNumberWords)])].sort((a,b)=>b.length-a.length).map(word=>word.replace(/[.*+?^${}()|[\\]\\]/g,'\\$&')).join('|');
const numberTokenPattern=`(?:و)?(?:${numberWordPattern})`;
const numPattern=`\\d+|${numberTokenPattern}(?:[-\\s]+(?:(?:and|و)\\s*)?${numberTokenPattern}){0,2}`;
const durationRegex=new RegExp(`(?:^|[^\\p{L}\\p{N}])(${numPattern})[-\\s]*(days?|day|روزه|روز|أيام|ايام|يوم|weeks?|week|هفته|أسبوعين|اسبوعين|أسبوع|اسبوع)(?=$|[^\\p{L}\\p{N}])`,'giu');
export function extractDurationDays(requestText:string):number|null {
  const vals=durationSpans(requestText).map(span=>span.days).filter(Boolean);
  if(vals.length&&new Set(vals).size===1)return vals[0];
  return null;
}
const durationSpans=(text:string)=>{const normalized=normalize(text);const spans=[...normalized.matchAll(durationRegex)].filter(m=>{const start=m.index??0;const end=start+m[0].length;const before=normalized.slice(Math.max(0,start-12),start);const after=normalized.slice(end,end+18);return !/(?:از\s*|\bin\s*)$/iu.test(before)&&!/^\s*(?:دیگه|دیگر|بعد|later|from\s+now)(?:\s|$)/iu.test(after);}).map(m=>({days:(numberValue(m[1])??0)*(/week|هفته|أسبوع|اسبوع/iu.test(m[2])?7:1),raw:m[0],index:m.index??0}));if(!spans.some(s=>/week|هفته|أسبوع|اسبوع/iu.test(s.raw))){const twoWeeks=normalized.match(/(?:^|\s)(?:أسبوعين|اسبوعين)(?:$|\s)/u);const oneWeek=normalized.match(/(?:^|\s)(?:أسبوع|اسبوع)(?:$|\s)/u);if(twoWeeks)spans.push({days:14,raw:twoWeeks[0],index:twoWeeks.index??0});else if(oneWeek)spans.push({days:7,raw:oneWeek[0],index:oneWeek.index??0});}return spans;};
const cleanPlace=(s:string)=>s.replace(/^[\s,،؛:]+|[\s,،؛:.!?؟]+$/g,'').replace(/\s+/g,' ').trim();
const genericPlace=/^(?:a city|the city|city|a town|town|somewhere|یک شهر|شهر|یه شهر|مدينة|مدينة ما|بلدة)$/iu;
function extractPlaces(source:string, locale:Locale, spans:ReturnType<typeof durationSpans>):{places:Field<string[]>;origin:Field<string>} {
  void locale;
  const text=normalize(source); const originMatch=text.match(/(?:from|از|من)\s+(.{1,70}?)\s+(?:to|به|إلى|الى)\s+/iu);
  let origin:Field<string>={value:null,status:'unknown',evidence:null};
  if(originMatch){const candidate=cleanPlace(originMatch[1].replace(/^(?:tehran|تهران|طهران)$/iu,'$&'));if(candidate&&!genericPlace.test(candidate))origin={value:candidate,status:'extracted',evidence:originMatch[0]};}
  // A small deterministic alias set covers commonly requested destinations; this is
  // extraction only, never verification. Unknown places still use the syntax parser below.
  const contextual=/(?:travel|trip|journey|visit|سفر|مسافرت|رحلة|السفر|أرید|میخواهم|می‌خواهم|می‌خوام|برم|أريد|اريد)/iu.test(text)||spans.length>0;
  if(!contextual)return{origin,places:{value:null,status:'unknown',evidence:null}};
  const known=/\b(Shiraz|Kashan|Isfahan|Esfahan|Tehran|Yazd|Qeshm)\b|شیراز|کاشان|اصفهان|تهران|طهران|یزد|قشم|شيراز|كاشان/giu;
  const found=[...text.matchAll(known)].filter(m=>!(origin.value&&m[0].toLocaleLowerCase()===origin.value.toLocaleLowerCase())).map(m=>({name:m[0],index:m.index??0}));
  if(found.length&&/(?:\bor\b|\bیا\b|\bأو\b)/iu.test(text))return{origin,places:{value:null,status:'ambiguous',evidence:null,candidates:[found.map(x=>x.name)]}};
  if(found.length){const unique=found.filter((x,i)=>found.findIndex(y=>y.name.toLocaleLowerCase()===x.name.toLocaleLowerCase())===i).map(x=>x.name);return{origin,places:{value:unique,status:'extracted',evidence:unique.join(' → ')}};}
  const candidates:string[]=[];
  const patterns=[/(?:to|in|visit|travel\s+to|trip\s+to)\s+(.{1,100})/giu,/(?:به|در)\s+(.{1,100})/gu,/(?:إلى|الى|في)\s+(.{1,100})/gu];
  if(contextual) for(const p of patterns){for(const m of text.matchAll(p)){let raw=m[1];
    raw=raw.replace(new RegExp(`(?:for|برای|لمدة)?\\s*${numPattern}[-\\s]*(?:days?|day|روزه|روز|أيام|ايام|يوم|weeks?|week|هفته|أسبوعين|اسبوعين|أسبوع|اسبوع).*$`,'iu'),'');
    raw=raw.split(/(?:\bfor\b|\bwith\b|\btravel\b|\btrip\b|\bjourney\b|\bvisit\b|\bI\s+want\b|\bI\s+would\b|\bwith\s+family\b|،|,|؛|;|\.|\?|!|؟|با خانواده|همراه خانواده|برای|سفر|مسافرت|می کنم|می کنم|مي کنم|ميکنم|ميزانية|ميزانیه|بودجه|أحب|احب|عائلية|به همراه)/iu)[0];
    const places=raw.split(/\s+(?:and then|and|و سپس|و|ثم)\s+/iu).map(cleanPlace);
    for(const place of places)if(!candidates.some(x=>x.toLocaleLowerCase()===place.toLocaleLowerCase()))candidates.push(place);
  }}
  // Explicit sequence connectors identify ordered destinations; only retain their city-sized spans.
  if(candidates.length>1 && origin.value) candidates.shift();
  if(/\b(?:or)\b|\bیا\b|\bأو\b/iu.test(text) && candidates.length) return {origin,places:{value:null,status:'ambiguous',evidence:null,candidates:[candidates]}};
  return candidates.length?{origin,places:{value:candidates,status:'extracted',evidence:candidates.join(' → ')}}:{origin,places:{value:null,status:'unknown',evidence:null}};
}
function explicitCount(text:string):number|null {const n=`(${numPattern})`;const m=normalize(text).match(new RegExp(`${n}\\s*(?:people|travelers|travellers|نفر|مسافر|أشخاص|اشخاص|أفراد|افراد)`,'iu'));return m?numberValue(m[1]):null;}
function explicitDateRange(text:string):TripRequirements['travelDates'] {const m=normalize(text).match(/(\d{4}-\d{2}-\d{2})\s*(?:to|through|تا|إلى|الى|حتى|—|–)\s*(\d{4}-\d{2}-\d{2})/iu);if(!m)return{value:null,status:'unknown',evidence:null};const valid=(s:string)=>{const d=new Date(`${s}T00:00:00Z`);return !Number.isNaN(d.valueOf())&&d.toISOString().slice(0,10)===s;};if(!valid(m[1])||!valid(m[2])||m[1]>m[2])return{value:null,status:'ambiguous',evidence:m[0],candidates:[]};return{value:{start:m[1],end:m[2]},status:'extracted',evidence:m[0]};}
function explicitAccessibilityNeeds(text:string):TripRequirements['accessibility'] {
 const normalized=normalize(text);
 const wheelchair=/(?:\bwheelchair(?:\s+|-)?(?:access|accessible|accessibility)\b|دسترسی\s+(?:با\s+)?ویلچر|مناسب\s+(?:برای\s+)?ویلچر|(?:إمكانية\s+الوصول|وصول|مناسب)\s+(?:بالكراسي\s+المتحركة|للكراسي\s+المتحركة))/iu.test(normalized);
 const stepFree=/(?:\bstep[- ]free(?:\s+(?:access|entrance|route))?\b|\bno\s+stairs\b|\bwithout\s+stairs\b|بدون\s+پله(?:‌ها)?|ورودی\s+بدون\s+پله|(?:بدون|دون)\s+(?:درجات|سلالم))/iu.test(normalized);
 const value:Array<'wheelchair_access'|'step_free_access'>=[];
 if(wheelchair)value.push('wheelchair_access');
 if(stepFree)value.push('step_free_access');
 return value.length?{value,status:'extracted',evidence:null}:{value:null,status:'unknown',evidence:null};
}
function parseBudget(text:string):TripRequirements['budget'] {const normalized=normalize(text);const markers=[...normalized.matchAll(/(?:\u0647\u0632\u06cc\u0646\u0647|\u0628\u0648\u062f\u062c\u0647|\u062e\u0631\u062c|cost|budget|spend)/giu)];const pattern=/([\d,]+(?:\.\d+)?)(?:\s*(\u0645\u06cc\u0644\u06cc\u0648\u0646|million|\u0645\u0644\u064a\u0648\u0646|\u0647\u0632\u0627\u0631|thousand|\u0645\u0644\u064a\u0627\u0631\u062f|billion))?(?:\s*(\u062a\u0648\u0645\u0627\u0646|\u0631\u06cc\u0627\u0644|IRR|toman|rial|USD|\u062f\u0644\u0627\u0631|EUR|AED|\u062f\u0631\u0647\u0645|\u0631\.\s*\u0633))?/giu;const matches=[...normalized.matchAll(pattern)];const nearby=matches.filter(m=>m[1]&&((!markers.length&&m[3])||markers.some(marker=>Math.min(Math.abs((m.index??0)-(marker.index??0)),Math.abs((m.index??0)+m[0].length-(marker.index??0)))<=48)));const m=nearby.sort((a,b)=>{const distance=(item:RegExpMatchArray)=>Math.min(...markers.map(marker=>Math.min(Math.abs((item.index??0)-(marker.index??0)),Math.abs((item.index??0)+item[0].length-(marker.index??0)))));return Number(Boolean(b[2]||b[3]))-Number(Boolean(a[2]||a[3]))||distance(a)-distance(b);})[0];if(!m)return{value:null,status:'unknown',evidence:null};const amount=Number(m[1].replaceAll(',',''));const scale=m[2]??'';const currencyText=m[3]??'';const currency=/(?:\u0631\s*\.\s*\u0633)/iu.test(currencyText)?'SAR':/(?:IRR|\u0631\u06cc\u0627\u0644|rial)/iu.test(currencyText)?'IRR':/(?:toman|\u062a\u0648\u0645\u0627\u0646)/iu.test(currencyText)?null:/(?:USD|\u062f\u0644\u0627\u0631)/iu.test(currencyText)?'USD':/(?:EUR)/iu.test(currencyText)?'EUR':/(?:AED|\u062f\u0631\u0647\u0645|\u0631\.\s*\u0633)/iu.test(currencyText)?'AED':null;const raw=m[0].trim();return{value:{amount,currency,unit:[scale,currencyText].filter(Boolean).join(' ')||'unknown',raw},status:'extracted',evidence:raw};}
function extractedText(text:string, trigger:RegExp):Field<string[]> {const m=normalize(text).match(trigger);return m?{value:[cleanPlace(m[1])],status:'extracted',evidence:m[0]}:{value:null,status:'unknown',evidence:null};}
function directedText(text:string, patterns:RegExp[]):Field<string[]> {
 const normalized=normalize(text);
 const matches=patterns.flatMap(pattern=>[...normalized.matchAll(pattern)]).map(match=>({value:cleanPlace(match[1]), evidence:match[0]}))
  .filter(match=>match.value.length>0);
 const unique=[...new Map(matches.map(match=>[match.value.toLocaleLowerCase(),match])).values()];
 return unique.length?{value:unique.map(match=>match.value),status:'extracted',evidence:unique.map(match=>match.evidence).join(' / ')}:{value:null,status:'unknown',evidence:null};
}
const directiveEnd='(?=\\s+(?:but\\b|however\\b|and\\s+must\\b|during\\b|for\\b|اما\\s|ولی\\s|لكن\\s|لمدة\\s|برای\\s)|[.!?؟؛;]|$)';
function explicitSoftPreferences(text:string):Field<string[]> {
 return directedText(text,[
  new RegExp(`\\b(?:i\\s+)?(?:prefer|would\\s+like)\\s+(.+?)${directiveEnd}`,'giu'),
  new RegExp(`(?:ترجیح\\s+می\\s+دهم|ترجیح\\s+میدهم)\\s+(.+?)${directiveEnd}`,'gu'),
  new RegExp(`(?:أفضل|افضل)\\s+(.+?)${directiveEnd}`,'gu'),
 ]);
}
function explicitHardConstraints(text:string):Field<string[]> {
 const normalized=normalize(text);
 const values:string[]=[];
 const hardMarkers=[
  /\b(?:must(?:\s+not)?|need(?:\s+to)?|required(?:\s+to)?|do\s+not)\s+(.+?)(?=\s+(?:but|however|during|for)\b|[.!?;]|$)/giu,
  /(?:باید|ضروری(?:\s+است)?|نباید)\s+(.+?)(?=\s+(?:اما|ولی|برای)\s|[.!؟؛]|$)/gu,
  /(?:يجب(?:\s+أن)?|ضروري|لا\s+(?:أريد|اريد))\s+(.+?)(?=\s+(?:لكن|لمدة|في)\s|[.!؟؛]|$)/gu,
 ];
 for(const pattern of hardMarkers) for(const match of normalized.matchAll(pattern)) if(match[1]) values.push(cleanPlace(match[1]));
 const surface=/(paved\s+paths?|مسیرهای\s*سنگ\s*فرش|طرقا\s*معبدة)/giu;
 for(const match of normalized.matchAll(surface)) {
  const before=normalized.slice(Math.max(0,(match.index??0)-24),match.index??0);
  if(/(?:prefer|would like|ترجیح\s*می\s*دهم|أفضل|افضل)\s*$/iu.test(before)) continue;
  const after=normalized.slice((match.index??0)+match[0].length,(match.index??0)+match[0].length+20);
  if(/(?:want|أريد|اريد)\s*$/iu.test(before)||/می\s*خواهم/u.test(after)) values.push(cleanPlace(match[0]));
  else if(/paved|surface|terrain/iu.test(match[0])) values.push(cleanPlace(match[0]));
 }
 const unique=[...new Set(values.filter(Boolean))];
 return unique.length?{value:unique,status:'extracted',evidence:unique.join(' / ')}:{value:null,status:'unknown',evidence:null};
}
function explicitRelativeStart(text:string):TripRequirements['relativeStartDate'] {
 const match=normalize(text).match(new RegExp(`(?:\\u0627\\u0632\\s*)?(${numPattern})\\s*(?:\\u0631\\u0648\\u0632|days?)\\s*(?:\\u062f\\u06cc\\u06af\\u0647|\\u062f\\u06cc\\u06af\\u0631|\\u0628\\u0639\\u062f|later|from\\s+now)`, 'iu'));
 if(!match)return{value:null,status:'unknown',evidence:null};
 const offset=numberValue(match[1]);
 return offset!==null&&offset>=0&&offset<=365?{value:{offset_days:offset,anchor_date:null,timezone:null},status:'extracted',evidence:match[0]}:{value:null,status:'unknown',evidence:match[0]};
}
export function createTripRequirements(input:{requestText:string;locale:Locale;maxDurationDays?:number}):TripIntakeResult {
 const original=input.requestText; const text=normalize(original).trim(); if(!text)return{kind:'invalid',reason:'request-required'};if(text.length>1200)return{kind:'invalid',reason:'request-too-long'};
 const max=input.maxDurationDays??MAX_TRIP_DURATION_DAYS;
 const spans=durationSpans(text);const durations=[...new Set(spans.map(s=>s.days).filter(Boolean))];if(durations.some(d=>d>max))return{kind:'invalid',reason:'duration-too-long'};
 const duration:Field<number>=durations.length>1?{value:null,status:'ambiguous',evidence:spans.map(s=>s.raw).join(' / '),candidates:durations}:durations.length?{value:durations[0],status:'extracted',evidence:spans[0].raw}:{value:null,status:'unknown',evidence:null};
 const {places,origin}=extractPlaces(text,input.locale,spans);
  const accessibility=explicitAccessibilityNeeds(text);
 const missingRequired:Array<'destination'|'duration'>=[];const ambiguousRequired:Array<'destination'|'duration'>=[];
 if(!places.value){(places.status==='ambiguous'?ambiguousRequired:missingRequired).push('destination');}if(!duration.value){(duration.status==='ambiguous'?ambiguousRequired:missingRequired).push('duration');}
 const interest=extractedText(text,/(?:interested in|love|enjoy|أحب|احب)\s+(.+?)(?:[.!؟؛،,;]|$)/iu);if(!interest.value){const historical=text.match(/(?:\u0645\u0646\u0627\u0637\u0642\s*\u062a\u0627\u0631\u06cc\u062e\u06cc|\u062c\u0627\u0647\u0627\u06cc\s*\u062a\u0627\u0631\u06cc\u062e\u06cc|\bhistorical\s+(?:areas|places|attractions)\b)/iu);if(historical)Object.assign(interest,{value:['historical_attractions'],status:'extracted',evidence:historical[0]});}{const end=text.indexOf(' علاقه دارم');const start=end>=0?text.lastIndexOf(' به ',end):-1;if(start>=0)Object.assign(interest,{value:[cleanPlace(text.slice(start+4,end))],status:'extracted',evidence:text.slice(start,end+12)});}
  const requirements:TripRequirements={requestText:original,locale:input.locale,destinations:places,origin,relativeStartDate:explicitRelativeStart(text),durationDays:duration,travelDates:explicitDateRange(text),travelerCount:(()=>{const n=explicitCount(text);return n?{value:n,status:'extracted' as const,evidence:text.match(new RegExp(`${n}\\s*(?:people|travelers|travellers|نفر|مسافر|أشخاص|اشخاص|أفراد|افراد)`,'iu'))?.[0]??null}:{value:null,status:'unknown' as const,evidence:null};})(),accessibility,budget:parseBudget(text),interests:interest,softPreferences:explicitSoftPreferences(text),constraints:explicitHardConstraints(text),extractionStatus:missingRequired.length||ambiguousRequired.length?'needs_clarification':'ready',missingRequired,ambiguousRequired,confirmationRequired:[],destinationVerification:'user_input_unverified'};
 return requirements.extractionStatus==='ready'?{kind:'ready',requirements}:{kind:'clarification',requirements};
}
