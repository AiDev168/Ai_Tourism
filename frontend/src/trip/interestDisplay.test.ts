import { describe, expect, it } from 'vitest';
import { displayTripInterest, reviewedTripInterests } from './interestDisplay';

describe('reviewed interest labels', () => {
  it('shows a known extracted interest in the traveler language without changing its stored code', () => {
    expect(displayTripInterest('historical_attractions', 'fa-IR')).toBe('جاهای تاریخی');
    expect(displayTripInterest('historical_attractions', 'en-US')).toBe('Historic places');
    expect(displayTripInterest('historical_attractions', 'ar')).toBe('المعالم التاريخية');
    expect(reviewedTripInterests('جاهای تاریخی، طبیعت')).toEqual(['historical_attractions', 'طبیعت']);
  });

  it('localizes the extracted garden interest and keeps the reviewed profile code stable', () => {
    expect(displayTripInterest('gardens', 'fa-IR')).toBe('باغ‌ها');
    expect(displayTripInterest('gardens', 'en-US')).toBe('Gardens');
    expect(displayTripInterest('gardens', 'ar')).toBe('الحدائق');
    expect(reviewedTripInterests('جاهای تاریخی، باغ‌ها')).toEqual(['historical_attractions', 'gardens']);
  });
});
