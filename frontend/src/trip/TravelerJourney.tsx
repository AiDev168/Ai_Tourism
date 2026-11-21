import { useEffect, useMemo, useRef, useState } from 'react';
import type { AuthSession } from '../auth/authApi';
import { formatNumber, type Locale } from '../i18n/messages';
import { journeyMessages, localizeRecommendationCode } from '../i18n/journeyMessages';
import { createTripRequirements, inclusiveEndDate, requirementsForPersistence, type TripRequirements } from './tripIntake';
import { integrateTripFollowUp } from './followUpIntake';
import { normalizeDestinationName, resolveDestinationNames, confirmDestinationCandidate, type DestinationResolution, type ProductionDestinationCandidate } from './destinationResolution';
import { ApiDestinationCatalogPort } from './destinationCatalogApi';
import { assistantMayReplaceField, reviewableAssistantCandidate } from './assistantCandidate';
import { tripRequirementsV1ToTripRequirements, type TripRequirementsV1 } from './tripIntake';
import { requirementClarificationMessages } from '../i18n/requirementClarificationMessages';
import { TravelerGuidance } from './TravelerGuidance';
import { nextTripQuestion } from './clarificationGuide';
import { displayTripInterest, reviewedTripInterests } from './interestDisplay';
import { JalaliDatePicker } from './JalaliDatePicker';
import { TravelerCompanyResponses } from './TravelerCompanyResponses';
import { deviceCalendarDate } from './jalaliDate';
import {
  travelerApi, TravelerApiError, parseRetrievalEvidence, type ConversationRecord, type ConversationSummary,
  type ItineraryRecord, type ItineraryStop, type ProvisionalDay, type ProvisionalItinerary, type ProvisionalStop,
  type RecommendationResult, type RequirementConsentDecision,
  type RequirementFieldCode, type TripRecord,
} from './travelerApi';

const catalog = new ApiDestinationCatalogPort();

const provisionalText: Record<Locale, { title: string; heading: string; warning: string; save: string; saved: string; edit: string; name: string; note: string; move: string; remove: string; add: string; saveChanges: string; model: string; traveler: string }> = {
  'fa-IR': {
    title: 'پیش‌نویس برنامه سفر', heading: 'برنامه پیشنهادی موقت',
    warning: 'این برنامه تأییدنشده است. نام مکان‌ها فقط پیشنهاد اولیه‌اند؛ ساعت کار، قیمت، مسیر، دسترسی و ایمنی بررسی نشده‌اند.',
    save: 'ذخیره پیش‌نویس موقت', saved: 'پیش‌نویس موقت ذخیره شد.', edit: 'ویرایش برنامه موقت', name: 'نام مکان پیشنهادی',
    note: 'یادداشت شما', move: 'انتقال به روز', remove: 'حذف', add: 'افزودن مکانِ واردشده توسط شما', saveChanges: 'ذخیره ویرایش‌ها',
    model: 'پیشنهاد هوش مصنوعی؛ تأییدنشده', traveler: 'مکان واردشده توسط شما',
  },
  'en-US': {
    title: 'Provisional trip draft', heading: 'Preliminary trip plan',
    warning: 'This plan is unverified. Place names are preliminary suggestions; hours, prices, routes, access and safety have not been checked.',
    save: 'Save provisional draft', saved: 'Provisional draft saved.', edit: 'Edit provisional plan', name: 'Suggested place name',
    note: 'Your note', move: 'Move to day', remove: 'Remove', add: 'Add a place you provide', saveChanges: 'Save edits',
    model: 'AI suggestion; unverified', traveler: 'Place provided by you',
  },
  ar: {
    title: 'مسودة رحلة مؤقتة', heading: 'خطة أولية للرحلة',
    warning: 'هذه الخطة غير موثقة. الأسماء اقتراحات أولية؛ ولم يتم التحقق من ساعات العمل أو الأسعار أو الطرق أو إمكانية الوصول أو السلامة.',
    save: 'حفظ المسودة المؤقتة', saved: 'حُفظت المسودة المؤقتة.', edit: 'تعديل الخطة المؤقتة', name: 'اسم المكان المقترح',
    note: 'ملاحظتك', move: 'النقل إلى اليوم', remove: 'حذف', add: 'إضافة مكان تحدده أنت', saveChanges: 'حفظ التعديلات',
    model: 'اقتراح ذكاء اصطناعي غير موثق', traveler: 'مكان أدخلته أنت',
  },
};

const chatFlowCopy: Record<Locale, { start: string; conversation: string; oneDay: string; twoDays: string; review: string; relativeDate: string }> = {
  'fa-IR': { start: 'ذخیرهٔ درخواست و شروع گفت‌وگو', conversation: 'گفت‌وگوی همین سفر', oneDay: 'یک روز', twoDays: 'دو روز', review: 'گام بعد: اطلاعات سفر را بررسی و تأیید کنید', relativeDate: 'گفتید حرکت فردا یا چند روز دیگر است. تاریخ شروع و پایان را بر اساس تقویم خودتان انتخاب و تأیید کنید؛ ما تاریخ را از ساعت سرور حدس نمی‌زنیم.' },
  'en-US': { start: 'Save request and start conversation', conversation: 'This trip’s conversation', oneDay: 'One day', twoDays: 'Two days', review: 'Next: review and confirm your trip details', relativeDate: 'You gave a relative departure date. Select and confirm calendar dates in your timezone; we do not guess them from the server clock.' },
  ar: { start: 'احفظ الطلب وابدأ المحادثة', conversation: 'محادثة هذه الرحلة', oneDay: 'يوم واحد', twoDays: 'يومان', review: 'التالي: راجع تفاصيل الرحلة وأكدها', relativeDate: 'ذكرت موعد مغادرة نسبيًا. اختر تاريخ البداية والنهاية وفق تقويمك وأكدهما؛ لا نخمن التاريخ من ساعة الخادم.' },
};

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
  send: string; review: string; initial: string; unavailable: string;
  destination: string; duration: string; apply: string; dismiss: string; unsaved: string; reviewSaved: string;
  speaker: string; promptsTitle: string; prompts: readonly string[];
  promptForAi: string; advisorActionHelp: string; promptHelp: string;
  saveWithoutAI: string; currentDuration: string;
  origin: string; travelerCount: string; budget: string; dates: string; interest: string;
}> = {
  'fa-IR': {
    send: 'پرسش از دستیار سفر', review: 'پیشنهاد مدل؛ پیش از تأیید سفر بررسی کنید:',
    initial: 'لطفاً برای سفر شرح‌داده‌شده سؤال تکمیلی مناسب بپرس.',
    unavailable: 'دستیار در حال حاضر در دسترس نیست؛ همچنان می‌توانید سفر را بدون آن ثبت کنید.',
    destination: 'مقصد پیشنهادی', duration: 'تعداد روز پیشنهادی',
    apply: 'انتقال به فرم سفر', dismiss: 'نادیده گرفتن', reviewSaved: 'بازبینی پیشنهاد ذخیره‌شده',
    unsaved: 'این پیشنهاد هنوز ذخیره یا تأیید نشده است. پس از انتقال، فرم سفر را بررسی و تأیید کنید.',
    origin: 'شهر مبدأ پیشنهادی', travelerCount: 'تعداد مسافران پیشنهادی',
    budget: 'بودجهٔ پیشنهادی', dates: 'تاریخ‌های پیشنهادی (میلادی)', interest: 'علاقهٔ پیشنهادی',
    speaker: 'مشاور هوش مصنوعی', promptsTitle: 'برای ادامه می‌توانید از مشاور بخواهید:',
    promptForAi: 'این عبارت برای مشاور هوش مصنوعی است؛ برای ارسال «پرسش از دستیار سفر» را انتخاب کنید.',
    advisorActionHelp: 'گفت‌وگوی هوشمند فعال است؛ پیام و سابقهٔ مرتبط سفر به سرویس تنظیم‌شده ارسال می‌شود.',
    promptHelp: 'انتخاب پرسش فقط پیش‌نویس را پر می‌کند؛ تا انتخاب یکی از اقدام‌های زیر چیزی ذخیره یا ارسال نمی‌شود.',
    saveWithoutAI: 'ثبت پاسخ بدون هوش مصنوعی',
    currentDuration: 'مدت ثبت‌شدهٔ این سفر: {days} روز.',
    prompts: ['دربارهٔ علایق و سبک سفرم یک سؤال تکمیلی بپرس.', 'برای روشن شدن بودجه و تعداد همراهانم سؤال بپرس.', 'محدودیت‌های ضروری سفرم را مرور کن و موارد مبهم را بپرس.'] },
  'en-US': {
    send: 'Ask travel assistant', review: 'AI suggestions — review before confirming:',
    initial: 'Please ask a useful clarification about the trip described above.',
    unavailable: 'The assistant is unavailable. You can still save your trip.',
    destination: 'Suggested destination', duration: 'Suggested days',
    apply: 'Use in trip form', dismiss: 'Dismiss', reviewSaved: 'Review saved suggestion',
    unsaved: 'Not saved or confirmed. Review and confirm the trip form after applying.',
    origin: 'Suggested departure city', travelerCount: 'Suggested travelers',
    budget: 'Suggested budget', dates: 'Suggested dates (Gregorian)', interest: 'Suggested interest',
    speaker: 'AI travel advisor', promptsTitle: 'Suggested follow-up questions:',
    promptForAi: 'This prompt is intended for the AI advisor. Select “Ask travel assistant” to send it.',
    advisorActionHelp: 'AI conversation is on by default. Messages and relevant trip history are sent to the configured provider.',
    promptHelp: 'Choosing a prompt only fills the draft. Nothing is saved or sent until you choose one of the actions below.',
    saveWithoutAI: 'Save reply without AI',
    currentDuration: 'Recorded trip length: {days} days.',
    prompts: ['Ask me about my interests and travel style.', 'Clarify my budget and number of travelers.', 'Review my essential constraints and ask what is unclear.'] },
  ar: {
    send: 'اسأل مساعد السفر', review: 'اقتراحات النموذج — راجعها قبل التأكيد:',
    initial: 'يرجى طرح سؤال توضيحي مناسب عن الرحلة المذكورة أعلاه.',
    unavailable: 'المساعد غير متاح حاليًا. يمكنك حفظ الرحلة بدونه.',
    destination: 'الوجهة المقترحة', duration: 'الأيام المقترحة',
    apply: 'نقل إلى نموذج الرحلة', dismiss: 'تجاهل', reviewSaved: 'مراجعة الاقتراح المحفوظ',
    unsaved: 'لم يُحفظ هذا الاقتراح أو يُؤكَّد. راجع نموذج الرحلة وأكّده بعد النقل.',
    origin: 'مدينة المغادرة المقترحة', travelerCount: 'عدد المسافرين المقترح',
    budget: 'الميزانية المقترحة', dates: 'التواريخ المقترحة (ميلادي)', interest: 'الاهتمام المقترح',
    speaker: 'مستشار السفر بالذكاء الاصطناعي', promptsTitle: 'يمكنك متابعة المحادثة عبر:',
    promptForAi: 'هذا طلب موجه إلى مستشار الذكاء الاصطناعي؛ اختر «اسأل مساعد السفر» لإرساله.',
    advisorActionHelp: 'المحادثة الذكية مفعّلة افتراضياً، وتُرسل الرسالة وسجل الرحلة إلى خدمة الذكاء الاصطناعي المهيأة.',
    promptHelp: 'اختيار السؤال يملأ المسودة فقط؛ لا يُحفظ شيء ولا يُرسل حتى تختار أحد الإجراءين أدناه.',
    saveWithoutAI: 'احفظ الرد دون ذكاء اصطناعي',
    currentDuration: 'مدة الرحلة المسجلة: {days} يومًا.',
    prompts: ['اسألني عن اهتماماتي وطريقة سفري.', 'اسألني عن الميزانية وعدد المسافرين.', 'راجع الشروط الأساسية واسأل عن الأمور غير الواضحة.'] },
};

function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

function safeRequirements(value: unknown, locale: Locale, originalRequest?: string): TripRequirements | null {
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
  const requestText = typeof candidate.requestText === 'string' ? candidate.requestText : originalRequest;
  if (!requestText) return null;
  const parsed = createTripRequirements({ requestText, locale });
  if (parsed.kind === 'invalid') return null;
  const defaults = parsed.requirements;
  const field = <T,>(input: unknown, valid: (value: unknown) => value is T, fallback: TripRequirements[keyof TripRequirements]) => {
    if (!input || typeof input !== 'object' || Array.isArray(input)) return fallback;
    const entry = input as Record<string, unknown>;
    if (!['extracted', 'unknown', 'ambiguous'].includes(String(entry.status))
        || (entry.value !== null && !valid(entry.value))) return fallback;
    return input;
  };
  const strings = (item: unknown): item is string[] => Array.isArray(item) && item.every(value => typeof value === 'string');
  const stringValue = (item: unknown): item is string => typeof item === 'string';
  const numberValue = (item: unknown): item is number => typeof item === 'number' && Number.isFinite(item);
  const dates = (item: unknown): item is { start: string; end: string } => !!item && typeof item === 'object'
    && typeof (item as Record<string, unknown>).start === 'string' && typeof (item as Record<string, unknown>).end === 'string';
  const budget = (item: unknown): item is NonNullable<TripRequirements['budget']['value']> => !!item && typeof item === 'object'
    && typeof (item as Record<string, unknown>).raw === 'string' && numberValue((item as Record<string, unknown>).amount);
  return {
    ...defaults,
    requestText, locale,
    destinations: field(candidate.destinations, strings, defaults.destinations) as TripRequirements['destinations'],
    origin: field(candidate.origin, stringValue, defaults.origin) as TripRequirements['origin'],
    durationDays: field(candidate.durationDays, numberValue, defaults.durationDays) as TripRequirements['durationDays'],
    travelDates: field(candidate.travelDates, dates, defaults.travelDates) as TripRequirements['travelDates'],
    travelerCount: field(candidate.travelerCount, numberValue, defaults.travelerCount) as TripRequirements['travelerCount'],
    accessibility: field(candidate.accessibility, strings, defaults.accessibility) as TripRequirements['accessibility'],
    budget: field(candidate.budget, budget, defaults.budget) as TripRequirements['budget'],
    interests: field(candidate.interests, strings, defaults.interests) as TripRequirements['interests'],
    softPreferences: field(candidate.softPreferences, strings, defaults.softPreferences) as TripRequirements['softPreferences'],
    constraints: field(candidate.constraints, strings, defaults.constraints) as TripRequirements['constraints'],
    travelDifficulty: field(candidate.travelDifficulty, strings, defaults.travelDifficulty) as TripRequirements['travelDifficulty'],
    weatherPreferences: field(candidate.weatherPreferences, strings, defaults.weatherPreferences) as TripRequirements['weatherPreferences'],
    localCuisine: field(candidate.localCuisine, strings, defaults.localCuisine) as TripRequirements['localCuisine'],
  };
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
  // Known traveler facts do not need consent to be treated as known merely
  // because catalogue metadata cannot evaluate destination fit. Hard or
  // unclassified constraints stay fail-closed in their dedicated review UI.
  void value;
  return [];
}

function parseReviewedBudget(text: string, locale: Locale): TripRequirements['budget']['value'] {
  if (!text.trim()) return null;
  // This is a budget field, not a complete natural-language trip request.
  // Supplying the parser's budget marker lets it validate amounts such as
  // "30 million toman" without requiring unrelated destination/date fields.
  const result = createTripRequirements({ requestText: `budget ${text.trim()}`, locale });
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
  return reviewedTripInterests(text);
}

function displayInterests(values: readonly string[], locale: Locale): string {
  return values.map(value => displayTripInterest(value, locale)).join('، ');
}

function consentFieldsForReviewedProfile(
  extracted: TripRequirements | null,
): RequirementFieldCode[] {
  return unresolvedConsentFields(extracted);
}

function restoredConsent(
  trip: TripRecord,
  fields: RequirementFieldCode[],
): RestoredRequirementConsent | null {
  void fields; // Historical valid decisions remain readable after removing routine prompts.
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
    !requirementFields.includes(field as RequirementFieldCode)
    || (decision !== 'must_have' && decision !== 'advisory'))
  ) return null;
  const acknowledgements = consent.advisory_acknowledged_fields;
  if (!Array.isArray(acknowledgements)
      || acknowledgements.some(field => typeof field !== 'string' || !requirementFields.includes(field as RequirementFieldCode))
      || new Set(acknowledgements).size !== acknowledgements.length) return null;
  const parsed: Partial<Record<RequirementFieldCode, RequirementConsentDecision>> = {};
  for (const [field, decision] of decisionEntries) {
    if (decision === 'must_have' || decision === 'advisory') parsed[field as RequirementFieldCode] = decision;
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
  autoStartConversation?: boolean;
  assistantConfigured?: boolean | null;
  travelerTimezone?: string;
  suggestedOrigin?: { approximateText: string; accuracyMeters: number } | null;
  onManualDateOverride?: () => void;
  onConversationVisibilityChange?: (active: boolean) => void;
  onSessionExpired: () => void;
  onRestoreRequest: (text: string, requirements: TripRequirements) => void;
  onStartNewDraft: () => void;
};

export function TravelerJourney({ locale, session, online, requirements, autoStartConversation = false, assistantConfigured = true, travelerTimezone = 'Asia/Tehran', suggestedOrigin = null, onManualDateOverride, onConversationVisibilityChange, onSessionExpired, onRestoreRequest, onStartNewDraft }: TravelerJourneyProps) {
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
  const [catalogueNextCursor, setCatalogueNextCursor] = useState<string | null>(null);
  const [destinationNames, setDestinationNames] = useState<string[]>([]);
  const [durationText, setDurationText] = useState('');
  const [originText, setOriginText] = useState('');
  const [travelerCountText, setTravelerCountText] = useState('');
  const [budgetText, setBudgetText] = useState('');
  const [travelStartText, setTravelStartText] = useState('');
  const [travelEndText, setTravelEndText] = useState('');
  const [interestText, setInterestText] = useState('');
  const [softPreferenceText, setSoftPreferenceText] = useState('');
  const [difficultyText, setDifficultyText] = useState('');
  const [weatherPreferenceText, setWeatherPreferenceText] = useState('');
  const [localCuisineText, setLocalCuisineText] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [requirementChoices, setRequirementChoices] = useState<Partial<Record<RequirementFieldCode, RequirementConsentDecision>>>({});
  const [advisoryAcknowledgements, setAdvisoryAcknowledgements] = useState<Partial<Record<RequirementFieldCode, boolean>>>({});
  const [messageText, setMessageText] = useState('');
  const [assistantPromptSelected, setAssistantPromptSelected] = useState(false);
  // AI is available by default; the server/provider still enforces access and quotas.
  const [assistantState, setAssistantState] = useState<'loading' | 'configured' | 'connected' | 'disabled' | 'unavailable' | 'quota_exhausted' | 'responded'>('loading');
  const [assistantReplyPending, setAssistantReplyPending] = useState(false);
  const [assistantRemaining, setAssistantRemaining] = useState<number | null>(null);
  const [shareOptions, setShareOptions] = useState<Array<{ organization_id: string; display_name: string; organization_type: string }>>([]);
  const [tripShares, setTripShares] = useState<Array<{ share_id: string; organization_id: string; display_name: string; revoked_at: string | null; latest_revision: number | null }>>([]);
  const [selectedShareOrganizations, setSelectedShareOrganizations] = useState<string[]>([]);
  const [shareToAllEligible, setShareToAllEligible] = useState(false);
  const [eligibleCompanyCount, setEligibleCompanyCount] = useState(0);
  const [broadcastLimit, setBroadcastLimit] = useState(500);
  const [includeOriginalRequestInShare, setIncludeOriginalRequestInShare] = useState(false);
  const [shareConsentAccepted, setShareConsentAccepted] = useState(false);
  const [sharingBusy, setSharingBusy] = useState(false);
  const [assistantCandidate, setAssistantCandidate] = useState<unknown>(null);
  const [extractionPath, setExtractionPath] = useState<'llm' | 'fallback' | 'user_override' | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationResult | null>(null);
  const [provisionalCandidate, setProvisionalCandidate] = useState<{ days: Array<{ day_number: number; stops: Array<{ name: string; role: 'model_proposed' }> }> } | null>(null);
  const [provisionalItinerary, setProvisionalItinerary] = useState<ProvisionalItinerary | null>(null);
  const [provisionalDays, setProvisionalDays] = useState<ProvisionalDay[]>([]);
  const [provisionalDirty, setProvisionalDirty] = useState(false);
  const [newProvisionalStop, setNewProvisionalStop] = useState('');
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
  const autoStartedRequestRef = useRef<string | null>(null);
  const draftInFlightRef = useRef<string | null>(null);
  const completedDraftRef = useRef<string | null>(null);
  const draftGenerationRef = useRef(0);
  const restoredCompanyReplyRef = useRef<string | null>(null);
  const manualProfileFieldsRef = useRef(new Set<string>());
  const assistantProfileFieldsRef = useRef(new Set<string>());
  const requestIdentityRef = useRef(requirements?.requestText ?? null);
  const resolutionSequenceRef = useRef(0);
  const catalogueBrowseSequenceRef = useRef(0);

  const extracted = useMemo(() => safeRequirements(activeTrip?.extracted_requirements, activeTrip?.locale ?? locale, activeTrip?.original_request), [activeTrip, locale]);
  const consentFields = useMemo(() => consentFieldsForReviewedProfile(extracted), [extracted]);
  const budgetValid = !budgetText.trim() || parseReviewedBudget(budgetText, locale) !== null;
  const datesValid = validTravelDates(travelStartText, travelEndText);
  const interests = parseInterests(interestText);
  const softPreferences = parseInterests(softPreferenceText);
  const interestsValid = interestText.length <= 300 && interests.length <= 10
    && interests.every(value => value.length <= 100 && !/[\u0000-\u001f\u007f]/u.test(value));
  const softPreferencesValid = softPreferenceText.length <= 300 && softPreferences.length <= 10
    && softPreferences.every(value => value.length <= 100 && !/[\u0000-\u001f\u007f]/u.test(value));
  const travelerCountValid = travelerCountText.trim() === '' || (/^[0-9]{1,2}$/.test(travelerCountText.trim())
    && Number(travelerCountText) >= 1 && Number(travelerCountText) <= 50);
  const consentComplete = consentIsComplete(consentFields, requirementChoices, advisoryAcknowledgements);
  const hasDestination = destinationNames.some(name => name.trim());
  const reviewedDuration = validDayCount(Number(durationText));
  const [attemptedProfileReview, setAttemptedProfileReview] = useState(false);
  const optionalField = locale === 'fa-IR' ? '(اختیاری)' : locale === 'ar' ? '(اختياري)' : '(Optional)';
  const reviewedAssistantCandidate = reviewableAssistantCandidate(assistantCandidate);
  const requirementCopy = requirementClarificationMessages[locale];
  const guidedQuestion = activeTrip ? nextTripQuestion(locale, destinationNames, durationText) : null;
  const conversationVisible = Boolean(session && activeTrip && activeConversation);
  useEffect(() => onConversationVisibilityChange?.(conversationVisible), [conversationVisible, onConversationVisibilityChange]);
  const invalidateConsent = () => {
    setRequirementChoices({});
    setAdvisoryAcknowledgements({});
    setConfirmed(false);
    setRecommendations(null);
    setItinerary(null);
    setProvisionalCandidate(null);
  };
  const markProfileFieldEdited = (field: string) => {
    manualProfileFieldsRef.current.add(field);
    assistantProfileFieldsRef.current.delete(field);
    setExtractionPath('user_override');
  };
  const acceptAssistantProfileField = (field: string) => {
    manualProfileFieldsRef.current.add(field);
    assistantProfileFieldsRef.current.add(field);
    setExtractionPath('llm');
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
  // A city name can be a known traveler requirement even when no approved
  // catalogue identity resolves it. In that one case a clearly unverified
  // provisional plan is safe; unresolved mandatory trip constraints continue
  // to block this path.
  const provisionalPlanningAllowed = recommendations?.status === 'empty'
    || (recommendations?.status === 'needs_confirmation'
      && recommendations.unresolved_fields.length === 1
      && recommendations.unresolved_fields[0] === 'destination_resolution');

  const resolveNames = async (names: string[], explicitChoices: readonly { index: number; destinationId: string }[] = []) => {
    const sequence = ++resolutionSequenceRef.current;
    if (!names.length || names.some(name => !name.trim())) { setResolution(null); setCatalogueDestinations([]); return; }
    try {
      const pages = await Promise.all(names.map(name => catalog.load(name)));
      if (sequence !== resolutionSequenceRef.current) return;
      const allAvailable = pages.every(item => item.kind === 'available' && item.boundary === 'knowledge.production_destinations');
      const catalogue = allAvailable
        ? { kind:'available' as const, boundary:'knowledge.production_destinations', destinations:pages.flatMap(item => item.kind === 'available' ? item.destinations : []) }
        : { kind:'unavailable' as const };
      setCatalogueDestinations(catalogue.kind === 'available' ? catalogue.destinations : []);
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

  const browseCatalogue = async (cursor?: string, append = false) => {
    if (!online || catalogueLoading) return;
    const sequence = ++catalogueBrowseSequenceRef.current;
    setCatalogueOpen(true); setCatalogueLoading(true); setCatalogueUnavailable(false);
    try {
      const result = await catalog.load(catalogueSearch.trim() || undefined, cursor);
      if (sequence !== catalogueBrowseSequenceRef.current) return;
      if (result.kind === 'available' && result.boundary === 'knowledge.production_destinations') {
        setCatalogueDestinations(current => append ? [...current, ...result.destinations.filter(item => !current.some(existing => existing.destinationId === item.destinationId))] : result.destinations);
        setCatalogueNextCursor(result.nextCursor ?? null);
      } else { setCatalogueDestinations([]); setCatalogueNextCursor(null); setCatalogueUnavailable(true); }
    } catch {
      if (sequence !== catalogueBrowseSequenceRef.current) return;
      setCatalogueDestinations([]); setCatalogueNextCursor(null); setCatalogueUnavailable(true);
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
    let current = true;
    if (!session || !online) {
      setAssistantRemaining(null);
      setAssistantState(online ? 'disabled' : 'unavailable');
      return () => { current = false; };
    }
    setAssistantState('loading');
    void travelerApi.assistantStatus().then(result => {
      if (current) {
        setAssistantState(result.state);
        setAssistantRemaining(Math.min(result.user_remaining, result.global_remaining));
      }
    }).catch(() => { if (current) { setAssistantState('unavailable'); setAssistantRemaining(null); } });
    return () => { current = false; };
  }, [session?.user.user_id, online]);

  useEffect(() => {
    if (!requirements) {
      requestIdentityRef.current = null;
      manualProfileFieldsRef.current.clear();
      return;
    }
    if (requestIdentityRef.current !== requirements.requestText) {
      requestIdentityRef.current = requirements.requestText;
      manualProfileFieldsRef.current.clear();
    }
  }, [requirements?.requestText]);

  useEffect(() => {
    let active = true;
    if (!session || !activeTrip || !confirmed || !online) {
      setTripShares([]);
      return () => { active = false; };
    }
    void Promise.all([
      travelerApi.companyShareOptions(activeTrip.trip_id),
      travelerApi.listTripCompanyShares(activeTrip.trip_id),
    ]).then(([options, shares]) => {
      if (!active) return;
      setShareOptions(options.items);
      setEligibleCompanyCount(options.eligible_count ?? options.items.length);
      setBroadcastLimit(options.broadcast_limit ?? 500);
      setTripShares(shares.items);
    }).catch(() => {
      if (active) { setShareOptions([]); setTripShares([]); }
    });
    return () => { active = false; };
  }, [session?.user.user_id, activeTrip?.trip_id, confirmed, online]);

  useEffect(() => {
    if (requirements) {
      if (requestIdentityRef.current !== requirements.requestText) {
        requestIdentityRef.current = requirements.requestText;
        manualProfileFieldsRef.current.clear();
      }
      if (activeTrip && requirements.requestText !== activeTrip.original_request && restoringRequestRef.current !== requirements.requestText) {
        setDirty(true);
        setConfirmed(false);
        setRecommendations(null);
        setItinerary(null);
      }
      const restoring = restoringRequestRef.current === requirements.requestText;
      // The restored server trip is authoritative, whether or not the traveler
      // had already confirmed it. The parent can still hold an older extraction.
      if (!restoring) {
        if (!manualProfileFieldsRef.current.has('destination')) setDestinationNames(requirements.destinations.value ? [...requirements.destinations.value] : []);
        if (!manualProfileFieldsRef.current.has('duration')) setDurationText(requirements.durationDays.value === null ? '' : String(requirements.durationDays.value));
        if (!manualProfileFieldsRef.current.has('origin')) setOriginText(requirements.origin.value ?? '');
        if (!manualProfileFieldsRef.current.has('travelers')) setTravelerCountText(requirements.travelerCount.value === null ? '' : String(requirements.travelerCount.value));
        if (!manualProfileFieldsRef.current.has('budget')) setBudgetText(requirements.budget.value?.raw ?? '');
        const manualDateOverride = manualProfileFieldsRef.current.has('travelStart') || manualProfileFieldsRef.current.has('travelEnd');
        if (!manualDateOverride) {
          setTravelStartText(requirements.travelDates.value?.start ?? requirements.relativeStartDate.value?.anchor_date ?? '');
          setTravelEndText(requirements.travelDates.value?.end ?? '');
        }
        if (!manualProfileFieldsRef.current.has('interests')) setInterestText(displayInterests(requirements.interests.value ?? [], locale));
        if (!manualProfileFieldsRef.current.has('softPreferences')) setSoftPreferenceText(displayInterests(requirements.softPreferences.value ?? [], locale));
        if (!manualProfileFieldsRef.current.has('difficulty')) setDifficultyText(displayInterests(requirements.travelDifficulty.value ?? [], locale));
        if (!manualProfileFieldsRef.current.has('weather')) setWeatherPreferenceText(displayInterests(requirements.weatherPreferences.value ?? [], locale));
        if (!manualProfileFieldsRef.current.has('cuisine')) setLocalCuisineText(displayInterests(requirements.localCuisine.value ?? [], locale));
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
    if (assistantConfigured === null) { setError(assistantCopy[locale].unavailable); return; }
    const draftKey = `${session.user.user_id}:${draftGenerationRef.current}:${requirements.requestText}`;
    if (draftInFlightRef.current === draftKey || completedDraftRef.current === draftKey) return;
    draftInFlightRef.current = draftKey;
    setBusy(true); setError(''); setStatus('');
    try {
      const destination_ids = choiceIds(resolution);
      const body = {
        locale,
        request_text: requirements.requestText,
        extracted_requirements: requirementsForPersistence(requirements),
        traveler_timezone: travelerTimezone,
        traveler_reference_date: deviceCalendarDate(travelerTimezone),
        destination_ids,
        idempotency_key: newIdempotencyKey(),
      };
      const result = activeConversation
        ? await travelerApi.createTripInConversation(csrf, activeConversation.conversation_id, body)
        : await travelerApi.createConversation(csrf, body);
      let savedConversation = result.conversation;
      let savedTrip = result.trip;
      completedDraftRef.current = draftKey;
      setActiveConversation(savedConversation);
      setActiveTrip(savedTrip);
      setDayCount(tripDayCount(savedTrip, requirements) ?? 1);
      setConfirmed(false);
      setDirty(false);
      
      setStatus(copy.saveSuccess);
      if (assistantConfigured !== true) setExtractionPath('fallback');
      if (assistantConfigured) {
        setAssistantReplyPending(true);
        try {
          const firstReply = await travelerApi.assistantTurn(csrf, savedConversation.conversation_id, {
            trip_id: savedTrip.trip_id,
            content: requirements.requestText,
            idempotency_key: newIdempotencyKey(),
            expected_version: savedConversation.version,
            existing_user_message_id: result.initial_message.message_id,
          });
          savedConversation = firstReply.conversation;
          savedTrip = firstReply.trip;
          setActiveConversation(savedConversation);
          setActiveTrip(savedTrip);
          setAssistantCandidate(firstReply.candidate_requirements);
          setExtractionPath(firstReply.extraction_path ?? 'fallback');
          if (firstReply.provisional_itinerary?.status === 'provisional_unverified') {
            setProvisionalCandidate({ days: firstReply.provisional_itinerary.days });
          }
          // Evidence-backed AI extraction may correct a rule-based fallback,
          // but never overwrites a field the traveler has edited. Profile
          // confirmation remains an explicit traveler action.
          const interpreted = reviewableAssistantCandidate(firstReply.candidate_requirements);
          const typed = interpreted?.typedRequirements;
          const hasDirectEvidence = (field: keyof NonNullable<typeof typed>['fields']): boolean => {
            const span = typed?.fields[field]?.evidence_span;
            return Boolean(typed?.original_text === requirements.requestText && span
              && Number.isInteger(span.start) && Number.isInteger(span.end)
              && requirements.requestText.slice(span.start, span.end) === span.text);
          };
          let improved = false;
          const candidateCanReplace = (fieldName: string, manualField: string) => {
            const field = (requirements as unknown as Record<string, { source?: string; value?: unknown }>)[fieldName];
            return assistantMayReplaceField(field?.source as 'traveler' | 'llm' | 'fallback' | 'correction' | undefined,
              field?.value != null, manualProfileFieldsRef.current.has(manualField),
              savedTrip.confirmed_requirements.confirmation_source === 'traveler_reviewed');
          };
          const canApply = (fieldName: string, manualField: string) => candidateCanReplace(fieldName, manualField);
          if (interpreted && typed && typed.original_text === requirements.requestText) {
            const modelLeftOpen = (field: keyof typeof typed.fields, draftField: string, manualField: string) =>
              typed.fields[field]?.status !== 'known' && typed.fields[field]?.source === 'llm'
              && canApply(draftField, manualField);
            if (modelLeftOpen('destination', 'destinations', 'destination')) {
              setDestinationNames([]); void resolveNames([]);
            }
            if (modelLeftOpen('duration_days', 'durationDays', 'duration')) setDurationText('');
            if (modelLeftOpen('origin', 'origin', 'origin')) setOriginText('');
            if (modelLeftOpen('travelers', 'travelerCount', 'travelers')) setTravelerCountText('');
            if (modelLeftOpen('budget', 'budget', 'budget')) setBudgetText('');
            if (modelLeftOpen('interests', 'interests', 'interests')) setInterestText('');
            if (modelLeftOpen('travel_dates', 'travelDates', 'travelStart')
                && modelLeftOpen('relative_start_date', 'relativeStartDate', 'travelStart')) {
              setTravelStartText('');
              if (canApply('travelDates', 'travelEnd')) setTravelEndText('');
            }
            if (interpreted.destination && canApply('destinations', 'destination') && hasDirectEvidence('destination')) {
              setDestinationNames([interpreted.destination]); void resolveNames([interpreted.destination]); acceptAssistantProfileField('destination'); improved = true;
            }
            if (interpreted.durationDays && canApply('durationDays', 'duration') && hasDirectEvidence('duration_days')) {
              setDurationText(String(interpreted.durationDays)); acceptAssistantProfileField('duration'); improved = true;
              const relativeStart = requirements.relativeStartDate.value?.anchor_date;
              const resolvedStart = travelStartText || relativeStart || requirements.relativeDateResolution?.start || '';
              const hasExplicitDateRange = requirements.travelDates.value !== null;
              if (resolvedStart && !hasExplicitDateRange && !manualProfileFieldsRef.current.has('travelEnd')) {
                const endDate = inclusiveEndDate(resolvedStart, interpreted.durationDays);
                if (endDate) setTravelEndText(endDate);
              }
            }
            if (interpreted.origin && canApply('origin', 'origin') && hasDirectEvidence('origin')) {
              setOriginText(interpreted.origin); acceptAssistantProfileField('origin'); improved = true;
            }
            if (interpreted.travelerCount && canApply('travelerCount', 'travelers') && hasDirectEvidence('travelers')) {
              setTravelerCountText(String(interpreted.travelerCount)); acceptAssistantProfileField('travelers'); improved = true;
            }
            if (interpreted.budgetText && canApply('budget', 'budget') && hasDirectEvidence('budget')) {
              setBudgetText(interpreted.budgetText); acceptAssistantProfileField('budget'); improved = true;
            }
            if (interpreted.travelStart && interpreted.travelEnd && canApply('travelDates', 'travelStart') && canApply('travelDates', 'travelEnd') && hasDirectEvidence('travel_dates')) {
              setTravelStartText(interpreted.travelStart); setTravelEndText(interpreted.travelEnd); acceptAssistantProfileField('travelStart'); acceptAssistantProfileField('travelEnd'); improved = true;
            }
            if (interpreted.relativeStartDate && !interpreted.travelStart
                && canApply('relativeStartDate', 'travelStart')
                && !manualProfileFieldsRef.current.has('travelStart')
                && hasDirectEvidence('relative_start_date')
                && interpreted.relativeStartDate.anchorDate) {
              const start = interpreted.relativeStartDate.anchorDate;
              setTravelStartText(start);
              acceptAssistantProfileField('travelStart');
              const effectiveDuration = interpreted.durationDays ?? Number(durationText);
              if (!manualProfileFieldsRef.current.has('travelEnd') && Number.isInteger(effectiveDuration)
                  && effectiveDuration >= 1 && effectiveDuration <= 365) {
                const end = inclusiveEndDate(start, effectiveDuration);
                if (end) { setTravelEndText(end); acceptAssistantProfileField('travelEnd'); }
              }
              improved = true;
            }
            if (interpreted.interest && canApply('interests', 'interests') && hasDirectEvidence('interests')) {
              setInterestText(displayInterests(reviewedTripInterests(interpreted.interest), locale)); acceptAssistantProfileField('interests'); improved = true;
            }
            if (interpreted.softPreferences?.length && canApply('softPreferences', 'softPreferences') && hasDirectEvidence('soft_preferences')) {
              setSoftPreferenceText(displayInterests(interpreted.softPreferences, locale)); acceptAssistantProfileField('softPreferences'); improved = true;
            }
            if (interpreted.travelDifficulty?.length && canApply('travelDifficulty', 'difficulty') && hasDirectEvidence('travel_difficulty')) {
              setDifficultyText(displayInterests(interpreted.travelDifficulty, locale)); acceptAssistantProfileField('difficulty'); improved = true;
            }
            if (interpreted.weatherPreferences?.length && canApply('weatherPreferences', 'weather') && hasDirectEvidence('weather_preferences')) {
              setWeatherPreferenceText(displayInterests(interpreted.weatherPreferences, locale)); acceptAssistantProfileField('weather'); improved = true;
            }
            if (interpreted.localCuisine?.length && canApply('localCuisine', 'cuisine') && hasDirectEvidence('local_cuisine')) {
              setLocalCuisineText(displayInterests(interpreted.localCuisine, locale)); acceptAssistantProfileField('cuisine'); improved = true;
            }
          }
          if (improved) { setDirty(true); invalidateConsent(); }
          setAssistantState('responded');
          setAssistantRemaining(value => value === null ? null : Math.max(0, value - 1));
          setStatus(locale === 'fa-IR' ? 'دستیار به درخواست شما پاسخ داد؛ پیشنهادهای استخراج‌شده هنوز تأیید نشده‌اند.'
            : locale === 'ar' ? 'أجاب المساعد عن طلبك؛ وما زالت المتطلبات المقترحة غير مؤكدة.'
              : 'The assistant replied; extracted suggestions are still unconfirmed.');
        } catch (value) {
          if (value instanceof TravelerApiError && value.status === 429) {
            setAssistantState('quota_exhausted');
            setAssistantRemaining(0);
            setError(locale === 'fa-IR' ? 'سهمیهٔ روزانهٔ دستیار تمام شده است. درخواست شما ذخیره شد و ارسال خودکار دیگری انجام نمی‌شود.'
              : locale === 'ar' ? 'اكتملت الحصة اليومية للمساعد. تم حفظ طلبك ولن نعيد الإرسال تلقائياً.'
                : 'The assistant daily limit is reached. Your request is saved; it will not be retried automatically.');
          } else if (value instanceof TravelerApiError && value.status === 503) {
            setAssistantState('unavailable');
            setExtractionPath('fallback');
            setError(assistantCopy[locale].unavailable);
          } else applyFailure(value);
          // The request/conversation remains saved even if the provider fails.
          const [freshConversation, freshTrip] = await Promise.all([
            travelerApi.getConversation(savedConversation.conversation_id),
            travelerApi.getTrip(savedTrip.trip_id),
          ]).catch(() => [savedConversation, savedTrip] as const);
          savedConversation = freshConversation;
          savedTrip = freshTrip;
          setActiveConversation(savedConversation);
          setActiveTrip(savedTrip);
        } finally { setAssistantReplyPending(false); }
      }
      const history = await travelerApi.listConversations(50);
      setConversations(history.items);
      requestAnimationFrame(() => document.getElementById('trip-follow-up')?.focus());
    } catch (value) { applyFailure(value); }
    finally { if (draftInFlightRef.current === draftKey) draftInFlightRef.current = null; setBusy(false); }
  };

  useEffect(() => {
    if (!requirements) {
      autoStartedRequestRef.current = null;
      completedDraftRef.current = null;
      draftGenerationRef.current += 1;
      return;
    }
    if (!autoStartConversation || !session || !online || activeTrip || busy || assistantConfigured === null) return;
    const key = `${session.user.user_id}:${draftGenerationRef.current}:${requirements.requestText}`;
    if (autoStartedRequestRef.current === key) return;
    autoStartedRequestRef.current = key;
    void persistDraft(); // One user submission => one saved conversation and one default AI turn.
  }, [autoStartConversation, requirements, session?.user.user_id, online, activeTrip?.trip_id, assistantConfigured]);

  const restoreTrip = async (conversationId: string, tripId: string) => {
    if (requirements && !activeTrip && requirements.requestText.trim() && !window.confirm(copy.replaceDraftConfirm)) return;
    setBusy(true); setError(''); setStatus('');
    try {
      const conversation = await travelerApi.getConversation(conversationId);
      const trip = await travelerApi.getTrip(tripId);
      setActiveConversation(conversation);
      setAssistantCandidate(null);
      
      const parsed = safeRequirements(trip.extracted_requirements, trip.locale, trip.original_request);
      setActiveTrip(trip);
      const hasReviewedProfile = trip.confirmed_requirements.confirmation_source === 'traveler_reviewed';
      const storedNames = trip.confirmed_requirements.destinations;
      const restoredNames = hasReviewedProfile && Array.isArray(storedNames)
        && storedNames.every(name => typeof name === 'string' && name.trim().length > 0 && name.length <= 100)
        ? storedNames as string[] : (parsed?.destinations.value ?? []);
      const parsedDays = validDayCount(parsed?.durationDays.value) ?? validDayCount(trip.duration_days);
      const restoredDays = hasReviewedProfile
        ? validDayCount(trip.confirmed_requirements.duration_days) ?? parsedDays
        : parsedDays;
      setDestinationNames(restoredNames.slice());
      setDurationText(restoredDays === null ? '' : String(restoredDays));
      const approvedOrigin = trip.confirmed_requirements.origin;
      const restoredOrigin = hasReviewedProfile && typeof approvedOrigin === 'string' && approvedOrigin.length <= 100
        ? approvedOrigin : hasReviewedProfile ? '' : (parsed?.origin.value ?? '');
      const approvedCount = validDayCount(trip.confirmed_requirements.traveler_count);
      const restoredTravelerCount = hasReviewedProfile && approvedCount !== null && approvedCount <= 50
        ? String(approvedCount) : hasReviewedProfile ? '' : (parsed?.travelerCount.value !== null && parsed?.travelerCount.value !== undefined
          ? String(parsed.travelerCount.value)
          : trip.traveler_count !== null ? String(trip.traveler_count) : '');
      setOriginText(restoredOrigin);
      setTravelerCountText(restoredTravelerCount);
      const savedBudget = trip.confirmed_requirements.budget;
      const restoredBudget = hasReviewedProfile && savedBudget && typeof savedBudget === 'object'
        && !Array.isArray(savedBudget) && typeof (savedBudget as Record<string, unknown>).raw === 'string'
        ? String((savedBudget as Record<string, unknown>).raw) : hasReviewedProfile ? '' : (parsed?.budget.value?.raw ?? '');
      const savedDates = trip.confirmed_requirements.travel_dates;
      const restoredDates = hasReviewedProfile && savedDates && typeof savedDates === 'object'
        && !Array.isArray(savedDates) ? savedDates as Record<string, unknown> : null;
      const restoredStart = typeof restoredDates?.start === 'string' ? restoredDates.start
        : hasReviewedProfile ? '' : (parsed?.travelDates.value?.start ?? parsed?.relativeStartDate.value?.anchor_date ?? '');
      const inferredEnd = restoredStart && restoredDays !== null ? inclusiveEndDate(restoredStart, restoredDays) : null;
      const restoredEnd = typeof restoredDates?.end === 'string' && restoredDates.end.trim()
        ? restoredDates.end
        : hasReviewedProfile ? '' : (parsed?.travelDates.value?.end || inferredEnd || '');
      const savedInterests = trip.confirmed_requirements.interests;
      const restoredInterests = hasReviewedProfile && Array.isArray(savedInterests)
        && savedInterests.every(value => typeof value === 'string')
        ? savedInterests as string[] : (parsed?.interests.value ?? []);
      setBudgetText(restoredBudget);
      setTravelStartText(restoredStart);
      setTravelEndText(restoredEnd);
      setInterestText(displayInterests(restoredInterests, locale));
      const savedSoftPreferences = trip.confirmed_requirements.soft_preferences;
      const restoredSoftPreferences = hasReviewedProfile && Array.isArray(savedSoftPreferences)
        && savedSoftPreferences.every(value => typeof value === 'string')
        ? savedSoftPreferences as string[] : (parsed?.softPreferences.value ?? []);
      setSoftPreferenceText(displayInterests(restoredSoftPreferences, locale));
      const restoreList = (value: unknown, fallback: string[] | null | undefined) =>
        Array.isArray(value) && value.every(item => typeof item === 'string') ? value as string[] : (fallback ?? []);
      setDifficultyText(displayInterests(restoreList(trip.confirmed_requirements.travel_difficulty,
        parsed?.travelDifficulty.value), locale));
      setWeatherPreferenceText(displayInterests(restoreList(trip.confirmed_requirements.weather_preferences,
        parsed?.weatherPreferences.value), locale));
      setLocalCuisineText(displayInterests(restoreList(trip.confirmed_requirements.local_cuisine,
        parsed?.localCuisine.value), locale));
      if (parsed) {
        restoringRequestRef.current = parsed.requestText;
        onRestoreRequest(parsed.requestText, parsed);
      }
      void resolveNames(restoredNames);
      const restoredConsentFields = consentFieldsForReviewedProfile(parsed);
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
      const restoredProvisional = await travelerApi.getProvisionalItinerary(trip.trip_id).catch(() => null);
      setProvisionalItinerary(restoredProvisional);
      setProvisionalDays(restoredProvisional?.days ?? []);
      setProvisionalDirty(false);
      setProvisionalCandidate(null);
      if (trip.latest_itinerary_id) {
        const saved = await travelerApi.getItinerary(trip.latest_itinerary_id);
        setItinerary(saved); setEditableStops(saved.stops.slice()); setDayCount(saved.day_count); setItineraryDirty(false);
      } else { setItinerary(null); setEditableStops([]); setDayCount(tripDayCount(trip, parsed) ?? 1); setItineraryDirty(false); }
      setDirty(false);
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  // Private company response URLs only identify a response. They do not
  // grant access: the usual authenticated trip + response APIs still enforce
  // traveler identity on every retrieval.
  useEffect(() => {
    if (!session || !online) return;
    const params = new URLSearchParams(window.location.search);
    const tripId = params.get('trip');
    const responseId = params.get('company_response');
    const isUuid = (value: string | null) =>
      Boolean(value && /^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(value));
    if (!isUuid(tripId) || !isUuid(responseId) || !tripId || !responseId) return;
    const key = `${session.user.user_id}:${tripId}:${responseId}`;
    if (restoredCompanyReplyRef.current === key) return;
    restoredCompanyReplyRef.current = key;
    let active = true;
    void travelerApi.getTrip(tripId).then(trip => {
      if (active && trip.trip_id === tripId) return restoreTrip(trip.conversation_id, tripId);
    }).catch(value => { if (active) applyFailure(value); });
    return () => { active = false; };
  }, [session?.user.user_id, online]);

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
        const manualDateOverride = manualProfileFieldsRef.current.has('travelStart') || manualProfileFieldsRef.current.has('travelEnd');
        if (!manualDateOverride) {
          setTravelStartText(latest.travelDates.value?.start ?? latest.relativeStartDate.value?.anchor_date ?? '');
          setTravelEndText(latest.travelDates.value?.end ?? '');
        }
        setInterestText(displayInterests(latest.interests.value ?? [], locale));
        setSoftPreferenceText(displayInterests(latest.softPreferences.value ?? [], locale));
        restoringRequestRef.current = latest.requestText;
        onRestoreRequest(latest.requestText, latest);
        void resolveNames(latest.destinations.value ?? []);
      }
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const askAssistant = async (overrideContent?: string) => {
    if (!session || !activeConversation || !activeTrip || !online) return;
    // When the status endpoint already reports no usable model, do not
    // reserve or charge an AI turn. Use existing local parsing instead.
    if (assistantState === 'disabled' || assistantState === 'quota_exhausted') {
      if (messageText.trim()) await sendMessage();
      else setError(assistantCopy[locale].unavailable);
      return;
    }
    const content = overrideContent?.trim() || messageText.trim() || assistantCopy[locale].initial;
    if (content.length > 1200) return;
    setBusy(true); setError(''); setStatus('');
    setAssistantReplyPending(true);
    setAssistantCandidate(null);
    try {
      const result = await travelerApi.assistantTurn(csrf, activeConversation.conversation_id, {
        trip_id: activeTrip.trip_id,
        content,
        idempotency_key: newIdempotencyKey(),
        expected_version: activeConversation.version,
      });
      setActiveConversation(result.conversation);
      setActiveTrip(result.trip);
      setAssistantCandidate(result.candidate_requirements);
      setExtractionPath(result.extraction_path ?? 'fallback');
      if (result.provisional_itinerary?.status === 'provisional_unverified') {
        setProvisionalCandidate({ days: result.provisional_itinerary.days });
      } else if (overrideContent) {
        setStatus(locale === 'fa-IR'
          ? 'دستیار پاسخ داد اما برنامهٔ روزبه‌روز تولید نکرد. می‌توانید دوباره درخواست کنید یا یک برنامهٔ خالی قابل ویرایش بسازید.'
          : locale === 'ar'
            ? 'ردّ المساعد دون خطة يومية. يمكنك إعادة الطلب أو إنشاء مسودة فارغة قابلة للتعديل.'
            : 'The assistant replied without a day-by-day draft. You can retry or create an editable empty draft.');
      }
      setAssistantState('responded');
      setAssistantRemaining(value => value === null ? null : Math.max(0, value - 1));
      setMessageText('');
      setAssistantPromptSelected(false);
      // AI replies are advisory: do not reset consent, the reviewed trip,
      // recommendations, or a saved itinerary after a chat message.
    } catch (value) {
      // A provider outage is different from an unavailable destination catalogue.
      if (value instanceof TravelerApiError && value.status === 429) {
        setAssistantState('quota_exhausted');
        setAssistantRemaining(0);
        setError(locale === 'fa-IR' ? 'سهمیهٔ روزانهٔ دستیار تمام شده است. پیام ذخیره شد و ارسال خودکار دیگری انجام نمی‌شود.'
          : locale === 'ar' ? 'اكتملت الحصة اليومية للمساعد. تم حفظ الرسالة ولن نعيد الإرسال تلقائياً.'
            : 'The assistant daily limit is reached. Your message is saved; it will not be retried automatically.');
      } else if (value instanceof TravelerApiError && value.status === 503) {
        setAssistantState('unavailable');
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
    } finally { setAssistantReplyPending(false); setBusy(false); }
  };

  const applyAssistantCandidate = () => {
    if (!reviewedAssistantCandidate || !activeTrip) return;
    // A blanket "use suggestions" action must not silently override a field
    // the traveler edited after the model suggestion. They can edit/confirm a
    // specific replacement in the form; other model suggestions remain usable.
    const canAcceptModelField = (field: string) =>
      !manualProfileFieldsRef.current.has(field) || assistantProfileFieldsRef.current.has(field);
    if (reviewedAssistantCandidate.destination !== null && canAcceptModelField('destination')) {
      acceptAssistantProfileField('destination');
      const names = [reviewedAssistantCandidate.destination];
      setDestinationNames(names);
      void resolveNames(names); // Catalogue verification is separate from AI text.
    }
    if (reviewedAssistantCandidate.durationDays !== null && canAcceptModelField('duration')) {
      acceptAssistantProfileField('duration');
      setDurationText(String(reviewedAssistantCandidate.durationDays));
    }
    if (reviewedAssistantCandidate.origin !== undefined && canAcceptModelField('origin')) {
      acceptAssistantProfileField('origin');
      setOriginText(reviewedAssistantCandidate.origin);
    }
    if (reviewedAssistantCandidate.travelerCount !== undefined && canAcceptModelField('travelers')) {
      acceptAssistantProfileField('travelers');
      setTravelerCountText(String(reviewedAssistantCandidate.travelerCount));
    }
    if (reviewedAssistantCandidate.budgetText !== undefined && canAcceptModelField('budget')) {
      acceptAssistantProfileField('budget');
      setBudgetText(reviewedAssistantCandidate.budgetText);
    }
    if (reviewedAssistantCandidate.travelStart !== undefined && reviewedAssistantCandidate.travelEnd !== undefined
        && canAcceptModelField('travelStart') && canAcceptModelField('travelEnd')) {
      acceptAssistantProfileField('travelStart'); acceptAssistantProfileField('travelEnd');
      setTravelStartText(reviewedAssistantCandidate.travelStart);
      setTravelEndText(reviewedAssistantCandidate.travelEnd);
    } else if (reviewedAssistantCandidate.relativeStartDate?.anchorDate && canAcceptModelField('travelStart')) {
      const start = reviewedAssistantCandidate.relativeStartDate.anchorDate;
      acceptAssistantProfileField('travelStart');
      setTravelStartText(start);
      if (canAcceptModelField('travelEnd')) {
        const end = inclusiveEndDate(start, reviewedAssistantCandidate.durationDays ?? Number(durationText));
        if (end) {
          acceptAssistantProfileField('travelEnd');
          setTravelEndText(end);
        }
      }
    }
    if (reviewedAssistantCandidate.interest !== undefined && canAcceptModelField('interests')) {
      acceptAssistantProfileField('interests');
      setInterestText(current => displayInterests(parseInterests([current, reviewedAssistantCandidate.interest!].filter(Boolean).join('، ')), locale));
    }
    if (reviewedAssistantCandidate.softPreferences?.length && canAcceptModelField('softPreferences')) {
      acceptAssistantProfileField('softPreferences');
      setSoftPreferenceText(current => displayInterests(parseInterests([current, ...reviewedAssistantCandidate.softPreferences!].filter(Boolean).join('، ')), locale));
    }
    if (reviewedAssistantCandidate.travelDifficulty?.length && canAcceptModelField('difficulty')) {
      acceptAssistantProfileField('difficulty'); setDifficultyText(displayInterests(reviewedAssistantCandidate.travelDifficulty, locale));
    }
    if (reviewedAssistantCandidate.weatherPreferences?.length && canAcceptModelField('weather')) {
      acceptAssistantProfileField('weather'); setWeatherPreferenceText(displayInterests(reviewedAssistantCandidate.weatherPreferences, locale));
    }
    if (reviewedAssistantCandidate.localCuisine?.length && canAcceptModelField('cuisine')) {
      acceptAssistantProfileField('cuisine'); setLocalCuisineText(displayInterests(reviewedAssistantCandidate.localCuisine, locale));
    }
    setDirty(true);
    invalidateConsent(); // Explicit profile confirmation remains mandatory.
    setAssistantCandidate(null);
    document.getElementById('trip-profile-editor')?.focus();
  };

  const confirmProfile = async () => {
    setAttemptedProfileReview(true);
    if (!hasDestination || reviewedDuration === null) {
      document.getElementById(!hasDestination ? 'profile-destination-0' : 'profile-duration')?.focus();
      return;
    }
    if (!session || !activeTrip || !online || !consentComplete || !travelerCountValid
        || !budgetValid || !datesValid || !interestsValid || !softPreferencesValid) {
      if (!online) setError(copy.offline);
      else if (!travelerCountValid) setError(copy.profileTravelersInvalid);
      else if (!budgetValid) setError(copy.profileBudgetInvalid);
      else if (!datesValid) setError(copy.profileDatesInvalid);
      else if (!interestsValid) setError(copy.profileInterestsInvalid);
      return;
    }
    setBusy(true); setError(''); setStatus('');
    const duration = reviewedDuration;
    const fieldSource = (manualField: string, source: string | undefined) =>
      manualProfileFieldsRef.current.has(manualField) && !assistantProfileFieldsRef.current.has(manualField)
        ? 'correction' : assistantProfileFieldsRef.current.has(manualField) ? 'llm' : source ?? 'traveler';
    const confirmedRequirements = {
      destinations: destinationNames.map(name => name.trim()).filter(Boolean),
      duration_days: duration,
      origin: originText.trim() || null,
      travel_dates: travelStartText && travelEndText
        ? { start: travelStartText, end: travelEndText } : null,
      traveler_count: travelerCountText.trim() ? Number(travelerCountText.trim()) : null,
      accessibility: extracted?.accessibility?.value ?? [],
      travel_difficulty: parseInterests(difficultyText),
      weather_preferences: parseInterests(weatherPreferenceText),
      local_cuisine: parseInterests(localCuisineText),
      budget: parseReviewedBudget(budgetText, locale),
      soft_preferences: softPreferences,
      interests,
      constraints: extracted?.constraints.value ?? [],
      confirmation_source: 'traveler_reviewed',
      field_provenance: {
        destinations: fieldSource('destination', extracted?.destinations.source),
        duration_days: fieldSource('duration', extracted?.durationDays.source),
        origin: fieldSource('origin', extracted?.origin.source),
        travel_dates: fieldSource('travelStart', extracted?.travelDates.source) === 'correction'
          || fieldSource('travelEnd', extracted?.travelDates.source) === 'correction' ? 'correction'
          : assistantProfileFieldsRef.current.has('travelStart') || assistantProfileFieldsRef.current.has('travelEnd') ? 'llm'
            : extracted?.travelDates.source ?? 'traveler',
        traveler_count: fieldSource('travelers', extracted?.travelerCount.source),
        budget: fieldSource('budget', extracted?.budget.source),
        interests: fieldSource('interests', extracted?.interests.source),
        soft_preferences: fieldSource('softPreferences', extracted?.softPreferences.source),
        travel_difficulty: fieldSource('difficulty', extracted?.travelDifficulty.source),
        weather_preferences: fieldSource('weather', extracted?.weatherPreferences.source),
        local_cuisine: fieldSource('cuisine', extracted?.localCuisine.source),
        constraints: extracted?.constraints.source ?? 'traveler', accessibility: extracted?.accessibility.source ?? 'traveler',
      },
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

  const shareRequestWithSelectedCompanies = async () => {
    if (!session || !activeTrip || !confirmed || !shareConsentAccepted || !online) return;
    if (shareToAllEligible) {
      if (eligibleCompanyCount < 1 || eligibleCompanyCount > broadcastLimit) return;
      const accepted = window.confirm(locale === 'fa-IR'
        ? `آیا با ارسال درخواست و برنامهٔ سفر (بدون متن اولیه) به همهٔ ${eligibleCompanyCount} شرکت تأییدشده و فعال فعلی موافقید؟ این اشتراک در صندوق داخلی شرکت‌ها قابل مشاهده است.`
        : `Share this reviewed trip with all ${eligibleCompanyCount} currently eligible companies?`);
      if (!accepted) return;
    } else if (!selectedShareOrganizations.length) return;
    setSharingBusy(true); setError(''); setStatus('');
    try {
      const shareResult = await travelerApi.shareTripWithCompanies(csrf, activeTrip.trip_id, {
        organization_ids: shareToAllEligible ? [] : selectedShareOrganizations,
        recipient_mode: shareToAllEligible ? 'all_eligible' : 'selected',
        broad_sharing_consent_confirmed: shareToAllEligible,
        consent_confirmed: true,
        include_original_request: shareToAllEligible ? false : includeOriginalRequestInShare,
        consent_policy_version: 'company-request-share-v1',
      });
      const [options, shares] = await Promise.all([
        travelerApi.companyShareOptions(activeTrip.trip_id), travelerApi.listTripCompanyShares(activeTrip.trip_id),
      ]);
      setShareOptions(options.items); setTripShares(shares.items);
      setEligibleCompanyCount(options.eligible_count ?? options.items.length);
      setSelectedShareOrganizations([]); setShareConsentAccepted(false); setShareToAllEligible(false);
      setStatus(shareResult.recipient_mode === 'all_eligible'
        ? (locale === 'fa-IR'
          ? `درخواست و برنامهٔ سفر با ${shareResult.recipient_count} شرکت تأییدشدهٔ فعلی در صندوق داخلی به اشتراک گذاشته شد.`
          : `Shared with ${shareResult.recipient_count} eligible companies in their protected inboxes.`)
        : (locale === 'fa-IR' ? 'درخواست تأییدشده فقط با شرکت‌های انتخاب‌شده به اشتراک گذاشته شد.'
          : locale === 'ar' ? 'تمت مشاركة الطلب المؤكد مع الشركات المحددة فقط.'
            : 'The reviewed request was shared only with the selected companies.'));
    } catch (value) { applyFailure(value); }
    finally { setSharingBusy(false); }
  };

  const revokeCompanyShare = async (shareId: string) => {
    if (!session || !activeTrip || !online || !window.confirm(locale === 'fa-IR'
      ? 'دسترسی این شرکت به نسخه‌های جدید درخواست لغو شود؟' : locale === 'ar'
        ? 'هل تريد إلغاء وصول هذه الشركة إلى الطلب؟' : 'Revoke this company’s access to the request?')) return;
    setSharingBusy(true);
    try {
      await travelerApi.revokeCompanyShare(csrf, activeTrip.trip_id, shareId);
      setTripShares(await travelerApi.listTripCompanyShares(activeTrip.trip_id).then(result => result.items));
    } catch (value) { applyFailure(value); }
    finally { setSharingBusy(false); }
  };

  const findRecommendations = async () => {
    if (!session || !activeTrip || !confirmed || dirty || !online) { if (!online) setError(copy.offline); return; }
    setBusy(true); setError(''); setStatus('');
    try {
      const result = await travelerApi.recommend(csrf, activeTrip.trip_id, activeTrip.destination_ids ?? []);
      setRecommendations(result); setItinerary(null);
      if (result.status === 'empty' || result.status === 'needs_confirmation') {
        const savedDraft = await travelerApi.getProvisionalItinerary(activeTrip.trip_id).catch(() => null);
        if (savedDraft) { setProvisionalItinerary(savedDraft); setProvisionalDays(savedDraft.days); }
      }
      const refreshed = await travelerApi.getTrip(activeTrip.trip_id);
      setActiveTrip(refreshed);
      if (result.reason_code === 'requirement_consent_stale') {
        setConfirmed(false);
        setError(localizeRecommendationCode(locale, result.reason_code));
        document.querySelector('.profile-confirm-action')?.scrollIntoView({ block: 'center' });
      }
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const saveProvisionalDraft = async () => {
    if (!session || !activeTrip || !confirmed || !online) { if (!online) setError(copy.offline); return; }
    const draftDayCount = requestedTripDays ?? dayCount;
    if (!Number.isInteger(draftDayCount) || draftDayCount < 1 || draftDayCount > 365) { setError(copy.dayCountInvalid); return; }
    const days: ProvisionalDay[] = Array.from({ length: draftDayCount }, (_, index) => ({
      day_number: index + 1,
      stops: (provisionalCandidate?.days.find(day => day.day_number === index + 1)?.stops ?? []).map((stop, stopIndex) => ({
        name: stop.name, role: stop.role, day_number: index + 1, stop_order: stopIndex + 1, notes_by_locale: {},
      })),
    }));
    setBusy(true); setError(''); setStatus('');
    try {
      const saved = await travelerApi.createProvisionalItinerary(csrf, activeTrip.trip_id, {
        expected_trip_version: activeTrip.version,
        day_count: draftDayCount,
        locale,
        title_by_locale: { [locale]: provisionalText[locale].title },
        days: days.map(day => ({ day_number: day.day_number, stops: day.stops.map(stop => ({ name: stop.name, role: stop.role })) })),
      });
      setProvisionalItinerary(saved); setProvisionalDays(saved.days); setProvisionalDirty(false); setDayCount(saved.day_count);
      setStatus(provisionalText[locale].saved);
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const saveProvisionalEdits = async () => {
    if (!session || !provisionalItinerary || !online) { if (!online) setError(copy.offline); return; }
    setBusy(true); setError(''); setStatus('');
    try {
      const saved = await travelerApi.updateProvisionalItinerary(csrf, provisionalItinerary.provisional_itinerary_id, {
        expected_revision: provisionalItinerary.revision,
        day_count: provisionalItinerary.day_count,
        title_by_locale: { ...provisionalItinerary.title_by_locale, [locale]: provisionalText[locale].title },
        days: provisionalDays.map(day => ({ day_number: day.day_number, stops: day.stops.map(stop => ({
          name: stop.name, role: stop.role, ...(stop.destination_id ? { destination_id: stop.destination_id } : {}),
          notes_by_locale: stop.notes_by_locale ?? {},
        })) })),
      });
      setProvisionalItinerary(saved); setProvisionalDays(saved.days); setProvisionalDirty(false); setStatus(provisionalText[locale].saved);
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const editProvisionalStop = (dayNumber: number, index: number, update: Partial<ProvisionalStop>) => {
    setProvisionalDays(days => days.map(day => day.day_number === dayNumber
      ? { ...day, stops: day.stops.map((stop, stopIndex) => stopIndex === index ? { ...stop, ...update } : stop) }
      : day));
    setProvisionalDirty(true);
  };

  const addProvisionalStop = (dayNumber: number) => {
    const name = newProvisionalStop.trim();
    if (!name || name.length > 160) return;
    setProvisionalDays(days => days.map(day => day.day_number === dayNumber
      ? { ...day, stops: [...day.stops, { name, role: 'traveler_provided', day_number: dayNumber, stop_order: day.stops.length + 1, notes_by_locale: {} }] }
      : day));
    setNewProvisionalStop(''); setProvisionalDirty(true);
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
      if (activeTrip?.trip_id === trip.trip_id) { setActiveTrip(null); setActiveConversation(null); setRecommendations(null); setItinerary(null); setProvisionalItinerary(null); setProvisionalDays([]); setProvisionalCandidate(null); }
      const history = await travelerApi.listConversations(50); setConversations(history.items); setStatus(copy.deleted);
    } catch (value) { applyFailure(value); }
    finally { setBusy(false); }
  };

  const deleteConversation = async (conversationId: string) => {
    if (!session || !online || !window.confirm(copy.deleteConversationConfirm)) return;
    setBusy(true); setError(''); setStatus('');
    try {
      await travelerApi.deleteConversation(csrf, conversationId);
      if (activeConversation?.conversation_id === conversationId) { setActiveConversation(null); setActiveTrip(null); setRecommendations(null); setItinerary(null); setProvisionalItinerary(null); setProvisionalDays([]); setProvisionalCandidate(null); }
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
        <div><p className="eyebrow">{copy.workspaceTitle}</p><h2 id="traveler-workspace-title">{activeTrip ? chatFlowCopy[locale].conversation : copy.workspaceTitle}</h2></div>
        {activeTrip && <span className="saved-pill">{copy.savedRecord}</span>}
      </div>

      {requirements && !activeTrip && <button className="primary journey-action" type="button" onClick={() => void persistDraft()} disabled={busy || !session || !online}>
        {busy ? copy.saving : activeConversation ? copy.createAnotherTrip : chatFlowCopy[locale].start}
      </button>}

      <TravelerGuidance locale={locale} hasTrip={Boolean(activeTrip)} confirmed={confirmed}
        hasRecommendations={Boolean(recommendations)} hasItinerary={Boolean(itinerary)} />
      <p className="privacy-notice">{copy.privacyNotice}</p>
      {!session && <p className="trip-form-help">{copy.signInToSave}</p>}
      {dirty && activeTrip && <p className="journey-alert" role="status">{copy.draftChanged}</p>}
      {error && <p className="journey-error" role="alert">{error}</p>}
      {status && <p className="journey-status" role="status">{status}</p>}

      {requirements && activeTrip && dirty && session
        && requirements.requestText !== activeTrip.original_request
        && <button className="primary journey-action" type="button" onClick={() => void (async () => {
        if (!activeConversation) return;
        setBusy(true); setError('');
        try {
          const result = await travelerApi.appendMessage(csrf, activeConversation.conversation_id, {
            trip_id: activeTrip.trip_id, content: requirements.requestText, extracted_requirements: requirementsForPersistence(requirements),
            idempotency_key: newIdempotencyKey(), expected_version: activeConversation.version, replace_previous_request: true,
          });
          setActiveConversation(result.conversation); setActiveTrip(result.trip); setDirty(false); setConfirmed(false); setRequirementChoices({}); setAdvisoryAcknowledgements({}); setRecommendations(null); setItinerary(null);
          setStatus(copy.saveSuccess);
        } catch (value) { applyFailure(value); }
        finally { setBusy(false); }
      })()} disabled={busy || !online}>{busy ? copy.saving : copy.updateTrip}</button>}

      {session && activeConversation && <div className="journey-new-actions">
        <button type="button" onClick={() => { setActiveTrip(null); setAssistantCandidate(null);  setConfirmed(false); setRequirementChoices({}); setAdvisoryAcknowledgements({}); setRecommendations(null); setItinerary(null); setDirty(false); setResolution(null); onStartNewDraft(); }}>{copy.createAnotherTrip}</button>
        <button type="button" onClick={() => { setActiveConversation(null); setActiveTrip(null); setAssistantCandidate(null);  setConfirmed(false); setRequirementChoices({}); setAdvisoryAcknowledgements({}); setRecommendations(null); setItinerary(null); setDirty(false); setResolution(null); onStartNewDraft(); }}>{copy.startNewConversation}</button>
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
            {guidedQuestion.field === 'duration' && <div className="clarification-short-answers">
              {([['1', chatFlowCopy[locale].oneDay], ['2', chatFlowCopy[locale].twoDays]] as const).map(([days, label]) =>
                <button key={days} type="button" disabled={busy || !online} onClick={() => {
                  setMessageText(locale === 'fa-IR' ? `مدت سفر ${days} روز است.` : locale === 'ar' ? `مدة الرحلة ${days} يوم.` : `The trip is ${days} day${days === '1' ? '' : 's'}.`);
                  setAssistantPromptSelected(false);
                  document.getElementById('trip-follow-up')?.focus();
                }}>{label}</button>)}
            </div>}
          </div>}
          <div className="assistant-prompt-suggestions" aria-label={assistantCopy[locale].promptsTitle}>
            <details><summary>{assistantCopy[locale].promptsTitle}</summary>
            <p>{assistantCopy[locale].promptHelp}</p>
            <div>{assistantCopy[locale].prompts.map(prompt => <button key={prompt} type="button"
              disabled={busy || !online} onClick={() => {
                setMessageText(prompt);
                setAssistantPromptSelected(true);
                document.getElementById('trip-follow-up')?.focus();
              }}>{prompt}</button>)}</div></details>
          </div>
          <label htmlFor="trip-follow-up">{copy.messagePlaceholder}</label>
          <textarea id="trip-follow-up" value={messageText}
            onChange={event => { setMessageText(event.target.value); setAssistantPromptSelected(false); }}
            onKeyDown={event => {
              if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing
                && messageText.trim() && !busy && online && messageText.length <= 1200) {
                event.preventDefault();
                void askAssistant();
              }
            }}
            maxLength={1200} rows={3} dir="auto" />
          {assistantPromptSelected && <p className="assistant-prompt-warning" role="status">{assistantCopy[locale].promptForAi}</p>}
          <details className="conversation-local-action">
            <summary>{assistantCopy[locale].saveWithoutAI}</summary>
            <button type="button" onClick={() => void sendMessage()}
              disabled={busy || !messageText.trim() || !online || assistantPromptSelected}>{assistantCopy[locale].saveWithoutAI}</button>
            <small>{copy.localSaveHelp}</small>
          </details>
          <div className="assistant-controls">

            <p className="assistant-provider-state" role="status" data-provider-state={assistantState}>
              {assistantReplyPending ? (locale === 'fa-IR' ? 'دستیار در حال پاسخ‌گویی است…' : locale === 'ar' ? 'يكتب المساعد الرد…' : 'The assistant is replying…')
                : assistantState === 'loading' ? (locale === 'fa-IR' ? 'در حال بررسی وضعیت دستیار…' : locale === 'ar' ? 'جارٍ التحقق من حالة المساعد…' : 'Checking assistant status…')
                : assistantState === 'configured' ? (locale === 'fa-IR' ? 'مسیر دستیار تنظیم شده است؛ پاسخ موفق هنوز در این گفت‌وگو ثبت نشده.' : locale === 'ar' ? 'مسار المساعد مُعدّ؛ لم يُسجّل رد ناجح في هذه المحادثة بعد.' : 'Assistant route is configured; no successful reply is recorded in this conversation yet.')
                  : assistantState === 'connected' ? (locale === 'fa-IR' ? 'اتصال به سرویس هوش مصنوعی برقرار است.' : locale === 'ar' ? 'تم الاتصال بخدمة الذكاء الاصطناعي.' : 'Connected to the AI service.')
                  : assistantState === 'responded' ? (locale === 'fa-IR' ? 'دستیار در همین گفت‌وگو پاسخ داده است.' : locale === 'ar' ? 'أجاب المساعد في هذه المحادثة.' : 'The assistant has replied in this conversation.')
                    : assistantState === 'quota_exhausted' ? (locale === 'fa-IR' ? 'سهمیهٔ روزانهٔ دستیار تمام شده است.' : locale === 'ar' ? 'اكتملت الحصة اليومية للمساعد.' : 'The assistant daily limit is reached.')
                      : assistantState === 'disabled' ? (locale === 'fa-IR' ? 'پاسخ‌گویی هوشمند فعال نیست؛ می‌توانید اطلاعات سفر را دستی ذخیره کنید.' : locale === 'ar' ? 'المساعد غير مفعّل؛ يمكنك حفظ تفاصيل الرحلة يدوياً.' : 'AI replies are disabled; you can still save trip details manually.')
                        : (locale === 'fa-IR' ? 'دستیار اکنون در دسترس نیست؛ درخواست سفر شما همچنان قابل ذخیره است.' : locale === 'ar' ? 'المساعد غير متاح حالياً؛ ويمكن حفظ تفاصيل الرحلة.' : 'The assistant is currently unavailable; trip details can still be saved.')}
              {assistantRemaining !== null && assistantState !== 'disabled' && assistantState !== 'unavailable' && <> · {locale === 'fa-IR' ? `سهمیهٔ قابل استفاده: ${formatNumber(locale, assistantRemaining)}` : locale === 'ar' ? `المتبقي اليوم: ${formatNumber(locale, assistantRemaining)}` : `${assistantRemaining} requests available today`}</>}
            </p>
            <p className="assistant-action-help">{assistantCopy[locale].advisorActionHelp}</p>
            <button className="primary" type="button" onClick={() => void askAssistant()}
              disabled={busy || !online || !messageText.trim() || messageText.length > 1200}>
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
                  {reviewedAssistantCandidate.softPreferences?.length && <>
                    <dt>{localizeRecommendationCode(locale, 'field:soft_preference')}</dt>
                    <dd dir="auto">{reviewedAssistantCandidate.softPreferences.join('، ')}</dd>
                  </>}
                </dl>
                <p>{assistantCopy[locale].unsaved}</p>
                <button type="button" onClick={applyAssistantCandidate} disabled={busy}>
                  {locale === 'fa-IR' ? 'استخراج نیازهای سفر' : locale === 'ar' ? 'استخراج متطلبات الرحلة' : 'Extract trip requirements'}
                </button>
                <button type="button" onClick={() => setAssistantCandidate(null)} disabled={busy}>{assistantCopy[locale].dismiss}</button>
              </div>}
          </div>
        </article>

        <article className="recommend-panel journey-panel" id="journey-recommendations">
          <div className="panel-title"><span className="mini-icon" aria-hidden="true">↗</span>{copy.profileTitle}</div>
          {import.meta.env.DEV && extractionPath && <small className="extraction-diagnostic" data-extraction-path={extractionPath} role="status">
            {extractionPath === 'llm' ? 'Extraction: configured LLM' : extractionPath === 'user_override' ? 'Extraction: traveler correction' : 'Extraction: deterministic fallback'}
          </small>}
          <p className="profile-next-step">{chatFlowCopy[locale].review}</p>
          {extracted && <section className="rahgard-extracted-summary" aria-labelledby="rahgard-extracted-summary-heading">
            <h3 id="rahgard-extracted-summary-heading">{locale === 'fa-IR' ? 'نیازهای استخراج‌شدهٔ سفر' : locale === 'ar' ? 'متطلبات الرحلة المستخلصة' : 'Extracted trip requirements'}</h3>
            <p>{locale === 'fa-IR' ? 'مقادیر از همین گفتگو و اصلاحات شما به‌روز می‌شوند؛ پیش از برنامه‌ریزی آن‌ها را تأیید کنید.' : 'Values reflect your conversation and edits; confirm them before planning.'}</p>
            <ul>{([
              { key: 'destination', label: copy.profileDestination, value: destinationNames.filter(name => name.trim()).join(' → '), required: true },
              { key: 'duration', label: copy.profileDuration, value: reviewedDuration !== null ? `${formatNumber(locale,reviewedDuration)} ${locale === 'fa-IR' ? 'روز' : 'days'}` : '', required: true },
              { key: 'origin', label: copy.profileOrigin, value: originText.trim(), required: false },
              { key: 'travelers', label: copy.profileTravelers, value: travelerCountText.trim(), required: false },
              { key: 'dates', label: copy.profileTravelStart, value: travelStartText && travelEndText ? `${travelStartText} – ${travelEndText}` : '', required: false },
              { key: 'budget', label: copy.profileBudget, value: budgetText.trim(), required: false },
              { key: 'interests', label: copy.profileInterests, value: interestText.trim(), required: false },
              { key: 'difficulty', label: locale === 'fa-IR' ? 'درجه سختی سفر' : 'Travel difficulty', value: difficultyText.trim(), required: false },
              { key: 'weather', label: locale === 'fa-IR' ? 'آب‌وهوا' : 'Weather', value: weatherPreferenceText.trim(), required: false },
              { key: 'cuisine', label: locale === 'fa-IR' ? 'غذای محلی' : 'Local cuisine', value: localCuisineText.trim(), required: false },
            ] as Array<{key:string; label:string; value:string; required:boolean}>).map(item =>
              <li key={item.key} data-required={item.required} data-filled={!!item.value}>
                <span className="rahgard-summary-indicator" aria-hidden="true">{item.value ? '✓' : item.required ? '!' : '○'}</span>
                <span className="rahgard-summary-label">{item.label}{item.required ? ' *' : ''}</span>
                <b dir="auto">{item.value || (item.required
                  ? (locale === 'fa-IR' ? 'نیاز به تکمیل' : 'Required')
                  : (locale === 'fa-IR' ? 'اختیاری' : 'Optional'))}</b>
              </li>)}</ul>
          </section>}
          {extracted && <div className="profile-editor" id="trip-profile-editor" tabIndex={-1}>
            <fieldset>
              <legend>{copy.profileDestination} <span className="trip-field-required">{locale === 'fa-IR' ? '(ضروری)' : locale === 'ar' ? '(مطلوب)' : '(Required)'}</span></legend>
              {(destinationNames.length ? destinationNames : ['']).map((name, index) => <div className="destination-edit-row" key={index}>
                <label htmlFor={`profile-destination-${index}`}>{copy.profileDestination} {formatNumber(locale, index + 1)}</label>
                <input id={`profile-destination-${index}`} aria-required={index === 0} aria-invalid={attemptedProfileReview && !hasDestination && index === 0} value={name} onChange={event => {
                  markProfileFieldEdited('destination');
                  const next = destinationNames.slice(); next[index] = event.target.value; setDestinationNames(next); setDirty(true); invalidateConsent(); void resolveNames(next);
                }} dir="auto" />
                <button type="button" aria-label={`${copy.removeDestination}: ${name}`} onClick={() => { markProfileFieldEdited('destination'); const next = destinationNames.filter((_, item) => item !== index); setDestinationNames(next); setDirty(true); invalidateConsent(); void resolveNames(next); }}>{copy.removeDestination}</button>
              </div>)}
              <button type="button" onClick={() => { markProfileFieldEdited('destination'); const next = [...destinationNames, '']; setDestinationNames(next); setDirty(true); invalidateConsent(); setResolution(null); }}>{copy.profileDestination} +</button>
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
                      <button type="button" onClick={() => { setCatalogueDestinations([]); setCatalogueNextCursor(null); void browseCatalogue(); }}>{locale === 'fa-IR' ? 'جست‌وجو' : locale === 'ar' ? 'بحث' : 'Search'}</button>
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
                      {catalogueNextCursor && <button type="button" disabled={catalogueLoading} onClick={() => void browseCatalogue(catalogueNextCursor,true)}>{locale === 'fa-IR' ? 'نتایج بیشتر' : locale === 'ar' ? 'المزيد من النتائج' : 'Load more results'}</button>}
                    </>}
              </div>}
              {!hasDestination && <p role={attemptedProfileReview ? 'alert' : undefined}>{copy.noDestination}</p>}
            </fieldset>
            <label htmlFor="profile-duration">{copy.profileDuration} <span className="trip-field-required">{locale === 'fa-IR' ? '(ضروری)' : locale === 'ar' ? '(مطلوب)' : '(Required)'}</span></label>
            <input id="profile-duration" type="number" min="1" max="365" aria-required="true" aria-invalid={attemptedProfileReview && reviewedDuration === null} aria-describedby={attemptedProfileReview && reviewedDuration === null ? 'profile-duration-error' : undefined} value={durationText} onChange={event => { const value = event.target.value; markProfileFieldEdited('duration'); setDurationText(value); const duration = Number(value); const start = travelStartText || extracted?.relativeStartDate.value?.anchor_date || extracted?.relativeDateResolution?.start || ''; if (start && extracted?.relativeStartDate.value && !manualProfileFieldsRef.current.has('travelEnd')) { const end = inclusiveEndDate(start, duration); if (end) setTravelEndText(end); } setDirty(true); invalidateConsent(); }} />
            {attemptedProfileReview && reviewedDuration === null && <p id="profile-duration-error" className="journey-error" role="alert">
              {locale === 'fa-IR' ? 'مدت سفر را به‌صورت عدد صحیح بین ۱ تا ۳۶۵ روز وارد کنید.' : locale === 'ar' ? 'أدخل مدة الرحلة بعدد صحيح بين يوم واحد و٣٦٥ يومًا.' : 'Enter a whole number from 1 to 365 days.'}
            </p>}
            <label htmlFor="profile-origin">{copy.profileOrigin} <span className="trip-field-optional">{locale === 'fa-IR' ? '(اختیاری)' : locale === 'ar' ? '(اختياري)' : '(Optional)'}</span></label>
            <input id="profile-origin" type="text" maxLength={100} dir="auto" value={originText}
              onChange={event => { markProfileFieldEdited('origin'); setOriginText(event.target.value); setDirty(true); invalidateConsent(); }} />
            {suggestedOrigin && <div className="approximate-origin-proposal" role="note">
              <p>{locale === 'fa-IR'
                ? `موقعیت تقریبی دستگاه: ${suggestedOrigin.approximateText} (دقت اعلام‌شده ±${Math.round(suggestedOrigin.accuracyMeters)} متر). این نقطه شهر یا ورودی مقصد نیست.`
                : locale === 'ar'
                  ? `موقعية الجهاز التقريبية: ${suggestedOrigin.approximateText} (الدقة المعلنة ±${Math.round(suggestedOrigin.accuracyMeters)} م). هذه ليست مدينة أو مدخلاً لمعلم.`
                : `Approximate device point: ${suggestedOrigin.approximateText} (the point is coarsened to ~1 km; device reported ±${Math.round(suggestedOrigin.accuracyMeters)} m). It is not a city or attraction entrance.`}</p>
              {locale !== 'en-US' && <small>{locale === 'fa-IR' ? 'مختصات پیشنهادی برای حفظ حریم خصوصی به حدود یک کیلومتر گرد شده‌اند.' : 'تم تقريب الإحداثيات المقترحة إلى نحو كيلومتر واحد لحماية الخصوصية.'}</small>}
              <button type="button" disabled={Boolean(originText.trim())} onClick={() => {
                if (originText.trim()) return;
                markProfileFieldEdited('origin');
                const label = locale === 'fa-IR' ? `موقعیت تقریبی GPS (${suggestedOrigin.approximateText})`
                  : locale === 'ar' ? `موقع GPS تقريبي (${suggestedOrigin.approximateText})`
                    : `Approximate GPS point (${suggestedOrigin.approximateText})`;
                setOriginText(label); setDirty(true); invalidateConsent();
              }}>{originText.trim()
                ? (locale === 'fa-IR' ? 'مبدأ واردشده حفظ شده است' : locale === 'ar' ? 'تم الاحتفاظ بنقطة الانطلاق المدخلة' : 'Keep entered origin')
                : (locale === 'fa-IR' ? 'استفاده از نقطهٔ تقریبی' : locale === 'ar' ? 'استخدم الموقع التقريبي' : 'Use approximate point')}</button>
            </div>}
            <label htmlFor="profile-travelers">{copy.profileTravelers}</label>
            <input id="profile-travelers" type="number" min="1" max="50" step="1" value={travelerCountText}
              aria-invalid={!travelerCountValid} onChange={event => { markProfileFieldEdited('travelers'); setTravelerCountText(event.target.value); setDirty(true); invalidateConsent(); }} />
            {!travelerCountValid && <p className="journey-error" role="alert">{copy.profileTravelersInvalid}</p>}
            <label htmlFor="profile-budget">{copy.profileBudget}</label>
            <input id="profile-budget" type="text" maxLength={100} dir="auto" value={budgetText}
              onChange={event => { markProfileFieldEdited('budget'); setBudgetText(event.target.value); setDirty(true); invalidateConsent(); }} />
            {!budgetValid && <p className="journey-error" role="alert">{copy.profileBudgetInvalid}</p>}
            {extracted?.relativeStartDate?.value && !extracted.travelDates.value && <p className="profile-relative-date" role="note">{chatFlowCopy[locale].relativeDate}</p>}
            <JalaliDatePicker id="profile-travel-start" label={copy.profileTravelStart} locale={locale}
              value={travelStartText} timeZone={travelerTimezone}
              onChange={value => { markProfileFieldEdited('travelStart'); onManualDateOverride?.(); setTravelStartText(value); setDirty(true); invalidateConsent(); }} />
            <JalaliDatePicker id="profile-travel-end" label={copy.profileTravelEnd} locale={locale}
              value={travelEndText} timeZone={travelerTimezone}
              onChange={value => { markProfileFieldEdited('travelEnd'); onManualDateOverride?.(); setTravelEndText(value); setDirty(true); invalidateConsent(); }} />
            {!datesValid && <p className="journey-error" role="alert">{copy.profileDatesInvalid}</p>}
            <label htmlFor="profile-interests">{copy.profileInterests}</label>
            <textarea id="profile-interests" maxLength={300} rows={2} dir="auto" value={interestText}
              onChange={event => { markProfileFieldEdited('interests'); setInterestText(event.target.value); setDirty(true); invalidateConsent(); }} />
            {!interestsValid && <p className="journey-error" role="alert">{copy.profileInterestsInvalid}</p>}
            <label htmlFor="profile-soft-preferences">{locale === 'fa-IR' ? 'ترجیح‌های اختیاری (جدا با ویرگول)' : locale === 'ar' ? 'التفضيلات الاختيارية (افصل بينها بفواصل)' : 'Optional preferences (comma-separated)'}</label>
            <textarea id="profile-soft-preferences" maxLength={300} rows={2} dir="auto" value={softPreferenceText}
              onChange={event => { markProfileFieldEdited('softPreferences'); setSoftPreferenceText(event.target.value); setDirty(true); invalidateConsent(); }} />
            {!softPreferencesValid && <p className="journey-error" role="alert">{copy.profileInterestsInvalid}</p>}
            <label htmlFor="profile-travel-difficulty">{locale === 'fa-IR' ? 'ترجیح سختی مسیر' : locale === 'ar' ? 'مستوى صعوبة المسار' : 'Travel difficulty preference'}</label>
            <textarea id="profile-travel-difficulty" maxLength={300} rows={2} dir="auto" value={difficultyText}
              onChange={event => { markProfileFieldEdited('difficulty'); setDifficultyText(event.target.value); setDirty(true); invalidateConsent(); }} />
            <label htmlFor="profile-weather-preferences">{locale === 'fa-IR' ? 'ترجیح‌های آب‌وهوا' : locale === 'ar' ? 'تفضيلات الطقس' : 'Weather preferences'} {optionalField}</label>
            <textarea id="profile-weather-preferences" maxLength={300} rows={2} dir="auto" value={weatherPreferenceText}
              onChange={event => { markProfileFieldEdited('weather'); setWeatherPreferenceText(event.target.value); setDirty(true); invalidateConsent(); }} />
            <label htmlFor="profile-local-cuisine">{locale === 'fa-IR' ? 'علاقه به خوراک محلی' : locale === 'ar' ? 'اهتمام بالمأكولات المحلية' : 'Local cuisine interests'}</label>
            <textarea id="profile-local-cuisine" maxLength={300} rows={2} dir="auto" value={localCuisineText}
              onChange={event => { markProfileFieldEdited('cuisine'); setLocalCuisineText(event.target.value); setDirty(true); invalidateConsent(); }} />
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
            </fieldset> : item.kind === 'resolved' || item.kind === 'confirmed' ? <p key={index} role="status" dir="auto">{item.destination.localizedNames[locale] ?? item.destination.canonicalName} · {item.kind === 'resolved' ? copy.catalogueMatch : copy.selectedByYou}</p> : item.kind === 'not-found' ? <p key={index} role="status">{item.originalPhrase}: {localizeRecommendationCode(locale, 'destination_identity_unresolved')}</p> : null)}
            <button type="button" className="primary profile-confirm-action" onClick={() => void confirmProfile()} disabled={busy || (!dirty && confirmed) || !online || !consentComplete || !travelerCountValid
              || !budgetValid || !datesValid || !interestsValid}>{copy.confirmProfile}</button>
          </div>}
          {confirmed && <div className="recommendation-controls">
            <h3>{copy.recommendationTitle}</h3>
            <button type="button" onClick={() => void findRecommendations()} disabled={busy || !online}>{busy ? copy.checkingRecommendations : copy.findRecommendations}</button>
            {recommendations && recommendations.status !== 'available' && <div className="empty-state" role="status">
              <p>{recommendations.status === 'empty' ? copy.recommendationEmpty : recommendations.reason_code
                ? localizeRecommendationCode(locale, recommendations.reason_code)
                : copy.recommendationClarify}</p>
              {recommendations.status === 'needs_confirmation' && <>
                {!!recommendations.unresolved_fields.length && <ul className="unresolved-requirements">
                  {recommendations.unresolved_fields.map(field => <li key={field}>{localizeRecommendationCode(locale, `field:${field}`)}</li>)}
                </ul>}
              </>}
            </div>}
            {provisionalPlanningAllowed && !provisionalCandidate && !provisionalItinerary && <section className="provisional-plan-card" aria-label={provisionalText[locale].title}>
              <span className="provisional-plan-badge">{provisionalText[locale].heading}</span>
              <h4>{provisionalText[locale].title}</h4>
              <p>{provisionalText[locale].warning}</p>
              <p>{locale === 'fa-IR'
                ? 'برای این درخواست پیشنهاد تأییدشده‌ای پیدا نشد. می‌توانید یک پیش‌نویس روزبه‌روز و قابل ویرایش تهیه کنید.'
                : locale === 'ar'
                  ? 'لا توجد توصية موثقة لهذا الطلب. يمكنك إنشاء مسودة يومية قابلة للتعديل.'
                  : 'There are no verified suggestions for this request. You can create an editable day-by-day draft.'}</p>
              <button id="generate-provisional-itinerary" className="primary" type="button" disabled={busy || !online || !assistantConfigured}
                onClick={() => {
                  const duration = requestedTripDays ?? Number(durationText);
                  const summary = [
                    destinationNames.filter(Boolean).join('، '),
                    Number.isInteger(duration) && duration > 0 ? String(duration) : '',
                    originText, travelStartText, travelEndText, travelerCountText, budgetText, interestText,
                    difficultyText, weatherPreferenceText, localCuisineText, softPreferenceText,
                  ].filter(Boolean).join(' | ').slice(0, 650);
                  const instruction = locale === 'fa-IR'
                    ? `برای این اطلاعات تأییدشدهٔ سفر (${summary})، لطفاً یک پیش‌نویس برنامهٔ روزبه‌روز با نام مکان‌های پیشنهادی در قالب provisional_itinerary تهیه کن. همهٔ مکان‌ها تأییدنشده‌اند؛ ساعت، هزینه، مسیر و اطلاعات ایمنی را ادعا نکن.`
                    : locale === 'ar'
                      ? `أنشئ مسودة رحلة يومية في provisional_itinerary لهذه التفاصيل المؤكدة (${summary}). أسماء الأماكن اقتراحات غير موثقة؛ لا تخترع المواعيد أو الأسعار أو الطرق أو معلومات السلامة.`
                      : `Create a day-by-day provisional_itinerary for this confirmed trip profile (${summary}). Suggested place names are unverified. Do not invent hours, prices, routes or safety facts.`;
                  void askAssistant(instruction);
                }}>{locale === 'fa-IR' ? 'دریافت برنامهٔ پیشنهادی از هوش مصنوعی' : locale === 'ar' ? 'إنشاء خطة أولية بالذكاء الاصطناعي' : 'Generate preliminary AI itinerary'}</button>
              <button className="secondary" type="button" disabled={busy || !online || !dayCountValid}
                onClick={() => void saveProvisionalDraft()}>{locale === 'fa-IR' ? 'ساخت برنامهٔ خالی برای ویرایش دستی' : locale === 'ar' ? 'إنشاء خطة فارغة للتحرير اليدوي' : 'Create an editable blank itinerary'}</button>
            </section>}
            {(provisionalCandidate || provisionalItinerary) && provisionalPlanningAllowed && <section className="provisional-plan-card" aria-labelledby="provisional-plan-title">
              <span className="provisional-plan-badge">{provisionalText[locale].heading}</span>
              <h4 id="provisional-plan-title">{provisionalText[locale].title}</h4>
              <p>{provisionalText[locale].warning}</p>
              {provisionalCandidate && !provisionalItinerary && <>
                <div className="provisional-plan-preview">
                  {Array.from({ length: requestedTripDays ?? dayCount }, (_, index) => {
                    const number = index + 1;
                    const day = provisionalCandidate.days.find(item => item.day_number === number);
                    return <div key={number}><strong>{copy.day} {formatNumber(locale, number)}</strong>
                      {day?.stops.length ? <ul>{day.stops.map((stop, stopIndex) => <li key={`${number}-${stopIndex}`} dir="auto">{stop.name} <small>· {provisionalText[locale].model}</small></li>)}</ul> : <p className="unplanned-day">{copy.unplannedDay}</p>}
                    </div>;
                  })}
                </div>
                <button id="save-provisional-itinerary" className="primary" type="button" onClick={() => void saveProvisionalDraft()} disabled={busy || !online || !dayCountValid}>{busy ? copy.saving : provisionalText[locale].save}</button>
              </>}
              {provisionalItinerary && <p role="status">{provisionalText[locale].saved}</p>}
            </section>}
            {recommendations?.requirement_assessments?.some(item => item.field === 'soft_preference'
              && item.status === 'known' && item.reason_code === 'known_fit_not_catalogue_verified')
              && <div className="journey-alert not-evaluated-warning" role="status">
                <strong>{copy.requirementNotEvaluatedTitle}</strong>
                <p>{copy.requirementAdvisoryWarning}</p>
                <p>{localizeRecommendationCode(locale, 'field:soft_preference')}</p>
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
                <button type="button" className="primary itinerary-generate-action" onClick={() => void createItinerary()} disabled={busy || !online || !dayCountValid}>{copy.createItinerary}</button>
              </>}
              {itinerary && <p>{copy.itinerarySaved}</p>}
            </div>}
          </div>}
        </article>
      </div>}

      {confirmed && activeTrip && session && <section className="company-request-sharing" aria-labelledby="company-request-share-title">
        <h3 id="company-request-share-title">{locale === 'fa-IR' ? 'اشتراک‌گذاری اختیاری با شرکت‌های گردشگری' : locale === 'ar' ? 'مشاركة اختيارية مع شركات السياحة' : 'Optional sharing with tourism companies'}</h3>
        <p>{locale === 'fa-IR'
          ? 'می‌توانید شرکت‌های خاص را انتخاب کنید یا با اجازهٔ جداگانه، اطلاعات تأییدشدهٔ سفر را به همهٔ شرکت‌های مجاز فعلی در صندوق داخلی بفرستید. نسخه‌های اصلاحی در همان درخواست ثبت می‌شوند. پیامک یا ارسال عمومی وجود ندارد.'
          : locale === 'ar'
            ? 'لا ترى الطلب المؤكد وخطة الرحلة إلا الشركات المعتمدة التي تختارها. تُضاف التعديلات كإصدارات جديدة في صندوق المؤسسة نفسه. لا تُرسل رسائل عامة أو رسائل نصية.'
            : 'Only verified companies you select can see your reviewed request and itinerary. Later edits create a new revision in the same inbox. No public broadcast or SMS is sent.'}</p>
        {shareOptions.length > 0 ? <fieldset className="company-share-options">
          <legend>{locale === 'fa-IR' ? 'روش اشتراک‌گذاری' : locale === 'ar' ? 'طريقة المشاركة' : 'Sharing method'}</legend>
          <label className="company-share-mode">
            <input type="radio" name="company-share-mode" checked={!shareToAllEligible}
              onChange={() => { setShareToAllEligible(false); setShareConsentAccepted(false); }} />
            {locale === 'fa-IR' ? 'انتخاب شرکت‌های مشخص' : 'Choose named companies'}
          </label>
          <label className="company-share-mode">
            <input type="radio" name="company-share-mode" checked={shareToAllEligible}
              onChange={() => { setShareToAllEligible(true); setShareConsentAccepted(false); setIncludeOriginalRequestInShare(false); }} />
            {locale === 'fa-IR' ? `ارسال به همهٔ ${eligibleCompanyCount} شرکت تأییدشده و فعال فعلی`
              : `Share with all ${eligibleCompanyCount} currently eligible companies`}
          </label>
          {shareToAllEligible && <p className="company-share-broadcast-note" role="note">
            {eligibleCompanyCount > broadcastLimit
              ? (locale === 'fa-IR' ? `تعداد شرکت‌ها بیش از سقف ایمن ${broadcastLimit} است؛ ارسال گروهی نیازمند تقسیم به دسته‌های کنترل‌شده است.` : 'Too many companies for a single safe batch.')
              : (locale === 'fa-IR' ? 'این انتخاب فقط برای شرکت‌های واجد شرایط در لحظهٔ ارسال اجرا می‌شود؛ شرکت‌های جدید در آینده خودکار اضافه نمی‌شوند. متن اولیهٔ درخواست ارسال نمی‌شود.' : 'Only currently eligible companies will receive a protected inbox entry. Original raw request is excluded.')}
          </p>}
          {!shareToAllEligible && shareOptions.map(option => <label key={option.organization_id}>
            <input type="checkbox" checked={selectedShareOrganizations.includes(option.organization_id)}
              onChange={event => {
                const checked = event.currentTarget.checked;
                setSelectedShareOrganizations(current => checked
                  ? [...new Set([...current, option.organization_id])].slice(0, 10)
                  : current.filter(id => id !== option.organization_id));
              }} />
            <span>{option.display_name}</span>
          </label>)}
          {!shareToAllEligible && <label><input type="checkbox" checked={includeOriginalRequestInShare}
            onChange={event => setIncludeOriginalRequestInShare(event.currentTarget.checked)} />
            {locale === 'fa-IR' ? 'متن اولیهٔ درخواست هم ارسال شود' : locale === 'ar' ? 'تضمين نص الطلب الأصلي' : 'Include the original request text'}</label>}
          <label className="company-share-consent"><input type="checkbox" checked={shareConsentAccepted}
            onChange={event => setShareConsentAccepted(event.currentTarget.checked)} />
            {locale === 'fa-IR' ? (shareToAllEligible
              ? 'با اشتراک‌گذاری اطلاعات تأییدشدهٔ سفر با تمام شرکت‌های فعال و تأییدشدهٔ فعلی موافقم.'
              : 'اجازه می‌دهم اطلاعات تأییدشدهٔ سفر و برنامهٔ آن با شرکت‌های انتخاب‌شده به اشتراک گذاشته شود.')
              : locale === 'ar' ? 'أوافق على مشاركة تفاصيل الرحلة المؤكدة وخطتها مع الشركات التي اخترتها.'
                : 'I authorize sharing my reviewed trip request and itinerary with the selected companies.'}</label>
          <button type="button" className="primary" onClick={() => void shareRequestWithSelectedCompanies()}
            disabled={sharingBusy || !online || !shareConsentAccepted
              || (shareToAllEligible ? eligibleCompanyCount === 0 || eligibleCompanyCount > broadcastLimit : !selectedShareOrganizations.length)}>
            {sharingBusy ? copy.saving : shareToAllEligible
              ? (locale === 'fa-IR' ? 'ارسال به همهٔ شرکت‌های مجاز' : 'Share with all eligible companies')
              : locale === 'fa-IR' ? 'اشتراک‌گذاری با شرکت‌های انتخاب‌شده' : locale === 'ar' ? 'مشاركة مع الشركات المحددة' : 'Share with selected companies'}
          </button>
        </fieldset> : <p role="status">{locale === 'fa-IR' ? 'در حال حاضر شرکت گردشگری تأییدشده‌ای برای انتخاب وجود ندارد.'
          : locale === 'ar' ? 'لا توجد حالياً شركات سياحة معتمدة للاختيار.' : 'No verified tourism companies are available to select.'}</p>}
        {!!tripShares.length && <ul className="company-share-list" aria-label={locale === 'fa-IR' ? 'شرکت‌های دارای دسترسی' : locale === 'ar' ? 'الشركات التي لديها وصول' : 'Companies with access'}>
          {tripShares.map(share => <li key={share.share_id}>
            <span>{share.display_name} · {locale === 'fa-IR' ? `نسخه ${formatNumber(locale, share.latest_revision ?? 0)}` : `revision ${share.latest_revision ?? 0}`}</span>
            {share.revoked_at ? <span>{locale === 'fa-IR' ? 'دسترسی لغوشده' : locale === 'ar' ? 'تم إلغاء الوصول' : 'Access revoked'}</span>
              : <button type="button" className="danger" disabled={sharingBusy} onClick={() => void revokeCompanyShare(share.share_id)}>
                {locale === 'fa-IR' ? 'لغو دسترسی' : locale === 'ar' ? 'إلغاء الوصول' : 'Revoke access'}
              </button>}
          </li>)}
        </ul>}
      </section>}

      {confirmed && activeTrip && session && <TravelerCompanyResponses
        locale={locale} csrfToken={csrf} tripId={activeTrip.trip_id}
        highlightResponseId={new URLSearchParams(window.location.search).get('company_response')} />}

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
                    }} className="danger">{copy.removeStop}</button>
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
        <button type="button" className="primary itinerary-save-action" onClick={() => void saveItinerary()} disabled={busy || !online || editableStops.length > 1_000 || editableStops.some(stop => editableStops.filter(other => other.day_number === stop.day_number).length > 50)}>{copy.saveItinerary}</button>
      </section>}

      {provisionalItinerary && <section className="saved-itinerary provisional-itinerary" aria-labelledby="provisional-itinerary-title">
        <span className="provisional-plan-badge">{provisionalText[locale].heading}</span>
        <h3 id="provisional-itinerary-title">{provisionalText[locale].edit}</h3>
        <p className="provisional-warning">{provisionalText[locale].warning}</p>
        <div className="saved-itinerary-days">
          {provisionalDays.map(day => <section className="itinerary-day" key={day.day_number} aria-labelledby={`provisional-day-${day.day_number}`}>
            <h4 id={`provisional-day-${day.day_number}`}>{copy.day} {formatNumber(locale, day.day_number)}</h4>
            {day.stops.length === 0 && <p className="unplanned-day" role="status">{copy.unplannedDay}</p>}
            {day.stops.map((stop, index) => <article className="saved-stop provisional-stop" key={`${day.day_number}-${index}`}>
              <label htmlFor={`provisional-name-${day.day_number}-${index}`}>{provisionalText[locale].name}</label>
              <input id={`provisional-name-${day.day_number}-${index}`} dir="auto" maxLength={160} value={stop.name}
                onChange={event => editProvisionalStop(day.day_number, index, { name: event.target.value })} />
              <small>{stop.role === 'traveler_provided' ? provisionalText[locale].traveler : provisionalText[locale].model}</small>
              <label htmlFor={`provisional-note-${day.day_number}-${index}`}>{provisionalText[locale].note}</label>
              <textarea id={`provisional-note-${day.day_number}-${index}`} dir="auto" maxLength={1000} value={stop.notes_by_locale?.[locale] ?? ''}
                onChange={event => editProvisionalStop(day.day_number, index, { notes_by_locale: { ...stop.notes_by_locale, [locale]: event.target.value } })} />
              <label htmlFor={`provisional-move-${day.day_number}-${index}`}>{provisionalText[locale].move}</label>
              <select id={`provisional-move-${day.day_number}-${index}`} value={day.day_number} onChange={event => {
                const targetDay = Number(event.target.value);
                setProvisionalDays(days => days.map(item => {
                  if (item.day_number === day.day_number) return { ...item, stops: item.stops.filter((_, stopIndex) => stopIndex !== index) };
                  if (item.day_number === targetDay) return { ...item, stops: [...item.stops, { ...stop, day_number: targetDay, stop_order: item.stops.length + 1 }] };
                  return item;
                }));
                setProvisionalDirty(true);
              }}>{provisionalDays.map(item => <option key={item.day_number} value={item.day_number}>{copy.day} {formatNumber(locale, item.day_number)}</option>)}</select>
              <button type="button" className="secondary" onClick={() => {
                setProvisionalDays(days => days.map(item => item.day_number === day.day_number ? { ...item, stops: item.stops.filter((_, stopIndex) => stopIndex !== index) } : item));
                setProvisionalDirty(true);
              }}>{provisionalText[locale].remove}</button>
            </article>)}
            <div className="provisional-add-stop">
              <label htmlFor={`provisional-add-${day.day_number}`}>{provisionalText[locale].add}</label>
              <input id={`provisional-add-${day.day_number}`} dir="auto" maxLength={160} value={newProvisionalStop} onChange={event => setNewProvisionalStop(event.target.value)} />
              <button type="button" className="secondary" onClick={() => addProvisionalStop(day.day_number)} disabled={!newProvisionalStop.trim()}>{provisionalText[locale].add}</button>
            </div>
          </section>)}
        </div>
        <button className="primary" type="button" onClick={() => void saveProvisionalEdits()} disabled={busy || !online || !provisionalDirty}>{busy ? copy.saving : provisionalText[locale].saveChanges}</button>
      </section>}

      {session && <section className="trip-history" aria-labelledby="trip-history-title">
        <div className="trip-history-heading"><h3 id="trip-history-title">{copy.historyTitle}</h3><button type="button" onClick={() => void travelerApi.listConversations(50).then(result => setConversations(result.items)).catch(applyFailure)} disabled={loadingHistory || busy}>{copy.retry}</button></div>
        {loadingHistory ? <p role="status">{copy.saving}</p> : conversations.length === 0 ? <p>{copy.historyEmpty}</p> : conversations.map(conversation => <article className="history-conversation" data-conversation-id={conversation.conversation_id} key={conversation.conversation_id}>
          {(conversation.trips ?? []).map(trip => <div className="history-trip" data-trip-id={trip.trip_id} key={trip.trip_id}>
            <button type="button" onClick={() => void restoreTrip(conversation.conversation_id, trip.trip_id)} disabled={busy} dir="auto">{trip.original_request || copy.openTrip}</button>
            <button type="button" className="danger" onClick={() => void deleteTrip(trip)} disabled={busy}>{copy.deleteTrip}</button>
          </div>)}
          <button type="button" className="danger" onClick={() => void deleteConversation(conversation.conversation_id)} disabled={busy}>{copy.deleteConversation}</button>
        </article>)}
      </section>}
    </section>
  );
}
