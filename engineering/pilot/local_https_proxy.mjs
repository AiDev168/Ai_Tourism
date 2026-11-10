import fs from 'node:fs';
import http from 'node:http';
import https from 'node:https';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const port = Number(process.env.PILOT_HTTPS_PORT);
const apiPort = Number(process.env.PILOT_API_PORT);
const dist = path.resolve(process.env.PILOT_FRONTEND_DIST || 'frontend/dist');
const pfxPath = process.env.PILOT_TLS_PFX;
const pfxPassword = process.env.PILOT_TLS_PFX_PASSWORD;
if (!Number.isInteger(port) || port < 1024 || port > 65535
  || !Number.isInteger(apiPort) || apiPort < 1024 || apiPort > 65535
  || !pfxPath || !pfxPassword || !fs.existsSync(path.join(dist, 'index.html'))) {
  throw new Error('Local pilot proxy configuration is incomplete');
}

const mime = new Map([
  ['.css', 'text/css; charset=utf-8'], ['.html', 'text/html; charset=utf-8'],
  ['.ico', 'image/x-icon'], ['.js', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'], ['.png', 'image/png'],
  ['.svg', 'image/svg+xml'], ['.webmanifest', 'application/manifest+json'],
  ['.webp', 'image/webp'], ['.woff2', 'font/woff2'],
]);

function proxyApi(req, res) {
  const upstream = http.request({
    hostname: '127.0.0.1', port: apiPort, method: req.method,
    path: req.url, headers: { ...req.headers, host: `127.0.0.1:${apiPort}`, 'x-forwarded-proto': 'https' },
    timeout: 12_000,
  }, (upstreamResponse) => {
    res.writeHead(upstreamResponse.statusCode || 502, upstreamResponse.headers);
    upstreamResponse.pipe(res);
  });
  upstream.on('timeout', () => upstream.destroy(new Error('API timeout')));
  upstream.on('error', () => {
    if (!res.headersSent) res.writeHead(502, { 'content-type': 'application/json', 'cache-control': 'no-store' });
    res.end(JSON.stringify({ error: { code: 'upstream_unavailable' } }));
  });
  req.pipe(upstream);
}

function serveStatic(req, res) {
  const pathname = decodeURIComponent(new URL(req.url || '/', 'https://localhost').pathname);
  const requested = path.resolve(dist, `.${pathname}`);
  if (requested !== dist && !requested.startsWith(`${dist}${path.sep}`)) {
    res.writeHead(404).end();
    return;
  }
  let target = requested;
  try {
    if (!fs.statSync(target).isFile()) target = path.join(dist, 'index.html');
  } catch {
    target = path.join(dist, 'index.html');
  }
  res.writeHead(200, {
    'content-type': mime.get(path.extname(target)) || 'application/octet-stream',
    'x-content-type-options': 'nosniff',
    'x-frame-options': 'DENY',
    'referrer-policy': 'strict-origin-when-cross-origin',
    'cache-control': path.basename(target) === 'index.html' ? 'no-cache' : 'public, max-age=31536000, immutable',
  });
  fs.createReadStream(target).pipe(res);
}

https.createServer({
  pfx: fs.readFileSync(pfxPath),
  passphrase: pfxPassword,
  minVersion: 'TLSv1.2',
}, (req, res) => {
  if (req.url?.startsWith('/api/')) return proxyApi(req, res);
  if (req.url?.startsWith('/health/')) return proxyApi(req, res);
  return serveStatic(req, res);
}).listen(port, '127.0.0.1', () => {
  process.stdout.write(`LOOPBACK_HTTPS_READY:${port}\n`);
});
