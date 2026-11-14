import { isValidJalaaliDate, jalaaliMonthLength, toGregorian, toJalaali } from 'jalaali-js';

export type JalaaliDate = { jy: number; jm: number; jd: number };
export type GregorianDate = { gy: number; gm: number; gd: number };

export const JALALI_MONTHS_FA = [
  'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
  'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند',
] as const;

export const JALALI_WEEKDAYS_FA = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه'] as const;

export function parseIsoCalendarDate(value: string): GregorianDate | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/u.exec(value);
  if (!match) return null;
  const [gy, gm, gd] = match.slice(1).map(Number);
  const date = new Date(Date.UTC(gy, gm - 1, gd));
  if (date.toISOString().slice(0, 10) !== value) return null;
  return { gy, gm, gd };
}

export function isoToJalaali(value: string): JalaaliDate | null {
  const date = parseIsoCalendarDate(value);
  return date ? toJalaali(date.gy, date.gm, date.gd) : null;
}

export function jalaaliToIso(date: JalaaliDate): string | null {
  if (!isValidJalaaliDate(date.jy, date.jm, date.jd)) return null;
  const gregorian = toGregorian(date.jy, date.jm, date.jd);
  return `${String(gregorian.gy).padStart(4, '0')}-${String(gregorian.gm).padStart(2, '0')}-${String(gregorian.gd).padStart(2, '0')}`;
}

export function jalaaliMonthDays(year: number, month: number): number {
  return jalaaliMonthLength(year, month);
}

export function jalaaliWeekStartOffset(year: number, month: number): number {
  const first = toGregorian(year, month, 1);
  // Iran's calendar week starts on Saturday; JS uses Sunday=0.
  return (new Date(Date.UTC(first.gy, first.gm - 1, first.gd)).getUTCDay() + 1) % 7;
}

export function formatJalaaliDate(value: string, locale: 'fa-IR' | 'en-US' | 'ar' = 'fa-IR'): string {
  const date = isoToJalaali(value);
  if (!date) return '';
  const numberLocale = locale === 'fa-IR' ? 'fa-IR' : locale === 'ar' ? 'ar' : 'en-US';
  return `${new Intl.NumberFormat(numberLocale, { useGrouping: false }).format(date.jd)} ${JALALI_MONTHS_FA[date.jm - 1]} ${new Intl.NumberFormat(numberLocale, { useGrouping: false }).format(date.jy)}`;
}

export function deviceCalendarDate(timeZone?: string): string {
  const zone = timeZone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit', calendar: 'gregory',
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}
