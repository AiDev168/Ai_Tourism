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

function ownerRagConfiguration() {
  const flag = process.env.TOURISM_RAG_ENABLED?.trim().toLowerCase() || '';
  if (!flag || ['0', 'false', 'no', 'off'].includes(flag)) return { enabled: false };
  if (!['1', 'true', 'yes', 'on'].includes(flag)) throw new Error('invalid_owner_rag_opt_in_flag');

  const url = process.env.TOURISM_RAG_API_URL || '';
  const token = process.env.TOURISM_RAG_API_TOKEN || '';
  if (!url || !token || token.trim() !== token || /[\r\n]/.test(token)) {
    throw new Error('owner_rag_opt_in_requires_server_configuration');
  }
  let parsed;
  try { parsed = new URL(url); } catch { throw new Error('owner_rag_url_must_be_fixed_loopback'); }
  if (parsed.protocol !== 'http:' || parsed.hostname !== '127.0.0.1' || parsed.port !== '8765'
      || !['', '/'].includes(parsed.pathname) || parsed.search || parsed.hash
      || parsed.username || parsed.password) {
    throw new Error('owner_rag_url_must_be_fixed_loopback');
  }
  return { enabled: true, url, token };
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
  const ownerRag = ownerRagConfiguration();

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
    TOURISM_RAG_ENABLED: ownerRag.enabled ? 'true' : 'false',
    ...(ownerRag.enabled ? {
      TOURISM_RAG_API_URL: ownerRag.url,
      TOURISM_RAG_API_TOKEN: ownerRag.token,
    } : {}),
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
  return { child, pipe, controlPort, controlToken, ownerRagEnabled: ownerRag.enabled };
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
    createPlan: 'ساخت پیش‌نویس برنامه',
    deleteTrip: 'حذف سفر',
    deleteConversation: 'حذف گفت‌وگو و همهٔ سفرهای آن',
    prompt: 'سفر ۱۵ روزه به شیراز با بودجهٔ ۲۰ میلیون تومان؛ به طبیعت و جاهای تاریخی علاقه دارم؛ ترجیح می‌دهم مسیرها سنگ‌فرش باشند؛ دسترسی ویلچر ضروری است؛ باید از مسیرهای ناهموار پرهیز شود.',
    accessLabel: 'دسترس‌پذیری',
    softPreference: 'مسیرهای سنگ‌فرش باشد',
  },
  'en-US': {
    workspace: 'My travel plans',
    confirm: 'Save trip details',
    find: 'Check verified suggestions',
    createPlan: 'Create plan draft',
    deleteTrip: 'Delete trip',
    deleteConversation: 'Delete conversation and all its trips',
    prompt: '10 day trip to Shiraz with a budget of 20 million IRR; I prefer paved paths; wheelchair access is essential; must avoid rough terrain.',
    accessLabel: 'Accessibility',
    softPreference: 'paved paths',
  },
  ar: {
    workspace: 'خطط رحلاتي',
    confirm: 'احفظ تفاصيل الرحلة',
    find: 'تحقق من الاقتراحات الموثقة',
    createPlan: 'أنشئ مسودة خطة',
    deleteTrip: 'احذف الرحلة',
    deleteConversation: 'احذف المحادثة وكل رحلاتها',
    prompt: 'رحلة لمدة ١٠ أيام إلى شيراز بميزانية ٢٠ مليون درهم؛ أفضل المسارات المعبدة؛ إمكانية الوصول بالكراسي المتحركة ضرورية؛ يجب تجنب الطرق الوعرة.',
    accessLabel: 'إمكانية الوصول',
    softPreference: 'المسارات المعبدة',
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

async function requestBrowserJson(page, path, method, csrf, body, requestAudit = null) {
  const response = await page.request.fetch(`${webOrigin}${path}`, {
    method,
    headers: {
      Origin: webOrigin,
      ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
    },
    ...(body === undefined ? {} : { data: body }),
    timeout: 15_000,
  });
  let payload = null;
  try { payload = await response.json(); } catch { /* Keep failure details to safe response codes only. */ }
  if (!response.ok()) {
    throw new Error(`browser_api_${method.toLowerCase()}_${response.status()}_${payload?.error?.code ?? 'failed'}`);
  }
  if (!response.headers()['cache-control']?.includes('no-store')) {
    throw new Error(`browser_api_response_cacheable_${method.toLowerCase()}`);
  }
  if (requestAudit) {
    requestAudit.push({
      method,
      path,
      status: response.status(),
      cacheControl: response.headers()['cache-control'],
      transport: 'playwright-api-request-to-local-vite-origin',
    });
  }
  return payload;
}

function assertNoInventedSchedule(itinerary, { coordinateAware = false } = {}) {
  const forbiddenInferredFields = [
    'planned_start_time',
    'duration_minutes',
    'travel_to_next_estimate_minutes',
    'opening_hours',
    'estimated_arrival_time',
    'estimated_travel_minutes',
  ];
  for (const stop of itinerary.stops ?? []) {
    for (const field of forbiddenInferredFields) {
      if (stop[field] != null) throw new Error(`itinerary_inferred_unsupported_${field}`);
    }
  }
  if (!Array.isArray(itinerary.warning_codes)
      || !itinerary.warning_codes.includes('no_hours_or_routes_inferred')) {
    throw new Error('itinerary_missing_no_hours_or_routes_warning');
  }
  if (coordinateAware) {
    if (!itinerary.warning_codes.includes('geodesic_grouping_heuristic_only')
        || !itinerary.warning_codes.includes('position_not_entrance')
        || itinerary.warning_codes.includes('stop_location_unknown')) {
      throw new Error('coordinate_aware_itinerary_warning_mismatch');
    }
  } else if (!itinerary.warning_codes.includes('stop_location_unknown')
      || itinerary.warning_codes.includes('geodesic_grouping_heuristic_only')) {
    throw new Error('coordinate_free_itinerary_location_warning_mismatch');
  }
}

function fixtureRequirements(requestText, locale) {
  const unknown = { value: null, status: 'unknown', evidence: null };
  return {
    requestText, locale,
    destinations: { value: ['TEST ONLY'], status: 'extracted', evidence: 'test-only fixture identity' },
    origin: unknown,
    durationDays: { value: 15, status: 'extracted', evidence: '15 days' },
    travelDates: unknown,
    travelerCount: unknown,
    accessibility: unknown,
    budget: unknown,
    interests: unknown,
    softPreferences: unknown,
    constraints: [],
    extractionStatus: 'ready',
    missingRequired: [],
    ambiguousRequired: [],
    confirmationRequired: [],
    destinationVerification: 'user_input_unverified',
  };
}

async function runPersistedFifteenDayFixture(page, api, csrf, locale, screenshotRoot, originalRequestText) {
  const apiTrace = [];
  const enabled = await checkedControl(api.controlPort, api.controlToken, {
    action: 'enable_itinerary_fixture',
  });
  const destinationIds = enabled.destination_ids;
  if (!Array.isArray(destinationIds) || destinationIds.length !== 4) {
    throw new Error('isolated_four_destination_fixture_missing');
  }
  try {
    const requestText = 'درخواست آزمایشی برای برنامه پانزده روزه';
    const started = await requestBrowserJson(page, '/api/v1/conversations', 'POST', csrf, {
      locale,
      request_text: requestText,
      extracted_requirements: fixtureRequirements(requestText, locale),
      idempotency_key: randomUUID(),
    }, apiTrace);
    const conversationId = started.conversation?.conversation_id;
    const trip = started.trip;
    if (!conversationId || !trip?.trip_id || trip.duration_days !== 15) {
      throw new Error('real_browser_test_trip_not_persisted');
    }
    const confirmed = await requestBrowserJson(page, `/api/v1/trips/${trip.trip_id}`, 'PATCH', csrf, {
      expected_version: trip.version,
      confirmed_requirements: {
        confirmation_source: 'traveler_reviewed', duration_days: 15,
        destinations: ['TEST ONLY'], constraints: [],
      },
      destination_ids: destinationIds,
    }, apiTrace);
    if (confirmed.duration_days !== 15
      || confirmed.confirmed_requirements?.duration_days !== 15) {
      throw new Error('real_browser_fifteen_day_confirmation_failed');
    }
    // Continue this persisted test trip in the actual traveler UI. The private
    // fixture only supplies isolated recommendation evidence; buttons below
    // initiate both recommendation and itinerary requests through Vite/FastAPI.
    const initialHistoryPending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/conversations'
      && response.request().method() === 'GET');
    await page.locator('.trip-history-heading button').click();
    await initialHistoryPending;
    await page.getByRole('button', { name: requestText, exact: true }).click();
    await page.waitForFunction(expected => document.querySelector('#trip-prompt')?.value === expected, requestText);
    await page.locator('#profile-duration').waitFor({ state: 'visible' });

    const uiConfirmPath = `/api/v1/trips/${trip.trip_id}`;
    const mandatoryChoices = page.locator('.requirement-consent-field input[value="must_have"]');
    for (let choiceIndex = 0; choiceIndex < await mandatoryChoices.count(); choiceIndex += 1) {
      await mandatoryChoices.nth(choiceIndex).check({ force: true });
    }
    const uiConfirmButton = page.getByRole('button', { name: localeCopy[locale].confirm, exact: true });
    await uiConfirmButton.waitFor({ state: 'visible' });
    const uiConfirmationPending = page.waitForResponse(response => new URL(response.url()).pathname === uiConfirmPath
      && response.request().method() === 'PATCH', { timeout: 30_000 })
      .then(response => ({ response }), error => ({ error }));
    await uiConfirmButton.click();
    const confirmationWaitResult = await uiConfirmationPending;
    let uiConfirmationResponse = confirmationWaitResult.response;
    if (!uiConfirmationResponse) {
      const diagnostic = await page.evaluate(label => ({
        confirmDisabled: [...document.querySelectorAll('button')].find(button => button.textContent?.trim() === label)?.disabled ?? null,
        invalidInputIds: [...document.querySelectorAll('[aria-invalid="true"]')].map(element => element.id),
        consentFieldCount: document.querySelectorAll('.requirement-consent-field').length,
        mandatoryChecked: [...document.querySelectorAll('.requirement-consent-field input[value="must_have"]')]
          .filter(element => element.checked).length,
        advisoryChecked: [...document.querySelectorAll('.requirement-consent-field input[value="advisory"]')]
          .filter(element => element.checked).length,
        consentAckMissing: [...document.querySelectorAll('.requirement-consent-field input[type="checkbox"]')]
          .filter(element => !element.checked).length,
      }), localeCopy[locale].confirm);
      throw new Error(`traveler_ui_profile_confirmation_no_request_${JSON.stringify(diagnostic)}`);
    }
    if (uiConfirmationResponse.status() !== 200
        || !uiConfirmationResponse.headers()['cache-control']?.includes('no-store')) {
      throw new Error('traveler_ui_profile_confirmation_failed');
    }
    const uiConfirmedTrip = await uiConfirmationResponse.json();
    const consent = uiConfirmedTrip.confirmed_requirements?.requirement_consent;
    if (!consent || consent.contract_version !== 'recommendation-consent-v1') {
      throw new Error('traveler_ui_profile_consent_snapshot_missing');
    }
    const fixtureProfile = { ...uiConfirmedTrip.confirmed_requirements };
    delete fixtureProfile.requirement_consent;
    const consentRequest = { ...consent };
    delete consentRequest.profile_version;
    const fixtureTrip = await requestBrowserJson(page, uiConfirmPath, 'PATCH', csrf, {
      expected_version: uiConfirmedTrip.version,
      confirmed_requirements: fixtureProfile,
      destination_ids: destinationIds,
      requirement_consent: consentRequest,
    }, apiTrace);
    if (fixtureTrip.destination_ids?.length !== 4
        || fixtureTrip.confirmed_requirements?.requirement_consent?.profile_version !== fixtureTrip.version) {
      throw new Error('isolated_test_fixture_identity_binding_failed');
    }

    const ownerRagBefore = await checkedControl(api.controlPort, api.controlToken, {
      action: 'owner_rag_call_counts',
    });
    const recommendationsPath = `/api/v1/trips/${trip.trip_id}/recommendations`;
    const recommendationPending = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/recommendations')
      && response.request().method() === 'POST');
    await page.getByRole('button', { name: localeCopy[locale].find, exact: true }).click();
    const recommendationResponse = await recommendationPending;
    if (new URL(recommendationResponse.url()).pathname !== recommendationsPath) {
      throw new Error(`traveler_ui_recommendation_trip_mismatch_${new URL(recommendationResponse.url()).pathname}`);
    }
    if (!recommendationResponse.headers()['cache-control']?.includes('no-store')) {
      throw new Error('browser_api_response_cacheable_post_recommendations');
    }
    apiTrace.push({ method: 'POST', path: recommendationsPath, status: recommendationResponse.status(),
      cacheControl: recommendationResponse.headers()['cache-control'], transport: 'traveler-ui-to-local-vite-origin' });
    const recommendation = await recommendationResponse.json();
    if (recommendation.status !== 'available' || recommendation.items?.length !== 4
      || recommendation.items.some(item => !item.evidence?.some(source => source.source_url.includes('.invalid')))) {
      throw new Error(`real_browser_test_only_recommendations_failed_${JSON.stringify({
        status: recommendation.status, reason: recommendation.reason_code,
        itemCount: recommendation.items?.length,
        evidenceCounts: recommendation.items?.map(item => item.evidence?.length ?? 0),
      })}`);
    }
    if (recommendation.items.some(item =>
      ['text', 'document_id', 'content_hash', 'claim_key', 'evidence_id'].some(key => key in item))) {
      throw new Error('owner_rag_evidence_fields_leaked_to_traveler_recommendation');
    }
    if (recommendation.items.some(item => item.retrieval_evidence?.length)) {
      throw new Error('owner_rag_no_evidence_was_replaced_with_fallback_citation');
    }
    const ownerRagAfter = await checkedControl(api.controlPort, api.controlToken, {
      action: 'owner_rag_call_counts',
    });
    if (ownerRagAfter.enabled !== api.ownerRagEnabled) throw new Error('owner_rag_mode_report_mismatch');
    const ownerRagProbe = {
      enabled: ownerRagAfter.enabled,
      calls: ownerRagAfter.calls - ownerRagBefore.calls,
      outcomes: Object.fromEntries(Object.keys(ownerRagAfter.outcomes).map(key => [
        key, ownerRagAfter.outcomes[key] - ownerRagBefore.outcomes[key],
      ])),
      travelerEvidenceTextReturned: false,
    };
    if (api.ownerRagEnabled && (ownerRagProbe.calls !== 1 || ownerRagProbe.outcomes.no_evidence !== 1)) {
      throw new Error('owner_rag_empty_index_http_probe_not_confirmed');
    }
    if (!api.ownerRagEnabled && ownerRagProbe.calls !== 0) {
      throw new Error('disabled_owner_rag_made_retrieval_calls');
    }
    if (recommendation.items.some(item => item.retrieval_evidence_status
      !== (api.ownerRagEnabled ? 'no_evidence' : 'disabled'))) {
      throw new Error('owner_rag_status_mismatch_with_truthful_structured_recommendation');
    }
    await page.locator('#journey-day-count').waitFor({ state: 'visible' });
    if (await page.locator('#journey-day-count').inputValue() !== '15') {
      throw new Error('traveler_ui_did_not_default_confirmed_fifteen_days');
    }
    const itineraryCreatePath = `/api/v1/trips/${trip.trip_id}/itineraries`;
    const itineraryCreatePending = page.waitForResponse(response => new URL(response.url()).pathname === itineraryCreatePath
      && response.request().method() === 'POST');
    await page.getByRole('button', { name: localeCopy[locale].createPlan, exact: true }).click();
    const itineraryCreateResponse = await itineraryCreatePending;
    if (!itineraryCreateResponse.headers()['cache-control']?.includes('no-store')) {
      throw new Error('browser_api_response_cacheable_post_itinerary');
    }
    apiTrace.push({ method: 'POST', path: itineraryCreatePath, status: itineraryCreateResponse.status(),
      cacheControl: itineraryCreateResponse.headers()['cache-control'], transport: 'traveler-ui-to-local-vite-origin' });
    const created = await itineraryCreateResponse.json();
    const itineraryId = created.itinerary_id;
    const initialDayCounts = Object.values((created.stops ?? []).reduce((counts, stop) => {
      counts[stop.day_number] = (counts[stop.day_number] ?? 0) + 1;
      return counts;
    }, {})).sort((left, right) => left - right);
    const cityFixtureIds = new Set(destinationIds.slice(0, 3).map(String));
    const regionalFixtureId = String(destinationIds[3]);
    const dayForFixture = new Map((created.stops ?? []).map(stop => [String(stop.destination_id), stop.day_number]));
    const cityDays = new Set([...cityFixtureIds].map(id => dayForFixture.get(id)));
    const cityDay = cityDays.size === 1 ? [...cityDays][0] : null;
    const regionalDay = dayForFixture.get(regionalFixtureId);
    if (!itineraryId || created.day_count !== 15 || created.status !== 'partial'
      || created.stops?.length !== 4 || created.unplanned_days?.length !== 13
      || JSON.stringify(initialDayCounts) !== JSON.stringify([1, 3])
      || cityDay == null || regionalDay == null || cityDay === regionalDay) {
      throw new Error('real_browser_fifteen_day_partial_itinerary_failed');
    }
    assertNoInventedSchedule(created, { coordinateAware: true });
    const catalogue = await requestBrowserJson(page, '/api/v1/catalog/destinations', 'GET', undefined, undefined, apiTrace);
    if (catalogue.count !== 0) throw new Error('test_fixture_leaked_to_production_catalogue');

    await page.reload({ waitUntil: 'domcontentloaded' });
    const historyPending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/conversations'
      && response.request().method() === 'GET');
    await page.locator('.trip-history-heading button').click();
    await historyPending;
    const requestButton = page.getByRole('button', { name: requestText, exact: true });
    await requestButton.waitFor({ state: 'visible' });
    await requestButton.click();
    await page.locator('#itinerary-day-15').waitFor({ state: 'visible' });
    if (await page.locator('.saved-itinerary-days .itinerary-day').count() !== 15
      || await page.locator('.saved-stop').count() !== 4
      || await page.locator('.unplanned-day').count() !== 13) {
      throw new Error('real_persisted_fifteen_day_itinerary_not_restored_in_ui');
    }
    const lastDay = await page.locator('#itinerary-day-15').textContent();
    const localizedDay = await page.evaluate(({ localeValue }) => new Intl.NumberFormat(localeValue, {
      numberingSystem: localeValue === 'ar' ? 'arab' : localeValue === 'fa-IR' ? 'arabext' : 'latn',
    }).format(15), { localeValue: locale });
    if (!lastDay?.includes(localizedDay)) throw new Error(`fifteen_day_label_not_localized_${locale}`);

    await page.locator(`#stop-day-${created.stops[0].recommendation_id}`).selectOption('5');
    await page.locator('.saved-stop').nth(1).locator('.stop-actions button').last().click();
    await sanitizeAndCapture(page, resolve(screenshotRoot, `partial-${locale}-390.png`), locale, 390, 844);
    await sanitizeAndCapture(page, resolve(screenshotRoot, `partial-${locale}-1440.png`), locale, 1440, 1000);
    const savePending = page.waitForResponse(response => new URL(response.url()).pathname === `/api/v1/itineraries/${itineraryId}`
      && response.request().method() === 'PUT');
    await page.locator('.saved-itinerary > button').last().click();
    const savedResponse = await savePending;
    const saved = await savedResponse.json();
    if (savedResponse.status() !== 200 || saved.revision !== 2 || saved.day_count !== 15 || saved.stops?.length !== 3) {
      throw new Error('real_browser_itinerary_edit_not_persisted');
    }
    apiTrace.push({
      method: 'PUT',
      path: `/api/v1/itineraries/${itineraryId}`,
      status: savedResponse.status(),
      cacheControl: savedResponse.headers()['cache-control'],
      transport: 'browser-page-request-to-local-vite-origin',
    });
    if (!savedResponse.headers()['cache-control']?.includes('no-store')) {
      throw new Error('browser_api_response_cacheable_put');
    }
    const reopened = await requestBrowserJson(
      page, `/api/v1/itineraries/${itineraryId}`, 'GET', undefined, undefined, apiTrace,
    );
    assertNoInventedSchedule(reopened, { coordinateAware: true });
    if (reopened.revision !== 2 || reopened.day_count !== 15 || reopened.stops?.length !== 3
      || reopened.unplanned_days?.length !== 12) {
      throw new Error('real_browser_itinerary_edit_reopen_mismatch');
    }
    const catalogueAfter = await requestBrowserJson(page, '/api/v1/catalog/destinations', 'GET', undefined, undefined, apiTrace);
    if (catalogueAfter.count !== 0) throw new Error('test_fixture_leaked_after_itinerary_edit');
    const deletedFixture = await requestBrowserJson(
      page, `/api/v1/conversations/${conversationId}`, 'DELETE', csrf,
    );
    if (!deletedFixture.deleted) throw new Error('positive_fixture_conversation_cleanup_failed');
    const refreshedHistory = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/conversations'
      && response.request().method() === 'GET');
    await page.locator('.trip-history-heading button').click();
    await refreshedHistory;
    const originalTrip = page.getByRole('button', { name: originalRequestText, exact: true });
    await originalTrip.waitFor({ state: 'visible' });
    await originalTrip.click();
    const originalRequestRestored = await page.waitForFunction(
      expected => document.querySelector('#trip-prompt')?.value === expected,
      originalRequestText,
      { timeout: 15_000 },
    );
    if (!originalRequestRestored) {
      throw new Error('original_journey_not_restored_after_positive_itinerary');
    }
    const positiveApiPaths = [
      ['POST', `/api/v1/trips/${trip.trip_id}/recommendations`],
      ['POST', `/api/v1/trips/${trip.trip_id}/itineraries`],
      ['PUT', `/api/v1/itineraries/${itineraryId}`],
      ['GET', `/api/v1/itineraries/${itineraryId}`],
    ];
    for (const [method, path] of positiveApiPaths) {
      if (!apiTrace.some(entry => entry.method === method && entry.path === path && entry.status >= 200 && entry.status < 300)) {
        throw new Error(`positive_live_api_call_not_observed_${method.toLowerCase()}`);
      }
    }
    return {
      itineraryId, dayCount: 15, initialStops: 4, initialDayGroupSizes: initialDayCounts, finalStops: 3,
      initialUnplannedDays: 13, finalUnplannedDays: 12,
      geographicDayAssignments: { cityClusterDay: cityDay, regionalDay, cityClusterStops: cityFixtureIds.size, regionalStops: 1 },
      ownerRagProbe,
      apiTrace: apiTrace.filter(entry => /recommendations|itineraries/.test(entry.path)),
      noInventedScheduleFields: true,
      geoGrouping: 'three pending Shiraz proposal points grouped together and one pending Marvdasht property-reference point grouped separately; coordinates were used only by synthetic in-memory test identities and were not published or returned to travelers',
      warningCodes: reopened.warning_codes,
    };
  } finally {
    await checkedControl(api.controlPort, api.controlToken, { action: 'disable_itinerary_fixture' });
  }
}


// Explicit opt-in browser acceptance: real canonical Fars IDs in disposable QA PG17.
// No in-memory/synthetic candidate override, provider call, or public approval.
async function runGeoCatalogueLocale(browser, api, locale, audit, artifactRoot) {
  const keys = [
    'shiraz-hafezieh-v1', 'shiraz-eram-garden-v1',
    'shiraz-vakil-bazaar-v1', 'unesco-persepolis-v1',
  ];
  const roles = ['representative_point', 'representative_point',
    'representative_point', 'property_reference'];
  const prompts = {
    'fa-IR': 'برنامه پانزده روزه شیراز، حافظیه، باغ ارم، بازار وکیل و تخت جمشید',
    'en-US': '15-day Fars QA visit to Hafezieh, Eram Garden, Vakil Bazaar, Persepolis',
    ar: 'رحلة تجريبية لمدة ١٥ يوماً إلى حافظية وحديقة إرم وسوق وكيل وبرسبوليس',
  };
  const context = await browser.newContext({ locale });
  const page = await context.newPage();
  const phone = syntheticPhone();
  let authenticated = false;
  reportResponseWaitCallsite(page);
  await attachBrowserGuards(page, audit);
  try {
    await page.goto(webOrigin, { waitUntil: 'domcontentloaded' });
    await selectAndVerifyLocale(page, locale);
    const identity = await signIn(page, api.controlPort, api.controlToken, phone);
    authenticated = true;
    const csrf = identity.csrfToken;
    const trace = [];
    const catalog = await requestBrowserJson(
      page, '/api/v1/catalog/destinations', 'GET', undefined, undefined, trace);
    if (catalog.status !== 'available' || catalog.count !== 4 || catalog.items?.length !== 4) {
      throw new Error('qa_real_geo_catalogue_not_four_destinations');
    }
    const byKey = new Map(catalog.items.map(item => [item.destination_key, item]));
    const selected = keys.map((key, index) => {
      const point = byKey.get(key);
      if (!point || point.coordinate_role !== roles[index]
          || !Number.isFinite(point.latitude) || !Number.isFinite(point.longitude)
          || !/^[0-9]+$/.test(point.destination_id)) {
        throw new Error('qa_real_geo_canonical_identity_coordinate_or_role_missing');
      }
      return point;
    });
    const selectedIds = selected.map(item => item.destination_id);
    const names = selected.map(item => item.canonical_name);
    const requestText = prompts[locale];
    const extracted = fixtureRequirements(requestText, locale);
    extracted.destinations = {
      value: names, status: 'extracted',
      evidence: 'selected seeded canonical Fars POIs in disposable QA',
    };
    const started = await requestBrowserJson(page, '/api/v1/conversations', 'POST', csrf, {
      locale, request_text: requestText, extracted_requirements: extracted,
      idempotency_key: randomUUID(),
    }, trace);
    const trip = started.trip;
    const conversationId = started.conversation?.conversation_id;
    if (!conversationId || !trip?.trip_id || trip.duration_days !== 15) {
      throw new Error('qa_real_geo_conversation_not_persisted');
    }
    const tripPath = '/api/v1/trips/' + trip.trip_id;
    await requestBrowserJson(page, tripPath, 'PATCH', csrf, {
      expected_version: trip.version,
      confirmed_requirements: {
        confirmation_source: 'traveler_reviewed', duration_days: 15,
        destinations: names, constraints: [],
      },
      destination_ids: selectedIds,
    }, trace);

    const historyWait = page.waitForResponse(response =>
      new URL(response.url()).pathname === '/api/v1/conversations'
      && response.request().method() === 'GET');
    await page.locator('.trip-history-heading button').click();
    await historyWait;
    await page.getByRole('button', { name: requestText, exact: true }).click();
    await page.locator('#profile-duration').waitFor({ state: 'visible' });
    const mandatory = page.locator('.requirement-consent-field input[value="must_have"]');
    for (let i = 0; i < await mandatory.count(); i += 1) {
      await mandatory.nth(i).check({ force: true });
    }
    const confirmWait = page.waitForResponse(response =>
      new URL(response.url()).pathname === tripPath && response.request().method() === 'PATCH');
    await page.getByRole('button', { name: localeCopy[locale].confirm, exact: true }).click();
    const confirmResponse = await confirmWait;
    if (confirmResponse.status() !== 200) throw new Error('qa_real_geo_ui_confirmation_failed');
    const confirmed = await confirmResponse.json();
    const consent = confirmed.confirmed_requirements?.requirement_consent;
    if (consent?.contract_version !== 'recommendation-consent-v1') {
      throw new Error('qa_real_geo_consent_missing');
    }
    const finalProfile = { ...confirmed.confirmed_requirements };
    delete finalProfile.requirement_consent;
    const consentRequest = { ...consent };
    delete consentRequest.profile_version;
    const finalTrip = await requestBrowserJson(page, tripPath, 'PATCH', csrf, {
      expected_version: confirmed.version, confirmed_requirements: finalProfile,
      destination_ids: selectedIds, requirement_consent: consentRequest,
    }, trace);
    if (finalTrip.destination_ids?.join(',') !== selectedIds.join(',')
        || finalTrip.confirmed_requirements?.requirement_consent?.profile_version !== finalTrip.version) {
      throw new Error('qa_real_geo_selected_ids_or_consent_changed');
    }

    const recommendationPath = tripPath + '/recommendations';
    const recommendationWait = page.waitForResponse(response =>
      new URL(response.url()).pathname === recommendationPath
      && response.request().method() === 'POST');
    await page.getByRole('button', { name: localeCopy[locale].find, exact: true }).click();
    const recommendationResponse = await recommendationWait;
    const recommendation = await recommendationResponse.json();
    if (recommendationResponse.status() !== 201
        || recommendation.status !== 'available' || recommendation.items?.length !== 4
        || !selectedIds.every(id => recommendation.items.some(item => item.destination_id === id))
        || recommendation.items.some(item => !item.evidence?.length || item.evidence.some(source =>
          !source.source_url?.startsWith('https://') || source.source_url.includes('.invalid')
          || source.source_role === 'test_fixture'))) {
      throw new Error('qa_real_geo_recommendation_not_real_canonical');
    }
    trace.push({ method: 'POST', path: recommendationPath, status: 201 });
    await page.locator('#journey-day-count').waitFor({ state: 'visible' });
    if (await page.locator('#journey-day-count').inputValue() !== '15') {
      throw new Error('qa_real_geo_trip_duration_wrong');
    }
    const planPath = tripPath + '/itineraries';
    const planWait = page.waitForResponse(response =>
      new URL(response.url()).pathname === planPath && response.request().method() === 'POST');
    await page.getByRole('button', { name: localeCopy[locale].createPlan, exact: true }).click();
    const planResponse = await planWait;
    const created = await planResponse.json();
    if (planResponse.status() !== 201 || !created.itinerary_id
        || created.day_count !== 15 || created.stops?.length !== 4
        || created.status !== 'partial' || created.unplanned_days?.length !== 13) {
      throw new Error('qa_real_geo_plan_not_created');
    }
    const days = new Map(created.stops.map(stop => [String(stop.destination_id), stop.day_number]));
    const cityDays = new Set(selectedIds.slice(0, 3).map(id => days.get(id)));
    const cityDay = cityDays.size === 1 ? [...cityDays][0] : null;
    const regionalDay = days.get(selectedIds[3]);
    if (cityDay == null || regionalDay == null || cityDay === regionalDay) {
      throw new Error('qa_real_geo_grouping_wrong');
    }
    assertNoInventedSchedule(created, { coordinateAware: true });
    trace.push({ method: 'POST', path: planPath, status: 201 });

    await page.reload({ waitUntil: 'domcontentloaded' });
    const restoreWait = page.waitForResponse(response =>
      new URL(response.url()).pathname === '/api/v1/conversations'
      && response.request().method() === 'GET');
    await page.locator('.trip-history-heading button').click();
    await restoreWait;
    await page.getByRole('button', { name: requestText, exact: true }).click();
    await page.locator('#itinerary-day-15').waitFor({ state: 'visible' });
    if (await page.locator('.saved-stop').count() !== 4
        || await page.locator('.unplanned-day').count() !== 13) {
      throw new Error('qa_real_geo_plan_not_reopened_in_pwa');
    }
    await page.locator('#stop-day-' + created.stops[0].recommendation_id).selectOption('5');
    await page.locator('.saved-stop').nth(1).locator('.stop-actions button').last().click();
    const localeDir = resolve(artifactRoot, locale);
    mkdirSync(localeDir, { recursive: true });
    await sanitizeAndCapture(page, resolve(localeDir, 'qa-real-geo-' + locale + '.png'),
      locale, 390, 844);
    const editPath = '/api/v1/itineraries/' + created.itinerary_id;
    const editWait = page.waitForResponse(response =>
      new URL(response.url()).pathname === editPath && response.request().method() === 'PUT');
    await page.locator('.saved-itinerary > button').last().click();
    const editResponse = await editWait;
    const saved = await editResponse.json();
    if (editResponse.status() !== 200 || saved.revision !== 2 || saved.stops?.length !== 3) {
      throw new Error('qa_real_geo_plan_edit_not_saved');
    }
    const reopened = await requestBrowserJson(page, editPath, 'GET', undefined, undefined, trace);
    assertNoInventedSchedule(reopened, { coordinateAware: true });
    if (reopened.revision !== 2 || reopened.day_count !== 15
        || reopened.stops?.length !== 3 || reopened.unplanned_days?.length !== 12) {
      throw new Error('qa_real_geo_plan_reopen_mismatch');
    }
    trace.push({ method: 'PUT', path: editPath, status: 200 });
    await requestBrowserJson(page, '/api/v1/conversations/' + conversationId, 'DELETE', csrf);
    return {
      locale, mode: 'canonical_Fars_IDs_in_disposable_QA_database',
      canonicalKeys: keys, coordinatesRoles: roles,
      dayCount: 15, cityDay, regionalDay,
      initialStops: 4, finalStops: 3,
      initialUnplannedDays: 13, finalUnplannedDays: 12,
      saveEditReopen: true, verifiedEntrance: false, verifiedRoadETA: false,
      apiTrace: trace.filter(row => /recommendations|itineraries/.test(row.path)),
    };
  } finally {
    if (authenticated) {
      try {
        await checkedControl(api.controlPort, api.controlToken,
          { action: 'cleanup_phones', phones: [phone] });
      } catch { /* only QA data; disposable container cleanup follows */ }
    }
    await page.close().catch(() => {});
    await context.close().catch(() => {});
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
  await page.locator('.conversation-local-action button').click();
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

    // A separate test-only 15-day journey goes through real FastAPI and
    // PostgreSQL. Its four synthetic identities exist only in the isolated
    // traveler dependency; no positive API calls are intercepted.
    const positiveItinerary = await runPersistedFifteenDayFixture(
      pageA, api, csrfA, locale, artifactLocale, copy.prompt,
    );
    localeChecks = true;
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
      partialFixtureDays: positiveItinerary.dayCount,
      partialFixtureInitialStops: positiveItinerary.initialStops,
      partialFixtureInitialUnplannedDays: positiveItinerary.initialUnplannedDays,
      partialFixtureStops: positiveItinerary.finalStops,
      partialFixtureUnplannedDays: positiveItinerary.finalUnplannedDays,
      positiveItinerary,
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
    if (process.env.RAHGARD_REAL_GEO_E2E === '1') {
      if (process.env.RAHGARD_RUN_GEO_QA !== '1' || api.ownerRagEnabled) {
        throw new Error('qa_real_geo_requires_explicit_disposable_opt_in_and_rag_off');
      }
      const results = [];
      for (const locale of ['fa-IR', 'en-US', 'ar']) {
        results.push(await runGeoCatalogueLocale(browser, api, locale, audit, artifactRoot));
      }
      if (audit.successfulExternalResponses || audit.pageErrors) {
        throw new Error('qa_real_geo_external_response_or_browser_error');
      }
      const report = {
        status: 'passed',
        mode: 'real_canonical_Fars_PG17_QA_only_not_public_approval',
        browser: 'Chromium ' + browser.version(),
        database: { name: process.env.AUTH_TEST_DATABASE_NAME, host: '127.0.0.1',
          majorVersion: 17, markerValidated: true },
        chat: { mode: 'simulated', liveProviderCalls: 0 },
        ownerRag: { mode: 'disabled', calls: 0 },
        locales: results,
        screenshots: results.map(result => ({
          locale: result.locale, kind: 'disposable QA canonical-place itinerary',
          path: result.locale + '/qa-real-geo-' + result.locale + '.png',
        })),
        audit: { externalRequestsBlocked: audit.externalRequests,
          successfulExternalResponses: 0, pageErrors: 0 },
        ownerApproval: false,
        safety: 'Only four existing canonical POIs were activated in marked disposable QA PG17. This is neither persistent pilot publication nor evidence of visitor entrances, route feasibility, operating hours, or live remote Chat.',
      };
      writeFileSync(resolve(artifactRoot, 'report.json'), JSON.stringify(report, null, 2) + '\n',
        { encoding: 'utf8', flag: 'wx' });
      console.log(JSON.stringify({ status: report.status, mode: report.mode,
        locales: results.map(result => result.locale), artifactRoot }));
      return;
    }
    const results = [];
    for (const locale of ['fa-IR', 'en-US', 'ar']) {
      results.push(await runLocaleJourney(browser, api, locale, audit, artifactRoot));
    }
    if (audit.successfulExternalResponses || audit.pageErrors) throw new Error('external_response_or_browser_runtime_error');
    const ownerRagCounts = await checkedControl(api.controlPort, api.controlToken, {
      action: 'owner_rag_call_counts',
    });
    const report = {
      status: 'passed',
      browser: `Chromium ${browser.version()}`,
      environment: 'live Vite proxy + FastAPI + guarded disposable PostgreSQL 17; fake SMS; simulated Chat gateway (no remote model)',
      database: {
        name: process.env.AUTH_TEST_DATABASE_NAME,
        host: process.env.AUTH_TEST_DATABASE_HOST,
        port: Number(process.env.AUTH_TEST_DATABASE_PORT),
        majorVersion: 17,
        markerValidated: true,
      },
      integrations: {
        chat: { mode: 'simulated', liveProviderCalls: 0 },
        ownerRag: {
          mode: api.ownerRagEnabled ? 'real_owner_http' : 'disabled',
          enabled: ownerRagCounts.enabled,
          calls: ownerRagCounts.calls,
          outcomes: ownerRagCounts.outcomes,
          travelerEvidenceTextReturned: false,
        },
      },
      locales: results,
      screenshots: [
        ...['fa-IR', 'en-US', 'ar'].flatMap(locale => [
          { locale, width: 390, height: 844, kind: 'live empty production catalogue', path: `${locale}/empty-${locale}-390.png` },
          { locale, width: 1440, height: 1000, kind: 'live empty production catalogue', path: `${locale}/empty-${locale}-1440.png` },
          { locale, width: 390, height: 844, dayCount: 15, kind: 'real API/DB edited test-only three-stop partial itinerary', path: `${locale}/partial-${locale}-390.png` },
          { locale, width: 1440, height: 1000, dayCount: 15, kind: 'real API/DB edited test-only three-stop partial itinerary', path: `${locale}/partial-${locale}-1440.png` },
        ]),
      ],
      audit: { externalRequestsBlocked: audit.externalRequests, successfulExternalResponses: 0, browserPageErrors: 0 },
      screenshotPolicy: 'Traveler-authored text is replaced in screenshot-only DOM captures; no phone, OTP, cookie, token, or request text is recorded.',
      fixturePolicy: 'The simulated Chat gateway makes no HTTP requests. Positive 15-day itinerary requests use real FastAPI and PostgreSQL with four existing synthetic-only identities exposed through a private loopback test control. Pending Shiraz/Fars proposal points are attached only in memory to these synthetic identities to exercise grouping; they are not canonical, approved, stored, or returned as traveler coordinates. No positive recommendation or itinerary API call is intercepted, and production catalogue views remain empty. When explicitly enabled, one real owner-RAG HTTP probe exercises the empty approved index; retrieved text is withheld from the response and report.',
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
