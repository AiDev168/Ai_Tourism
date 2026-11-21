import { describe, expect, it } from 'vitest';
import { displayPartnerRequest } from './partnerRequestDisplay';

describe('company request fields are accessible and safe to display', () => {
  const sample = {
    destinations: ['شیراز'], duration_days: 4, origin: 'مشهد', traveler_count: 3,
    budget: { raw: '۲۵ میلیون تومان', currency: 'TOMAN' },
    travel_dates: { start: '2026-12-05', end: '2026-12-08' },
    interests: ['باغ‌ها', 'آثار تاریخی'],
    confirmation_source: 'traveler_reviewed',
    field_provenance: { budget: 'correction' },
    requirement_consent: { field_decisions: { destination: 'must_have' } },
    unknown_internal_key: 'should-not-show',
  };
  it('shows user-friendly Persian fields instead of internal keys or raw JSON', () => {
    const rows = displayPartnerRequest(sample, 'fa-IR');
    expect(rows.find(item => item.key === 'budget')?.text).toBe('۲۵ میلیون تومان');
    expect(rows.find(item => item.key === 'travel_dates')?.text).toContain('2026-12-08');
    expect(rows.find(item => item.key === 'destinations')?.text).toBe('شیراز');
    expect(rows.some(item => item.label === 'مقصد سفر')).toBe(true);
    const printed = JSON.stringify(rows);
    for (const secret of ['traveler_reviewed','field_provenance','requirement_consent','unknown_internal_key']) {
      expect(printed).not.toContain(secret);
    }
  });
  it('does not render arbitrary object values as [object Object] or JSON', () => {
    const rows = displayPartnerRequest({ budget: { unknown: 'internal' }, accessibility: { secret: true } }, 'fa-IR');
    expect(rows.find(item => item.key === 'budget')?.text).toBe('مشخص نشده');
    expect(rows.find(item => item.key === 'accessibility')?.text).toBe('مشخص نشده');
    expect(JSON.stringify(rows)).not.toContain('secret');
  });
  it('supports all three interface languages', () => {
    for (const locale of ['fa-IR','en-US','ar'] as const) {
      expect(displayPartnerRequest(sample,locale).find(item => item.key === 'origin')?.provided).toBe(true);
      expect(displayPartnerRequest(sample,locale).every(item => item.label.trim().length > 0)).toBe(true);
    }
  });
});
