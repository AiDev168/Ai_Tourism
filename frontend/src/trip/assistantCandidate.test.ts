import { describe, expect, it } from 'vitest';
import { reviewableAssistantCandidate } from './assistantCandidate';

describe('reviewable assistant suggestions', () => {
  it('accepts only bounded destination names and valid day counts', () => {
    expect(reviewableAssistantCandidate({ destination: '  کاشان  ', duration_days: 3 }))
      .toEqual({ destination: 'کاشان', durationDays: 3 });
    expect(reviewableAssistantCandidate({ destination_name: 'Shiraz', durationDays: 2 }))
      .toEqual({ destination: 'Shiraz', durationDays: 2 });
  });
  it('does not turn unsupported or invalid model output into editable fields', () => {
    expect(reviewableAssistantCandidate({ destination: '\nunsafe', duration_days: 400 })).toBeNull();
    expect(reviewableAssistantCandidate({ destination: 'x'.repeat(101), duration_days: -1 })).toBeNull();
    expect(reviewableAssistantCandidate({ destination: null, duration_days: 2.5 })).toBeNull();
    expect(reviewableAssistantCandidate({ budget: '1000', traveler_count: 4 })).toBeNull();
    expect(reviewableAssistantCandidate(null)).toBeNull();
  });
  it('allows a single valid suggestion without inventing the other field', () => {
    expect(reviewableAssistantCandidate({ destination: 'اصفهان', duration_days: null }))
      .toEqual({ destination: 'اصفهان', durationDays: null });
    expect(reviewableAssistantCandidate({ duration_days: 1 }))
      .toEqual({ destination: null, durationDays: 1 });
  });
});
