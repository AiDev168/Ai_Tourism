import type { Locale } from '../i18n/messages';
import type { TripRequirements } from '../trip/tripIntake';

export const MAX_DEVICE_LOCATION_AGE_MS = 5 * 60 * 1000;
export const MAX_DEVICE_LOCATION_ACCURACY_METERS = 5_000;

export type DevicePosition = {
  coords: { latitude: number; longitude: number; accuracy: number };
  timestamp: number;
};

export type ApproximateDeviceOrigin = {
  approximateText: string;
  accuracyMeters: number;
};

export type DeviceOriginValidation =
  | { kind: 'accepted'; origin: ApproximateDeviceOrigin }
  | { kind: 'rejected'; reason: 'invalid' | 'stale' | 'accuracy' };

export type DeviceLocationError = 'denied' | 'timeout' | 'unavailable';

export function deviceLocationErrorKey(code: number): DeviceLocationError {
  return code === 1 ? 'denied' : code === 3 ? 'timeout' : 'unavailable';
}

export type DeviceOriginRequestResult =
  | { kind: 'accepted'; origin: ApproximateDeviceOrigin }
  | { kind: 'rejected'; reason: DeviceLocationError | 'invalid' | 'stale' | 'accuracy' };

/** One-shot browser request; raw coordinates are validated then immediately discarded. */
export function requestDeviceOrigin(
  geolocation: Pick<Geolocation, 'getCurrentPosition'>,
  referenceNow?: number,
): Promise<DeviceOriginRequestResult> {
  return new Promise(resolve => {
    geolocation.getCurrentPosition(
      position => resolve(validateDevicePosition(position, referenceNow ?? Date.now())),
      error => resolve({ kind: 'rejected', reason: deviceLocationErrorKey(error.code) }),
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 0 },
    );
  });
}

/** Validate a fresh browser position, then reduce precision before application state sees it. */
export function validateDevicePosition(position: DevicePosition, now = Date.now()): DeviceOriginValidation {
  const { latitude, longitude, accuracy } = position.coords;
  if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90
      || !Number.isFinite(longitude) || longitude < -180 || longitude > 180
      || !Number.isFinite(accuracy) || accuracy <= 0) {
    return { kind: 'rejected', reason: 'invalid' };
  }
  const age = now - position.timestamp;
  if (!Number.isFinite(position.timestamp) || age < 0 || age > MAX_DEVICE_LOCATION_AGE_MS) {
    return { kind: 'rejected', reason: 'stale' };
  }
  if (accuracy > MAX_DEVICE_LOCATION_ACCURACY_METERS) {
    return { kind: 'rejected', reason: 'accuracy' };
  }
  return {
    kind: 'accepted',
    origin: {
      // Two decimal places coarsen the position to roughly kilometre scale.
      approximateText: `${latitude.toFixed(2)}, ${longitude.toFixed(2)}`,
      accuracyMeters: Math.round(accuracy),
    },
  };
}

/** Be conservative: if the request contains an explicit departure cue, GPS must never replace it. */
export function requestHasExplicitOrigin(text: string, locale: Locale): boolean {
  const value = text.normalize('NFKC').replace(/[\u200c\u200e\u200f]/gu, ' ').replace(/\s+/gu, ' ').trim();
  if (!value) return false;
  if (locale === 'fa-IR') {
    const route = /(?:^|[\u060c,;.! \u061f?\s])\u0627\u0632\s+([^\u060c,;.! \u061f?]{1,60}?)\s+(?:\u0645\u06cc\s*(?:\u062e\u0648\u0627\u0645|\u062e\u0648\u0627\u0645)|\u0645\u06cc\s*\u0631\u0648(?:\u0645|\u06cc\u0645)|\u0628\u0631(?:\u0648\u0645|\u0645|\u06cc\u0645)|\u062d\u0631\u06a9\u062a\s*\u0645\u06cc\s*\u06a9\u0646\u0645|\u0631\u0627\u0647\s*\u0645\u06cc\s*\u0627\u0641\u062a\u0645)\s+([^\u060c,;.! \u061f?]{1,80})/u.exec(value);
    if (!route) return false;
    const originPhrase = route[1];
    const relativeDate = /(?:^|\s)(?:\u0627\u0645\u0631\u0648\u0632|\u0641\u0631\u062f\u0627|\u067e\u0633\s*\u0641\u0631\u062f\u0627|\u062f\u06cc\u0631\u0648\u0632|\u0627\u0645\u0634\u0628|\u0634\u0646\u0628\u0647|\u06cc\u06a9\u0634\u0646\u0628\u0647|\u062f\u0648\u0634\u0646\u0628\u0647|\u0633\u0647\s*\u0634\u0646\u0628\u0647|\u0686\u0647\u0627\u0631\u0634\u0646\u0628\u0647|\u067e\u0646\u062c\u0634\u0646\u0628\u0647|\u062c\u0645\u0639\u0647|(?:\d+|\u06cc\u06a9|\u062f\u0648|\u0633\u0647|\u0686\u0647\u0627\u0631|\u067e\u0646\u062c|\u0634\u0634|\u0647\u0641\u062a|\u0647\u0634\u062a|\u0646\u0647|\u062f\u0647|\u0686\u0646\u062f)\s+\u0631\u0648\u0632(?:\s+(?:\u062f\u06cc\u06af\u0647|\u062f\u06cc\u06af\u0631|\u0628\u0639\u062f))?|\u0647\u0641\u062a\u0647\s+(?:\u0628\u0639\u062f|\u062f\u06cc\u06af\u0647|\u062f\u06cc\u06af\u0631)|\u0645\u0627\u0647\s+(?:\u0628\u0639\u062f|\u062f\u06cc\u06af\u0647|\u062f\u06cc\u06af\u0631))(?:\s|$)/u;
    return !relativeDate.test(originPhrase);
  }
  if (locale === 'ar') {
    return /(?:^|[\u060c,;.! \u061f?\s])\u0645\u0646\s+[^\u060c,;.! \u061f?]{1,80}?\s+(?:\u0625\u0644\u0649|\u0627\u0644\u0649|\u0646\u062d\u0648)\s+[^\u060c,;.! \u061f?]{1,80}/u.test(value);
  }
  return /(?:^|[,.!?\s])from\s+.{1,80}?\s+(?:to|toward|towards)\s+.{1,80}/iu.test(value);
}

export function withApproximateDeviceOrigin(
  requirements: TripRequirements,
  origin: ApproximateDeviceOrigin,
  locale: Locale,
): TripRequirements {
  if (requirements.origin.value?.trim() || requestHasExplicitOrigin(requirements.requestText, locale)) {
    return requirements;
  }
  const prefix = locale === 'fa-IR' ? '\u0645\u0648\u0642\u0639\u06cc\u062a \u062a\u0642\u0631\u06cc\u0628\u06cc \u062f\u0633\u062a\u06af\u0627\u0647' : locale === 'ar' ? '\u0645\u0648\u0642\u0639 GPS \u062a\u0642\u0631\u064a\u0628\u064a' : 'Approximate device location';
  return {
    ...requirements,
    origin: {
      value: `${prefix} (${origin.approximateText}; ±${origin.accuracyMeters} m)`,
      status: 'extracted',
      evidence: 'Traveler accepted a privacy-coarsened device position; city identity is unresolved.',
      source: 'traveler',
    },
  };
}
