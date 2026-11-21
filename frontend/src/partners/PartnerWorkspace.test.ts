import { describe, expect, it } from 'vitest';
import { localScheduleInstant, partnerShareViewPath } from './PartnerWorkspace';

describe('partner schedule timezone conversion', () => {
  it('converts the entered wall time in the selected IANA timezone', () => {
    expect(localScheduleInstant('2026-11-16T12:00','Asia/Tehran')).toBe('2026-11-16T08:30:00.000Z');
  });

  it('rejects a wall time that does not exist during a daylight-saving jump', () => {
    expect(() => localScheduleInstant('2026-03-08T02:30','America/New_York')).toThrow('invalid in selected time zone');
  });
});

describe('partner request and itinerary links', () => {
  it('creates different addressable links for the same protected revision', () => {
    const request = partnerShareViewPath('org-1', 'share-1', 2, 'request');
    const itinerary = partnerShareViewPath('org-1', 'share-1', 2, 'itinerary');
    expect(request).not.toBe(itinerary);
    const req = new URL(request, 'https://localhost:8443');
    const plan = new URL(itinerary, 'https://localhost:8443');
    expect(req.pathname).toBe('/partners');
    expect(req.searchParams.get('org')).toBe('org-1');
    expect(req.searchParams.get('share')).toBe('share-1');
    expect(req.searchParams.get('revision')).toBe('2');
    expect(req.searchParams.get('view')).toBe('request');
    expect(plan.searchParams.get('view')).toBe('itinerary');
    // The URLs identify a protected resource, and contain no authentication credentials.
    expect(req.searchParams.has('token')).toBe(false);
    expect(req.searchParams.has('key')).toBe(false);
  });

  it('does not confuse different company organizations or revisions', () => {
    const previous = partnerShareViewPath('org-A', 'same-share', 1, 'itinerary');
    const updated = partnerShareViewPath('org-A', 'same-share', 2, 'itinerary');
    const outsider = partnerShareViewPath('org-B', 'same-share', 2, 'itinerary');
    expect(previous).not.toBe(updated);
    expect(updated).not.toBe(outsider);
  });
});
