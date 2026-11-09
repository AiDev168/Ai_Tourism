/** Only explicitly reviewable AI hints enter the editable trip form. */
import { createTripRequirements } from './tripIntake';

export type ReviewableAssistantCandidate = {
  destination: string | null;
  durationDays: number | null;
  origin?: string;
  travelerCount?: number;
  budgetText?: string;
  travelStart?: string;
  travelEnd?: string;
  interest?: string;
};

function safeText(value: unknown, limit: number): string | null {
  return typeof value === 'string' && value.trim().length > 0
    && value.trim().length <= limit && !value.includes('\\')
    && !/[\u0000-\u001f\u007f]/u.test(value) ? value.trim() : null;
}

function validIsoDay(text: unknown): text is string {
  if (typeof text !== 'string' || !/^\d{4}-\d{2}-\d{2}$/u.test(text)) return false;
  const date = new Date(text + 'T00:00:00Z');
  return !Number.isNaN(date.valueOf()) && date.toISOString().slice(0, 10) === text;
}

export function reviewableAssistantCandidate(
  raw: Record<string, string | number | null> | null,
): ReviewableAssistantCandidate | null {
  if (!raw) return null;
  const destination = safeText(raw.destination ?? raw.destination_name ?? raw.destinations, 100);
  const rawDays = raw.duration_days ?? raw.durationDays;
  const durationDays = typeof rawDays === 'number' && Number.isInteger(rawDays)
    && rawDays >= 1 && rawDays <= 365 ? rawDays : null;
  const origin = safeText(raw.origin, 100);
  const rawTravelers = raw.traveler_count;
  const travelerCount = typeof rawTravelers === 'number' && Number.isInteger(rawTravelers)
    && rawTravelers >= 1 && rawTravelers <= 50 ? rawTravelers : null;
  const rawBudget = safeText(raw.budget_text, 100);
  const parsedBudget = rawBudget ? createTripRequirements({ requestText: rawBudget, locale: 'fa-IR' }) : null;
  const budgetText = parsedBudget && parsedBudget.kind !== 'invalid' && parsedBudget.requirements.budget.value
    ? rawBudget : null;
  const interest = safeText(raw.interest, 100);
  const start = raw.travel_start, end = raw.travel_end;
  const validRange = validIsoDay(start) && validIsoDay(end) && start <= end;
  if (destination === null && durationDays === null && origin === null
    && travelerCount === null && budgetText === null && interest === null && !validRange) return null;
  const candidate: ReviewableAssistantCandidate = { destination, durationDays };
  if (origin !== null) candidate.origin = origin;
  if (travelerCount !== null) candidate.travelerCount = travelerCount;
  if (budgetText !== null) candidate.budgetText = budgetText;
  if (interest !== null) candidate.interest = interest;
  if (validRange) { candidate.travelStart = start; candidate.travelEnd = end; }
  return candidate;
}
