import { describe, expect, it } from 'vitest';
import { isLeapJalaaliYear } from 'jalaali-js';
import {
  formatJalaaliDate, isoToJalaali, jalaaliMonthDays, jalaaliToIso,
  parseIsoCalendarDate,
} from './jalaliDate';

describe('Jalali calendar and Gregorian storage contract', () => {
  it('converts Nowruz without changing the persisted ISO date', () => {
    expect(isoToJalaali('2025-03-21')).toEqual({ jy: 1404, jm: 1, jd: 1 });
    expect(jalaaliToIso({ jy: 1404, jm: 1, jd: 1 })).toBe('2025-03-21');
  });

  it('handles leap and common Esfand lengths', () => {
    expect(isLeapJalaaliYear(1403)).toBe(true);
    expect(jalaaliMonthDays(1403, 12)).toBe(30);
    expect(isLeapJalaaliYear(1404)).toBe(false);
    expect(jalaaliMonthDays(1404, 12)).toBe(29);
  });

  it('round trips dates across months and year boundaries', () => {
    for (const iso of ['2024-03-19', '2024-03-20', '2025-03-20', '2025-03-21', '2026-12-31']) {
      const jalali = isoToJalaali(iso);
      expect(jalali).not.toBeNull();
      expect(jalaaliToIso(jalali!)).toBe(iso);
    }
  });

  it('rejects malformed dates and renders Persian date labels', () => {
    expect(parseIsoCalendarDate('2025-02-30')).toBeNull();
    expect(formatJalaaliDate('not-a-date')).toBe('');
    expect(formatJalaaliDate('2025-03-21', 'fa-IR')).toContain('فروردین');
  });
});
