/** Only explicitly reviewed AI hints enter the editable trip form. */
import { createTripRequirements, type TripRequirementsV1 } from './tripIntake';

export type ReviewableAssistantCandidate = {
  destination: string | null;
  durationDays: number | null;
  origin?: string;
  travelerCount?: number;
  budgetText?: string;
  travelStart?: string;
  travelEnd?: string;
  interest?: string;
  typedRequirements?: TripRequirementsV1;
};

function safeText(value: unknown, limit: number): string | null {
  return typeof value === 'string' && value.trim().length > 0 && value.trim().length <= limit
    && !value.includes('\\') && !/[\u0000-\u001f\u007f]/u.test(value) ? value.trim() : null;
}

function validIsoDay(text: unknown): text is string {
  if (typeof text !== 'string' || !/^\d{4}-\d{2}-\d{2}$/u.test(text)) return false;
  const date = new Date(text + 'T00:00:00Z');
  return !Number.isNaN(date.valueOf()) && date.toISOString().slice(0, 10) === text;
}

function typedCandidate(raw: unknown): TripRequirementsV1 | null {
  if (!raw || typeof raw !== 'object') return null;
  const value = raw as Partial<TripRequirementsV1>;
  if (value.contract_version !== 'trip-requirements-v1' || typeof value.original_text !== 'string'
      || value.original_text.length > 1200 || !value.fields || !value.clarification) return null;
  return value as TripRequirementsV1;
}

export function reviewableAssistantCandidate(raw: unknown): ReviewableAssistantCandidate | null {
  const typed = typedCandidate(raw);
  if (typed) {
    const fields = typed.fields;
    const known = <T,>(field: { status?: string; value?: T | null }) => field.status === 'known' ? field.value ?? null : null;
    const destination = safeText(known(fields.destination), 100);
    const duration = known(fields.duration_days);
    const durationDays = typeof duration === 'number' && Number.isInteger(duration) && duration >= 1 && duration <= 365 ? duration : null;
    const candidate: ReviewableAssistantCandidate = { destination, durationDays, typedRequirements: typed };
    const origin = safeText(known(fields.origin), 100);
    if (origin) candidate.origin = origin;
    const travelers = known(fields.travelers);
    if (typeof travelers === 'number' && Number.isInteger(travelers) && travelers >= 1 && travelers <= 50) candidate.travelerCount = travelers;
    const budget = known(fields.budget);
    if (budget && typeof budget.raw === 'string' && budget.raw.length <= 120) candidate.budgetText = budget.raw;
    const dates = known(fields.travel_dates);
    if (dates && validIsoDay(dates.start) && validIsoDay(dates.end) && dates.start <= dates.end) {
      candidate.travelStart = dates.start; candidate.travelEnd = dates.end;
    }
    const interests = known(fields.interests);
    if (Array.isArray(interests) && interests.length && interests.every(item => typeof item === 'string' && item.length <= 100)) candidate.interest = interests.join('، ');
    return candidate;
  }

  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const flat = raw as Record<string, unknown>;
  const destination = safeText(flat.destination ?? flat.destination_name ?? flat.destinations, 100);
  const rawDays = flat.duration_days ?? flat.durationDays;
  const durationDays = typeof rawDays === 'number' && Number.isInteger(rawDays) && rawDays >= 1 && rawDays <= 365 ? rawDays : null;
  const candidate: ReviewableAssistantCandidate = { destination, durationDays };
  const origin = safeText(flat.origin, 100); if (origin) candidate.origin = origin;
  const rawTravelers = flat.traveler_count;
  if (typeof rawTravelers === 'number' && Number.isInteger(rawTravelers) && rawTravelers >= 1 && rawTravelers <= 50) candidate.travelerCount = rawTravelers;
  const rawBudget = safeText(flat.budget_text, 100);
  const parsedBudget = rawBudget ? createTripRequirements({ requestText: rawBudget, locale: 'fa-IR' }) : null;
  if (rawBudget && parsedBudget && parsedBudget.kind !== 'invalid' && parsedBudget.requirements.budget.value) candidate.budgetText = rawBudget;
  const interest = safeText(flat.interest, 100); if (interest) candidate.interest = interest;
  const start = flat.travel_start, end = flat.travel_end;
  if (validIsoDay(start) && validIsoDay(end) && start <= end) { candidate.travelStart = start; candidate.travelEnd = end; }
  return candidate.destination === null && candidate.durationDays === null && !candidate.origin
    && !candidate.travelerCount && !candidate.budgetText && !candidate.interest && !candidate.travelStart ? null : candidate;
}
