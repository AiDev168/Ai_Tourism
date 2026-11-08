// Guarded, real-browser traveler journey. OTP codes cross only an authenticated
// loopback test-control socket; the application has no OTP debug API.
import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { randomBytes, randomInt } from 'node:crypto';
import { existsSync } from 'node:fs';
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
    try { ready = (await fetch(webOrigin)).ok; } catch { /* server is starting */ }
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
  await page.locator('.auth-panel button[type="submit"]').click();
  await page.locator('.auth-signed-in').waitFor({ state: 'visible' });
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

async function waitForRequest(page, predicate, timeout = 20_000) {
  return page.waitForResponse(predicate, { timeout });
}

async function main() {
  if (!Number.isInteger(webPort) || !Number.isInteger(apiPort) || webPort < 1024 || apiPort < 1024 || webPort === 55433 || apiPort === 55433) {
    throw new Error('invalid_or_forbidden_test_ports');
  }
  const phones = [syntheticPhone(), syntheticPhone()];
  let safeToCleanup = false;
  let api;
  let web;
  let browser;
  let pipe;
  let controlPort;
  let controlToken;
  let externalRequests = 0;
  let successfulExternalResponses = 0;
  let pageErrors = 0;
  let ownerA;
  let csrfA;
  let ownerB;
  let csrfB;
  let tripId;
  let conversationId;
  let conversationVersion;
  let createBody;
  let noStoreVerify = false;
  let noStoreMe = false;

  try {
    api = await startApi();
    pipe = api.pipe;
    controlPort = api.controlPort;
    controlToken = api.controlToken;
    const unused = await checkedControl(controlPort, controlToken, { action: 'assert_phones_unused', phones });
    if (!unused.ok) throw new Error('synthetic_test_identity_collision');
    safeToCleanup = true;
    web = await startWeb();
    browser = await chromium.launch({ executablePath: chrome, headless: true });

    const contextA = await browser.newContext({ locale: 'fa-IR' });
    const pageA = await contextA.newPage();
    await pageA.route('**/*', route => {
      if (new URL(route.request().url()).origin !== webOrigin) {
        externalRequests += 1;
        return route.abort();
      }
      return route.continue();
    });
    pageA.on('pageerror', () => { pageErrors += 1; });
    pageA.on('response', async response => {
      const path = new URL(response.url()).pathname;
      if (new URL(response.url()).origin !== webOrigin && response.status() >= 200 && response.status() < 400) {
        successfulExternalResponses += 1;
      }
      if (path === '/api/v1/auth/otp/verify' && response.status() === 200) {
        const body = await response.json().catch(() => null);
        ownerA = body?.user?.user_id;
        csrfA = body?.csrf_token;
        noStoreVerify = response.headers()['cache-control']?.includes('no-store') === true;
      }
      if (path === '/api/v1/auth/me' && response.status() === 200) {
        noStoreMe = response.headers()['cache-control']?.includes('no-store') === true;
      }
      if (path === '/api/v1/conversations' && response.request().method() === 'POST' && response.status() === 201) {
        const body = await response.json().catch(() => null);
        tripId = body?.trip?.trip_id;
        conversationId = body?.conversation?.conversation_id;
        conversationVersion = body?.conversation?.version;
      }
    });
    pageA.on('request', request => {
      if (new URL(request.url()).pathname === '/api/v1/conversations' && request.method() === 'POST') {
        createBody = request.postDataJSON();
      }
    });

    await pageA.goto(webOrigin, { waitUntil: 'domcontentloaded' });
    const health = await fetch(`${apiTarget}/health/live`);
    if (!health.ok) throw new Error('api_health_check_failed');

    const destinations = await pageA.request.get(`${webOrigin}/api/v1/catalog/destinations`, { timeout: 10_000 });
    const emptyCatalogue = await destinations.json();
    if (destinations.status() !== 200 || emptyCatalogue.count !== 0 || emptyCatalogue.status !== 'available') {
      throw new Error('approved_spatial_catalogue_not_empty_or_unavailable');
    }
    const culinaryResponse = await pageA.request.get(
      `${webOrigin}/api/v1/catalog/culinary?locale=fa-IR`,
      { timeout: 10_000 },
    );
    const culinaryCatalogue = await culinaryResponse.json();
    if (
      culinaryResponse.status() !== 200
      || culinaryCatalogue.status !== 'available'
      || culinaryCatalogue.count !== 0
      || culinaryCatalogue.items?.length !== 0
    ) {
      throw new Error('pending_culinary_candidates_leaked_or_catalogue_unavailable');
    }

    await signIn(pageA, controlPort, controlToken, phones[0]);
    if (!ownerA || !csrfA || !noStoreVerify) throw new Error('authenticated_user_state_missing_or_cached');
    await pageA.reload({ waitUntil: 'domcontentloaded' });
    await pageA.locator('.auth-signed-in').waitFor({ state: 'visible' });
    if (!noStoreMe) throw new Error('auth_me_cache_policy_missing');
    const storageKeys = await pageA.evaluate(() => Object.keys(localStorage).map(key => key.toLowerCase()));
    if (storageKeys.some(key => key.includes('token') || key.includes('session') || key.includes('csrf'))) {
      throw new Error('credential_in_browser_storage');
    }

    await pageA.locator('#trip-prompt').fill('سفر ۳ روزه به شیراز به همراه خانواده');
    await pageA.locator('.trip-form button[type="submit"]').click();
    await pageA.locator('.journey-action').waitFor({ state: 'visible' });
    const persist = waitForRequest(pageA, response => response.url().includes('/api/v1/conversations') && response.request().method() === 'POST');
    await pageA.locator('.journey-action').click();
    const persisted = await persist;
    const persistedBody = await persisted.json().catch(() => null);
    tripId = persistedBody?.trip?.trip_id;
    conversationId = persistedBody?.conversation?.conversation_id;
    conversationVersion = persistedBody?.conversation?.version;
    if (persisted.status() !== 201 || !tripId || !conversationId || !createBody) {
      throw new Error(`conversation_trip_persistence_failed_${persisted.status()}`);
    }
    await pageA.locator('.history-trip button').filter({ hasText: 'سفر ۳ روزه به شیراز به همراه خانواده' }).first().waitFor({ state: 'visible' });

    await pageA.locator('.profile-editor > button').click();
    await pageA.locator('.recommendation-controls').waitFor({ state: 'visible' });
    const recResponsePromise = waitForRequest(pageA, response => response.url().includes(`/api/v1/trips/${tripId}/recommendations`));
    await pageA.locator('.recommendation-controls > button').click();
    const recResponse = await recResponsePromise;
    const recommendation = await recResponse.json();
    if (recResponse.status() !== 201 || !recResponse.headers()['cache-control']?.includes('no-store') || recommendation.status !== 'empty' || recommendation.reason_code !== 'catalogue_empty') {
      throw new Error(`recommendation_empty_state_not_truthful_${recResponse.status()}_${recommendation.reason_code ?? 'unknown'}`);
    }
    if (await pageA.locator('.itinerary-start').count()) throw new Error('itinerary_offered_without_eligible_candidate');

    for (const locale of ['en-US', 'ar', 'fa-IR']) {
      await pageA.locator('#locale').selectOption(locale);
      await pageA.waitForFunction(expected => document.documentElement.lang === expected, locale);
      const direction = await pageA.locator('html').getAttribute('dir');
      if (direction !== (locale === 'en-US' ? 'ltr' : 'rtl')) throw new Error('locale_direction_mismatch');
    }

    await pageA.reload({ waitUntil: 'domcontentloaded' });
    await pageA.locator('.auth-signed-in').waitFor({ state: 'visible' });
    await pageA.locator('.history-trip button').filter({ hasText: 'سفر ۳ روزه به شیراز به همراه خانواده' }).first().click();
    await pageA.locator('.saved-message-user p').filter({ hasText: 'سفر ۳ روزه به شیراز به همراه خانواده' }).waitFor({ state: 'visible' });

    const contextB = await browser.newContext({ locale: 'fa-IR' });
    const pageB = await contextB.newPage();
    await pageB.route('**/*', route => {
      if (new URL(route.request().url()).origin !== webOrigin) {
        externalRequests += 1;
        return route.abort();
      }
      return route.continue();
    });
    pageB.on('pageerror', () => { pageErrors += 1; });
    pageB.on('response', async response => {
      if (new URL(response.url()).origin !== webOrigin && response.status() >= 200 && response.status() < 400) {
        successfulExternalResponses += 1;
      }
      if (new URL(response.url()).pathname === '/api/v1/auth/otp/verify' && response.status() === 200) {
        const body = await response.json().catch(() => null);
        ownerB = body?.user?.user_id;
        csrfB = body?.csrf_token;
      }
    });
    await pageB.goto(webOrigin, { waitUntil: 'domcontentloaded' });
    await signIn(pageB, controlPort, controlToken, phones[1]);
    if (!ownerB || !csrfB || ownerA === ownerB || !conversationId || !conversationVersion) throw new Error('second_test_identity_missing');
    const deniedRead = await apiStatus(pageB, `/api/v1/trips/${tripId}`, 'GET');
    const deniedWrite = await apiStatus(pageB, '/api/v1/conversations', 'POST', {}, createBody);
    const deniedDelete = await apiStatus(pageB, `/api/v1/trips/${tripId}`, 'DELETE', { 'X-CSRF-Token': csrfB });
    const deniedAppend = await apiStatus(pageB, `/api/v1/conversations/${conversationId}/messages`, 'POST', {
      'X-CSRF-Token': csrfB,
    }, {
      trip_id: tripId,
      content: 'Append authorization probe.',
      idempotency_key: 'e2e-cross-owner-append-0001',
      expected_version: conversationVersion,
    });
    if (deniedRead !== 404 || deniedWrite !== 403 || deniedDelete !== 404 || deniedAppend !== 404) {
      throw new Error('owner_or_csrf_boundary_failed');
    }

    const initialOwnerB = ownerB;
    await pageB.locator('.auth-signed-in button').first().click();
    await pageB.locator('.auth-entry > button').waitFor({ state: 'visible' });
    if (await apiStatus(pageB, '/api/v1/auth/me', 'GET') !== 401) throw new Error('logout_session_still_valid');
    await signIn(pageB, controlPort, controlToken, phones[1]);
    if (!ownerB || !csrfB || ownerB !== initialOwnerB || ownerB === ownerA) throw new Error('user_b_session_restore_failed');

    pageA.once('dialog', dialog => dialog.accept());
    await pageA.locator('.history-trip').filter({ hasText: 'سفر ۳ روزه به شیراز به همراه خانواده' }).locator('button').nth(1).click();
    await pageA.waitForFunction(() => document.querySelectorAll('.history-trip').length === 0);

    // Create a second persisted trip so account deletion proves cascade cleanup.
    await pageA.locator('.journey-action').waitFor({ state: 'visible' });
    await pageA.locator('.journey-action').click();
    await pageA.locator('.history-trip').waitFor({ state: 'visible' });
    pageA.once('dialog', dialog => dialog.accept());
    await pageA.locator('.auth-signed-in button').nth(1).click();
    await pageA.locator('.auth-entry > button').waitFor({ state: 'visible' });
    if (await apiStatus(pageA, '/api/v1/auth/me', 'GET') !== 401) throw new Error('deleted_session_still_valid');
    const deletedA = await checkedControl(controlPort, controlToken, { action: 'account_state', user_id: ownerA, phone: phones[0] });
    if (deletedA.users || deletedA.sessions || deletedA.trips || deletedA.conversations || deletedA.messages || deletedA.otp_challenges || deletedA.verified_phones) {
      throw new Error('account_data_cascade_incomplete');
    }

    const deleteB = await apiStatus(pageB, '/api/v1/auth/me', 'DELETE', { 'X-CSRF-Token': csrfB });
    if (deleteB !== 204 || await apiStatus(pageB, '/api/v1/auth/me', 'GET') !== 401) throw new Error('second_account_delete_failed');
    const deletedB = await checkedControl(controlPort, controlToken, { action: 'account_state', user_id: ownerB, phone: phones[1] });
    if (deletedB.users || deletedB.sessions || deletedB.trips || deletedB.conversations || deletedB.messages || deletedB.otp_challenges || deletedB.verified_phones) {
      throw new Error('second_account_data_cascade_incomplete');
    }
    if (successfulExternalResponses || pageErrors) throw new Error('browser_network_or_runtime_error');
    await contextB.close();
    await contextA.close();
    console.log(JSON.stringify({ status: 'passed', locales: ['fa-IR', 'en-US', 'ar'], verified_empty_catalogue: true, owner_and_csrf_checks: true, deletion_and_session_invalidation: true, external_requests_blocked: externalRequests }));
  } finally {
    if (browser) await browser.close();
    if (web && web.exitCode === null) web.kill();
    if (api && safeToCleanup) {
      try { await checkedControl(controlPort, controlToken, { action: 'cleanup_phones', phones }); } catch { /* process teardown follows */ }
    }
    if (api?.child && api.child.exitCode === null) api.child.kill();
    pipe?.close();
  }
}

main().catch(error => {
  // Never print exception details that might contain user or provider data.
  console.error(`Traveler E2E failed: ${String(error?.message || 'unknown').replace(/[^a-z0-9_-]/gi, '_').slice(0, 80)}`);
  process.exitCode = 1;
});
