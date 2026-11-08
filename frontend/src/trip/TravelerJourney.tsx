import { useEffect, useMemo, useRef, useState } from 'react';
import type { AuthSession } from '../auth/authApi';
import { formatNumber, type Locale } from '../i18n/messages';
import { journeyMessages, localizeRecommendationCode } from '../i18n/journeyMessages';
import { createTripRequirements, type TripRequirements } from './tripIntake';
import { resolveDestinationNames, confirmDestinationCandidate, type DestinationResolution } from './destinationResolution';
import { ApiDestinationCatalogPort } from './destinationCatalogApi';
import {
  travelerApi, TravelerApiError, type ConversationRecord, type ConversationSummary,
  type ItineraryRecord, type ItineraryStop, type RecommendationResult, type RequirementConsentDecision,
  type RequirementFieldCode, type TripRecord,
} from './travelerApi';

const catalog = new ApiDestinationCatalogPort();

function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

function safeRequirements(value: unknown, locale: Locale): TripRequirements | null {
  if (!value || typeof value !== 'object') return null;
  const candidate = value as Partial<TripRequirements>;
  if (typeof candidate.requestText !== 'string' || !candidate.destinations || !candidate.durationDays) return null;
  return {
    ...candidate,
    accessibility: candidate.accessibility ?? { value: null, status: 'unknown', evidence: null },
    softPreferences: candidate.softPreferences ?? { value: null, status: 'unknown', evidence: null },
    locale,
  } as TripRequirements;
}

function choiceIds(resolution: DestinationResolution | null): string[] {
  if (!resolution || resolution.kind !== 'resolved') return [];
  return resolution.items.flatMap(item => item.kind === 'resolved' || item.kind === 'confirmed'
    ? [item.destination.destinationId] : []);
}

function validDayCount(value: unknown): number | null {
  return typeof value === 'number' && Number.isInteger(value) && value >= 1 && value <= 365
    ? value : null;
}

function tripDayCount(trip: TripRecord | null, extracted: TripRequirements | null): number | null {
  return validDayCount(trip?.confirmed_requirements?.duration_days)
    ?? validDayCount(trip?.duration_days)
    ?? validDayCount(extracted?.durationDays.value);
}

const requirementFields: RequirementFieldCode[] = ['budget', 'travel_dates', 'traveler_count', 'origin', 'soft_preference'];
type RestoredRequirementConsent = {
  decisions: Partial<Record<RequirementFieldCode, RequirementConsentDecision>>;
  acknowledgedFields: RequirementFieldCode[];
};

function unresolvedConsentFields(value: TripRequirements | null): RequirementFieldCode[] {
  if (!value) return [];
  const explicit: Record<RequirementFieldCode, unknown> = {
    budget: value.budget.value,
    travel_dates: value.travelDates.value,
    traveler_count: value.travelerCount.value,
    origin: value.origin.value,
    soft_preference: value.softPreferences.value,
  };
  return requirementFields.filter(field => {
    const fieldValue = explicit[field];
    return fieldValue !== null && fieldValue !== undefined
      && (typeof fieldValue !== 'string' || fieldValue.trim().length > 0);
  });
}

function restoredConsent(
  trip: TripRecord,
  fields: RequirementFieldCode[],
): RestoredRequirementConsent | null {
  const raw = trip.confirmed_requirements.requirement_consent;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const consent = raw as Record<string, unknown>;
  if (consent.contract_version !== 'recommendation-consent-v1'
      || !Number.isInteger(consent.profile_version)
      || consent.profile_version !== trip.version) return null;
  const decisions = consent.field_decisions;
  if (!decisions || typeof decisions !== 'object' || Array.isArray(decisions)) return null;
  const decisionEntries = Object.entries(decisions as Record<string, unknown>);
  if (decisionEntries.some(([field, decision]) =>
    !fields.includes(field as RequirementFieldCode)
    || (decision !== 'must_have' && decision !== 'advisory'))
  ) return null;
  const acknowledgements = consent.advisory_acknowledged_fields;
  if (!Array.isArray(acknowledgements)
      || acknowledgements.some(field => typeof field !== 'string' || !fields.includes(field as RequirementFieldCode))
      || new Set(acknowledgements).size !== acknowledgements.length) return null;
  const parsed: Partial<Record<RequirementFieldCode, RequirementConsentDecision>> = {};
  for (const field of fields) {
    const decision = (decisions as Record<string, unknown>)[field];
    if (decision === 'must_have' || decision === 'advisory') parsed[field] = decision;
  }
  const acknowledgedFields = acknowledgements as RequirementFieldCode[];
  if (acknowledgedFields.some(field => parsed[field] !== 'advisory')) return null;
  return { decisions: parsed, acknowledgedFields };
}

function consentIsComplete(
  fields: RequirementFieldCode[],
  decisions: Partial<Record<RequirementFieldCode, RequirementConsentDecision>>,
  acknowledgements: Partial<Record<RequirementFieldCode, boolean>>,
): boolean {
  return fields.every(field => {
    const decision = decisions[field];
    return decision !== undefined && (decision !== 'advisory' || acknowledgements[field] === true);
  });
}

function assignStopToDay(stops: ItineraryStop[], recommendationId: string, nextDay: number): ItineraryStop[] {
  const moving = stops.find(stop => stop.recommendation_id === recommendationId);
  if (!moving || moving.day_number === nextDay) return stops;
  const previousDay = moving.day_number;
  const next = stops.map(stop => stop.recommendation_id === recommendationId ? { ...stop, day_number: nextDay } : stop);
  return normalizeDayOrders(next, [previousDay, nextDay]);
}

function normalizeDayOrders(stops: ItineraryStop[], days: number[]): ItineraryStop[] {
  const next = stops.slice();
  for (const day of new Set(days)) {
    const ordered = next.filter(stop => stop.day_number === day).sort((a, b) => a.stop_order - b.stop_order);
    const orderById = new Map(ordered.map((stop, index) => [stop.recommendation_id, index + 1]));
    for (let index = 0; index < next.length; index += 1) {
      const stop = next[index];
      if (stop.day_number === day) next[index] = { ...stop, stop_order: orderById.get(stop.recommendation_id) ?? stop.stop_order };
    }
  }
  return next;
}

export type TravelerJourneyProps = {
  locale: Locale;
  session: AuthSession | null;
  online: boolean;
  requirements: TripRequirements | null;
  onSessionExpired: () => void;
  onRestoreRequest: (text: string, requirements: TripRequirements) => void;
  onStartNewDraft: () => void;
};

export function TravelerJourney({ locale, session, online, requirements, onSessionExpired, onRestoreRequest, onStartNewDraft }: TravelerJourneyProps) {
  const copy = journeyMessages[locale];
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversation, setActiveConversation] = useState<ConversationRecord | null>(null);
  const [activeTrip, setActiveTrip] = useState<TripRecord | null>(null);
  const [resolution, setResolution] = useState<DestinationResolution | null>(null);
  const [destinationNames, setDestinationNames] = useState<string[]>([]);
  const [durationText, setDurationText] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [requirementChoices, setRequirementChoices] = useState<Partial<Record<RequirementFieldCode, RequirementConsentDecision>>>({});
  const [advisoryAcknowledgements, setAdvisoryAcknowledgements] = useState<Partial<Record<RequirementFieldCode, boolean>>>({});
  const [messageText, setMessageText] = useState('');
  const [recommendations, setRecommendations] = useState<RecommendationResult | null>(null);
  const [itinerary, setItinerary] = useState<ItineraryRecord | null>(null);
  const [editableStops, setEditableStops] = useState<ItineraryStop[]>([]);
  const [dayCount, setDayCount] = useState(1);
  const [itineraryDirty, setItineraryDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [dirty, setDirty] = useState(false);
  const restoringRequestRef = useRef<string | null>(null);

  const extracted = useMemo(() => safeRequirements(activeTrip?.extracted_requirements, activeTrip?.locale ?? locale), [activeTrip, locale]);
  const consentFields = useMemo(() => unresolvedConsentFields(extracted), [extracted]);
  const consentComplete = consentIsComplete(consentFields, requirementChoices, advisoryAcknowledgements);
  const invalidateConsent = () => {
    setRequirementChoices({});
    setAdvisoryAcknowledgements({});
    setConfirmed(false);
    setRecommendations(null);
    setItinerary(null);
  };
  const chooseRequirement = (field: RequirementFieldCode, decision: RequirementConsentDecision) => {
    setRequirementChoices(current => ({ ...current, [field]: decision }));
    setAdvisoryAcknowledgements(current => ({ ...current, [field]: false }));
    setConfirmed(false);
    setRecommendations(null);
    setItinerary(null);
  };
  const selectedIds = choiceIds(resolution);
  const currentMessages = activeConversation?.messages.filter(message => !activeTrip || message.trip_id === activeTrip.trip_id) ?? [];
  const csrf = session?.csrf_token ?? '';
  const requestedTripDays = tripDayCount(activeTrip, extracted);
  const dayCountValid = Number.isInteger(dayCount) && dayCount >= 1 && dayCount <= 365
    && requestedTripDays !== null && dayCount <= requestedTripDays;
  const dayNumbers = Array.from({ length: dayCountValid ? dayCount : 0 }, (_, index) => index + 1);
  const locallyUnplannedDays = dayNumbers.filter(day => !editableStops.some(stop => stop.day_number === day));
  const displayedItineraryStatus = itineraryDirty
    ? !dayCountValid || locallyUnplannedDays.length ? 'partial' : 'complete'
    : itinerary?.status;

  const resolveNames = async (names: string[]) => {
    if (!names.length || names.some(name => !name.trim())) { setResolution(null); return; }
    try {
      const catalogue = await catalog.load();
      setResolution(resolveDestinationNames(names, locale, catalogue));
    } catch {
      setResolution(resolveDestinationNames(names, locale, { kind: 'unavailable' }));
    }
  };

  useEffect(() => {
    let active = true;
    if (!session) {
      setConversations([]);
      setActiveConversation(null);
      setActiveTrip(null);
      setRecommendations(null);
      setItinerary(null);
      setRequirementChoices({});
      setAdvisoryAcknowledgements({});
      setItineraryDirty(false);
      setResolution(null);
      return;
    }
    setLoadingHistory(true);
    void travelerApi.listConversations(50).then(result => {
      if (active) setConversations(result.items);
    }).catch(value => {
      if (!active) return;
      if (value instanceof TravelerApiError && value.status === 401) onSessionExpired();
      else setError(copy.genericError);
    }).finally(() => { if (active) setLoadingHistory(false); });
    return () => { active = false; };
  }, [session?.user.user_id]);

  useEffect(() => {
    if (requirements) {
      if (activeTrip && requirements.requestText !== activeTrip.original_request && restoringRequestRef.current !== requirements.requestText) {
        setDirty(true);
        setConfirmed(false);
        setRecommendations(null);
        setItinerary(null);
      }
      setDestinationNames(requirements.destinations.value ? [...requirements.destinations.value] : []);
      setDurationText(requirements.durationDays.value === null ? '' : String(requirements.durationDays.value));
      const suggestedDays = validDayCount(requirements.durationDays.value);
      if (!activeTrip?.latest_itinerary_id && suggestedDays !== null) setDayCount(suggestedDays);
      void resolveNames(requirements.destinations.value ?? []);
      const restoring = restoringRequestRef.current === requirements.requestText;
      if (requirements.requestText === activeTrip?.original_request) setDirty(false);
      if (restoring) restoringRequestRef.current = null;
      if (!restoring) {
        setConfirmed(false);
        setRecommendations(null);
        setItinerary(null);
        setItineraryDirty(false);
        setRequirementChoices({});
        setAdvisoryAcknowledgements({});
      }
    } else if (!activeTrip) {
      setResolution(null);
    }
  }, [requirements, activeTrip?.trip_id]);

  const applyFailure = (value: unknown) => {
    if (value instanceof TravelerApiError) {
      if (value.status === 401) { setError(copy.sessionExpired); onSessionExpired(); return; }
      if (value.status === 403) { setError(copy.forbidden); return; }
      if (value.status === 404) { setError(copy.forbidden); return; }
      if (value.status === 409) { setError(copy.conflict); return; }
      if (value.status === 503) { setError(copy.recommendationUnavailable); return; }
    }
    setError(online ? copy.genericError : copy.offline);
  };

  const persistDraft = async () => {
    if (!session || !requirements || !online) { if (!online) setError(copy.offline); return; }
    setBusy(true); setError(''); setStatus('');
    try {
      const destination_ids = choiceIds(resolution);
      const body = {
        locale,
        request_text: requirements.requestText,
        extracted_requirements: requirements,
        destination_ids,
        idempotency_key: newIdempotencyKey(),
      };
      const result = activeConversation
        ? await travelerApi.createTripInConversation(csrf, activeConversation.conversation_id, body)
        : await travelerApi.createConversation(csrf, body);
      setActiveConversation(result.conversation);
      setActiveTrip(result.trip);
      setDayCount(tripDayCount(result.trip, requirements) ?? 1);
      setConfirmed(false);
      setDirty(false);
      setStatus(copy.saveSuccess);
      const history = await travelerApi.listConversations(50);
      setConversations(history.items);
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const restoreTrip = async (conversationId: string, tripId: string) => {
    if (requirements && !activeTrip && requirements.requestText.trim() && !window.confirm(copy.replaceDraftConfirm)) return;
    setBusy(true); setError(''); setStatus('');
    try {
      const conversation = await travelerApi.getConversation(conversationId);
      const trip = await travelerApi.getTrip(tripId);
      setActiveConversation(conversation);
      setActiveTrip(trip);
      const parsed = safeRequirements(trip.extracted_requirements, trip.locale);
      if (parsed) {
        setDestinationNames((parsed.destinations.value ?? []).slice());
        setDurationText(parsed.durationDays.value === null ? '' : String(parsed.durationDays.value));
        restoringRequestRef.current = parsed.requestText;
        onRestoreRequest(parsed.requestText, parsed);
        void resolveNames(trip.destination_ids.length ? trip.destination_ids.map(id => {
          const name = (parsed.destinations.value ?? [])[trip.destination_ids.indexOf(id)];
          return name ?? '';
        }) : parsed.destinations.value ?? []);
      }
      const savedConsent = restoredConsent(trip, unresolvedConsentFields(parsed));
      setRequirementChoices(savedConsent?.decisions ?? {});
      setAdvisoryAcknowledgements(Object.fromEntries(
        (savedConsent?.acknowledgedFields ?? []).map(field => [field, true]),
      ) as Partial<Record<RequirementFieldCode, boolean>>);
      const hasReviewedProfile = trip.confirmed_requirements.confirmation_source === 'traveler_reviewed';
      setConfirmed(hasReviewedProfile && savedConsent !== null
        && consentIsComplete(unresolvedConsentFields(parsed), savedConsent.decisions,
          Object.fromEntries(savedConsent.acknowledgedFields.map(field => [field, true]))));
      const latestRecs = trip.latest_recommendation_request_id
        ? await travelerApi.latestRecommendations(trip.trip_id).catch(() => null) : null;
      setRecommendations(latestRecs);
      if (trip.latest_itinerary_id) {
        const saved = await travelerApi.getItinerary(trip.latest_itinerary_id);
        setItinerary(saved); setEditableStops(saved.stops.slice()); setDayCount(saved.day_count); setItineraryDirty(false);
      } else { setItinerary(null); setEditableStops([]); setDayCount(tripDayCount(trip, parsed) ?? 1); setItineraryDirty(false); }
      setDirty(false);
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const sendMessage = async () => {
    if (!session || !activeConversation || !activeTrip || !messageText.trim() || !online) { if (!online) setError(copy.offline); return; }
    setBusy(true); setError(''); setStatus('');
    try {
      const merged = `${activeTrip.original_request}\n${messageText.trim()}`;
      const parsed = createTripRequirements({ requestText: merged, locale: activeTrip.locale });
      const result = await travelerApi.appendMessage(csrf, activeConversation.conversation_id, {
        trip_id: activeTrip.trip_id,
        content: messageText.trim(),
        extracted_requirements: parsed.kind === 'invalid' ? undefined : parsed.requirements,
        idempotency_key: newIdempotencyKey(),
        expected_version: activeConversation.version,
      });
      setActiveConversation(result.conversation);
      setActiveTrip(result.trip);
      setMessageText('');
      setConfirmed(false); setRequirementChoices({}); setAdvisoryAcknowledgements({}); setRecommendations(null); setItinerary(null); setStatus(copy.messageSaved);
      const latest = safeRequirements(result.trip.extracted_requirements, result.trip.locale);
      if (latest) { setDestinationNames(latest.destinations.value?.slice() ?? []); setDurationText(latest.durationDays.value === null ? '' : String(latest.durationDays.value)); restoringRequestRef.current = latest.requestText; onRestoreRequest(latest.requestText, latest); void resolveNames(latest.destinations.value ?? []); }
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const confirmProfile = async () => {
    if (!session || !activeTrip || !online || !consentComplete) { if (!online) setError(copy.offline); return; }
    setBusy(true); setError(''); setStatus('');
    const duration = durationText.trim() === '' ? null : Number(durationText);
    const confirmedRequirements = {
      destinations: destinationNames.map(name => name.trim()).filter(Boolean),
      duration_days: duration,
      origin: extracted?.origin.value ?? null,
      travel_dates: extracted?.travelDates.value ?? null,
      traveler_count: extracted?.travelerCount.value ?? null,
      accessibility: extracted?.accessibility?.value ?? [],
      budget: extracted?.budget.value ?? null,
      soft_preferences: extracted?.softPreferences.value ?? [],
      interests: extracted?.interests.value ?? [],
      constraints: extracted?.constraints.value ?? [],
      confirmation_source: 'traveler_reviewed',
    };
    try {
      const trip = await travelerApi.confirmTripProfile(csrf, activeTrip.trip_id, {
        expected_version: activeTrip.version,
        confirmed_requirements: confirmedRequirements,
        destination_ids: selectedIds,
        requirement_consent: {
          contract_version: 'recommendation-consent-v1',
          field_decisions: requirementChoices,
          advisory_acknowledged_fields: requirementFields.filter(field =>
            requirementChoices[field] === 'advisory' && advisoryAcknowledgements[field] === true),
        },
      });
      setActiveTrip(trip); setConfirmed(true); setDirty(false); setRecommendations(null); setItinerary(null); setStatus(copy.profileSaved);
      setItineraryDirty(false);
      setDayCount(validDayCount(duration) ?? 1);
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const findRecommendations = async () => {
    if (!session || !activeTrip || !confirmed || dirty || !online) { if (!online) setError(copy.offline); return; }
    setBusy(true); setError(''); setStatus('');
    try {
      const result = await travelerApi.recommend(csrf, activeTrip.trip_id, selectedIds);
      setRecommendations(result); setItinerary(null);
      const refreshed = await travelerApi.getTrip(activeTrip.trip_id);
      setActiveTrip(refreshed);
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const createItinerary = async () => {
    if (!session || !activeTrip || !recommendations || recommendations.status !== 'available' || !recommendations.items.length || !online) return;
    if (!dayCountValid) { setError(copy.dayCountInvalid); return; }
    setBusy(true); setError(''); setStatus('');
    try {
      const saved = await travelerApi.createItinerary(csrf, activeTrip.trip_id, {
        recommendation_request_id: recommendations.recommendation_request_id, day_count: dayCount, locale,
      });
      setItinerary(saved); setEditableStops(saved.stops.slice()); setDayCount(saved.day_count); setItineraryDirty(false); setStatus(copy.itinerarySaved);
      setActiveTrip(await travelerApi.getTrip(activeTrip.trip_id));
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const saveItinerary = async () => {
    if (!session || !itinerary || !online) { if (!online) setError(copy.offline); return; }
    setBusy(true); setError(''); setStatus('');
    const title_by_locale = { ...itinerary.title_by_locale, [locale]: copy.itineraryTitle };
    try {
      const saved = await travelerApi.updateItinerary(csrf, itinerary.itinerary_id, {
        expected_revision: itinerary.revision,
        title_by_locale,
        stops: editableStops.map(stop => ({
          recommendation_id: stop.recommendation_id,
          day_number: stop.day_number,
          stop_order: stop.stop_order,
          notes_by_locale: stop.notes_by_locale,
        })),
      });
      setItinerary(saved); setEditableStops(saved.stops.slice()); setItineraryDirty(false); setStatus(copy.itinerarySaved);
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const deleteTrip = async (trip: TripRecord) => {
    if (!session || !online || !window.confirm(copy.deleteConfirm)) return;
    setBusy(true); setError(''); setStatus('');
    try {
      await travelerApi.deleteTrip(csrf, trip.trip_id);
      if (activeTrip?.trip_id === trip.trip_id) { setActiveTrip(null); setActiveConversation(null); setRecommendations(null); setItinerary(null); }
      const history = await travelerApi.listConversations(50); setConversations(history.items); setStatus(copy.deleted);
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const deleteConversation = async (conversationId: string) => {
    if (!session || !online || !window.confirm(copy.deleteConversationConfirm)) return;
    setBusy(true); setError(''); setStatus('');
    try {
      await travelerApi.deleteConversation(csrf, conversationId);
      if (activeConversation?.conversation_id === conversationId) { setActiveConversation(null); setActiveTrip(null); setRecommendations(null); setItinerary(null); }
      const history = await travelerApi.listConversations(50); setConversations(history.items); setStatus(copy.deleted);
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const appendStop = (recommendationId: string) => {
    const item = recommendations?.items.find(result => result.recommendation_id === recommendationId);
    if (!item || editableStops.length >= 1_000) return;
    const day = dayNumbers.find(candidateDay => editableStops.filter(stop => stop.day_number === candidateDay).length < 50);
    if (day === undefined) return;
    const stopOrder = editableStops.filter(stop => stop.day_number === day).length + 1;
    setEditableStops(stops => normalizeDayOrders([...stops, {
      recommendation_id: item.recommendation_id, destination_id: item.destination_id,
      canonical_name: item.canonical_name, localized_names: item.localized_names,
      city_name: item.city_name, province_name: item.province_name,
      day_number: day, stop_order: stopOrder, notes_by_locale: {},
    }], [day]));
    setItineraryDirty(true);
  };

  const moveStop = (day: number, recommendationId: string, delta: number) => {
    setEditableStops(stops => {
      const dayStops = stops.filter(stop => stop.day_number === day).sort((a, b) => a.stop_order - b.stop_order);
      const index = dayStops.findIndex(stop => stop.recommendation_id === recommendationId);
      const target = index + delta;
      if (index < 0 || target < 0 || target >= dayStops.length) return stops;
      [dayStops[index], dayStops[target]] = [dayStops[target], dayStops[index]];
      const order = new Map(dayStops.map((stop, position) => [stop.recommendation_id, position + 1]));
      return stops.map(stop => stop.day_number === day ? { ...stop, stop_order: order.get(stop.recommendation_id) ?? stop.stop_order } : stop);
    });
    setItineraryDirty(true);
  };

  return (
    <section className="traveler-workspace" id="itinerary" dir={locale === 'en-US' ? 'ltr' : 'rtl'} aria-labelledby="traveler-workspace-title">
      <div className="traveler-workspace-heading">
        <div><p className="eyebrow">{copy.workspaceTitle}</p><h2 id="traveler-workspace-title">{activeTrip ? activeTrip.original_request : copy.workspaceTitle}</h2></div>
        {activeTrip && <span className="saved-pill">{copy.savedRecord}</span>}
      </div>

      <p className="privacy-notice">{copy.privacyNotice}</p>
      {!session && <p className="trip-form-help">{copy.signInToSave}</p>}
      {dirty && activeTrip && <p className="journey-alert" role="status">{copy.draftChanged}</p>}
      {error && <p className="journey-error" role="alert">{error}</p>}
      {status && <p className="journey-status" role="status">{status}</p>}

      {requirements && !activeTrip && <button className="primary journey-action" type="button" onClick={() => void persistDraft()} disabled={busy || !session || !online}>
        {busy ? copy.saving : activeConversation ? copy.createAnotherTrip : copy.saveTrip}
      </button>}
      {requirements && activeTrip && dirty && session && <button className="primary journey-action" type="button" onClick={() => void (async () => {
        if (!activeConversation) return;
        setBusy(true); setError('');
        try {
          const result = await travelerApi.appendMessage(csrf, activeConversation.conversation_id, {
            trip_id: activeTrip.trip_id, content: requirements.requestText, extracted_requirements: requirements,
            idempotency_key: newIdempotencyKey(), expected_version: activeConversation.version, replace_previous_request: true,
          });
          setActiveConversation(result.conversation); setActiveTrip(result.trip); setDirty(false); setConfirmed(false); setRequirementChoices({}); setAdvisoryAcknowledgements({}); setRecommendations(null); setItinerary(null);
          setStatus(copy.saveSuccess);
        } catch (value) { applyFailure(value); }
        finally { setBusy(false); }
      })()} disabled={busy || !online}>{busy ? copy.saving : copy.updateTrip}</button>}

      {session && activeConversation && <div className="journey-new-actions">
        <button type="button" onClick={() => { setActiveTrip(null); setConfirmed(false); setRequirementChoices({}); setAdvisoryAcknowledgements({}); setRecommendations(null); setItinerary(null); setDirty(false); setResolution(null); onStartNewDraft(); }}>{copy.createAnotherTrip}</button>
        <button type="button" onClick={() => { setActiveConversation(null); setActiveTrip(null); setConfirmed(false); setRequirementChoices({}); setAdvisoryAcknowledgements({}); setRecommendations(null); setItinerary(null); setDirty(false); setResolution(null); onStartNewDraft(); }}>{copy.startNewConversation}</button>
      </div>}

      {activeTrip && activeConversation && <div className="journey-columns">
        <article className="conversation-panel journey-panel">
          <div className="panel-title"><span className="mini-icon" aria-hidden="true">✳</span><span>{copy.continueTitle}</span></div>
          <div className="conversation-transcript" aria-live="polite">
            {currentMessages.map(message => <div className={`saved-message saved-message-${message.role}`} key={message.message_id}>
              <small>{message.role === 'user' ? activeTrip.locale : copy.emptyAssistant}</small>
              <p dir="auto">{message.content}</p>
            </div>)}
            {!currentMessages.length && <p>{copy.emptyAssistant}</p>}
          </div>
          <label htmlFor="trip-follow-up">{copy.messagePlaceholder}</label>
          <textarea id="trip-follow-up" value={messageText} onChange={event => setMessageText(event.target.value)} maxLength={1200} rows={3} dir="auto" />
          <button type="button" onClick={() => void sendMessage()} disabled={busy || !messageText.trim() || !online}>{copy.sendMessage}</button>
        </article>

        <article className="recommend-panel journey-panel">
          <div className="panel-title"><span className="mini-icon" aria-hidden="true">↗</span>{copy.profileTitle}</div>
          {extracted && <div className="profile-editor">
            <fieldset>
              <legend>{copy.profileDestination}</legend>
              {destinationNames.map((name, index) => <div className="destination-edit-row" key={`${index}-${name}`}>
                <label htmlFor={`profile-destination-${index}`}>{copy.profileDestination} {formatNumber(locale, index + 1)}</label>
                <input id={`profile-destination-${index}`} value={name} onChange={event => {
                  const next = destinationNames.slice(); next[index] = event.target.value; setDestinationNames(next); setDirty(true); invalidateConsent(); void resolveNames(next);
                }} dir="auto" />
                <button type="button" aria-label={`${copy.removeDestination}: ${name}`} onClick={() => { const next = destinationNames.filter((_, item) => item !== index); setDestinationNames(next); setDirty(true); invalidateConsent(); void resolveNames(next); }}>{copy.removeDestination}</button>
              </div>)}
              <button type="button" onClick={() => { const next = [...destinationNames, '']; setDestinationNames(next); setDirty(true); invalidateConsent(); setResolution(null); }}>{copy.profileDestination} +</button>
              {!destinationNames.length && <p>{copy.noDestination}</p>}
            </fieldset>
            <label htmlFor="profile-duration">{copy.profileDuration}</label>
            <input id="profile-duration" type="number" min="1" max="365" value={durationText} onChange={event => { setDurationText(event.target.value); setDirty(true); invalidateConsent(); }} />
            {!!consentFields.length && <fieldset className="requirement-consent" aria-describedby="requirement-consent-intro">
              <legend>{copy.requirementConsentTitle}</legend>
              <p id="requirement-consent-intro">{copy.requirementConsentIntro}</p>
              {consentFields.map(field => {
                const label = localizeRecommendationCode(locale, `field:${field}`);
                const choice = requirementChoices[field];
                const fieldId = `requirement-consent-${field}`;
                return <fieldset className="requirement-consent-field" key={field}>
                  <legend>{label}</legend>
                  <p>{copy.requirementUnverified}</p>
                  <label htmlFor={`${fieldId}-must`}>
                    <input id={`${fieldId}-must`} type="radio" name={fieldId} value="must_have" checked={choice === 'must_have'}
                      onChange={() => chooseRequirement(field, 'must_have')} />
                    {copy.requirementMustHave}
                  </label>
                  <p>{copy.requirementMustHaveHelp}</p>
                  <label htmlFor={`${fieldId}-advisory`}>
                    <input id={`${fieldId}-advisory`} type="radio" name={fieldId} value="advisory" checked={choice === 'advisory'}
                      onChange={() => chooseRequirement(field, 'advisory')} />
                    {copy.requirementAdvisory}
                  </label>
                  {choice === 'advisory' && <div className="requirement-advisory-warning" role="group" aria-label={`${label}: ${copy.requirementAdvisoryWarning}`}>
                    <p className="journey-alert" role="alert">{copy.requirementAdvisoryWarning}</p>
                    <label htmlFor={`${fieldId}-ack`}>
                      <input id={`${fieldId}-ack`} type="checkbox" checked={advisoryAcknowledgements[field] === true}
                        onChange={event => { const checked = event.currentTarget.checked; setAdvisoryAcknowledgements(current => ({ ...current, [field]: checked })); setConfirmed(false); setRecommendations(null); setItinerary(null); }} />
                      {copy.requirementAdvisoryAcknowledgement}
                    </label>
                  </div>}
                </fieldset>;
              })}
              <p>{copy.requirementChoiceRequired}</p>
            </fieldset>}
            {!!extracted?.constraints.value?.length && <div className="journey-alert requirement-unclassified" role="status">
              <strong>{localizeRecommendationCode(locale, 'field:constraints')}:</strong> {copy.requirementUnclassifiedMandatory}
              <button type="button" onClick={() => document.getElementById('trip-follow-up')?.focus()}>{copy.requirementClarifyByEditing}</button>
            </div>}
            {!!extracted?.softPreferences.value?.length && <p className="soft-preference-value" role="status">
              {copy.requirementPreferenceValue}: <span dir="auto">{extracted.softPreferences.value.join(', ')}</span>
            </p>}
            {!!extracted?.accessibility?.value?.length && <div className="journey-alert requirement-accessibility-mandatory" role="status">
              <strong>{localizeRecommendationCode(locale, 'field:access')}:</strong>
              <p>{copy.requirementAccessibilityMandatory}</p>
              <ul>{extracted.accessibility.value.map(need => <li key={need}>{copy[need]}</li>)}</ul>
              <button type="button" onClick={() => document.getElementById('trip-follow-up')?.focus()}>{copy.requirementClarifyByEditing}</button>
            </div>}
            {resolution?.kind === 'catalogue-empty' && <p className="journey-alert" role="status">{copy.recommendationEmpty}</p>}
            {resolution?.kind === 'catalogue-unavailable' && <p className="journey-error" role="alert">{copy.recommendationUnavailable}</p>}
            {resolution?.items.map((item, index) => item.kind === 'ambiguous' ? <fieldset key={index} className="destination-choice">
              <legend>{item.originalPhrase}</legend>
              {item.candidates.map(candidate => <label key={candidate.destinationId} dir="auto"><input type="radio" name={`traveler-choice-${index}`} checked={resolution.items[index]?.kind === 'confirmed' && resolution.items[index].destination.destinationId === candidate.destinationId} onChange={() => setResolution(current => current ? confirmDestinationCandidate(current, index, candidate.destinationId) : current)} />{candidate.localizedNames[locale] ?? candidate.canonicalName} · {candidate.provinceName}</label>)}
              <button type="button" onClick={() => { setError(copy.recommendationClarify); document.getElementById(`profile-destination-${index}`)?.focus(); }}>{copy.noneOfThese}</button>
            </fieldset> : item.kind === 'resolved' || item.kind === 'confirmed' ? <p key={index} role="status" dir="auto">{item.destination.localizedNames[locale] ?? item.destination.canonicalName} · {item.kind === 'resolved' ? copy.catalogueMatch : copy.selectedByYou}</p> : item.kind === 'not-found' ? <p key={index} role="status">{item.originalPhrase}: {copy.recommendationClarify}</p> : null)}
            <button type="button" onClick={() => void confirmProfile()} disabled={busy || (!dirty && confirmed) || !online || !consentComplete}>{copy.confirmProfile}</button>
          </div>}
          {confirmed && <div className="recommendation-controls">
            <h3>{copy.recommendationTitle}</h3>
            <button type="button" onClick={() => void findRecommendations()} disabled={busy || !online}>{busy ? copy.checkingRecommendations : copy.findRecommendations}</button>
            {recommendations && recommendations.status !== 'available' && <div className="empty-state" role="status">
              <p>{recommendations.status === 'needs_confirmation' ? copy.recommendationClarify : copy.recommendationEmpty}</p>
              {recommendations.status === 'needs_confirmation' && <>
                {recommendations.reason_code && <p>{localizeRecommendationCode(locale, recommendations.reason_code)}</p>}
                {!!recommendations.unresolved_fields.length && <ul className="unresolved-requirements">
                  {recommendations.unresolved_fields.map(field => <li key={field}>{localizeRecommendationCode(locale, `field:${field}`)}</li>)}
                </ul>}
              </>}
            </div>}
            {!!recommendations?.not_evaluated_fields?.length && <div className="journey-alert not-evaluated-warning" role="status">
              <strong>{copy.requirementNotEvaluatedTitle}</strong>
              <p>{copy.requirementAdvisoryWarning}</p>
              <ul>{recommendations.not_evaluated_fields.map(field => <li key={field}>{localizeRecommendationCode(locale, `field:${field}`)}</li>)}</ul>
            </div>}
            {recommendations?.status === 'available' && recommendations.items.map(item => <article className="evidence-card" key={item.recommendation_id}>
              <h4 dir="auto">{item.localized_names[locale] ?? item.canonical_name}</h4>
              <p>{item.city_name ? `${item.city_name} · ` : ''}{item.province_name}</p>
              <p>{item.explanation_key === 'published_area_candidate' ? copy.explanationArea : copy.explanationMatch}</p>
              {!!item.matched_requirements.length && <p><strong>{copy.matched}:</strong> {item.matched_requirements.map(code => localizeRecommendationCode(locale, code)).join('، ')}</p>}
              {!!item.unknown_fields.length && <p><strong>{copy.unknown}:</strong> {item.unknown_fields.map(code => localizeRecommendationCode(locale, code)).join('، ')}</p>}
              {!!item.warnings.length && <p className="journey-alert"><strong>{copy.warnings}:</strong> {item.warnings.map(code => localizeRecommendationCode(locale, code)).join(' ')}</p>}
              <details><summary>{copy.evidence}</summary>{item.evidence.length ? item.evidence.map(source => <p key={source.source_id}>
                <a href={source.source_url} target="_blank" rel="noreferrer">{source.source_name}</a>{source.retrieved_at ? ` · ${copy.sourceRetrieved}: ${new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(new Date(source.retrieved_at))}` : ''}
              </p>) : <p>{copy.noEvidence}</p>}</details>
            </article>)}
            {recommendations?.status === 'available' && <div className="itinerary-start">
              <h3>{copy.itineraryTitle}</h3>
              <p>{copy.itinerarySuggestionWarning}</p>
              {!itinerary && <>
                <label htmlFor="journey-day-count">{copy.dayCount}</label>
                <input id="journey-day-count" type="number" min={1} max={Math.min(365, requestedTripDays ?? 365)} step={1} value={dayCount || ''}
                  aria-describedby="journey-day-count-help" aria-invalid={!dayCountValid}
                  onChange={event => setDayCount(event.currentTarget.value === '' ? 0 : event.currentTarget.valueAsNumber)} />
                <p id="journey-day-count-help">{copy.dayCountHelp}</p>
                {!dayCountValid && <p className="journey-error" role="alert">{copy.dayCountInvalid}</p>}
                <button type="button" onClick={() => void createItinerary()} disabled={busy || !online || !dayCountValid}>{copy.createItinerary}</button>
              </>}
              {itinerary && <p>{copy.itinerarySaved}</p>}
            </div>}
          </div>}
        </article>
      </div>}

      {itinerary && <section className="saved-itinerary" aria-labelledby="saved-itinerary-title">
        <h3 id="saved-itinerary-title">{copy.itineraryTitle}</h3>
        <p className={`itinerary-coverage itinerary-coverage-${displayedItineraryStatus ?? 'partial'}`} role="status">
          {displayedItineraryStatus === 'complete' ? copy.itineraryComplete : copy.itineraryPartial}
        </p>
        <p>{copy.itineraryCoverageNote}</p>
        <div className="saved-itinerary-days">
          {dayNumbers.map(day => {
            const dayStops = editableStops.filter(stop => stop.day_number === day).sort((a, b) => a.stop_order - b.stop_order);
            return <section className="itinerary-day" key={day} aria-labelledby={`itinerary-day-${day}`}>
              <h4 id={`itinerary-day-${day}`}>{copy.day} {formatNumber(locale, day)}</h4>
              {(dayStops.length === 0 || (!itineraryDirty && itinerary.unplanned_days.includes(day))) && <p className="unplanned-day" role="status">{copy.unplannedDay}</p>}
              <div className="saved-itinerary-stops">
                {dayStops.map((stop, index) => <article className="saved-stop" key={stop.recommendation_id}>
                  <h5 dir="auto">{stop.localized_names?.[locale] ?? stop.canonical_name ?? stop.name ?? ''}</h5>
                  <label htmlFor={`stop-day-${stop.recommendation_id}`}>{copy.dayCount}</label>
                  <select id={`stop-day-${stop.recommendation_id}`} value={stop.day_number} onChange={event => {
                    const newDay = Number(event.target.value);
                    setEditableStops(stops => assignStopToDay(stops, stop.recommendation_id, newDay));
                    setItineraryDirty(true);
                  }}>{dayNumbers.map(optionDay => <option value={optionDay} key={optionDay} disabled={optionDay !== stop.day_number && editableStops.filter(other => other.day_number === optionDay).length >= 50}>{copy.day} {formatNumber(locale, optionDay)}</option>)}</select>
                  <label htmlFor={`stop-note-${stop.recommendation_id}`}>{copy.noteLabel}</label>
                  <textarea id={`stop-note-${stop.recommendation_id}`} dir="auto" value={stop.notes_by_locale[locale] ?? ''} onChange={event => {
                    setEditableStops(stops => stops.map(item => item.recommendation_id === stop.recommendation_id
                      ? { ...item, notes_by_locale: { ...item.notes_by_locale, [locale]: event.target.value } } : item));
                    setItineraryDirty(true);
                  }} />
                  <div className="stop-actions">
                    <button type="button" aria-label={`${copy.moveEarlier} ${copy.day} ${formatNumber(locale, day)}`} onClick={() => moveStop(day, stop.recommendation_id, -1)} disabled={index === 0}>↑</button>
                    <button type="button" aria-label={`${copy.moveLater} ${copy.day} ${formatNumber(locale, day)}`} onClick={() => moveStop(day, stop.recommendation_id, 1)} disabled={index === dayStops.length - 1}>↓</button>
                    <button type="button" onClick={() => {
                      setEditableStops(stops => normalizeDayOrders(stops.filter(item => item.recommendation_id !== stop.recommendation_id), [day]));
                      setItineraryDirty(true);
                    }}>{copy.removeStop}</button>
                  </div>
                </article>)}
              </div>
            </section>;
          })}
        </div>
        {recommendations?.items && <div className="add-itinerary-stop">
          <label htmlFor="add-itinerary-stop">{copy.addStop}</label>
          <select id="add-itinerary-stop" defaultValue="" disabled={editableStops.length >= 1_000 || !dayNumbers.some(day => editableStops.filter(stop => stop.day_number === day).length < 50)} onChange={event => { if (event.target.value) appendStop(event.target.value); event.target.value = ''; }}>
            <option value="">{copy.selectTrip}</option>
            {recommendations.items.filter(item => !editableStops.some(stop => stop.recommendation_id === item.recommendation_id)).map(item => <option key={item.recommendation_id} value={item.recommendation_id}>{item.localized_names[locale] ?? item.canonical_name}</option>)}
          </select>
        </div>}
        <button type="button" onClick={() => void saveItinerary()} disabled={busy || !online || editableStops.length > 1_000 || editableStops.some(stop => editableStops.filter(other => other.day_number === stop.day_number).length > 50)}>{copy.saveItinerary}</button>
      </section>}

      {session && <section className="trip-history" aria-labelledby="trip-history-title">
        <div className="trip-history-heading"><h3 id="trip-history-title">{copy.historyTitle}</h3><button type="button" onClick={() => void travelerApi.listConversations(50).then(result => setConversations(result.items)).catch(applyFailure)} disabled={loadingHistory || busy}>{copy.retry}</button></div>
        {loadingHistory ? <p role="status">{copy.saving}</p> : conversations.length === 0 ? <p>{copy.historyEmpty}</p> : conversations.map(conversation => <article className="history-conversation" key={conversation.conversation_id}>
          {(conversation.trips ?? []).map(trip => <div className="history-trip" key={trip.trip_id}>
            <button type="button" onClick={() => void restoreTrip(conversation.conversation_id, trip.trip_id)} disabled={busy} dir="auto">{trip.original_request || copy.openTrip}</button>
            <button type="button" onClick={() => void deleteTrip(trip)} disabled={busy}>{copy.deleteTrip}</button>
          </div>)}
          <button type="button" onClick={() => void deleteConversation(conversation.conversation_id)} disabled={busy}>{copy.deleteConversation}</button>
        </article>)}
      </section>}
    </section>
  );
}
