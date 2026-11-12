// Manual credential checkpoint for the real private pilot. Never records
// credentials, cookies, storage state, requests, or private page text.
import { chromium } from 'playwright-core';
import { createInterface } from 'node:readline';

const browser = await chromium.launch({
  headless: false,
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  args: ['--no-first-run'],
});
const context = await browser.newContext({ ignoreHTTPSErrors: true, locale: 'fa-IR' });
const page = await context.newPage();
let pageErrors = 0;
page.on('pageerror', () => { pageErrors += 1; });
page.on('dialog', dialog => { void dialog.dismiss(); });
const safeRoute = value => value.replace(/[0-9a-f-]{36}/giu, ':id');
page.on('request', request => {
  const url = new URL(request.url());
  if (url.pathname.startsWith('/api/v1/')) process.stdout.write(`API_REQUEST:${request.method()}:${safeRoute(url.pathname)}\n`);
});
page.on('response', response => {
  const url = new URL(response.url());
  if (url.pathname.startsWith('/api/v1/')) process.stdout.write(`API_RESPONSE:${response.status()}:${safeRoute(url.pathname)}\n`);
});
await page.goto('https://localhost:8443/', { waitUntil: 'domcontentloaded' });
process.stdout.write('PILOT_BROWSER_READY: enter the owner login privately in Chrome.\n');
const input = createInterface({ input: process.stdin, output: process.stdout });
for await (const command of input) {
  try {
  const action = command.trim();
  if (action === 'status') {
    const signedIn = await page.locator('.trip-history').count() > 0;
    process.stdout.write(`AUTHENTICATED_UI:${signedIn};PAGE_ERRORS:${pageErrors}\n`);
  } else if (action === 'ready') {
    if (!(await page.locator('.auth-signed-in').isVisible().catch(() => false))) {
      process.stdout.write('OWNER_LOGIN_NOT_COMPLETE_IN_THIS_WINDOW\n');
      continue;
    }
    try {
      const { runJourney } = await import(`./issue11-journey-runner.mjs?run=${Date.now()}`);
      await runJourney({ page, context });
    } catch (error) {
      const code = error instanceof Error && /^[a-z0-9_:-]+$/u.test(error.message) ? error.message
        : error?.name === 'TimeoutError' ? 'browser_timeout'
          : error?.name === 'Error' ? 'browser_action_error' : 'unexpected_browser_error';
      process.stdout.write(`JOURNEY_BLOCKED:${code}\n`);
    }
  } else if (action === 'history') {
    const buttons = page.locator('.history-trip > button:first-child');
    await buttons.first().waitFor({ state: 'visible' });
    const count = await buttons.count();
    const results = [];
    for (let index = 0; index < Math.min(count, 2); index += 1) {
      const responsePromise = page.waitForResponse(response =>
        /\/api\/v1\/conversations\/[0-9a-f-]+$/i.test(new URL(response.url()).pathname)
        && response.request().method() === 'GET', { timeout: 12000 });
      await buttons.nth(index).click();
      const response = await responsePromise;
      const reviewVisible = await page.locator('#profile-duration').isVisible().catch(() => false);
      results.push({ row: index + 1, status: response.status(), reviewVisible });
      process.stdout.write(`HISTORY_ROW:${index + 1};STATUS:${response.status()};REVIEW_VISIBLE:${reviewVisible}\n`);
    }
    process.stdout.write(`HISTORY_RESULTS:${JSON.stringify(results)};PAGE_ERRORS:${pageErrors}\n`);
  } else if (action === 'new_trip') {
    const request = 'برای فردا برای 5 نفر برای بازدید از مناطق تاریخی شیراز برنامه ریزی سفر کن و هزینه ای که میخوایم بکنیم 5 میلیون تومان است';
    await page.locator('#trip-prompt').fill(request);
    const responsePromise = page.waitForResponse(response =>
      new URL(response.url()).pathname === '/api/v1/requirements/interpret'
      && response.request().method() === 'POST');
    await page.locator('.trip-form button[type="submit"]').click();
    const response = await responsePromise;
    const body = response.ok() ? await response.json() : null;
    const fields = body?.requirements?.fields;
    const contractCorrect = fields?.destination?.value === 'شیراز'
      && fields?.travelers?.value === 5
      && fields?.relative_start_date?.value?.offset_days === 1
      && fields?.duration_days?.status === 'missing'
      && fields?.budget?.value?.amount === '5'
      && fields?.budget?.value?.scale === 'million'
      && fields?.budget?.value?.currency === 'TOMAN'
      && fields?.interests?.value?.includes('historical_attractions');
    process.stdout.write(`NEW_TRIP_INTERPRET:${response.status()};CONTRACT_CORRECT:${Boolean(contractCorrect)};PAGE_ERRORS:${pageErrors}\n`);
  } else if (action === 'persist') {
    const responsePromise = page.waitForResponse(response =>
      new URL(response.url()).pathname === '/api/v1/conversations'
      && response.request().method() === 'POST');
    await page.locator('.journey-action').click();
    const response = await responsePromise;
    const body = response.ok() ? await response.json() : null;
    const reviewVisible = await page.locator('#profile-duration').isVisible().catch(() => false);
    process.stdout.write(`PERSIST:${response.status()};REVIEW_VISIBLE:${reviewVisible};ORIGINAL_PRESERVED:${body?.trip?.original_request === 'برای فردا برای 5 نفر برای بازدید از مناطق تاریخی شیراز برنامه ریزی سفر کن و هزینه ای که میخوایم بکنیم 5 میلیون تومان است'};PAGE_ERRORS:${pageErrors}\n`);
  } else if (action === 'assistant') {
    if (!(await page.locator('#assistant-remote-consent').isChecked())) {
      process.stdout.write('ASSISTANT_BLOCKED:owner_must_check_processing_consent_in_browser\n');
      continue;
    }
    await page.locator('#trip-follow-up').fill('مدت سفر مشخص نیست؛ برای برنامه‌ریزی چه اطلاعات دیگری لازم است؟');
    const responsePromise = page.waitForResponse(response =>
      /\/api\/v1\/conversations\/[0-9a-f-]+\/assistant-turns$/i.test(new URL(response.url()).pathname)
      && response.request().method() === 'POST');
    await page.locator('.assistant-controls > button').click();
    const response = await responsePromise;
    const body = response.ok() ? await response.json() : null;
    const visible = await page.locator('.saved-message-assistant p').count() > 0;
    process.stdout.write(`ASSISTANT:${response.status()};VISIBLE:${visible};CANDIDATE_TYPED:${body?.candidate_requirements?.contract_version === 'trip-requirements-v1'};PAGE_ERRORS:${pageErrors}\n`);
  } else if (action === 'exit') {
    break;
  }
  } catch (error) {
    process.stdout.write(`ACTION_FAILED:${error instanceof Error ? error.name : 'UnknownError'};PAGE_ERRORS:${pageErrors}\n`);
  }
}
await context.close();
await browser.close();
