// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AuthSession } from '../auth/authApi';
import { journeyMessages, localizeRecommendationCode } from '../i18n/journeyMessages';
import { createTripRequirements } from './tripIntake';
import { TravelerJourney } from './TravelerJourney';

const session: AuthSession = {
  user: { user_id: 'traveler-1', phone_e164: '+989120000001', phone_verified: true },
  csrf_token: 'csrf-memory',
};
let root: Root;
let host: HTMLDivElement;

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}
async function settle() { await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); }); }

function tripRecord(requestText: string, requirements: ReturnType<typeof createTripRequirements> & object) {
  if (requirements.kind === 'invalid') throw new Error('Test request must be valid');
  const extracted = requirements.requirements;
  return {
    trip_id: 'trip-1', conversation_id: 'conversation-1', version: 1, locale: 'en-US' as const,
    original_request: requestText, extracted_requirements: extracted, confirmed_requirements: {},
    destination_ids: [], duration_days: extracted.durationDays.value, traveler_count: null, budget_amount_original: null,
    budget_currency_iso: null, budget_unit: null, trip_status: 'draft', created_at: '2026-11-08T00:00:00Z',
    updated_at: '2026-11-08T00:00:00Z', latest_recommendation_request_id: null, latest_itinerary_id: null,
  };
}

beforeEach(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  host = document.createElement('div'); document.body.append(host); root = createRoot(host);
});
afterEach(() => { act(() => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('persisted traveler journey', () => {
  it('persists the exact signed-in request, then shows an honest empty result without creating an itinerary', async () => {
    const requestText = 'Plan a 3-day trip to Shiraz';
    const parsed = createTripRequirements({ requestText, locale: 'en-US' });
    expect(parsed.kind).not.toBe('invalid');
    if (parsed.kind === 'invalid') return;
    const trip = tripRecord(requestText, parsed);
    const conversation = {
      conversation_id: 'conversation-1', locale: 'en-US', version: 1,
      started_at: trip.created_at, updated_at: trip.updated_at, last_message_at: trip.updated_at,
      trips: [trip], messages: [{ message_id: 'message-1', trip_id: trip.trip_id, role: 'user', content: requestText, created_at: trip.created_at }],
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const method = init?.method ?? 'GET';
      if (url.endsWith('/conversations?limit=50')) return response({ items: [], next_cursor: null });
      if (url === '/api/v1/catalog/destinations') return response({ status: 'available', complete: true, count: 0, items: [] });
      if (url === '/api/v1/conversations' && method === 'POST') return response({ conversation, trip, initial_message: conversation.messages[0] }, 201);
      if (url === `/api/v1/trips/${trip.trip_id}` && method === 'PATCH') return response({ ...trip, version: 2, confirmed_requirements: { confirmation_source: 'traveler_reviewed' } });
      if (url === `/api/v1/trips/${trip.trip_id}/recommendations` && method === 'POST') return response({
        recommendation_request_id: 'recommendation-request-1', status: 'empty', reason_code: 'no_eligible_candidates',
        unresolved_fields: [], algorithm_version: 'deterministic-v1', trip_version: 2, items: [],
      });
      if (url === `/api/v1/trips/${trip.trip_id}` && method === 'GET') return response({ ...trip, version: 2 });
      throw new Error(`Unexpected request: ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => root.render(<TravelerJourney locale="en-US" session={session} online requirements={parsed.requirements}
      onSessionExpired={() => undefined} onRestoreRequest={() => undefined} onStartNewDraft={() => undefined} />));
    await settle();

    await act(async () => { host.querySelector<HTMLButtonElement>('.journey-action')!.click(); }); await settle();
    const createCall = fetchMock.mock.calls.find(call => String(call[0]) === '/api/v1/conversations')!;
    const createInit = createCall[1] as RequestInit;
    const submitted = JSON.parse(String(createInit.body));
    expect(submitted.request_text).toBe(requestText);
    expect(submitted.locale).toBe('en-US');
    expect(submitted.idempotency_key).toEqual(expect.any(String));
    expect(createInit.credentials).toBe('same-origin');
    expect(createInit.cache).toBe('no-store');
    expect((createInit.headers as Headers).get('X-CSRF-Token')).toBe('csrf-memory');
    expect(host.textContent).toContain(requestText);

    const confirm = [...host.querySelectorAll('button')].find(button => button.textContent === journeyMessages['en-US'].confirmProfile)!;
    await act(async () => { confirm.click(); }); await settle();
    const recommendations = [...host.querySelectorAll('button')].find(button => button.textContent === journeyMessages['en-US'].findRecommendations)!;
    await act(async () => { recommendations.click(); }); await settle();
    expect(host.textContent).toContain(journeyMessages['en-US'].recommendationEmpty);
    expect(host.querySelector('button')?.textContent).not.toBe(journeyMessages['en-US'].createItinerary);
    expect(fetchMock.mock.calls.some(call => String(call[0]).endsWith('/itineraries'))).toBe(false);
  });

  it('renders the privacy notice in all supported directions/locales and keeps anonymous intake transient', async () => {
    for (const locale of ['fa-IR', 'en-US', 'ar'] as const) {
      await act(async () => root.render(<TravelerJourney locale={locale} session={null} online requirements={null}
        onSessionExpired={() => undefined} onRestoreRequest={() => undefined} onStartNewDraft={() => undefined} />));
      const workspace = host.querySelector<HTMLElement>('.traveler-workspace')!;
      expect(workspace.dir).toBe(locale === 'en-US' ? 'ltr' : 'rtl');
      expect(workspace.textContent).toContain(journeyMessages[locale].privacyNotice);
      expect(workspace.textContent).toContain(journeyMessages[locale].signInToSave);
    }
  });

  it('localizes recommendation explanation and warning codes without exposing IDs or unlocalized tag terms', () => {
    for (const locale of ['fa-IR', 'en-US', 'ar'] as const) {
      expect(journeyMessages[locale].explanationMatch).not.toBe(journeyMessages[locale].explanationArea);
      const destinationMatch = localizeRecommendationCode(locale, 'destination:7421');
      const interestMatch = localizeRecommendationCode(locale, 'interest:historic_gardens');
      expect(destinationMatch).not.toContain('7421');
      expect(interestMatch).not.toContain('historic_gardens');
      for (const warning of [
        'ranking_is_structured_match_not_quality_score',
        'interest_not_matched_in_published_tags',
        'tag_language_unspecified_exact_match_only',
        'published_tag_projection_unavailable',
        'source_freshness_unknown',
      ]) {
        expect(localizeRecommendationCode(locale, warning)).not.toBe(warning);
      }
      for (const field of [
        'budget', 'travel_dates', 'traveler_count', 'access', 'accessibility', 'mobility', 'surface',
        'activity', 'activity_difficulty', 'difficulty', 'season', 'radius', 'time_window', 'transport',
        'travel_style', 'accommodation', 'party_composition', 'hard_constraint', 'destination_resolution',
        'trip_profile', 'duration_days', 'origin', 'constraints',
      ]) {
        expect(localizeRecommendationCode(locale, `field:${field}`)).not.toBe(journeyMessages[locale].unknown);
      }
      if (locale === 'fa-IR') {
        expect(localizeRecommendationCode(locale, 'field:accessibility')).toBe('دسترس‌پذیری');
      }
      expect(localizeRecommendationCode(locale, 'budget_unverifiable')).not.toBe('budget_unverifiable');
    }
  });

  it('requires an explicit field choice and a separate advisory acknowledgement before saving consent', async () => {
    const requestText = 'Plan a 3-day trip to Shiraz with a budget of 100000 toman; I prefer paved paths';
    const parsed = createTripRequirements({ requestText, locale: 'en-US' });
    expect(parsed.kind).not.toBe('invalid');
    if (parsed.kind === 'invalid') return;
    const trip = tripRecord(requestText, parsed);
    const conversation = {
      conversation_id: 'conversation-1', locale: 'en-US', version: 1,
      started_at: trip.created_at, updated_at: trip.updated_at, last_message_at: trip.updated_at,
      trips: [trip], messages: [],
    };
    const savedTrip = {
      ...trip, version: 2,
      confirmed_requirements: {
        confirmation_source: 'traveler_reviewed',
        requirement_consent: {
          contract_version: 'recommendation-consent-v1', profile_version: 2,
          field_decisions: { budget: 'advisory', soft_preference: 'advisory' },
          advisory_acknowledged_fields: ['budget', 'soft_preference'],
        },
      },
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const method = init?.method ?? 'GET';
      if (url.endsWith('/conversations?limit=50')) return response({ items: [], next_cursor: null });
      if (url === '/api/v1/catalog/destinations') return response({ status: 'available', complete: true, count: 0, items: [] });
      if (url === '/api/v1/conversations' && method === 'POST') return response({ conversation, trip, initial_message: null }, 201);
      if (url === `/api/v1/trips/${trip.trip_id}` && method === 'PATCH') return response(savedTrip);
      if (url === `/api/v1/trips/${trip.trip_id}/recommendations` && method === 'POST') return response({
        recommendation_request_id: 'recommendation-request-1', status: 'empty', reason_code: 'no_eligible_candidates',
        unresolved_fields: [], waived_fields: ['budget', 'soft_preference'], not_evaluated_fields: ['budget', 'soft_preference'],
        requirement_assessments: [
          { field: 'budget', decision: 'advisory', status: 'not_evaluated', reason_code: 'budget_unverifiable' },
          { field: 'soft_preference', decision: 'advisory', status: 'not_evaluated', reason_code: 'preference_unverifiable' },
        ],
        algorithm_version: 'structured-catalogue-ranking-v3', retrieval_version: 'approved-structured-catalogue-v2',
        trip_version: 2, items: [],
      });
      if (url === `/api/v1/trips/${trip.trip_id}` && method === 'GET') return response(savedTrip);
      throw new Error(`Unexpected request: ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => root.render(<TravelerJourney locale="en-US" session={session} online requirements={parsed.requirements}
      onSessionExpired={() => undefined} onRestoreRequest={() => undefined} onStartNewDraft={() => undefined} />));
    await settle();
    await act(async () => { host.querySelector<HTMLButtonElement>('.journey-action')!.click(); }); await settle();

    const confirm = [...host.querySelectorAll('button')].find(button => button.textContent === journeyMessages['en-US'].confirmProfile)!;
    const must = host.querySelector<HTMLInputElement>('#requirement-consent-budget-must')!;
    const advisory = host.querySelector<HTMLInputElement>('#requirement-consent-budget-advisory')!;
    const softPreferenceAdvisory = host.querySelector<HTMLInputElement>('#requirement-consent-soft_preference-advisory')!;
    expect(must.checked).toBe(false);
    expect(advisory.checked).toBe(false);
    expect(softPreferenceAdvisory.checked).toBe(false);
    expect(host.querySelector('.soft-preference-value')?.textContent).toContain('paved paths');
    expect(confirm.disabled).toBe(true);
    await act(async () => { advisory.click(); }); await settle();
    expect(host.textContent).toContain(journeyMessages['en-US'].requirementAdvisoryWarning);
    expect(confirm.disabled).toBe(true);
    await act(async () => { host.querySelector<HTMLInputElement>('#requirement-consent-budget-ack')!.click(); }); await settle();
    expect(confirm.disabled).toBe(true);
    await act(async () => { softPreferenceAdvisory.click(); }); await settle();
    await act(async () => { host.querySelector<HTMLInputElement>('#requirement-consent-soft_preference-ack')!.click(); }); await settle();
    expect(confirm.disabled).toBe(false);
    await act(async () => { confirm.click(); }); await settle();
    const patchCall = fetchMock.mock.calls.find(call => String(call[0]) === `/api/v1/trips/${trip.trip_id}` && (call[1] as RequestInit).method === 'PATCH')!;
    const patchBody = JSON.parse(String((patchCall[1] as RequestInit).body));
    expect(patchBody.requirement_consent).toEqual({
      contract_version: 'recommendation-consent-v1',
      field_decisions: { budget: 'advisory', soft_preference: 'advisory' },
      advisory_acknowledged_fields: ['budget', 'soft_preference'],
    });
    expect(patchBody.confirmed_requirements.soft_preferences).toEqual(['paved paths']);
    await act(async () => {
      [...host.querySelectorAll('button')].find(button => button.textContent === journeyMessages['en-US'].findRecommendations)!.click();
    }); await settle();
    expect(host.textContent).toContain(journeyMessages['en-US'].requirementNotEvaluatedTitle);
    expect(host.textContent).toContain(journeyMessages['en-US'].requirementAdvisoryWarning);
    expect(host.textContent).toContain(journeyMessages['en-US'].recommendationEmpty);
  });

  it('does not restore a confirmed profile when its server-bound consent record is missing', async () => {
    const requestText = 'Plan a 3-day trip to Shiraz';
    const parsed = createTripRequirements({ requestText, locale: 'en-US' });
    expect(parsed.kind).not.toBe('invalid');
    if (parsed.kind === 'invalid') return;
    const trip = {
      ...tripRecord(requestText, parsed),
      confirmed_requirements: { confirmation_source: 'traveler_reviewed' },
    };
    const conversation = {
      conversation_id: 'conversation-1', locale: 'en-US', version: 1,
      started_at: trip.created_at, updated_at: trip.updated_at, last_message_at: trip.updated_at,
      trips: [trip], messages: [],
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/conversations?limit=50')) return response({ items: [conversation], next_cursor: null });
      if (url === '/api/v1/conversations/conversation-1') return response(conversation);
      if (url === `/api/v1/trips/${trip.trip_id}`) return response(trip);
      if (url === '/api/v1/catalog/destinations') return response({ status: 'available', complete: true, count: 0, items: [] });
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => root.render(<TravelerJourney locale="en-US" session={session} online requirements={null}
      onSessionExpired={() => undefined} onRestoreRequest={() => undefined} onStartNewDraft={() => undefined} />));
    await settle();
    const openTrip = [...host.querySelectorAll('button')].find(button => button.textContent === requestText)!;
    await act(async () => { openTrip.click(); }); await settle();

    expect(host.querySelector('.recommendation-controls')).toBeNull();
    expect(host.textContent).toContain(journeyMessages['en-US'].profileTitle);
    expect(host.textContent).not.toContain(journeyMessages['en-US'].findRecommendations);
  });

  it('renders needs-confirmation guidance when the backend reason code is null', async () => {
    const requestText = 'Plan a 3-day trip to Shiraz';
    const parsed = createTripRequirements({ requestText, locale: 'en-US' });
    expect(parsed.kind).not.toBe('invalid');
    if (parsed.kind === 'invalid') return;
    const baseTrip = tripRecord(requestText, parsed);
    const trip = {
      ...baseTrip, version: 2, latest_recommendation_request_id: 'recommendation-request-1',
      confirmed_requirements: {
        confirmation_source: 'traveler_reviewed',
        requirement_consent: { contract_version: 'recommendation-consent-v1', profile_version: 2, field_decisions: {}, advisory_acknowledged_fields: [] },
      },
    };
    const conversation = {
      conversation_id: 'conversation-1', locale: 'en-US', version: 1,
      started_at: trip.created_at, updated_at: trip.updated_at, last_message_at: trip.updated_at,
      trips: [trip], messages: [],
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/conversations?limit=50')) return response({ items: [conversation], next_cursor: null });
      if (url === '/api/v1/conversations/conversation-1') return response(conversation);
      if (url === `/api/v1/trips/${trip.trip_id}`) return response(trip);
      if (url === `/api/v1/trips/${trip.trip_id}/recommendations`) return response({
        recommendation_request_id: 'recommendation-request-1', status: 'needs_confirmation', reason_code: null,
        unresolved_fields: ['budget'], waived_fields: [], not_evaluated_fields: [], requirement_assessments: [],
        algorithm_version: 'structured-catalogue-ranking-v3', retrieval_version: 'approved-structured-catalogue-v2',
        trip_version: 2, items: [],
      });
      if (url === '/api/v1/catalog/destinations') return response({ status: 'available', complete: true, count: 0, items: [] });
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => root.render(<TravelerJourney locale="en-US" session={session} online requirements={null}
      onSessionExpired={() => undefined} onRestoreRequest={() => undefined} onStartNewDraft={() => undefined} />));
    await settle();
    const openTrip = [...host.querySelectorAll('button')].find(button => button.textContent === requestText)!;
    await act(async () => { openTrip.click(); }); await settle();

    expect(host.textContent).toContain(journeyMessages['en-US'].recommendationClarify);
    expect(host.textContent).toContain(localizeRecommendationCode('en-US', 'field:budget'));
  });

  it('keeps unclassified hard constraints mandatory and offers a follow-up clarification path', async () => {
    const requestText = 'I need wheelchair access for a 3-day trip to Shiraz';
    const parsed = createTripRequirements({ requestText, locale: 'en-US' });
    expect(parsed.kind).not.toBe('invalid');
    if (parsed.kind === 'invalid') return;
    const trip = tripRecord(requestText, parsed);
    const conversation = {
      conversation_id: 'conversation-1', locale: 'en-US', version: 1,
      started_at: trip.created_at, updated_at: trip.updated_at, last_message_at: trip.updated_at,
      trips: [trip], messages: [],
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const method = init?.method ?? 'GET';
      if (url.endsWith('/conversations?limit=50')) return response({ items: [], next_cursor: null });
      if (url === '/api/v1/catalog/destinations') return response({ status: 'available', complete: true, count: 0, items: [] });
      if (url === '/api/v1/conversations' && method === 'POST') return response({ conversation, trip, initial_message: null }, 201);
      throw new Error(`Unexpected request: ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => root.render(<TravelerJourney locale="en-US" session={session} online requirements={parsed.requirements}
      onSessionExpired={() => undefined} onRestoreRequest={() => undefined} onStartNewDraft={() => undefined} />));
    await settle();
    await act(async () => { host.querySelector<HTMLButtonElement>('.journey-action')!.click(); }); await settle();

    expect(host.textContent).toContain(journeyMessages['en-US'].requirementUnclassifiedMandatory);
    expect(host.textContent).toContain(journeyMessages['en-US'].requirementClarifyByEditing);
    expect(host.textContent).toContain(journeyMessages['en-US'].requirementAccessibilityMandatory);
    expect(host.textContent).toContain(journeyMessages['en-US'].wheelchair_access);
    expect(host.querySelector('#requirement-consent-accessibility')).toBeNull();
    expect(host.querySelector('#requirement-consent-hard_constraint')).toBeNull();
    expect(host.querySelector('.requirement-unclassified button')).not.toBeNull();
  });

  it('creates a ten-day itinerary by default and renders every day with honest partial coverage', async () => {
    const requestText = 'Plan a 10-day trip to Shiraz';
    const parsed = createTripRequirements({ requestText, locale: 'en-US' });
    expect(parsed.kind).not.toBe('invalid');
    if (parsed.kind === 'invalid') return;
    const trip = tripRecord(requestText, parsed);
    const conversation = {
      conversation_id: 'conversation-1', locale: 'en-US', version: 1,
      started_at: trip.created_at, updated_at: trip.updated_at, last_message_at: trip.updated_at,
      trips: [trip], messages: [],
    };
    const recommendation = {
      recommendation_id: 'recommendation-1', destination_id: '7421', rank: 1, final_score: 1,
      matched_requirements: ['destination:7421'], unknown_fields: ['opening_hours'], warnings: [],
      explanation_key: 'explicit_destination_match', score_components: [], evidence: [{
        source_id: 1, source_name: 'Approved source', source_url: 'https://example.test/source', source_role: 'official',
        evidence_note: null, retrieved_at: null, valid_from: null, valid_until: null, reliability_score: null,
      }], canonical_name: 'Shiraz Garden', localized_names: { 'en-US': 'Shiraz Garden' },
      city_name: 'Shiraz', province_name: 'Fars', destination_type: 'attraction',
    };
    const itinerary = {
      itinerary_id: 'itinerary-1', trip_id: trip.trip_id, revision: 1, version: 1, day_count: 10,
      status: 'partial', unplanned_days: [2, 3, 4, 5, 6, 7, 8, 9, 10],
      title_by_locale: { 'en-US': 'Editable day plan' },
      stops: [{ recommendation_id: 'recommendation-1', day_number: 1, stop_order: 1, notes_by_locale: {},
        destination_id: '7421', canonical_name: 'Shiraz Garden', localized_names: { 'en-US': 'Shiraz Garden' } }],
      recommendation_request_id: 'recommendation-request-1', updated_at: '2026-11-08T00:00:00Z',
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const method = init?.method ?? 'GET';
      if (url.endsWith('/conversations?limit=50')) return response({ items: [], next_cursor: null });
      if (url === '/api/v1/catalog/destinations') return response({ status: 'available', complete: true, count: 0, items: [] });
      if (url === '/api/v1/conversations' && method === 'POST') return response({ conversation, trip, initial_message: null }, 201);
      if (url === `/api/v1/trips/${trip.trip_id}` && method === 'PATCH') return response({ ...trip, version: 2, confirmed_requirements: { duration_days: 10 } });
      if (url === `/api/v1/trips/${trip.trip_id}/recommendations` && method === 'POST') return response({
        recommendation_request_id: 'recommendation-request-1', status: 'available', reason_code: 'available',
        unresolved_fields: [], algorithm_version: 'structured-catalogue-ranking-v2', trip_version: 2, items: [recommendation],
      });
      if (url === `/api/v1/trips/${trip.trip_id}` && method === 'GET') return response({ ...trip, version: 2, latest_itinerary_id: itinerary.itinerary_id });
      if (url === `/api/v1/trips/${trip.trip_id}/itineraries` && method === 'POST') return response(itinerary, 201);
      throw new Error(`Unexpected request: ${method} ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    await act(async () => root.render(<TravelerJourney locale="en-US" session={session} online requirements={parsed.requirements}
      onSessionExpired={() => undefined} onRestoreRequest={() => undefined} onStartNewDraft={() => undefined} />));
    await settle();
    await act(async () => { host.querySelector<HTMLButtonElement>('.journey-action')!.click(); }); await settle();
    const confirm = [...host.querySelectorAll('button')].find(button => button.textContent === journeyMessages['en-US'].confirmProfile)!;
    await act(async () => { confirm.click(); }); await settle();
    const recommendations = [...host.querySelectorAll('button')].find(button => button.textContent === journeyMessages['en-US'].findRecommendations)!;
    await act(async () => { recommendations.click(); }); await settle();

    const daysInput = host.querySelector<HTMLInputElement>('#journey-day-count')!;
    expect(daysInput.value).toBe('10');
    const create = [...host.querySelectorAll('button')].find(button => button.textContent === journeyMessages['en-US'].createItinerary)!;
    await act(async () => { create.click(); }); await settle();
    const createCall = fetchMock.mock.calls.find(call => String(call[0]) === `/api/v1/trips/${trip.trip_id}/itineraries`)!;
    expect(JSON.parse(String((createCall[1] as RequestInit).body)).day_count).toBe(10);
    expect(host.textContent).toContain(journeyMessages['en-US'].itineraryPartial);
    expect(host.textContent).toContain(journeyMessages['en-US'].unplannedDay);
    expect(host.querySelectorAll('.itinerary-day')).toHaveLength(10);
    expect(host.querySelectorAll('.unplanned-day')).toHaveLength(9);
  });
});
