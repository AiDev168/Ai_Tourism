// Guarded, real-browser traveler journey. OTP codes cross only an authenticated
// loopback test-control socket; the application has no OTP debug API.
import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { randomBytes, randomInt, randomUUID } from 'node:crypto';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { createServer, createConnection } from 'node:net';
import { resolve } from 'node:path';
import process from 'node:process';

const root = resolve(import.meta.dirname, '../..');
const backendRoot = resolve(root, 'backend');
const python = process.env.E2E_PYTHON || resolve(root, '.venv/Scripts/python.exe');
const chrome = process.env.E2E_CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const webPort = Number(process.env.E2E_WEB_PORT || 4181);
const apiPort = Number(process.env.E2E_API_PORT || 8811);
const webOrigin = `http://127.0.0.1:${webPort}`;
const apiTarget = `http://127.0.0.1:${apiPort}`;

function requireEnv(name) {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`missing_${name.toLowerCase()}`);
  return value;
}

function runtimeEnv(extra = {}) {
  const env = {};
  for (const key of ['PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP']) {
    if (process.env[key]) env[key] = process.env[key];
  }
  return { ...env, ...extra };
}

function syntheticPhone() {
  return `+98912${randomInt(0, 10_000_000).toString().padStart(7, '0')}`;
}

function makePipe(client) {
  const waiting = [];
  const queued = [];
  const reader = createInterface({ input: client.stdout });
  reader.on('line', line => {
    let value;
    try { value = JSON.parse(line); } catch { return; }
    const resolveNext = waiting.shift();
    if (resolveNext) resolveNext(value);
    else queued.push(value);
  });
  return {
    next(timeoutMs = 20_000) {
      if (queued.length) return Promise.resolve(queued.shift());
      return new Promise((resolvePromise, reject) => {
        const timer = setTimeout(() => {
          const index = waiting.indexOf(finish);
          if (index >= 0) waiting.splice(index, 1);
          reject(new Error('test_pipe_timeout'));
        }, timeoutMs);
        function finish(value) { clearTimeout(timer); resolvePromise(value); }
        waiting.push(finish);
      });
    },
    close() { reader.close(); },
  };
}

async function reserveLoopbackPort() {
  const listener = createServer();
  await new Promise((resolvePromise, reject) => {
    listener.once('error', reject);
    listener.listen(0, '127.0.0.1', resolvePromise);
  });
  const { port } = listener.address();
  await new Promise(resolvePromise => listener.close(resolvePromise));
  return port;
}

async function controlRequest(port, token, command) {
  return new Promise((resolvePromise, reject) => {
    const client = createConnection({ host: '127.0.0.1', port });
    let response = '';
    const timer = setTimeout(() => { client.destroy(); reject(new Error('control_request_timeout')); }, 20_000);
    client.on('connect', () => client.write(`${JSON.stringify({ ...command, token })}\n`));
    client.on('data', chunk => { response += chunk.toString('utf8'); });
    client.on('error', () => { clearTimeout(timer); reject(new Error('control_request_failed')); });
    client.on('end', () => {
      clearTimeout(timer);
      try { resolvePromise(JSON.parse(response.trim())); } catch { reject(new Error('control_response_invalid')); }
    });
  });
}

async function checkedControl(port, token, command) {
  const result = await controlRequest(port, token, command);
  if (!result?.ok) throw new Error(`test_control_${command.action}_failed`);
  return result;
}

async function startApi() {
  const integration = requireEnv('AUTH_INTEGRATION_TESTS');
  if (integration !== '1') throw new Error('set_auth_integration_tests_1');
  for (const key of [
    'AUTH_TEST_DATABASE_HOST', 'AUTH_TEST_DATABASE_PORT', 'AUTH_TEST_DATABASE_NAME',
    'AUTH_TEST_DATABASE_USER', 'AUTH_TEST_DATABASE_PASSWORD', 'AUTH_TEST_DATABASE_MARKER',
  ]) requireEnv(key);
  if (!existsSync(python)) throw new Error('test_python_executable_missing');
  if (!existsSync(chrome)) throw new Error('configured_chrome_executable_missing');
  const controlPort = await reserveLoopbackPort();
  const controlToken = randomBytes(32).toString('hex');

  const childEnv = runtimeEnv({
    AUTH_INTEGRATION_TESTS: '1',
    AUTH_TEST_DATABASE_HOST: process.env.AUTH_TEST_DATABASE_HOST,
    AUTH_TEST_DATABASE_PORT: process.env.AUTH_TEST_DATABASE_PORT,
    AUTH_TEST_DATABASE_NAME: process.env.AUTH_TEST_DATABASE_NAME,
    AUTH_TEST_DATABASE_USER: process.env.AUTH_TEST_DATABASE_USER,
    AUTH_TEST_DATABASE_PASSWORD: process.env.AUTH_TEST_DATABASE_PASSWORD,
    AUTH_TEST_DATABASE_MARKER: process.env.AUTH_TEST_DATABASE_MARKER,
    E2E_API_PORT: String(apiPort),
    E2E_WEB_ORIGIN: webOrigin,
    E2E_CONTROL_PORT: String(controlPort),
    E2E_CONTROL_TOKEN: controlToken,
    PYTHONIOENCODING: 'utf-8',
  });
  const child = spawn(python, ['tests/traveler_e2e_server.py'], {
    cwd: backendRoot,
    env: childEnv,
    stdio: ['ignore', 'pipe', 'ignore'],
    windowsHide: true,
  });
  const pipe = makePipe(child);
  const ready = await pipe.next(25_000);
  if (!ready?.ok || ready.event !== 'ready') {
    child.kill();
    throw new Error('guarded_api_start_failed');
  }
  return { child, pipe, controlPort, controlToken };
}

async function startWeb() {
  const vite = resolve(root, 'frontend/node_modules/vite/bin/vite.js');
  if (!existsSync(vite)) throw new Error('frontend_dependencies_missing');
  const server = spawn(process.execPath, [vite, '--host', '127.0.0.1', '--port', String(webPort), '--strictPort'], {
    cwd: resolve(root, 'frontend'),
    env: runtimeEnv({ VITE_API_PROXY_TARGET: apiTarget }),
    stdio: 'ignore',
    windowsHide: true,
  });
  let ready = false;
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (server.exitCode !== null) break;
    try {
      const [page, viteClient] = await Promise.all([fetch(webOrigin), fetch(`${webOrigin}/@vite/client`)]);
      ready = page.ok && viteClient.ok && (await viteClient.text()).includes('createHotContext');
    } catch { /* server is starting */ }
    if (ready) break;
    if (server.exitCode !== null) break;
    await new Promise(resolvePromise => setTimeout(resolvePromise, 250));
  }
  if (!ready) {
    server.kill();
    throw new Error('vite_server_start_failed');
  }
  return server;
}

async function signIn(page, controlPort, controlToken, phone) {
  await page.locator('.auth-entry > button').click();
  await page.locator('#auth-phone').fill(phone);
  await page.locator('.auth-panel button[type="submit"]').click();
  await page.locator('#auth-code').waitFor({ state: 'visible' });
  const { code } = await checkedControl(controlPort, controlToken, { action: 'next_otp' });
  if (!/^\d{6}$/.test(code)) throw new Error('fake_otp_shape_invalid');
  await page.locator('#auth-code').fill(code);
  const verification = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/auth/otp/verify');
  await page.locator('.auth-panel button[type="submit"]').click();
  const response = await verification;
  if (response.status() !== 200 || !response.headers()['cache-control']?.includes('no-store')) {
    throw new Error('otp_verify_failed_or_cached');
  }
  const body = await response.json();
  await page.locator('.auth-signed-in').waitFor({ state: 'visible' });
  if (!body?.user?.user_id || !body?.csrf_token) throw new Error('authenticated_state_missing');
  return { userId: body.user.user_id, csrfToken: body.csrf_token };
}

async function apiStatus(page, path, method, headers = {}, body) {
  return page.evaluate(async ({ path, method, headers, body }) => {
    const response = await fetch(path, {
      method,
      credentials: 'same-origin',
      headers: { ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...headers },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    return response.status;
  }, { path, method, headers, body });
}

async function apiRequestStatus(page, path, method, headers = {}, body) {
  const response = await page.request.fetch(`${webOrigin}${path}`, {
    method,
    headers,
    ...(body === undefined ? {} : { data: body }),
  });
  return response.status();
}

async function waitForRequest(page, predicate, timeout = 20_000) {
  return page.waitForResponse(predicate, { timeout });
}

function reportResponseWaitCallsite(page) {
  const waitForResponse = page.waitForResponse.bind(page);
  page.waitForResponse = (predicate, options) => {
    const line = new Error().stack?.split('\n')[2]?.match(/:(\d+):\d+\)?$/)?.[1] ?? 'unknown';
    return waitForResponse(predicate, options).catch(() => {
      throw new Error(`browser_response_wait_timeout_line_${line}`);
    });
  };
}

const localeCopy = {
  'fa-IR': {
    workspace: 'برنامه‌های سفر من',
    confirm: 'ذخیرهٔ تغییرات برداشت سفر',
    find: 'بررسی پیشنهادهای تأییدشده',
    deleteTrip: 'حذف سفر',
    deleteConversation: 'حذف گفت‌وگو و همهٔ سفرهای آن',
    prompt: 'سفر ۱۵ روزه به شیراز با بودجهٔ ۲۰ میلیون تومان؛ به طبیعت و جاهای تاریخی علاقه دارم؛ ترجیح می‌دهم مسیرها سنگ‌فرش باشند؛ دسترسی ویلچر ضروری است؛ باید از مسیرهای ناهموار پرهیز شود.',
    accessLabel: 'دسترس‌پذیری',
    softPreference: 'مسیرهای سنگ‌فرش باشد',
    fixtureName: 'نمونهٔ آزمایشی',
  },
  'en-US': {
    workspace: 'My travel plans',
    confirm: 'Save trip details',
    find: 'Check verified suggestions',
    deleteTrip: 'Delete trip',
    deleteConversation: 'Delete conversation and all its trips',
    prompt: '10 day trip to Shiraz with a budget of 20 million IRR; I prefer paved paths; wheelchair access is essential; must avoid rough terrain.',
    accessLabel: 'Accessibility',
    softPreference: 'paved paths',
    fixtureName: 'Test fixture',
  },
  ar: {
    workspace: 'خطط رحلاتي',
    confirm: 'احفظ تفاصيل الرحلة',
    find: 'تحقق من الاقتراحات الموثقة',
    deleteTrip: 'احذف الرحلة',
    deleteConversation: 'احذف المحادثة وكل رحلاتها',
    prompt: 'رحلة لمدة ١٠ أيام إلى شيراز بميزانية ٢٠ مليون درهم؛ أفضل المسارات المعبدة؛ إمكانية الوصول بالكراسي المتحركة ضرورية؛ يجب تجنب الطرق الوعرة.',
    accessLabel: 'إمكانية الوصول',
    softPreference: 'المسارات المعبدة',
    fixtureName: 'نموذج اختباري',
  },
};

function attachBrowserGuards(page, audit) {
  page.on('pageerror', () => { audit.pageErrors += 1; });
  page.on('response', response => {
    if (new URL(response.url()).origin !== webOrigin && response.status() >= 200 && response.status() < 400) {
      audit.successfulExternalResponses += 1;
    }
  });
  return page.route('**/*', route => {
    if (new URL(route.request().url()).origin !== webOrigin) {
      audit.externalRequests += 1;
      return route.abort();
    }
    return route.continue();
  });
}

async function selectAndVerifyLocale(page, locale) {
  await page.locator('#locale').selectOption(locale);
  await page.waitForFunction(expected => document.documentElement.lang === expected, locale);
  const actual = await page.evaluate(() => ({
    lang: document.documentElement.lang,
    pageDirection: document.documentElement.dir,
    workspace: document.querySelector('.traveler-workspace-heading .eyebrow')?.textContent?.trim(),
  }));
  if (actual.lang !== locale || actual.pageDirection !== (locale === 'en-US' ? 'ltr' : 'rtl')) {
    throw new Error(`locale_page_direction_${locale}`);
  }
  if (actual.workspace !== localeCopy[locale].workspace) throw new Error(`locale_copy_missing_${locale}`);
}

async function sanitizeAndCapture(page, path, locale, width, height) {
  await page.setViewportSize({ width, height });
  // Replace traveler-authored text only in the captured DOM. The live journey
  // and API assertions happen before this visual redaction.
  const hiddenSensitiveStyles = await page.evaluate(() => {
    const sensitive = [
      ...document.querySelectorAll('#trip-prompt, .trip-summary, .saved-message-user p, .history-trip > button:first-child, .auth-signed-in span'),
    ];
    const styles = sensitive.map(node => node.getAttribute('style'));
    sensitive.forEach(node => { node.style.visibility = 'hidden'; });
    return styles;
  });
  const originalText = await page.evaluate(title => {
    const heading = document.querySelector('#traveler-workspace-title');
    const targets = [
      ...(heading ? [heading] : []),
      ...document.querySelectorAll('.auth-signed-in span'),
      ...document.querySelectorAll('.saved-message-user p'),
      ...document.querySelectorAll('.history-trip > button:first-child'),
      ...document.querySelectorAll('.trip-summary dd'),
    ];
    const values = targets.map(node => node.textContent ?? '');
    const formControls = [...document.querySelectorAll('input:not([type="number"]), textarea')];
    const formValues = formControls.map(node => node.value);
    if (heading) heading.textContent = title;
    document.querySelectorAll('.auth-signed-in span').forEach(node => { node.textContent = title; });
    document.querySelectorAll('.saved-message-user p').forEach(node => { node.textContent = title; });
    document.querySelectorAll('.history-trip > button:first-child').forEach(node => { node.textContent = title; });
    formControls.forEach(node => { node.value = ''; });
    return { text: values, formValues };
  }, localeCopy[locale].workspace);
  await page.screenshot({ path, fullPage: true, animations: 'disabled' });
  await page.evaluate(saved => {
    const targets = [
      ...document.querySelectorAll('#traveler-workspace-title'),
      ...document.querySelectorAll('.auth-signed-in span'),
      ...document.querySelectorAll('.saved-message-user p'),
      ...document.querySelectorAll('.history-trip > button:first-child'),
      ...document.querySelectorAll('.trip-summary dd'),
    ];
    targets.forEach((node, index) => { node.textContent = saved.text[index] ?? ''; });
    [...document.querySelectorAll('input:not([type="number"]), textarea')]
      .forEach((node, index) => { node.value = saved.formValues[index] ?? ''; });
  }, originalText);
  await page.evaluate(styles => {
    const sensitive = [
      ...document.querySelectorAll('#trip-prompt, .trip-summary, .saved-message-user p, .history-trip > button:first-child, .auth-signed-in span'),
    ];
    sensitive.forEach((node, index) => {
      const previous = styles[index];
      if (previous === null) node.removeAttribute('style');
      else node.setAttribute('style', previous);
    });
  }, hiddenSensitiveStyles);
}

function fixtureRecommendation(tripId, tripVersion, locale) {
  const requestId = randomUUID();
  const items = Array.from({ length: 4 }, (_, index) => {
    const destinationId = String(9_100_001 + index);
    const sourceId = 99_001 + index;
    const name = `${localeCopy[locale].fixtureName} ${index + 1}`;
    return {
      recommendation_id: randomUUID(),
      destination_id: destinationId,
      rank: index + 1,
      final_score: 0,
      matched_requirements: [],
      unknown_fields: ['opening_hours', 'price', 'accessibility'],
      warnings: ['test_fixture_only', 'ranking_is_structured_match_not_quality_score'],
      explanation_key: 'published_area_candidate',
      explanation_by_locale: {
        'fa-IR': 'نمونهٔ صرفاً آزمایشی؛ دادهٔ واقعی یا منتشرشده نیست.',
        'en-US': 'Test-only fixture; not real or published content.',
        ar: 'نموذج للاختبار فقط؛ ليس محتوى حقيقيًا أو منشورًا.',
      },
      score_components: [],
      evidence: [{
        source_id: sourceId,
        source_name: 'TEST FIXTURE SOURCE — NOT A REAL SOURCE',
        source_url: `https://example.test/task32/${sourceId}`,
        source_role: 'test_fixture_only',
        evidence_note: 'Synthetic test fixture; excluded from production views.',
        retrieved_at: null,
        valid_from: null,
        valid_until: null,
        reliability_score: null,
      }],
      canonical_name: name,
      localized_names: { 'fa-IR': name, 'en-US': name, ar: name },
      city_name: null,
      province_name: 'TEST FIXTURE ONLY',
      destination_type: 'synthetic_fixture',
    };
  });
  return {
    recommendation_request_id: requestId,
    status: 'available',
    reason_code: null,
    algorithm_version: 'task32-test-fixture-only-v1',
    retrieval_version: 'isolated-test-fixture-only-v1',
    trip_version: tripVersion,
    unresolved_fields: [],
    requirement_assessments: [{ field: 'budget', decision: 'advisory', status: 'not_evaluated', reason_code: 'budget_unverifiable' }],
    waived_fields: ['budget'],
    not_evaluated_fields: ['budget'],
    items,
    test_fixture_only: true,
    trip_id: tripId,
  };
}

function fixtureItinerary(tripId, recommendation, itineraryId = randomUUID(), dayCount = 10) {
  const stops = recommendation.items.map((item, index) => ({
    itinerary_stop_id: randomUUID(),
    recommendation_id: item.recommendation_id,
    destination_id: item.destination_id,
    day_number: index + 1,
    stop_order: 1,
    notes_by_locale: {},
    canonical_name: item.canonical_name,
    localized_names: item.localized_names,
  }));
  return {
    itinerary_id: itineraryId,
    trip_id: tripId,
    recommendation_request_id: recommendation.recommendation_request_id,
    version: 1,
    revision: 1,
    day_count: dayCount,
    status: 'partial',
    unplanned_days: Array.from({ length: dayCount - 4 }, (_, index) => index + 5),
    title_by_locale: { 'fa-IR': 'نمونهٔ برنامه', 'en-US': 'Test fixture itinerary', ar: 'خطة اختبارية' },
    stops,
    updated_at: new Date().toISOString(),
    test_fixture_only: true,
  };
}

async function runPartialFixture(page, locale, tripId, tripVersion, screenshotRoot, dayCount = 10) {
  const recommendation = fixtureRecommendation(tripId, tripVersion, locale);
  const itineraryId = randomUUID();
  let current = fixtureItinerary(tripId, recommendation, itineraryId, dayCount);
  let updateBody = null;
  await page.route(`${webOrigin}/api/v1/trips/${tripId}/recommendations`, async route => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(recommendation) });
    } else await route.continue();
  });
  await page.route(`${webOrigin}/api/v1/trips/${tripId}/itineraries`, async route => {
    if (route.request().method() === 'POST') {
      const request = route.request().postDataJSON();
      if (request.day_count !== dayCount) throw new Error('fixture_itinerary_day_count_mismatch');
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(current) });
    } else await route.continue();
  });
  await page.route(`${webOrigin}/api/v1/itineraries/${itineraryId}`, async route => {
    const method = route.request().method();
    if (method === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(current) });
    } else if (method === 'PUT') {
      updateBody = route.request().postDataJSON();
      if (updateBody.expected_revision !== 1 || updateBody.stops.length !== 3) {
        throw new Error('fixture_edit_revision_or_stop_count_invalid');
      }
      const byId = new Map(current.stops.map(stop => [stop.recommendation_id, stop]));
      current = {
        ...current,
        revision: 2,
        stops: updateBody.stops.map((stop, index) => ({
          ...byId.get(stop.recommendation_id),
          day_number: stop.day_number,
          stop_order: stop.stop_order,
          notes_by_locale: stop.notes_by_locale,
          itinerary_stop_id: randomUUID(),
        })),
      };
      const planned = new Set(current.stops.map(stop => stop.day_number));
      current.unplanned_days = Array.from({ length: dayCount }, (_, index) => index + 1).filter(day => !planned.has(day));
      current.status = current.unplanned_days.length ? 'partial' : 'complete';
      current.updated_at = new Date().toISOString();
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(current) });
    } else await route.continue();
  });

  await page.getByRole('button', { name: localeCopy[locale].find }).click();
  await page.locator('.itinerary-start').waitFor({ state: 'visible' });
  await page.locator('#journey-day-count').fill(String(dayCount));
  await page.locator('.itinerary-start button').click();
  await page.locator('.saved-itinerary-days .itinerary-day').nth(dayCount - 1).waitFor({ state: 'visible' });
  if (await page.locator('.saved-itinerary-days .itinerary-day').count() !== dayCount) throw new Error('fixture_requested_days_not_rendered');
  const localizedLastDay = await page.locator(`#itinerary-day-${dayCount}`).textContent();
  const formattedLastDay = await page.evaluate(({ localeValue, value }) => new Intl.NumberFormat(localeValue, {
    numberingSystem: localeValue === 'ar' ? 'arab' : localeValue === 'fa-IR' ? 'arabext' : 'latn',
  }).format(value), { localeValue: locale, value: dayCount });
  if (!localizedLastDay?.includes(formattedLastDay)) throw new Error(`itinerary_day_number_not_localized_${locale}`);
  if (await page.locator('.saved-stop').count() !== 4 || await page.locator('.unplanned-day').count() !== dayCount - 4) {
    throw new Error('fixture_four_stops_unplanned_day_count_mismatch');
  }
  if ((await page.locator('.itinerary-coverage').textContent())?.trim() === '') throw new Error('fixture_partial_status_missing');

  const firstStop = current.stops[0];
  await page.locator(`#stop-day-${firstStop.recommendation_id}`).selectOption('5');
  await page.locator('.saved-stop').nth(1).locator('.stop-actions button').last().click();
  await sanitizeAndCapture(page, resolve(screenshotRoot, `partial-${locale}-390.png`), locale, 390, 844);
  await sanitizeAndCapture(page, resolve(screenshotRoot, `partial-${locale}-1440.png`), locale, 1440, 1000);
  const savedEditResponse = page.waitForResponse(response => new URL(response.url()).pathname === `/api/v1/itineraries/${itineraryId}`
    && response.request().method() === 'PUT');
  await page.locator('.saved-itinerary > button').last().click();
  const savedEdit = await savedEditResponse;
  const savedEditBody = await savedEdit.json();
  if (savedEdit.status() !== 200 || savedEditBody.revision !== 2 || savedEditBody.day_count !== dayCount) {
    throw new Error('fixture_edit_response_revision_or_duration_failed');
  }
  if (!updateBody || updateBody.expected_revision !== 1 || updateBody.stops.length !== 3
    || !updateBody.stops.some(stop => stop.recommendation_id === firstStop.recommendation_id && stop.day_number === 5)
    || current.day_count !== dayCount || current.revision !== 2 || current.status !== 'partial') {
    throw new Error('fixture_edit_save_revision_or_duration_failed');
  }
}

// Browser -> real authenticated assistant endpoint -> durable PostgreSQL rows.
// Only the external LLM is simulated by the guarded API server dependency.
// The candidate is deliberately unverified and MUST NOT change the trip.
async function appendPersianFollowUp(page, conversationId, tripId, content) {
  await page.locator('#trip-follow-up').fill(content);
  const path = `/api/v1/conversations/${conversationId}/messages`;
  const responsePending = page.waitForResponse(response =>
    new URL(response.url()).pathname === path && response.request().method() === 'POST');
  await page.locator('#trip-follow-up + button').click();
  const response = await responsePending;
  const body = await response.json();
  if (response.status() !== 201 || !response.headers()['cache-control']?.includes('no-store')
      || body.trip?.original_request !== localeCopy['fa-IR'].prompt
      || body.message?.content !== content) {
    throw new Error('persian_follow_up_not_persisted_or_original_request_changed');
  }
  return body;
}

async function verifySimulatedAssistant(page, api, locale, conversationId, tripId, csrf, expectedTripVersion, expectedConversationVersion, expectedDuration) {
  const before = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_count' });
  const assistantButton = page.locator('.assistant-controls > button');
  if (await assistantButton.isEnabled()) throw new Error('assistant_without_remote_consent_enabled');
  const noConsentStatus = await apiStatus(page,
    '/api/v1/conversations/' + conversationId + '/assistant-turns', 'POST',
    { 'X-CSRF-Token': csrf }, {
      trip_id: tripId, content: 'Unauthorized provider processing',
      idempotency_key: randomUUID(), expected_version: expectedConversationVersion,
      remote_processing_consent: false,
    });
  if (noConsentStatus !== 422) throw new Error('assistant_without_consent_api_not_rejected');
  const afterNoConsent = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_count' });
  if (afterNoConsent.count !== before.count) throw new Error('assistant_gateway_called_without_consent');
  const prompt = {
    'fa-IR': 'برای این سفر یک پیشنهاد آزمایشی بده.',
    'en-US': 'Give an example suggestion for this trip.',
    ar: 'أعطني اقتراحا تجريبيا لهذه الرحلة.',
  }[locale];
  await page.locator('#trip-follow-up').fill(prompt);
  await page.locator('#assistant-remote-consent').check();
  const path = '/api/v1/conversations/' + conversationId + '/assistant-turns';
  const responsePending = page.waitForResponse(response =>
    new URL(response.url()).pathname === path && response.request().method() === 'POST');
  await assistantButton.click();
  const response = await responsePending;
  const body = await response.json();
  if (response.status() !== 200 || !response.headers()['cache-control']?.includes('no-store')
      || body.replayed || body.candidate_requirements?.destination !== 'Kashan'
      || body.candidate_requirements?.duration_days !== 2
      || body.trip?.version !== expectedTripVersion
      || Object.keys(body.trip?.confirmed_requirements ?? {}).length !== 0) {
    throw new Error('simulated_assistant_endpoint_or_trip_invariant_failed_' + locale);
  }
  await page.locator('.saved-message-assistant p').waitFor({ state: 'visible' });
  await page.locator('.assistant-candidate').waitFor({ state: 'visible' });
  if (await page.locator('#profile-duration').inputValue() !== String(expectedDuration)) {
    throw new Error('assistant_changed_profile_without_confirmation_' + locale);
  }
  const stored = await page.request.get(webOrigin + '/api/v1/conversations/' + conversationId);
  const conversation = await stored.json();
  const saved = conversation.messages?.filter(m => m.role === 'assistant' && m.trip_id === tripId);
  if (stored.status() !== 200 || saved?.length !== 1
      || saved[0].candidate_requirements?.destination !== 'Kashan'
      || saved[0].candidate_requirements?.duration_days !== 2
      || 'metadata' in saved[0]) {
    throw new Error('assistant_advisory_not_reopenable_or_metadata_exposed_' + locale);
  }
  // Same idempotency key must replay durable state, not call the simulated
  // gateway again or create another assistant message.
  const originalRequest = response.request().postDataJSON();
  const replay = await page.evaluate(async ({ path, payload, csrfToken }) => {
    const result = await fetch(path, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
      body: JSON.stringify(payload),
    });
    const data = await result.json();
    return { status: result.status, replayed: data.replayed,
      tripVersion: data.trip?.version, messageId: data.message?.message_id };
  }, { path, payload: originalRequest, csrfToken: csrf });
  const after = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_count' });
  if (replay.status !== 200 || !replay.replayed || replay.tripVersion !== expectedTripVersion
      || replay.messageId !== body.message?.message_id || after.count !== before.count + 1) {
    throw new Error('simulated_assistant_idempotency_or_call_budget_failed_' + locale);
  }
  const profileBeforeDismissal = await page.locator('#profile-duration').inputValue();
  await page.locator('.assistant-candidate button').last().click(); // Reject suggestion.
  if (await page.locator('.assistant-candidate').count() !== 0
      || await page.locator('#profile-duration').inputValue() !== profileBeforeDismissal) {
    throw new Error('assistant_suggestion_dismissal_mutated_profile_' + locale);
  }

  // A second explicitly consented simulated turn provides a bounded candidate
  // that the traveler applies only to the editable draft; confirmation remains
  // gated until the profile and requirement decisions are reviewed.
  const secondPrompt = locale === 'fa-IR'
    ? 'این پیشنهاد را فقط برای بررسی نشان بده و اطلاعات قطعی سفر را تغییر نده.'
    : 'Show another suggestion for review without changing confirmed trip details.';
  await page.locator('#trip-follow-up').fill(secondPrompt);
  const secondPending = page.waitForResponse(response =>
    new URL(response.url()).pathname === path && response.request().method() === 'POST');
  await assistantButton.click();
  const secondResponse = await secondPending;
  const secondBody = await secondResponse.json();
  if (secondResponse.status() !== 200 || secondBody.trip?.version !== expectedTripVersion
      || secondBody.candidate_requirements?.duration_days !== 2) {
    throw new Error('second_simulated_assistant_turn_invalid_' + locale);
  }
  await page.locator('.assistant-candidate button').first().click(); // Apply only as an editable suggestion.
  const confirmButton = page.getByRole('button', { name: localeCopy[locale].confirm });
  if (await page.locator('#profile-duration').inputValue() !== '2' || await confirmButton.isEnabled()) {
    throw new Error('applied_ai_suggestion_bypassed_profile_review_' + locale);
  }
  await page.locator('#profile-duration').fill(String(expectedDuration));
  const destinationByLocale = { 'fa-IR': 'شیراز', 'en-US': 'Shiraz', ar: 'شيراز' };
  await page.locator('#profile-destination-0').fill(destinationByLocale[locale]);
  if (locale === 'fa-IR') {
    if (await page.locator('#profile-duration').inputValue() !== '15'
        || await page.locator('#profile-travelers').inputValue() !== '4'
        || !((await page.locator('#profile-budget').inputValue()).includes('45'))
        || !(await page.locator('#profile-budget').inputValue()).includes('تومان')
        || await confirmButton.isEnabled()) {
      throw new Error('traveler_correction_or_confirmation_gate_failed_fa-IR');
    }
  } else if (await page.locator('#profile-duration').inputValue() !== String(expectedDuration)
      || await confirmButton.isEnabled()) {
    throw new Error(`traveler_duration_restore_or_confirmation_gate_failed_${locale}`);
  }
  const finalCallCount = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_count' });
  if (finalCallCount.count !== before.count + 2) throw new Error('simulated_gateway_call_budget_not_two_' + locale);
  return true;
}

async function runLocaleJourney(browser, api, locale, audit, artifactRoot) {
  const copy = localeCopy[locale];
  const phones = [syntheticPhone(), syntheticPhone()];
  let safeToCleanup = false;
  let contextA;
  let contextB;
  let pageA;
  let pageB;
  let ownerA;
  let csrfA;
  let ownerB;
  let csrfB;
  let tripId;
  let conversationId;
  let conversationVersion;
  let firstTripResponseBody;
  let firstTripVersion;
  let noStoreMe = false;
  let localeChecks = false;
  let consentSnapshotVerified = false;
  let emptyResultVerified = false;
  let productionCatalogueCount = null;
  let recommendationOutcome = null;
  let recommendationReasonCode = null;
  let unresolvedFields = [];
  let correctedPersistedDurationDays = null;
  let ownerAndCsrfVerified = false;
  let deletionVerified = false;

  try {
    const unusedPhones = await checkedControl(api.controlPort, api.controlToken, {
      action: 'assert_phones_unused', phones,
    });
    if (!unusedPhones.ok) throw new Error(`synthetic_test_identity_collision_${locale}`);
    safeToCleanup = true;
    contextA = await browser.newContext({ locale });
    pageA = await contextA.newPage();
    reportResponseWaitCallsite(pageA);
    await attachBrowserGuards(pageA, audit);
    await pageA.goto(webOrigin, { waitUntil: 'domcontentloaded' });
    await selectAndVerifyLocale(pageA, locale);

    const destinations = await pageA.request.get(`${webOrigin}/api/v1/catalog/destinations`, { timeout: 10_000 });
    const emptyCatalogue = await destinations.json();
    if (destinations.status() !== 200 || emptyCatalogue.count !== 0 || emptyCatalogue.status !== 'available') {
      throw new Error(`production_catalogue_not_honestly_empty_${locale}`);
    }
    productionCatalogueCount = emptyCatalogue.count;
    const culinaryResponse = await pageA.request.get(
      `${webOrigin}/api/v1/catalog/culinary?locale=${encodeURIComponent(locale)}`,
      { timeout: 10_000 },
    );
    const culinaryCatalogue = await culinaryResponse.json();
    if (culinaryResponse.status() !== 200 || culinaryCatalogue.status !== 'available'
      || culinaryCatalogue.count !== 0 || culinaryCatalogue.items?.length !== 0) {
      throw new Error(`pending_culinary_content_leaked_${locale}`);
    }

    const identityA = await signIn(pageA, api.controlPort, api.controlToken, phones[0]);
    ownerA = identityA.userId;
    csrfA = identityA.csrfToken;
    const meResponse = pageA.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/auth/me' && response.request().method() === 'GET');
    await pageA.reload({ waitUntil: 'domcontentloaded' });
    await pageA.locator('.auth-signed-in').waitFor({ state: 'visible' });
    noStoreMe = (await meResponse).headers()['cache-control']?.includes('no-store') === true;
    if (!noStoreMe) throw new Error(`auth_me_cache_policy_missing_${locale}`);
    const storageKeys = await pageA.evaluate(() => Object.keys(localStorage).map(key => key.toLowerCase()));
    if (storageKeys.some(key => key.includes('token') || key.includes('session') || key.includes('csrf'))) {
      throw new Error(`credential_in_browser_storage_${locale}`);
    }

    await pageA.locator('#trip-prompt').fill(copy.prompt);
    const inputDirection = await pageA.locator('#trip-prompt').evaluate(element => getComputedStyle(element).direction);
    if (inputDirection !== (locale === 'en-US' ? 'ltr' : 'rtl')) throw new Error(`locale_input_direction_${locale}`);
    await pageA.locator('.trip-form button[type="submit"]').click();
    await pageA.locator('.journey-action').waitFor({ state: 'visible' });
    const persist = pageA.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/conversations'
      && response.request().method() === 'POST');
    await pageA.locator('.journey-action').click();
    const persisted = await persist;
    firstTripResponseBody = await persisted.json();
    tripId = firstTripResponseBody?.trip?.trip_id;
    conversationId = firstTripResponseBody?.conversation?.conversation_id;
    conversationVersion = firstTripResponseBody?.conversation?.version;
    if (persisted.status() !== 201 || !tripId || !conversationId
      || firstTripResponseBody.trip.original_request !== copy.prompt) {
      throw new Error(`conversation_trip_persistence_failed_${locale}_${persisted.status()}`);
    }
    const initialDuration = locale === 'fa-IR' ? 15 : 10;
    let assistantTripVersion = firstTripResponseBody.trip.version;
    let assistantConversationVersion = firstTripResponseBody.conversation.version;
    const initialTripRead = await pageA.request.get(`${webOrigin}/api/v1/trips/${tripId}`);
    const initialTripRecord = await initialTripRead.json();
    if (initialTripRead.status() !== 200
        || initialTripRecord.extracted_requirements?.durationDays?.value !== initialDuration
        || await pageA.locator('#profile-duration').inputValue() !== String(initialDuration)) {
      throw new Error(`persisted_initial_duration_mismatch_${locale}_${initialDuration}`);
    }
    if (locale === 'fa-IR') {
      const corrections = [
        'مدت سفر را دوازده روز کنید؛ چهار نفر هستیم و بودجه ۳۰ میلیون تومان است.',
        'اصلاح نهایی: مدت سفر پانزده روز است و بودجه ۴۵ میلیون تومان؛ ما چهار نفر هستیم.',
        ...Array.from({ length: 10 }, (_, index) =>
          `برای همان سفر پانزده‌روزه به شیراز، اطلاعات پیشین را نگه دارید؛ ادامهٔ گفت‌وگو ${index + 1}.`),
      ];
      let latest;
      for (const turn of corrections) {
        latest = await appendPersianFollowUp(pageA, conversationId, tripId, turn);
      }
      const correctedTripRead = await pageA.request.get(`${webOrigin}/api/v1/trips/${tripId}`);
      const correctedTrip = await correctedTripRead.json();
      const extracted = correctedTrip.extracted_requirements;
      const budget = extracted?.budget?.value;
      const accessibility = extracted?.accessibility?.value ?? [];
      const constraints = extracted?.constraints?.value ?? [];
      const persistedConversation = await pageA.request.get(`${webOrigin}/api/v1/conversations/${conversationId}`);
      const persistedMessages = await persistedConversation.json();
      if (correctedTripRead.status() !== 200 || correctedTrip.original_request !== copy.prompt
          || extracted?.durationDays?.value !== 15 || extracted?.travelerCount?.value !== 4
          || !budget?.raw?.includes('45') || !budget.raw.includes('تومان')
          || !budget.unit?.includes('تومان') || budget.currency !== null
          || !accessibility.includes('wheelchair_access')
          || !constraints.some(value => /rough|terrain|ناهموار/iu.test(value))
          || persistedConversation.status() !== 200
          || persistedMessages.messages?.filter(message => message.role === 'user').length < 13
          || latest?.trip?.extracted_requirements?.durationDays?.value !== 15) {
        throw new Error('persian_15_day_corrections_or_long_history_not_persisted');
      }
      correctedPersistedDurationDays = extracted.durationDays.value;
      if (await pageA.locator('#profile-duration').inputValue() !== '15'
          || await pageA.locator('#profile-travelers').inputValue() !== '4'
          || !(await pageA.locator('#profile-budget').inputValue()).includes('45')
          || !(await pageA.locator('#profile-budget').inputValue()).includes('تومان')) {
        throw new Error('persian_corrected_profile_not_visible');
      }
      assistantTripVersion = correctedTrip.version;
      assistantConversationVersion = persistedMessages.version;
      conversationVersion = assistantConversationVersion;
    }
    await pageA.locator('.history-trip > button').first().waitFor({ state: 'visible' });
    const assistantIntegrationVerified = await verifySimulatedAssistant(
      pageA, api, locale, conversationId, tripId, csrfA,
      assistantTripVersion, assistantConversationVersion, initialDuration,
    );
    await pageA.locator('#requirement-consent-budget-advisory').waitFor({ state: 'visible' });
    await pageA.locator('.requirement-accessibility-mandatory').waitFor({ state: 'visible' });
    if (await pageA.locator('#requirement-consent-accessibility-must, #requirement-consent-accessibility-advisory').count() !== 0) {
      throw new Error(`mandatory_access_field_was_offered_consent_downgrade_${locale}`);
    }
    const consentRadio = pageA.locator('#requirement-consent-budget-advisory');
    if (await consentRadio.isChecked()) throw new Error(`advisory_consent_was_preselected_${locale}`);
    const confirmButton = pageA.getByRole('button', { name: copy.confirm });
    if (await confirmButton.isEnabled()) throw new Error(`profile_confirm_enabled_without_explicit_choice_${locale}`);
    await consentRadio.check();
    const advisoryAcknowledgement = pageA.locator('#requirement-consent-budget-ack');
    await advisoryAcknowledgement.check();
    await pageA.locator('#requirement-consent-soft_preference-advisory').check();
    await pageA.locator('#requirement-consent-soft_preference-ack').check();
    // The confirmed profile may also contain explicit dates, party size, or
    // origin. Each is a separate user decision; exercise any rendered choice
    // individually instead of treating the first acknowledgement as a blanket
    // waiver. Safety/access fields are intentionally absent from this list.
    for (const field of ['travel_dates', 'traveler_count', 'origin']) {
      const advisoryChoice = pageA.locator(`#requirement-consent-${field}-advisory`);
      if (await advisoryChoice.count()) {
        if (await advisoryChoice.isChecked()) throw new Error(`advisory_consent_was_preselected_${field}_${locale}`);
        await advisoryChoice.check();
        await pageA.locator(`#requirement-consent-${field}-ack`).check();
      }
    }
    if (await confirmButton.isDisabled()) throw new Error(`explicit_advisory_choice_not_accepted_${locale}`);

    const confirmResponsePromise = pageA.waitForResponse(response => new URL(response.url()).pathname === `/api/v1/trips/${tripId}`
      && response.request().method() === 'PATCH');
    await confirmButton.click();
    const confirmResponse = await confirmResponsePromise;
    if (confirmResponse.status() !== 200) throw new Error(`profile_confirmation_failed_${locale}`);
    const confirmedProfileResponse = await pageA.request.get(`${webOrigin}/api/v1/trips/${tripId}`);
    const confirmedProfile = (await confirmedProfileResponse.json()).confirmed_requirements;
    if (locale === 'fa-IR' && (confirmedProfileResponse.status() !== 200
        || confirmedProfile?.duration_days !== 15 || confirmedProfile?.traveler_count !== 4
        || confirmedProfile?.confirmation_source !== 'traveler_reviewed')) {
      throw new Error('get_trip_did_not_return_confirmed_persian_15_day_profile');
    }
    const confirmedProfileShape = Object.fromEntries(Object.entries(confirmedProfile ?? {}).map(([key, value]) => [
      key,
      key === 'budget' && value && typeof value === 'object'
        ? { keys: Object.keys(value).sort(), currency: value.currency ?? null,
            unitAllowed: ['rial', 'toman', 'irr', 'million rial', 'million toman'].includes(String(value.unit ?? '').trim().toLowerCase()),
            unitLength: typeof value.unit === 'string' ? value.unit.length : null, amountType: typeof value.amount }
        : Array.isArray(value) ? `array:${value.length}` : value === null ? 'null' : typeof value,
    ]));
    const confirmedTrip = await confirmResponse.json();
    firstTripVersion = confirmedTrip.version;
    if (locale === 'fa-IR') {
      const reviewed = confirmedTrip.confirmed_requirements ?? {};
      const reviewedBudget = reviewed.budget;
      if (reviewed.duration_days !== 15 || reviewed.traveler_count !== 4
          || reviewed.confirmation_source !== 'traveler_reviewed'
          || !reviewedBudget?.raw?.includes('45') || !reviewedBudget.raw.includes('تومان')
          || !reviewedBudget.unit?.includes('تومان') || reviewedBudget.currency !== null) {
        throw new Error('confirmed_persian_15_day_profile_or_budget_denomination_changed');
      }
    }
    const persistedConsent = confirmedTrip.confirmed_requirements?.requirement_consent;
    const consentDecisionFields = Object.keys(persistedConsent?.field_decisions ?? {}).sort();
    const acknowledgedConsentFields = [...(persistedConsent?.advisory_acknowledged_fields ?? [])].sort();
    if (persistedConsent?.contract_version !== 'recommendation-consent-v1'
      || persistedConsent?.profile_version !== confirmedTrip.version
      || persistedConsent?.field_decisions?.budget !== 'advisory'
      || persistedConsent?.field_decisions?.soft_preference !== 'advisory'
      || Object.values(persistedConsent?.field_decisions ?? {}).some(decision => decision !== 'advisory')
      || consentDecisionFields.join(',') !== acknowledgedConsentFields.join(',')
      || !persistedConsent?.advisory_acknowledged_fields?.includes('budget')
      || !persistedConsent?.advisory_acknowledged_fields?.includes('soft_preference')) {
      throw new Error(`server_bound_consent_snapshot_missing_${locale}`);
    }
    consentSnapshotVerified = true;
    if (await pageA.locator('.requirement-unclassified').count() !== 1) {
      throw new Error(`unclassified_hard_requirement_not_disclosed_${locale}`);
    }
    if (await pageA.locator('.requirement-accessibility-mandatory').count() !== 1) {
      throw new Error(`accessibility_mandatory_notice_missing_${locale}`);
    }

    const recommendationResponsePromise = pageA.waitForResponse(response => new URL(response.url()).pathname === `/api/v1/trips/${tripId}/recommendations`
      && response.request().method() === 'POST');
    await pageA.getByRole('button', { name: copy.find }).click();
    const recommendationResponse = await recommendationResponsePromise;
    const recommendation = await recommendationResponse.json();
    const budgetAssessment = recommendation.requirement_assessments?.find(item => item.field === 'budget');
    const preferenceAssessment = recommendation.requirement_assessments?.find(item => item.field === 'soft_preference');
    const accessibilityAssessment = recommendation.requirement_assessments?.find(item => item.field === 'accessibility');
    const hardConstraintAssessment = recommendation.requirement_assessments?.find(item => item.field === 'hard_constraint');
    if (recommendationResponse.status() !== 201 || !recommendationResponse.headers()['cache-control']?.includes('no-store')
      || recommendation.status !== 'needs_confirmation' || recommendation.reason_code !== 'hard_constraints_unverifiable'
      || !recommendation.waived_fields?.includes('budget') || !recommendation.not_evaluated_fields?.includes('budget')
      || !recommendation.waived_fields?.includes('soft_preference') || !recommendation.not_evaluated_fields?.includes('soft_preference')
      || [...recommendation.waived_fields].sort().join(',') !== consentDecisionFields.join(',')
      || [...recommendation.not_evaluated_fields].sort().join(',') !== consentDecisionFields.join(',')
      || recommendation.requirement_assessments?.some(item => consentDecisionFields.includes(item.field)
        && (item.decision !== 'advisory' || item.status !== 'not_evaluated'))
      || budgetAssessment?.decision !== 'advisory' || budgetAssessment.status !== 'not_evaluated'
      || preferenceAssessment?.decision !== 'advisory' || preferenceAssessment.status !== 'not_evaluated'
      || preferenceAssessment.reason_code !== 'preference_unverifiable'
      || accessibilityAssessment?.decision !== 'must_have' || accessibilityAssessment.status !== 'unresolved'
      || !['access_unverifiable', 'accessibility_unverifiable'].includes(accessibilityAssessment.reason_code)
      || hardConstraintAssessment?.decision !== 'must_have' || hardConstraintAssessment.status !== 'unresolved'
      || !recommendation.unresolved_fields?.includes('hard_constraint') || recommendation.items?.length !== 0) {
      throw new Error(`empty_or_advisory_result_contract_failed_${locale}_${JSON.stringify({
        http: recommendationResponse.status(), status: recommendation.status,
        reason: recommendation.reason_code, waived: recommendation.waived_fields,
        notEvaluated: recommendation.not_evaluated_fields,
        assessments: recommendation.requirement_assessments?.map(item => [item.field, item.decision, item.status, item.reason_code]),
        unresolved: recommendation.unresolved_fields,
        profileShape: confirmedProfileShape,
      })}`);
    }
    // This is a needs_confirmation result because mandatory fields remain
    // unresolved. It is not an empty/no_evidence recommendation response;
    // the independent catalogue read above is what proves the production
    // catalogue has zero approved destinations for this disposable DB.
    recommendationOutcome = recommendation.status;
    recommendationReasonCode = recommendation.reason_code;
    unresolvedFields = [...recommendation.unresolved_fields];
    if (await pageA.locator('.itinerary-start').count()) throw new Error(`itinerary_offered_without_eligible_candidate_${locale}`);
    const notEvaluated = pageA.locator('.not-evaluated-warning');
    await notEvaluated.waitFor({ state: 'visible' });
    const warningText = await notEvaluated.textContent();
    const localizedBudget = { 'fa-IR': 'بودجه', 'en-US': 'Budget', ar: 'الميزانية' }[locale];
    if (!warningText?.includes(localizedBudget)) throw new Error(`advisory_warning_not_localized_${locale}`);
    const unresolved = pageA.locator('.unresolved-requirements');
    await unresolved.waitFor({ state: 'visible' });
    const unresolvedCopy = await unresolved.textContent();
    if (await unresolved.locator('li').count() < 2 || !unresolvedCopy?.includes(copy.accessLabel)) {
      throw new Error(`mandatory_access_and_hard_constraint_not_exposed_${locale}`);
    }
    emptyResultVerified = true;

    const reloadMe = pageA.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/auth/me'
      && response.request().method() === 'GET');
    await pageA.reload({ waitUntil: 'domcontentloaded' });
    await pageA.locator('.auth-signed-in').waitFor({ state: 'visible' });
    if (!(await reloadMe).headers()['cache-control']?.includes('no-store')) throw new Error(`auth_me_not_no_store_${locale}`);
    await pageA.locator('.history-trip > button').first().click();
    // The initial request and the assistant follow-up are two distinct user
    // messages. Check both explicitly instead of waiting on an ambiguous
    // multi-element locator (Playwright strict mode).
    const savedUserMessages = pageA.locator('.saved-message-user p');
    await savedUserMessages.nth(1).waitFor({ state: 'visible' });
    if (await savedUserMessages.count() < (locale === 'fa-IR' ? 13 : 2)
      || !(await savedUserMessages.first().textContent())?.includes(copy.prompt)) {
      throw new Error(`history_request_not_restored_${locale}`);
    }
    await pageA.locator('.saved-message-assistant button').first().click();
    await pageA.locator('.assistant-candidate').waitFor({ state: 'visible' });
    if (!(await pageA.locator('.assistant-candidate').textContent())?.includes('Kashan')) {
      throw new Error('restored_assistant_candidate_missing_' + locale);
    }
    await pageA.locator('.assistant-candidate button').last().click();
    if (!(await pageA.locator('#requirement-consent-budget-advisory').isChecked())
      || !(await pageA.locator('#requirement-consent-budget-ack').isChecked())
      || !(await pageA.locator('#requirement-consent-soft_preference-advisory').isChecked())
      || !(await pageA.locator('#requirement-consent-soft_preference-ack').isChecked())) {
      throw new Error(`history_consent_not_restored_${locale}`);
    }
    const reopenedTrip = await pageA.request.get(`${webOrigin}/api/v1/trips/${tripId}`);
    const reopenedRecord = await reopenedTrip.json();
    if (reopenedRecord.confirmed_requirements?.requirement_consent?.profile_version !== reopenedRecord.version
      || reopenedRecord.confirmed_requirements?.requirement_consent?.field_decisions?.budget !== 'advisory') {
      throw new Error(`history_consent_version_changed_${locale}`);
    }
    if (await apiStatus(pageA, `/api/v1/trips/${tripId}/recommendations`, 'GET') !== 200) {
      throw new Error(`saved_empty_recommendation_not_reopenable_${locale}`);
    }

    const artifactLocale = resolve(artifactRoot, locale);
    mkdirSync(artifactLocale, { recursive: true });
    await sanitizeAndCapture(pageA, resolve(artifactLocale, `empty-${locale}-390.png`), locale, 390, 844);
    await sanitizeAndCapture(pageA, resolve(artifactLocale, `empty-${locale}-1440.png`), locale, 1440, 1000);

    contextB = await browser.newContext({ locale });
    pageB = await contextB.newPage();
    reportResponseWaitCallsite(pageB);
    await attachBrowserGuards(pageB, audit);
    await pageB.goto(webOrigin, { waitUntil: 'domcontentloaded' });
    await selectAndVerifyLocale(pageB, locale);
    const identityB = await signIn(pageB, api.controlPort, api.controlToken, phones[1]);
    ownerB = identityB.userId;
    csrfB = identityB.csrfToken;
    if (ownerA === ownerB) throw new Error(`test_identities_not_distinct_${locale}`);

    const csrfDenied = await apiStatus(pageB, '/api/v1/conversations', 'POST', {}, {
      locale, request_text: 'CSRF protection probe', extracted_requirements: {}, destination_ids: [],
      idempotency_key: randomUUID(),
    });
    const badOriginDenied = await apiRequestStatus(pageB, `/api/v1/trips/${tripId}`, 'DELETE', {
      Origin: 'https://invalid-origin.example', 'X-CSRF-Token': csrfB,
    });
    const ownerReadDenied = await apiStatus(pageB, `/api/v1/trips/${tripId}`, 'GET');
    const ownerDeleteDenied = await apiStatus(pageB, `/api/v1/trips/${tripId}`, 'DELETE', { 'X-CSRF-Token': csrfB });
    const appendDenied = await apiStatus(pageB, `/api/v1/conversations/${conversationId}/messages`, 'POST', {
      'X-CSRF-Token': csrfB,
    }, {
      trip_id: tripId, content: 'Cross-owner authorization probe', idempotency_key: randomUUID(),
      expected_version: conversationVersion,
    });
    const assistantDenied = await apiStatus(pageB,
      '/api/v1/conversations/' + conversationId + '/assistant-turns', 'POST',
      { 'X-CSRF-Token': csrfB }, {
        trip_id: tripId, content: 'Cross-owner assistant probe',
        idempotency_key: randomUUID(), expected_version: conversationVersion,
        remote_processing_consent: true,
      });
    const conversationDeleteDenied = await apiStatus(pageB, `/api/v1/conversations/${conversationId}`, 'DELETE', {
      'X-CSRF-Token': csrfB,
    });
    if (csrfDenied !== 403 || badOriginDenied !== 403 || ownerReadDenied !== 404 || ownerDeleteDenied !== 404
      || appendDenied !== 404 || assistantDenied !== 404 || conversationDeleteDenied !== 404) {
      throw new Error(`real_http_owner_csrf_boundary_failed_${locale}`);
    }
    ownerAndCsrfVerified = true;

    // A separate, explicitly labeled browser fixture exercises the partial
    // duration editor (15 days in fa-IR; retain the 10-day locale smoke).
    // Its API routes are intercepted in this test process and
    // never write fixture identities or facts into PostgreSQL production views.
    const fixtureDayCount = locale === 'fa-IR' ? 15 : 10;
    await runPartialFixture(pageA, locale, tripId, firstTripVersion, artifactLocale, fixtureDayCount);
    localeChecks = true;
    await pageA.unroute(`${webOrigin}/api/v1/trips/${tripId}/recommendations`);
    await pageA.unroute(`${webOrigin}/api/v1/trips/${tripId}/itineraries`);
    await pageA.unroute(`${webOrigin}/api/v1/itineraries/**`);
    const productionAgain = await pageA.request.get(`${webOrigin}/api/v1/catalog/destinations`);
    const productionAgainBody = await productionAgain.json();
    if (productionAgain.status() !== 200 || productionAgainBody.count !== 0) {
      throw new Error(`ui_fixture_affected_production_catalogue_${locale}`);
    }

    // Add a second trip to the same conversation so trip deletion and
    // conversation deletion are independently exercised in the browser.
    await pageA.locator('.journey-new-actions button').first().click();
    const secondPrompt = `${copy.prompt} — ${locale === 'en-US' ? 'second draft' : locale === 'ar' ? 'مسودة ثانية' : 'پیش‌نویس دوم'}`;
    await pageA.locator('#trip-prompt').fill(secondPrompt);
    await pageA.locator('.trip-form button[type="submit"]').click();
    await pageA.locator('.journey-action').waitFor({ state: 'visible' });
    const secondPersist = pageA.waitForResponse(response => new URL(response.url()).pathname === `/api/v1/conversations/${conversationId}/trips`
      && response.request().method() === 'POST' && response.status() === 201);
    await pageA.locator('.journey-action').click();
    const secondResponse = await secondPersist;
    const secondTrip = await secondResponse.json();
    if (!secondTrip?.trip?.trip_id || secondTrip.conversation.conversation_id !== conversationId) {
      throw new Error(`second_trip_not_persisted_${locale}`);
    }
    const rows = await pageA.locator('.history-trip').evaluateAll(nodes => nodes.map(node => node.querySelector('button')?.textContent?.trim() ?? ''));
    const originalIndex = rows.findIndex(text => text === copy.prompt);
    if (originalIndex < 0) throw new Error(`original_trip_history_missing_${locale}`);
    const originalHistoryRow = pageA.locator('.history-trip').nth(originalIndex);
    pageA.once('dialog', dialog => dialog.accept());
    const tripDeleteResponsePromise = pageA.waitForResponse(response => new URL(response.url()).pathname === `/api/v1/trips/${tripId}`
      && response.request().method() === 'DELETE');
    await originalHistoryRow.getByRole('button', { name: copy.deleteTrip }).click();
    const tripDeleteResponse = await tripDeleteResponsePromise;
    if (tripDeleteResponse.status() < 200 || tripDeleteResponse.status() >= 300
      || await apiStatus(pageA, `/api/v1/trips/${tripId}`, 'GET') !== 404) {
      throw new Error(`trip_delete_not_applied_${locale}_${tripDeleteResponse.status()}`);
    }
    if (await pageA.locator('.history-conversation').count() !== 1) throw new Error(`conversation_removed_with_remaining_trip_${locale}`);
    pageA.once('dialog', dialog => dialog.accept());
    await pageA.locator('.history-conversation').first().getByRole('button', { name: copy.deleteConversation }).click();
    await pageA.waitForFunction(() => document.querySelectorAll('.history-conversation').length === 0);
    if (await apiStatus(pageA, `/api/v1/conversations/${conversationId}`, 'GET') !== 404) {
      throw new Error(`conversation_delete_not_applied_${locale}`);
    }

    // Create one more real owner record immediately before account deletion.
    const accountDeleteCreate = await pageA.evaluate(async ({ localeValue, requestText, csrf }) => {
      const response = await fetch('/api/v1/conversations', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
        body: JSON.stringify({ locale: localeValue, request_text: requestText, extracted_requirements: {},
          destination_ids: [], idempotency_key: crypto.randomUUID() }),
      });
      return response.status;
    }, { localeValue: locale, requestText: copy.prompt, csrf: csrfA });
    if (accountDeleteCreate !== 201) throw new Error(`account_delete_fixture_record_create_failed_${locale}`);
    const accountDeleteStatus = await apiStatus(pageA, '/api/v1/auth/me', 'DELETE', { 'X-CSRF-Token': csrfA });
    if (accountDeleteStatus !== 204 || await apiStatus(pageA, '/api/v1/auth/me', 'GET') !== 401) {
      throw new Error(`account_deletion_or_session_revocation_failed_${locale}`);
    }
    const deletedA = await checkedControl(api.controlPort, api.controlToken, {
      action: 'account_state', user_id: ownerA, phone: phones[0],
    });
    if (deletedA.users || deletedA.sessions || deletedA.trips || deletedA.conversations || deletedA.messages
      || deletedA.otp_challenges || deletedA.verified_phones) {
      throw new Error(`account_data_or_phone_challenge_remained_${locale}`);
    }

    // Logout and reauthentication are checked for the second test identity
    // before account deletion, proving server-side session invalidation.
    await pageB.locator('.auth-signed-in button').first().click();
    await pageB.locator('.auth-entry > button').waitFor({ state: 'visible' });
    if (await apiStatus(pageB, '/api/v1/auth/me', 'GET') !== 401) throw new Error(`logout_did_not_revoke_session_${locale}`);
    const renewedIdentityB = await signIn(pageB, api.controlPort, api.controlToken, phones[1]);
    if (renewedIdentityB.userId !== ownerB) throw new Error(`account_identity_changed_on_relogin_${locale}`);
    if (await apiStatus(pageB, '/api/v1/auth/me', 'DELETE', { 'X-CSRF-Token': renewedIdentityB.csrfToken }) !== 204) {
      throw new Error(`second_account_deletion_failed_${locale}`);
    }
    const deletedB = await checkedControl(api.controlPort, api.controlToken, {
      action: 'account_state', user_id: ownerB, phone: phones[1],
    });
    if (deletedB.users || deletedB.sessions || deletedB.trips || deletedB.conversations || deletedB.messages
      || deletedB.otp_challenges || deletedB.verified_phones) {
      throw new Error(`second_account_data_remained_${locale}`);
    }
    deletionVerified = true;

    return {
      locale, productionCatalogueEmptyVerified: emptyResultVerified,
      productionCatalogueCount,
      recommendationOutcome, recommendationReasonCode, unresolvedFields,
      consentSnapshotVerified,
      requestedDurationDays: initialDuration,
      persistedDurationDays: initialTripRecord.extracted_requirements?.durationDays?.value,
      correctedPersistedDurationDays,
      persistedUserTurnCount: locale === 'fa-IR' ? 13 : 2,
      simulatedAssistantIntegrationVerified: assistantIntegrationVerified,
      simulatedGatewayCalls: 2,
      partialFixtureDays: fixtureDayCount,
      partialFixtureStops: 4,
      partialFixtureUnplannedDays: fixtureDayCount - 4,
      historyReopenVerified: true, ownerAndCsrfVerified, deletionVerified, localeChecks,
      noStoreMe, noStoreVerify: true, externalRequestsBlocked: true,
    };
  } finally {
    if (safeToCleanup) {
      try { await checkedControl(api.controlPort, api.controlToken, { action: 'cleanup_phones', phones }); }
      catch { /* process teardown follows; no test identity is reused */ }
    }
    if (pageB) await pageB.close().catch(() => {});
    if (pageA) await pageA.close().catch(() => {});
    if (contextB) await contextB.close().catch(() => {});
    if (contextA) await contextA.close().catch(() => {});
  }
}

async function main() {
  if (!Number.isInteger(webPort) || !Number.isInteger(apiPort) || webPort < 1024 || apiPort < 1024
    || webPort === 55433 || apiPort === 55433) {
    throw new Error('invalid_or_forbidden_test_ports');
  }
  const runName = `run-${new Date().toISOString().replace(/[:.]/g, '-')}-${process.pid}`;
  const artifactRoot = resolve(root, 'artifacts/visual-qa-task15d', runName);
  if (existsSync(artifactRoot)) throw new Error('task15d_artifact_path_collision');
  mkdirSync(artifactRoot, { recursive: true });
  const audit = { externalRequests: 0, successfulExternalResponses: 0, pageErrors: 0 };
  let api;
  let web;
  let browser;
  try {
    api = await startApi();
    web = await startWeb();
    browser = await chromium.launch({
      executablePath: chrome,
      headless: true,
      // Keep the live browser run viable on Windows CI/dev hosts with a tight
      // process budget while still exercising the real installed Chromium.
      args: ['--disable-gpu', '--renderer-process-limit=2', '--disable-background-networking', '--no-first-run'],
    });
    const results = [];
    for (const locale of ['fa-IR', 'en-US', 'ar']) {
      results.push(await runLocaleJourney(browser, api, locale, audit, artifactRoot));
    }
    if (audit.successfulExternalResponses || audit.pageErrors) throw new Error('external_response_or_browser_runtime_error');
    const report = {
      status: 'passed',
      browser: `Chromium ${browser.version()}`,
      environment: 'live Vite proxy + FastAPI + guarded disposable PostgreSQL 17; fake SMS and simulated Chat gateway (no remote model)',
      locales: results,
      screenshots: [
        ...['fa-IR', 'en-US', 'ar'].flatMap(locale => [
          { locale, width: 390, height: 844, kind: 'live empty production catalogue', path: `${locale}/empty-${locale}-390.png` },
          { locale, width: 1440, height: 1000, kind: 'live empty production catalogue', path: `${locale}/empty-${locale}-1440.png` },
          { locale, width: 390, height: 844, dayCount: locale === 'fa-IR' ? 15 : 10, kind: 'test-only four-stop partial itinerary fixture', path: `${locale}/partial-${locale}-390.png` },
          { locale, width: 1440, height: 1000, dayCount: locale === 'fa-IR' ? 15 : 10, kind: 'test-only four-stop partial itinerary fixture', path: `${locale}/partial-${locale}-1440.png` },
        ]),
      ],
      audit: { externalRequestsBlocked: audit.externalRequests, successfulExternalResponses: 0, browserPageErrors: 0 },
      screenshotPolicy: 'Traveler-authored text is replaced in screenshot-only DOM captures; no phone, OTP, cookie, token, or request text is recorded.',
      fixturePolicy: 'Simulated Chat gateway makes no HTTP requests. The fa-IR 15-day and en-US/ar 10-day partial fixtures are Playwright-intercepted and never written to production views.',
    };
    writeFileSync(resolve(artifactRoot, 'report.json'), `${JSON.stringify(report, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
    console.log(JSON.stringify({ status: report.status, browser: report.browser, locales: results.map(result => result.locale), screenshots: report.screenshots.length, artifactRoot: artifactRoot.replaceAll('\\', '/') }));
  } finally {
    if (browser) await browser.close();
    if (web && web.exitCode === null) web.kill();
    if (api?.child && api.child.exitCode === null) api.child.kill();
    api?.pipe.close();
  }
}
main().catch(error => {
  // Never print exception details that might contain user or provider data.
  console.error(`Traveler E2E failed: ${String(error?.message || 'unknown').replace(/[^a-z0-9_-]/gi, '_').slice(0, 500)}`);
  process.exitCode = 1;
});
