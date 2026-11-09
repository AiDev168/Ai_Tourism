/** Only explicitly reviewable AI hints enter the editable trip form. */
export type ReviewableAssistantCandidate = {
  destination: string | null;
  durationDays: number | null;
  origin?: string;
  travelerCount?: number;
};

function safePlace(value: unknown): string | null {
  return typeof value === 'string' && value.trim().length > 0
    && value.trim().length <= 100 && !value.includes('\\') && !/[\u0000-\u001f\u007f]/u.test(value)
    ? value.trim() : null;
}

export function reviewableAssistantCandidate(
  raw: Record<string, string | number | null> | null,
): ReviewableAssistantCandidate | null {
  if (!raw) return null;
  const destination = safePlace(raw.destination ?? raw.destination_name ?? raw.destinations);
  const rawDays = raw.duration_days ?? raw.durationDays;
  const durationDays = typeof rawDays === 'number' && Number.isInteger(rawDays)
    && rawDays >= 1 && rawDays <= 365 ? rawDays : null;
  const origin = safePlace(raw.origin);
  const rawTravelers = raw.traveler_count;
  const travelerCount = typeof rawTravelers === 'number' && Number.isInteger(rawTravelers)
    && rawTravelers >= 1 && rawTravelers <= 50 ? rawTravelers : null;
  if (destination === null && durationDays === null && origin === null && travelerCount === null) return null;
  const candidate: ReviewableAssistantCandidate = { destination, durationDays };
  if (origin !== null) candidate.origin = origin;
  if (travelerCount !== null) candidate.travelerCount = travelerCount;
  return candidate;
}
