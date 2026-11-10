// Vite emits content-hashed JS/CSS. A production PWA must precache those
// exact files: caching only index.html yields a blank offline launch.
import { createHash } from 'node:crypto';
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptPath = fileURLToPath(import.meta.url);
const defaultRoot = resolve(dirname(scriptPath), '..');

function listFiles(folder) {
  const paths = [];
  const visit = dir => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) visit(path);
      else if (entry.isFile()) paths.push(path);
    }
  };
  visit(folder);
  return paths.sort();
}

export function injectPwaAssets(root = defaultRoot) {
  const publicWorker = readFileSync(join(root, 'public', 'sw.js'), 'utf8');
  const out = join(root, 'dist');
  const index = readFileSync(join(out, 'index.html'), 'utf8');
  const files = listFiles(out).filter(file => relative(out, file).replaceAll(sep, '/') !== 'sw.js');
  const names = files.map(file => relative(out, file).split(sep).join('/'));
  const jsCss = names.filter(name => /^assets\/[A-Za-z0-9._/-]+\.(?:js|css)$/.test(name));
  if (!jsCss.some(name => name.endsWith('.js')) || !jsCss.some(name => name.endsWith('.css'))) {
    throw new Error('PWA build requires compiled JS and CSS assets');
  }
  const buildAssets = jsCss.map(name => '/' + name);
  const referenced = [...index.matchAll(/(?:src|href)="(\/assets\/[^"]+\.(?:js|css))"/g)].map(match => match[1]);
  if (!referenced.some(name => name.endsWith('.js')) ||
      !referenced.every(name => buildAssets.includes(name))) {
    throw new Error('PWA index references missing hashed JS/CSS');
  }
  if (publicWorker.split('__RAHGARD_BUILD_ID__').length !== 2 ||
      publicWorker.split('/* __RAHGARD_BUILD_ASSETS__ */ []').length !== 2) {
    throw new Error('PWA service-worker injection markers are missing or duplicated');
  }

  // A change to any deployed static file (including un-hashed icons/images)
  // changes sw.js bytes, prompting a new install and clean cache rotation.
  const hash = createHash('sha256').update(publicWorker);
  for (const [i, file] of files.entries()) {
    hash.update(names[i]);
    hash.update(readFileSync(file));
  }
  const version = hash.digest('hex').slice(0, 16);
  const worker = publicWorker
    .replace('__RAHGARD_BUILD_ID__', version)
    .replace('/* __RAHGARD_BUILD_ASSETS__ */ []', JSON.stringify(buildAssets));
  writeFileSync(join(out, 'sw.js'), worker, 'utf8');
  return { cache: 'rahgard-shell-' + version, assets: buildAssets };
}

if (process.argv[1] && resolve(process.argv[1]) === scriptPath) {
  const result = injectPwaAssets();
  process.stdout.write('[pwa] ' + result.cache + ': cached ' + result.assets.length + ' compiled JS/CSS assets\n');
}
