import type { Locale } from '../i18n/messages';
import type { TripRequirements } from './tripIntake';

export type ConversationMessage = {
  message_id: string;
  trip_id: string | null;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  created_at: string;
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
