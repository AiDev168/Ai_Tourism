import { describe, expect, it } from 'vitest';
import { displayTripInterest, reviewedTripInterests } from './interestDisplay';

describe('reviewed interest labels', () => {
  it('shows a known extracted interest in the traveler language without changing its stored code', () => {
    expect(displayTripInterest('historical_attractions', 'fa-IR')).toBe('جاهای تاریخی');
    expect(displayTripInterest('historical_attractions', 'en-US')).toBe('Historic places');
    expect(displayTripInterest('historical_attractions', 'ar')).toBe('المعالم التاريخية');
    expect(reviewedTripInterests('جاهای تاریخی، طبیعت')).toEqual(['historical_attractions', 'طبیعت']);
  });
});
