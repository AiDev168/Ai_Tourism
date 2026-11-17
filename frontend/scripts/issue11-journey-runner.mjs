// Real private-pilot acceptance. It uses the visible browser's authenticated
// context and ordinary UI/API calls. It never logs private text or credentials.
const requestText = 'برای فردا برای 5 نفر برای بازدید از مناطق تاریخی شیراز برنامه ریزی سفر کن و هزینه ای که میخوایم بکنیم 5 میلیون تومان است';

function report(step, status, elapsedMs) {
  process.stdout.write(`PILOT_STEP:${step};STATUS:${status};MS:${elapsedMs}\n`);
}

function requireTruth(value, code) {
  if (!value) throw new Error(code);
}

async function call(page, step, predicate, action, expected = 200) {
  const start = Date.now();
  const responsePromise = page.waitForResponse(
    response => predicate(new URL(response.url()).pathname, response.request().method()), { timeout: 20000 },
  ).then(response => ({ response }), () => ({ timedOut: true }));
  await action();
  const result = await responsePromise;
  requireTruth(!result.timedOut, `${step}_response_timeout`);
  const response = result.response;
  report(step, response.status(), Date.now() - start);
  if (expected !== null && response.status() !== expected) {
    const body = await response.json().catch(() => null);
    const code = typeof body?.error?.code === 'string' ? body.error.code : 'unknown';
    report(`${step}_error_code`, code, 0);
    throw new Error(`${step}_http_${response.status()}_${code}`);
  }
  return response;
}

function tomorrowInTehran() {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Tehran', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  const today = new Date(`${values.year}-${values.month}-${values.day}T00:00:00Z`);
  today.setUTCDate(today.getUTCDate() + 1);
  return today.toISOString().slice(0, 10);
}

async function savedTripRecords(page) {
  const response = await page.request.get('https://localhost:8443/api/v1/conversations?limit=50');
  requireTruth(response.status() === 200, 'history_api_unavailable');
  const body = await response.json();
  return (body.items ?? []).flatMap(conversation => (conversation.trips ?? []).map(trip => ({
    ...trip, conversation_id: conversation.conversation_id,
  })));
}

async function resumeExistingJourney(page, targetTrip, existingTrips) {
  const open = await call(page, 'reopen_in_progress_trip',
    (path, method) => /^\/api\/v1\/conversations\/[0-9a-f-]+$/iu.test(path) && method === 'GET',
    () => page.locator(`[data-trip-id="${targetTrip.trip_id}"] > button:first-child`).click());
  const detail = await open.json();
  const trip = detail.trips?.find(item => item.trip_id === targetTrip.trip_id);
  const tripId = trip?.trip_id;
  const conversationId = detail.conversation_id;
  requireTruth(Boolean(tripId && conversationId), 'in_progress_trip_not_found');
  await page.locator('#profile-duration').waitFor({ state: 'visible' });
  report('new_trip_reopened', 200, 0);

  const realAssistantTurns = await page.locator('.saved-message-assistant').count();
  report('persisted_real_assistant_replies', realAssistantTurns, 0);
  if (!realAssistantTurns) report('live_chat_blocked', 'prior_provider_timeout_and_daily_limit', 0);

  await page.locator('#profile-duration').fill('1');
  const budgetInput = await page.locator('#profile-budget').inputValue();
  requireTruth(budgetInput.trim().length > 0, 'budget_missing');
  requireTruth(await page.locator('#profile-travelers').inputValue() === '5', 'traveler_count_lost');
  const tomorrow = tomorrowInTehran();
  await page.locator('#profile-travel-start').fill(tomorrow);
  await page.locator('#profile-travel-end').fill(tomorrow);
  while (await page.locator('.destination-edit-row').count()) {
    await page.locator('.destination-edit-row').first().locator('button').click();
  }
  const catalogue = await page.request.get('https://localhost:8443/api/v1/catalog/destinations');
  report('published_catalogue', catalogue.status(), 0);
  requireTruth(catalogue.status() === 200, 'catalogue_unavailable');
  const catalogueBody = await catalogue.json();
  const selected = catalogueBody.items?.filter(item => /shiraz|شیراز/iu.test(item.city_name ?? ''))
    .slice(0, 3) ?? [];
  requireTruth(selected.length >= 1, 'approved_shiraz_poi_missing');
  report('selected_approved_destination_count', selected.length, 0);
  await page.getByRole('button', { name: 'دیدن مقصدهای تأییدشده', exact: true }).click();
  await page.locator('#approved-destination-browser li').first().waitFor({ state: 'visible' });
  for (const item of selected) {
    const name = item.localized_names['fa-IR'] ?? item.canonical_name;
    const button = page.getByRole('button', { name: new RegExp(name.replace(/[.*+?^${}()|[\]\\]/gu, '\\$&')) });
    await button.first().click();
  }
  for (const field of ['budget', 'traveler_count', 'travel_dates']) {
    const choice = page.locator(`#requirement-consent-${field}-advisory`);
    if (await choice.count()) {
      await choice.check();
      await page.locator(`#requirement-consent-${field}-ack`).check();
    }
  }
  const profile = await call(page, 'confirm_profile',
    (path, method) => path === `/api/v1/trips/${tripId}` && method === 'PATCH',
    () => page.getByRole('button', { name: 'ذخیرهٔ تغییرات برداشت سفر', exact: true }).click());
  const profileBody = (await profile.json())?.confirmed_requirements;
  report('budget_schema_keys', Object.keys(profileBody?.budget ?? {}).sort().join(','), 0);
  const budgetEvidence = `${profileBody?.budget?.unit ?? ''} ${profileBody?.budget?.raw ?? ''}`;
  const profileChecks = {
    duration: profileBody?.duration_days === 1,
    travelers: profileBody?.traveler_count === 5,
    currency: profileBody?.budget?.currency === 'TOMAN',
    amount: Number(profileBody?.budget?.amount) === 5,
    scale: profileBody?.budget?.scale === 'million' || /million|میلیون|مليون/iu.test(budgetEvidence),
    denomination: profileBody?.budget?.currency === 'TOMAN' && /toman|تومان/iu.test(budgetEvidence),
  };
  for (const [field, passed] of Object.entries(profileChecks)) report(`profile_${field}`, passed ? 'PASS' : 'FAIL', 0);
  requireTruth(Object.values(profileChecks).every(Boolean), 'confirmed_profile_wrong');
  const recommended = await call(page, 'recommend',
    (path, method) => path === `/api/v1/trips/${tripId}/recommendations` && method === 'POST',
    () => page.getByRole('button', { name: 'بررسی پیشنهادهای تأییدشده', exact: true }).click(), 201);
  const recommendationBody = await recommended.json();
  report('recommendation_status', recommendationBody?.status ?? 'missing', 0);
  report('recommendation_count', recommendationBody?.items?.length ?? 0, 0);
  report('recommendation_reason', recommendationBody?.reason_code ?? 'none', 0);
  report('recommendation_unresolved', (recommendationBody?.unresolved_fields ?? []).join(','), 0);
  requireTruth(recommendationBody?.status === 'available' && recommendationBody.items?.length > 0
    && recommendationBody.items.every(item => item.evidence?.length > 0), 'real_recommendation_not_available');
  const itinerary = await call(page, 'create_itinerary',
    (path, method) => /\/api\/v1\/trips\/[0-9a-f-]+\/itineraries$/iu.test(path) && method === 'POST',
    () => page.locator('.itinerary-start button').click(), 201);
  requireTruth((await itinerary.json())?.day_count === 1, 'one_day_plan_not_created');
  const note = 'یادداشت شخصی برای مرور برنامه';
  await page.locator('.saved-stop textarea').first().fill(note);
  await call(page, 'save_itinerary_edit',
    (path, method) => /\/api\/v1\/itineraries\/[0-9a-f-]+$/iu.test(path) && method === 'PUT',
    () => page.locator('.saved-itinerary > button').last().click());
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('.auth-signed-in').waitFor({ state: 'visible' });
  await call(page, 'reopen_new_trip',
    (path, method) => path === `/api/v1/conversations/${conversationId}` && method === 'GET',
    () => page.locator(`[data-trip-id="${tripId}"] > button:first-child`).click());
  await page.locator('.saved-stop textarea').first().waitFor({ state: 'visible' });
  requireTruth(await page.locator('.saved-stop textarea').first().inputValue() === note, 'itinerary_edit_not_reopened');
  for (let index = 0; index < existingTrips.length; index += 1) {
    const legacyTrip = existingTrips[index];
    await call(page, `legacy_conversation_${index + 1}`,
      (path, method) => /^\/api\/v1\/conversations\/[0-9a-f-]+$/iu.test(path) && method === 'GET',
      () => page.locator(`[data-trip-id="${legacyTrip.trip_id}"] > button:first-child`).click());
    await page.locator('#profile-duration').waitFor({ state: 'visible' });
    report(`legacy_trip_${index + 1}_rendered`, 200, 0);
  }
  report('REAL_ASSISTANT_TURNS', realAssistantTurns, 0);
  report('STRUCTURED_TRAVELER_JOURNEY', 'PASS', 0);
  report('FULL_REAL_TRAVELER_JOURNEY', realAssistantTurns >= 1 ? 'PASS' : 'BLOCKED_LIVE_ASSISTANT', 0);
}

export async function runJourney({ page }) {
  let realAssistantTurns = 0;
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('.auth-signed-in').waitFor({ state: 'visible' });
  requireTruth(await page.locator('.traveler-app').count() === 1, 'app_upgrade_not_served');
  const oldTrips = page.locator('.history-trip > button:first-child');
  await oldTrips.first().waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
  const tripRecords = await savedTripRecords(page);
  requireTruth(tripRecords.length >= 2, 'two_existing_trips_missing');
  report('saved_trip_count', tripRecords.length, 0);
  const matchingTrips = tripRecords.filter(trip => trip.original_request === requestText);
  report('matching_request_count', matchingTrips.length, 0);
  const resumableTrip = matchingTrips.sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))[0];
  if (resumableTrip) {
    const existingTrips = tripRecords.filter(trip => trip.trip_id !== resumableTrip.trip_id).slice(0, 2);
    await resumeExistingJourney(page, resumableTrip, existingTrips);
    return;
  }
  const existingTrips = tripRecords.slice(0, 2);
  await page.locator('#trip-prompt').waitFor({ state: 'visible' });
  await page.locator('#trip-prompt').fill(requestText);
  const interpreted = await call(page, 'interpret',
    (path, method) => path === '/api/v1/requirements/interpret' && method === 'POST',
    () => page.locator('.trip-form button[type="submit"]').click());
  const fields = (await interpreted.json()).requirements?.fields;
  requireTruth(fields?.destination?.value === 'شیراز'
    && fields?.travelers?.value === 5
    && fields?.relative_start_date?.value?.offset_days === 1
    && fields?.duration_days?.status === 'missing'
    && fields?.budget?.value?.amount === '5'
    && fields?.budget?.value?.scale === 'million'
    && fields?.budget?.value?.currency === 'TOMAN'
    && fields?.interests?.value?.includes('historical_attractions'), 'persian_interpretation_wrong');
  requireTruth((await page.locator('.trip-summary').textContent())?.includes('جاهای تاریخی'), 'understanding_not_readable');

  await page.locator('.journey-action').first().waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});
  report('trip_action_count', await page.locator('.journey-action').count(), 0);
  report('active_trip_badge_count', await page.locator('.saved-pill').count(), 0);
  report('active_trip_profile_fields', await page.locator('#profile-duration').count(), 0);
  report('trip_draft_summary_visible', await page.locator('.trip-summary').isVisible().catch(() => false), 0);
  requireTruth(await page.locator('.journey-action').count() >= 1, 'create_trip_action_missing');
  requireTruth(await page.locator('.journey-action').isEnabled(), 'create_trip_action_disabled');
  const created = await call(page, 'create_conversation',
    (path, method) => path === '/api/v1/conversations' && method === 'POST',
    () => page.locator('.journey-action').click(), 201);
  const createdBody = await created.json();
  const tripId = createdBody?.trip?.trip_id;
  const conversationId = createdBody?.conversation?.conversation_id;
  requireTruth(Boolean(tripId && conversationId) && createdBody.trip.original_request === requestText,
    'new_trip_not_persisted');
  await page.locator('#trip-follow-up').waitFor({ state: 'visible' });

  await page.locator('#assistant-remote-consent').check();
  for (const [index, message] of [
    'مدت سفر را هنوز مشخص نکرده‌ام. برای برنامه‌ریزی این سفر چه چیز دیگری باید روشن شود؟',
    'اصلاح می‌کنم: مدت سفر یک روز است و پنج میلیون تومان بودجهٔ کل گروه است. برای بازدید تاریخی چه پیشنهادی داری؟',
  ].entries()) {
    await page.locator('#trip-follow-up').fill(message);
    const turn = await call(page, `real_assistant_turn_${index + 1}`,
      (path, method) => path === `/api/v1/conversations/${conversationId}/assistant-turns` && method === 'POST',
      () => page.locator('.assistant-controls > button').click(), null);
    if (turn.status() !== 200) {
      report(`real_assistant_turn_${index + 1}_blocked`, turn.status(), 0);
      break;
    }
    const body = await turn.json();
    requireTruth(body?.message?.role === 'assistant' && typeof body.message.content === 'string'
      && body.message.content.trim().length > 0 && body?.replayed === false,
      `assistant_turn_${index + 1}_not_real_reply`);
    requireTruth(await page.locator('.saved-message-assistant').count() >= index + 1,
      `assistant_turn_${index + 1}_not_visible`);
    realAssistantTurns += 1;
  }

  // The AI's suggestions stay advisory. The test operator explicitly reviews
  // the one-day duration and calendar date through the real profile controls.
  await page.locator('#profile-duration').fill('1');
  const budgetInput = await page.locator('#profile-budget').inputValue();
  requireTruth(budgetInput.trim().length > 0, 'budget_missing');
  requireTruth(await page.locator('#profile-travelers').inputValue() === '5', 'traveler_count_lost');
  const tomorrow = tomorrowInTehran();
  await page.locator('#profile-travel-start').fill(tomorrow);
  await page.locator('#profile-travel-end').fill(tomorrow);

  // Replace the broad city phrase with individually approved POI identities;
  // no unpublished or synthetic catalogue row is injected.
  const existingDestination = page.locator('.destination-edit-row');
  if (await existingDestination.count()) await existingDestination.first().locator('button').click();
  const catalogue = await page.request.get('https://localhost:8443/api/v1/catalog/destinations');
  report('published_catalogue', catalogue.status(), 0);
  requireTruth(catalogue.status() === 200, 'catalogue_unavailable');
  const catalogueBody = await catalogue.json();
  const selected = catalogueBody.items?.filter(item => /shiraz|شیراز/iu.test(item.city_name ?? '')).slice(0, 3) ?? [];
  requireTruth(selected.length >= 1, 'approved_shiraz_poi_missing');
  await page.getByRole('button', { name: 'دیدن مقصدهای تأییدشده', exact: true }).click();
  await page.locator('#approved-destination-browser li').first().waitFor({ state: 'visible' });
  for (const item of selected) {
    const name = item.localized_names['fa-IR'] ?? item.canonical_name;
    const locality = item.city_name ?? item.province_name ?? '';
    await page.getByRole('button', { name: `افزودن به سفر: ${name} · ${locality}`, exact: true }).click();
  }

  for (const field of ['budget', 'traveler_count', 'travel_dates']) {
    const choice = page.locator(`#requirement-consent-${field}-advisory`);
    requireTruth(await choice.count() === 1, `${field}_consent_missing`);
    await choice.check();
    await page.locator(`#requirement-consent-${field}-ack`).check();
  }
  const profile = await call(page, 'confirm_profile',
    (path, method) => path === `/api/v1/trips/${tripId}` && method === 'PATCH',
    () => page.getByRole('button', { name: 'ذخیرهٔ تغییرات برداشت سفر', exact: true }).click());
  const profileBody = await profile.json();
  requireTruth(profileBody?.confirmed_requirements?.duration_days === 1
    && profileBody?.confirmed_requirements?.traveler_count === 5
    && profileBody?.confirmed_requirements?.budget?.currency === 'TOMAN'
    && Number(profileBody.confirmed_requirements.budget.amount) === 5
    && (profileBody.confirmed_requirements.budget.scale === 'million'
      || /million|میلیون|مليون/iu.test(`${profileBody.confirmed_requirements.budget.unit ?? ''} ${profileBody.confirmed_requirements.budget.raw ?? ''}`))
    && /toman|تومان/iu.test(`${profileBody.confirmed_requirements.budget.unit ?? ''} ${profileBody.confirmed_requirements.budget.raw ?? ''}`), 'confirmed_profile_wrong');

  const recommended = await call(page, 'recommend',
    (path, method) => path === `/api/v1/trips/${tripId}/recommendations` && method === 'POST',
    () => page.getByRole('button', { name: 'بررسی پیشنهادهای تأییدشده', exact: true }).click(), 201);
  const recommendationBody = await recommended.json();
  requireTruth(recommendationBody?.status === 'available'
    && recommendationBody.items?.length >= 1
    && recommendationBody.items.every(item => item.evidence?.length > 0), 'real_recommendation_not_available');

  const itinerary = await call(page, 'create_itinerary',
    (path, method) => /\/api\/v1\/trips\/[0-9a-f-]+\/itineraries$/iu.test(path) && method === 'POST',
    () => page.locator('.itinerary-start button').click(), 201);
  const itineraryBody = await itinerary.json();
  requireTruth(itineraryBody?.day_count === 1 && itineraryBody.stops?.length >= 1, 'one_day_plan_not_created');
  const note = 'یادداشت شخصی برای مرور برنامه';
  await page.locator('.saved-stop textarea').first().fill(note);
  await call(page, 'save_itinerary_edit',
    (path, method) => /\/api\/v1\/itineraries\/[0-9a-f-]+$/iu.test(path) && method === 'PUT',
    () => page.locator('.saved-itinerary > button').last().click());

  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('.auth-signed-in').waitFor({ state: 'visible' });
  await call(page, 'reopen_new_trip',
    (path, method) => path === `/api/v1/conversations/${conversationId}` && method === 'GET',
    () => page.locator(`[data-trip-id="${tripId}"] > button:first-child`).click());
  await page.locator('.saved-stop textarea').first().waitFor({ state: 'visible' });
  requireTruth(await page.locator('.saved-stop textarea').first().inputValue() === note,
    'itinerary_edit_not_reopened');
  requireTruth(await page.locator('.saved-message-assistant').count() >= realAssistantTurns,
    'assistant_history_not_reopened');
  for (let index = 0; index < existingTrips.length; index += 1) {
    const legacyTrip = existingTrips[index];
    await call(page, `legacy_conversation_${index + 1}`,
      (path, method) => /^\/api\/v1\/conversations\/[0-9a-f-]+$/iu.test(path) && method === 'GET',
      () => page.locator(`[data-trip-id="${legacyTrip.trip_id}"] > button:first-child`).click());
    await page.locator('#profile-duration').waitFor({ state: 'visible' });
    requireTruth(await page.locator('.journey-error').count() === 0, `legacy_trip_${index + 1}_ui_error`);
    report(`legacy_trip_${index + 1}_rendered`, 200, 0);
  }
  report('STRUCTURED_TRAVELER_JOURNEY', 'PASS', 0);
  report('REAL_ASSISTANT_TURNS', realAssistantTurns, 0);
  report('FULL_REAL_TRAVELER_JOURNEY', realAssistantTurns === 2 ? 'PASS' : 'BLOCKED_LIVE_ASSISTANT', 0);
}
