import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { relative, resolve } from 'node:path';

const root = resolve(import.meta.dirname, '../..');
const output = resolve(root, 'artifacts/visual-qa');
const executablePath = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const vite = resolve(root, 'frontend/node_modules/vite/bin/vite.js');
const server = spawn(process.execPath, [vite, 'preview', '--host', '127.0.0.1', '--port', '4179', '--strictPort'], { cwd: resolve(root, 'frontend'), stdio: 'ignore' });
const locales = ['fa-IR', 'en-US', 'ar'];
const widths = [360, 390, 430, 768, 1024, 1440];
const prompts = {
  'fa-IR': 'برای یک سفر سه روز در شیراز با ریتمی آرام برنامه می‌خواهم.',
  'en-US': 'I would like three days in Shiraz, at a quiet pace.',
  ar: 'أرغب في رحلة ثلاثة أيام في شيراز بإيقاع هادئ.',
};
const mixedScript = 'Shiraz شیراز شيراز القاهرة Cairo · Latin فارسی العربية ';
const results = [];
let browser;
let offlineCheck;

try {
  let ready = false;
  for (let i = 0; i < 60; i++) {
    try { ready = (await fetch('http://127.0.0.1:4179')).ok; } catch {}
    if (ready) break;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  if (!ready) throw new Error('Vite preview did not start on 127.0.0.1:4179; run npm run build first.');
  browser = await chromium.launch({ executablePath, headless: true });

  for (const locale of locales) {
    for (const width of widths) {
      const page = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: 1 });
      await page.emulateMedia({ reducedMotion: 'reduce' });
      const errors = [];
      const externalRequests = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('request', request => {
        if (new URL(request.url()).origin !== 'http://127.0.0.1:4179') externalRequests.push(request.url());
      });
      await page.goto('http://127.0.0.1:4179', { waitUntil: 'networkidle' });
      await page.locator('#locale').selectOption(locale);
      await page.waitForFunction(expected => document.documentElement.lang === expected, locale);
      await page.evaluate(async () => {
        await document.fonts.load('400 16px "Estedad Variable"', 'Latin text');
        await document.fonts.load('400 16px "Estedad Variable"', 'فارسی العربية');
        await document.fonts.ready;
        for (const image of Array.from(document.images)) { image.loading = 'eager'; await image.decode(); }
      });

      const direction = await page.locator('html').getAttribute('dir');
      const title = await page.title();
      const fontStatus = await page.evaluate(() => ({
        loaded: document.fonts.check('400 16px "Estedad Variable"'),
        resources: performance.getEntriesByType('resource').map(entry => entry.name).filter(name => name.includes('/fonts/estedad-')),
      }));
      const imageStatus = await page.evaluate(() => Array.from(document.images).map(image => ({
        loaded: image.complete && image.naturalWidth > 0,
        local: new URL(image.currentSrc).origin === location.origin,
        format: image.currentSrc.split('.').at(-1),
      })));

      const promptField = page.locator('#trip-prompt');
      await promptField.focus();
      await promptField.pressSequentially(prompts[locale]);
      const promptInputLength = [...(await promptField.inputValue()).trim()].length;
      await page.locator('.trip-form button[type="submit"]').click();
      const clarificationCount = await page.locator('.trip-response li').count();
      await page.locator('#trip-destination').fill('Shiraz شیراز شيراز القاهرة Cairo');
      await page.locator('.trip-form button[type="submit"]').click();
      const intakeReady = await page.locator('#captured-title').count() === 1;
      const intakeSummary = intakeReady ? await page.locator('.trip-summary').innerText() : '';
      await page.locator('.text-button').click();
      await page.locator('.trip-form button[type="submit"]').click();
      const validationVisible = await page.locator('#form-error[role="alert"]').count() === 1;
      await page.locator('.text-button').count().then(async count => { if (count) await page.locator('.text-button').click(); });

      await page.locator('#trip-prompt').fill(prompts[locale]);
      await page.locator('#trip-destination').fill(mixedScript.repeat(2));
      await page.locator('#trip-duration').selectOption('1');
      await page.locator('.trip-form button[type="submit"]').click();
      const mixedDestinationLayout = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
      await page.locator('.text-button').click();

      await page.locator('#trip-prompt').fill(mixedScript.repeat(10));
      const mixedScriptLayout = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
      await page.locator('#trip-prompt').fill('');
      const editButton = page.locator('.itinerary .outline');
      await editButton.click();
      const itineraryInputs = page.locator('.itinerary-input');
      await itineraryInputs.first().fill(mixedScript.repeat(4));
      const editLayout = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
      await itineraryInputs.first().fill('');
      await editButton.click();

      await page.locator('body').click({ position: { x: 5, y: 5 } });
      await page.keyboard.press('Tab');
      const keyboardFocus = await page.evaluate(() => {
        const active = document.activeElement;
        const style = active ? getComputedStyle(active) : null;
        return Boolean(active && style && style.outlineStyle !== 'none' && style.outlineWidth !== '0px');
      });
      const reducedMotion = await page.evaluate(() => ({
        preference: matchMedia('(prefers-reduced-motion: reduce)').matches,
        transition: getComputedStyle(document.querySelector('.primary')).transitionDuration,
      }));
      await page.addScriptTag({ path: resolve(root, 'frontend/node_modules/axe-core/axe.min.js') });
      const accessibility = await page.evaluate(async () => {
        const result = await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] } });
        return result.violations.map(item => ({ id: item.id, impact: item.impact, nodes: item.nodes.map(node => ({ target: node.target, failure: node.failureSummary })) }));
      });

      if (locale === 'fa-IR' && width === 360) {
        await page.waitForFunction(() => Boolean(navigator.serviceWorker?.controller));
        await page.reload({ waitUntil: 'networkidle' });
        await page.context().setOffline(true);
        await page.reload({ waitUntil: 'networkidle' });
        offlineCheck = await page.evaluate(async () => ({
          controlled: Boolean(navigator.serviceWorker?.controller),
          shell: document.querySelector('#root')?.children.length > 0,
          imageCached: (await fetch('/images/naghshe-jahan-640.webp')).ok,
          fontCached: (await fetch('/fonts/estedad-latin-variable.woff2')).ok,
        }));
        await page.context().setOffline(false);
        await page.reload({ waitUntil: 'networkidle' });
        await page.locator('#locale').selectOption(locale);
      }

      await page.evaluate(() => document.activeElement instanceof HTMLElement && document.activeElement.blur());
      await mkdir(resolve(output, locale), { recursive: true });
      await page.screenshot({ path: resolve(output, locale, `${width}.png`), fullPage: true, animations: 'disabled' });
      results.push({ locale, width, direction, title, fontStatus, imageStatus, promptInputLength, clarificationCount, intakeReady, intakeSummary, validationVisible,
        mixedDestinationLayout, mixedScriptLayout, editLayout, keyboardFocus, reducedMotion, accessibility, externalRequests, errors,
        screenshot: relative(root, resolve(output, locale, `${width}.png`)).replaceAll('\\', '/') });
      await page.close();
    }
  }

  const expectedDirection = locale => locale === 'en-US' ? 'ltr' : 'rtl';
  const failures = results.filter(item => item.direction !== expectedDirection(item.locale) || !item.title ||
    item.mixedDestinationLayout.document > item.width || item.mixedScriptLayout.document > item.width || item.editLayout.document > item.width ||
    !item.fontStatus.loaded || item.fontStatus.resources.length < 2 || item.imageStatus.some(image => !image.loaded || !image.local) ||
    item.promptInputLength < 5 || item.clarificationCount !== 1 || !item.intakeReady || !item.validationVisible || !item.keyboardFocus ||
    !item.reducedMotion.preference || item.reducedMotion.transition !== '1e-05s' || item.accessibility.length ||
    item.externalRequests.length || item.errors.length);
  const report = { generatedAt: new Date().toISOString(), browser: 'Installed Google Chrome, headless', cases: results.length,
    offlineCheck, failures, results };
  await mkdir(output, { recursive: true });
  await writeFile(resolve(output, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ cases: results.length, failures: failures.length, offlineCheck, output }, null, 2));
  if (failures.length || !offlineCheck?.controlled || !offlineCheck?.shell || !offlineCheck?.imageCached || !offlineCheck?.fontCached) process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  server.kill();
}
