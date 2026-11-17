import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { injectPwaAssets } from './inject-pwa-assets.mjs';

function fixture() {
  const root = mkdtempSync(join(tmpdir(), 'rahgard-pwa-'));
  mkdirSync(join(root, 'public'), { recursive: true });
  mkdirSync(join(root, 'dist', 'assets'), { recursive: true });
  mkdirSync(join(root, 'dist', 'icons'), { recursive: true });
  writeFileSync(join(root, 'public', 'sw.js'),
    "const CACHE = 'rahgard-shell-__RAHGARD_BUILD_ID__';\n" +
    'const BUILD_ASSETS = /* __RAHGARD_BUILD_ASSETS__ */ [];\n');
  writeFileSync(join(root, 'dist', 'index.html'),
    '<script src="/assets/index-abc.js"></script><link href="/assets/index-abc.css" rel="stylesheet">');
  writeFileSync(join(root, 'dist', 'assets', 'index-abc.js'), 'console.log("hello")');
  writeFileSync(join(root, 'dist', 'assets', 'index-abc.css'), 'body{display:block}');
  writeFileSync(join(root, 'dist', 'icons', 'icon.png'), 'icon-v1');
  return root;
}

test('production worker precaches exact hashed JS/CSS and regenerates after a static change', () => {
  const root = fixture();
  try {
    const first = injectPwaAssets(root);
    assert.deepEqual(first.assets, ['/assets/index-abc.css', '/assets/index-abc.js']);
    assert.match(first.cache, /^rahgard-shell-[a-f0-9]{16}$/);
    const compiled = readFileSync(join(root, 'dist', 'sw.js'), 'utf8');
    assert.ok(compiled.includes(JSON.stringify(first.assets)));
    assert.ok(compiled.includes(first.cache));
    assert.ok(!compiled.includes('__RAHGARD_BUILD_ID__'));
    assert.deepEqual(injectPwaAssets(root), first);
    writeFileSync(join(root, 'dist', 'icons', 'icon.png'), 'icon-v2');
    const second = injectPwaAssets(root);
    assert.notEqual(first.cache, second.cache);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('missing JS/CSS and stale referenced bundles cannot produce an installable shell', () => {
  const root = fixture();
  try {
    writeFileSync(join(root, 'dist', 'index.html'),
      '<script src="/assets/removed.js"></script>');
    assert.throws(() => injectPwaAssets(root), /missing hashed JS\/CSS/);
    writeFileSync(join(root, 'dist', 'index.html'), '<title>missing bundle</title>');
    assert.throws(() => injectPwaAssets(root), /missing hashed JS\/CSS/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
