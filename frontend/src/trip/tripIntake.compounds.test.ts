import { describe, expect, it } from 'vitest';
import { createTripRequirements } from './tripIntake';

describe('compound written trip durations', () => {
  it.each([
    ['Trip to Shiraz for twenty-one days', 'en-US', 21],
    ['برای بیست و یک روز به شیراز سفر می‌کنم', 'fa-IR', 21],
    ['رحلة إلى شيراز لمدة ثلاثة وعشرين يوماً', 'ar', 23],
  ])('extracts %s', (requestText, locale, days) => {
    const result = createTripRequirements({ requestText, locale: locale as 'fa-IR' | 'en-US' | 'ar' });
    expect(result.kind).toBe('ready');
    if (result.kind === 'ready') expect(result.requirements.durationDays.value).toBe(days);
  });

  it('accepts the 365-day default boundary and clarifies unsupported number wording', () => {
    expect(createTripRequirements({ requestText: 'Trip to Shiraz for 365 days', locale: 'en-US' }).kind).toBe('ready');
    expect(createTripRequirements({ requestText: 'Trip to Shiraz for many days', locale: 'en-US' }))
      .toMatchObject({ kind: 'clarification', requirements: { missingRequired: ['duration'] } });
  });
});
