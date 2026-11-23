// Local production-build check for the repaired auth, progress and sharing
// surfaces. Screenshots are optional and must be written outside the repo.
import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const outputDir = process.env.RAHGARD_PRIVATE_EVIDENCE_DIR ? resolve(process.env.RAHGARD_PRIVATE_EVIDENCE_DIR) : null;
if (outputDir && (outputDir === root || outputDir.startsWith(`${root}/`) || outputDir.startsWith(`${root}\\`))) {
  throw new Error('Screenshots must be stored outside the Git checkout.');
}
const vite = resolve(root, 'frontend/node_modules/vite/bin/vite.js');
const axe = resolve(root, 'frontend/node_modules/axe-core/axe.min.js');
const server = spawn(process.execPath, [vite, 'preview', '--host', '127.0.0.1', '--port', '4183', '--strictPort'],
  { cwd: resolve(root, 'frontend'), stdio: 'ignore' });
let browser;
const cases = [];
const contrastRatio = (foreground, background) => {
  const channel = value => {
    const c = value / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  const rgb = value => value.match(/[\d.]+/g).slice(0, 3).map(Number);
  const lum = color => { const [r,g,b] = rgb(color).map(channel); return 0.2126*r + 0.7152*g + 0.0722*b; };
  const a = lum(foreground), b = lum(background);
  return (Math.max(a,b) + 0.05) / (Math.min(a,b) + 0.05);
};

try {
  let ready = false;
  for (let i = 0; i < 40; i += 1) {
    try { ready = (await fetch('http://127.0.0.1:4183/')).ok; } catch {}
    if (ready) break;
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  if (!ready) throw new Error('Production preview did not start.');
  browser = await chromium.launch({ executablePath: process.env.E2E_CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
  for (const theme of ['light', 'dark']) {
    for (const width of [390, 1440]) {
      const page = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: 1 });
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await page.goto('http://127.0.0.1:4183/', { waitUntil: 'networkidle' });
      await page.locator('html').evaluate((html, value) => html.setAttribute('data-rahgard-theme', value), theme);
      await page.locator('#root').evaluate(rootNode => {
        const fixture = document.createElement('main');
        fixture.className = 'unified-trip-experience';
        fixture.innerHTML = `
          <section class="auth-panel" aria-labelledby="contrast-auth-title">
            <h2 id="contrast-auth-title">Sign in to Rahgard</h2>
            <p>Use your private account to continue planning.</p>
            <label for="contrast-email">Email</label><input id="contrast-email" placeholder="you@example.com" />
            <div class="auth-mode-switch"><button type="button" aria-pressed="true">Sign in</button></div>
            <button class="auth-back" type="button">Back</button>
            <p role="alert">The sign-in request could not be completed.</p>
          </section>
          <section class="company-request-sharing"><h3>Optional sharing with tourism companies</h3><p>Only selected verified organizations can see a request after consent.</p></section>
          <section class="rahgard-progress" aria-label="Trip progress">
            <div class="rahgard-progress-header"><div><h3>Plan your trip</h3><p>Review the requirements before making a plan.</p><p class="rahgard-progress-next">Next: confirm trip details</p></div></div>
            <span class="rahgard-progress-count">1 of 3</span>
            <ol class="rahgard-progress-steps"><li class="is-complete">Request</li><li class="is-current">Review</li><li>Itinerary</li></ol>
          </section>`;
        rootNode.prepend(fixture);
      });
      await page.addScriptTag({ path: axe });
      const measured = await page.evaluate(async () => {
        const color = node => {
          const s = getComputedStyle(node);
          let backgrounds = [];
          for (let parent = node; parent; parent = parent.parentElement) {
            const style = getComputedStyle(parent);
            if (style.backgroundImage.includes('gradient')) {
              backgrounds = style.backgroundImage.match(/rgba?\([^)]*\)/g) ?? [];
              if (backgrounds.length) break;
            }
            if (style.backgroundColor !== 'transparent' && style.backgroundColor !== 'rgba(0, 0, 0, 0)') {
              backgrounds = [style.backgroundColor];
              break;
            }
          }
          return { text: s.color, backgrounds, fontSize: parseFloat(s.fontSize), weight: Number(s.fontWeight) || 400 };
        };
        const panel = document.querySelector('.auth-panel');
        const progress = document.querySelector('.rahgard-progress');
        const share = document.querySelector('.company-request-sharing');
        const input = document.querySelector('#contrast-email');
        return {
          authHeading: color(panel.querySelector('h2')),
          authBody: color(panel.querySelector('p')),
          authLabel: color(panel.querySelector('label')),
          authInput: color(input),
          authPlaceholder: { text: getComputedStyle(input, '::placeholder').color, backgrounds: [getComputedStyle(input).backgroundColor] },
          authButton: color(panel.querySelector('.auth-mode-switch button')),
          authError: color(panel.querySelector('[role=alert]')),
          progressHeading: color(progress.querySelector('h3')),
          progressBody: color(progress.querySelector('.rahgard-progress-next')),
          progressSteps: [...progress.querySelectorAll('li')].map(color),
          sharingHeading: color(share.querySelector('h3')),
          overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
          axe: (await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa'] } })).violations.map(v => ({ id: v.id, impact: v.impact, targets: v.nodes.map(n => n.target) })),
        };
      });
      const checks = [];
      const addCheck = (name, foreground, background, minimum) => {
        const backgrounds = Array.isArray(background) ? background : [background];
        const ratios = backgrounds.map(item => contrastRatio(foreground, item));
        const ratio = Math.min(...ratios);
        checks.push({ name, foreground, backgrounds, ratio: Number(ratio.toFixed(2)), minimum, pass: ratio >= minimum });
      };
      for (const key of ['authHeading','authBody','authLabel','authInput','authPlaceholder','authError','progressHeading','progressBody','sharingHeading']) {
        const item = measured[key];
        addCheck(`${key}.text`, item.text, item.backgrounds, item.fontSize >= 24 && item.weight >= 700 ? 3 : 4.5);
      }
      addCheck('authButton.text', measured.authButton.text, measured.authButton.backgrounds, 4.5);
      measured.progressSteps.forEach((item, index) => addCheck(`progressStep${index}.text`, item.text, item.backgrounds, 4.5));
      const caseResult = { theme, width, checks, overflow: measured.overflow, axeViolations: measured.axe };
      if (outputDir) {
        await mkdir(outputDir, { recursive: true });
        const screenshot = resolve(outputDir, `issue24-contrast-${theme}-${width}.png`);
        await page.screenshot({ path: screenshot, fullPage: true, animations: 'disabled' });
        caseResult.screenshot = screenshot;
      }
      cases.push(caseResult);
      await page.close();
    }
  }
  const failures = cases.flatMap(item => [
    ...item.checks.filter(check => !check.pass).map(check => `${item.theme}/${item.width}:${check.name}=${check.ratio}`),
    ...(item.overflow ? [`${item.theme}/${item.width}:horizontal_overflow`] : []),
    ...item.axeViolations.map(v => `${item.theme}/${item.width}:axe:${v.id}`),
  ]);
  process.stdout.write(`${JSON.stringify({ status: failures.length ? 'FAIL' : 'PASS', cases: cases.length, failures, results: cases })}\n`);
  if (failures.length) process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  server.kill();
}
