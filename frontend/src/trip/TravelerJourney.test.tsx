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
    destination_ids: [], duration_days: 3, traveler_count: null, budget_amount_original: null,
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
        algorithm_version: 'deterministic-v1', trip_version: 2, items: [],
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
    }
  });
});
