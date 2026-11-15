import { chromium } from 'playwright-core';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const root = resolve(import.meta.dirname, '../..');
const output = resolve(root, 'artifacts/p0-product-recovery/screenshots');
const origin = process.env.P0_VISUAL_ORIGIN || 'http://127.0.0.1:4179';
const executablePath = process.env.P0_CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const variants = [
  { name: 'fa-IR-mobile', locale: 'fa-IR', width: 390, height: 844 },
  { name: 'fa-IR-desktop', locale: 'fa-IR', width: 1440, height: 1000 },
];

await mkdir(output, { recursive: true });
const browser = await chromium.launch({ executablePath, headless: true });
const results = [];
try {
  for (const variant of variants) {
    const page = await browser.newPage({
      locale: variant.locale,
      viewport: { width: variant.width, height: variant.height },
      reducedMotion: 'reduce',
    });
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.name));
    // The screenshots document the anonymous shell. Stop the production API
    // proxy from reaching any ambient development service on this machine.
    await page.route('**/api/**', route => route.fulfill({ status: 503, body: '{}' }));
    await page.goto(origin, { waitUntil: 'domcontentloaded' });
    await page.locator('#locale').selectOption(variant.locale);
    await page.waitForFunction(locale => document.documentElement.lang === locale, variant.locale);
    await page.evaluate(() => document.fonts.ready);
    const layout = await page.evaluate(() => ({
      viewport: innerWidth,
      document: document.documentElement.scrollWidth,
      direction: document.documentElement.dir,
      language: document.documentElement.lang,
    }));
    const file = resolve(output, `${variant.name}.png`);
    await page.screenshot({ path: file, fullPage: true });
    results.push({ ...variant, ...layout, horizontalOverflow: layout.document > layout.viewport,
      pageErrors, screenshot: file.replaceAll('\\', '/') });
    await page.close();
  }
} finally {
  await browser.close();
}

const report = {
  mode: 'anonymous PWA shell; API requests locally stubbed to 503 and not forwarded',
  browser: `Chromium ${browser.version()}`,
  source_sha: process.env.P0_SOURCE_SHA || 'uncommitted working tree',
  results,
};
const reportPath = resolve(output, 'report.json');
await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, { flag: 'w', encoding: 'utf8' });
console.log(JSON.stringify({ results: results.map(({ name, horizontalOverflow, pageErrors }) => ({ name, horizontalOverflow, pageErrors })), report: reportPath }));
if (results.some(result => result.horizontalOverflow || result.pageErrors.length)) process.exitCode = 1;
