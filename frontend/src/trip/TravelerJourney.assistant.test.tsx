// @vitest-environment jsdom
import { act, useState } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AuthSession } from '../auth/authApi';
import { createTripRequirements, type TripRequirements } from './tripIntake';
import { TravelerJourney } from './TravelerJourney';

const session: AuthSession = {
  user: { user_id: 'traveler-1', phone_e164: '+989120000001', phone_verified: true },
  csrf_token: 'test-csrf',
};
let root: Root;
let host: HTMLDivElement;
const reply = (value: unknown) => new Response(JSON.stringify(value), {
  status: 200, headers: { 'Content-Type': 'application/json' },
});
async function settle() { await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); }); }
function clickLabel(label: string) {
  const button = [...host.querySelectorAll('button')].find(item => item.textContent?.trim() === label);
  if (!button) throw new Error('Missing button: ' + label);
  button.click();
}

beforeEach(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  host = document.createElement('div'); document.body.append(host); root = createRoot(host);
});
afterEach(() => { act(() => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('assistant suggestions and reviewed trip restoration', () => {
  it('restores confirmed edits, keeps AI advisory, then saves only after explicit profile confirmation', async () => {
    const requestText = 'Plan a 3-day trip to Shiraz';
    const parsed = createTripRequirements({ requestText, locale: 'en-US' });
    if (parsed.kind === 'invalid') throw new Error('Invalid fixture');
    const now = '2026-11-09T00:00:00Z';
    const trip = {
      trip_id: 'trip-1', conversation_id: 'conversation-1', version: 2, locale: 'en-US' as const,
      original_request: requestText, extracted_requirements: parsed.requirements,
      confirmed_requirements: {
        confirmation_source: 'traveler_reviewed', destinations: ['Yazd'], duration_days: 2,
        requirement_consent: { contract_version: 'recommendation-consent-v1', profile_version: 2,
          field_decisions: {}, advisory_acknowledged_fields: [] },
      },
      destination_ids: [], duration_days: 2, traveler_count: null, budget_amount_original: null,
      budget_currency_iso: null, budget_unit: null, trip_status: 'draft', created_at: now,
      updated_at: now, latest_recommendation_request_id: null, latest_itinerary_id: null,
    };
    const conversation = {
      conversation_id: 'conversation-1', locale: 'en-US', version: 1,
      started_at: now, updated_at: now, last_message_at: now, trips: [trip],
      messages: [
        { message_id: 'initial-1', trip_id: trip.trip_id, role: 'user',
          content: requestText, created_at: now },
        { message_id: 'saved-ai-1', trip_id: trip.trip_id, role: 'assistant',
          content: 'An earlier suggestion', created_at: now,
          candidate_requirements: { destination: 'Qeshm', duration_days: 2 } },
      ],
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const method = init?.method ?? 'GET';
      if (url.endsWith('/conversations?limit=50')) return reply({ items: [conversation], next_cursor: null });
      if (url === '/api/v1/catalog/destinations') return reply({ status: 'available', complete: true, count: 0, items: [] });
      if (url === '/api/v1/conversations/conversation-1') return reply(conversation);
      if (url === '/api/v1/trips/trip-1' && method === 'GET') return reply(trip);
      if (url === '/api/v1/conversations/conversation-1/assistant-turns' && method === 'POST') {
        return reply({ conversation: { ...conversation, version: 3 }, trip,
          message: { message_id: 'assistant-1', trip_id: trip.trip_id, role: 'assistant',
            content: 'Would you prefer Kashan?', created_at: now },
          candidate_requirements: { destination: 'Kashan', duration_days: 1 },
          clarification: null, replayed: false });
      }
      if (url === '/api/v1/trips/trip-1' && method === 'PATCH') {
        const body = JSON.parse(String(init?.body));
        return reply({ ...trip, version: 3, confirmed_requirements: body.confirmed_requirements });
      }
      throw new Error('Unexpected request: ' + method + ' ' + url);
    });
    vi.stubGlobal('fetch', fetchMock);
    function Harness() {
      const [requirements, setRequirements] = useState<TripRequirements | null>(null);
      return <TravelerJourney locale="en-US" session={session} online requirements={requirements}
        onSessionExpired={() => undefined} onRestoreRequest={(_text, value) => setRequirements(value)}
        onStartNewDraft={() => setRequirements(null)} />;
    }
    await act(async () => root.render(<Harness />)); await settle();
    await act(async () => clickLabel(requestText)); await settle();
    expect(host.querySelector<HTMLInputElement>('#profile-destination-0')?.value).toBe('Yazd');
    expect(host.querySelector<HTMLInputElement>('#profile-duration')?.value).toBe('2');

    // A previously saved AI hint can be reviewed without a second provider call.
    await act(async () => clickLabel('Review saved suggestion')); await settle();
    expect(host.textContent).toContain('Qeshm');
    expect(host.querySelector<HTMLInputElement>('#profile-destination-0')?.value).toBe('Yazd');
    await act(async () => clickLabel('Dismiss')); await settle();
    expect(fetchMock.mock.calls.some(call => String(call[0]).endsWith('/assistant-turns'))).toBe(false);

    await act(async () => { host.querySelector<HTMLInputElement>('#assistant-remote-consent')!.click(); });
    await act(async () => clickLabel('Ask travel assistant')); await settle();
    expect(host.textContent).toContain('Suggested destination');
    expect(host.textContent).toContain('Kashan');
    expect(host.querySelector<HTMLInputElement>('#profile-destination-0')?.value).toBe('Yazd');
    expect(fetchMock.mock.calls.filter(call => call[1]?.method === 'PATCH')).toHaveLength(0);

    await act(async () => clickLabel('Use in trip form')); await settle();
    expect(host.querySelector<HTMLInputElement>('#profile-destination-0')?.value).toBe('Kashan');
    expect(host.querySelector<HTMLInputElement>('#profile-duration')?.value).toBe('1');
    expect(fetchMock.mock.calls.filter(call => call[1]?.method === 'PATCH')).toHaveLength(0);
    await act(async () => clickLabel('Save trip details')); await settle();
    const saved = fetchMock.mock.calls.find(call => call[1]?.method === 'PATCH');
    expect(saved).toBeDefined();
    const body = JSON.parse(String(saved![1]?.body));
    expect(body.confirmed_requirements.destinations).toEqual(['Kashan']);
    expect(body.confirmed_requirements.duration_days).toBe(1);
  });
});
