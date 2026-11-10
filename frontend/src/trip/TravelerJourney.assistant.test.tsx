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
  it('keeps a Persian 15-day request visible and separates saved traveler notes from consented remote AI', async () => {
    const requestText = 'برای ۱۵ روز به شیراز سفر می‌کنیم';
    const parsed = createTripRequirements({ requestText, locale: 'fa-IR' });
    if (parsed.kind !== 'ready') throw new Error('Invalid Persian 15-day fixture');
    const tripRequirements = parsed.requirements;
    expect(tripRequirements.durationDays.value).toBe(15);
    const now = '2026-11-09T00:00:00Z';
    const trip = {
      trip_id: 'trip-15', conversation_id: 'conversation-15', version: 1, locale: 'fa-IR' as const,
      original_request: requestText, extracted_requirements: parsed.requirements, confirmed_requirements: {},
      destination_ids: [], duration_days: 15, traveler_count: null, budget_amount_original: null,
      budget_currency_iso: null, budget_unit: null, trip_status: 'draft', created_at: now,
      updated_at: now, latest_recommendation_request_id: null, latest_itinerary_id: null,
    };
    const initialMessage = { message_id: 'initial-15', trip_id: trip.trip_id, role: 'user',
      content: requestText, created_at: now };
    let conversation = { conversation_id: 'conversation-15', locale: 'fa-IR' as const, version: 1,
      started_at: now, updated_at: now, last_message_at: now, trips: [trip], messages: [initialMessage] };
    let currentTrip = trip;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const method = init?.method ?? 'GET';
      if (url.endsWith('/conversations?limit=50')) return reply({ items: [], next_cursor: null });
      if (url === '/api/v1/catalog/destinations') return reply({ status: 'available', complete: true, count: 0, items: [] });
      if (url === '/api/v1/conversations' && method === 'POST') {
        return reply({ conversation, trip: currentTrip, initial_message: initialMessage });
      }
      if (url === '/api/v1/conversations/conversation-15/messages' && method === 'POST') {
        const body = JSON.parse(String(init?.body));
        const message = { message_id: 'local-note-15', trip_id: trip.trip_id, role: 'user', content: body.content, created_at: now };
        currentTrip = { ...currentTrip, version: 2, extracted_requirements: body.extracted_requirements };
        conversation = { ...conversation, version: 2, trips: [currentTrip], messages: [...conversation.messages, message] };
        return reply({ trip: currentTrip, conversation, message });
      }
      if (url === '/api/v1/conversations/conversation-15/assistant-turns' && method === 'POST') {
        const body = JSON.parse(String(init?.body));
        const message = { message_id: 'assistant-reply-15', trip_id: trip.trip_id, role: 'assistant',
          content: 'مدت سفر همان ۱۵ روز است؛ مقصد را خودتان مرور کنید.', created_at: now };
        conversation = { ...conversation, version: 3, messages: [...conversation.messages, message] };
        return reply({ conversation, trip: currentTrip, message,
          candidate_requirements: { destination: null, duration_days: 10 }, clarification: null, replayed: false,
          received_test_turn: body });
      }
      throw new Error('Unexpected request: ' + method + ' ' + url);
    });
    vi.stubGlobal('fetch', fetchMock);
    function Harness() {
      const [requirements, setRequirements] = useState<TripRequirements | null>(tripRequirements);
      return <TravelerJourney locale="fa-IR" session={session} online requirements={requirements}
        onSessionExpired={() => undefined} onRestoreRequest={(_text, value) => setRequirements(value)}
        onStartNewDraft={() => setRequirements(null)} />;
    }
    await act(async () => root.render(<Harness />)); await settle();
    await act(async () => host.querySelector<HTMLButtonElement>('.journey-action')!.click());
    await settle();

    expect(host.textContent).toContain(requestText);
    expect(host.textContent).toContain('مدت ثبت‌شدهٔ این سفر: ۱۵ روز.');
    expect(host.querySelector<HTMLInputElement>('#profile-duration')?.value).toBe('15');
    expect(host.querySelector<HTMLInputElement>('#assistant-remote-consent')?.checked).toBe(false);

    const firstSuggestion = host.querySelector<HTMLButtonElement>('.assistant-prompt-suggestions button');
    expect(firstSuggestion).toBeTruthy();
    await act(async () => firstSuggestion!.click()); await settle();
    expect(host.querySelector<HTMLTextAreaElement>('#trip-follow-up')?.value).toBe(firstSuggestion!.textContent);
    expect(fetchMock.mock.calls.some(call => String(call[0]).endsWith('/messages')
      || String(call[0]).endsWith('/assistant-turns'))).toBe(false);
    expect(host.querySelector<HTMLInputElement>('#profile-duration')?.value).toBe('15');

    const textarea = host.querySelector<HTMLTextAreaElement>('#trip-follow-up')!;
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
      setter?.call(textarea, 'ما چهار نفر هستیم');
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => clickLabel('ثبت پاسخ بدون هوش مصنوعی')); await settle();
    const localCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/messages'))!;
    const localPayload = JSON.parse(String(localCall[1]?.body));
    expect(localPayload.content).toBe('ما چهار نفر هستیم');
    expect(localPayload.extracted_requirements.durationDays.value).toBe(15);
    expect(fetchMock.mock.calls.some(call => String(call[0]).endsWith('/assistant-turns'))).toBe(false);
    expect(host.querySelector<HTMLInputElement>('#profile-duration')?.value).toBe('15');

    const remoteInput = host.querySelector<HTMLTextAreaElement>('#trip-follow-up')!;
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
      setter?.call(remoteInput, 'لطفاً یک سؤال تکمیلی بپرس');
      remoteInput.dispatchEvent(new Event('input', { bubbles: true }));
    });
    const remoteButton = [...host.querySelectorAll('button')].find(button => button.textContent?.trim() === 'پرسش از دستیار سفر')!;
    expect(remoteButton.disabled).toBe(true);
    await act(async () => host.querySelector<HTMLInputElement>('#assistant-remote-consent')!.click());
    expect(remoteButton.disabled).toBe(false);
    await act(async () => remoteButton.click()); await settle();
    const remoteCall = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/assistant-turns'))!;
    const remotePayload = JSON.parse(String(remoteCall[1]?.body));
    expect(remotePayload.remote_processing_consent).toBe(true);
    expect(remotePayload.content).toBe('لطفاً یک سؤال تکمیلی بپرس');
    expect(host.textContent).toContain('مدت ثبت‌شدهٔ این سفر: ۱۵ روز.');
    expect(host.querySelector<HTMLInputElement>('#profile-duration')?.value).toBe('15');
    expect(fetchMock.mock.calls.some(call => String(call[0]).endsWith('/trips/trip-15')
      && (call[1]?.method === 'PATCH' || call[1]?.method === 'PUT'))).toBe(false);
  });

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
          candidate_requirements: {
            destination: 'Kashan', duration_days: 1, origin: 'Tehran', traveler_count: 4,
            budget_text: '200000 toman', travel_start: '2027-03-01',
            travel_end: '2027-03-04', interest: 'historic gardens',
          },
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
    expect(host.querySelector<HTMLInputElement>('#profile-origin')?.value).toBe('Tehran');
    expect(host.querySelector<HTMLInputElement>('#profile-travelers')?.value).toBe('4');
    expect(host.querySelector<HTMLInputElement>('#profile-budget')?.value).toBe('200000 toman');
    expect(host.querySelector<HTMLInputElement>('#profile-travel-start')?.value).toBe('2027-03-01');
    expect(host.querySelector<HTMLInputElement>('#profile-travel-end')?.value).toBe('2027-03-04');
    expect(host.querySelector<HTMLTextAreaElement>('#profile-interests')?.value).toBe('historic gardens');
    expect(fetchMock.mock.calls.filter(call => call[1]?.method === 'PATCH')).toHaveLength(0);
    const saveButton = [...host.querySelectorAll('button')].find(button => button.textContent?.trim() === 'Save trip details');
    expect(saveButton?.disabled).toBe(true); // Unreviewed AI fields cannot silently change trip consent.
    await act(async () => {
      host.querySelector<HTMLInputElement>('#requirement-consent-origin-must')!.click();
      host.querySelector<HTMLInputElement>('#requirement-consent-traveler_count-must')!.click();
      host.querySelector<HTMLInputElement>('#requirement-consent-budget-must')!.click();
      host.querySelector<HTMLInputElement>('#requirement-consent-travel_dates-must')!.click();
    });
    await settle();
    expect(saveButton?.disabled).toBe(false);
    await act(async () => clickLabel('Save trip details')); await settle();
    const saved = fetchMock.mock.calls.find(call => call[1]?.method === 'PATCH');
    expect(saved).toBeDefined();
    const body = JSON.parse(String(saved![1]?.body));
    expect(body.confirmed_requirements.destinations).toEqual(['Kashan']);
    expect(body.confirmed_requirements.duration_days).toBe(1);
    expect(body.confirmed_requirements.origin).toBe('Tehran');
    expect(body.confirmed_requirements.traveler_count).toBe(4);
    expect(body.confirmed_requirements.budget.amount).toBe(200000);
    expect(body.confirmed_requirements.budget.unit).toBe('toman');
    expect(body.confirmed_requirements.travel_dates).toEqual({
      start: '2027-03-01', end: '2027-03-04',
    });
    expect(body.confirmed_requirements.interests).toEqual(['historic gardens']);
    expect(body.requirement_consent.field_decisions).toEqual({
      origin: 'must_have', traveler_count: 'must_have',
      budget: 'must_have', travel_dates: 'must_have',
    });
  });
});
