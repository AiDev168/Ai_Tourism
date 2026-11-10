import type { Locale } from '../i18n/messages';
import type { TripRequirements } from './tripIntake';

export type ConversationMessage = {
  message_id: string;
  trip_id: string | null;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  created_at: string;
  /** Advisory hints persisted with an AI reply, never traveler-confirmed. */
  candidate_requirements?: Record<string, string | number | null>;
};

export type TripRecord = {
  trip_id: string;
  conversation_id: string;
  version: number;
  locale: Locale;
  original_request: string;
  extracted_requirements: TripRequirements | Record<string, unknown>;
  confirmed_requirements: Record<string, unknown>;
  destination_ids: string[];
  duration_days: number | null;
  traveler_count: number | null;
  budget_amount_original: string | number | null;
  budget_currency_iso: string | null;
  budget_unit: 'rial' | 'toman' | null;
  trip_status: string;
  created_at: string;
  updated_at: string;
  latest_recommendation_request_id?: string | null;
  latest_itinerary_id?: string | null;
};

export type RequirementConsentDecision = 'must_have' | 'advisory';
export type RequirementFieldCode = 'budget' | 'travel_dates' | 'traveler_count' | 'origin' | 'soft_preference';
export type RequirementConsent = {
  contract_version: 'recommendation-consent-v1';
  field_decisions: Partial<Record<RequirementFieldCode, RequirementConsentDecision>>;
  advisory_acknowledged_fields: RequirementFieldCode[];
};
export type RequirementAssessment = {
  field: string;
  decision: RequirementConsentDecision | null;
  status: 'satisfied' | 'not_evaluated' | 'unresolved';
  reason_code: string | null;
};

export type ConversationRecord = {
  conversation_id: string;
  locale: Locale;
  version: number;
  started_at: string;
  updated_at: string;
  last_message_at: string | null;
  trips: TripRecord[];
  messages: ConversationMessage[];
};

export type ConversationSummary = Omit<ConversationRecord, 'messages'> & { messages?: ConversationMessage[] };

export type EvidenceSource = {
  source_id: number;
  source_name: string;
  source_url: string;
  source_role: string;
  evidence_note: string | null;
  retrieved_at: string | null;
  valid_from: string | null;
  valid_until: string | null;
  reliability_score: number | null;
};

export type RetrievalCitationSource = {
  source_id: string;
  source_name: string;
  source_url: string;
  source_role: string;
  license: string | null;
  retrieved_at: string | null;
  valid_from: string | null;
  valid_until: string | null;
};

export type RetrievalEvidenceCitation = {
  evidence_id: string;
  canonical_entity_key: string;
  destination_id: number;
  document_id: string;
  claim_key: string;
  content_hash: string;
  locale: Locale;
  corpus: 'spatial_destinations';
  text: string;
  sources: RetrievalCitationSource[];
};

export type RecommendationItem = {
  recommendation_id: string;
  destination_id: string;
  rank: number;
  final_score: number;
  matched_requirements: string[];
  unknown_fields: string[];
  warnings: string[];
  explanation_key: 'explicit_destination_match' | 'published_area_candidate';
  score_components: RankingComponent[];
  evidence: EvidenceSource[];
  /** Server-mapped claim evidence; unknown JSON is parsed before rendering. */
  retrieval_evidence?: unknown;
  canonical_name: string;
  localized_names: Partial<Record<Locale, string | null>>;
  city_name: string | null;
  province_name: string;
  destination_type: string;
};

export type RankingComponent = {
  component_key: 'destination_scope' | 'exact_interest_tag_match';
  raw_score: number;
  weight: number;
  weighted_score: number;
  matched_terms: string[];
};

export type RecommendationResult = {
  recommendation_request_id: string;
  status: 'available' | 'empty' | 'needs_confirmation';
  reason_code: string | null;
  /** Stable requirement field codes the catalogue cannot assess. */
  unresolved_fields: string[];
  requirement_assessments: RequirementAssessment[];
  waived_fields: string[];
  not_evaluated_fields: string[];
  algorithm_version: string;
  retrieval_version: string;
  trip_version: number;
  items: RecommendationItem[];
};

function isNonEmptyString(value: unknown, maxLength: number): value is string {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= maxLength;
}

function isNullableTimestamp(value: unknown): value is string | null {
  return value === null || (typeof value === 'string' && Number.isFinite(Date.parse(value)));
}

function parseRetrievalCitationSource(value: unknown): RetrievalCitationSource | null {
  if (typeof value !== 'object' || value === null) return null;
  const source = value as Record<string, unknown>;
  if (!isNonEmptyString(source.source_id, 240) || !/^\d+$/.test(source.source_id)
    || !isNonEmptyString(source.source_name, 500)
    || !isNonEmptyString(source.source_url, 2048)
    || !isNonEmptyString(source.source_role, 64)
    || !(source.license === null || isNonEmptyString(source.license, 500))
    || !isNullableTimestamp(source.retrieved_at)
    || !isNullableTimestamp(source.valid_from)
    || !isNullableTimestamp(source.valid_until)) return null;

  try {
    const url = new URL(source.source_url);
    if (url.protocol !== 'https:' || url.username || url.password) return null;
  } catch {
    return null;
  }
  if (source.valid_from && source.valid_until
    && Date.parse(source.valid_from) > Date.parse(source.valid_until)) return null;
  return {
    source_id: source.source_id,
    source_name: source.source_name,
    source_url: source.source_url,
    source_role: source.source_role,
    license: source.license,
    retrieved_at: source.retrieved_at,
    valid_from: source.valid_from,
    valid_until: source.valid_until,
  };
}

/** Parse only server-mapped, spatial citations belonging to this exact card. */
export function parseRetrievalEvidence(
  value: unknown,
  destinationId: string,
  locale: Locale,
): RetrievalEvidenceCitation[] {
  if (!Array.isArray(value) || value.length === 0 || value.length > 20) return [];
  const expectedId = Number(destinationId);
  if (!Number.isSafeInteger(expectedId) || expectedId < 1 || String(expectedId) !== destinationId) return [];
  const parsed: RetrievalEvidenceCitation[] = [];
  for (const raw of value) {
    if (typeof raw !== 'object' || raw === null) return [];
    const item = raw as Record<string, unknown>;
    if (!isNonEmptyString(item.evidence_id, 240)
      || typeof item.canonical_entity_key !== 'string'
      || item.canonical_entity_key !== item.canonical_entity_key.trim()
      || !isNonEmptyString(item.canonical_entity_key, 240)
      || item.destination_id !== expectedId
      || !isNonEmptyString(item.document_id, 240)
      || !isNonEmptyString(item.claim_key, 240)
      || typeof item.content_hash !== 'string' || !/^[a-f0-9]{64}$/.test(item.content_hash)
      || item.locale !== locale || item.corpus !== 'spatial_destinations'
      || !isNonEmptyString(item.text, 8_000)
      || !Array.isArray(item.sources) || item.sources.length === 0 || item.sources.length > 32) return [];

    const sources = item.sources.map(parseRetrievalCitationSource);
    if (sources.some(source => source === null)) return [];
    const resolvedSources = sources as RetrievalCitationSource[];
    if (new Set(resolvedSources.map(source => source.source_id)).size !== resolvedSources.length) return [];
    parsed.push({
      evidence_id: item.evidence_id,
      canonical_entity_key: item.canonical_entity_key,
      destination_id: expectedId,
      document_id: item.document_id,
      claim_key: item.claim_key,
      content_hash: item.content_hash,
      locale,
      corpus: 'spatial_destinations',
      text: item.text,
      sources: resolvedSources,
    });
  }
  if (new Set(parsed.map(item => item.evidence_id)).size !== parsed.length) return [];
  return parsed;
}

export type ItineraryStop = {
  itinerary_stop_id?: string;
  recommendation_id: string;
  day_number: number;
  stop_order: number;
  notes_by_locale: Partial<Record<Locale, string>>;
  destination_id?: string;
  name?: string;
  canonical_name?: string;
  localized_names?: Partial<Record<Locale, string | null>>;
  city_name?: string | null;
  province_name?: string;
};

export type ItineraryRecord = {
  itinerary_id: string;
  trip_id: string;
  revision: number;
  version: number;
  /** Requested days; each day is rendered even when it has no eligible stop. */
  day_count: number;
  status: 'complete' | 'partial';
  /** Server-derived day numbers without any evidenced itinerary stop. */
  unplanned_days: number[];
  warning_codes?: string[];
  title_by_locale: Partial<Record<Locale, string>>;
  stops: ItineraryStop[];
  recommendation_request_id: string;
  updated_at: string;
};

export class TravelerApiError extends Error {
  constructor(readonly code: string, readonly status: number) {
    super(code);
    this.name = 'TravelerApiError';
  }
}

async function request<T>(path: string, csrfToken: string | undefined, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body) headers.set('Content-Type', 'application/json');
  if (csrfToken && init?.method && init.method !== 'GET') headers.set('X-CSRF-Token', csrfToken);
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers,
    credentials: 'same-origin',
    cache: 'no-store',
  });
  if (!response.ok) {
    let code = 'request_failed';
    try {
      const body = await response.json() as { error?: { code?: string } };
      code = body.error?.code ?? code;
    } catch { /* Keep a safe generic error if the server body is malformed. */ }
    throw new TravelerApiError(code, response.status);
  }
  if (response.status === 204) return undefined as T;
  return await response.json() as T;
}

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const travelerApi = {
  createConversation: (csrf: string, body: {
    locale: Locale;
    request_text: string;
    extracted_requirements: TripRequirements;
    confirmed_requirements?: Record<string, unknown>;
    destination_ids?: string[];
    idempotency_key: string;
  }) => request<{ conversation: ConversationRecord; trip: TripRecord; initial_message: ConversationMessage }>(
    '/conversations', csrf, json('POST', body),
  ),
  createTripInConversation: (csrf: string, conversationId: string, body: {
    locale: Locale;
    request_text: string;
    extracted_requirements: TripRequirements;
    confirmed_requirements?: Record<string, unknown>;
    destination_ids?: string[];
    idempotency_key: string;
  }) => request<{ conversation: ConversationRecord; trip: TripRecord; initial_message: ConversationMessage }>(
    `/conversations/${encodeURIComponent(conversationId)}/trips`, csrf, json('POST', body),
  ),
  listConversations: (limit = 20, cursor?: string) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (cursor) params.set('cursor', cursor);
    return request<{ items: ConversationSummary[]; next_cursor: string | null }>(`/conversations?${params}`, undefined);
  },
  getConversation: (id: string) => request<ConversationRecord>(`/conversations/${encodeURIComponent(id)}`, undefined),
  appendMessage: (csrf: string, conversationId: string, body: {
    trip_id: string;
    content: string;
    extracted_requirements?: TripRequirements;
    idempotency_key: string;
    expected_version: number;
    replace_previous_request?: boolean;
  }) => request<{ conversation: ConversationRecord; trip: TripRecord; message: ConversationMessage }>(
    `/conversations/${encodeURIComponent(conversationId)}/messages`, csrf, json('POST', body),
  ),
  assistantTurn: (csrf: string, conversationId: string, body: {
    trip_id: string;
    content: string;
    idempotency_key: string;
    expected_version: number;
    remote_processing_consent: true;
    extracted_requirements?: TripRequirements;
  }) => request<{
    conversation: ConversationRecord;
    trip: TripRecord;
    message: ConversationMessage;
    candidate_requirements: Record<string, string | number | null>;
    clarification: string | null;
    replayed: boolean;
  }>(`/conversations/${encodeURIComponent(conversationId)}/assistant-turns`, csrf, json('POST', body)),
  confirmTripProfile: (csrf: string, tripId: string, body: {
    expected_version: number;
    confirmed_requirements: Record<string, unknown>;
    destination_ids: string[];
    requirement_consent: RequirementConsent;
  }) => request<TripRecord>(`/trips/${encodeURIComponent(tripId)}`, csrf, json('PATCH', body)),
  getTrip: (tripId: string) => request<TripRecord>(`/trips/${encodeURIComponent(tripId)}`, undefined),
  deleteTrip: (csrf: string, tripId: string) => request<void>(`/trips/${encodeURIComponent(tripId)}`, csrf, { method: 'DELETE' }),
  deleteConversation: (csrf: string, conversationId: string) => request<void>(`/conversations/${encodeURIComponent(conversationId)}`, csrf, { method: 'DELETE' }),
  recommend: (csrf: string, tripId: string, selected_destination_ids: string[]) => request<RecommendationResult>(
    `/trips/${encodeURIComponent(tripId)}/recommendations`, csrf, json('POST', { selected_destination_ids }),
  ),
  latestRecommendations: (tripId: string) => request<RecommendationResult>(`/trips/${encodeURIComponent(tripId)}/recommendations`, undefined),
  createItinerary: (csrf: string, tripId: string, body: {
    recommendation_request_id: string;
    day_count: number;
    locale: Locale;
  }) => request<ItineraryRecord>(`/trips/${encodeURIComponent(tripId)}/itineraries`, csrf, json('POST', body)),
  getItinerary: (itineraryId: string) => request<ItineraryRecord>(`/itineraries/${encodeURIComponent(itineraryId)}`, undefined),
  updateItinerary: (csrf: string, itineraryId: string, body: {
    expected_revision: number;
    title_by_locale: Partial<Record<Locale, string>>;
    stops: Array<{ recommendation_id: string; day_number: number; stop_order: number; notes_by_locale: Partial<Record<Locale, string>> }>;
  }) => request<ItineraryRecord>(`/itineraries/${encodeURIComponent(itineraryId)}`, csrf, json('PUT', body)),
  deleteAccount: (csrf: string) => request<void>('/auth/me', csrf, { method: 'DELETE' }),
};
