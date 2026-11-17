import type { Locale } from '../i18n/messages';
import { createTripRequirements, type Field, type TripIntakeResult, type TripRequirements } from './tripIntake';

/**
 * Treat each traveler follow-up as its own utterance, not as a concatenated
 * prompt. Concatenating the original request with corrections such as "five
 * days instead" made two explicit durations look contradictory and could
 * exceed the 1200-character intake budget.
 *
 * This is a reviewable local extraction, NEVER an AI-confirmed trip profile.
 * Explicit new values supersede older extracted fields; unknown values cannot
 * erase earlier facts; ambiguous corrections remain ambiguous and must be
 * reviewed. Mandatory constraints and access needs are cumulative.
 */
/** Accept a short, explicit city answer only in a trip conversation that is
 * awaiting a destination (or an explicit "no, <city>" correction).
 * This is traveler-provided text, NOT verification or AI inference.
 */
function shortCityReply(text: string, permitCorrection: boolean): Field<string[]> | null {
  let answer = text.normalize('NFC').trim();
  const correction = /^(?:نه[\s،,:!]+|no[\s,:!]+)(.+)$/iu.exec(answer);
  if (correction) {
    if (!permitCorrection) return null;
    answer = correction[1].trim();
  } else if (!permitCorrection) {
    // Only the missing-destination path accepts an unprefixed short answer.
  } else {
    return null; // Never overwrite a known city with arbitrary prose.
  }
  answer = answer.replace(/^[،,\s]+|[.،,؟?!\s]+$/gu, '').trim();
  if (!answer || answer.length > 80 || answer.split(/\s+/u).length > 4
      || /\d/u.test(answer)
      || /(?:\b(?:days?|weeks?|budget|not|maybe|perhaps|unsure|unknown|don't|dont|need|prefer|want|from|with|travel|trip|city)\b|روز|هفته|بودجه|نمی|نمیدان|نمی‌دان|نمیدون|نمی‌دون|شاید|مطمئن|ترجیح|سفر|مسافرت|برای|مدت|نفر|نمیخوا|میخوا|مقصد|أيام|ايام|ميزانية|ربما|لا\s+أعرف|لا\s+اعرف|رحلة)/iu.test(answer)) {
    return null;
  }
  const choices = answer.split(/\s+(?:یا|or|أو|او)\s+/iu);
  if (choices.some(choice => !/^[\p{L}\p{M}\u200c -]+$/u.test(choice.trim()) || !choice.trim())) return null;
  if (choices.length > 1) {
    return { value: null, status: 'ambiguous', evidence: text, candidates: [choices.map(v => v.trim())] };
  }
  return { value: [answer], status: 'extracted', evidence: text };
}

export function integrateTripFollowUp(
  previous: TripRequirements,
  followUpText: string,
  locale: Locale,
  lastReviewedProfile: Record<string, unknown> | null = null,
): TripIntakeResult {
  const incoming = createTripRequirements({ requestText: followUpText, locale });
  if (incoming.kind === 'invalid') return incoming;

  const correction = incoming.requirements;
  const base: TripRequirements = { ...previous, locale };
  if (lastReviewedProfile?.confirmation_source === 'traveler_reviewed') {
    const destinations = lastReviewedProfile.destinations;
    if (Array.isArray(destinations) && destinations.length <= 50
        && destinations.every(value => typeof value === 'string'
          && value.trim().length > 0 && value.trim().length <= 100)) {
      base.destinations = { value: destinations.slice(), status: 'extracted', evidence: null };
    }
    const duration = lastReviewedProfile.duration_days;
    if (typeof duration === 'number' && Number.isInteger(duration) && duration >= 1 && duration <= 365) {
      base.durationDays = { value: duration, status: 'extracted', evidence: null };
    }
    const origin = lastReviewedProfile.origin;
    if (typeof origin === 'string' && origin.trim().length > 0 && origin.trim().length <= 100) {
      base.origin = { value: origin.trim(), status: 'extracted', evidence: null };
    }
    const travelers = lastReviewedProfile.traveler_count;
    if (typeof travelers === 'number' && Number.isInteger(travelers) && travelers >= 1 && travelers <= 50) {
      base.travelerCount = { value: travelers, status: 'extracted', evidence: null };
    }
  }

  // A short standalone answer like "کاشان" is otherwise invisible to the
  // generic trip parser, which intentionally requires travel context.
  // Determine correction authority AFTER loading a manually reviewed profile.
  if (correction.destinations.status === 'unknown') {
    const explicitAnswer = shortCityReply(followUpText, Boolean(base.destinations.value));
    if (explicitAnswer) correction.destinations = explicitAnswer;
  }

  const takeExplicit = <T>(oldField: Field<T>, newField: Field<T>): Field<T> =>
    newField.status === 'unknown' ? oldField : newField;

  const dedup = <T extends string>(a: T[] | null, b: T[] | null): T[] | null => {
    const seen = new Set<string>();
    const result = [...(a ?? []), ...(b ?? [])].filter(value => {
      const normalized = value.trim().toLocaleLowerCase();
      if (!normalized || seen.has(normalized)) return false;
      seen.add(normalized);
      return true;
    });
    return result.length ? result : null;
  };

  const cumulative = <T extends string>(oldField: Field<T[]>, newField: Field<T[]>): Field<T[]> => {
    if (newField.value === null) return oldField;
    return { value: dedup(oldField.value, newField.value), status: 'extracted',
      evidence: [oldField.evidence, newField.evidence].filter(Boolean).join(' / ') || null };
  };

  const result: TripRequirements = {
    ...base,
    requestText: previous.requestText, // preserve exact initial user input
    locale,
    destinations: takeExplicit(base.destinations, correction.destinations),
    origin: takeExplicit(base.origin, correction.origin),
    durationDays: takeExplicit(base.durationDays, correction.durationDays),
    travelDates: takeExplicit(base.travelDates, correction.travelDates),
    travelerCount: takeExplicit(base.travelerCount, correction.travelerCount),
    budget: takeExplicit(base.budget, correction.budget),
    interests: cumulative(base.interests, correction.interests),
    softPreferences: cumulative(base.softPreferences, correction.softPreferences),
    // Never silently drop a hard constraint or accessibility requirement.
    constraints: cumulative(base.constraints, correction.constraints),
    accessibility: cumulative(base.accessibility, correction.accessibility),
    destinationVerification: 'user_input_unverified',
    confirmationRequired: [...new Set([...base.confirmationRequired, ...correction.confirmationRequired])],
    missingRequired: [],
    ambiguousRequired: [],
    extractionStatus: 'ready',
  };

  for (const [code, field] of [
    ['destination', result.destinations],
    ['duration', result.durationDays],
  ] as const) {
    if (field.value === null) {
      if (field.status === 'ambiguous') result.ambiguousRequired.push(code);
      else result.missingRequired.push(code);
    }
  }
  if (result.missingRequired.length || result.ambiguousRequired.length) result.extractionStatus = 'needs_clarification';
  return result.extractionStatus === 'ready'
    ? { kind: 'ready', requirements: result }
    : { kind: 'clarification', requirements: result };
}
