// @vitest-environment jsdom
import { act, useState } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AuthSession } from '../auth/authApi';
import { createTripRequirements, type TripRequirements } from './tripIntake';
import { TravelerJourney } from './TravelerJourney';

const session: AuthSession = {
  user: { user_id: 'traveler-clarification', phone_e164: '+989120000001', phone_verified: true },
  csrf_token: 'fixture-csrf',
};

function ok(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { 'Content-Type': 'application/json' },
  });
}

async function settle() {
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
}

let host: HTMLDivElement;
let root: Root;
beforeEach(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  host = document.createElement('div');
  document.body.append(host);
  root = createRoot(host);
});
afterEach(() => {
  act(() => root.unmount());
  host.remove();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('visible traveler-only clarification flow', () => {
  it('asks the missing destination, accepts a short answer and never automatically confirms it', async () => {
    const requestText = 'Plan a 3-day trip';
    const parsed = createTripRequirements({ requestText, locale: 'en-US' });
    if (parsed.kind === 'invalid') throw new Error('Invalid test request');
    const now = '2026-11-09T00:00:00Z';
    const initialTrip = {
      trip_id: 'trip-1', conversation_id: 'conversation-1', version: 1, locale: 'en-US' as const,
      original_request: requestText, extracted_requirements: parsed.requirements,
      confirmed_requirements: {}, destination_ids: [],
      duration_days: 3, traveler_count: null, budget_amount_original: null,
      budget_currency_iso: null, budget_unit: null, trip_status: 'draft',
      created_at: now, updated_at: now,
      latest_recommendation_request_id: null, latest_itinerary_id: null,
    };
    const firstMessage = { message_id: 'initial-message', trip_id: initialTrip.trip_id,
      role: 'user', content: requestText, created_at: now };
    const initialConversation = {
      conversation_id: 'conversation-1', locale: 'en-US', version: 1,
      started_at: now, updated_at: now, last_message_at: now,
      trips: [initialTrip], messages: [firstMessage],
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';
      if (url.endsWith('/conversations?limit=50')) return ok({ items: [], next_cursor: null });
      if (url === '/api/v1/catalog/destinations')
        return ok({ status: 'available', complete: true, count: 0, items: [] });
      if (url === '/api/v1/conversations' && method === 'POST')
        return ok({ conversation: initialConversation, trip: initialTrip, initial_message: firstMessage }, 201);
      if (url === '/api/v1/conversations/conversation-1/messages' && method === 'POST') {
        const body = JSON.parse(String(init?.body));
        const nextTrip = { ...initialTrip, version: 2,
          extracted_requirements: body.extracted_requirements, confirmed_requirements: {} };
        const message = { message_id: 'reply-message', trip_id: initialTrip.trip_id,
          role: 'user', content: body.content, created_at: now };
        return ok({ trip: nextTrip, message,
          conversation: { ...initialConversation, version: 2, trips: [nextTrip],
            messages: [firstMessage, message] } });
      }
      throw new Error('Unexpected network call: ' + method + ' ' + url);
    });
    vi.stubGlobal('fetch', fetchMock);
    function Harness() {
      const [requirements, setRequirements] = useState<TripRequirements | null>(parsed.requirements);
      return <TravelerJourney session={session} online locale="en-US" requirements={requirements}
        onSessionExpired={() => undefined} onRestoreRequest={(_raw, updated) => setRequirements(updated)}
        onStartNewDraft={() => setRequirements(null)} />;
    }
    await act(async () => root.render(<Harness />));
    await settle();
    await act(async () => {
      host.querySelector<HTMLButtonElement>('.journey-action')!.click();
    });
    await settle();
    expect(host.querySelector('.traveler-clarification')?.textContent).toContain(
      'Which city or destination',
    );

    const textArea = host.querySelector<HTMLTextAreaElement>('#trip-follow-up')!;
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
      setter?.call(textArea, 'Shiraz');
      textArea.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await settle();
    const appendButton = [...host.querySelectorAll('button')].find(
      element => element.textContent?.trim() === 'Add to conversation',
    );
    expect(appendButton).toBeDefined();
    await act(async () => appendButton!.click());
    await settle();

    const appendCall = fetchMock.mock.calls.find(call =>
      String(call[0]).endsWith('/conversation-1/messages'));
    expect(appendCall).toBeDefined();
    const submitted = JSON.parse(String(appendCall![1]?.body));
    expect(submitted.content).toBe('Shiraz');
    expect(submitted.extracted_requirements.destinations.value).toEqual(['Shiraz']);
    expect(host.querySelector<HTMLInputElement>('#profile-destination-0')?.value).toBe('Shiraz');
    expect(host.querySelector('.traveler-clarification')).toBeNull();
    expect(fetchMock.mock.calls.some(call => String(call[0]).endsWith('/assistant-turns'))).toBe(false);
    expect(fetchMock.mock.calls.some(call => call[1]?.method === 'PATCH')).toBe(false);
  });
});
