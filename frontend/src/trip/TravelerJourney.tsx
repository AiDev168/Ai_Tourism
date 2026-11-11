import { useEffect, useMemo, useRef, useState } from 'react';
import type { AuthSession } from '../auth/authApi';
import { formatNumber, type Locale } from '../i18n/messages';
import { journeyMessages, localizeRecommendationCode } from '../i18n/journeyMessages';
import { createTripRequirements, type TripRequirements } from './tripIntake';
import { integrateTripFollowUp } from './followUpIntake';
import { normalizeDestinationName, resolveDestinationNames, confirmDestinationCandidate, type DestinationResolution, type ProductionDestinationCandidate } from './destinationResolution';
import { ApiDestinationCatalogPort } from './destinationCatalogApi';
import { reviewableAssistantCandidate } from './assistantCandidate';
import { tripRequirementsV1ToTripRequirements, type TripRequirementsV1 } from './tripIntake';
import { requirementClarificationMessages } from '../i18n/requirementClarificationMessages';
import { TravelerGuidance } from './TravelerGuidance';
import { nextTripQuestion } from './clarificationGuide';
import {
  travelerApi, TravelerApiError, parseRetrievalEvidence, type ConversationRecord, type ConversationSummary,
  type ItineraryRecord, type ItineraryStop, type RecommendationResult, type RequirementConsentDecision,
  type RequirementFieldCode, type TripRecord,
} from './travelerApi';

const catalog = new ApiDestinationCatalogPort();

export function LocationReference({ coordinate, locale }: { coordinate?: ProductionDestinationCandidate['coordinate']; locale: Locale }) {
  if (!coordinate) return null;
  const copy = journeyMessages[locale];
  const format = (value: number) => value.toLocaleString(locale, { maximumFractionDigits: 3 });
  return <p className="location-reference" role="note">
    {coordinate.role === 'visitor_entrance' ? copy.pointEntrance : copy.pointReference}
    {' '}{copy.pointCoordinates}: <bdi dir="ltr">{format(coordinate.latitude)}, {format(coordinate.longitude)}</bdi>
  </p>;
}

const assistantCopy: Record<Locale, {
  consent: string; send: string; review: string; initial: string; unavailable: string;
  destination: string; duration: string; apply: string; dismiss: string; unsaved: string; reviewSaved: string;
  speaker: string; promptsTitle: string; prompts: readonly string[];
  promptForAi: string; advisorActionHelp: string; promptHelp: string;
  saveWithoutAI: string; currentDuration: string;
  origin: string; travelerCount: string; budget: string; dates: string; interest: string;
}> = {
  'fa-IR': { consent: 'با ارسال این پیام و تاریخچهٔ گفت‌وگوی سفر به سرویس هوش مصنوعی موافقم.',
    send: 'پرسش از دستیار سفر', review: 'پیشنهاد مدل؛ پیش از تأیید سفر بررسی کنید:',
    initial: 'لطفاً برای سفر شرح‌داده‌شده سؤال تکمیلی مناسب بپرس.',
    unavailable: 'دستیار در حال حاضر در دسترس نیست؛ همچنان می‌توانید سفر را بدون آن ثبت کنید.',
    destination: 'مقصد پیشنهادی', duration: 'تعداد روز پیشنهادی',
    apply: 'انتقال به فرم سفر', dismiss: 'نادیده گرفتن', reviewSaved: 'بازبینی پیشنهاد ذخیره‌شده',
    unsaved: 'این پیشنهاد هنوز ذخیره یا تأیید نشده است. پس از انتقال، فرم سفر را بررسی و تأیید کنید.',
    origin: 'شهر مبدأ پیشنهادی', travelerCount: 'تعداد مسافران پیشنهادی',
    budget: 'بودجهٔ پیشنهادی', dates: 'تاریخ‌های پیشنهادی (میلادی)', interest: 'علاقهٔ پیشنهادی',
    speaker: 'مشاور هوش مصنوعی', promptsTitle: 'برای ادامه می‌توانید از مشاور بخواهید:',
    promptForAi: 'این عبارت یک درخواست از مشاور هوش مصنوعی است؛ برای ارسال، رضایت پردازش بیرونی را فعال و «پرسش از دستیار سفر» را انتخاب کنید.',
    advisorActionHelp: 'پرسش از دستیار: فقط با رضایت شما، پیام و سابقهٔ مرتبط سفر به سرویس هوش مصنوعی ارسال می‌شود.',
    promptHelp: 'انتخاب پرسش فقط پیش‌نویس را پر می‌کند؛ تا انتخاب یکی از اقدام‌های زیر چیزی ذخیره یا ارسال نمی‌شود.',
    saveWithoutAI: 'ثبت پاسخ بدون هوش مصنوعی',
    currentDuration: 'مدت ثبت‌شدهٔ این سفر: {days} روز.',
    prompts: ['دربارهٔ علایق و سبک سفرم یک سؤال تکمیلی بپرس.', 'برای روشن شدن بودجه و تعداد همراهانم سؤال بپرس.', 'محدودیت‌های ضروری سفرم را مرور کن و موارد مبهم را بپرس.'] },
  'en-US': { consent: 'I consent to sending this message and prior trip conversation to the AI service.',
    send: 'Ask travel assistant', review: 'AI suggestions — review before confirming:',
    initial: 'Please ask a useful clarification about the trip described above.',
    unavailable: 'The assistant is unavailable. You can still save your trip.',
    destination: 'Suggested destination', duration: 'Suggested days',
    apply: 'Use in trip form', dismiss: 'Dismiss', reviewSaved: 'Review saved suggestion',
    unsaved: 'Not saved or confirmed. Review and confirm the trip form after applying.',
    origin: 'Suggested departure city', travelerCount: 'Suggested travelers',
    budget: 'Suggested budget', dates: 'Suggested dates (Gregorian)', interest: 'Suggested interest',
    speaker: 'AI travel advisor', promptsTitle: 'Suggested follow-up questions:',
    promptForAi: 'This prompt is intended for the AI advisor. Consent to external processing and select “Ask travel assistant” to send it.',
    advisorActionHelp: 'Ask travel assistant sends the message and relevant trip history to the configured AI provider only with your consent.',
    promptHelp: 'Choosing a prompt only fills the draft. Nothing is saved or sent until you choose one of the actions below.',
    saveWithoutAI: 'Save reply without AI',
    currentDuration: 'Recorded trip length: {days} days.',
    prompts: ['Ask me about my interests and travel style.', 'Clarify my budget and number of travelers.', 'Review my essential constraints and ask what is unclear.'] },
  ar: { consent: 'أوافق على إرسال هذه الرسالة وسجل محادثة الرحلة إلى خدمة الذكاء الاصطناعي.',
    send: 'اسأل مساعد السفر', review: 'اقتراحات النموذج — راجعها قبل التأكيد:',
    initial: 'يرجى طرح سؤال توضيحي مناسب عن الرحلة المذكورة أعلاه.',
    unavailable: 'المساعد غير متاح حاليًا. يمكنك حفظ الرحلة بدونه.',
    destination: 'الوجهة المقترحة', duration: 'الأيام المقترحة',
    apply: 'نقل إلى نموذج الرحلة', dismiss: 'تجاهل', reviewSaved: 'مراجعة الاقتراح المحفوظ',
    unsaved: 'لم يُحفظ هذا الاقتراح أو يُؤكَّد. راجع نموذج الرحلة وأكّده بعد النقل.',
    origin: 'مدينة المغادرة المقترحة', travelerCount: 'عدد المسافرين المقترح',
    budget: 'الميزانية المقترحة', dates: 'التواريخ المقترحة (ميلادي)', interest: 'الاهتمام المقترح',
    speaker: 'مستشار السفر بالذكاء الاصطناعي', promptsTitle: 'يمكنك متابعة المحادثة عبر:',
    promptForAi: 'هذا طلب موجه إلى مستشار الذكاء الاصطناعي. وافق على المعالجة الخارجية ثم اختر «اسأل مساعد السفر».',
    advisorActionHelp: 'عند اختيار مستشار السفر وبموافقتك، تُرسل الرسالة وسجل الرحلة المرتبط إلى خدمة الذكاء الاصطناعي.',
    promptHelp: 'اختيار السؤال يملأ المسودة فقط؛ لا يُحفظ شيء ولا يُرسل حتى تختار أحد الإجراءين أدناه.',
    saveWithoutAI: 'احفظ الرد دون ذكاء اصطناعي',
    currentDuration: 'مدة الرحلة المسجلة: {days} يومًا.',
    prompts: ['اسألني عن اهتماماتي وطريقة سفري.', 'اسألني عن الميزانية وعدد المسافرين.', 'راجع الشروط الأساسية واسأل عن الأمور غير الواضحة.'] },
};

function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

function safeRequirements(value: unknown, locale: Locale): TripRequirements | null {
  if (!value || typeof value !== 'object') return null;
  const record = value as Record<string, unknown>;
  const possibleV1 = (record.requirements_v1 ?? value) as Partial<TripRequirementsV1>;
  if (possibleV1.contract_version === 'trip-requirements-v1'
      && possibleV1.fields && possibleV1.clarification
      && typeof possibleV1.original_text === 'string') {
    try { return tripRequirementsV1ToTripRequirements(possibleV1 as TripRequirementsV1); }
    catch { return null; }
  }
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

function parseReviewedBudget(text: string, locale: Locale): TripRequirements['budget']['value'] {
  if (!text.trim()) return null;
  const result = createTripRequirements({ requestText: text.trim(), locale });
  return result.kind === 'invalid' ? null : result.requirements.budget.value;
}

function validIsoDay(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/u.test(value)) return false;
  const date = new Date(value + 'T00:00:00Z');
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

function validTravelDates(start: string, end: string): boolean {
  return (!start && !end) || (validIsoDay(start) && validIsoDay(end) && start <= end);
}

function parseInterests(text: string): string[] {
  return [...new Set(text.split(/[,،؛;]/u).map(value => value.trim()).filter(Boolean))];
}

function consentFieldsForReviewedProfile(
  extracted: TripRequirements | null,
  origin: string,
  travelers: string,
  budget: string,
  dateStart: string,
  dateEnd: string,
): RequirementFieldCode[] {
  const fields = unresolvedConsentFields(extracted);
  if (origin.trim() && !fields.includes('origin')) fields.push('origin');
  if (travelers.trim() && !fields.includes('traveler_count')) fields.push('traveler_count');
  if (budget.trim() && !fields.includes('budget')) fields.push('budget');
  if ((dateStart || dateEnd) && !fields.includes('travel_dates')) fields.push('travel_dates');
  return fields;
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
  const [catalogueDestinations, setCatalogueDestinations] = useState<readonly ProductionDestinationCandidate[]>([]);
  const [catalogueOpen, setCatalogueOpen] = useState(false);
  const [catalogueLoading, setCatalogueLoading] = useState(false);
  const [catalogueUnavailable, setCatalogueUnavailable] = useState(false);
  const [catalogueSearch, setCatalogueSearch] = useState('');
  const [destinationNames, setDestinationNames] = useState<string[]>([]);
  const [durationText, setDurationText] = useState('');
  const [originText, setOriginText] = useState('');
  const [travelerCountText, setTravelerCountText] = useState('');
  const [budgetText, setBudgetText] = useState('');
  const [travelStartText, setTravelStartText] = useState('');
  const [travelEndText, setTravelEndText] = useState('');
  const [interestText, setInterestText] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [requirementChoices, setRequirementChoices] = useState<Partial<Record<RequirementFieldCode, RequirementConsentDecision>>>({});
  const [advisoryAcknowledgements, setAdvisoryAcknowledgements] = useState<Partial<Record<RequirementFieldCode, boolean>>>({});
  const [messageText, setMessageText] = useState('');
  const [assistantPromptSelected, setAssistantPromptSelected] = useState(false);
  const [remoteConsent, setRemoteConsent] = useState(false);
  const [assistantCandidate, setAssistantCandidate] = useState<unknown>(null);
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
  const resolutionSequenceRef = useRef(0);
  const catalogueBrowseSequenceRef = useRef(0);

  const extracted = useMemo(() => safeRequirements(activeTrip?.extracted_requirements, activeTrip?.locale ?? locale), [activeTrip, locale]);
  const consentFields = useMemo(() => consentFieldsForReviewedProfile(
    extracted, originText, travelerCountText, budgetText, travelStartText, travelEndText,
  ), [extracted, originText, travelerCountText, budgetText, travelStartText, travelEndText]);
  const budgetValid = !budgetText.trim() || parseReviewedBudget(budgetText, locale) !== null;
  const datesValid = validTravelDates(travelStartText, travelEndText);
  const interests = parseInterests(interestText);
  const interestsValid = interestText.length <= 300 && interests.length <= 10
    && interests.every(value => value.length <= 100 && !/[\u0000-\u001f\u007f]/u.test(value));
  const travelerCountValid = travelerCountText.trim() === '' || (/^[0-9]{1,2}$/.test(travelerCountText.trim())
    && Number(travelerCountText) >= 1 && Number(travelerCountText) <= 50);
  const consentComplete = consentIsComplete(consentFields, requirementChoices, advisoryAcknowledgements);
  const reviewedAssistantCandidate = reviewableAssistantCandidate(assistantCandidate);
  const requirementCopy = requirementClarificationMessages[locale];
  const guidedQuestion = activeTrip ? nextTripQuestion(locale, destinationNames, durationText) : null;
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

  const resolveNames = async (names: string[], explicitChoices: readonly { index: number; destinationId: string }[] = []) => {
    const sequence = ++resolutionSequenceRef.current;
    if (!names.length || names.some(name => !name.trim())) { setResolution(null); setCatalogueDestinations([]); return; }
    try {
      const catalogue = await catalog.load();
      if (sequence !== resolutionSequenceRef.current) return;
      setCatalogueDestinations(catalogue.kind === 'available' && catalogue.boundary === 'knowledge.production_destinations'
        ? catalogue.destinations : []);
      let resolved = resolveDestinationNames(names, locale, catalogue);
      for (const choice of explicitChoices) {
        resolved = confirmDestinationCandidate(resolved, choice.index, choice.destinationId);
      }
      setResolution(resolved);
    } catch {
      if (sequence !== resolutionSequenceRef.current) return;
      setCatalogueDestinations([]);
      setResolution(resolveDestinationNames(names, locale, { kind: 'unavailable' }));
    }
  };

  const browseCatalogue = async () => {
    if (!online || catalogueLoading) return;
    const sequence = ++catalogueBrowseSequenceRef.current;
    setCatalogueOpen(true); setCatalogueLoading(true); setCatalogueUnavailable(false);
    try {
      const result = await catalog.load();
      if (sequence !== catalogueBrowseSequenceRef.current) return;
      if (result.kind === 'available' && result.boundary === 'knowledge.production_destinations') setCatalogueDestinations(result.destinations);
      else { setCatalogueDestinations([]); setCatalogueUnavailable(true); }
    } catch {
      if (sequence !== catalogueBrowseSequenceRef.current) return;
      setCatalogueDestinations([]); setCatalogueUnavailable(true);
    } finally { if (sequence === catalogueBrowseSequenceRef.current) setCatalogueLoading(false); }
  };

  const addCatalogueDestination = (destination: ProductionDestinationCandidate) => {
    if (itineraryDirty && !window.confirm(copy.discardItineraryEdits)) return;
    const name = destination.localizedNames[locale] ?? destination.canonicalName;
    const selected = resolution?.items.flatMap(item => item.kind === 'resolved' || item.kind === 'confirmed'
      ? [item.destination.destinationId] : []) ?? [];
    if (selected.includes(destination.destinationId)) return;
    const ambiguousIndex = resolution?.items.findIndex(item => item.kind === 'ambiguous'
      && item.candidates.some(candidate => candidate.destinationId === destination.destinationId)
      && normalizeDestinationName(item.originalPhrase) === normalizeDestinationName(name)) ?? -1;
    if (ambiguousIndex >= 0 && resolution) {
      resolutionSequenceRef.current += 1;
      setResolution(confirmDestinationCandidate(resolution, ambiguousIndex, destination.destinationId));
      setDirty(true); invalidateConsent(); return;
    }
    const keptIndexes = destinationNames.map((item, index) => item.trim() ? index : -1).filter(index => index >= 0);
    const next = [...keptIndexes.map(index => destinationNames[index]), name];
    if (next.length > 50) return;
    const explicitChoices = keptIndexes.flatMap((oldIndex, index) => {
      const item = resolution?.items[oldIndex];
      return item?.kind === 'confirmed' ? [{ index, destinationId: item.destination.destinationId }] : [];
    });
    explicitChoices.push({ index: next.length - 1, destinationId: destination.destinationId });
    setDestinationNames(next); setDirty(true); invalidateConsent(); void resolveNames(next, explicitChoices);
  };

  useEffect(() => {
    let active = true;
    if (!session) {
      resolutionSequenceRef.current += 1;
      catalogueBrowseSequenceRef.current += 1;
      setCatalogueOpen(false); setCatalogueLoading(false); setCatalogueDestinations([]);
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
    return () => { active = false; resolutionSequenceRef.current += 1; catalogueBrowseSequenceRef.current += 1; };
  }, [session?.user.user_id]);

  useEffect(() => {
    if (requirements) {
      if (activeTrip && requirements.requestText !== activeTrip.original_request && restoringRequestRef.current !== requirements.requestText) {
        setDirty(true);
        setConfirmed(false);
        setRecommendations(null);
        setItinerary(null);
      }
      const restoring = restoringRequestRef.current === requirements.requestText;
      // The restored, traveler-reviewed profile is authoritative for the form.
      // Do not overwrite it with the older parser extraction from the parent.
      if (!(restoring && activeTrip?.confirmed_requirements.confirmation_source === 'traveler_reviewed')) {
        setDestinationNames(requirements.destinations.value ? [...requirements.destinations.value] : []);
        setDurationText(requirements.durationDays.value === null ? '' : String(requirements.durationDays.value));
        setOriginText(requirements.origin.value ?? '');
        setTravelerCountText(requirements.travelerCount.value === null ? '' : String(requirements.travelerCount.value));
        setBudgetText(requirements.budget.value?.raw ?? '');
        setTravelStartText(requirements.travelDates.value?.start ?? '');
        setTravelEndText(requirements.travelDates.value?.end ?? '');
        setInterestText(requirements.interests.value?.join('، ') ?? '');
        const suggestedDays = validDayCount(requirements.durationDays.value);
        if (!activeTrip?.latest_itinerary_id && suggestedDays !== null) setDayCount(suggestedDays);
        void resolveNames(requirements.destinations.value ?? []);
      }
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
      resolutionSequenceRef.current += 1;
      setResolution(null);
      setCatalogueDestinations([]);
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
      setAssistantCandidate(null);
      setRemoteConsent(false);
      const parsed = safeRequirements(trip.extracted_requirements, trip.locale);
      const hasReviewedProfile = trip.confirmed_requirements.confirmation_source === 'traveler_reviewed';
      const storedNames = trip.confirmed_requirements.destinations;
      const restoredNames = hasReviewedProfile && Array.isArray(storedNames)
        && storedNames.every(name => typeof name === 'string' && name.trim().length > 0 && name.length <= 100)
        ? storedNames as string[] : (parsed?.destinations.value ?? []);
      const restoredDays = hasReviewedProfile
        ? validDayCount(trip.confirmed_requirements.duration_days)
        : (parsed?.durationDays.value ?? null);
      setDestinationNames(restoredNames.slice());
      setDurationText(restoredDays === null ? '' : String(restoredDays));
      const approvedOrigin = trip.confirmed_requirements.origin;
      const restoredOrigin = hasReviewedProfile && typeof approvedOrigin === 'string' && approvedOrigin.length <= 100
        ? approvedOrigin : (parsed?.origin.value ?? '');
      const approvedCount = validDayCount(trip.confirmed_requirements.traveler_count);
      const restoredTravelerCount = hasReviewedProfile && approvedCount !== null && approvedCount <= 50
        ? String(approvedCount) : (parsed?.travelerCount.value === null || parsed?.travelerCount.value === undefined
          ? '' : String(parsed.travelerCount.value));
      setOriginText(restoredOrigin);
      setTravelerCountText(restoredTravelerCount);
      const savedBudget = trip.confirmed_requirements.budget;
      const restoredBudget = hasReviewedProfile && savedBudget && typeof savedBudget === 'object'
        && !Array.isArray(savedBudget) && typeof (savedBudget as Record<string, unknown>).raw === 'string'
        ? String((savedBudget as Record<string, unknown>).raw) : (parsed?.budget.value?.raw ?? '');
      const savedDates = trip.confirmed_requirements.travel_dates;
      const restoredDates = hasReviewedProfile && savedDates && typeof savedDates === 'object'
        && !Array.isArray(savedDates) ? savedDates as Record<string, unknown> : null;
      const restoredStart = typeof restoredDates?.start === 'string' ? restoredDates.start : (parsed?.travelDates.value?.start ?? '');
      const restoredEnd = typeof restoredDates?.end === 'string' ? restoredDates.end : (parsed?.travelDates.value?.end ?? '');
      const savedInterests = trip.confirmed_requirements.interests;
      const restoredInterests = hasReviewedProfile && Array.isArray(savedInterests)
        && savedInterests.every(value => typeof value === 'string')
        ? savedInterests as string[] : (parsed?.interests.value ?? []);
      setBudgetText(restoredBudget);
      setTravelStartText(restoredStart);
      setTravelEndText(restoredEnd);
      setInterestText(restoredInterests.join('، '));
      if (parsed) {
        restoringRequestRef.current = parsed.requestText;
        onRestoreRequest(parsed.requestText, parsed);
      }
      void resolveNames(restoredNames);
      const restoredConsentFields = consentFieldsForReviewedProfile(
        parsed, restoredOrigin, restoredTravelerCount, restoredBudget, restoredStart, restoredEnd,
      );
      const savedConsent = restoredConsent(trip, restoredConsentFields);
      setRequirementChoices(savedConsent?.decisions ?? {});
      setAdvisoryAcknowledgements(Object.fromEntries(
        (savedConsent?.acknowledgedFields ?? []).map(field => [field, true]),
      ) as Partial<Record<RequirementFieldCode, boolean>>);
      setConfirmed(hasReviewedProfile && savedConsent !== null
        && consentIsComplete(restoredConsentFields, savedConsent.decisions,
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
    if (!session || !activeConversation || !activeTrip || !messageText.trim() || !online) {
      if (!online) setError(copy.offline);
      return;
    }
    const initial = createTripRequirements({ requestText: activeTrip.original_request, locale: activeTrip.locale });
    const previous = safeRequirements(activeTrip.extracted_requirements, activeTrip.locale)
      ?? (initial.kind === 'invalid' ? null : initial.requirements);
    if (!previous) { setError(copy.genericError); return; }
    // Parse the new utterance on its own. The original 1200-character request
    // remains unchanged; later explicit corrections do not become conflicts
    // merely because an earlier value also appears in the history.
    const parsed = integrateTripFollowUp(
      previous, messageText.trim(), activeTrip.locale, activeTrip.confirmed_requirements,
    );
    if (parsed.kind === 'invalid') { setError(copy.followUpInvalid); return; }
    setBusy(true); setError(''); setStatus('');
    try {
      const result = await travelerApi.appendMessage(csrf, activeConversation.conversation_id, {
        trip_id: activeTrip.trip_id,
        content: messageText.trim(),
        extracted_requirements: parsed.requirements,
        idempotency_key: newIdempotencyKey(),
        expected_version: activeConversation.version,
      });
      setActiveConversation(result.conversation);
      setActiveTrip(result.trip);
      setMessageText('');
      setAssistantPromptSelected(false);
      setAssistantCandidate(null);
      setConfirmed(false); setRequirementChoices({}); setAdvisoryAcknowledgements({});
      setRecommendations(null); setItinerary(null);
      const latest = safeRequirements(result.trip.extracted_requirements, result.trip.locale);
      setStatus(latest?.extractionStatus === 'needs_clarification'
        ? copy.followUpNeedsReview : copy.messageSaved);
      if (latest) {
        setDestinationNames(latest.destinations.value?.slice() ?? []);
        setDurationText(latest.durationDays.value === null ? '' : String(latest.durationDays.value));
        setOriginText(latest.origin.value ?? '');
        setTravelerCountText(latest.travelerCount.value === null ? '' : String(latest.travelerCount.value));
        setBudgetText(latest.budget.value?.raw ?? '');
        setTravelStartText(latest.travelDates.value?.start ?? '');
        setTravelEndText(latest.travelDates.value?.end ?? '');
        setInterestText(latest.interests.value?.join('، ') ?? '');
        restoringRequestRef.current = latest.requestText;
        onRestoreRequest(latest.requestText, latest);
        void resolveNames(latest.destinations.value ?? []);
      }
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const askAssistant = async () => {
    if (!session || !activeConversation || !activeTrip || !remoteConsent || !online) return;
    const content = messageText.trim() || assistantCopy[locale].initial;
    if (content.length > 1200) return;
    setBusy(true); setError(''); setStatus('');
    setAssistantCandidate(null);
    try {
      const result = await travelerApi.assistantTurn(csrf, activeConversation.conversation_id, {
        trip_id: activeTrip.trip_id,
        content,
        idempotency_key: newIdempotencyKey(),
        expected_version: activeConversation.version,
        remote_processing_consent: true,
      });
      setActiveConversation(result.conversation);
      setActiveTrip(result.trip);
      setAssistantCandidate(result.candidate_requirements);
      setMessageText('');
      setAssistantPromptSelected(false);
      // AI replies are advisory: do not reset consent, the reviewed trip,
      // recommendations, or a saved itinerary after a chat message.
    } catch (value) {
      // A provider outage is different from an unavailable destination catalogue.
      if (value instanceof TravelerApiError && value.status === 503) {
        setError(assistantCopy[locale].unavailable);
      } else {
        applyFailure(value);
      }
      // A failed provider request still persists the user turn. Refresh the
      // optimistic version so a subsequent explicit attempt is not stale.
      try {
        const [conversation, trip] = await Promise.all([
          travelerApi.getConversation(activeConversation.conversation_id),
          travelerApi.getTrip(activeTrip.trip_id),
        ]);
        setActiveConversation(conversation); setActiveTrip(trip);
      } catch { /* Keep the original safe error. */ }
    } finally { setBusy(false); }
  };

  const applyAssistantCandidate = () => {
    if (!reviewedAssistantCandidate || !activeTrip) return;
    if (reviewedAssistantCandidate.destination !== null) {
      const names = [reviewedAssistantCandidate.destination];
      setDestinationNames(names);
      void resolveNames(names); // Catalogue verification is separate from AI text.
    }
    if (reviewedAssistantCandidate.durationDays !== null) {
      setDurationText(String(reviewedAssistantCandidate.durationDays));
    }
    if (reviewedAssistantCandidate.origin !== undefined) {
      setOriginText(reviewedAssistantCandidate.origin);
    }
    if (reviewedAssistantCandidate.travelerCount !== undefined) {
      setTravelerCountText(String(reviewedAssistantCandidate.travelerCount));
    }
    if (reviewedAssistantCandidate.budgetText !== undefined) {
      setBudgetText(reviewedAssistantCandidate.budgetText);
    }
    if (reviewedAssistantCandidate.travelStart !== undefined && reviewedAssistantCandidate.travelEnd !== undefined) {
      setTravelStartText(reviewedAssistantCandidate.travelStart);
      setTravelEndText(reviewedAssistantCandidate.travelEnd);
    }
    if (reviewedAssistantCandidate.interest !== undefined) {
      setInterestText(current => parseInterests([current, reviewedAssistantCandidate.interest!].filter(Boolean).join('، ')).join('، '));
    }
    setDirty(true);
    invalidateConsent(); // Explicit profile confirmation remains mandatory.
    setAssistantCandidate(null);
  };

  const confirmProfile = async () => {
    if (!session || !activeTrip || !online || !consentComplete || !travelerCountValid
        || !budgetValid || !datesValid || !interestsValid) {
      if (!online) setError(copy.offline);
      else if (!travelerCountValid) setError(copy.profileTravelersInvalid);
      else if (!budgetValid) setError(copy.profileBudgetInvalid);
      else if (!datesValid) setError(copy.profileDatesInvalid);
      else if (!interestsValid) setError(copy.profileInterestsInvalid);
      return;
    }
    setBusy(true); setError(''); setStatus('');
    const duration = durationText.trim() === '' ? null : Number(durationText);
    const confirmedRequirements = {
      destinations: destinationNames.map(name => name.trim()).filter(Boolean),
      duration_days: duration,
      origin: originText.trim() || null,
      travel_dates: travelStartText && travelEndText
        ? { start: travelStartText, end: travelEndText } : (extracted?.travelDates.value ?? null),
      traveler_count: travelerCountText.trim() ? Number(travelerCountText.trim()) : null,
      accessibility: extracted?.accessibility?.value ?? [],
      budget: parseReviewedBudget(budgetText, locale) ?? extracted?.budget.value ?? null,
      soft_preferences: extracted?.softPreferences.value ?? [],
      interests: interests.length ? interests : (extracted?.interests.value ?? []),
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

      <TravelerGuidance locale={locale} hasTrip={Boolean(activeTrip)} confirmed={confirmed}
        hasRecommendations={Boolean(recommendations)} hasItinerary={Boolean(itinerary)} />
      <p className="privacy-notice">{copy.privacyNotice}</p>
      {!session && <p className="trip-form-help">{copy.signInToSave}</p>}
      {dirty && activeTrip && <p className="journey-alert" role="status">{copy.draftChanged}</p>}
      {error && <p className="journey-error" role="alert">{error}</p>}
      {status && <p className="journey-status" role="status">{status}</p>}

      {requirements && !activeTrip && <button className="primary journey-action" type="button" onClick={() => void persistDraft()} disabled={busy || !session || !online}>
        {busy ? copy.saving : activeConversation ? copy.createAnotherTrip : copy.saveTrip}
      </button>}
      {requirements && activeTrip && dirty && session
        && requirements.requestText !== activeTrip.original_request
        && <button className="primary journey-action" type="button" onClick={() => void (async () => {
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
        <button type="button" onClick={() => { setActiveTrip(null); setAssistantCandidate(null); setRemoteConsent(false); setConfirmed(false); setRequirementChoices({}); setAdvisoryAcknowledgements({}); setRecommendations(null); setItinerary(null); setDirty(false); setResolution(null); onStartNewDraft(); }}>{copy.createAnotherTrip}</button>
        <button type="button" onClick={() => { setActiveConversation(null); setActiveTrip(null); setAssistantCandidate(null); setRemoteConsent(false); setConfirmed(false); setRequirementChoices({}); setAdvisoryAcknowledgements({}); setRecommendations(null); setItinerary(null); setDirty(false); setResolution(null); onStartNewDraft(); }}>{copy.startNewConversation}</button>
      </div>}

      {activeTrip && activeConversation && <div className="journey-columns">
        <article className="conversation-panel journey-panel">
          <div className="panel-title"><span className="mini-icon" aria-hidden="true">✳</span><span>{copy.continueTitle}</span></div>
          {requestedTripDays !== null && <p className="conversation-trip-duration" role="status">
            {assistantCopy[locale].currentDuration.replace('{days}', formatNumber(locale, requestedTripDays))}
          </p>}
          <div className="conversation-transcript" aria-live="polite">
            {currentMessages.map(message => <div className={`saved-message saved-message-${message.role}`} key={message.message_id}>
              <small>{message.role === 'user' ? activeTrip.locale : assistantCopy[locale].speaker}</small>
              <p dir="auto">{message.content}</p>
              {message.role === 'assistant' &&
                reviewableAssistantCandidate(message.candidate_requirements ?? null) &&
                <button type="button" disabled={busy}
                  onClick={() => setAssistantCandidate(message.candidate_requirements ?? null)}>
                  {assistantCopy[locale].reviewSaved}
                </button>}
            </div>)}
            {!currentMessages.length && <p>{copy.emptyAssistant}</p>}
          </div>
          {guidedQuestion && <div className="traveler-clarification" role="status">
            <strong>{guidedQuestion.question}</strong>
            <p>{guidedQuestion.instruction}</p>
            <button type="button" disabled={busy || !online} onClick={() => {
              document.getElementById('trip-follow-up')?.focus();
            }}>{guidedQuestion.answerLabel}</button>
          </div>}
          <div className="assistant-prompt-suggestions" aria-label={assistantCopy[locale].promptsTitle}>
            <p>{assistantCopy[locale].promptsTitle}</p>
            <p>{assistantCopy[locale].promptHelp}</p>
            <div>{assistantCopy[locale].prompts.map(prompt => <button key={prompt} type="button"
              disabled={busy || !online} onClick={() => {
                setMessageText(prompt);
                setAssistantPromptSelected(true);
                document.getElementById('trip-follow-up')?.focus();
              }}>{prompt}</button>)}</div>
          </div>
          <label htmlFor="trip-follow-up">{copy.messagePlaceholder}</label>
          <textarea id="trip-follow-up" value={messageText}
            onChange={event => { setMessageText(event.target.value); setAssistantPromptSelected(false); }}
            maxLength={1200} rows={3} dir="auto" />
          {assistantPromptSelected && <p className="assistant-prompt-warning" role="status">{assistantCopy[locale].promptForAi}</p>}
          <div className="conversation-local-action">
            <button type="button" onClick={() => void sendMessage()}
              disabled={busy || !messageText.trim() || !online || assistantPromptSelected}>{assistantCopy[locale].saveWithoutAI}</button>
            <small>{copy.localSaveHelp}</small>
          </div>
          <div className="assistant-controls">
            <label htmlFor="assistant-remote-consent">
              <input id="assistant-remote-consent" type="checkbox" checked={remoteConsent}
                onChange={event => setRemoteConsent(event.currentTarget.checked)} />
              {assistantCopy[locale].consent}
            </label>
            <p className="assistant-action-help">{assistantCopy[locale].advisorActionHelp}</p>
            <button className="primary" type="button" onClick={() => void askAssistant()}
              disabled={busy || !online || !remoteConsent || messageText.length > 1200}>
              {assistantCopy[locale].send}
            </button>
            {reviewedAssistantCandidate &&
              <div className="assistant-candidate" role="status">
                <strong>{assistantCopy[locale].review}</strong>
                {reviewedAssistantCandidate.typedRequirements && <dl className="assistant-candidate-evidence">
                  {Object.entries(reviewedAssistantCandidate.typedRequirements.fields).map(([fieldName, field]) => {
                    const labels = requirementCopy.fieldLabels;
                    const label = labels[fieldName] ?? fieldName;
                    const value = field.value;
                    const evidence = field.evidence_span?.text;
                    const state = field.status === 'known' ? requirementCopy.known
                      : field.status === 'ambiguous' ? requirementCopy.ambiguous : requirementCopy.unresolved;
                    return <div key={fieldName}>
                      <dt>{label}</dt><dd>{state}{value === undefined || value === null ? '' : `: ${typeof value === 'string' ? value : JSON.stringify(value)}`}</dd>
                      {evidence && <><dt>{requirementCopy.evidence}</dt><dd dir="auto">{evidence}</dd></>}
                    </div>;
                  })}
                  {!!reviewedAssistantCandidate.typedRequirements.clarification.question_fields.length && <div>
                    <dt>{requirementCopy.unresolved}</dt>
                    <dd>{reviewedAssistantCandidate.typedRequirements.clarification.question_fields.map(field => requirementCopy.fieldLabels[field.split('.')[0]] ?? field).join('، ')}</dd>
                  </div>}
                </dl>}
                <dl>
                  {reviewedAssistantCandidate.destination !== null && <>
                    <dt>{assistantCopy[locale].destination}</dt>
                    <dd dir="auto">{reviewedAssistantCandidate.destination}</dd>
                  </>}
                  {reviewedAssistantCandidate.durationDays !== null && <>
                    <dt>{assistantCopy[locale].duration}</dt>
                    <dd>{formatNumber(locale, reviewedAssistantCandidate.durationDays)}</dd>
                  </>}
                  {reviewedAssistantCandidate.origin !== undefined && <>
                    <dt>{assistantCopy[locale].origin}</dt>
                    <dd dir="auto">{reviewedAssistantCandidate.origin}</dd>
                  </>}
                  {reviewedAssistantCandidate.travelerCount !== undefined && <>
                    <dt>{assistantCopy[locale].travelerCount}</dt>
                    <dd>{formatNumber(locale, reviewedAssistantCandidate.travelerCount)}</dd>
                  </>}
                  {reviewedAssistantCandidate.budgetText !== undefined && <>
                    <dt>{assistantCopy[locale].budget}</dt>
                    <dd dir="auto">{reviewedAssistantCandidate.budgetText}</dd>
                  </>}
                  {reviewedAssistantCandidate.travelStart !== undefined && reviewedAssistantCandidate.travelEnd !== undefined && <>
                    <dt>{assistantCopy[locale].dates}</dt>
                    <dd dir="ltr">{reviewedAssistantCandidate.travelStart} – {reviewedAssistantCandidate.travelEnd}</dd>
                  </>}
                  {reviewedAssistantCandidate.interest !== undefined && <>
                    <dt>{assistantCopy[locale].interest}</dt>
                    <dd dir="auto">{reviewedAssistantCandidate.interest}</dd>
                  </>}
                </dl>
                <p>{assistantCopy[locale].unsaved}</p>
                <button type="button" onClick={applyAssistantCandidate} disabled={busy}>{assistantCopy[locale].apply}</button>
                <button type="button" onClick={() => setAssistantCandidate(null)} disabled={busy}>{assistantCopy[locale].dismiss}</button>
              </div>}
          </div>
        </article>

        <article className="recommend-panel journey-panel" id="journey-recommendations">
          <div className="panel-title"><span className="mini-icon" aria-hidden="true">↗</span>{copy.profileTitle}</div>
          {extracted && <div className="profile-editor">
            <fieldset>
              <legend>{copy.profileDestination}</legend>
              {destinationNames.map((name, index) => <div className="destination-edit-row" key={index}>
                <label htmlFor={`profile-destination-${index}`}>{copy.profileDestination} {formatNumber(locale, index + 1)}</label>
                <input id={`profile-destination-${index}`} value={name} onChange={event => {
                  const next = destinationNames.slice(); next[index] = event.target.value; setDestinationNames(next); setDirty(true); invalidateConsent(); void resolveNames(next);
                }} dir="auto" />
                <button type="button" aria-label={`${copy.removeDestination}: ${name}`} onClick={() => { const next = destinationNames.filter((_, item) => item !== index); setDestinationNames(next); setDirty(true); invalidateConsent(); void resolveNames(next); }}>{copy.removeDestination}</button>
              </div>)}
              <button type="button" onClick={() => { const next = [...destinationNames, '']; setDestinationNames(next); setDirty(true); invalidateConsent(); setResolution(null); }}>{copy.profileDestination} +</button>
              <button type="button" aria-expanded={catalogueOpen} aria-controls="approved-destination-browser"
                onClick={() => { if (catalogueOpen) setCatalogueOpen(false); else void browseCatalogue(); }}
                disabled={!online || catalogueLoading}>{copy.browseDestinations}</button>
              {catalogueOpen && <div id="approved-destination-browser" className="approved-destination-browser">
                {catalogueLoading ? <p role="status">{copy.checkingRecommendations}</p> : catalogueUnavailable
                  ? <p className="journey-error" role="alert">{copy.recommendationUnavailable}</p> : catalogueDestinations.length === 0
                    ? <p role="status">{copy.recommendationEmpty}</p> : <>
                      <label htmlFor="approved-destination-search">{copy.searchDestinations}</label>
                      <input id="approved-destination-search" type="search" value={catalogueSearch} dir="auto"
                        onChange={event => setCatalogueSearch(event.target.value)} />
                      {(() => {
                        const query = normalizeDestinationName(catalogueSearch);
                        const matches = catalogueDestinations.filter(destination => !query || [
                          destination.canonicalName, ...Object.values(destination.localizedNames),
                          destination.cityName, destination.provinceName, ...destination.aliases.map(alias => alias.value),
                        ].some(value => typeof value === 'string' && normalizeDestinationName(value).includes(query)));
                        return matches.length ? <ul>{matches.map(destination => {
                          const name = destination.localizedNames[locale] ?? destination.canonicalName;
                          const selected = resolution?.items.some(item => (item.kind === 'resolved' || item.kind === 'confirmed')
                            && item.destination.destinationId === destination.destinationId) ?? false;
                          return <li key={destination.destinationId}>
                            <span dir="auto">{name} · {destination.cityName ?? destination.provinceName}</span>
                            <LocationReference locale={locale} coordinate={destination.coordinate} />
                            <button type="button" disabled={selected || destinationNames.filter(item => item.trim()).length >= 50}
                              aria-label={`${copy.addDestination}: ${name} · ${destination.cityName ?? destination.provinceName ?? ''}`} onClick={() => addCatalogueDestination(destination)}>{selected ? copy.selectedByYou : copy.addDestination}</button>
                          </li>;
                        })}</ul> : <p role="status">{copy.noDestinationMatches}</p>;
                      })()}
                    </>}
              </div>}
              {!destinationNames.length && <p>{copy.noDestination}</p>}
            </fieldset>
            <label htmlFor="profile-duration">{copy.profileDuration}</label>
            <input id="profile-duration" type="number" min="1" max="365" value={durationText} onChange={event => { setDurationText(event.target.value); setDirty(true); invalidateConsent(); }} />
            <label htmlFor="profile-origin">{copy.profileOrigin}</label>
            <input id="profile-origin" type="text" maxLength={100} dir="auto" value={originText}
              onChange={event => { setOriginText(event.target.value); setDirty(true); invalidateConsent(); }} />
            <label htmlFor="profile-travelers">{copy.profileTravelers}</label>
            <input id="profile-travelers" type="number" min="1" max="50" step="1" value={travelerCountText}
              aria-invalid={!travelerCountValid} onChange={event => { setTravelerCountText(event.target.value); setDirty(true); invalidateConsent(); }} />
            {!travelerCountValid && <p className="journey-error" role="alert">{copy.profileTravelersInvalid}</p>}
            <label htmlFor="profile-budget">{copy.profileBudget}</label>
            <input id="profile-budget" type="text" maxLength={100} dir="auto" value={budgetText}
              onChange={event => { setBudgetText(event.target.value); setDirty(true); invalidateConsent(); }} />
            {!budgetValid && <p className="journey-error" role="alert">{copy.profileBudgetInvalid}</p>}
            <label htmlFor="profile-travel-start">{copy.profileTravelStart}</label>
            <input id="profile-travel-start" type="date" value={travelStartText}
              onChange={event => { setTravelStartText(event.target.value); setDirty(true); invalidateConsent(); }} />
            <label htmlFor="profile-travel-end">{copy.profileTravelEnd}</label>
            <input id="profile-travel-end" type="date" value={travelEndText}
              onChange={event => { setTravelEndText(event.target.value); setDirty(true); invalidateConsent(); }} />
            {!datesValid && <p className="journey-error" role="alert">{copy.profileDatesInvalid}</p>}
            <label htmlFor="profile-interests">{copy.profileInterests}</label>
            <textarea id="profile-interests" maxLength={300} rows={2} dir="auto" value={interestText}
              onChange={event => { setInterestText(event.target.value); setDirty(true); invalidateConsent(); }} />
            {!interestsValid && <p className="journey-error" role="alert">{copy.profileInterestsInvalid}</p>}
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
              {item.candidates.map(candidate => <label key={candidate.destinationId} dir="auto"><input type="radio" name={`traveler-choice-${index}`} checked={resolution.items[index]?.kind === 'confirmed' && resolution.items[index].destination.destinationId === candidate.destinationId} onChange={() => { resolutionSequenceRef.current += 1; setResolution(current => current ? confirmDestinationCandidate(current, index, candidate.destinationId) : current); }} />{candidate.localizedNames[locale] ?? candidate.canonicalName} · {candidate.provinceName}</label>)}
              <button type="button" onClick={() => { setError(copy.recommendationClarify); document.getElementById(`profile-destination-${index}`)?.focus(); }}>{copy.noneOfThese}</button>
            </fieldset> : item.kind === 'resolved' || item.kind === 'confirmed' ? <p key={index} role="status" dir="auto">{item.destination.localizedNames[locale] ?? item.destination.canonicalName} · {item.kind === 'resolved' ? copy.catalogueMatch : copy.selectedByYou}</p> : item.kind === 'not-found' ? <p key={index} role="status">{item.originalPhrase}: {copy.recommendationClarify}</p> : null)}
            <button type="button" onClick={() => void confirmProfile()} disabled={busy || (!dirty && confirmed) || !online || !consentComplete || !travelerCountValid
              || !budgetValid || !datesValid || !interestsValid}>{copy.confirmProfile}</button>
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
              <LocationReference locale={locale} coordinate={catalogueDestinations.find(destination => destination.destinationId === item.destination_id)?.coordinate} />
              <p>{item.explanation_key === 'published_area_candidate' ? copy.explanationArea : copy.explanationMatch}</p>
              {!!item.matched_requirements.length && <p><strong>{copy.matched}:</strong> {item.matched_requirements.map(code => localizeRecommendationCode(locale, code)).join('، ')}</p>}
              {!!item.unknown_fields.length && <p><strong>{copy.unknown}:</strong> {item.unknown_fields.map(code => localizeRecommendationCode(locale, code)).join('، ')}</p>}
              {!!item.warnings.length && <p className="journey-alert"><strong>{copy.warnings}:</strong> {item.warnings.map(code => localizeRecommendationCode(locale, code)).join(' ')}</p>}
              <details><summary>{copy.evidence}</summary>{item.evidence.length ? item.evidence.map(source => <p key={source.source_id}>
                <a href={source.source_url} target="_blank" rel="noreferrer">{source.source_name}</a>{source.retrieved_at ? ` · ${copy.sourceRetrieved}: ${new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(new Date(source.retrieved_at))}` : ''}
              </p>) : <p>{copy.noEvidence}</p>}</details>
            </article>)}
            {recommendations?.status === 'available' && (() => {
              const citationCards = recommendations.items.flatMap(item =>
                parseRetrievalEvidence(item.retrieval_evidence, item.destination_id, locale)
                  .map(citation => ({ item, citation })),
              );
              return citationCards.length > 0 ? <section className="retrieval-citations-list" aria-label={copy.retrievalEvidenceTitle}>
                {citationCards.map(({ item, citation }) => <article className="retrieval-citation" key={citation.evidence_id}>
                  <h4 dir="auto">{item.localized_names[locale] ?? item.canonical_name}</h4>
                  <p className="retrieval-citation-boundary">{copy.retrievalEvidenceBoundary}</p>
                  <strong>{copy.retrievalClaimLabel}</strong>
                  <blockquote dir="auto">{citation.text}</blockquote>
                  <ul>{citation.sources.map(source => <li key={source.source_id}>
                    <a href={source.source_url} target="_blank" rel="noreferrer">{source.source_name}</a>
                    {source.retrieved_at ? ` · ${copy.sourceRetrieved}: ${new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(new Date(source.retrieved_at))}` : ''}
                  </li>)}</ul>
                </article>)}
              </section> : null;
            })()}
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
        {(itinerary.warning_codes ?? []).map(code => <p className="itinerary-warning" role="note" key={code}>{copy.itineraryWarnings[code as keyof typeof copy.itineraryWarnings] ?? copy.itinerarySuggestionWarning}</p>)}
        <div className="saved-itinerary-days">
          {dayNumbers.map(day => {
            const dayStops = editableStops.filter(stop => stop.day_number === day).sort((a, b) => a.stop_order - b.stop_order);
            return <section className="itinerary-day" key={day} aria-labelledby={`itinerary-day-${day}`}>
              <h4 id={`itinerary-day-${day}`}>{copy.day} {formatNumber(locale, day)}</h4>
              {(dayStops.length === 0 || (!itineraryDirty && itinerary.unplanned_days.includes(day))) && <p className="unplanned-day" role="status">{copy.unplannedDay}</p>}
              <div className="saved-itinerary-stops">
                {dayStops.map((stop, index) => <article className="saved-stop" key={stop.recommendation_id}>
                  <h5 dir="auto">{stop.localized_names?.[locale] ?? stop.canonical_name ?? stop.name ?? ''}</h5>
                  <LocationReference locale={locale} coordinate={catalogueDestinations.find(destination => destination.destinationId === stop.destination_id)?.coordinate} />
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
