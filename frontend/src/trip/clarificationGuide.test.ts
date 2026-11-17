import { describe, expect, it } from 'vitest';
import { nextTripQuestion } from './clarificationGuide';

describe('guided traveler clarification', () => {
  it('prioritizes missing destination over travel duration', () => {
    const result = nextTripQuestion('fa-IR', [], '');
    expect(result?.field).toBe('destination');
    expect(result?.question).toContain('مقصد');
    expect(result?.instruction).toContain('افزودن به گفت‌وگو');
  });

  it('asks for duration when destination is known but duration is absent', () => {
    const result = nextTripQuestion('en-US', ['Shiraz'], '');
    expect(result?.field).toBe('duration');
    expect(result?.question).toContain('days');
  });

  it('does not ask unnecessary questions when both required fields are present', () => {
    for (const locale of ['fa-IR', 'en-US', 'ar'] as const) {
      expect(nextTripQuestion(locale, ['کاشان'], '5')).toBeNull();
      expect(nextTripQuestion(locale, [''], '5')?.field).toBe('destination');
      expect(nextTripQuestion(locale, ['کاشان'], '0')?.field).toBe('duration');
    }
  });

  it('shows localized guidance without implying a remote provider request', () => {
    const arabic = nextTripQuestion('ar', [], '');
    expect(arabic?.question).toContain('مدينة');
    expect(arabic?.instruction).toContain('المحادثة');
  });
});
