import { describe, expect, it } from 'vitest';
import { createTripRequirements, type TripRequirements } from './tripIntake';
import { integrateTripFollowUp } from './followUpIntake';

function initial(text: string, locale: 'fa-IR' | 'en-US' | 'ar' = 'en-US'): TripRequirements {
  const outcome = createTripRequirements({ requestText: text, locale });
  if (outcome.kind === 'invalid') throw new Error('Invalid baseline fixture');
  return outcome.requirements;
}
function apply(previous: TripRequirements, message: string, reviewed: Record<string, unknown> | null = null) {
  return integrateTripFollowUp(previous, message, previous.locale, reviewed);
}

describe('multi-turn traveler-only requirement integration', () => {
  it('takes the latest explicit duration without concatenating conflicting history', () => {
    const first = initial('Plan a 3-day trip to Shiraz');
    const result = apply(first, 'Make it a 5-day trip');
    expect(result.kind).toBe('ready');
    if (result.kind === 'invalid') return;
    expect(result.requirements.durationDays.value).toBe(5);
    expect(result.requirements.destinations.value).toEqual(['Shiraz']);
    expect(result.requirements.requestText).toBe(first.requestText);
    expect(result.requirements.ambiguousRequired).toEqual([]);
    expect(result.requirements.destinationVerification).toBe('user_input_unverified');
  });

  it('integrates explicit departure city and party size from a later turn', () => {
    const result = apply(initial('Plan a 3-day trip to Shiraz'),
      'Travel from Tehran to Shiraz with 4 travelers');
    expect(result.kind).toBe('ready');
    if (result.kind === 'invalid') return;
    expect(result.requirements.origin.value).toBe('Tehran');
    expect(result.requirements.travelerCount.value).toBe(4);
    expect(result.requirements.destinations.value).toEqual(['Shiraz']);
  });

  it('adds an explicit budget without erasing destination or duration', () => {
    const result = apply(initial('Plan a 3-day trip to Shiraz'), 'Budget 200000 toman');
    expect(result.kind).toBe('ready');
    if (result.kind === 'invalid') return;
    expect(result.requirements.budget.value?.amount).toBe(200000);
    expect(result.requirements.budget.value?.unit).toBe('toman');
    expect(result.requirements.durationDays.value).toBe(3);
    expect(result.requirements.destinations.value).toEqual(['Shiraz']);
  });

  it('retains explicit mandatory wheelchair and hard constraints when the traveler revises duration', () => {
    const first = initial('Plan a 3-day trip to Shiraz; must have wheelchair access');
    expect(first.accessibility.value).toContain('wheelchair_access');
    const result = apply(first, 'Make it a 5-day trip');
    expect(result.kind).toBe('ready');
    if (result.kind === 'invalid') return;
    expect(result.requirements.accessibility.value).toContain('wheelchair_access');
    expect(result.requirements.constraints.value).toEqual(first.constraints.value);
    expect(result.requirements.durationDays.value).toBe(5);
  });

  it('does not undo a previously reviewed and manually edited destination when only budget changes', () => {
    const first = initial('Plan a 3-day trip to Shiraz');
    const result = apply(first, 'Budget 200000 toman', {
      confirmation_source: 'traveler_reviewed',
      destinations: ['Yazd'], duration_days: 2, origin: 'Tehran', traveler_count: 4,
    });
    expect(result.kind).toBe('ready');
    if (result.kind === 'invalid') return;
    expect(result.requirements.destinations.value).toEqual(['Yazd']);
    expect(result.requirements.durationDays.value).toBe(2);
    expect(result.requirements.origin.value).toBe('Tehran');
    expect(result.requirements.travelerCount.value).toBe(4);
  });

  it('marks a contradictory new duration as ambiguous rather than reverting silently', () => {
    const result = apply(initial('Plan a 3-day trip to Shiraz'), 'Make it 5 days or 6 days');
    expect(result.kind).toBe('clarification');
    if (result.kind === 'invalid') return;
    expect(result.requirements.durationDays.value).toBeNull();
    expect(result.requirements.ambiguousRequired).toContain('duration');
    expect(result.requirements.extractionStatus).toBe('needs_clarification');
  });

  it('rejects an impossible length and preserves the prior source data without confirmation', () => {
    const first = initial('Plan a 3-day trip to Shiraz');
    expect(apply(first, 'Make it 400 days')).toEqual({ kind: 'invalid', reason: 'duration-too-long' });
    expect(first.durationDays.value).toBe(3);
  });

  it('does not let an unanswered follow-up erase a prior explicit destination', () => {
    const first = initial('Plan a 3-day trip to Shiraz');
    const result = apply(first, 'I am not sure about my budget yet');
    expect(result.kind).toBe('ready');
    if (result.kind === 'invalid') return;
    expect(result.requirements.destinations.value).toEqual(['Shiraz']);
    expect(result.requirements.durationDays.value).toBe(3);
    expect(result.requirements.budget.value).toBeNull();
  });
});
