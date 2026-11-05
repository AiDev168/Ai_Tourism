import { describe, expect, it } from 'vitest';
import { direction, formatCurrency, formatDate, formatNumber, locales, messages } from './messages';

describe('locale foundation', () => {
  it('provides complete UI copy in all supported locales', () => {
    const keys = Object.keys(messages['fa-IR']).sort();
    for (const locale of locales) expect(Object.keys(messages[locale]).sort()).toEqual(keys);
  });
  it('uses locale-specific direction and Intl formatting', () => {
    expect(direction('fa-IR')).toBe('rtl'); expect(direction('ar')).toBe('rtl'); expect(direction('en-US')).toBe('ltr');
    expect(formatNumber('fa-IR', 12345)).not.toBe(formatNumber('en-US', 12345));
    expect(formatNumber('ar', 1000)).toContain('١');
    expect(formatCurrency('ar', 1000, 'USD')).not.toBe(formatCurrency('en-US', 1000, 'USD'));
    expect(formatDate('en-US', new Date('2026-11-05T12:00:00Z'))).toContain('November');
  });
});
