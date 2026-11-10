// Real Chromium smoke for the production-built, installable offline shell.
// No backend, database, paid provider or SMS calls are necessary.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';
import { chromium } from 'playwright-core';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const port = Number(process.env.PWA_E2E_PORT || '4186');
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Invalid PWA_E2E_PORT');
const origin = 'http://127.0.0.1:' + port;
const executablePath = process.env.PWA_E2E_CHROME_PATH || process.env.E2E_CHROME_PATH ||
  'C:/Program Files/Google/Chrome/Application/chrome.exe';
const viteCli = join(root, 'node_modules', 'vite', 'bin', 'vite.js');

if (!existsSync(join(root, 'dist', 'sw.js')) || !existsSync(viteCli)) {
  throw new Error('Run npm install and npm run build before the PWA offline browser check');
}
if (!existsSync(executablePath)) {
  throw new Error('Chrome not found; set PWA_E2E_CHROME_PATH to the Chrome executable');
}

const server = spawn(process.execPath,
  [viteCli, 'preview', '--host', '127.0.0.1', '--port', String(port), '--strictPort'],
  { cwd: root, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
let startupErrors = '';
server.stderr.on('data', chunk => {
  startupErrors = (startupErrors + String(chunk)).slice(-3000);
});
server.stdout.resume();
let exited = false;
server.on('exit', () => { exited = true; });
let browser;

async function serverReady() {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    if (exited) throw new Error('Vite preview exited: ' + startupErrors);
    try {
      const response = await fetch(origin, { signal: AbortSignal.timeout(1000) });
      if (response.ok) return;
    } catch { /* Still starting. */ }
    await delay(250);
  }
  throw new Error('Vite preview did not start: ' + startupErrors);
}

try {
  await serverReady();
  browser = await chromium.launch({ executablePath, headless: true });
  const context = await browser.newContext({ serviceWorkers: 'allow' });
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto(origin, { waitUntil: 'domcontentloaded' });
  await page.locator('.traveler-workspace').waitFor({ state: 'visible' });
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.waitForFunction(() => navigator.serviceWorker.controller !== null, null, { timeout: 30_000 });

  const preflight = await page.evaluate(async () => {
    const names = (await caches.keys()).filter(name => name.startsWith('rahgard-shell-'));
    if (names.length !== 1) return { names, urls: [] };
    const cache = await caches.open(names[0]);
    return { names, urls: (await cache.keys()).map(request => new URL(request.url).pathname) };
  });
  assert.equal(preflight.names.length, 1, 'Expected exactly one installed shell cache');
  assert.ok(preflight.urls.includes('/'), 'Offline navigation shell is not cached');
  assert.ok(preflight.urls.some(path => /^\/assets\/.+\.js$/.test(path)), 'JS bundle is not cached');
  assert.ok(preflight.urls.some(path => /^\/assets\/.+\.css$/.test(path)), 'CSS bundle is not cached');
  assert.ok(preflight.urls.every(path => !path.startsWith('/api/')), 'Private API was cached');

  await context.setOffline(true);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('.traveler-workspace').waitFor({ state: 'visible', timeout: 20_000 });
  assert.equal(await page.locator('.hero h1').isVisible(), true, 'Offline app did not hydrate');
  assert.equal(await page.locator('.offline-banner').isVisible(), true, 'Missing offline state');
  assert.deepEqual(pageErrors, [], 'Unexpected browser script error');
  process.stdout.write('PWA_OFFLINE_BROWSER_PASS: offline navigation, React hydration, JS/CSS cache and no private API cache\n');
  await context.close();
} finally {
  if (browser) await browser.close();
  if (!exited) server.kill();
}
