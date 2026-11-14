// Dedicated, visible, isolated Chrome checkpoint for the owner's private pilot.
// Uses a fresh browser context and never reads personal Chrome cookies.
import { chromium } from 'playwright-core';
import { createInterface } from 'node:readline';

const browser = await chromium.launch({
  headless: false,
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  args: ['--no-first-run', '--start-maximized'],
});
const context = await browser.newContext({ ignoreHTTPSErrors: true, locale: 'fa-IR', viewport: { width: 1440, height: 960 } });
const page = await context.newPage();
let pageErrors = 0;
page.on('pageerror', () => { pageErrors += 1; });
page.on('dialog', dialog => { void dialog.dismiss(); });
const safePath = pathname => pathname.replace(/[0-9a-f-]{36}/giu, ':id');
page.on('request', request => {
  const url = new URL(request.url());
  if (url.pathname.startsWith('/api/v1/')) process.stdout.write(`API_REQUEST:${request.method()}:${safePath(url.pathname)}\n`);
});
page.on('response', response => {
  const url = new URL(response.url());
  if (url.pathname.startsWith('/api/v1/')) process.stdout.write(`API_RESPONSE:${response.status()}:${safePath(url.pathname)}\n`);
});
await page.goto('https://localhost:8443/', { waitUntil: 'domcontentloaded' });
process.stdout.write('ISSUE12_CHROME_READY: privately sign in in this dedicated visible Chrome window; no credentials are captured.\n');

const input = createInterface({ input: process.stdin, output: process.stdout });
for await (const raw of input) {
  const command = raw.trim();
  try {
    if (command === 'status') {
      const authenticated = await page.locator('.auth-signed-in').isVisible().catch(() => false);
      let assistant = 'not_checked';
      if (authenticated) {
        const result = await page.evaluate(async () => {
          const response = await fetch('/api/v1/assistant/status', { credentials: 'same-origin', cache: 'no-store' });
          return { status: response.status, body: await response.json().catch(() => null) };
        });
        assistant = result.status === 200
          ? `${result.body.state};remaining=${Math.min(result.body.user_remaining, result.body.global_remaining)}`
          : `http_${result.status}`;
      }
      process.stdout.write(`AUTHENTICATED:${authenticated};CHAT_STATUS:${assistant};PAGE_ERRORS:${pageErrors}\n`);
    } else if (command === 'acceptance') {
      if (!(await page.locator('.auth-signed-in').isVisible().catch(() => false))) {
        process.stdout.write('ACCEPTANCE_BLOCKED:owner_login_required_in_this_window\n');
        continue;
      }
      const { runIssue12Acceptance } = await import(`./issue12-acceptance.mjs?run=${Date.now()}`);
      const result = await runIssue12Acceptance({ page });
      process.stdout.write(`ISSUE12_ACCEPTANCE:${result.status};CHAT_SUCCESS_DELTA:${result.chatSuccessDelta};PAGE_ERRORS:${pageErrors}\n`);
    } else if (command === 'exit') {
      break;
    } else {
      process.stdout.write('COMMANDS: status | acceptance | exit\n');
    }
  } catch (error) {
    const code = error instanceof Error && /^[a-z0-9_:-]+$/u.test(error.message)
      ? error.message : error?.name === 'TimeoutError' ? 'browser_timeout' : 'acceptance_error';
    process.stdout.write(`ISSUE12_ACTION_FAILED:${code};PAGE_ERRORS:${pageErrors}\n`);
  }
}

await context.close();
await browser.close();
