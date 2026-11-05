import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { relative, resolve } from 'node:path';

const root = resolve(import.meta.dirname, '../..');
const output = resolve(root, 'artifacts/visual-qa');
const executablePath = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const server = spawn(process.execPath, [resolve(root, 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '4179', '--strictPort'], { cwd: resolve(root, 'frontend'), stdio: 'ignore' });
const locales = ['fa-IR', 'en-US', 'ar'];
const widths = [360, 390, 430, 768, 1024, 1440];
const results = [];
let browser;
try {
  let ready = false;
  for (let i = 0; i < 60; i++) {
    try { ready = (await fetch('http://127.0.0.1:4179')).ok; } catch {}
    if (ready) break;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  if (!ready) throw new Error('Vite did not start on 127.0.0.1:4179');
  browser = await chromium.launch({ executablePath, headless: true });
  for (const locale of locales) {
    for (const width of widths) {
      const page = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: 1 });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto('http://127.0.0.1:4179', { waitUntil: 'networkidle' });
      await page.locator('#locale').selectOption(locale);
      await page.waitForFunction(expected => document.documentElement.lang === expected, locale);
      const direction = await page.locator('html').getAttribute('dir');
      const title = await page.title();
      const layout = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
      const imageLoaded = await page.locator('.hero-photo').evaluate(image => image.complete && image.naturalWidth > 0);
      await page.locator('#trip-prompt').fill('Kashan کاشان كاشان · long mixed-script itinerary ' + 'آرام '.repeat(35));
      const mixedScriptLayout = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
      await page.locator('#trip-prompt').fill('');
      const editButton = page.locator('.itinerary .outline');
      await editButton.click();
      const itineraryInputs = page.locator('.itinerary-input');
      await itineraryInputs.first().fill('Kashan کاشان كاشان · ' + 'route '.repeat(30));
      const editLayout = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
      await itineraryInputs.first().fill('');
      await editButton.click();
      await page.addScriptTag({ path: resolve(root, 'frontend/node_modules/axe-core/axe.min.js') });
      const accessibility = await page.evaluate(async () => {
        const result = await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] } });
        return result.violations.map(item => ({ id: item.id, impact: item.impact, description: item.description, nodes: item.nodes.map(node => ({ target: node.target, summary: node.failureSummary })) }));
      });
      const folder = resolve(output, locale);
      await mkdir(folder, { recursive: true });
      const screenshot = resolve(folder, `${width}.png`);
      await page.screenshot({ path: screenshot, fullPage: true, animations: 'disabled' });
      results.push({ locale, width, direction, title, layout, mixedScriptLayout, editLayout, imageLoaded, accessibility, errors, screenshot: relative(root, screenshot).replaceAll('\\', '/') });
      await page.close();
    }
  }
  const expectedDirection = locale => locale === 'en-US' ? 'ltr' : 'rtl';
  const failures = results.filter(item => item.direction !== expectedDirection(item.locale) || !item.title || item.layout.document > item.width || item.mixedScriptLayout.document > item.width || item.editLayout.document > item.width || !item.imageLoaded || item.accessibility.length || item.errors.length);
  const report = { generatedAt: new Date().toISOString(), browser: 'Installed Google Chrome, headless', cases: results.length, failures, results };
  await mkdir(output, { recursive: true });
  await writeFile(resolve(output, 'report.json'), JSON.stringify(report, null, 2));
  if (failures.length) process.exitCode = 1;
  console.log(JSON.stringify({ cases: results.length, failures: failures.length, output }, null, 2));
} finally {
  if (browser) await browser.close();
  server.kill();
}
