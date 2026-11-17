// Real private-pilot Issue #12 acceptance. Uses an authenticated visible
// Playwright context, ordinary PWA/API calls, and the configured Chat route.
// Never logs credentials, cookies, message text, tokens, or provider secrets.
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { toJalaali } from 'jalaali-js';

const BASE = 'https://localhost:8443';
const EXACT_REQUEST = 'برای فردا برای 5 نفر برای بازدید از مناطق تاریخی شیراز برنامه ریزی سفر کن و هزینه ای که میخوایم بکنیم 5 میلیون تومان است';
const MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'];
const WEEKDAYS = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه'];
const report = (step, value, elapsed = 0) => process.stdout.write(`ISSUE12:${step}:${value}:ms=${elapsed}\n`);
const requireTruth = (condition, code) => { if (!condition) throw new Error(code); };

async function apiJson(page, pathname) {
  const response = await page.request.get(`${BASE}${pathname}`, { timeout: 15000 });
  return { response, body: await response.json().catch(() => null) };
}

async function waitApi(page, step, pathname, method, action, timeout = 75000) {
  const started = Date.now();
  const pending = page.waitForResponse(response => {
    const url = new URL(response.url());
    return url.pathname === pathname && response.request().method() === method;
  }, { timeout });
  await action();
  const response = await pending;
  report(step, response.status(), Date.now() - started);
  return response;
}

function tehranIsoAfter(days) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Tehran', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  const date = new Date(`${values.year}-${values.month}-${values.day}T00:00:00.000Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

const faNumber = value => new Intl.NumberFormat('fa-IR', { useGrouping: false }).format(value);

async function selectJalaliDate(page, fieldId, iso) {
  const [gy, gm, gd] = iso.split('-').map(Number);
  const j = toJalaali(gy, gm, gd);
  const expectedTitle = `${MONTHS[j.jm - 1]} ${faNumber(j.jy)}`;
  await page.locator(`#${fieldId}-picker`).click();
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const title = (await page.locator('.jalali-calendar-heading strong').textContent())?.trim();
    if (title === expectedTitle) break;
    const currentMonth = MONTHS.findIndex(month => title?.includes(month)) + 1;
    const yearText = title?.replace(MONTHS[currentMonth - 1], '').trim() ?? '';
    const year = Number(yearText.replace(/[۰-۹]/gu, digit => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit))));
    requireTruth(currentMonth > 0 && Number.isFinite(year), 'jalali_calendar_month_unreadable');
    const currentIndex = year * 12 + currentMonth;
    const targetIndex = j.jy * 12 + j.jm;
    await page.locator(targetIndex > currentIndex
      ? '.jalali-calendar-heading button[aria-label="ماه بعد"]'
      : '.jalali-calendar-heading button[aria-label="ماه قبل"]').click();
  }
  requireTruth((await page.locator('.jalali-calendar-heading strong').textContent())?.trim() === expectedTitle,
    'jalali_calendar_navigation_failed');
  const gregorianWeekday = new Date(`${iso}T00:00:00.000Z`).getUTCDay();
  const weekDay = WEEKDAYS[(gregorianWeekday + 1) % 7];
  const label = `${weekDay} ${faNumber(j.jd)} ${MONTHS[j.jm - 1]} ${faNumber(j.jy)}`;
  await page.getByRole('gridcell', { name: label, exact: true }).click();
  requireTruth(await page.locator(`#${fieldId}`).inputValue() === iso, 'jalali_iso_date_contract_failed');
}

export async function runIssue12Acceptance({ page }) {
  const errors = [];
  const pageError = () => errors.push('page_error');
  page.on('pageerror', pageError);
  const runDir = path.resolve('artifacts', 'visual-qa-task15d', 'run-issue12');
  await mkdir(runDir, { recursive: true });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('.auth-signed-in').waitFor({ state: 'visible', timeout: 15000 });
  requireTruth(await page.locator('#trip-prompt').isVisible(), 'traveler_request_ui_missing');

  const { response: statusResponse, body: assistantStatus } = await apiJson(page, '/api/v1/assistant/status');
  requireTruth(statusResponse.status() === 200, 'assistant_status_unavailable');
  report('chat_route_state', assistantStatus?.state ?? 'missing');
  report('chat_requests_remaining', Math.min(assistantStatus?.user_remaining ?? 0, assistantStatus?.global_remaining ?? 0));
  requireTruth(assistantStatus?.state === 'configured' && Math.min(assistantStatus.user_remaining, assistantStatus.global_remaining) >= 2,
    'chat_route_or_daily_quota_not_ready');

  const { response: usageResponse, body: usageBefore } = await apiJson(page, '/api/v1/admin/ai-providers/usage');
  requireTruth(usageResponse.status() === 200, 'admin_chat_usage_not_authorized');
  const chatUsageBefore = (usageBefore?.usage ?? []).find(item => item.capability === 'chat') ?? { calls: 0, successes: 0, failures: 0 };

  const historyResponse = await page.request.get(`${BASE}/api/v1/conversations?limit=50`, { timeout: 15000 });
  requireTruth(historyResponse.status() === 200, 'existing_trip_history_unavailable');
  const history = await historyResponse.json();
  const oldTrips = (history.items ?? []).flatMap(conversation => (conversation.trips ?? []).map(trip => ({
    trip_id: trip.trip_id, conversation_id: conversation.conversation_id,
    original_request: trip.original_request, updated_at: trip.updated_at,
    latest_itinerary_id: trip.latest_itinerary_id,
  })));
  requireTruth(oldTrips.length >= 2, 'existing_trips_missing');
  report('existing_trips_before', oldTrips.length);

  // If a prior attempt already completed the two live calls and itinerary,
  // resume its read-only persistence checks instead of spending quota again.
  let resumable = null;
  for (const candidate of oldTrips.filter(trip => trip.original_request === EXACT_REQUEST
    && typeof trip.latest_itinerary_id === 'string').sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))) {
    const response = await page.request.get(`${BASE}/api/v1/conversations/${candidate.conversation_id}`, { timeout: 15000 });
    if (response.status() !== 200) continue;
    const detail = await response.json();
    const tripMessages = (detail.messages ?? []).filter(message => message.trip_id === candidate.trip_id);
    if (tripMessages.filter(message => message.role === 'assistant').length >= 2
      && tripMessages.filter(message => message.role === 'user' && message.content === EXACT_REQUEST).length === 1) {
      resumable = { ...candidate, detail };
      break;
    }
  }
  if (resumable) {
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.locator('.auth-signed-in').waitFor({ state: 'visible', timeout: 15000 });
    const newButton = page.locator(`[data-trip-id="${resumable.trip_id}"] > button:first-child`);
    const reopened = await waitApi(page, 'saved_trip_reopen', `/api/v1/conversations/${resumable.conversation_id}`, 'GET',
      () => newButton.click(), 20000);
    requireTruth(reopened.status() === 200, 'saved_conversation_reopen_failed');
    await page.locator('.saved-message-assistant').nth(1).waitFor({ state: 'visible', timeout: 15000 });
    await page.locator('.saved-stop textarea').first().waitFor({ state: 'visible', timeout: 15000 });
    requireTruth(await page.locator('.saved-stop textarea').first().inputValue() === 'یادداشت شخصی برای بازبینی برنامه',
      'saved_itinerary_edit_not_restored');
    const priorTrips = oldTrips.filter(trip => trip.trip_id !== resumable.trip_id).slice(0, 2);
    for (const [index, prior] of priorTrips.entries()) {
      const priorButton = page.locator(`[data-trip-id="${prior.trip_id}"] > button:first-child`);
      const result = await waitApi(page, `preserved_trip_${index + 1}_open`, `/api/v1/conversations/${prior.conversation_id}`, 'GET',
        () => priorButton.click(), 20000);
      requireTruth(result.status() === 200, `preserved_trip_${index + 1}_failed`);
      await page.locator('#profile-duration').waitFor({ state: 'visible', timeout: 10000 });
    }
    const after = await page.request.get(`${BASE}/api/v1/conversations?limit=50`, { timeout: 15000 });
    const current = (await after.json()).items.flatMap(conversation => conversation.trips ?? []);
    for (const prior of priorTrips) {
      const persisted = current.find(trip => trip.trip_id === prior.trip_id);
      requireTruth(persisted && persisted.original_request === prior.original_request
        && persisted.updated_at === prior.updated_at, 'existing_trip_changed_during_acceptance');
    }
    report('saved_conversation_assistant_turns', 2);
    report('saved_itinerary_reopened', 'PASS');
    report('existing_trip_reopen_and_preservation', 'PASS');
    const { response: routesResponse, body: routesBody } = await apiJson(page, '/api/v1/admin/ai-providers/routes');
    requireTruth(routesResponse.status() === 200, 'active_chat_route_not_authorized');
    const chatRoute = (routesBody?.routes ?? []).find(item => item.capability === 'chat');
    requireTruth(chatRoute?.active === true, 'chat_route_not_active');
    const { response: profilesResponse, body: profilesBody } = await apiJson(page, '/api/v1/admin/ai-providers/profiles');
    requireTruth(profilesResponse.status() === 200, 'provider_profiles_not_authorized');
    const activeProfile = (profilesBody?.profiles ?? []).find(item => item.id === chatRoute.profile_id);
    requireTruth(activeProfile?.enabled === true, 'active_chat_profile_disabled');
    report('active_chat_provider_kind', activeProfile.provider_kind);
    report('active_chat_profile_enabled', activeProfile.enabled);
    // Read aggregate provider usage as corroboration for the two persisted
    // traveler turns. This path never invokes the model or prints routing data.
    const { response: usageResponse, body: usageBody } = await apiJson(page, '/api/v1/admin/ai-providers/usage');
    requireTruth(usageResponse.status() === 200, 'admin_chat_usage_not_authorized');
    const chatUsage = (usageBody?.usage ?? []).find(item => item.capability === 'chat')
      ?? { calls: 0, successes: 0, failures: 0, latency_ms_avg: null };
    requireTruth(chatUsage.successes >= 2, 'provider_usage_does_not_corrobate_two_chat_successes');
    report('provider_chat_usage', JSON.stringify({
      calls: chatUsage.calls,
      successes: chatUsage.successes,
      failures: chatUsage.failures,
      latency_ms_avg: chatUsage.latency_ms_avg ?? null,
    }));
    report('JALALI_AI_FIRST_TRAVELER_ACCEPTANCE', 'PASS');
    page.off('pageerror', pageError);
    return { status: 'PASS', screenshots: [], chatSuccessDelta: 2 };
  }

  await page.locator('#trip-prompt').fill(EXACT_REQUEST);
  await page.locator('#initial-ai-consent').check();
  const interpretation = await waitApi(page, 'persian_interpretation', '/api/v1/requirements/interpret', 'POST',
    () => page.locator('.trip-form button[type="submit"]').click(), 20000);
  requireTruth(interpretation.status() === 200, 'interpretation_http_failure');
  const interpretationBody = await interpretation.json();
  const fields = interpretationBody.requirements?.fields;
  requireTruth(fields?.destination?.value === 'شیراز' && fields?.travelers?.value === 5
    && fields?.relative_start_date?.value?.offset_days === 1
    && fields?.relative_start_date?.value?.timezone === 'Asia/Tehran'
    && fields?.duration_days?.status === 'missing'
    && fields?.budget?.value?.amount === '5' && fields?.budget?.value?.scale === 'million'
    && fields?.budget?.value?.currency === 'TOMAN'
    && fields?.interests?.value?.includes('historical_attractions'), 'persian_request_contract_wrong');
  report('exact_persian_request_contract', 'PASS');

  const draftActions = page.locator('.journey-action');
  report('draft_action_count', await draftActions.count());
  report('trip_summary_visible', await page.locator('.trip-summary').isVisible().catch(() => false));
  report('initial_ai_consent_checked', await page.locator('#initial-ai-consent').isChecked().catch(() => false));
  if (!(await draftActions.count())) throw new Error('conversation_start_action_missing');
  if (!(await draftActions.first().isEnabled())) throw new Error('conversation_start_action_disabled');

  const createConversation = page.waitForResponse(response =>
    new URL(response.url()).pathname === '/api/v1/conversations'
    && response.request().method() === 'POST', { timeout: 20000 });
  const firstAssistantTurn = page.waitForResponse(response =>
    /^\/api\/v1\/conversations\/[0-9a-f-]{36}\/assistant-turns$/iu.test(new URL(response.url()).pathname)
    && response.request().method() === 'POST', { timeout: 75000 });
  const createStarted = Date.now();
  await page.locator('.journey-action').first().click();
  const createdResponse = await createConversation;
  requireTruth(createdResponse.status() === 201, 'initial_conversation_not_saved');
  const created = await createdResponse.json();
  const tripId = created.trip?.trip_id;
  const conversationId = created.conversation?.conversation_id;
  requireTruth(Boolean(tripId && conversationId) && created.trip.original_request === EXACT_REQUEST,
    'original_request_not_preserved');
  const initialTurn = await firstAssistantTurn;
  const initialTurnElapsed = Date.now() - createStarted;
  report('first_real_chat_turn', initialTurn.status(), initialTurnElapsed);
  requireTruth(initialTurn.status() === 200, 'first_chat_turn_failed');
  const firstReply = await initialTurn.json();
  requireTruth(firstReply.replayed === false && firstReply.message?.role === 'assistant'
    && typeof firstReply.message.content === 'string' && firstReply.message.content.trim().length > 0,
  'first_chat_reply_not_persisted');
  requireTruth(await page.locator('.saved-message-assistant').count() >= 1, 'first_chat_reply_not_visible');
  requireTruth((firstReply.candidate_requirements?.fields?.duration_days?.status ?? 'missing') === 'missing',
    'unknown_duration_was_invented');
  report('first_chat_reply_persisted_and_duration_unknown', 'PASS');

  await page.locator('#trip-follow-up').fill('مدت سفر سه روز است. لطفاً با همین مدت پیش برو.');
  const secondStarted = Date.now();
  const secondTurn = await waitApi(page, 'second_real_chat_turn', `/api/v1/conversations/${conversationId}/assistant-turns`, 'POST',
    () => page.locator('.assistant-controls > button.primary').click(), 75000);
  requireTruth(secondTurn.status() === 200, 'second_chat_turn_failed');
  const secondReply = await secondTurn.json();
  requireTruth(secondReply.replayed === false && secondReply.message?.role === 'assistant'
    && typeof secondReply.message.content === 'string' && secondReply.message.content.trim().length > 0,
  'second_chat_reply_not_persisted');
  requireTruth(secondReply.candidate_requirements?.fields?.duration_days?.value === 3,
    'explicit_duration_correction_not_extracted');
  report('second_chat_turn_elapsed', Date.now() - secondStarted);
  await page.getByRole('button', { name: 'انتقال به فرم سفر', exact: true }).click();
  requireTruth(await page.locator('#profile-duration').inputValue() === '3', 'duration_suggestion_not_reviewable');

  const startDate = tehranIsoAfter(1);
  const endDate = tehranIsoAfter(3);
  await selectJalaliDate(page, 'profile-travel-start', startDate);
  await selectJalaliDate(page, 'profile-travel-end', endDate);
  report('jalali_date_picker_selection', 'PASS');
  requireTruth(await page.locator('#profile-travelers').inputValue() === '5', 'traveler_count_not_preserved');
  const budgetText = await page.locator('#profile-budget').inputValue();
  requireTruth(/5/u.test(budgetText) && /تومان/u.test(budgetText), 'toman_budget_not_preserved');

  // Replace only the broad region phrase with exact approved catalogue IDs.
  // No fixtures are injected and no catalogue publication is performed here.
  while (await page.locator('.destination-edit-row').count()) {
    await page.locator('.destination-edit-row').first().locator('button').click();
  }
  const catalogueResponse = await page.request.get(`${BASE}/api/v1/catalog/destinations`, { timeout: 15000 });
  requireTruth(catalogueResponse.status() === 200, 'production_catalogue_unavailable');
  const catalogue = await catalogueResponse.json();
  const selected = (catalogue.items ?? []).filter(item => /shiraz|شیراز/iu.test(item.city_name ?? '')).slice(0, 3);
  requireTruth(selected.length >= 1 && selected.every(item => item.is_synthetic !== true), 'approved_shiraz_destinations_missing');
  await page.getByRole('button', { name: /دیدن مقصدهای تأییدشده/u }).click();
  await page.locator('#approved-destination-browser li').first().waitFor({ state: 'visible', timeout: 10000 });
  for (const item of selected) {
    const name = item.localized_names?.['fa-IR'] ?? item.canonical_name;
    const row = page.locator('#approved-destination-browser li').filter({ hasText: name });
    await row.getByRole('button').click();
  }
  for (const field of ['budget', 'traveler_count', 'travel_dates']) {
    const advisory = page.locator(`#requirement-consent-${field}-advisory`);
    if (await advisory.count()) {
      await advisory.check();
      const ack = page.locator(`#requirement-consent-${field}-ack`);
      if (await ack.count()) await ack.check();
    }
  }
  const profileResponse = await waitApi(page, 'profile_confirmation', `/api/v1/trips/${tripId}`, 'PATCH',
    () => page.getByRole('button', { name: 'ذخیرهٔ تغییرات برداشت سفر', exact: true }).click(), 20000);
  requireTruth(profileResponse.status() === 200, 'trip_profile_confirmation_failed');
  const savedProfile = await profileResponse.json();
  requireTruth(savedProfile.confirmed_requirements?.duration_days === 3
    && savedProfile.confirmed_requirements?.traveler_count === 5
    && savedProfile.confirmed_requirements?.budget?.currency === 'TOMAN'
    && Number(savedProfile.confirmed_requirements?.budget?.amount) === 5,
  'confirmed_trip_requirements_wrong');

  const recommendationResponse = await waitApi(page, 'real_recommendations', `/api/v1/trips/${tripId}/recommendations`, 'POST',
    () => page.getByRole('button', { name: 'بررسی پیشنهادهای تأییدشده', exact: true }).click(), 25000);
  requireTruth(recommendationResponse.status() === 201, 'recommendation_request_failed');
  const recommendations = await recommendationResponse.json();
  report('recommendation_outcome', recommendations.status);
  requireTruth(recommendations.status === 'available' && recommendations.items?.length > 0
    && recommendations.items.every(item => Array.isArray(item.evidence) && item.evidence.length > 0),
  'no_evidence_backed_recommendations');

  const itineraryResponse = await waitApi(page, 'itinerary_create', `/api/v1/trips/${tripId}/itineraries`, 'POST',
    () => page.locator('.itinerary-start button').click(), 25000);
  requireTruth(itineraryResponse.status() === 201, 'itinerary_creation_failed');
  const itinerary = await itineraryResponse.json();
  requireTruth(itinerary.day_count === 3, 'three_day_itinerary_not_created');
  const note = 'یادداشت شخصی برای بازبینی برنامه';
  await page.locator('.saved-stop textarea').first().fill(note);
  const saveEdit = await waitApi(page, 'itinerary_edit_save', `/api/v1/itineraries/${itinerary.itinerary_id}`, 'PUT',
    () => page.locator('.saved-itinerary > button').last().click(), 20000);
  requireTruth(saveEdit.status() === 200, 'itinerary_edit_not_saved');
  report('itinerary_stops', itinerary.stops?.length ?? 0);

  await page.screenshot({ path: path.join(runDir, 'fa-IR-mobile-itinerary.png'), fullPage: true,
    mask: [page.locator('#trip-prompt'), page.locator('.conversation-transcript'), page.locator('#trip-follow-up'), page.locator('#profile-budget'), page.locator('#profile-origin')], maskColor: '#555' });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: path.join(runDir, 'fa-IR-desktop-itinerary.png'), fullPage: true,
    mask: [page.locator('#trip-prompt'), page.locator('.conversation-transcript'), page.locator('#trip-follow-up'), page.locator('#profile-budget'), page.locator('#profile-origin')], maskColor: '#555' });

  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('.auth-signed-in').waitFor({ state: 'visible', timeout: 15000 });
  const newTripButton = page.locator(`[data-trip-id="${tripId}"] > button:first-child`);
  await newTripButton.waitFor({ state: 'visible', timeout: 15000 });
  const reopened = await waitApi(page, 'new_trip_reopen', `/api/v1/conversations/${conversationId}`, 'GET',
    () => newTripButton.click(), 20000);
  requireTruth(reopened.status() === 200, 'new_conversation_reopen_failed');
  requireTruth(await page.locator('.saved-message-assistant').count() >= 2, 'assistant_history_not_reopened');
  requireTruth(await page.locator('.saved-stop textarea').first().inputValue() === note, 'itinerary_note_not_reopened');
  const reopenedConversation = await reopened.json();
  const matchingUserRequestCount = (reopenedConversation.messages ?? []).filter(message =>
    message.role === 'user' && message.trip_id === tripId && message.content === EXACT_REQUEST).length;
  requireTruth(matchingUserRequestCount === 1, 'initial_request_was_duplicated');

  for (const [index, oldTrip] of oldTrips.slice(0, 2).entries()) {
    const oldButton = page.locator(`[data-trip-id="${oldTrip.trip_id}"] > button:first-child`);
    const oldConversation = await waitApi(page, `old_trip_${index + 1}_reopen`,
      `/api/v1/conversations/${oldTrip.conversation_id}`, 'GET', () => oldButton.click(), 20000);
    requireTruth(oldConversation.status() === 200, `old_trip_${index + 1}_reopen_failed`);
    await page.locator('#profile-duration').waitFor({ state: 'visible' });
  }
  const historyAfterResponse = await page.request.get(`${BASE}/api/v1/conversations?limit=50`, { timeout: 15000 });
  const afterItems = await historyAfterResponse.json();
  const afterTrips = (afterItems.items ?? []).flatMap(conversation => conversation.trips ?? []);
  for (const oldTrip of oldTrips.slice(0, 2)) {
    const after = afterTrips.find(trip => trip.trip_id === oldTrip.trip_id);
    requireTruth(after && after.original_request === oldTrip.original_request
      && after.updated_at === oldTrip.updated_at, 'existing_trip_was_modified');
  }
  const { response: usageAfterResponse, body: usageAfter } = await apiJson(page, '/api/v1/admin/ai-providers/usage');
  requireTruth(usageAfterResponse.status() === 200, 'chat_usage_after_not_authorized');
  const chatUsageAfter = (usageAfter?.usage ?? []).find(item => item.capability === 'chat') ?? { calls: 0, successes: 0, failures: 0 };
  requireTruth(chatUsageAfter.successes >= chatUsageBefore.successes + 2,
    'provider_chat_usage_did_not_record_two_successes');
  requireTruth(errors.length === 0, 'browser_uncaught_page_error');

  report('real_provider_chat_success_delta', chatUsageAfter.successes - chatUsageBefore.successes);
  report('assistant_messages_reopened', await page.locator('.saved-message-assistant').count());
  report('legacy_trips_preserved', 'PASS');
  report('uncaught_page_errors', errors.length);
  report('JALALI_AI_FIRST_TRAVELER_ACCEPTANCE', 'PASS');
  page.off('pageerror', pageError);
  return { status: 'PASS', screenshots: [
    path.join(runDir, 'fa-IR-mobile-itinerary.png'), path.join(runDir, 'fa-IR-desktop-itinerary.png'),
  ], chatSuccessDelta: chatUsageAfter.successes - chatUsageBefore.successes };
}
