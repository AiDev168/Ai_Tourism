// One explicitly authorized real-apex journey. Credentials and request text are
// never printed; screenshots are written only to an owner-private directory.
import { randomBytes } from 'node:crypto';
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

const origin = 'https://hinaa.ir';
if (process.env.RAHGARD_LIVE_V2_ACCEPTANCE !== 'I_AUTHORIZE_ONE_TEST_ACCOUNT') {
  throw new Error('Set the one-run authorization flag before the live acceptance run.');
}
const hasExistingCredentials = Boolean(process.env.RAHGARD_ACCEPTANCE_EMAIL && process.env.RAHGARD_ACCEPTANCE_PASSWORD);
if (!hasExistingCredentials && process.env.RAHGARD_ALLOW_ONE_TEST_REGISTRATION !== 'I_AUTHORIZE_ONE_TEST_ACCOUNT') {
  throw new Error('Supply a private existing test login or separately authorize one disposable test registration.');
}

const generated = hasExistingCredentials ? null : {
  email: `issue24-${randomBytes(6).toString('hex')}@example.com`,
  password: `R7!${randomBytes(3).toString('hex')}`.slice(0, 9),
};
const email = process.env.RAHGARD_ACCEPTANCE_EMAIL ?? generated.email;
const password = process.env.RAHGARD_ACCEPTANCE_PASSWORD ?? generated.password;
const browser = await chromium.launch({
  executablePath: process.env.E2E_CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  args: ['--disable-background-networking', '--disable-quic'],
});
const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await context.newPage();
page.setDefaultTimeout(25_000);
let phase = 'open';
let pageErrors = 0;
const apiEvents = [];
let omittedApiEvents = 0;
const maxApiEvents = 80;
page.on('pageerror', () => { pageErrors += 1; });
page.on('response', async response => {
  try {
    const url = new URL(response.url());
    if (url.origin !== origin || !url.pathname.startsWith('/api/v1/')) return;
    const request = response.request();
    const id = response.headers()['x-request-id'] ?? '';
    const event = {
      method: request.method(),
      path: url.pathname.replace(/[0-9a-f-]{36}/gi, ':id'),
      status: response.status(),
      request_id: /^[A-Za-z0-9._:-]{1,100}$/.test(id) ? id : null,
    };
    if (request.method() !== 'GET' && response.status() >= 400) {
      const body = await response.json().catch(() => null);
      const code = body?.detail?.code ?? body?.detail ?? body?.error?.code;
      if (typeof code === 'string' && /^[a-z0-9_]{1,80}$/i.test(code)) event.error_code = code;
    }
    if (apiEvents.length < maxApiEvents) apiEvents.push(event);
    else omittedApiEvents += 1;
  } catch { /* Never let diagnostics interfere with the real browser journey. */ }
});

function assert(condition, label) { if (!condition) throw new Error(label); }
function normalized(value) { return typeof value === 'string' ? value.normalize('NFKC').trim() : ''; }
function safeScreenshotPath() {
  const configured = process.env.RAHGARD_PRIVATE_EVIDENCE_DIR;
  if (!configured) return null;
  const dir = resolve(configured);
  const repository = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
  const rel = relative(repository, dir);
  assert(!isAbsolute(rel) && (rel === '..' || rel.startsWith(`..${sep}`)), 'private_evidence_dir_must_be_outside_repo');
  return resolve(dir, 'issue24-live-apex-390.png');
}

try {
  phase = 'public_apex';
  const root = await page.goto(origin, { waitUntil: 'domcontentloaded' });
  assert(root?.status() === 200 && page.url() === `${origin}/`, 'apex_root_not_200');
  const assets = await page.evaluate(() => ({
    styles: [...document.querySelectorAll('link[rel="stylesheet"]')].map(node => new URL(node.href).pathname),
    scripts: [...document.querySelectorAll('script[src]')].map(node => new URL(node.src).pathname),
  }));
  assert(assets.styles.some(path => /assets\/.*\.css$/.test(path)), 'hashed_css_asset_missing');
  assert(assets.scripts.some(path => /assets\/.*\.js$/.test(path)), 'hashed_js_asset_missing');

  await page.locator('#locale').selectOption('en-US');
  await page.locator('.auth-entry > button').first().click();
  if (generated) {
    await page.getByRole('button', { name: 'Create a pilot email account', exact: true }).click();
  }
  await page.locator('#auth-stage-email').fill(email);
  await page.locator('#auth-stage-password').fill(password);
  phase = generated ? 'register_once' : 'login';
  const authPath = generated ? '/api/v1/auth/staging/register' : '/api/v1/auth/staging/login';
  const authResponse = page.waitForResponse(r => new URL(r.url()).pathname === authPath && r.request().method() === 'POST');
  await page.locator('.auth-panel form button[type="submit"]').click();
  assert((await authResponse).status() === 200, `${generated ? 'registration' : 'login'}_failed`);
  await page.locator('.auth-signed-in').waitFor();
  const cookie = (await context.cookies(origin)).find(item => item.name === '__Host-rahgard_session');
  assert(cookie?.secure && cookie.httpOnly && cookie.path === '/' && cookie.domain === 'hinaa.ir', 'secure_host_cookie_missing');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('.auth-signed-in').waitFor();

  const screenshot = safeScreenshotPath();
  if (screenshot) {
    const { mkdir } = await import('node:fs/promises');
    await mkdir(resolve(screenshot, '..'), { recursive: true });
    await page.screenshot({ path: screenshot, fullPage: true, animations: 'disabled' });
  }

  phase = 'create_conversation_and_trip';
  const prompt = 'از مشهد می‌خوام از پس‌فردا برای پنج روز برم شیراز. پنج نفر هستیم و بودجه‌مون ۳۰ میلیون تومنه. بیشتر جاهای تاریخی و باغ‌ها رو دوست داریم.';
  await page.locator('#trip-prompt').fill(prompt);
  const createResponsePromise = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/conversations' && r.request().method() === 'POST', { timeout: 45_000 });
  await page.locator('.trip-form button[type="submit"]').click();
  const createResponse = await createResponsePromise;
  assert([200, 201].includes(createResponse.status()), 'conversation_create_http_failure');
  const created = await createResponse.json();
  const tripId = created?.trip?.trip_id;
  const conversationId = created?.conversation?.conversation_id;
  assert(/^[0-9a-f-]{36}$/i.test(tripId ?? ''), 'persisted_trip_id_missing');
  assert(/^[0-9a-f-]{36}$/i.test(conversationId ?? ''), 'persisted_conversation_id_missing');

  phase = 'assistant_reply_persistence';
  let assistantPersisted = false;
  let assistantProviderTagged = false;
  let assistantModelTagged = false;
  for (let i = 0; i < 60; i += 1) {
    const state = await page.evaluate(async id => {
      const response = await fetch(`/api/v1/conversations/${id}`, { credentials: 'same-origin', cache: 'no-store' });
      if (!response.ok) return { status: response.status, assistant: 0, providerTagged: false, modelTagged: false };
      const body = await response.json();
      const messages = body.messages?.filter(message => message.role === 'assistant') ?? [];
      return { status: response.status, assistant: messages.length,
        providerTagged: messages.some(message => typeof message.provider_name === 'string' && message.provider_name.length > 0),
        modelTagged: messages.some(message => typeof message.model_name === 'string' && message.model_name.length > 0) };
    }, conversationId);
    if (state.status === 200 && state.assistant > 0) {
      assistantPersisted = true;
      assistantProviderTagged = state.providerTagged;
      assistantModelTagged = state.modelTagged;
      break;
    }
    await page.waitForTimeout(1000);
  }
  assert(assistantPersisted, 'assistant_reply_not_persisted');

  phase = 'review_profile';
  const originField = page.locator('#profile-origin');
  const destinationField = page.locator('#profile-destination-0');
  await destinationField.waitFor();
  if (!await destinationField.inputValue()) await destinationField.fill('شیراز');
  if (!await page.locator('#profile-duration').inputValue()) await page.locator('#profile-duration').fill('5');
  if (!await originField.inputValue()) await originField.fill('مشهد');
  if (!await page.locator('#profile-travelers').inputValue()) await page.locator('#profile-travelers').fill('5');
  if (!await page.locator('#profile-budget').inputValue()) await page.locator('#profile-budget').fill('۳۰ میلیون تومان');
  for (const field of await page.locator('.requirement-consent-field').all()) {
    await field.locator('input[value="advisory"]').check();
    await field.locator('input[type="checkbox"]').check();
  }
  const profileSavedPromise = page.waitForResponse(r => new URL(r.url()).pathname === `/api/v1/trips/${tripId}` && r.request().method() === 'PATCH');
  await page.locator('.profile-confirm-action').click();
  assert((await profileSavedPromise).status() === 200, 'profile_confirmation_failed');
  const confirmedProfile = await page.evaluate(async id => {
    const response = await fetch(`/api/v1/trips/${id}`, { credentials: 'same-origin', cache: 'no-store' });
    return response.ok ? response.json() : null;
  }, tripId);
  const confirmed = confirmedProfile?.confirmed_requirements ?? {};
  const destinations = Array.isArray(confirmed.destinations) ? confirmed.destinations.map(value => normalized(value)) : [];
  const budget = confirmed.budget ?? {};
  const budgetEvidence = `${normalized(budget.raw)} ${normalized(budget.unit)}`;
  assert(destinations.some(value => value.includes('شیراز')) && normalized(confirmed.origin).includes('مشهد'), 'confirmed_trip_locations_mismatch');
  assert(confirmed.duration_days === 5 && confirmedProfile?.duration_days === 5, 'confirmed_duration_mismatch');
  assert(confirmed.traveler_count === 5 && confirmedProfile?.traveler_count === 5, 'confirmed_traveler_count_mismatch');
  // The canonical profile intentionally preserves magnitude + denomination
  // (for example 30 + “million toman”). Legacy trip columns only represent an
  // exact IRR amount and must stay NULL when that shape cannot be represented.
  assert(Number(budget.amount) === 30
    && String(budget.currency ?? '').toUpperCase() === 'TOMAN'
    && /million|میلیون|ملیون/iu.test(budgetEvidence)
    && /toman|تومان|تومن/iu.test(budgetEvidence), 'confirmed_budget_mismatch');

  phase = 'recommendation_and_company_eligibility';
  const recommendationPromise = page.waitForResponse(r => new URL(r.url()).pathname === `/api/v1/trips/${tripId}/recommendations` && r.request().method() === 'POST');
  await page.locator('.recommendation-controls button').first().click();
  const recommendationResponse = await recommendationPromise;
  assert(recommendationResponse.status() === 201, 'recommendation_request_failed');
  const recommendationBody = await recommendationResponse.json();
  const recommendationStatus = recommendationBody.status;
  assert(['available', 'empty', 'needs_confirmation'].includes(recommendationStatus), 'recommendation_status_invalid');
  const optionsResponse = await page.evaluate(async id => {
    const response = await fetch(`/api/v1/partners/trips/${id}/company-share-options`, { credentials: 'same-origin', cache: 'no-store' });
    return { status: response.status, body: response.ok ? await response.json() : null };
  }, tripId);
  assert(optionsResponse.status === 200 && Number.isInteger(optionsResponse.body?.eligible_count), 'company_eligibility_unavailable');

  phase = 'five_day_editable_plan';
  const blankButton = page.getByRole('button', { name: 'Create an editable blank itinerary', exact: true });
  assert(await blankButton.count(), 'editable_blank_plan_action_missing');
  const planResponsePromise = page.waitForResponse(r => new URL(r.url()).pathname === `/api/v1/trips/${tripId}/provisional-itineraries` && r.request().method() === 'POST');
  await blankButton.click();
  const planResponse = await planResponsePromise;
  assert([200, 201].includes(planResponse.status()), 'provisional_save_failed');
  const plan = await planResponse.json();
  const planId = plan.provisional_itinerary_id;
  assert(planId && plan.status === 'provisional_unverified' && Array.isArray(plan.days) && plan.days.length === 5, 'five_day_plan_not_persisted_or_mislabeled');
  for (let day = 1; day <= 5; day += 1) {
    const input = page.locator(`#provisional-add-${day}`);
    const detail = input.locator('xpath=ancestor::details[1]');
    if (await detail.count() && !await detail.evaluate(element => element.open)) await detail.locator('summary').click();
    await input.fill(day === 1 ? 'بازدید از یک مکان تاریخی منتخب پس از بررسی' : `بررسی و انتخاب برنامهٔ روز ${day}`);
    await input.locator('..').getByRole('button').click();
  }
  const editPromise = page.waitForResponse(r => new URL(r.url()).pathname === `/api/v1/provisional-itineraries/${planId}` && r.request().method() === 'PUT');
  await page.getByRole('button', { name: 'Save edits', exact: true }).click();
  assert((await editPromise).status() === 200, 'provisional_edit_save_failed');

  let sharedRecipientCount = 0;
  if (optionsResponse.body.eligible_count > 0) {
    phase = 'explicit_selected_company_share';
    const recipient = page.locator('.company-share-options label:not(.company-share-consent) input[type="checkbox"]').first();
    assert(await recipient.count(), 'eligible_company_control_missing');
    await recipient.check();
    await page.locator('.company-share-consent input[type="checkbox"]').check();
    const sharePromise = page.waitForResponse(r => new URL(r.url()).pathname === `/api/v1/partners/trips/${tripId}/company-shares` && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Share with selected companies', exact: true }).click();
    const shareResponse = await sharePromise;
    assert(shareResponse.status() === 201, 'explicit_company_share_failed');
    const shareBody = await shareResponse.json();
    sharedRecipientCount = shareBody.recipient_count;
    assert(sharedRecipientCount === 1, 'selected_company_share_count_mismatch');
  }

  phase = 'logout_login_and_reopen';
  await page.locator('.auth-signed-in button').first().click();
  await page.locator('.auth-entry > button').first().click();
  await page.locator('#auth-stage-email').fill(email);
  await page.locator('#auth-stage-password').fill(password);
  const loginPromise = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/auth/staging/login' && r.request().method() === 'POST');
  await page.locator('.auth-panel form button[type="submit"]').click();
  assert((await loginPromise).status() === 200, 'reauthentication_failed');
  await page.locator('.auth-signed-in').waitFor();
  const finalTrip = await page.evaluate(async id => { const r = await fetch(`/api/v1/trips/${id}`, { credentials: 'same-origin' }); return { status: r.status, body: r.ok ? await r.json() : null }; }, tripId);
  const finalPlan = await page.evaluate(async id => { const r = await fetch(`/api/v1/trips/${id}/provisional-itineraries`, { credentials: 'same-origin' }); return { status: r.status, body: r.ok ? await r.json() : null }; }, tripId);
  const finalConversation = await page.evaluate(async id => { const r = await fetch(`/api/v1/conversations/${id}`, { credentials: 'same-origin' }); return { status: r.status, body: r.ok ? await r.json() : null }; }, conversationId);
  const finalShares = await page.evaluate(async id => { const r = await fetch(`/api/v1/partners/trips/${id}/company-shares`, { credentials: 'same-origin' }); return { status: r.status, body: r.ok ? await r.json() : null }; }, tripId);
  assert(finalTrip.status === 200 && finalTrip.body?.trip_id === tripId, 'trip_reopen_failed');
  assert(finalPlan.status === 200 && finalPlan.body?.provisional_itinerary_id === planId && finalPlan.body?.days?.length === 5, 'five_day_plan_reopen_failed');
  assert(finalConversation.status === 200 && finalConversation.body?.conversation_id === conversationId, 'conversation_reopen_failed');
  assert(finalShares.status === 200 && (finalShares.body?.items?.length ?? 0) === sharedRecipientCount, 'company_shares_reopen_failed');
  assert(pageErrors === 0, 'uncaught_browser_error');

  process.stdout.write(`${JSON.stringify({ status: 'PASS', origin, viewport: '390x844',
    hashedCssDelivered: true, hashedJsDelivered: true, accountMode: generated ? 'one-time-test-registration' : 'existing-test-login',
    secureHostCookie: true, tripSaved: true, conversationSaved: true, assistantPersisted,
    assistantProviderTagged, assistantModelTagged, realProviderInferenceVerified: assistantProviderTagged && assistantModelTagged,
    persistedProfile: { destination: 'شیراز', origin: 'مشهد', durationDays: 5, travelers: 5,
      budgetMagnitude: 30, budgetCurrency: 'TOMAN', budgetScaleAndSourceRetained: true },
    profileConfirmed: true, recommendationStatus, eligibleCompanyCount: optionsResponse.body.eligible_count,
    companySharingSent: sharedRecipientCount > 0, sharedRecipientCount, fiveDayPlanSavedEditedReopened: true, reauthenticated: true,
    screenshotPrivate: Boolean(screenshot), pageErrors, apiEvents, omittedApiEvents })}\n`);
} catch (error) {
  const failedEvents = apiEvents.filter(event => event.method !== 'GET' && event.status >= 400);
  process.stderr.write(`LIVE_APEX_ACCEPTANCE_BLOCKED ${JSON.stringify({ phase, error: String(error?.message ?? 'unknown').slice(0, 160),
    failedEvents, lastApiEvents: apiEvents.slice(-8), omittedApiEvents, pageErrors })}\n`);
  process.exitCode = 1;
} finally {
  await context.close();
  await browser.close();
}
