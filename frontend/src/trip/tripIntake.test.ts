import { describe, expect, it } from 'vitest';
import { createTripRequirements, extractDurationDays, inclusiveEndDate, mergeRequirementInterpretations, tripRequirementsV1ToTripRequirements, resolveRelativeTripDates, requirementsForPersistence } from './tripIntake';

const intake=(requestText:string,locale:'fa-IR'|'en-US'|'ar'='fa-IR')=>createTripRequirements({requestText,locale});
describe('Persian colloquial origin fallback', () => {
 it.each([
   ['از مشهد میخوام برم شیراز', 'مشهد'],
   ['من از بندر عباس می‌خواهم برم شیراز', 'بندر عباس'],
 ])('recognizes the stated departure in %s', (text, origin) => {
   const result = intake(text);
   if (result.kind === 'invalid') throw new Error('Unexpected invalid request');
   expect(result.requirements.origin.value).toBe(origin);
   expect(result.requirements.origin.source).toBe('fallback');
   expect(result.requirements.destinations.value).toContain('شیراز');
 });
 it('does not interpret tomorrow as a departure city', () => {
   const result = intake('از فردا میخوام برم شیراز');
   if (result.kind === 'invalid') throw new Error('Unexpected invalid request');
   expect(result.requirements.origin.value).toBeNull();
 });
});

describe('natural-language trip intake v2',()=>{
 it('keeps the owner Persian request as tomorrow, five travelers, historical Shiraz and five million TOMAN',()=>{
  const text='برای فردا برای 5 نفر برای بازدید از مناطق تاریخی شیراز برنامه ریزی سفر کن و هزینه ای که میخوایم بکنیم 5 میلیون تومان است';
  const result=intake(text);
  expect(result.kind).toBe('clarification');
  if(result.kind==='clarification'){
   const fields=result.requirements;
   expect(fields.requestText).toBe(text);
   expect(fields.destinations.value).toContain('شیراز');
   expect(fields.travelerCount.value).toBe(5);
   expect(fields.interests.value).toContain('historical_attractions');
   expect(fields.relativeStartDate.value?.offset_days).toBe(1);
   expect(fields.budget.value).toMatchObject({amount:5,currency:'TOMAN'});
   expect(fields.durationDays.value).toBeNull();
  }
 });
 it.each([
  ['سفر ۳ روزه به شیراز به همراه خانواده','fa-IR',3,'شیراز'],
  ['برای ۷ روز به کاشان سفر می‌کنم','fa-IR',7,'کاشان'],
  ['برای چهارده روز به اصفهان سفر می‌کنم','fa-IR',14,'اصفهان'],
  ['برای ۳۰ روز به شیراز سفر می‌کنم','fa-IR',30,'شیراز'],
  ['Travel from Tehran to Isfahan and then Shiraz for 90 days','en-US',90,'Isfahan'],
  ['A 7-day trip to Kashan','en-US',7,'Kashan'],
  ['رحلة لمدة ٧ أيام إلى شيراز','ar',7,'شيراز'],
  ['رحلة لمدة ثلاثة أيام إلى شيراز','ar',3,'شيراز'],
  ['دو هفته به کاشان سفر می‌کنم','fa-IR',14,'کاشان'],
  ['I want to visit Isfahan for ten days','en-US',10,'Isfahan'],
 ])('extracts required fields from %s', (text,locale,days,destination)=>{
  const result=intake(text,locale as 'fa-IR'|'en-US'|'ar');expect(result.kind).toBe('ready');if(result.kind==='ready'){expect(result.requirements.durationDays.value).toBe(days);expect(result.requirements.destinations.value?.[0]).toBe(destination);expect(result.requirements.requestText).toBe(text);expect(result.requirements.destinationVerification).toBe('user_input_unverified');}
 });
 it.each([['7 days',7],['۷ روز',7],['٧ أيام',7],['one week',7],['two weeks',14],['یک هفته',7],['دو هفته',14],['أسبوع',7],['أسبوعين',14],['سی روز',30]])('normalizes duration expression %s', (text,days)=>expect(extractDurationDays(text)).toBe(days));
 it('supports an explicit Persian destination sequence in order',()=>{const r=intake('می‌خواهم از تهران به اصفهان و سپس شیراز سفر کنم و ۷ روز بمانم');expect(r.kind).toBe('ready');if(r.kind==='ready')expect(r.requirements.destinations.value).toEqual(['اصفهان','شیراز']);});
 it('asks clarification for missing destination or duration and treats a city name alone as incomplete',()=>{expect(intake('شیراز')).toMatchObject({kind:'clarification',requirements:{missingRequired:['destination','duration']}});expect(intake('A quiet trip for 5 days','en-US')).toMatchObject({kind:'clarification',requirements:{missingRequired:['destination']}});expect(intake('I want to visit Shiraz','en-US')).toMatchObject({kind:'clarification',requirements:{missingRequired:['duration']}});});
 it('flags conflicting durations and alternative destinations for confirmation',()=>{expect(intake('سفر به شیراز برای ۷ روز و ۱۰ روز')).toMatchObject({kind:'clarification',requirements:{ambiguousRequired:['duration']}});expect(intake('Travel to Shiraz or Kashan for 7 days','en-US')).toMatchObject({kind:'clarification',requirements:{ambiguousRequired:['destination']}});});
 it('does not hide a conflict between an explicit day count and a standalone week',()=>expect(intake('Trip to Shiraz for 4 days and one week','en-US')).toMatchObject({kind:'clarification',requirements:{ambiguousRequired:['duration']}}));
 it('uses configurable technical maximum without a three-day cap',()=>{expect(createTripRequirements({requestText:'Trip to Shiraz for 366 days',locale:'en-US'})).toEqual({kind:'invalid',reason:'duration-too-long'});expect(createTripRequirements({requestText:'Trip to Shiraz for 30 days',locale:'en-US',maxDurationDays:30}).kind).toBe('ready');});
 it('preserves the entered budget quantity and denomination without converting Rial or Toman',()=>{const r=intake('برای ۷ روز به شیراز با خانواده سفر می‌کنم؛ بودجه ۲۰ میلیون تومان است و به باغ علاقه دارم');expect(r.kind).toBe('ready');if(r.kind==='ready'){expect(r.requirements.budget.value).toMatchObject({amount:20,unit:'میلیون تومان',currency:'TOMAN',raw:'20 میلیون تومان'});expect(r.requirements.travelerCount.value).toBeNull();expect(r.requirements.interests.value).toEqual(['باغ']);expect(r.requirements.travelDates.value).toBeNull();}});
 it('keeps unknown optional values from blocking intake',()=>expect(intake('I want to travel to Shiraz for four days','en-US').kind).toBe('ready'));
 it('extracts only an explicit ISO date range and rejects invalid dates as ambiguous',()=>{const valid=intake('Trip to Shiraz for 4 days from 2027-03-02 to 2027-03-05','en-US');expect(valid.kind).toBe('ready');if(valid.kind==='ready')expect(valid.requirements.travelDates.value).toEqual({start:'2027-03-02',end:'2027-03-05'});const invalid=intake('Trip to Shiraz for 4 days from 2027-02-31 to 2027-03-05','en-US');if(invalid.kind==='ready')expect(invalid.requirements.travelDates.status).toBe('ambiguous');});
 it('keeps toman and rial units distinct and extracts only explicitly stated traveler counts',()=>{const toman=intake('Trip to Shiraz for 4 days, budget 20 million toman, four people','en-US');const rial=intake('Trip to Shiraz for 4 days, budget 20 million IRR, four people','en-US');expect(toman.kind).toBe('ready');expect(rial.kind).toBe('ready');if(toman.kind==='ready'&&rial.kind==='ready'){expect(toman.requirements.budget.value?.unit).toBe('million toman');expect(rial.requirements.budget.value?.unit).toBe('million IRR');expect(toman.requirements.budget.value?.amount).toBe(rial.requirements.budget.value?.amount);expect(toman.requirements.travelerCount.value).toBe(4);}});
 it('does not treat a relative departure as stay duration and keeps unstated currency unknown',()=>{const r=intake('از دو روز دیگه با 4 نفر میخوام برم از مناطق تاریخی شیراز دیدن کنم و فقط 10 میلیون هزینه میخوام بکنم');expect(r.kind).toBe('clarification');if(r.kind==='clarification'){expect(r.requirements.destinations.value).toEqual(['شیراز']);expect(r.requirements.relativeStartDate.value?.offset_days).toBe(2);expect(r.requirements.durationDays.value).toBeNull();expect(r.requirements.travelerCount.value).toBe(4);expect(r.requirements.budget.value).toMatchObject({amount:10,currency:null,raw:'10 میلیون'});expect(r.requirements.interests.value).toEqual(['historical_attractions']);expect(r.requirements.constraints.value).toBeNull();}});
  it('distinguishes Persian stay duration from relative departure wording',()=>{expect(intake('سه روز دیگر به شیراز می‌رویم')).toMatchObject({kind:'clarification',requirements:{durationDays:{value:null},relativeStartDate:{value:{offset_days:3}}}});expect(intake('سفر سه‌روزه به شیراز')).toMatchObject({kind:'ready',requirements:{durationDays:{value:3},relativeStartDate:{value:null}}});});
 it('maps server v1 interpretation without reparsing and preserves unknown currency',()=>{const result=intake('از دو روز دیگه با 4 نفر میخوام برم از مناطق تاریخی شیراز دیدن کنم و فقط 10 میلیون هزینه میخوام بکنم');expect(result.kind).toBe('clarification');if(result.kind==='clarification'){const req=result.requirements;const mapped=tripRequirementsV1ToTripRequirements({contract_version:'trip-requirements-v1',original_text:req.requestText,locale:req.locale,fields:{destination:{status:'known',value:'شیراز',evidence_span:{start:0,end:5,text:'شیراز'}},origin:{status:'missing',value:null},relative_start_date:{status:'known',value:{offset_days:2,anchor_date:null,timezone:null}},duration_days:{status:'missing',value:null},travel_dates:{status:'missing',value:null},travelers:{status:'known',value:4},budget:{status:'known',value:{amount:'10',scale:'million',currency:null,currency_status:'unknown',raw:'10 میلیون'}},interests:{status:'known',value:['historical_attractions']},hard_constraints:{status:'missing',value:null},accessibility:{status:'missing',value:null}},clarification:{missing_fields:['duration_days'],ambiguous_fields:[],question_fields:['duration_days','budget.currency']}});expect(mapped.durationDays.value).toBeNull();expect(mapped.relativeStartDate.value?.offset_days).toBe(2);expect(mapped.budget.value).toMatchObject({amount:10,currency:null,scale:'million'});expect(mapped.requestText).toBe(req.requestText);}});
 it.each([
  ['Trip to Shiraz for 4 days, budget 20 million toman', 'en-US', 20, 'TOMAN', 'million toman'],
  ['Trip to Shiraz for 4 days, budget 20 million IRR', 'en-US', 20, 'IRR', 'million IRR'],
  ['سفر ۴ روزه به شیراز با بودجهٔ ۲۰ میلیون ریال', 'fa-IR', 20, 'IRR', 'میلیون ریال'],
  ['Trip to Shiraz for 4 days, budget 20 million USD', 'en-US', 20, 'USD', 'million USD'],
  ['رحلة لمدة ٤ أيام إلى شيراز بميزانية ٢٠ مليون درهم', 'ar', 20, 'AED', 'مليون درهم'],
  ['رحلة لمدة ٤ أيام إلى شيراز بميزانية ٢٠ مليون ر.س', 'ar', 20, 'SAR', 'مليون ر.س'],
 ] as const)('keeps parser budget contract explicit for %s', (text, locale, amount, currency, unit) => {
  const result=intake(text, locale);
  expect(result.kind).toBe('ready');
  if(result.kind==='ready')expect(result.requirements.budget.value).toMatchObject({amount,currency,unit,raw:expect.any(String)});
 });
 it.each([
  ['I prefer paved paths but must avoid rough terrain during a 4-day trip to Shiraz', 'en-US', 'paved paths', 'avoid rough terrain'],
  ['سفر ۴ روزه به شیراز؛ ترجیح می‌دهم مسیرهای سنگ‌فرش را انتخاب کنم ولی باید از مسیرهای ناهموار پرهیز کنم', 'fa-IR', 'مسیرهای سنگ فرش را انتخاب کنم', 'از مسیرهای ناهموار پرهیز کنم'],
  ['رحلة لمدة ٤ أيام إلى شيراز، أفضل المسارات المعبدة لكن يجب تجنب الطرق الوعرة', 'ar', 'المسارات المعبدة', 'تجنب الطرق الوعرة'],
 ] as const)('separates explicit preference from mandatory wording in %s', (text, locale, preference, hard) => {
  const result=intake(text, locale);
  expect(result.kind).toBe('ready');
  if(result.kind==='ready'){
   expect(result.requirements.softPreferences.value).toEqual([preference]);
   expect(result.requirements.constraints.value).toEqual([hard]);
  }
 });
 it.each([
  ['I want paved paths for a 4-day trip to Shiraz', 'en-US'],
  ['برای ۴ روز در شیراز مسیرهای سنگ‌فرش می‌خواهم', 'fa-IR'],
  ['أريد طرقًا معبدة في رحلة إلى شيراز لمدة ٤ أيام', 'ar'],
 ] as const)('keeps ambiguous desire mandatory instead of making it advisory: %s', (text, locale) => {
  const result=intake(text, locale);
  expect(result.kind).toBe('ready');
  if(result.kind==='ready'){
   expect(result.requirements.softPreferences.value).toBeNull();
   expect(result.requirements.constraints.value).not.toBeNull();
  }
 });
 it.each([
  ['I need wheelchair access for a 3-day trip to Shiraz','en-US',['wheelchair_access']],
  ['سفر ۳ روزه به شیراز با دسترسی با ویلچر','fa-IR',['wheelchair_access']],
  ['رحلة لمدة ٣ أيام إلى شيراز مع إمكانية الوصول بالكراسي المتحركة','ar',['wheelchair_access']],
  ['A 3-day trip to Shiraz with a step-free entrance','en-US',['step_free_access']],
  ['سفر ۳ روزه به شیراز با ورودی بدون پله','fa-IR',['step_free_access']],
  ['رحلة لمدة ٣ أيام إلى شيراز بمدخل دون درجات','ar',['step_free_access']],
 ])('extracts only explicitly stated access attribute phrases in %s', (text,locale,attributes)=>{
  const result=intake(text,locale as 'fa-IR'|'en-US'|'ar');
  expect(result.kind).toBe('ready');
  if(result.kind==='ready')expect(result.requirements.accessibility.value).toEqual(attributes);
 });
 it.each([
  ['I will not travel by boat for 4 days to Shiraz', 'en-US', 'I will not travel by boat'],
  ['I prefer trains but I won\'t travel by boat for 4 days to Shiraz', 'en-US', 'I won\'t travel by boat'],
  ['\u0628\u0627 \u0642\u0627\u06cc\u0642 \u0646\u0645\u06cc\u200c\u0631\u0648\u06cc\u0645\u060c \u0633\u0641\u0631 \u06f4 \u0631\u0648\u0632\u0647 \u0628\u0647 \u0634\u06cc\u0631\u0627\u0632', 'fa-IR', '\u0628\u0627 \u0642\u0627\u06cc\u0642 \u0646\u0645\u06cc \u0631\u0648\u06cc\u0645'],
 ] as const)('keeps explicit travel prohibitions mandatory: %s', (text, locale, expected) => {
  const result = intake(text, locale);
  expect(result.kind).toBe('ready');
  if (result.kind === 'ready') {
   expect(result.requirements.constraints.value).toContain(expected);
   if (text.includes('prefer')) expect(result.requirements.softPreferences.value).toEqual(['trains']);
  }
 });
 it('does not infer an access requirement from a statement about the traveler alone',()=>{
  const result=intake('I use a wheelchair and want a 3-day trip to Shiraz','en-US');
  expect(result.kind).toBe('ready');
  if(result.kind==='ready')expect(result.requirements.accessibility.value).toBeNull();
 });
});


describe('traveler-local relative dates', () => {
 it('computes an inclusive end date when duration is clarified later', () => {
  expect(inclusiveEndDate('2026-11-17', 5)).toBe('2026-11-21');
  expect(inclusiveEndDate('2026-12-30', 4)).toBe('2027-01-02');
  expect(inclusiveEndDate('2026-02-31', 2)).toBeNull();
  expect(inclusiveEndDate('2026-11-17', 0)).toBeNull();
 });
 it.each([
   ['\u0641\u0631\u062f\u0627', 1],
   ['\u067e\u0633 \u0641\u0631\u062f\u0627', 2],
   ['\u067e\u0633\u200c\u0641\u0631\u062f\u0627', 2],
   ['tomorrow', 1], ['day after tomorrow', 2],
   ['\u063a\u062f\u0627\u064b', 1], ['\u0628\u0639\u062f \u063a\u062f', 2],
 ])('resolves %s without changing trip duration', (phrase, days) => {
   const locale = phrase.includes('tomorrow') ? 'en-US' : /\u063a\u062f/.test(phrase) ? 'ar' : 'fa-IR';
   const result = createTripRequirements({ requestText: `${phrase} \u0628\u0647 \u0634\u06cc\u0631\u0627\u0632`, locale });
   if (result.kind === 'invalid') throw new Error('Unexpected invalid phrase');
   expect(result.requirements.durationDays.value).toBeNull();
   expect(result.requirements.relativeStartDate.value?.offset_days).toBe(days);
 });
 it.each([
  ['\u0628\u0639\u062f \u062b\u0644\u0627\u062b\u0629 \u0623\u064a\u0627\u0645 \u0625\u0644\u0649 \u0634\u064a\u0631\u0627\u0632', 3],
  ['\u0628\u0639\u062f 3 \u0623\u064a\u0627\u0645 \u0625\u0644\u0649 \u0634\u064a\u0631\u0627\u0632', 3],
 ])('recognizes Arabic relative offsets %s', (requestText, offset) => {
  const result = createTripRequirements({ requestText, locale: 'ar' });
  if (result.kind === 'invalid') throw new Error('Unexpected invalid phrase');
  expect(result.requirements.relativeStartDate.value?.offset_days).toBe(offset);
  expect(result.requirements.durationDays.value).toBeNull();
 });
 it('fills editable start/end from an explicit traveler timezone date without the server clock', () => {
   const raw = createTripRequirements({ requestText: '\u0633\u0641\u0631 \u06f3 \u0631\u0648\u0632\u0647 \u0628\u0647 \u0634\u06cc\u0631\u0627\u0632 \u0627\u0632 \u067e\u0633 \u0641\u0631\u062f\u0627', locale: 'fa-IR' });
   if (raw.kind === 'invalid') throw new Error('Unexpected invalid phrase');
   const normalized = resolveRelativeTripDates(raw.requirements, '2026-11-15', 'Asia/Tehran');
   expect(normalized.relativeStartDate.value).toMatchObject({ offset_days: 2, anchor_date: '2026-11-17', timezone: 'Asia/Tehran' });
   expect(normalized.travelDates.value).toEqual({ start: '2026-11-17', end: '2026-11-19' });
 });
 it('keeps the start date when duration is unknown, without inventing an end date', () => {
   const raw = createTripRequirements({ requestText: '\u0627\u0632 \u0641\u0631\u062f\u0627 \u0628\u0647 \u0634\u06cc\u0631\u0627\u0632 \u0633\u0641\u0631 \u0645\u06cc\u200c\u06a9\u0646\u06cc\u0645', locale: 'fa-IR' });
   if (raw.kind === 'invalid') throw new Error('Unexpected invalid phrase');
   const normalized = resolveRelativeTripDates(raw.requirements, '2026-11-15', 'Asia/Tehran');
   expect(normalized.relativeStartDate.value?.anchor_date).toBe('2026-11-16');
   expect(normalized.travelDates.value).toBeNull();
 });
 it('reprojects auto-derived dates when the traveler timezone calendar date changes', () => {
   const raw = createTripRequirements({ requestText: '3-day trip in Shiraz starting tomorrow', locale: 'en-US' });
   if (raw.kind === 'invalid') throw new Error('Unexpected invalid phrase');
   const first = resolveRelativeTripDates(raw.requirements, '2026-11-15', 'Asia/Tehran');
   expect(first.travelDates.value).toEqual({ start: '2026-11-16', end: '2026-11-18' });
   const moved = resolveRelativeTripDates(first, '2026-11-16', 'America/Los_Angeles');
   expect(moved.travelDates.value).toEqual({ start: '2026-11-17', end: '2026-11-19' });
   expect(moved.relativeDateResolution).toMatchObject({ referenceDate: '2026-11-16', timezone: 'America/Los_Angeles' });
 });
 it('keeps explicit dates authoritative and strips browser-only projection metadata before persistence', () => {
   const raw = createTripRequirements({ requestText: 'Trip from 2026-11-20 to 2026-11-22 in Shiraz', locale: 'en-US' });
   if (raw.kind === 'invalid') throw new Error('Unexpected invalid phrase');
   const explicit = resolveRelativeTripDates(raw.requirements, '2026-11-15', 'Asia/Tehran');
   expect(explicit.travelDates.value).toEqual({ start: '2026-11-20', end: '2026-11-22' });
   const derivedRaw = createTripRequirements({ requestText: '3-day trip in Shiraz starting tomorrow', locale: 'en-US' });
   if (derivedRaw.kind === 'invalid') throw new Error('Unexpected invalid phrase');
   const derived = resolveRelativeTripDates(derivedRaw.requirements, '2026-11-15', 'Asia/Tehran');
   expect(requirementsForPersistence(derived)).not.toHaveProperty('relativeDateResolution');
 });
 it('keeps validated LLM values primary and fills only missing values from the tagged local fallback', () => {
   const local = createTripRequirements({ requestText: '3-day trip to Tehran', locale: 'en-US' });
   if (local.kind === 'invalid') throw new Error('Unexpected invalid phrase');
   const interpreted = tripRequirementsV1ToTripRequirements({
     contract_version: 'trip-requirements-v1', original_text: local.requirements.requestText, locale: 'en-US',
     fields: {
       destination: { status: 'known', source: 'llm', value: 'Shiraz', evidence_span: { start: 0, end: 3, text: '3-day' } },
       origin: { status: 'missing', value: null }, relative_start_date: { status: 'missing', value: null },
       duration_days: { status: 'missing', source: 'llm', value: null }, travel_dates: { status: 'missing', value: null },
       travelers: { status: 'missing', value: null }, budget: { status: 'missing', value: null },
       interests: { status: 'missing', value: null }, soft_preferences: { status: 'missing', value: null },
       hard_constraints: { status: 'missing', value: null }, accessibility: { status: 'missing', value: null },
     }, clarification: { missing_fields: ['duration_days'], ambiguous_fields: [], question_fields: ['duration_days'] },
   });
   const merged = mergeRequirementInterpretations(local.requirements, interpreted);
   expect(merged.destinations.value).toEqual(['Shiraz']);
   expect(merged.destinations.source).toBe('llm');
   expect(merged.durationDays.value).toBe(3);
   expect(merged.durationDays.source).toBe('fallback');
   expect(merged.missingRequired).toEqual([]);
 });
});
