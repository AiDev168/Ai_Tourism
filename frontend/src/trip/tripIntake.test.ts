import { describe, expect, it } from 'vitest';
import { createTripRequirements, extractDurationDays } from './tripIntake';

describe('trip request intake', () => {
  it.each([
    ['three days in Shiraz', 3],
    ['۳ روز در شیراز', 3],
    ['٣ أيام في شيراز', 3],
  ])('extracts only explicit localized duration from %s', (requestText, expected) => {
    expect(extractDurationDays(requestText)).toBe(expected);
  });

  it('asks for clarification when destination and duration are missing', () => {
    expect(createTripRequirements({ requestText: 'A quiet trip', destination: '', durationDays: '' })).toEqual({
      kind: 'clarification', missing: ['destination', 'duration'],
    });
  });

  it('captures user-provided mixed-script destination without normalizing its spelling', () => {
    expect(createTripRequirements({ requestText: 'A calm trip for 2 days', destination: 'Shiraz شیراز شيراز', durationDays: '' })).toEqual({
      kind: 'ready', requirements: { requestText: 'A calm trip for 2 days', destination: 'Shiraz شیراز شيراز', durationDays: 2 },
    });
  });

  it('rejects unsupported durations rather than truncating or guessing', () => {
    expect(createTripRequirements({ requestText: 'Trip for 4 days', destination: 'Shiraz', durationDays: '' })).toEqual({
      kind: 'invalid', reason: 'duration-invalid',
    });
  });
});
