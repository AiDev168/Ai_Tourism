/** Only explicitly reviewable AI hints enter the editable trip form. */
export type ReviewableAssistantCandidate = {
  destination: string | null;
  durationDays: number | null;
};

export function reviewableAssistantCandidate(
  raw: Record<string, string | number | null> | null,
): ReviewableAssistantCandidate | null {
  if (!raw) return null;
  const name = raw.destination ?? raw.destination_name ?? raw.destinations;
  const destination = typeof name === 'string' && name.trim().length > 0
    && name.trim().length <= 100 && !/[\u0000-\u001f\u007f]/u.test(name)
    ? name.trim() : null;
  const rawDays = raw.duration_days ?? raw.durationDays;
  const durationDays = typeof rawDays === 'number' && Number.isInteger(rawDays)
    && rawDays >= 1 && rawDays <= 365 ? rawDays : null;
  return destination !== null || durationDays !== null ? { destination, durationDays } : null;
}
