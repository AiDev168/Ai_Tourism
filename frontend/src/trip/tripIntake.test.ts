import { describe, expect, it } from 'vitest';
import { createTripRequirements, extractDurationDays } from './tripIntake';

const intake=(requestText:string,locale:'fa-IR'|'en-US'|'ar'='fa-IR')=>createTripRequirements({requestText,locale});
describe('natural-language trip intake v2',()=>{
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
 it('preserves the entered budget quantity and denomination without converting Rial or Toman',()=>{const r=intake('برای ۷ روز به شیراز با خانواده سفر می‌کنم؛ بودجه ۲۰ میلیون تومان است و به باغ علاقه دارم');expect(r.kind).toBe('ready');if(r.kind==='ready'){expect(r.requirements.budget.value).toMatchObject({amount:20,unit:'میلیون تومان',currency:null,raw:'20 میلیون تومان'});expect(r.requirements.travelerCount.value).toBeNull();expect(r.requirements.interests.value).toEqual(['باغ']);expect(r.requirements.travelDates.value).toBeNull();}});
 it('keeps unknown optional values from blocking intake',()=>expect(intake('I want to travel to Shiraz for four days','en-US').kind).toBe('ready'));
 it('extracts only an explicit ISO date range and rejects invalid dates as ambiguous',()=>{const valid=intake('Trip to Shiraz for 4 days from 2027-03-02 to 2027-03-05','en-US');expect(valid.kind).toBe('ready');if(valid.kind==='ready')expect(valid.requirements.travelDates.value).toEqual({start:'2027-03-02',end:'2027-03-05'});const invalid=intake('Trip to Shiraz for 4 days from 2027-02-31 to 2027-03-05','en-US');if(invalid.kind==='ready')expect(invalid.requirements.travelDates.status).toBe('ambiguous');});
 it('keeps toman and rial units distinct and extracts only explicitly stated traveler counts',()=>{const toman=intake('Trip to Shiraz for 4 days, budget 20 million toman, four people','en-US');const rial=intake('Trip to Shiraz for 4 days, budget 20 million IRR, four people','en-US');expect(toman.kind).toBe('ready');expect(rial.kind).toBe('ready');if(toman.kind==='ready'&&rial.kind==='ready'){expect(toman.requirements.budget.value?.unit).toBe('million toman');expect(rial.requirements.budget.value?.unit).toBe('million IRR');expect(toman.requirements.budget.value?.amount).toBe(rial.requirements.budget.value?.amount);expect(toman.requirements.travelerCount.value).toBe(4);}});
 it.each([
  ['Trip to Shiraz for 4 days, budget 20 million toman', 'en-US', 20, null, 'million toman'],
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
 it('does not infer an access requirement from a statement about the traveler alone',()=>{
  const result=intake('I use a wheelchair and want a 3-day trip to Shiraz','en-US');
  expect(result.kind).toBe('ready');
  if(result.kind==='ready')expect(result.requirements.accessibility.value).toBeNull();
 });
});
