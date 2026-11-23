// Read-only public apex UI diagnostic. It never fills or submits a traveler form.
import { chromium } from 'playwright-core';

const origin = process.env.RAHGARD_PUBLIC_ORIGIN || 'https://hinaa.ir';
if (new URL(origin).origin !== origin || new URL(origin).protocol !== 'https:') {
  throw new Error('RAHGARD_PUBLIC_ORIGIN must be an exact HTTPS origin.');
}
const browser = await chromium.launch({ executablePath: process.env.E2E_CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  let pageErrors = 0;
  page.on('pageerror', () => { pageErrors += 1; });
  const response = await page.goto(`${origin}/`, { waitUntil: 'domcontentloaded', timeout: 20_000 });
  const result = await page.evaluate(() => ({
    localeControl: Boolean(document.querySelector('#locale')),
    tripPrompt: Boolean(document.querySelector('#trip-prompt')),
    submitControl: Boolean(document.querySelector('.trip-form button[type="submit"]')),
    authControl: Boolean(document.querySelector('.auth-entry button')),
    hashedCss: [...document.querySelectorAll('link[rel="stylesheet"]')].some(link => /\/assets\/[^/]+\.css$/.test(new URL(link.href).pathname)),
    hashedJs: [...document.querySelectorAll('script[src]')].some(script => /\/assets\/[^/]+\.js$/.test(new URL(script.src).pathname)),
    horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  }));
  if (response?.status() !== 200 || page.url() !== `${origin}/` || pageErrors
      || !result.localeControl || !result.tripPrompt || !result.submitControl || !result.authControl
      || !result.hashedCss || !result.hashedJs || result.horizontalOverflow) {
    process.stderr.write(`${JSON.stringify({ status: 'FAIL', httpStatus: response?.status() ?? null, pageErrors, ...result })}\n`);
    process.exitCode = 1;
  } else {
    process.stdout.write(`${JSON.stringify({ status: 'PASS_READ_ONLY', origin, httpStatus: 200, pageErrors, ...result, submitted: false })}\n`);
  }
} finally {
  await browser.close();
}
