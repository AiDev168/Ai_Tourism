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
    expect(reviewableAssistantCandidate({ origin: 'bad\ncity', traveler_count: 0 })).toBeNull();
    expect(reviewableAssistantCandidate({ origin: 'bad\\ncity', traveler_count: 0 })).toBeNull();
    expect(reviewableAssistantCandidate({ origin: 'x'.repeat(101), traveler_count: 51 })).toBeNull();
  });
  it('accepts bounded exact budget, Gregorian date range, and a declared interest', () => {
    expect(reviewableAssistantCandidate({
      budget_text: '200000 تومان', travel_start: '2027-03-01',
      travel_end: '2027-03-04', interest: 'باغ‌های تاریخی',
    })).toEqual({
      destination: null, durationDays: null, budgetText: '200000 تومان',
      travelStart: '2027-03-01', travelEnd: '2027-03-04',
      interest: 'باغ‌های تاریخی',
    });
  });

  it('rejects invented, partial, impossible, and escaped date or budget hints', () => {
    expect(reviewableAssistantCandidate({
      budget_text: 'very cheap', travel_start: '2027-02-30',
      travel_end: '2027-03-02', interest: 'bad\\nvalue',
    })).toBeNull();
    expect(reviewableAssistantCandidate({
      budget_text: '200000', travel_start: '2027-03-05',
      travel_end: '2027-03-02',
    })).toBeNull();
    expect(reviewableAssistantCandidate({
      travel_start: '2027-03-01', interest: 'x'.repeat(101),
    })).toBeNull();
  });

  it('allows a single valid suggestion without inventing the other field', () => {
    expect(reviewableAssistantCandidate({ destination: 'اصفهان', duration_days: null }))
      .toEqual({ destination: 'اصفهان', durationDays: null });
    expect(reviewableAssistantCandidate({ duration_days: 1 }))
      .toEqual({ destination: null, durationDays: 1 });
  });
});
