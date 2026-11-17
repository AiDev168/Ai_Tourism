import { describe, expect, it } from 'vitest';
import { localScheduleInstant } from './PartnerWorkspace';

describe('partner schedule timezone conversion', () => {
  it('converts the entered wall time in the selected IANA timezone', () => {
    expect(localScheduleInstant('2026-11-16T12:00','Asia/Tehran')).toBe('2026-11-16T08:30:00.000Z');
  });

  it('rejects a wall time that does not exist during a daylight-saving jump', () => {
    expect(() => localScheduleInstant('2026-03-08T02:30','America/New_York')).toThrow('invalid in selected time zone');
  });
});
