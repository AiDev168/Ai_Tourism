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
 it('preserves explicit budget unit, does not guess travelers from family, and leaves unknowns null',()=>{const r=intake('برای ۷ روز به شیراز با خانواده سفر می‌کنم؛ بودجه ۲۰ میلیون تومان است و به باغ علاقه دارم');expect(r.kind).toBe('ready');if(r.kind==='ready'){expect(r.requirements.budget.value).toMatchObject({amount:20_000_000,unit:'میلیون تومان',currency:null});expect(r.requirements.travelerCount.value).toBeNull();expect(r.requirements.interests.value).toEqual(['باغ']);expect(r.requirements.travelDates.value).toBeNull();}});
 it('keeps unknown optional values from blocking intake',()=>expect(intake('I want to travel to Shiraz for four days','en-US').kind).toBe('ready'));
 it('extracts only an explicit ISO date range and rejects invalid dates as ambiguous',()=>{const valid=intake('Trip to Shiraz for 4 days from 2027-03-02 to 2027-03-05','en-US');expect(valid.kind).toBe('ready');if(valid.kind==='ready')expect(valid.requirements.travelDates.value).toEqual({start:'2027-03-02',end:'2027-03-05'});const invalid=intake('Trip to Shiraz for 4 days from 2027-02-31 to 2027-03-05','en-US');if(invalid.kind==='ready')expect(invalid.requirements.travelDates.status).toBe('ambiguous');});
 it('keeps toman and rial units distinct and extracts only explicitly stated traveler counts',()=>{const toman=intake('Trip to Shiraz for 4 days, budget 20 million toman, four people','en-US');const rial=intake('Trip to Shiraz for 4 days, budget 20 million IRR, four people','en-US');expect(toman.kind).toBe('ready');expect(rial.kind).toBe('ready');if(toman.kind==='ready'&&rial.kind==='ready'){expect(toman.requirements.budget.value?.unit).toBe('million toman');expect(rial.requirements.budget.value?.unit).toBe('million IRR');expect(toman.requirements.budget.value?.amount).toBe(rial.requirements.budget.value?.amount);expect(toman.requirements.travelerCount.value).toBe(4);}});
});
