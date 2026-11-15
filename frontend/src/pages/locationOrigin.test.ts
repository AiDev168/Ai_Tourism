import { describe, expect, it } from 'vitest';
import { createTripRequirements } from '../trip/tripIntake';
import {
  MAX_DEVICE_LOCATION_AGE_MS,
  deviceLocationErrorKey,
  requestDeviceOrigin,
  requestHasExplicitOrigin,
  validateDevicePosition,
  withApproximateDeviceOrigin,
} from './locationOrigin';

const fix = (overrides: Partial<GeolocationPosition> = {}): GeolocationPosition => ({
  coords: {
    latitude: 35.6895123,
    longitude: 51.3890123,
    accuracy: 24,
    altitude: null,
    altitudeAccuracy: null,
    heading: null,
    speed: null,
    toJSON: () => ({}),
  },
  timestamp: 1_000_000,
  toJSON: () => ({}),
  ...overrides,
});

describe('privacy-preserving device origin', () => {
  it('accepts a fresh precise fix and exposes only a coarsened approximate point', () => {
    const result = validateDevicePosition(fix(), 1_000_001);
    expect(result).toEqual({
      kind: 'accepted',
      origin: { approximateText: '35.69, 51.39', accuracyMeters: 24 },
    });
  });

  it('rejects stale, future, invalid, and insufficiently accurate fixes', () => {
    expect(validateDevicePosition(fix(), 1_000_000 + MAX_DEVICE_LOCATION_AGE_MS + 1))
      .toEqual({ kind: 'rejected', reason: 'stale' });
    expect(validateDevicePosition(fix({ timestamp: 1_000_002 }), 1_000_000))
      .toEqual({ kind: 'rejected', reason: 'stale' });
    expect(validateDevicePosition(fix({ coords: { ...fix().coords, latitude: 91 } }), 1_000_000))
      .toEqual({ kind: 'rejected', reason: 'invalid' });
    expect(validateDevicePosition(fix({ coords: { ...fix().coords, accuracy: 5_001 } }), 1_000_000))
      .toEqual({ kind: 'rejected', reason: 'accuracy' });
  });

  it('keeps geolocation denial, timeout, and unavailable errors distinct', () => {
    expect(deviceLocationErrorKey(1)).toBe('denied');
    expect(deviceLocationErrorKey(3)).toBe('timeout');
    expect(deviceLocationErrorKey(2)).toBe('unavailable');
  });

  it('uses a one-shot fresh-position request and maps a mocked permission denial', async () => {
    let success: PositionCallback | undefined;
    let failure: PositionErrorCallback | undefined;
    let options: PositionOptions | undefined;
    const mockedGeolocation = {
      getCurrentPosition: (ok: PositionCallback, fail?: PositionErrorCallback | null, opts?: PositionOptions) => {
        success = ok;
        failure = fail ?? undefined;
        options = opts;
      },
    } as Pick<Geolocation, 'getCurrentPosition'>;

    const accepted = requestDeviceOrigin(mockedGeolocation, 1_000_000);
    expect(options).toMatchObject({ enableHighAccuracy: true, timeout: 10_000, maximumAge: 0 });
    success?.(fix());
    await expect(accepted).resolves.toMatchObject({ kind: 'accepted', origin: { approximateText: '35.69, 51.39' } });

    const denied = requestDeviceOrigin(mockedGeolocation, 1_000_000);
    failure?.({ code: 1, message: 'denied', PERMISSION_DENIED: 1, POSITION_UNAVAILABLE: 2, TIMEOUT: 3 });
    await expect(denied).resolves.toEqual({ kind: 'rejected', reason: 'denied' });
  });

  it('fills an unknown origin with a clearly labeled approximate value', () => {
    const parsed = createTripRequirements({ requestText: '\u0628\u0631\u0627\u06cc \u0633\u0641\u0631 \u0628\u0631\u0646\u0627\u0645\u0647 \u0631\u06cc\u0632\u06cc \u06a9\u0646', locale: 'fa-IR' });
    expect(parsed.kind).not.toBe('invalid');
    if (parsed.kind === 'invalid') return;
    const result = withApproximateDeviceOrigin(parsed.requirements, {
      approximateText: '35.69, 51.39', accuracyMeters: 24,
    }, 'fa-IR');
    expect(result.origin.status).toBe('extracted');
    expect(result.origin.value).toContain('35.69, 51.39');
    expect(result.origin.value).toContain('\u0645\u0648\u0642\u0639\u06cc\u062a \u062a\u0642\u0631\u06cc\u0628\u06cc');
    expect(result.origin.source).toBe('traveler');
    expect(result.origin.evidence).toMatch(/city identity is unresolved/u);
  });

  it('preserves explicit Persian origins and does not misread relative dates as origins', () => {
    const explicitText = '\u0627\u0632 \u0645\u0634\u0647\u062f \u0645\u06cc\u200c\u062e\u0648\u0627\u0645 \u0628\u0631\u0645 \u0634\u06cc\u0631\u0627\u0632';
    expect(requestHasExplicitOrigin(explicitText, 'fa-IR')).toBe(true);
    expect(requestHasExplicitOrigin('\u0627\u0632 \u0641\u0631\u062f\u0627 \u0628\u0631\u0627\u06cc \u067e\u0646\u062c \u0631\u0648\u0632 \u0645\u06cc\u200c\u062e\u0648\u0627\u0645 \u0628\u0631\u0645 \u0634\u06cc\u0631\u0627\u0632', 'fa-IR')).toBe(false);
    expect(requestHasExplicitOrigin('\u0627\u0632 \u062f\u0648 \u0631\u0648\u0632 \u062f\u06cc\u06af\u0647 \u0645\u06cc\u062e\u0648\u0627\u0645 \u0628\u0631\u0645 \u0634\u06cc\u0631\u0627\u0632', 'fa-IR')).toBe(false);
    expect(requestHasExplicitOrigin('from Mashhad to Shiraz', 'en-US')).toBe(true);
    expect(requestHasExplicitOrigin('\u0645\u0646 \u0645\u0634\u0647\u062f \u0625\u0644\u0649 \u0634\u064a\u0631\u0627\u0632', 'ar')).toBe(true);

    const explicit = createTripRequirements({ requestText: explicitText, locale: 'fa-IR' });
    expect(explicit.kind).not.toBe('invalid');
    if (explicit.kind === 'invalid') return;
    const protectedValue = withApproximateDeviceOrigin(explicit.requirements, {
      approximateText: '35.69, 51.39', accuracyMeters: 24,
    }, 'fa-IR');
    expect(protectedValue.origin).toEqual(explicit.requirements.origin);

    const manual = { ...explicit.requirements, requestText: 'plan a trip', origin: {
      value: 'Tabriz', status: 'extracted' as const, evidence: 'Traveler entered it', source: 'traveler' as const,
    } };
    expect(withApproximateDeviceOrigin(manual, {
      approximateText: '35.69, 51.39', accuracyMeters: 24,
    }, 'en-US').origin).toEqual(manual.origin);
  });
});
