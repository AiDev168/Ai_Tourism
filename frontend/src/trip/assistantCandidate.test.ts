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
    expect(reviewableAssistantCandidate({ budget: '1000', traveler_count: 4 }))
      .toEqual({ destination: null, durationDays: null, travelerCount: 4 });
    expect(reviewableAssistantCandidate(null)).toBeNull();
  });
  it('reviews bounded origin and party size without accepting unsupported hints', () => {
    expect(reviewableAssistantCandidate({ origin: '  تهران ', traveler_count: 3, internal: 'ignore' }))
      .toEqual({ destination: null, durationDays: null, origin: 'تهران', travelerCount: 3 });
    expect(reviewableAssistantCandidate({ origin: 'bad\\ncity', traveler_count: 0 })).toBeNull();
    expect(reviewableAssistantCandidate({ origin: 'x'.repeat(101), traveler_count: 51 })).toBeNull();
  });
  it('allows a single valid suggestion without inventing the other field', () => {
    expect(reviewableAssistantCandidate({ destination: 'اصفهان', duration_days: null }))
      .toEqual({ destination: 'اصفهان', durationDays: null });
    expect(reviewableAssistantCandidate({ duration_days: 1 }))
      .toEqual({ destination: null, durationDays: 1 });
  });
});
