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

const containsFortyFive = value => /(?:45|۴۵|٤٥)/u.test(String(value ?? ''));
const containsToman = value => /(?:تومان|toman)/iu.test(String(value ?? ''));
const containsMillion = value => /(?:million|میلیون|مليون)/iu.test(String(value ?? ''));

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

function realChatConfiguration() {
  const provider = process.env.RAHGARD_REAL_CHAT_PROVIDER?.trim().toLowerCase() || '';
  if (!provider) return null;
  if (!['lm_studio', 'remote_vllm', 'forced_outage'].includes(provider)) throw new Error('invalid_real_chat_provider');
  const endpoint = process.env.RAHGARD_REAL_CHAT_ENDPOINT || '';
  const model = process.env.RAHGARD_REAL_CHAT_MODEL || '';
  const token = process.env.RAHGARD_REAL_CHAT_TOKEN || '';
  let parsed;
  try { parsed = new URL(endpoint); } catch { throw new Error('real_chat_endpoint_invalid'); }
  if (provider === 'lm_studio' || provider === 'forced_outage') {
    const port = Number(process.env.RAHGARD_REAL_CHAT_LOOPBACK_HTTP_PORT || '');
    if (parsed.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(parsed.hostname)
      || !Number.isInteger(port) || port < 1024 || port > 65535 || Number(parsed.port) !== port
      || parsed.pathname !== '/v1/chat/completions' || parsed.search || parsed.hash
      || parsed.username || parsed.password || !model || !token) {
      throw new Error('local_chat_must_use_explicit_loopback_chat_endpoint');
    }
    return { provider, endpoint, model, token, loopbackPort: port };
  }
  if (parsed.protocol !== 'https:' || parsed.hostname !== 'llm.hinaa.ir'
    || parsed.pathname !== '/v1/chat/completions' || parsed.search || parsed.hash
    || parsed.username || parsed.password || model !== 'TaHa1_VL' || !token) {
    throw new Error('remote_vllm_must_use_approved_https_endpoint_model_and_private_token');
  }
  return { provider, endpoint, model, token, loopbackPort: null };
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
  let closed = false;
  const reader = createInterface({ input: client.stdout });
  // A startup failure must be reported as an early child exit, not a
  // misleading timeout after Python has already closed its stdout.
  reader.on('close', () => {
    closed = true;
    while (waiting.length) waiting.shift()({ ok: false, event: 'process_closed' });
  });
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
      if (closed) return Promise.resolve({ ok: false, event: 'process_closed' });
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
  const realChat = realChatConfiguration();
  const realGeoMode = process.env.RAHGARD_REAL_GEO_E2E === '1';
  const nationalCatalogueMode = process.env.RAHGARD_NATIONAL_CATALOGUE_E2E === '1';
  if (realGeoMode && process.env.RAHGARD_RUN_GEO_QA !== '1') {
    throw new Error('real_geo_e2e_missing_explicit_disposable_qa_opt_in');
  }

  const childEnv = runtimeEnv({
    AUTH_INTEGRATION_TESTS: '1',
    RAHGARD_REAL_GEO_E2E: realGeoMode ? '1' : '0',
    RAHGARD_RUN_GEO_QA: realGeoMode ? '1' : '0',
    RAHGARD_NATIONAL_CATALOGUE_E2E: nationalCatalogueMode ? '1' : '0',
    AUTH_TEST_DATABASE_HOST: process.env.AUTH_TEST_DATABASE_HOST,
    AUTH_TEST_DATABASE_PORT: process.env.AUTH_TEST_DATABASE_PORT,
    AUTH_TEST_DATABASE_NAME: process.env.AUTH_TEST_DATABASE_NAME,
    AUTH_TEST_DATABASE_USER: process.env.AUTH_TEST_DATABASE_USER,
    AUTH_TEST_DATABASE_PASSWORD: process.env.AUTH_TEST_DATABASE_PASSWORD,
    AUTH_TEST_DATABASE_MARKER: process.env.AUTH_TEST_DATABASE_MARKER,
    ...(nationalCatalogueMode || realChat ? {
      AUTH_TEST_DATABASE_OWNER_PASSWORD: process.env.AUTH_TEST_DATABASE_OWNER_PASSWORD,
    } : {}),
    E2E_API_PORT: String(apiPort),
    E2E_WEB_ORIGIN: webOrigin,
    E2E_CONTROL_PORT: String(controlPort),
    E2E_CONTROL_TOKEN: controlToken,
    PYTHONIOENCODING: 'utf-8',
    ...(realChat ? {
      RAHGARD_REAL_CHAT_PROVIDER: realChat.provider,
      RAHGARD_REAL_CHAT_ENDPOINT: realChat.endpoint,
      RAHGARD_REAL_CHAT_MODEL: realChat.model,
      RAHGARD_REAL_CHAT_TOKEN: realChat.token,
      ...(realChat.loopbackPort ? { RAHGARD_REAL_CHAT_LOOPBACK_HTTP_PORT: String(realChat.loopbackPort) } : {}),
    } : {}),
    TOURISM_RAG_ENABLED: ownerRag.enabled ? 'true' : 'false',
    ...(ownerRag.enabled ? {
      TOURISM_RAG_API_URL: ownerRag.url,
      TOURISM_RAG_API_TOKEN: ownerRag.token,
    } : {}),
  });
  const child = spawn(python, ['tests/traveler_e2e_server.py'], {
    cwd: backendRoot,
    env: childEnv,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  });
  // Python only emits stable exception class labels to stderr. Retain a small
  // bounded buffer internally; never print a Python traceback or credentials.
  let safeErrorType = '';
  let safeErrorPhase = '';
  let safeAssistantFailure = '';
  let safeChatUpstreamStatus = '';
  let safeCatalogueFailure = '';
  child.stderr.on('data', chunk => {
    const safeChunk = chunk.toString('utf8');
    const upstreamStatusMatch = safeChunk.match(/chat\.upstream\.unavailable status_code=(\d{3})/);
    if (upstreamStatusMatch) safeChatUpstreamStatus = upstreamStatusMatch[1];
    const assistantMatch = safeChunk.match(/assistant\.turn\.failed phase=([a-z_]+) error_type=([A-Za-z]+)/);
    if (assistantMatch) safeAssistantFailure = `${assistantMatch[1]}_${assistantMatch[2]}`;
    const catalogueMatch = safeChunk.match(/catalogue_review\.(decision|publication)_(failed|denied) phase=([a-z_]+) sqlstate=([A-Z0-9]+)(?: error_type=([A-Za-z]+))?/);
    if (catalogueMatch) safeCatalogueFailure = `${catalogueMatch[1]}_${catalogueMatch[2]}_${catalogueMatch[3]}_${catalogueMatch[4]}_${catalogueMatch[5] || 'unknown'}`;
    const match = safeChunk.match(/E2E server failed closed: ([A-Za-z]+Error)/);
    if (match) {
      safeErrorType = match[1].toLowerCase();
      const phaseMatch = safeChunk.match(/phase=([a-z_]+)/);
      if (phaseMatch) safeErrorPhase = phaseMatch[1];
    }
  });
  child.on('error', () => { safeErrorType = 'process_spawn_error'; });
  const pipe = makePipe(child);
  let ready;
  try {
    ready = await pipe.next(25_000);
  } catch {
    child.kill();
    throw new Error('guarded_api_ready_timeout');
  }
  if (!ready?.ok || ready.event !== 'ready') {
    child.kill();
    throw new Error('guarded_api_start_failed_' + (safeErrorType || ready?.event || 'unknown')
      + (safeErrorPhase ? `_phase_${safeErrorPhase}` : ''));
  }
  return { child, pipe, controlPort, controlToken, ownerRagEnabled: ownerRag.enabled,
    safeAssistantFailure: () => safeAssistantFailure,
    safeChatUpstreamStatus: () => safeChatUpstreamStatus,
    safeCatalogueFailure: () => safeCatalogueFailure };
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
  await page.locator('.auth-entry > button').first().click();
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
    prompt: '\u0631\u062d\u0644\u0629 \u0644\u0645\u062f\u0629 10 \u0623\u064a\u0627\u0645 \u0625\u0644\u0649 Shiraz \u0628\u0645\u064a\u0632\u0627\u0646\u064a\u0629 20 \u0645\u0644\u064a\u0648\u0646 \u062f\u0631\u0647\u0645؛ \u0623\u0641\u0636\u0644 \u0627\u0644\u0645\u0633\u0627\u0631\u0627\u062a \u0627\u0644\u0645\u0639\u0628\u062f\u0629؛ \u0627\u062d\u062a\u064a\u0627\u062c\u0627\u062a \u062d\u0631\u0643\u064a\u0629 \u0636\u0631\u0648\u0631\u064a\u0629؛ \u064a\u062c\u0628 \u062a\u062c\u0646\u0628 \u0627\u0644\u0637\u0631\u0642 \u0627\u0644\u0648\u0639\u0631\u0629.' ,
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
    const safePath = new URL(path, webOrigin).pathname.replace(/[0-9a-f]{8}-[0-9a-f-]{27,}/gi, ':id');
    throw new Error(`browser_api_${method.toLowerCase()}_${response.status()}_${payload?.error?.code ?? 'failed'}_${safePath.replace(/[^a-zA-Z0-9_/:.-]/g, '_')}`);
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

async function browserApi(page, path, method, csrf, body) {
  const response = await page.request.fetch(`${webOrigin}${path}`, {
    method,
    headers: {
      Origin: webOrigin,
      ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
    },
    ...(body === undefined ? {} : { data: body }),
    timeout: 30_000,
  });
  let payload = null;
  try { payload = await response.json(); } catch { /* status is retained for negative cases */ }
  return { status: response.status(), payload };
}

async function runNationalCatalogueAcceptance(browser, api, audit, artifactRoot) {
  const archivePath = process.env.RAHGARD_OWNER_ARCHIVE_PATH;
  if (!archivePath || !existsSync(archivePath)) throw new Error('national_acceptance_owner_archive_missing');
  const context = await browser.newContext({ locale: 'en-US' });
  const page = await context.newPage();
  const trace = [];
  const networkTrace = [];
  let resolveArchiveUploadResponse;
  const archiveUploadResponse = new Promise(resolvePromise => { resolveArchiveUploadResponse = resolvePromise; });
  page.on('request', request => {
    const url = new URL(request.url());
    if (url.origin === webOrigin && url.pathname.startsWith('/api/')) {
      const body = request.postDataBuffer();
      networkTrace.push({ phase: 'request', method: request.method(), path: url.pathname, bodyBytes: body?.length ?? 0 });
    }
  });
  page.on('response', response => {
    const url = new URL(response.url());
    if (url.origin === webOrigin && url.pathname.startsWith('/api/')) {
      networkTrace.push({ phase: 'response', method: response.request().method(), path: url.pathname, status: response.status() });
      if (url.pathname === '/api/v1/catalogue-review/archives') {
        const dir = resolve(artifactRoot, 'national-catalogue');
        mkdirSync(dir, { recursive: true });
        writeFileSync(resolve(dir, 'archive-upload-response.json'), JSON.stringify({ status: response.status() }));
        resolveArchiveUploadResponse(response);
      }
    }
  });
  page.on('requestfailed', request => {
    const url = new URL(request.url());
    if (url.origin === webOrigin && url.pathname.startsWith('/api/')) {
      networkTrace.push({ phase: 'failed', method: request.method(), path: url.pathname, error: request.failure()?.errorText?.slice(0, 120) ?? 'unknown' });
      if (url.pathname === '/api/v1/catalogue-review/archives') {
        const dir = resolve(artifactRoot, 'national-catalogue');
        mkdirSync(dir, { recursive: true });
        writeFileSync(resolve(dir, 'archive-upload-failed-event.json'), JSON.stringify({ method: request.method(), error: request.failure()?.errorText?.slice(0, 120) ?? 'unknown' }));
      }
    }
  });
  page.on('pageerror', error => networkTrace.push({ phase: 'pageerror', name: error.name }));
  const operatorPhone = syntheticPhone();
  const companyPhone = syntheticPhone();
  const tenantTwoPhone = syntheticPhone();
  const travelerPhone = syntheticPhone();
  let currentPhone = null;
  let currentIdentity = null;
  let stagedSummary = null;
  let publishedPlace = null;
  let organization = null;
  let partnerSummary = null;
  let travelerSummary = null;
  reportResponseWaitCallsite(page);
  const milestone = name => console.log(`[national-e2e] ${name}`);
  await attachBrowserGuards(page, audit);
  try {
    const baselineCounts = await checkedControl(api.controlPort, api.controlToken, { action: 'national_catalogue_counts' });
    if (!baselineCounts.ok) throw new Error('national_catalogue_baseline_counts_unavailable');
    await page.goto(webOrigin, { waitUntil: 'domcontentloaded' });
    await selectAndVerifyLocale(page, 'en-US');
    currentPhone = operatorPhone;
    currentIdentity = await signIn(page, api.controlPort, api.controlToken, operatorPhone);
    const grant = await checkedControl(api.controlPort, api.controlToken, {
      action: 'grant_catalogue_capabilities', user_id: currentIdentity.userId,
      capabilities: ['candidate_review', 'source_review', 'catalogue_publish'],
    });
    if (!grant.ok) throw new Error('national_test_operator_capability_grant_failed');
    await page.goto(`${webOrigin}/admin/catalogue-review`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('heading', { name: 'Catalogue review and publication' }).waitFor({ state: 'visible' });
    milestone('operator authenticated; catalogue review UI loaded');
    const reviewBootstrap = await Promise.all([
      requestBrowserJson(page, '/api/v1/catalogue-review/candidates?limit=50&kind=destination_identity', 'GET', undefined, undefined, trace),
      requestBrowserJson(page, '/api/v1/catalogue-review/sources?limit=100', 'GET', undefined, undefined, trace),
      requestBrowserJson(page, '/api/v1/catalogue-review/sources/pending-verification', 'GET', undefined, undefined, trace),
      requestBrowserJson(page, '/api/v1/catalogue-review/sources/verified', 'GET', undefined, undefined, trace),
      requestBrowserJson(page, '/api/v1/catalogue-review/candidates/approved', 'GET', undefined, undefined, trace),
    ]);
    if (reviewBootstrap.some((result, index) => !Array.isArray(result.items) && index !== 3)) {
      throw new Error('national_operator_review_api_contract_unavailable');
    }

    const uploadInput = page.locator('input[type="file"]');
    await uploadInput.setInputFiles(archivePath);
    const uploadState = await uploadInput.evaluate(element => ({ count: element.files?.length ?? 0, name: element.files?.[0]?.name ?? '' }));
    if (uploadState.count !== 1 || !uploadState.name.toLowerCase().endsWith('.zip')) throw new Error('national_archive_file_not_selected');
    const uploadButton = page.locator('.catalogue-review > section.partner-card button.primary');
    if (await uploadButton.isDisabled()) throw new Error('national_archive_upload_button_disabled_after_file_selection');
    const noticesBeforeUpload = await page.locator('[role="alert"],[role="status"]').allTextContents();
    const operatorDir = resolve(artifactRoot, 'national-catalogue');
    mkdirSync(operatorDir, { recursive: true });
    await page.screenshot({ path: resolve(operatorDir, 'operator-before-staging.png'), fullPage: true, animations: 'disabled' });
    await page.evaluate(() => {
      window.__rahgardNationalUploadClicked = false;
      window.__rahgardNationalUploadFetches = [];
      window.__rahgardNationalUploadFetchError = null;
      const nativeFetch = window.fetch.bind(window);
      window.fetch = (input, init) => {
        const path = new URL(typeof input === 'string' ? input : input.url, window.location.href).pathname;
        if (path === '/api/v1/catalogue-review/archives') window.__rahgardNationalUploadFetches.push({ method: init?.method ?? 'GET' });
        return nativeFetch(input, init).catch(error => {
          if (path === '/api/v1/catalogue-review/archives') window.__rahgardNationalUploadFetchError = `${error.name}:${error.message}`.slice(0, 160);
          throw error;
        });
      };
      const button = document.querySelector('.catalogue-review > section.partner-card button.primary');
      button?.addEventListener('click', () => { window.__rahgardNationalUploadClicked = true; }, { capture: true, once: true });
    });
    milestone('submitting selected archive through the operator UI');
    await uploadButton.click({ timeout: 15_000 });
    milestone('archive upload action dispatched by the browser');
    await page.waitForTimeout(500);
    writeFileSync(resolve(operatorDir, 'archive-upload-network-checkpoint.json'),
      `${JSON.stringify({ fileName: uploadState.name, networkTrace: networkTrace.filter(item => item.path === '/api/v1/catalogue-review/archives') }, null, 2)}\n`, 'utf8');
    if (!networkTrace.some(item => item.phase === 'request' && item.path === '/api/v1/catalogue-review/archives')) {
      const uiState = await page.evaluate(() => ({
        nativeClickCaptured: window.__rahgardNationalUploadClicked === true,
        appFetchCalls: window.__rahgardNationalUploadFetches,
        appFetchError: window.__rahgardNationalUploadFetchError,
        upload: Array.from(document.querySelectorAll('.catalogue-review > section.partner-card button.primary'))
          .map(button => ({ text: button.textContent?.trim(), disabled: button.disabled, type: button.type })),
        selectedFileCount: document.querySelector('input[type="file"]')?.files?.length ?? 0,
        visibleNotices: Array.from(document.querySelectorAll('[role="alert"],[role="status"]')).map(item => item.textContent?.trim()).filter(Boolean),
      }));
      await page.screenshot({ path: resolve(operatorDir, 'operator-upload-after-click.png'), fullPage: true, animations: 'disabled' });
      writeFileSync(resolve(operatorDir, 'archive-upload-failure.json'), `${JSON.stringify({ fileName: uploadState.name, noticesBeforeUpload, reviewBootstrapCounts: reviewBootstrap.map(result => Array.isArray(result.items) ? result.items.length : 'no_items_array'), uiState, networkTrace }, null, 2)}\n`, 'utf8');
      throw new Error(`national_archive_upload_click_did_not_send_request_${JSON.stringify(networkTrace.slice(-20))}`);
    }
    let uploadDeadline;
    const uploaded = await Promise.race([
      archiveUploadResponse,
      new Promise(resolvePromise => {
        uploadDeadline = setTimeout(() => resolvePromise(null), 90_000);
        uploadDeadline.unref();
      }),
    ]);
    if (uploadDeadline) clearTimeout(uploadDeadline);
    if (!uploaded) {
      const uiState = await page.evaluate(() => ({
        appFetchError: window.__rahgardNationalUploadFetchError,
        appFetchCalls: window.__rahgardNationalUploadFetches,
        notices: Array.from(document.querySelectorAll('[role="alert"]')).map(node => node.textContent?.trim()).filter(Boolean),
      }));
      writeFileSync(resolve(operatorDir, 'archive-upload-failure.json'), `${JSON.stringify({ fileName: uploadState.name, uiState, networkTrace: networkTrace.filter(item => item.path === '/api/v1/catalogue-review/archives') }, null, 2)}\n`, 'utf8');
      throw new Error('national_archive_upload_response_missing');
    }
    if (uploaded.status() !== 202) throw new Error(`national_browser_archive_upload_failed_${uploaded.status()}`);
    // Validate committed rows through the isolated PostgreSQL control socket;
    // this avoids relying on Playwright to consume the optional upload summary
    // body after the UI has already received a successful HTTP response.
    const stagedCounts = await checkedControl(api.controlPort, api.controlToken, { action: 'national_catalogue_counts' });
    stagedSummary = {
      archive_sha256: '7e9a27654535590f593aeea8e9f7ba9422fb128ca2c4fc93129061c544aff397',
      rows_present: stagedCounts.candidates,
      candidate_rows_by_kind: {
        destination_identity: stagedCounts.identities,
        discovery_lead: stagedCounts.leads,
      },
      source_rows_present: stagedCounts.source_candidates,
      publication_approved: false,
    };
    milestone(`owner archive is present: ${stagedSummary.rows_present} candidate rows`);
    if (stagedSummary.rows_present !== 700
        || stagedSummary.candidate_rows_by_kind.destination_identity !== 167
        || stagedSummary.candidate_rows_by_kind.discovery_lead !== 533
        || stagedSummary.source_rows_present !== 257) {
      throw new Error('national_browser_archive_staging_counts_mismatch');
    }
    trace.push({ method: 'POST', path: '/api/v1/catalogue-review/archives', status: uploaded.status() });

    const key = 'unesco-armenian-st-thaddeus-v1';
    let candidatePage = await requestBrowserJson(page,
      '/api/v1/catalogue-review/candidates?limit=100&kind=destination_identity', 'GET');
    let candidate = candidatePage.items.find(item => item.source_record_key === key);
    let candidatePages = 1;
    while (!candidate && candidatePage.next_cursor) {
      if (candidatePages++ >= 10) throw new Error('national_candidate_review_pagination_limit');
      candidatePage = await requestBrowserJson(page,
        `/api/v1/catalogue-review/candidates?limit=100&kind=destination_identity&after=${encodeURIComponent(candidatePage.next_cursor)}`,
        'GET');
      candidate = candidatePage.items.find(item => item.source_record_key === key);
    }
    if (!candidate || candidate.candidate_status !== 'needs_review' || candidate.candidate_kind !== 'destination_identity') {
      throw new Error('national_browser_target_archive_candidate_not_in_review_queue');
    }
    milestone('operator inspected target archive identity in review queue');
    const searchInput = page.getByLabel('Search', { exact: true });
    // The candidate itself is inspected in the real UI; evidence and review
    // mutations below use the same authenticated FastAPI endpoints as the UI.
    await searchInput.fill(candidate.proposed_name_fa || candidate.raw_name || key);
    await page.getByRole('button', { name: 'Reload', exact: true }).click();
    const card = page.locator(`.candidate-review-card[data-candidate-id="${candidate.candidate_id}"]`);
    await card.waitFor({ state: 'visible', timeout: 30_000 });
    if (!(await card.textContent())?.includes('destination_identity')) throw new Error('operator_candidate_inspection_missing');
    await page.screenshot({ path: resolve(operatorDir, 'operator-candidate-review.png'), fullPage: true, animations: 'disabled' });

    const inspectedAt = new Date().toISOString();
    const sources = [
      { name: 'UNESCO World Heritage Centre - component maps', publisher: 'UNESCO World Heritage Centre', title: 'Armenian Monastic Ensembles of Iran - Maps', url: 'https://whc.unesco.org/en/list/1262/maps/', excerpt: '1262-001 The Monastery of Saint Thaddeus N39 5 32.00 E44 32 40.00' },
      { name: 'Visit Iran - Saint Thaddeus detail', publisher: 'Visit Iran', title: 'Monastery of Saint Thaddeus or Qara Kelisa', url: 'https://visitiran.ir/attraction/monastery-saint-thaddeus-or-qara-kelisa', excerpt: 'in Bah Bah Jik County, 20km of Chaldoran City, is located in the highest part of the West Azerbaijan Province' },
      { name: 'UNESCO World Heritage Centre - property description', publisher: 'UNESCO World Heritage Centre', title: 'Armenian Monastic Ensembles of Iran', url: 'https://whc.unesco.org/en/list/1262/', excerpt: 'consists of three monastic ensembles of the Armenian Christian faith' },
    ];
    const sourceIds = [];
    const sourceSummaries = [];
    await page.getByRole('button', { name: 'Sources', exact: true }).click();
    for (const source of sources) {
      const sourceForm = page.locator('.catalogue-review article.partner-card')
        .filter({ has: page.getByRole('heading', { name: 'Register source for inspection', exact: true }) });
      await sourceForm.getByLabel('Source name').fill(source.name);
      await sourceForm.getByLabel('Source type').fill('official_tourism');
      await sourceForm.getByLabel('Publisher').fill(source.publisher);
      await sourceForm.getByLabel('Page title').fill(source.title);
      await sourceForm.getByLabel('HTTPS page URL').fill(source.url);
      await sourceForm.getByLabel('Why this source is relevant').fill('Directly inspected page used for one archive candidate evidence review.');
      const registrationWait = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/catalogue-review/sources/register'
        && response.request().method() === 'POST');
      await sourceForm.getByRole('button', { name: 'Register pending source', exact: true }).click();
      const registeredResponse = await registrationWait;
      if (registeredResponse.status() !== 201) throw new Error(`operator_source_registration_failed_${registeredResponse.status()}`);
      trace.push({ method: 'POST', path: '/api/v1/catalogue-review/sources/register', status: registeredResponse.status() });
      const pendingCard = page.locator('.catalogue-review article.partner-card')
        .filter({ hasText: source.url })
        .filter({ has: page.getByRole('button', { name: 'Verify source inspection', exact: true }) });
      await pendingCard.waitFor({ state: 'visible', timeout: 15_000 });
      await pendingCard.getByLabel('Publisher').fill(source.publisher);
      await pendingCard.getByLabel('Page title').fill(source.title);
      await pendingCard.getByLabel('Direct source excerpt (max 25 words)').fill(source.excerpt);
      const verificationWait = page.waitForResponse(response => /^\/api\/v1\/catalogue-review\/sources\/\d+\/verification$/.test(new URL(response.url()).pathname)
        && response.request().method() === 'POST');
      await pendingCard.getByRole('button', { name: 'Verify source inspection', exact: true }).click();
      const verifiedResponse = await verificationWait;
      if (verifiedResponse.status() !== 201) {
        throw new Error(`operator_source_review_not_verified_${verifiedResponse.status()}`);
      }
      const verificationPath = new URL(verifiedResponse.url()).pathname;
      const sourceId = Number(verificationPath.match(/\/sources\/(\d+)\/verification$/)?.[1]);
      if (!Number.isSafeInteger(sourceId)) throw new Error('operator_source_review_id_unavailable');
      trace.push({ method: 'POST', path: verificationPath, status: verifiedResponse.status() });
      sourceIds.push(sourceId);
      sourceSummaries.push({ publisher: source.publisher, title: source.title, url: source.url, status: 'verified' });
    }
    milestone('operator registered and directly reviewed three source records');

    await page.getByRole('button', { name: 'Candidates', exact: true }).click();
    await page.getByLabel('Search', { exact: true }).fill(candidate.proposed_name_fa || candidate.raw_name || key);
    await page.getByRole('button', { name: 'Reload', exact: true }).click();
    await page.locator(`.candidate-review-card[data-candidate-id="${candidate.candidate_id}"]`).waitFor({ state: 'visible' });

    const lat = Number(candidate.proposed_latitude).toFixed(7);
    const lon = Number(candidate.proposed_longitude).toFixed(7);
    const evidenceSpecs = [
      { source_id: sourceIds[0], field_key: 'identity', claim_value: candidate.proposed_name_fa, evidence_excerpt: '1262-001 The Monastery of Saint Thaddeus' },
      { source_id: sourceIds[1], field_key: 'province', claim_value: candidate.raw_province, evidence_excerpt: sources[1].excerpt },
      { source_id: sourceIds[0], field_key: 'coordinates', claim_value: `${lat},${lon}`, evidence_excerpt: sources[0].excerpt },
      { source_id: sourceIds[2], field_key: 'description', claim_value: 'One of the three monastic ensembles of the Armenian Christian faith described by UNESCO.', evidence_excerpt: sources[2].excerpt },
    ];
    const evidenceRows = [];
    const candidateCard = page.locator(`.candidate-review-card[data-candidate-id="${candidate.candidate_id}"]`);
    for (const evidence of evidenceSpecs) {
      const source = sources[sourceIds.indexOf(evidence.source_id)];
      await candidateCard.getByLabel('Verified source').selectOption(String(evidence.source_id));
      await candidateCard.getByLabel('Field').selectOption(evidence.field_key);
      await candidateCard.getByLabel('Reviewed claim value').fill(evidence.claim_value);
      await candidateCard.getByLabel('Direct source excerpt (max 25 words)').fill(evidence.evidence_excerpt);
      const evidenceWait = page.waitForResponse(response => new URL(response.url()).pathname === `/api/v1/catalogue-review/candidates/${candidate.candidate_id}/evidence`
        && response.request().method() === 'POST');
      await candidateCard.getByRole('button', { name: 'Add evidence', exact: true }).click();
      const evidenceResponse = await evidenceWait;
      if (evidenceResponse.status() !== 201) throw new Error(`operator_candidate_evidence_failed_${evidenceResponse.status()}`);
      trace.push({ method: 'POST', path: `/api/v1/catalogue-review/candidates/${candidate.candidate_id}/evidence`, status: evidenceResponse.status() });
      await candidateCard.locator('ul li').filter({ hasText: evidence.claim_value }).waitFor({ state: 'visible' });
      evidenceRows.push({ field_key: evidence.field_key, source_id: evidence.source_id });
    }
    const reviewReason = 'Reviewed identity, province, map-reference coordinate role and description against directly inspected source pages.';
    await candidateCard.getByLabel('Decision reason').fill(reviewReason);
    const decisionWait = page.waitForResponse(response => new URL(response.url()).pathname === `/api/v1/catalogue-review/candidates/${candidate.candidate_id}/decision`
      && response.request().method() === 'POST');
    await candidateCard.getByRole('button', { name: 'Approve new identity', exact: true }).click();
    const decisionResponse = await decisionWait;
    if (decisionResponse.status() !== 200) throw new Error(`operator_identity_decision_invalid_${decisionResponse.status()}_${api.safeCatalogueFailure() || 'no_db_diagnostic'}`);
    trace.push({ method: 'POST', path: `/api/v1/catalogue-review/candidates/${candidate.candidate_id}/decision`, status: decisionResponse.status() });
    await page.getByRole('button', { name: 'Publication queue', exact: true }).click();
    const publicationCard = page.locator('.partner-card').filter({ hasText: candidate.proposed_name_fa });
    await publicationCard.waitFor({ state: 'visible' });
    const destinationKey = 'archive-st-thaddeus-browser-e2e-v1';
    await publicationCard.getByLabel('Destination key').fill(destinationKey);
    await publicationCard.getByLabel('Coordinate role').selectOption('property_reference');
    const publishWait = page.waitForResponse(response => new URL(response.url()).pathname === `/api/v1/catalogue-review/candidates/${candidate.candidate_id}/publish`
      && response.request().method() === 'POST');
    await publicationCard.getByRole('button', { name: 'Publish destination', exact: true }).click();
    const publishResponse = await publishWait;
    if (publishResponse.status() !== 201) {
      throw new Error(`operator_browser_publication_failed_${publishResponse.status()}_${api.safeCatalogueFailure() || 'no_db_diagnostic'}`);
    }
    milestone('operator reviewed evidence, approved identity, and published one canonical destination');
    trace.push({ method: 'POST', path: `/api/v1/catalogue-review/candidates/${candidate.candidate_id}/publish`, status: publishResponse.status() });
    const publicCatalogue = await requestBrowserJson(page, '/api/v2/catalog/destinations?limit=100', 'GET', undefined, undefined, trace);
    publishedPlace = publicCatalogue.items.find(item => item.destination_key === destinationKey);
    if (!publishedPlace || publicCatalogue.items.some(item => item.is_synthetic)) {
      throw new Error('operator_unpublished_candidate_leaked_or_archive_place_missing');
    }
    const reviewQueue = await requestBrowserJson(page,
      '/api/v1/catalogue-review/candidates?limit=100&kind=discovery_lead', 'GET');
    if (reviewQueue.items.length !== 100 || reviewQueue.items.some(item => item.candidate_status !== 'needs_review')) {
      throw new Error('operator_discovery_leads_not_left_unpublished');
    }
    const canaryLead = reviewQueue.items.find(item => item.raw_name && !publicCatalogue.items.some(place =>
      String(place.canonical_name ?? '').toLocaleLowerCase() === String(item.raw_name).toLocaleLowerCase()));
    if (canaryLead) {
      const leakCheck = await requestBrowserJson(page,
        `/api/v2/catalog/destinations?limit=100&q=${encodeURIComponent(canaryLead.raw_name)}`, 'GET');
      if (leakCheck.items.some(item => String(item.canonical_name ?? '').toLocaleLowerCase() === String(canaryLead.raw_name).toLocaleLowerCase())) {
        throw new Error('unpublished_archive_lead_visible_in_public_catalogue');
      }
    }

    // Company tenant one: browser-authenticated organization/service/offer lifecycle.
    await page.locator('.auth-signed-in button').first().click();
    await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
    currentPhone = companyPhone;
    currentIdentity = await signIn(page, api.controlPort, api.controlToken, companyPhone);
    await page.goto(`${webOrigin}/partners`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('heading', { name: 'Partner workspace' }).waitFor({ state: 'visible' });
    const partnerSubmit = async (button, pathPattern, expectedStatus = 201) => {
      const pending = page.waitForResponse(response => pathPattern.test(new URL(response.url()).pathname)
        && response.request().method() === 'POST');
      await button.click();
      const response = await pending;
      if (response.status() !== expectedStatus) throw new Error(`partner_ui_submit_failed_${response.status()}`);
      trace.push({ method: 'POST', path: new URL(response.url()).pathname, status: response.status() });
    };
    const orgForm = page.locator('form.partner-card').filter({ has: page.getByRole('heading', { name: 'Organization', exact: true }) });
    await orgForm.getByLabel('Legal name').fill('Rahgard Acceptance Travel Co');
    await orgForm.getByLabel('Display name').fill('Acceptance Travel Co');
    await partnerSubmit(orgForm.getByRole('button', { name: 'Create organization', exact: true }), /^\/api\/v1\/partners\/organizations$/);
    const organizationRows = await requestBrowserJson(page, '/api/v1/partners/organizations', 'GET', undefined, undefined, trace);
    const organizationRow = organizationRows.items.find(item => item.display_name === 'Acceptance Travel Co');
    organization = organizationRow?.organization_id;
    if (!organization) throw new Error('partner_organization_not_created_from_browser_form');
    const approvedTestOrganization = await controlRequest(api.controlPort, api.controlToken, {
      action: 'approve_isolated_test_organization', organization_id: organization,
      created_by: currentIdentity.userId, display_name: 'Acceptance Travel Co',
    });
    if (!approvedTestOrganization.ok) throw new Error(`isolated_test_company_approval_failed_${approvedTestOrganization.reason || 'unknown'}`);
    await page.locator('.partner-forms').waitFor({ state: 'visible', timeout: 15_000 });

    const serviceForm = page.locator('form.partner-card').filter({ has: page.getByRole('heading', { name: 'Service', exact: true }) });
    await serviceForm.getByLabel('Service name').fill('Saint Thaddeus guided visit');
    await serviceForm.getByLabel('Service description').fill('Private draft service for acceptance.');
    await serviceForm.getByLabel('Service key').fill('st-thaddeus-guided-visit');
    await serviceForm.getByLabel('Service type').fill('guided_visit');
    await partnerSubmit(serviceForm.getByRole('button', { name: 'Create service', exact: true }), /^\/api\/v1\/partners\/organizations\/[0-9a-f-]+\/services$/i);
    let workspace = await requestBrowserJson(page, `/api/v1/partners/organizations/${organization}/workspace`, 'GET', undefined, undefined, trace);
    const service = workspace.services.find(item => item.service_key === 'st-thaddeus-guided-visit');
    if (!service) throw new Error('partner_service_not_created_from_browser_form');
    await page.getByTestId('partner-service-select').selectOption(String(service.service_id));

    const linkForm = page.locator('form.partner-card').filter({ has: page.getByRole('heading', { name: 'Link service to a published destination', exact: true }) });
    await linkForm.getByLabel('Canonical destination').selectOption(String(publishedPlace.destination_id));
    await linkForm.getByLabel('Relationship').selectOption('at');
    await linkForm.getByLabel('Evidence note (optional)').fill('Acceptance relation to published canonical place.');
    await partnerSubmit(linkForm.getByRole('button', { name: 'Add destination link', exact: true }), /^\/api\/v1\/partners\/organizations\/[0-9a-f-]+\/services\/[0-9a-f-]+\/destinations$/i);

    const scheduleStart = '2030-11-20T10:00';
    const scheduleEnd = '2030-11-20T12:00';
    const scheduleForm = page.locator('form.partner-card').filter({ has: page.getByRole('heading', { name: 'Schedule', exact: true }) });
    await scheduleForm.getByLabel('Schedule type').selectOption('appointment');
    await scheduleForm.getByLabel('Time zone').fill('Asia/Tehran');
    await scheduleForm.getByLabel('Starts (optional)').fill(scheduleStart);
    await scheduleForm.getByLabel('Ends (optional)').fill(scheduleEnd);
    await partnerSubmit(scheduleForm.getByRole('button', { name: 'Create schedule', exact: true }), /^\/api\/v1\/partners\/organizations\/[0-9a-f-]+\/schedules$/i);
    workspace = await requestBrowserJson(page, `/api/v1/partners/organizations/${organization}/workspace`, 'GET', undefined, undefined, trace);
    const schedule = workspace.schedules.find(item => item.schedule_type === 'appointment');
    if (!schedule) throw new Error('partner_schedule_not_created_from_browser_form');
    await page.getByTestId('partner-schedule-select').selectOption(String(schedule.schedule_id));

    const offerForm = page.locator('form.partner-card').filter({ has: page.getByRole('heading', { name: 'Offer', exact: true }) });
    await offerForm.getByLabel('Offer type').fill('guided_visit');
    await partnerSubmit(offerForm.getByRole('button', { name: 'Create offer', exact: true }), /^\/api\/v1\/partners\/organizations\/[0-9a-f-]+\/offers$/i);
    workspace = await requestBrowserJson(page, `/api/v1/partners/organizations/${organization}/workspace`, 'GET', undefined, undefined, trace);
    const offer = workspace.offers.find(item => item.offer_type === 'guided_visit');
    if (!offer) throw new Error('partner_offer_not_created_from_browser_form');
    await page.getByTestId('partner-offer-select').selectOption(String(offer.offer_id));

    const priceForm = page.locator('form.partner-card').filter({ has: page.getByRole('heading', { name: 'Price', exact: true }) });
    await priceForm.getByLabel('Amount').fill('1200000');
    await priceForm.getByLabel('Currency code').fill('IRR');
    await priceForm.getByLabel('Denomination').fill('Rial');
    await priceForm.getByLabel('Price unit').fill('per_person');
    await partnerSubmit(priceForm.getByRole('button', { name: 'Add price', exact: true }), /^\/api\/v1\/partners\/organizations\/[0-9a-f-]+\/prices$/i);

    const availabilityForm = page.locator('form.partner-card').filter({ has: page.getByRole('heading', { name: 'Availability', exact: true }) });
    await availabilityForm.getByLabel('Occurrence time').fill(scheduleStart);
    await availabilityForm.getByLabel('State').selectOption('unknown');
    await partnerSubmit(availabilityForm.getByRole('button', { name: 'Add availability', exact: true }), /^\/api\/v1\/partners\/organizations\/[0-9a-f-]+\/availability$/i);
    await page.reload({ waitUntil: 'domcontentloaded' });
    workspace = await requestBrowserJson(page, `/api/v1/partners/organizations/${organization}/workspace`, 'GET', undefined, undefined, trace);
    if (workspace.services.length !== 1 || workspace.destinations.length !== 1 || workspace.schedules.length !== 1
        || workspace.offers.length !== 1 || workspace.prices.length !== 1 || workspace.availability.length !== 1) {
      throw new Error('partner_workspace_data_not_persisted');
    }
    await page.screenshot({ path: resolve(operatorDir, 'partner-workspace-persisted.png'), fullPage: true, animations: 'disabled' });
    partnerSummary = { organizations: 1, services: workspace.services.length, linkedDestinations: workspace.destinations.length,
      schedules: workspace.schedules.length, offers: workspace.offers.length, prices: workspace.prices.length, availability: workspace.availability.length };
    milestone('partner workspace records persisted and reopened');

    // Tenant two cannot read or mutate tenant one's service data.
    await page.locator('.auth-signed-in button').first().click();
    await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
    currentPhone = tenantTwoPhone;
    currentIdentity = await signIn(page, api.controlPort, api.controlToken, tenantTwoPhone);
    const tenantTwo = await requestBrowserJson(page, '/api/v1/partners/organizations', 'POST', currentIdentity.csrfToken,
      { legal_name: 'Isolation Test Tenant', display_name: 'Isolation Tenant', organization_type: 'company', registration_country: 'IR' }, trace);
    const deniedRead = await browserApi(page, `/api/v1/partners/organizations/${organization}/workspace`, 'GET');
    const deniedWrite = await browserApi(page, `/api/v1/partners/organizations/${organization}/services`, 'POST', currentIdentity.csrfToken,
      { service_type: 'tour', service_key: 'forged-cross-tenant-write', locale: 'en-US', display_name: 'forged' });
    if (deniedRead.status !== 200 || deniedRead.payload?.services?.length !== 0
        || ![403, 422].includes(deniedWrite.status)) {
      throw new Error(`partner_cross_tenant_access_not_denied_${deniedRead.status}_${deniedWrite.status}`);
    }
    partnerSummary.crossTenantReadRows = deniedRead.payload.services.length;
    partnerSummary.crossTenantWriteStatus = deniedWrite.status;
    milestone('cross-tenant browser/API read and write denied');

    // Traveler searches the new archive-backed canonical identity and persists a
    // recommendation itinerary in FastAPI/PostgreSQL, then reopens after a new session.
    await page.locator('.auth-signed-in button').first().click();
    await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
    currentPhone = travelerPhone;
    currentIdentity = await signIn(page, api.controlPort, api.controlToken, travelerPhone);
    await page.goto(webOrigin, { waitUntil: 'domcontentloaded' });
    await selectAndVerifyLocale(page, 'en-US');
    const foundPlace = (await requestBrowserJson(page,
      `/api/v2/catalog/destinations?limit=100&q=${encodeURIComponent(publishedPlace.canonical_name)}`,
      'GET', undefined, undefined, trace)).items;
    const selected = foundPlace.find(item => item.destination_key === destinationKey);
    if (!selected) throw new Error('traveler_archive_destination_search_missing');
    const startRequest = '2-day trip from Chalderan to the Monastery of Saint Thaddeus in West Azerbaijan for 2 travelers, budget 30 million toman; gentle walks, mild weather and local cuisine';
    const interpreted = await requestBrowserJson(page, '/api/v1/requirements/interpret', 'POST', currentIdentity.csrfToken,
      { locale: 'en-US', request_text: startRequest }, trace);
    if (interpreted.requirements?.fields?.duration_days?.value !== 2) throw new Error('duration_null_parser_regression');
    const started = await requestBrowserJson(page, '/api/v1/conversations', 'POST', currentIdentity.csrfToken, {
      locale: 'en-US', request_text: startRequest,
      extracted_requirements: interpreted.requirements,
      traveler_timezone: 'Asia/Tehran', traveler_reference_date: '2026-11-16', idempotency_key: randomUUID(),
    }, trace);
    const trip = started.trip;
    if (!started.conversation?.conversation_id || !trip?.trip_id || trip.duration_days !== 2) throw new Error('traveler_conversation_duration_not_persisted');
    const confirmed = await requestBrowserJson(page, `/api/v1/trips/${trip.trip_id}`, 'PATCH', currentIdentity.csrfToken, {
      expected_version: trip.version,
      confirmed_requirements: {
        confirmation_source: 'traveler_reviewed', destinations: [selected.canonical_name], duration_days: 2,
        origin: 'Chalderan', travel_dates: { start: '2026-11-19', end: '2026-11-20' }, traveler_count: 2,
        accessibility: [], budget: { amount: 30, currency: 'TOMAN', unit: 'million toman', raw: '30 million toman' },
        soft_preferences: [], interests: ['heritage'], constraints: [],
        travel_difficulty: ['easy'], weather_preferences: ['mild'], local_cuisine: ['regional cuisine'],
        field_provenance: { destinations: 'traveler', duration_days: 'llm', origin: 'traveler', travel_dates: 'traveler',
          traveler_count: 'traveler', budget: 'traveler', interests: 'traveler', soft_preferences: 'traveler',
          travel_difficulty: 'llm', weather_preferences: 'traveler', local_cuisine: 'llm', constraints: 'traveler', accessibility: 'traveler' },
      },
      destination_ids: [String(selected.destination_id)],
      requirement_consent: { contract_version: 'recommendation-consent-v1', field_decisions: {}, advisory_acknowledged_fields: [] },
    }, trace);
    if (confirmed.version !== trip.version + 1 || confirmed.duration_days !== 2) throw new Error('traveler_profile_confirmation_failed');
    if (confirmed.confirmed_requirements?.origin !== 'Chalderan'
        || confirmed.confirmed_requirements?.budget?.currency !== 'TOMAN'
        || confirmed.confirmed_requirements?.travel_difficulty?.[0] !== 'easy'
        || confirmed.confirmed_requirements?.weather_preferences?.[0] !== 'mild'
        || confirmed.confirmed_requirements?.local_cuisine?.[0] !== 'regional cuisine'
        || confirmed.confirmed_requirements?.field_provenance?.duration_days !== 'llm') {
      throw new Error('traveler_confirmed_requirements_or_provenance_not_persisted');
    }
    const shareOptions = await requestBrowserJson(page,
      `/api/v1/partners/trips/${trip.trip_id}/company-share-options`, 'GET', undefined, undefined, trace);
    if (!shareOptions.items.some(item => item.organization_id === organization)) {
      throw new Error('traveler_share_options_missing_approved_company');
    }
    const shared = await requestBrowserJson(page, `/api/v1/partners/trips/${trip.trip_id}/company-shares`, 'POST', currentIdentity.csrfToken, {
      organization_ids: [organization], consent_confirmed: true,
      include_original_request: false, consent_policy_version: 'company-request-share-v1',
    }, trace);
    if (!shared.shared || shared.shares.length !== 1) throw new Error('traveler_company_share_not_created');
    const privateInboxProbe = await requestBrowserJson(page,
      `/api/v1/partners/organizations/${organization}/requests`, 'GET', undefined, undefined, trace);
    if (privateInboxProbe.items.length !== 0) throw new Error('traveler_without_company_membership_saw_inbox');
    const recommendation = await requestBrowserJson(page, `/api/v1/trips/${trip.trip_id}/recommendations`, 'POST', currentIdentity.csrfToken,
      { selected_destination_ids: [String(selected.destination_id)] }, trace);
    if (recommendation.status !== 'available' || !recommendation.items.some(item => item.destination_id === String(selected.destination_id)
        && item.evidence?.some(source => source.source_url?.startsWith('https://')))) {
      const matching = recommendation.items?.find(item => item.destination_id === String(selected.destination_id));
      throw new Error(`traveler_archive_backed_recommendation_missing_${String(recommendation.status)}_${String(recommendation.reason_code ?? 'no_reason')}_${matching?.evidence?.length ?? 0}`);
    }
    const itinerary = await requestBrowserJson(page, `/api/v1/trips/${trip.trip_id}/itineraries`, 'POST', currentIdentity.csrfToken,
      { recommendation_request_id: recommendation.recommendation_request_id, day_count: 2, locale: 'en-US' }, trace);
    if (!itinerary.itinerary_id || itinerary.stops.length !== 1) throw new Error('traveler_archive_itinerary_not_created');
    const secondRead = await requestBrowserJson(page, `/api/v1/itineraries/${itinerary.itinerary_id}`, 'GET', undefined, undefined, trace);
    if (secondRead.stops.length !== 1 || secondRead.trip_id !== trip.trip_id) throw new Error('traveler_itinerary_initial_read_mismatch');

    // A reviewed profile change is a new revision of the same shared trip;
    // it must not create another lead or expose the original message by default.
    const revisedProfile = await requestBrowserJson(page, `/api/v1/trips/${trip.trip_id}`, 'PATCH', currentIdentity.csrfToken, {
      expected_version: confirmed.version,
      confirmed_requirements: {
        confirmation_source: 'traveler_reviewed', destinations: [selected.canonical_name], duration_days: 2,
        origin: 'Chalderan', travel_dates: { start: '2026-11-19', end: '2026-11-20' }, traveler_count: 2,
        accessibility: [], budget: { amount: 30, currency: 'TOMAN', unit: 'million toman', raw: '30 million toman' },
        soft_preferences: ['nearby walks'], interests: ['heritage'], constraints: [],
        travel_difficulty: ['easy'], weather_preferences: ['mild'], local_cuisine: ['regional cuisine'],
        field_provenance: { destinations: 'traveler', duration_days: 'llm', origin: 'traveler', travel_dates: 'traveler',
          traveler_count: 'traveler', budget: 'traveler', interests: 'traveler', soft_preferences: 'correction',
          travel_difficulty: 'llm', weather_preferences: 'traveler', local_cuisine: 'llm', constraints: 'traveler', accessibility: 'traveler' },
      },
      destination_ids: [String(selected.destination_id)],
      requirement_consent: { contract_version: 'recommendation-consent-v1', field_decisions: {}, advisory_acknowledged_fields: [] },
    }, trace);
    if (revisedProfile.version !== confirmed.version + 1) throw new Error('traveler_shared_request_revision_profile_not_saved');
    const revisedRecommendation = await requestBrowserJson(page, `/api/v1/trips/${trip.trip_id}/recommendations`, 'POST', currentIdentity.csrfToken,
      { selected_destination_ids: [String(selected.destination_id)] }, trace);
    if (revisedRecommendation.status !== 'available') throw new Error('traveler_revision_recommendation_not_available');
    const revisedItinerary = await requestBrowserJson(page, `/api/v1/trips/${trip.trip_id}/itineraries`, 'POST', currentIdentity.csrfToken,
      { recommendation_request_id: revisedRecommendation.recommendation_request_id, day_count: 2, locale: 'en-US' }, trace);
    if (!revisedItinerary.itinerary_id || revisedItinerary.stops.length !== 1) throw new Error('traveler_revision_itinerary_not_saved');
    const revisionItineraryRead = await requestBrowserJson(page, `/api/v1/itineraries/${revisedItinerary.itinerary_id}`, 'GET', undefined, undefined, trace);
    if (revisionItineraryRead.trip_id !== trip.trip_id || revisionItineraryRead.stops.length !== 1) {
      throw new Error('traveler_revision_itinerary_not_reopened');
    }

    await page.locator('.auth-signed-in button').first().click();
    await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
    currentPhone = companyPhone;
    currentIdentity = await signIn(page, api.controlPort, api.controlToken, companyPhone);
    await page.goto(`${webOrigin}/partners`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('heading', { name: 'Partner workspace' }).waitFor({ state: 'visible' });
    const inboxPayload = await requestBrowserJson(page,
      `/api/v1/partners/organizations/${organization}/requests`, 'GET', undefined, undefined, trace);
    if (inboxPayload.items.length !== 4
        || !inboxPayload.items.some(item => item.event_kind === 'request_shared')
        || !inboxPayload.items.some(item => item.event_kind === 'request_revised')
        || inboxPayload.items.some(item => item.request_snapshot?.original_request != null)
        || inboxPayload.items.some(item => item.request_snapshot?.trip_id !== trip.trip_id)) {
      throw new Error('partner_request_inbox_revision_or_privacy_mismatch');
    }
    await page.locator('.partner-request-item').first().waitFor({ state: 'visible' });
    await page.getByText('Traveler request inbox', { exact: true }).waitFor({ state: 'visible' });
    if (await page.locator('.partner-request-item').count() !== 4) throw new Error('partner_request_inbox_ui_missing_revisions');
    milestone('selected-company consent, private request inbox, and same-trip revision verified');

    await page.locator('.auth-signed-in button').first().click();
    await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
    currentPhone = tenantTwoPhone;
    currentIdentity = await signIn(page, api.controlPort, api.controlToken, tenantTwoPhone);
    const otherTenantInbox = await requestBrowserJson(page,
      `/api/v1/partners/organizations/${organization}/requests`, 'GET', undefined, undefined, trace);
    if (otherTenantInbox.items.length !== 0) throw new Error('other_tenant_read_company_request_inbox');

    await page.locator('.auth-signed-in button').first().click();
    await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
    currentPhone = travelerPhone;
    currentIdentity = await signIn(page, api.controlPort, api.controlToken, travelerPhone);
    const ownShares = await requestBrowserJson(page,
      `/api/v1/partners/trips/${trip.trip_id}/company-shares`, 'GET', undefined, undefined, trace);
    if (ownShares.items.length !== 1 || ownShares.items[0].share_id !== shared.shares[0].share_id) {
      throw new Error('traveler_share_identity_not_persisted');
    }
    const revoked = await requestBrowserJson(page,
      `/api/v1/partners/trips/${trip.trip_id}/company-shares/${shared.shares[0].share_id}`,
      'DELETE', currentIdentity.csrfToken, undefined, trace);
    if (!revoked.revoked) throw new Error('traveler_company_share_revoke_failed');

    await page.locator('.auth-signed-in button').first().click();
    await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
    currentPhone = companyPhone;
    currentIdentity = await signIn(page, api.controlPort, api.controlToken, companyPhone);
    const afterRevokeInbox = await requestBrowserJson(page,
      `/api/v1/partners/organizations/${organization}/requests`, 'GET', undefined, undefined, trace);
    if (afterRevokeInbox.items.length !== 0) throw new Error('revoked_company_share_still_visible');

    await page.locator('.auth-signed-in button').first().click();
    await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
    currentPhone = travelerPhone;
    currentIdentity = await signIn(page, api.controlPort, api.controlToken, travelerPhone);
    const history = await requestBrowserJson(page, '/api/v1/conversations', 'GET', undefined, undefined, trace);
    if (!history.items.some(item => item.conversation_id === started.conversation.conversation_id)) throw new Error('traveler_conversation_not_reopened_after_auth');
    const reopenedTrip = await requestBrowserJson(page, `/api/v1/trips/${trip.trip_id}`, 'GET', undefined, undefined, trace);
    const reopenedItinerary = await requestBrowserJson(page, `/api/v1/itineraries/${revisedItinerary.itinerary_id}`, 'GET', undefined, undefined, trace);
    if (reopenedTrip.duration_days !== 2 || reopenedItinerary.stops.length !== 1
        || reopenedTrip.confirmed_requirements?.field_provenance?.duration_days !== 'llm'
        || reopenedTrip.confirmed_requirements?.weather_preferences?.[0] !== 'mild'
        || reopenedItinerary.stops[0].destination_id !== String(selected.destination_id)) throw new Error('traveler_itinerary_not_reopened_after_auth');
    await page.screenshot({ path: resolve(operatorDir, 'traveler-archive-itinerary-reopened.png'), fullPage: true, animations: 'disabled' });
    travelerSummary = { searchResults: foundPlace.length, destinationKey, tripId: trip.trip_id,
      conversationId: started.conversation.conversation_id, durationDays: reopenedTrip.duration_days,
      recommendationOutcome: recommendation.status, itineraryId: revisedItinerary.itinerary_id,
      persistedStops: reopenedItinerary.stops.length, reopenedAfterNewAuthentication: true };

    const counts = await checkedControl(api.controlPort, api.controlToken, { action: 'national_catalogue_counts' });
    if (counts.unpublished_leads - baselineCounts.unpublished_leads !== 533
        || counts.candidates - baselineCounts.candidates !== 700
        || counts.identities - baselineCounts.identities !== 167
        || counts.leads - baselineCounts.leads !== 533
        || counts.verified_sources - baselineCounts.verified_sources !== 3
        || counts.published_destinations - baselineCounts.published_destinations !== 1
        || counts.organizations - baselineCounts.organizations !== 2
        || counts.services - baselineCounts.services !== 1
        || counts.schedules - baselineCounts.schedules !== 1
        || counts.offers - baselineCounts.offers !== 1
        || counts.prices - baselineCounts.prices !== 1
        || counts.availability - baselineCounts.availability !== 1
        || counts.itineraries - baselineCounts.itineraries !== 2) {
      throw new Error('national_postgres_acceptance_counts_mismatch');
    }
    return { archiveStaging: stagedSummary, baselineCounts, operator: { candidate: key, fieldEvidence: evidenceRows.length,
      reviewedSources: sourceSummaries,
      sourcePagesReviewed: sources.length, publishedKey: destinationKey, unpublishedDiscoveryLeads: counts.unpublished_leads },
      partner: partnerSummary, traveler: travelerSummary, databaseCounts: counts,
      apiTrace: trace, simulatedComponents: { otp: 'fake test adapter', chat: 'simulated in-process Gateway', liveProviderCalls: 0 } };
  } finally {
    await context.close();
  }
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
    const requestText = '\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u0622\u0632\u0645\u0627\u06cc\u0634\u06cc: \u0633\u0641\u0631 15 \u0631\u0648\u0632\u0647';
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
  const browseScenario = process.env.RAHGARD_GEO_BROWSE_E2E === '1';
  const keys = [
    'shiraz-hafezieh-v1', 'shiraz-eram-garden-v1',
    'shiraz-vakil-bazaar-v1', 'unesco-persepolis-v1',
  ];
  const roles = ['representative_point', 'representative_point',
    'representative_point', 'property_reference'];
  const prompts = {
    'fa-IR': 'برای ۱۵ روز سفر به شیراز، حافظیه، باغ ارم، بازار وکیل و تخت جمشید',
    'en-US': '15-day trip to Hafezieh, Eram Garden, Vakil Bazaar, and Persepolis in Fars',
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
    const requestText = browseScenario
      ? 'برای ۱۵ روز سفر با مقصدی که هنوز انتخاب نشده است'
      : prompts[locale];
    const interpretation = await requestBrowserJson(
      page, '/api/v1/requirements/interpret', 'POST', csrf,
      { locale, request_text: requestText }, trace);
    const interpretedDuration = interpretation.requirements?.fields?.duration_days?.value;
    if (!browseScenario && locale === 'fa-IR' && interpretedDuration !== 15) {
      throw new Error(`qa_real_geo_interpretation_duration_${String(interpretedDuration ?? 'null')}`);
    }
    const extracted = fixtureRequirements(requestText, locale);
    extracted.destinations = browseScenario
      ? { value: null, status: 'unknown', evidence: null }
      : { value: names, status: 'extracted',
        evidence: 'selected seeded canonical Fars POIs in disposable QA' };
    const started = await requestBrowserJson(page, '/api/v1/conversations', 'POST', csrf, {
      locale, request_text: requestText, extracted_requirements: extracted,
      idempotency_key: randomUUID(),
    }, trace);
    const trip = started.trip;
    const conversationId = started.conversation?.conversation_id;
    // Intake is advisory until explicit profile confirmation, so the legacy
    // confirmed trip.duration_days column is correctly NULL at creation time.
    // Assert the persisted extracted requirement instead of treating it as a
    // confirmed value prematurely.
    if (!conversationId || !trip?.trip_id || trip.extracted_requirements?.durationDays?.value !== 15) {
      const persisted = trip?.extracted_requirements;
      const canonicalDuration = persisted?.requirements_v1?.fields?.duration_days?.value;
      const duration = persisted?.durationDays;
      const canonical = persisted?.requirements_v1?.fields?.duration_days;
      throw new Error(`qa_real_geo_conversation_not_persisted_trip_${Boolean(trip?.trip_id)}_conversation_${Boolean(conversationId)}_duration_${String(duration?.value ?? 'null')}_${duration?.status ?? 'no_status'}_canonical_${String(canonicalDuration ?? 'null')}_${canonical?.status ?? 'no_status'}_preflight_${String(interpretedDuration ?? 'null')}_locale_${locale}`);
    }
    const tripPath = '/api/v1/trips/' + trip.trip_id;
    if (!browseScenario) {
      await requestBrowserJson(page, tripPath, 'PATCH', csrf, {
        expected_version: trip.version,
        confirmed_requirements: {
          confirmation_source: 'traveler_reviewed', duration_days: 15,
          destinations: names, constraints: [],
        },
        destination_ids: selectedIds,
      }, trace);
    }

    const historyWait = page.waitForResponse(response =>
      new URL(response.url()).pathname === '/api/v1/conversations'
      && response.request().method() === 'GET');
    await page.locator('.trip-history-heading button').click();
    await historyWait;
    await page.getByRole('button', { name: requestText, exact: true }).click();
    await page.waitForFunction(expected => document.querySelector('#trip-prompt')?.value === expected, requestText);
    await page.locator('#profile-duration').waitFor({ state: 'visible' });
    if (browseScenario) {
      if (locale !== 'fa-IR') throw new Error('geo_browse_scenario_requires_persian_locale');
      if (await page.locator('.recommendation-controls').count()) {
        throw new Error('geo_browse_recommendations_visible_before_explicit_review');
      }
      await page.getByRole('button', { name: 'دیدن مقصدهای تأییدشده', exact: true }).click();
      await page.locator('#approved-destination-search').waitFor({ state: 'visible' });
      const browser = page.locator('#approved-destination-browser');
      if (await browser.locator('.location-reference').count() !== 4
          || !(await browser.textContent())?.includes('نقطهٔ تقریبی برای نمایش موقعیت؛ ورودی بازدیدکنندگان یا مسیر نیست.')) {
        throw new Error('geo_browse_approximate_reference_warning_missing');
      }
      const firstName = selected[0].localized_names?.[locale] ?? selected[0].canonical_name;
      await page.locator('#approved-destination-search').fill(firstName);
      if (await browser.locator('li').count() !== 1) throw new Error('geo_browse_search_did_not_filter');
      await page.locator('#approved-destination-search').fill('');
      for (const destination of selected) {
        const name = destination.localized_names?.[locale] ?? destination.canonical_name;
        const locality = destination.city_name ?? destination.province_name ?? '';
        const button = page.getByRole('button', { name: `افزودن به سفر: ${name} · ${locality}`, exact: true });
        await button.click();
        await button.waitFor({ state: 'visible' });
        await page.waitForFunction(label => {
          const match = [...document.querySelectorAll('#approved-destination-browser button')]
            .find(item => item.getAttribute('aria-label') === label);
          return match?.disabled === true;
        }, `افزودن به سفر: ${name} · ${locality}`);
      }
      if (await page.locator('.recommendation-controls').count()) {
        throw new Error('geo_browse_add_silently_confirmed_profile');
      }
    }
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
    let finalTrip = confirmed;
    if (!browseScenario) {
      const finalProfile = { ...confirmed.confirmed_requirements };
      delete finalProfile.requirement_consent;
      const consentRequest = { ...consent };
      delete consentRequest.profile_version;
      finalTrip = await requestBrowserJson(page, tripPath, 'PATCH', csrf, {
        expected_version: confirmed.version, confirmed_requirements: finalProfile,
        destination_ids: selectedIds, requirement_consent: consentRequest,
      }, trace);
    }
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
      locale, mode: browseScenario ? 'canonical_Fars_browse_and_explicit_review_disposable_QA'
        : 'canonical_Fars_IDs_in_disposable_QA_database',
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
  const submitted = response.request().postDataJSON()?.extracted_requirements;
  if (response.status() !== 201 || !response.headers()['cache-control']?.includes('no-store')
      || body.trip?.original_request !== localeCopy['fa-IR'].prompt
      || body.message?.content !== content) {
    throw new Error('persian_follow_up_not_persisted_or_original_request_changed');
  }
  if (/(?:45|۴۵)\s*میلیون/u.test(content)
      && Number(submitted?.budget?.value?.amount) !== 45) {
    throw new Error(`persian_budget_correction_not_extracted_amount=${submitted?.budget?.value?.amount ?? 'missing'}`);
  }
  if (/(?:45|۴۵)\s*میلیون/u.test(content)
      && Number(body.trip?.extracted_requirements?.budget?.value?.amount) !== 45) {
    throw new Error(`persian_budget_correction_not_persisted_amount=${body.trip?.extracted_requirements?.budget?.value?.amount ?? 'missing'}`);
  }
  return body;
}

async function verifySimulatedAssistant(page, api, locale, conversationId, tripId, csrf, expectedTripVersion, expectedConversationVersion, expectedDuration) {
  const before = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_count' });
  const assistantButton = page.locator('.assistant-controls > button');
  if (!(await assistantButton.isEnabled())) throw new Error('assistant_blocked_without_redundant_ai_consent');
  const destinationByLocale = { 'fa-IR': '\u0634\u06cc\u0631\u0627\u0632', 'en-US': 'Shiraz', ar: 'Shiraz' };
  const prompt = {
    'fa-IR': '\u0628\u0631\u0627\u06cc \u0633\u0641\u0631 2 \u0631\u0648\u0632 \u0633\u0641\u0631 \u0628\u0647 \u0634\u06cc\u0631\u0627\u0632 \u067e\u06cc\u0634\u0646\u0647\u0627\u062f \u0628\u062f\u0647.',
    'en-US': 'Please suggest a 2-day trip to Shiraz.',
    ar: '\u0627\u0642\u062a\u0631\u062d \u0631\u062d\u0644\u0629 \u0644\u0645\u062f\u0629 2 \u064a\u0648\u0645 \u0625\u0644\u0649 Shiraz.',
  }[locale];
  const expectedCandidateDestination = destinationByLocale[locale];
  await page.locator('#trip-follow-up').fill(prompt);
  const path = '/api/v1/conversations/' + conversationId + '/assistant-turns';
  const responsePending = page.waitForResponse(response =>
    new URL(response.url()).pathname === path && response.request().method() === 'POST');
  await assistantButton.click();
  const response = await responsePending;
  const body = await response.json();
  const candidateFields = body.candidate_requirements?.fields;
  if (response.status() !== 200 || !response.headers()['cache-control']?.includes('no-store')
      || body.replayed || body.candidate_requirements?.contract_version !== 'trip-requirements-v1'
      || candidateFields?.destination?.value !== expectedCandidateDestination
      || candidateFields?.duration_days?.value !== 2
      || body.trip?.version !== expectedTripVersion
      || Object.keys(body.trip?.confirmed_requirements ?? {}).length !== 0) {
    throw new Error(`simulated_assistant_endpoint_or_trip_invariant_failed_${locale}_status=${response.status()}_no_store=${response.headers()['cache-control']?.includes('no-store')}_replayed=${body.replayed}_candidate_version=${body.candidate_requirements?.contract_version}_candidate_destination=${candidateFields?.destination?.value}_candidate_duration=${candidateFields?.duration_days?.value}_trip_version=${body.trip?.version}_expected_trip_version=${expectedTripVersion}_confirmed_keys=${Object.keys(body.trip?.confirmed_requirements ?? {}).length}`);
  }
  await page.locator('.saved-message-assistant p').first().waitFor({ state: 'visible' });
  await page.locator('.assistant-candidate').waitFor({ state: 'visible' });
  if (await page.locator('#profile-duration').inputValue() !== String(expectedDuration)) {
    throw new Error('assistant_changed_profile_without_confirmation_' + locale);
  }
  const stored = await page.request.get(webOrigin + '/api/v1/conversations/' + conversationId);
  const conversation = await stored.json();
  const saved = conversation.messages?.filter(m => m.role === 'assistant' && m.trip_id === tripId);
  const savedAssistantTurn = saved?.find(m => m.message_id === body.message?.message_id);
  if (stored.status() !== 200 || !savedAssistantTurn
      || savedAssistantTurn.candidate_requirements?.fields?.destination?.value !== expectedCandidateDestination
      || savedAssistantTurn.candidate_requirements?.fields?.duration_days?.value !== 2
      || 'metadata' in savedAssistantTurn) {
    throw new Error(`assistant_advisory_not_reopenable_or_metadata_exposed_${locale}_status=${stored.status()}_saved=${saved?.length}_destination=${savedAssistantTurn?.candidate_requirements?.fields?.destination?.value}_duration=${savedAssistantTurn?.candidate_requirements?.fields?.duration_days?.value}_metadata=${'metadata' in (savedAssistantTurn ?? {})}`);
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

  // A second simulated turn provides a bounded candidate
  // that the traveler applies only to the editable draft; confirmation remains
  // gated until the profile and requirement decisions are reviewed.
  const secondPrompt = prompt;
  await page.locator('#trip-follow-up').fill(secondPrompt);
  const secondPending = page.waitForResponse(response =>
    new URL(response.url()).pathname === path && response.request().method() === 'POST');
  await assistantButton.click();
  const secondResponse = await secondPending;
  const secondBody = await secondResponse.json();
  if (secondResponse.status() !== 200 || secondBody.trip?.version !== expectedTripVersion
      || secondBody.candidate_requirements?.fields?.duration_days?.value !== 2) {
    throw new Error('second_simulated_assistant_turn_invalid_' + locale);
  }
  await page.locator('.assistant-candidate button').first().click(); // Apply only as an editable suggestion.
  const confirmButton = page.getByRole('button', { name: localeCopy[locale].confirm });
  // Applying an AI suggestion may enable the explicit confirmation action.
  // The safety invariant is that it must NOT confirm the profile by itself.
  if (await page.locator('#profile-duration').inputValue() !== '2'
      || await page.locator('.recommendation-controls').count() !== 0) {
    throw new Error('applied_ai_suggestion_auto_confirmed_profile_' + locale);
  }
  await page.locator('#profile-duration').fill(String(expectedDuration));
  await page.locator('#profile-destination-0').fill(destinationByLocale[locale]);
  if (locale === 'fa-IR') {
    if (await page.locator('#profile-duration').inputValue() !== '15'
        || await page.locator('#profile-travelers').inputValue() !== '4'
        || !containsFortyFive(await page.locator('#profile-budget').inputValue())
        || !containsToman(await page.locator('#profile-budget').inputValue())
        || await page.locator('.recommendation-controls').count() !== 0) {
      throw new Error('traveler_correction_auto_confirmed_profile_fa-IR');
    }
  } else if (await page.locator('#profile-duration').inputValue() !== String(expectedDuration)
      || await page.locator('.recommendation-controls').count() !== 0) {
    throw new Error(`traveler_duration_restore_auto_confirmed_profile_${locale}`);
  }
  const finalCallCount = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_count' });
  if (finalCallCount.count !== before.count + 2) throw new Error('simulated_gateway_call_budget_not_two_' + locale);
  return true;
}

function normalizedPersianText(value) {
  return String(value ?? '').normalize('NFKC').replace(/\u200c/g, '').replace(/[يى]/g, '\u06cc');
}

function providerFieldSnapshot(candidate) {
  const fields = candidate?.fields && typeof candidate.fields === 'object' ? candidate.fields : {};
  return Object.fromEntries(Object.entries(fields).map(([name, field]) => [name, {
    status: field?.status ?? 'missing', source: field?.source ?? null,
    hasValue: field?.value !== null && field?.value !== undefined,
  }]));
}

async function runRealProviderJourney(browser, api, audit, artifactRoot, provider) {
  const context = await browser.newContext({ locale: 'fa-IR', timezoneId: 'Asia/Tehran' });
  const page = await context.newPage();
  await page.clock.setFixedTime(new Date('2026-12-01T08:00:00Z'));
  page.setDefaultTimeout(90_000);
  const phone = syntheticPhone();
  let identity;
  let tripId = null;
  let conversationId = null;
  const endpointTrace = [];
  page.on('response', response => {
    const path = new URL(response.url()).pathname.replace(/[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}/gi, ':id');
    if (/^\/api\/v1\/(?:assistant\/status|conversations|trips|partners\/organizations|partners\/trips)(?:\/|$)/.test(path)) {
      endpointTrace.push({ method: response.request().method(), path, status: response.status() });
    }
  });
  const safeResult = {
    provider: provider.provider,
    model: provider.model,
    routeType: provider.provider === 'lm_studio' ? 'loopback_http' : 'remote_https',
    invocationAttempts: 0,
    successfulInvocations: 0,
    extractionPath: null,
    fields: {},
    correctionTurn: false,
    manualEditPreserved: false,
    itineraryGenerated: false,
    persistedAndReopened: false,
    protectedCompanyViews: false,
    sharedRevisionPersisted: false,
    crossTenantDenied: false,
  };
  try {
    await attachBrowserGuards(page, audit);
    await page.goto(webOrigin, { waitUntil: 'domcontentloaded' });
    await selectAndVerifyLocale(page, 'fa-IR');
    identity = await signIn(page, api.controlPort, api.controlToken, phone);

    await page.locator('.trip-intake-panel [data-provider-state="connected"]').waitFor({ timeout: 12000 });
    safeResult.providerHandshake = 'configured_model_found';
    const before = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_status' });
    if (before.attempts !== 0 || before.route?.model_id !== provider.model
      || before.route?.host !== new URL(provider.endpoint).hostname) {
      throw new Error('real_chat_provider_route_identity_mismatch');
    }
    const requestText = 'برای سه نفر از مشهد به شیراز، چهار روز، با بودجه ۲۰ میلیون تومان؛ علاقه‌مند به باغ‌ها، آثار تاریخی و غذای محلی، مسیرهای سبک و هوای معتدل هستیم.';
    const firstTurn = page.waitForResponse(response =>
      new URL(response.url()).pathname.endsWith('/assistant-turns') && response.request().method() === 'POST');
    await page.locator('#trip-prompt').fill(requestText);
    await page.locator('.trip-form button[type="submit"]').click();
    const firstResponse = await firstTurn;
    const firstBody = await firstResponse.json().catch(() => ({}));
    if (firstResponse.status() !== 200 || !firstBody.trip?.trip_id || !firstBody.conversation?.conversation_id) {
      const failedCalls = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_status' });
      throw new Error(`real_chat_initial_turn_failed_status_${firstResponse.status()}_attempts_${failedCalls.attempts}`
        + `_successes_${failedCalls.successes}_upstream_${api.safeChatUpstreamStatus() || 'unknown'}`
        + `_adapter_${api.safeAssistantFailure() || 'unknown'}`);
    }
    tripId = firstBody.trip.trip_id;
    conversationId = firstBody.conversation.conversation_id;
    safeResult.extractionPath = firstBody.extraction_path;
    const fields = firstBody.candidate_requirements?.fields ?? {};
    safeResult.fields = providerFieldSnapshot(firstBody.candidate_requirements);
    const fieldValue = name => fields[name]?.value;
    const originOk = normalizedPersianText(fieldValue('origin')).includes('\u0645\u0634\u0647\u062f');
    const destinationOk = normalizedPersianText(fieldValue('destination')).includes('\u0634\u06cc\u0631\u0627\u0632');
    const durationOk = fieldValue('duration_days') === 4;
    // The canonical requirement model names this persisted form field
    // `travelers`; `traveler_count` is the provider extraction-contract key.
    const travelersOk = fieldValue('travelers') === 3;
    const budgetOk = normalizedPersianText(JSON.stringify(fieldValue('budget') ?? fieldValue('budget_text')))
      .includes('\u062a\u0648\u0645\u0627\u0646');
    const dateField = fieldValue('relative_start_date');
    const relativeDateOk = dateField == null;
    safeResult.relativeStartDateSource = fields.relative_start_date?.source || 'missing';
    const initialStatus = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_status' });
    safeResult.invocationAttempts = initialStatus.attempts;
    safeResult.successfulInvocations = initialStatus.successes;
    safeResult.providerTelemetry = {
      route: initialStatus.route,
      attempts: initialStatus.attempts,
      successes: initialStatus.successes,
      failures: initialStatus.failures,
      latencyMs: initialStatus.latency_ms,
      responseFieldKeys: initialStatus.response_field_keys,
      responseEvidenceKeys: initialStatus.response_evidence_keys,
    };
    if (initialStatus.attempts !== 1 || initialStatus.successes !== 1
      || firstBody.extraction_path !== 'llm') {
      const acceptedSources = Object.entries(providerFieldSnapshot(firstBody.candidate_requirements))
        .map(([name, field]) => `${name}_${field.source || field.status}`).join('_');
      throw new Error('real_chat_provider_invocation_or_llm_provenance_failed'
        + `_attempts_${initialStatus.attempts}_successes_${initialStatus.successes}`
        + `_accepted_${acceptedSources || 'none'}`
        + `_provider_keys_${(initialStatus.response_field_keys || []).join('_') || 'none'}`
        + `_evidence_keys_${(initialStatus.response_evidence_keys || []).join('_') || 'none'}`);
    }
    if (!(originOk && destinationOk && durationOk && travelersOk && budgetOk && relativeDateOk)) {
      const failures = [!originOk && 'origin', !destinationOk && 'destination', !durationOk && 'duration_days',
        !travelersOk && 'traveler_count', !budgetOk && 'budget', !relativeDateOk && 'relative_start_date']
        .filter(Boolean).join('_');
      const safeState = key => {
        const field = fields[key];
        return field ? `${field.status || 'unknown'}_${field.source || 'unknown'}_${field.value == null ? 'null' : typeof field.value}` : 'absent';
      };
      throw new Error(`real_chat_semantic_fields_failed_${failures}`
        + `_states_origin_${safeState('origin')}_destination_${safeState('destination')}`
        + `_duration_${safeState('duration_days')}_travelers_${safeState('travelers')}`
        + `_budget_${safeState('budget')}_date_${safeState('relative_start_date')}`
        + `_provider_keys_${(initialStatus.response_field_keys || []).join('_') || 'none'}`
        + `_evidence_keys_${(initialStatus.response_evidence_keys || []).join('_') || 'none'}`);
    }
    // Core semantic extraction must demonstrably come from the provider. The
    // date can validly use the deterministic fallback when the model omits an
    // offset; the report preserves that source distinction.
    const requiredLlmFields = ['origin', 'destination', 'travelers', 'budget', 'interests'];
    const nonLlmFields = requiredLlmFields.filter(key => fields[key]?.source !== 'llm');
    if (nonLlmFields.length) throw new Error(`real_chat_required_semantics_not_llm_${nonLlmFields.join('_')}`);
    await page.locator('.saved-message-assistant p').first().waitFor({ state: 'visible' });
    if (!normalizedPersianText(await page.locator('#profile-origin').inputValue()).includes('\u0645\u0634\u0647\u062f')
      || await page.locator('#profile-duration').inputValue() !== '4'
      || await page.locator('#profile-travelers').inputValue() !== '3'
      || !normalizedPersianText(await page.locator('#profile-budget').inputValue()).includes('\u062a\u0648\u0645\u0627\u0646')) {
      throw new Error('real_chat_fields_not_synchronized_to_profile_form');
    }

    await page.locator('#profile-origin').fill('مشهد');
    await page.locator('#profile-budget').fill('۲۵ میلیون تومان');
    await page.locator('#trip-follow-up').fill('تاریخ شروع سفر 2026-12-05 و تاریخ پایان 2026-12-08 است. بودجهٔ اصلاح‌شده ۲۵ میلیون تومان است.');
    const correctionResponsePromise = page.waitForResponse(response =>
      new URL(response.url()).pathname.endsWith('/assistant-turns') && response.request().method() === 'POST');
    await page.locator('.assistant-controls > button').click();
    const correctionResponse = await correctionResponsePromise;
    const correctionBody = await correctionResponse.json().catch(() => ({}));
    if (correctionResponse.status() !== 200 || correctionBody.extraction_path !== 'llm') {
      const correctionCalls = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_status' });
      const correctionFields = correctionBody.candidate_requirements?.fields ?? {};
      const correctionSources = ['origin', 'destination'].map(key =>
        `${key}_${correctionFields[key]?.source || correctionFields[key]?.status || 'absent'}`).join('_');
      throw new Error(`real_chat_correction_turn_failed_status_${correctionResponse.status()}`
        + `_extraction_${correctionBody.extraction_path || 'absent'}_attempts_${correctionCalls.attempts}`
        + `_successes_${correctionCalls.successes}_${correctionSources}`
        + `_response_keys_${(correctionCalls.response_field_keys || []).join('_') || 'none'}`
        + `_evidence_keys_${(correctionCalls.response_evidence_keys || []).join('_') || 'none'}`
        + `_failure_${correctionCalls.last_failure_category || 'none'}`);
    }
    safeResult.correctionTurn = true;
    safeResult.correctionFields = providerFieldSnapshot(correctionBody.candidate_requirements);
    await page.locator('.assistant-candidate').waitFor({ state: 'visible' });
    await page.locator('.assistant-candidate button').first().click();
    const manualOrigin = normalizedPersianText(await page.locator('#profile-origin').inputValue());
    safeResult.manualEditPreserved = manualOrigin.includes('مشهد')
      && await page.locator('#profile-budget').inputValue() === '۲۵ میلیون تومان';
    if (!safeResult.manualEditPreserved) throw new Error('real_chat_candidate_overwrote_manual_origin');
    const dateUpdates = [['start', '2026-12-05'], ['end', '2026-12-08']];
    safeResult.followUpDatesFromModel = true;
    for (const [field, iso] of dateUpdates) {
      const id = '#profile-travel-' + field;
      if (await page.locator(id).inputValue() === iso) continue;
      safeResult.followUpDatesFromModel = false;
      await page.locator(id + '-picker').click();
      const persianDay = new Intl.DateTimeFormat('fa-IR-u-ca-persian', {
        day: 'numeric', timeZone: 'UTC',
      }).format(new Date(iso + 'T00:00:00Z'));
      await page.locator('.jalali-calendar-grid').getByText(persianDay, { exact: true }).click();
      if (await page.locator(id).inputValue() !== iso) throw new Error('issue23_calendar_iso_mismatch');
    }
    if (!await page.locator('#profile-travel-difficulty').inputValue()) {
      await page.locator('#profile-travel-difficulty').fill('مسیرهای سبک');
    }
    if (!await page.locator('#profile-weather-preferences').inputValue()) {
      await page.locator('#profile-weather-preferences').fill('هوای معتدل');
    }
    if (!await page.locator('#profile-local-cuisine').inputValue()) {
      await page.locator('#profile-local-cuisine').fill('غذای محلی');
    }
    safeResult.invocationAttempts = (await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_status' })).attempts;
    safeResult.successfulInvocations = (await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_status' })).successes;

    const confirmation = page.locator('.profile-confirm-action');
    if (await confirmation.isDisabled()) throw new Error('real_chat_profile_confirmation_disabled');
    const profileSaved = page.waitForResponse(response =>
      new URL(response.url()).pathname === `/api/v1/trips/${tripId}` && response.request().method() === 'PATCH');
    await confirmation.click();
    if ((await profileSaved).status() !== 200) throw new Error('real_chat_profile_save_failed');
    const confirmed = await (await page.request.get(`${webOrigin}/api/v1/trips/${tripId}`)).json();
    if (confirmed.confirmed_requirements?.origin !== 'مشهد'
      || Number(confirmed.confirmed_requirements?.budget?.amount) !== 25
      || confirmed.confirmed_requirements?.confirmation_source !== 'traveler_reviewed') {
      throw new Error('real_chat_confirmed_snapshot_did_not_preserve_manual_edit');
    }
    safeResult.followUpDatesConfirmed = confirmed.confirmed_requirements?.travel_dates?.start === '2026-12-05'
      && confirmed.confirmed_requirements?.travel_dates?.end === '2026-12-08';
    safeResult.confirmedPreferenceFields = ['travel_difficulty', 'weather_preferences', 'local_cuisine']
      .filter(field => confirmed.confirmed_requirements?.[field]?.length);
    if (!safeResult.followUpDatesConfirmed || safeResult.confirmedPreferenceFields.length !== 3) {
      throw new Error('issue23_reviewed_dates_or_preferences_not_saved');
    }

    const recResponsePromise = page.waitForResponse(response =>
      new URL(response.url()).pathname === `/api/v1/trips/${tripId}/recommendations`
      && response.request().method() === 'POST');
    await page.locator('.recommendation-controls > button').click();
    const recResponse = await recResponsePromise;
    const recBody = await recResponse.json().catch(() => ({}));
    // POST creates and persists a recommendation snapshot, so the route's
    // contract returns 201 (the UI reads the same response as its result).
    if (recResponse.status() !== 201 || !['empty', 'available', 'needs_confirmation'].includes(recBody.status)) {
      throw new Error(`real_chat_recommendation_failed_status_${recResponse.status()}`);
    }
    safeResult.recommendationStatus = recBody.status;
    safeResult.recommendationReason = recBody.reason_code;
    safeResult.requirementAssessments = recBody.requirement_assessments ?? [];
    safeResult.confirmedProfileVersion = confirmed.version;
    safeResult.confirmationSource = confirmed.confirmed_requirements?.confirmation_source;
    safeResult.selectedDestinationCount = (confirmed.destination_ids ?? []).length;
    const knownForPlanning = new Set(safeResult.requirementAssessments
      .filter(item => item.status === 'known').map(item => item.field));
    if (!knownForPlanning.has('destination') || !knownForPlanning.has('duration_days')
      || recBody.reason_code === 'requirements_incomplete') {
      throw new Error('confirmed_destination_or_duration_misclassified_as_missing');
    }
    safeResult.recommendationCount = Array.isArray(recBody.items) ? recBody.items.length : 0;
    safeResult.unresolvedFields = Array.isArray(recBody.unresolved_fields) ? recBody.unresolved_fields : [];
    const mayUseProvisionalDraft = recBody.status === 'empty'
      || (recBody.status === 'needs_confirmation'
        && Array.isArray(recBody.unresolved_fields)
        && recBody.unresolved_fields.length === 1
        && recBody.unresolved_fields[0] === 'destination_resolution');
    if (mayUseProvisionalDraft) {
      const generateDraft = page.locator('#generate-provisional-itinerary');
      await generateDraft.waitFor({ state: 'visible', timeout: 15000 });
      const itineraryTurn = page.waitForResponse(response =>
        new URL(response.url()).pathname.endsWith('/assistant-turns') && response.request().method() === 'POST');
      await generateDraft.click({ timeout: 15000 });
      const itineraryResponse = await itineraryTurn;
      const itineraryBody = await itineraryResponse.json().catch(() => ({}));
      if (itineraryResponse.status() !== 200 || itineraryBody.provisional_itinerary?.status !== 'provisional_unverified') {
        const failedCall = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_status' });
        throw new Error(`real_chat_structured_itinerary_missing_status_${itineraryResponse.status()}`
          + `_attempts_${failedCall.attempts}_successes_${failedCall.successes}`
          + `_failure_${failedCall.last_failure_category || 'none'}`);
      }
      safeResult.itineraryGenerated = true;
      safeResult.invocationAttempts = (await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_status' })).attempts;
      safeResult.successfulInvocations = (await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_status' })).successes;
      const saveDraftResponse = page.waitForResponse(response =>
        new URL(response.url()).pathname === `/api/v1/trips/${tripId}/provisional-itineraries`
        && response.request().method() === 'POST');
      await page.locator('#save-provisional-itinerary').click({ timeout: 15000 });
      const savedResponse = await saveDraftResponse;
      if (savedResponse.status() !== 201) throw new Error('real_chat_provisional_itinerary_save_failed');
      const savedDraft = await savedResponse.json();
      const restoredDraftResponse = await page.request.get(`${webOrigin}/api/v1/trips/${tripId}/provisional-itineraries`);
      const restoredDraft = await restoredDraftResponse.json();
      if (restoredDraftResponse.status() !== 200 || restoredDraft.provisional_itinerary_id !== savedDraft.provisional_itinerary_id) {
        throw new Error('real_chat_provisional_itinerary_not_persisted');
      }
      const note = 'یادداشت آزمایشی مسافر';
      await page.locator('.provisional-itinerary .provisional-stop textarea').first().fill(note);
      const editResponse = page.waitForResponse(response =>
        new URL(response.url()).pathname === `/api/v1/provisional-itineraries/${savedDraft.provisional_itinerary_id}`
        && response.request().method() === 'PUT', { timeout: 15000 });
      await page.locator('.provisional-itinerary > button.primary').click();
      if ((await editResponse).status() !== 200) throw new Error('issue23_provisional_edit_not_saved');
      const edited = await requestBrowserJson(page, `/api/v1/trips/${tripId}/provisional-itineraries`, 'GET');
      if (!edited.days?.some(day => day.stops.some(stop => stop.notes_by_locale?.['fa-IR'] === note))) {
        throw new Error('issue23_provisional_saved_note_missing');
      }
      safeResult.provisionalEdited = true;
      safeResult.persistedAndReopened = true;
    } else if (recBody.status === 'available' && recBody.items?.length) {
      const dayCountInput = page.locator('#journey-day-count');
      await dayCountInput.waitFor({ state: 'visible' });
      await dayCountInput.fill(String(Math.min(3, Number(await dayCountInput.getAttribute('max')) || 3)));
      const itineraryPromise = page.waitForResponse(response =>
        new URL(response.url()).pathname === `/api/v1/trips/${tripId}/itineraries`
        && response.request().method() === 'POST');
      await page.locator('.itinerary-generate-action').click();
      const itineraryResponse = await itineraryPromise;
      if (itineraryResponse.status() !== 201) {
        throw new Error(`real_chat_catalogue_itinerary_failed_status_${itineraryResponse.status()}`);
      }
      const itinerary = await itineraryResponse.json();
      const itineraryId = itinerary.itinerary_id;
      const firstStop = itinerary.stops?.[0];
      if (!itineraryId || !firstStop) throw new Error('real_chat_catalogue_itinerary_has_no_stops');
      safeResult.itineraryGenerated = true;
      await page.locator(`#stop-note-${firstStop.recommendation_id}`).fill('Acceptance edit, test only.');
      const editPromise = page.waitForResponse(response =>
        new URL(response.url()).pathname === `/api/v1/itineraries/${itineraryId}`
        && response.request().method() === 'PUT');
      await page.locator('.itinerary-save-action').click();
      if ((await editPromise).status() !== 200) throw new Error('real_chat_catalogue_itinerary_edit_save_failed');
      const reopened = await page.request.get(`${webOrigin}/api/v1/itineraries/${itineraryId}`);
      const reopenedBody = await reopened.json();
      if (reopened.status() !== 200
        || reopenedBody.stops?.[0]?.notes_by_locale?.['fa-IR'] !== 'Acceptance edit, test only.') {
        throw new Error('real_chat_catalogue_itinerary_edit_not_persisted');
      }
      safeResult.persistedAndReopened = true;
    } else {
      throw new Error(`real_chat_recommendation_requires_traveler_resolution_${recBody.status}`
        + `_${safeResult.unresolvedFields.join('_') || 'no_listed_field'}`);
    }

    // Exercise the positive deterministic recommendation/itinerary boundary
    // with the existing clearly synthetic test identities, only when the
    // disposable database's real production publication view is empty. This
    // dependency override is private to the guarded E2E process; it does not
    // publish or expose any fixture through the public catalogue endpoint.
    const fixture = await controlRequest(api.controlPort, api.controlToken, { action: 'enable_itinerary_fixture' });
    if (!fixture.ok) throw new Error(`real_provider_test_catalogue_fixture_enable_failed_${fixture.reason || 'unknown'}`);
    if (!Array.isArray(fixture.destination_ids) || fixture.destination_ids.length !== 4) {
      throw new Error('real_provider_test_catalogue_fixture_unavailable');
    }
    const publicCatalogueBefore = await requestBrowserJson(page, '/api/v1/catalog/destinations', 'GET');
    const publicCatalogueIdsBefore = (publicCatalogueBefore.items ?? []).map(item => item.destination_id).sort();
    if (publicCatalogueBefore.items?.some(item => String(item.destination_key).startsWith('E2E-TEST-ONLY-'))) {
      throw new Error('synthetic_fixture_preexisted_in_public_catalogue');
    }
    const fixtureTripResponse = await requestBrowserJson(page, `/api/v1/conversations/${conversationId}/trips`, 'POST', identity.csrfToken, {
      locale: 'fa-IR', request_text: 'Isolated test-only destination selection.',
      traveler_timezone: 'Asia/Tehran', traveler_reference_date: new Date().toISOString().slice(0, 10),
      idempotency_key: randomUUID(),
    });
    const fixtureTripId = fixtureTripResponse.trip?.trip_id;
    if (!fixtureTripId) throw new Error('real_provider_test_trip_not_persisted');
    const fixtureTripProfile = structuredClone(confirmed.confirmed_requirements);
    delete fixtureTripProfile.requirement_consent;
    fixtureTripProfile.destinations = ['SYNTHETIC E2E TEST DESTINATION — NOT A REAL PLACE'];
    fixtureTripProfile.destination_ids = [fixture.destination_ids[0]];
    const consentReceipt = structuredClone(confirmed.confirmed_requirements.requirement_consent);
    delete consentReceipt.profile_version;
    const fixtureConfirmed = await requestBrowserJson(page, `/api/v1/trips/${fixtureTripId}`, 'PATCH', identity.csrfToken, {
      expected_version: fixtureTripResponse.trip.version,
      confirmed_requirements: fixtureTripProfile,
      destination_ids: fixture.destination_ids.slice(0, 1),
      requirement_consent: consentReceipt,
    });
    const fixtureRecommendation = await requestBrowserJson(page, `/api/v1/trips/${fixtureTripId}/recommendations`, 'POST', identity.csrfToken, {
      selected_destination_ids: fixture.destination_ids.slice(0, 1),
    });
    if (fixtureRecommendation.status !== 'available' || fixtureRecommendation.items?.[0]?.destination_id !== fixture.destination_ids[0]) {
      throw new Error(`real_provider_test_catalogue_recommendation_failed_${fixtureRecommendation.status}`);
    }
    const fixtureItinerary = await requestBrowserJson(page, `/api/v1/trips/${fixtureTripId}/itineraries`, 'POST', identity.csrfToken, {
      recommendation_request_id: fixtureRecommendation.recommendation_request_id,
      day_count: Math.min(3, fixtureConfirmed.trip?.duration_days || 3), locale: 'fa-IR',
    });
    const fixtureItineraryRead = await requestBrowserJson(page, `/api/v1/itineraries/${fixtureItinerary.itinerary_id}`, 'GET');
    if (!fixtureItineraryRead.stops?.some(stop => stop.destination_id === fixture.destination_ids[0])) {
      throw new Error('real_provider_test_catalogue_itinerary_not_persisted');
    }
    await checkedControl(api.controlPort, api.controlToken, { action: 'disable_itinerary_fixture' });
    const publicCatalogueAfter = await requestBrowserJson(page, '/api/v1/catalog/destinations', 'GET');
    const publicCatalogueIdsAfter = (publicCatalogueAfter.items ?? []).map(item => item.destination_id).sort();
    if (JSON.stringify(publicCatalogueIdsAfter) !== JSON.stringify(publicCatalogueIdsBefore)
      || publicCatalogueAfter.items?.some(item => String(item.destination_key).startsWith('E2E-TEST-ONLY-'))) {
      throw new Error('synthetic_fixture_leaked_after_test');
    }
    safeResult.syntheticCatalogueAcceptance = {
      status: 'test_only_dependency_override', recommendation: true, itineraryPersisted: true,
      publicCatalogueBeforeAndAfterEmpty: true,
    };

    // Verify that this real-provider-derived, traveler-confirmed profile and
    // its provisional itinerary can be shared through the existing protected
    // partner boundary, then revised as the same trip. These organizations
    // exist only in this disposable PostgreSQL run.
    const companyOnePhone = syntheticPhone();
    await page.selectOption('#locale', 'en-US');
    await page.locator('.auth-signed-in button').first().click();
    await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
    const companyOneIdentity = await signIn(page, api.controlPort, api.controlToken, companyOnePhone);
    await page.goto(`${webOrigin}/partners`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('heading', { name: 'Partner workspace' }).waitFor({ state: 'visible' });
    const createCompany = async (label, identityForCompany, approve = true) => {
      const orgForm = page.locator('form.partner-card').filter({
        has: page.getByRole('heading', { name: 'Organization', exact: true }),
      });
      const legalName = `V2 acceptance ${label}`;
      const displayName = `V2 acceptance ${label}`;
      await orgForm.getByLabel('Legal name').fill(legalName);
      await orgForm.getByLabel('Display name').fill(displayName);
      const createPromise = page.waitForResponse(response =>
        new URL(response.url()).pathname === '/api/v1/partners/organizations'
        && response.request().method() === 'POST');
      await orgForm.getByRole('button', { name: 'Create organization', exact: true }).click();
      if ((await createPromise).status() !== 201) throw new Error('real_provider_company_create_failed');
      const rows = await requestBrowserJson(page, '/api/v1/partners/organizations', 'GET', undefined, undefined);
      const row = rows.items.find(item => item.display_name === displayName);
      if (!row?.organization_id) throw new Error('real_provider_company_not_persisted');
      if (!approve) return row.organization_id;
      const approved = await controlRequest(api.controlPort, api.controlToken, {
        action: 'approve_isolated_test_organization', organization_id: row.organization_id,
        created_by: identityForCompany.userId, display_name: displayName,
      });
      if (!approved.ok) throw new Error(`real_provider_isolated_company_approval_failed_${approved.reason || 'unknown'}`);
      return row.organization_id;
    };
    const companyOne = await createCompany(`Company ${companyOnePhone.slice(-4)}`, companyOneIdentity);
    await page.locator('.auth-signed-in button').first().click();
    await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
    const companyTwoPhone = syntheticPhone();
    const companyTwoIdentity = await signIn(page, api.controlPort, api.controlToken, companyTwoPhone);
    await page.goto(`${webOrigin}/partners`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('heading', { name: 'Partner workspace' }).waitFor({ state: 'visible' });
    const companyTwo = await createCompany(`Company ${companyTwoPhone.slice(-4)}`, companyTwoIdentity);
    if (companyOne === companyTwo) throw new Error('real_provider_company_tenants_not_distinct');

    const switchIdentity = async targetPhone => {
      await page.locator('.auth-signed-in button').first().click();
      await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
      return signIn(page, api.controlPort, api.controlToken, targetPhone);
    };
    const verifyCompanyInboxInBrowser = async () => {
      await page.goto(`${webOrigin}/partners`, { waitUntil: 'domcontentloaded' });
      const revisions = page.locator('.partner-request-item');
      await revisions.nth(1).waitFor({ state: 'visible' });
      if (await revisions.count() !== 2) throw new Error('issue23_company_browser_revision_count');
      for (const revision of await revisions.all()) {
        if (!await revision.locator('a[href*="view=request"]').isVisible()
          || !await revision.locator('a[href*="view=itinerary"]').isVisible()) {
          throw new Error('issue23_company_browser_request_or_plan_links_hidden');
        }
      }
    };
    const rejectedPhone = syntheticPhone();
    const rejectedIdentity = await switchIdentity(rejectedPhone);
    const rejectedCompany = await createCompany('Company REJECTED', rejectedIdentity, false);

    await page.locator('.auth-signed-in button').first().click();
    await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
    identity = await signIn(page, api.controlPort, api.controlToken, phone);
    const shareOptions = await requestBrowserJson(page,
      `/api/v1/partners/trips/${tripId}/company-share-options`, 'GET', undefined, undefined);
    const recipients = new Set(shareOptions.items.map(item => item.organization_id));
    if (!recipients.has(companyOne) || !recipients.has(companyTwo) || recipients.has(rejectedCompany)) {
      throw new Error('real_provider_company_share_eligibility_incorrect');
    }
    await page.goto(webOrigin, { waitUntil: 'domcontentloaded' });
    await page.locator(`.history-trip[data-trip-id="${tripId}"] button`).first().click();
    for (const targetPhone of [companyOnePhone, companyTwoPhone]) {
      await page.locator('.company-share-options label').filter({ hasText: `Company ${targetPhone.slice(-4)}` })
        .locator('input').check();
    }
    await page.locator('.company-share-consent input').check();
    const shareResponse = page.waitForResponse(response =>
      new URL(response.url()).pathname === `/api/v1/partners/trips/${tripId}/company-shares`
      && response.request().method() === 'POST');
    await page.locator('.company-share-options button').click();
    const share = await (await shareResponse).json();
    if (!share.shared || share.shares.length !== 2) throw new Error('real_provider_traveler_share_failed');
    const shareId = share.shares.find(item => item.organization_id === companyOne)?.share_id;
    const companyTwoShare = share.shares.find(item => item.organization_id === companyTwo)?.share_id;
    if (!shareId || !companyTwoShare) throw new Error('real_provider_company_share_ids_missing');
    const latestTrip = await requestBrowserJson(page, `/api/v1/trips/${tripId}`, 'GET');
    const revisedRequirements = structuredClone(latestTrip.confirmed_requirements);
    // The read representation nests the persisted consent receipt; PATCH only
    // accepts the profile without that field and the explicit top-level
    // consent request below.
    delete revisedRequirements.requirement_consent;
    revisedRequirements.soft_preferences = [...new Set([...(revisedRequirements.soft_preferences ?? []), 'اولویت بازدید آرام از باغ‌های شیراز'])];
    const revisedTrip = await requestBrowserJson(page, `/api/v1/trips/${tripId}`, 'PATCH', identity.csrfToken, {
      expected_version: latestTrip.version,
      confirmed_requirements: revisedRequirements,
      destination_ids: latestTrip.destination_ids ?? [],
      requirement_consent: { contract_version: 'recommendation-consent-v1', field_decisions: {}, advisory_acknowledged_fields: [] },
    });
    if (revisedTrip.trip_id !== tripId || revisedTrip.version !== latestTrip.version + 1) {
      throw new Error('real_provider_trip_revision_identity_or_version_failed');
    }
    safeResult.sharedRevisionPersisted = true;
    const allEligibleShare = await requestBrowserJson(page,
      `/api/v1/partners/trips/${tripId}/company-shares`, 'POST', identity.csrfToken, {
        recipient_mode: 'all_eligible', organization_ids: [],
        broad_sharing_consent_confirmed: true, consent_confirmed: true,
        include_original_request: false, consent_policy_version: 'company-request-share-v1',
      });
    if (allEligibleShare.recipient_mode !== 'all_eligible'
      || allEligibleShare.recipient_count !== 2 || allEligibleShare.shares.length !== 2) {
      throw new Error('real_provider_bulk_share_all_eligible_consent_or_dedup_failed');
    }
    safeResult.bulkSharing = { eligibleRecipients: 2, deduplicated: true, originalRequestExcluded: true };

    const signedOutCompanyOne = await requestBrowserJson(page,
      `/api/v1/partners/organizations/${companyOne}/requests`, 'GET');
    if (signedOutCompanyOne.items.length !== 0) throw new Error('real_provider_traveler_saw_company_inbox');
    await page.locator('.auth-signed-in button').first().click();
    await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
    const outsider = await signIn(page, api.controlPort, api.controlToken, companyTwoPhone);
    const secondInbox = await requestBrowserJson(page,
      `/api/v1/partners/organizations/${companyTwo}/requests`, 'GET');
    if (!['request_shared', 'request_revised'].every(kind => secondInbox.items.some(item =>
      item.share_id === companyTwoShare && item.event_kind === kind
      && item.request_snapshot?.trip_id === tripId && item.itinerary_snapshot?.provisional))) {
      throw new Error('real_provider_second_company_request_or_revision_missing');
    }
    await verifyCompanyInboxInBrowser();
    const crossTenantInbox = await requestBrowserJson(page,
      `/api/v1/partners/organizations/${companyOne}/requests`, 'GET');
    const crossTenantWorkspace = await browserApi(page,
      `/api/v1/partners/organizations/${companyOne}/workspace`, 'GET');
    const crossTenantWrite = await browserApi(page,
      `/api/v1/partners/organizations/${companyOne}/services`, 'POST', outsider.csrfToken,
      { service_type: 'tour', service_key: 'unauthorized-v2-acceptance-write', locale: 'en-US', display_name: 'forged' });
    if (crossTenantInbox.items.length !== 0 || crossTenantWorkspace.status !== 200
      || crossTenantWorkspace.payload?.services?.length !== 0
      || ![403, 422].includes(crossTenantWrite.status)) {
      throw new Error('real_provider_cross_tenant_company_access_not_denied');
    }
    const crossTenantCompanyResponse = await browserApi(page,
      `/api/v1/partners/organizations/${companyOne}/requests/${shareId}/responses`,
      'POST', outsider.csrfToken,
      { client_request_id:crypto.randomUUID(), revision_id:crypto.randomUUID(),
        response_kind:'accepted_as_requested', message:'forged company response' });
    if (crossTenantCompanyResponse.status !== 403) {
      throw new Error('real_provider_cross_tenant_company_response_was_not_denied');
    }
    safeResult.crossTenantDenied = true;

    await page.locator('.auth-signed-in button').first().click();
    await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
    // This is a second login of the same company, not another declaration
    // of the identity created earlier in this journey.
    const companyOneReauthenticated = await signIn(page, api.controlPort, api.controlToken, companyOnePhone);
    const inbox = await requestBrowserJson(page,
      `/api/v1/partners/organizations/${companyOne}/requests`, 'GET');
    const revisions = await requestBrowserJson(page,
      `/api/v1/partners/organizations/${companyOne}/requests/${shareId}/revisions`, 'GET');
    const sharedRevision = inbox.items.find(item => item.event_kind === 'request_shared');
    const changedRevision = inbox.items.find(item => item.event_kind === 'request_revised');
    const protectedRequest = sharedRevision?.request_snapshot;
    const protectedItinerary = sharedRevision?.itinerary_snapshot;
    if (!sharedRevision || !changedRevision || inbox.items.some(item => item.request_snapshot?.original_request != null)
      || protectedRequest?.trip_id !== tripId || !protectedRequest?.requirements
      || !protectedItinerary?.provisional || protectedItinerary.provisional.status !== 'provisional_unverified'
      || revisions.items.length !== 2 || revisions.items[0].share_id !== shareId) {
      throw new Error('real_provider_company_protected_request_and_itinerary_views_failed');
    }
    const anonymousContext = await browser.newContext();
    try {
      const anonymousPage = await anonymousContext.newPage();
      const anonymousResponse = await anonymousPage.request.get(
        `${webOrigin}/api/v1/partners/organizations/${companyOne}/requests`);
      if (anonymousResponse.status() !== 401) throw new Error('real_provider_anonymous_company_inbox_not_denied');
    } finally {
      await anonymousContext.close();
    }
    safeResult.protectedCompanyViews = true;
    await verifyCompanyInboxInBrowser();
    // Two independently addressable, authenticated company links must be usable
    // in the actual browser, not just present as JSON on the inbox response.
    const companyRequestLink = `/partners?org=${encodeURIComponent(companyOne)}&share=${encodeURIComponent(shareId)}&revision=2&view=request`;
    const companyPlanLink = `/partners?org=${encodeURIComponent(companyOne)}&share=${encodeURIComponent(shareId)}&revision=2&view=itinerary`;
    await page.goto(webOrigin + companyRequestLink, { waitUntil: 'domcontentloaded' });
    await page.locator('.partner-readable-request').waitFor({ state: 'visible', timeout: 15_000 });
    if (await page.locator('.partner-linked-view [role="alert"]').count()) {
      throw new Error('real_provider_company_request_link_access_denied');
    }
    await page.goto(webOrigin + companyPlanLink, { waitUntil: 'domcontentloaded' });
    await page.locator('.partner-shared-day').first().waitFor({ state: 'visible', timeout: 15_000 });
    if (await page.locator('.partner-linked-view [role="alert"]').count()) {
      throw new Error('real_provider_company_plan_link_access_denied');
    }
    safeResult.protectedCompanyDeepLinks = { request: true, itinerary: true, revision: 2 };
    safeResult.protectedCompanyBrowserViews = 2;
    const companyResponsePath = `/api/v1/partners/organizations/${companyOne}/requests/${shareId}/responses`;
    const staleCompanyResponse = await browserApi(page,companyResponsePath,'POST',companyOneReauthenticated.csrfToken,{
      client_request_id:crypto.randomUUID(),revision_id:sharedRevision.revision_id,
      response_kind:'accepted_as_requested',message:'stale offer',
    });
    if (staleCompanyResponse.status !== 409) {
      throw new Error('real_provider_stale_company_revision_not_rejected');
    }
    const acceptedClientRequestId = crypto.randomUUID();
    const acceptedResponse = await requestBrowserJson(page,companyResponsePath,'POST',companyOneReauthenticated.csrfToken,{
      client_request_id:acceptedClientRequestId,revision_id:changedRevision.revision_id,
      response_kind:'accepted_as_requested',message:'QA: We can support this as requested.',
    });
    const conflictingRetry = await browserApi(page,companyResponsePath,'POST',companyOneReauthenticated.csrfToken,{
      client_request_id:acceptedClientRequestId,revision_id:changedRevision.revision_id,
      response_kind:'accepted_as_requested',message:'QA: attempt to change original acceptance',
    });
    if (conflictingRetry.status !== 409) throw new Error('real_provider_company_idempotency_key_conflict_not_rejected');
    const counterResponse = await requestBrowserJson(page,companyResponsePath,'POST',companyOneReauthenticated.csrfToken,{
      client_request_id:crypto.randomUUID(),revision_id:changedRevision.revision_id,
      response_kind:'counter_offer',message:'QA: Revised price and dates.',
      proposed_price_toman:27000000,proposed_start_date:'2026-12-05',
      proposed_end_date:'2026-12-08',proposed_schedule_notes:'QA: adjusted departure sequence',
    });
    if (!acceptedResponse.response?.response_id || !counterResponse.response?.response_id) {
      throw new Error('real_provider_company_response_create_failed');
    }
    const companyResponseList = await requestBrowserJson(page,companyResponsePath,'GET');
    if (companyResponseList.items.length !== 2) throw new Error('real_provider_company_response_inbox_failed');
    await page.goto(webOrigin + companyPlanLink, { waitUntil: 'domcontentloaded' });
    await page.locator('.partner-response-actions').waitFor({ state: 'visible', timeout: 15_000 });
    await page.locator('.partner-response-history summary').waitFor({ state: 'visible', timeout: 15_000 });
    identity = await switchIdentity(phone);
    const travelerResponses = await requestBrowserJson(page,
      `/api/v1/partners/trips/${tripId}/company-responses`, 'GET');
    if (!travelerResponses.items.some(item => item.response_id === acceptedResponse.response.response_id)
      || !travelerResponses.items.some(item => item.response_id === counterResponse.response.response_id)) {
      throw new Error('real_provider_traveler_company_response_inbox_failed');
    }
    await page.goto(webOrigin, { waitUntil: 'domcontentloaded' });
    await page.locator(`.history-trip[data-trip-id="${tripId}"] button`).first().click();
    await page.locator('.traveler-company-responses').waitFor({ state: 'visible', timeout: 15_000 });
    await page.locator('.traveler-company-response').first().waitFor({ state: 'visible', timeout: 15_000 });
    const tripBeforeDecision = await requestBrowserJson(page,`/api/v1/trips/${tripId}`,'GET');
    const decision = await requestBrowserJson(page,
      `/api/v1/partners/trips/${tripId}/company-responses/${counterResponse.response.response_id}/decision`,
      'POST',identity.csrfToken,{decision:'accepted'});
    if (decision.traveler_decision !== 'accepted') {
      throw new Error('real_provider_traveler_company_decision_failed');
    }
    const tripAfterDecision = await requestBrowserJson(page,`/api/v1/trips/${tripId}`,'GET');
    if (tripBeforeDecision.version !== tripAfterDecision.version
      || JSON.stringify(tripBeforeDecision.confirmed_requirements)
          !== JSON.stringify(tripAfterDecision.confirmed_requirements)) {
      throw new Error('real_provider_company_decision_must_not_modify_traveler_trip');
    }
    safeResult.companyProposals = { acceptedAsRequested:true, counterOffer:true,
      travelerAcceptedCounterOffer:true, travelerTripUnchanged:true };

    const revoked = await requestBrowserJson(page,
      `/api/v1/partners/trips/${tripId}/company-shares/${companyTwoShare}`, 'DELETE', identity.csrfToken);
    if (!revoked.revoked) throw new Error('real_provider_revocation_failed');
    for (const deniedPhone of [companyTwoPhone, rejectedPhone]) {
      await switchIdentity(deniedPhone);
      const denied = await requestBrowserJson(page,
        `/api/v1/partners/organizations/${companyTwo}/requests`, 'GET');
      if (denied.items.length) throw new Error('real_provider_revoked_or_unverified_company_saw_request');
      if (deniedPhone === companyTwoPhone) {
        const revokedLink = `/partners?org=${encodeURIComponent(companyTwo)}&share=${encodeURIComponent(companyTwoShare)}&revision=2&view=itinerary`;
        await page.goto(webOrigin + revokedLink, { waitUntil: 'domcontentloaded' });
        await page.locator('.partner-linked-view [role="alert"]').waitFor({ state: 'visible', timeout: 15_000 });
        if (await page.locator('.partner-shared-day').count()) {
          throw new Error('real_provider_revoked_company_deep_link_leaked_itinerary');
        }
      }
    }
    await switchIdentity(companyOnePhone);
    const retained = await requestBrowserJson(page,
      `/api/v1/partners/organizations/${companyOne}/requests`, 'GET');
    if (retained.items.length !== 2) throw new Error('real_provider_revocation_changed_other_recipient');
    safeResult.companyDelivery = {
      channel: 'authenticated_in_app_inbox', recipients: ['QA_COMPANY_A', 'QA_COMPANY_B'],
      eventKinds: ['request_shared', 'request_revised'], revisionCount: 2,
      rejectedCompanyExcluded: true, companyBRevoked: true, companyARetained: true,
    };

    // Return to the traveler identity so the remaining conversation and trip
    // reads prove the original owner can still access their own saved records.
    await page.locator('.auth-signed-in button').first().click();
    await page.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
    identity = await signIn(page, api.controlPort, api.controlToken, phone);
    const conversationResponse = await page.request.get(`${webOrigin}/api/v1/conversations/${conversationId}`);
    const conversation = await conversationResponse.json();
    if (conversationResponse.status() !== 200
      || conversation.messages?.filter(message => message.role === 'assistant').length < 2) {
      throw new Error('real_chat_conversation_turns_not_persisted');
    }
    await page.goto(webOrigin, { waitUntil: 'domcontentloaded' });
    await page.locator(`.history-trip[data-trip-id="${tripId}"]`).waitFor({ state: 'visible' });
    await page.locator(`.history-trip[data-trip-id="${tripId}"] button`).first().click();
    await page.locator('.provisional-itinerary').waitFor({ state: 'visible' });
    await selectAndVerifyLocale(page, 'fa-IR');
    if (safeResult.provisionalEdited
      && await page.locator('.provisional-itinerary .provisional-stop textarea').first().inputValue() !== 'یادداشت آزمایشی مسافر') {
      throw new Error('issue23_provisional_edit_missing_after_reopen');
    }
    await page.locator('#profile-travel-start-picker').click();
    const today = page.locator('.jalali-calendar-grid button[aria-current="date"]');
    const selected = page.locator('.jalali-calendar-grid button[aria-pressed="true"]');
    const todayCount = await today.count();
    const selectedCount = await selected.count();
    if (todayCount !== 1 || selectedCount !== 1) {
      throw new Error('issue23_calendar_state_missing_today_' + todayCount + '_selected_' + selectedCount);
    }
    if (await today.evaluate(el => getComputedStyle(el).backgroundColor)
        === await selected.evaluate(el => getComputedStyle(el).backgroundColor)) {
      throw new Error('issue23_calendar_today_and_selected_colors_equal');
    }
    safeResult.jalaliTodayAndSelectionDistinct = true;
    await page.locator('.jalali-calendar').screenshot({ path: resolve(artifactRoot, 'issue23-jalali-calendar.png') });
    await page.keyboard.press('Escape');
    const finalProviderStatus = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_status' });
    safeResult.providerTelemetry = {
      route: finalProviderStatus.route,
      attempts: finalProviderStatus.attempts,
      successes: finalProviderStatus.successes,
      failures: finalProviderStatus.failures,
      latencyMs: finalProviderStatus.latency_ms,
      responseFieldKeys: finalProviderStatus.response_field_keys,
      responseEvidenceKeys: finalProviderStatus.response_evidence_keys,
    };

    await page.evaluate(() => {
      document.querySelectorAll('input,textarea').forEach(element => { element.value = ''; });
      document.querySelectorAll('#trip-prompt,#trip-follow-up').forEach(element => {
        element.setAttribute('placeholder', '[redacted acceptance input]');
      });
      document.querySelectorAll('.saved-message-user p,.saved-message-assistant p,#trip-prompt,.history-trip > button:first-child')
        .forEach(element => { element.textContent = '[redacted acceptance text]'; });
      document.querySelectorAll('.auth-signed-in *').forEach(element => {
        if (/^\+?[0-9]{8,15}$/.test(element.textContent.trim())) element.textContent = '[test account]';
      });
    });
    const screenshots = [];
    for (const [width, height] of [[390, 844], [1440, 1000]]) {
      await page.setViewportSize({ width, height });
      if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)) {
        throw new Error('real_provider_horizontal_overflow_' + width);
      }
      const screenshot = 'real-chat-' + provider.provider + '-' + width + '.png';
      await page.screenshot({ path: resolve(artifactRoot, screenshot), fullPage: true });
      screenshots.push(screenshot);
    }
    const report = {
      status: 'passed', mode: 'authenticated_real_chat_provider_local_acceptance',
      provider: safeResult, browser: `Chromium ${browser.version()}`,
      database: { host: '127.0.0.1', majorVersion: 17, markerValidated: true, tripPersisted: true },
      privacy: { rawPromptsSaved: false, providerTokenSaved: false, browserTokenStorage: false },
      caseId: 'ISSUE23_QA_TRAVELER_A', endpointTrace, screenshots,
    };
    writeFileSync(resolve(artifactRoot, `real-chat-${provider.provider}.json`), `${JSON.stringify(report, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
    return report;
  } catch (error) {
    writeFileSync(resolve(artifactRoot, 'issue23-partial-trace.json'), JSON.stringify({
      status: 'failed', provider: safeResult, endpointTrace,
    }, null, 2) + '\n', 'utf8');
    throw error;
  } finally {
    if (page) await page.close().catch(() => {});
    await context.close().catch(() => {});
  }
}

async function runForcedOutageFallbackJourney(browser, api, audit, artifactRoot) {
  const context = await browser.newContext({ locale: 'fa-IR', timezoneId: 'Asia/Tehran' });
  const page = await context.newPage();
  page.setDefaultTimeout(45_000);
  const phone = syntheticPhone();
  try {
    await attachBrowserGuards(page, audit);
    await page.goto(webOrigin, { waitUntil: 'domcontentloaded' });
    await selectAndVerifyLocale(page, 'fa-IR');
    await signIn(page, api.controlPort, api.controlToken, phone);
    const before = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_status' });
    if (before.attempts !== 0 || before.route?.scheme !== 'http'
      || before.route?.host !== '127.0.0.1' || before.route?.port === 1234) {
      throw new Error('forced_outage_route_not_isolated_loopback');
    }
    const requestText = '\u0627\u0632 \u0645\u0634\u0647\u062f \u0645\u06cc\u200c\u062e\u0648\u0627\u0645 \u0627\u0632 \u067e\u0633\u200c\u0641\u0631\u062f\u0627 \u0628\u0631\u0627\u06cc \u067e\u0646\u062c \u0631\u0648\u0632 \u0628\u0631\u0645 \u0634\u06cc\u0631\u0627\u0632. \u067e\u0646\u062c \u0646\u0641\u0631 \u0647\u0633\u062a\u06cc\u0645 \u0648 \u0628\u0648\u062f\u062c\u0647\u200c\u0645\u0648\u0646 \u06f3\u06f0 \u0645\u06cc\u0644\u06cc\u0648\u0646 \u062a\u0648\u0645\u0627\u0646\u0647.';
    const turnPromise = page.waitForResponse(response =>
      new URL(response.url()).pathname.endsWith('/assistant-turns') && response.request().method() === 'POST');
    await page.locator('#trip-prompt').fill(requestText);
    await page.locator('.trip-form button[type="submit"]').click();
    const failedTurn = await turnPromise;
    if (failedTurn.status() !== 503) throw new Error(`forced_outage_expected_safe_503_got_${failedTurn.status()}`);
    const diagnostic = page.locator('.extraction-diagnostic');
    await diagnostic.waitFor({ state: 'visible' });
    if (await diagnostic.getAttribute('data-extraction-path') !== 'fallback') {
      throw new Error('forced_outage_fallback_provenance_not_visible');
    }

    const historyResponse = await page.request.get(`${webOrigin}/api/v1/conversations?limit=50`);
    const history = await historyResponse.json();
    const conversation = history.items?.[0];
    const trip = conversation?.trips?.[0];
    if (historyResponse.status() !== 200 || !conversation?.conversation_id || !trip?.trip_id) {
      throw new Error('forced_outage_saved_trip_not_listed');
    }
    const tripResponse = await page.request.get(`${webOrigin}/api/v1/trips/${trip.trip_id}`);
    const saved = await tripResponse.json();
    const fields = saved.extracted_requirements?.requirements_v1?.fields ?? {};
    const expected = {
      origin: fields.origin?.status === 'known' && fields.origin?.source === 'fallback',
      destination: fields.destination?.status === 'known' && fields.destination?.source === 'fallback',
      duration: fields.duration_days?.value === 5 && fields.duration_days?.source === 'fallback',
      travelers: fields.travelers?.value === 5 && fields.travelers?.source === 'fallback',
      budget: fields.budget?.status === 'known' && fields.budget?.source === 'fallback',
      relative_date: fields.relative_start_date?.value?.offset_days === 2
        && fields.relative_start_date?.source === 'fallback',
    };
    if (tripResponse.status() !== 200 || Object.values(expected).some(value => !value)) {
      throw new Error(`forced_outage_regex_fields_failed_${Object.entries(expected).filter(([, ok]) => !ok).map(([key]) => key).join('_')}`);
    }
    await page.waitForFunction(() => {
      const origin = document.querySelector('#profile-origin')?.value || '';
      const duration = document.querySelector('#profile-duration')?.value || '';
      const travelers = document.querySelector('#profile-travelers')?.value || '';
      return origin.includes('\u0645\u0634\u0647\u062f') && duration === '5' && travelers === '5';
    });
    if (!normalizedPersianText(await page.locator('#profile-origin').inputValue()).includes('\u0645\u0634\u0647\u062f')
      || await page.locator('#profile-duration').inputValue() !== '5'
      || await page.locator('#profile-travelers').inputValue() !== '5') {
      throw new Error('forced_outage_fallback_not_synchronized_to_form');
    }
    await page.locator('#profile-origin').fill('\u06a9\u0631\u0645\u0627\u0646\u0634\u0627\u0647');
    const confirm = page.locator('.profile-confirm-action');
    if (await confirm.isDisabled()) throw new Error('forced_outage_manual_profile_cannot_be_confirmed');
    const patchPromise = page.waitForResponse(response =>
      new URL(response.url()).pathname === `/api/v1/trips/${trip.trip_id}` && response.request().method() === 'PATCH');
    await confirm.click();
    const patchResponse = await patchPromise;
    if (patchResponse.status() !== 200) throw new Error('forced_outage_manual_override_not_saved');
    const confirmedResponse = await page.request.get(`${webOrigin}/api/v1/trips/${trip.trip_id}`);
    const confirmed = await confirmedResponse.json();
    if (confirmedResponse.status() !== 200 || confirmed.confirmed_requirements?.origin !== '\u06a9\u0631\u0645\u0627\u0646\u0634\u0627\u0647') {
      throw new Error('forced_outage_confirmed_override_not_persistent');
    }
    const counts = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_status' });
    if (counts.attempts !== 1 || counts.successes !== 0 || counts.failures !== 1) {
      throw new Error('forced_outage_call_count_or_no_retry_failed');
    }
    await page.evaluate(() => {
      document.querySelectorAll('input,textarea').forEach(element => { element.value = ''; });
      document.querySelectorAll('#trip-prompt,#trip-follow-up').forEach(element => {
        element.setAttribute('placeholder', '[redacted acceptance input]');
      });
      document.querySelectorAll('.saved-message-user p,.saved-message-assistant p,#trip-prompt,.history-trip > button:first-child')
        .forEach(element => { element.textContent = '[redacted acceptance text]'; });
      document.querySelectorAll('.auth-signed-in *').forEach(element => {
        if (/^\+?[0-9]{8,15}$/.test(element.textContent.trim())) element.textContent = '[test account]';
      });
    });
    await page.screenshot({ path: resolve(artifactRoot, 'real-chat-forced-outage-fallback.png'), fullPage: true });
    const report = {
      status: 'passed', mode: 'actual_adapter_forced_loopback_outage_and_regex_fallback',
      provider: { route: 'loopback_http_closed_port', attempts: counts.attempts,
        successes: counts.successes, failures: counts.failures, fallbackFormAndPersistence: expected,
        manualOverridePersisted: true, automaticRetry: false },
      database: { host: '127.0.0.1', majorVersion: 17, markerValidated: true, tripPersisted: true },
      privacy: { rawPromptsSaved: false, providerTokenSaved: false, browserTokenStorage: false },
      screenshot: 'real-chat-forced-outage-fallback.png',
    };
    writeFileSync(resolve(artifactRoot, 'real-chat-forced-outage-fallback.json'), `${JSON.stringify(report, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
    return report;
  } finally {
    await page.close().catch(() => {});
    await context.close().catch(() => {});
  }
}

async function runLocaleJourney(browser, api, locale, audit, artifactRoot) {
  const copy = localeCopy[locale];
  const assistantCallsBeforeLocale = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_count' });
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

    const initialPersist = pageA.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/conversations'
      && response.request().method() === 'POST' && response.status() === 201);
    const automaticAssistant = pageA.waitForResponse(response =>
      new URL(response.url()).pathname.endsWith('/assistant-turns') && response.request().method() === 'POST');
    await pageA.locator('#trip-prompt').fill(copy.prompt);
    const inputDirection = await pageA.locator('#trip-prompt').evaluate(element => getComputedStyle(element).direction);
    if (inputDirection !== (locale === 'en-US' ? 'ltr' : 'rtl')) throw new Error(`locale_input_direction_${locale}`);
    await pageA.locator('.trip-form button[type="submit"]').click();
    const persisted = await initialPersist;
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
    const initialAssistant = await automaticAssistant;
    const initialAssistantBody = await initialAssistant.json();
    if (initialAssistant.status() !== 200) {
      const safeCode = typeof initialAssistantBody?.error?.code === 'string' ? initialAssistantBody.error.code : 'unknown';
      throw new Error(`automatic_initial_assistant_turn_failed_${locale}_${initialAssistant.status()}_${safeCode}_${api.safeAssistantFailure() || 'no_safe_failure_log'}`);
    }
    if (!initialAssistantBody.message?.content || initialAssistantBody.trip?.trip_id !== tripId
        || initialAssistantBody.trip?.original_request !== copy.prompt) {
      throw new Error(`automatic_initial_assistant_result_not_persisted_${locale}`);
    }
    assistantTripVersion = initialAssistantBody.trip.version;
    assistantConversationVersion = initialAssistantBody.conversation.version;
    conversationVersion = assistantConversationVersion;
    await pageA.locator('.saved-message-assistant p').first().waitFor({ state: 'visible' });
    const initialAssistantCallCount = await checkedControl(api.controlPort, api.controlToken, { action: 'assistant_call_count' });
    if (initialAssistantCallCount.count !== assistantCallsBeforeLocale.count + 1) {
      throw new Error(`initial_request_did_not_use_exactly_one_assistant_turn_${locale}`);
    }
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
          || Number(budget?.amount) !== 45 || !containsToman(budget?.raw)
          || !containsMillion(budget?.unit) || budget.currency !== 'TOMAN'
          || !accessibility.includes('wheelchair_access')
          || !constraints.some(value => /rough|terrain|ناهموار/iu.test(value))
          || persistedConversation.status() !== 200
          || persistedMessages.messages?.filter(message => message.role === 'user').length < 13
          || latest?.trip?.extracted_requirements?.durationDays?.value !== 15) {
        throw new Error(`persian_15_day_corrections_or_long_history_not_persisted_status=${correctedTripRead.status()}_duration=${extracted?.durationDays?.value}_travelers=${extracted?.travelerCount?.value}_budget_amount=${budget?.amount}_budget_currency=${budget?.currency}_budget_toman=${containsToman(budget?.raw)}_budget_raw_length=${String(budget?.raw ?? '').length}_budget_unit=${budget?.unit || 'missing'}_accessibility=${accessibility.length}_constraints=${constraints.length}_conversation=${persistedConversation.status()}_user_messages=${persistedMessages.messages?.filter(message => message.role === 'user').length ?? -1}_latest_duration=${latest?.trip?.extracted_requirements?.durationDays?.value}`);
      }
      correctedPersistedDurationDays = extracted.durationDays.value;
      if (await pageA.locator('#profile-duration').inputValue() !== '15'
          || await pageA.locator('#profile-travelers').inputValue() !== '4'
          || !containsFortyFive(await pageA.locator('#profile-budget').inputValue())
          || !containsToman(await pageA.locator('#profile-budget').inputValue())) {
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
    if (await pageA.locator('.requirement-accessibility-mandatory').count() === 0) {
      const diagnosticResponse = await pageA.request.get(`${webOrigin}/api/v1/trips/${tripId}`);
      const diagnosticTrip = await diagnosticResponse.json();
      const diagnosticFields = diagnosticTrip.extracted_requirements?.accessibility;
      throw new Error(`mandatory_accessibility_not_rendered_${locale}_trip=${diagnosticResponse.status()}_field_status=${diagnosticFields?.status}_values=${JSON.stringify(diagnosticFields?.value ?? [])}`);
    }
    await pageA.locator('.requirement-accessibility-mandatory').waitFor({ state: 'visible' });
    if (await pageA.locator('#requirement-consent-accessibility-must, #requirement-consent-accessibility-advisory').count() !== 0) {
      throw new Error(`mandatory_access_field_was_offered_consent_downgrade_${locale}`);
    }
    if (await pageA.locator('.requirement-consent').count() !== 0) {
      throw new Error(`routine_profile_confirmation_prompt_was_rendered_${locale}`);
    }
    const confirmButton = pageA.getByRole('button', { name: copy.confirm });
    if (await confirmButton.isDisabled()) throw new Error(`profile_confirmation_unnecessarily_blocked_${locale}`);

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
          || Number(reviewedBudget?.amount) !== 45 || !containsToman(reviewedBudget?.raw)
          || !containsMillion(reviewedBudget?.unit)
          || reviewedBudget.currency !== 'TOMAN') {
        throw new Error('confirmed_persian_15_day_profile_or_budget_denomination_changed');
      }
    }
    const persistedConsent = confirmedTrip.confirmed_requirements?.requirement_consent;
    const consentDecisionFields = Object.keys(persistedConsent?.field_decisions ?? {}).sort();
    const acknowledgedConsentFields = [...(persistedConsent?.advisory_acknowledged_fields ?? [])].sort();
    if (persistedConsent?.contract_version !== 'recommendation-consent-v1'
      || persistedConsent?.profile_version !== confirmedTrip.version
      || consentDecisionFields.length !== 0
      || acknowledgedConsentFields.length !== 0) {
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
    const assessmentsByField = Object.fromEntries((recommendation.requirement_assessments ?? []).map(item => [item.field, item]));
    if (recommendationResponse.status() !== 201 || !recommendationResponse.headers()['cache-control']?.includes('no-store')
      || recommendation.status !== 'needs_confirmation' || recommendation.reason_code !== 'hard_constraints_unverifiable'
      || recommendation.waived_fields?.length !== 0 || recommendation.not_evaluated_fields?.length !== 0
      || ['duration_days', 'budget', 'soft_preference', 'destination'].some(field => assessmentsByField[field]?.status !== 'known')
      || budgetAssessment?.status !== 'known'
      || (preferenceAssessment && preferenceAssessment.status !== 'known')
      || accessibilityAssessment?.decision !== 'must_have' || accessibilityAssessment.status !== 'unresolved'
      || !['access_unverifiable', 'accessibility_unverifiable'].includes(accessibilityAssessment.reason_code)
      || hardConstraintAssessment?.decision !== 'must_have' || hardConstraintAssessment.status !== 'unresolved'
      || !recommendation.unresolved_fields?.includes('hard_constraint') || recommendation.items?.length !== 0) {
      throw new Error(`recommendation_contract_failed_${locale}_${JSON.stringify({
        http: recommendationResponse.status(), status: recommendation.status, reason: recommendation.reason_code,
        waived: recommendation.waived_fields, notEvaluated: recommendation.not_evaluated_fields,
        assessments: recommendation.requirement_assessments?.map(item => [item.field, item.decision, item.status, item.reason_code]),
        unresolved: recommendation.unresolved_fields, items: recommendation.items?.length,
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
    const restoredCandidateText = await pageA.locator('.assistant-candidate').textContent();
    const expectedDestination = locale === 'fa-IR' ? '\u0634\u06cc\u0631\u0627\u0632' : 'Shiraz';
    if (!restoredCandidateText?.includes(expectedDestination)) {
      throw new Error('restored_assistant_candidate_missing_' + locale);
    }
    await pageA.locator('.assistant-candidate button').last().click();
    if (await pageA.locator('.requirement-consent').count() !== 0) {
      throw new Error(`routine_consent_prompt_reappeared_after_restore_${locale}`);
    }
    const reopenedTrip = await pageA.request.get(`${webOrigin}/api/v1/trips/${tripId}`);
    const reopenedRecord = await reopenedTrip.json();
    if (reopenedRecord.confirmed_requirements?.requirement_consent?.profile_version !== reopenedRecord.version
      || Object.keys(reopenedRecord.confirmed_requirements?.requirement_consent?.field_decisions ?? {}).length !== 0) {
      throw new Error(`history_confirmation_version_changed_${locale}`);
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
    const secondPersist = pageA.waitForResponse(response => {
      const path = new URL(response.url()).pathname;
      return response.request().method() === 'POST'
        && (path === '/api/v1/conversations' || path === `/api/v1/conversations/${conversationId}/trips`);
    });
    await pageA.locator('.trip-form button[type="submit"]').click();
    const secondResponse = await secondPersist;
    const secondTrip = await secondResponse.json();
    if (secondResponse.status() !== 201 || !secondTrip?.trip?.trip_id
        || secondTrip.conversation?.conversation_id !== conversationId) {
      throw new Error(`second_trip_not_persisted_${locale}_status=${secondResponse.status()}_path=${new URL(secondResponse.url()).pathname}_code=${secondTrip?.error?.code ?? 'none'}`);
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
    await pageB.locator('.auth-entry > button').first().waitFor({ state: 'visible' });
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
  const realChat = realChatConfiguration();
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
    if (realChat) {
      const report = realChat.provider === 'forced_outage'
        ? await runForcedOutageFallbackJourney(browser, api, audit, artifactRoot)
        : await runRealProviderJourney(browser, api, audit, artifactRoot, realChat);
      if (audit.pageErrors) throw new Error('real_chat_browser_page_error');
      console.log(JSON.stringify({ status: report.status, provider: report.provider.provider || 'forced_outage',
        model: report.provider.model || null, invocationAttempts: report.provider.invocationAttempts ?? report.provider.attempts,
        successfulInvocations: report.provider.successfulInvocations ?? report.provider.successes,
        extractionPath: report.provider.extractionPath || 'fallback',
        correctionTurn: report.provider.correctionTurn ?? false,
        itineraryGenerated: report.provider.itineraryGenerated ?? false,
        persistedAndReopened: report.provider.persistedAndReopened ?? report.provider.manualOverridePersisted,
        artifactRoot }));
      return;
    }
    if (process.env.RAHGARD_NATIONAL_CATALOGUE_E2E === '1') {
      if (process.env.RAHGARD_OWNER_ARCHIVE_PATH == null || process.env.AUTH_TEST_DATABASE_OWNER_PASSWORD == null
          || process.env.RAHGARD_REAL_GEO_E2E === '1' || api.ownerRagEnabled) {
        throw new Error('national_catalogue_mode_requires_local_archive_and_isolated_owner_access');
      }
      const journeys = await runNationalCatalogueAcceptance(browser, api, audit, artifactRoot);
      if (audit.successfulExternalResponses || audit.pageErrors) throw new Error('national_catalogue_browser_runtime_failure');
      const report = {
        status: 'passed', mode: 'full_application_archive_operator_partner_traveler_isolated_acceptance',
        browser: `Chromium ${browser.version()}`,
        database: { name: process.env.AUTH_TEST_DATABASE_NAME, host: '127.0.0.1', majorVersion: 17, markerValidated: true },
        integrations: journeys.simulatedComponents,
        archive: { sha256: journeys.archiveStaging.archive_sha256, staging: journeys.archiveStaging,
          noLiveDatabaseOrVps: true },
        journeys: { operator: journeys.operator, partner: journeys.partner, traveler: journeys.traveler },
        databaseCounts: journeys.databaseCounts,
        trace: journeys.apiTrace,
        screenshots: ['national-catalogue/operator-candidate-review.png','national-catalogue/partner-workspace-persisted.png','national-catalogue/traveler-archive-itinerary-reopened.png'],
        audit: { externalRequestsBlocked: audit.externalRequests, successfulExternalResponses: 0, browserPageErrors: 0 },
        note: 'Fake OTP and an in-process simulated Chat Gateway were used. All archive staging, source review, candidate evidence, identity decision, publication, partner records, recommendation and itinerary requests used the actual authenticated FastAPI and isolated PostgreSQL 17. No live provider or production data was used.',
      };
      writeFileSync(resolve(artifactRoot, 'report.json'), `${JSON.stringify(report, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
      console.log(JSON.stringify({ status: report.status, mode: report.mode, archive: report.archive.staging.candidate_rows_by_kind,
        published: journeys.databaseCounts.published_destinations, operator: 'passed', partner: 'passed', traveler: 'passed', artifactRoot }));
      return;
    }
    if (process.env.RAHGARD_REAL_GEO_E2E === '1') {
      if (process.env.RAHGARD_RUN_GEO_QA !== '1' || api.ownerRagEnabled) {
        throw new Error('qa_real_geo_requires_explicit_disposable_opt_in_and_rag_off');
      }
      const results = [];
      const locales = process.env.RAHGARD_GEO_BROWSE_E2E === '1' ? ['fa-IR'] : ['fa-IR', 'en-US', 'ar'];
      for (const locale of locales) {
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
