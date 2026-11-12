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
  const responsePromise = page.waitForResponse(response => predicate(new URL(response.url()).pathname, response.request().method()), { timeout: 45000 });
  await action();
  const response = await responsePromise;
  report(step, response.status(), Date.now() - start);
  if (expected !== null) requireTruth(response.status() === expected, `${step}_http_${response.status()}`);
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

export async function runJourney({ page }) {
  let realAssistantTurns = 0;
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('.auth-signed-in').waitFor({ state: 'visible' });
  requireTruth(await page.locator('.traveler-app').count() === 1, 'app_upgrade_not_served');
  requireTruth(await page.locator('.trip-history > .history-conversation').count() >= 2, 'existing_history_missing');

  const oldTrips = page.locator('.history-trip > button:first-child');
  requireTruth(await oldTrips.count() >= 2, 'two_existing_trips_missing');
  for (let index = 0; index < 2; index += 1) {
    await call(page, `legacy_conversation_${index + 1}`,
      (path, method) => /^\/api\/v1\/conversations\/[0-9a-f-]+$/iu.test(path) && method === 'GET',
      () => oldTrips.nth(index).click());
    await page.locator('#profile-duration').waitFor({ state: 'visible' });
    requireTruth(await page.locator('.journey-error').count() === 0, `legacy_trip_${index + 1}_ui_error`);
    report(`legacy_trip_${index + 1}_rendered`, 200, 0);
  }

  await page.locator('.journey-new-actions button').last().click();
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
  requireTruth((await page.locator('#profile-budget').inputValue()).includes('تومان'), 'budget_unit_lost');
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
    && profileBody?.confirmed_requirements?.budget?.currency === 'TOMAN', 'confirmed_profile_wrong');

  const recommended = await call(page, 'recommend',
    (path, method) => path === `/api/v1/trips/${tripId}/recommendations` && method === 'POST',
    () => page.getByRole('button', { name: 'بررسی پیشنهادهای تأییدشده', exact: true }).click());
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
    () => page.getByRole('button', { name: requestText, exact: true }).click());
  await page.locator('.saved-stop textarea').first().waitFor({ state: 'visible' });
  requireTruth(await page.locator('.saved-stop textarea').first().inputValue() === note,
    'itinerary_edit_not_reopened');
  requireTruth(await page.locator('.saved-message-assistant').count() >= realAssistantTurns,
    'assistant_history_not_reopened');
  report('STRUCTURED_TRAVELER_JOURNEY', 'PASS', 0);
  report('REAL_ASSISTANT_TURNS', realAssistantTurns, 0);
  requireTruth(realAssistantTurns === 2, 'real_ai_acceptance_blocked');
  report('FULL_REAL_TRAVELER_JOURNEY', 'PASS', 0);
}
