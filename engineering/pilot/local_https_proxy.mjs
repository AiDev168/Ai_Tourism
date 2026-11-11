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
  // The proxy is loopback-only. Preserve the browser's exact localhost Host
  // authority so same-origin local-owner auth can compare it with Origin, and
  // strip every client-supplied forwarding header: the backend trusts the TCP
  // peer address, not proxy assertions about a remote identity.
  const headers = { ...req.headers };
  for (const name of Object.keys(headers)) {
    const normalized = name.toLowerCase();
    if (normalized === 'forwarded' || normalized.startsWith('x-forwarded-')) delete headers[name];
  }

  // Owner login performs multiple bounded PostgreSQL operations and PBKDF2.
  // On Windows/Docker, several sequential TLS connections can exceed the
  // former generic 12s proxy limit while /health and GET /method remain OK.
  // Keep other routes at 12s. A larger login limit is NOT a substitute for
  // measuring and reducing backend latency once the first pilot is working.
  const ownerLogin = req.method === 'POST'
    && req.url === '/api/v1/auth/local-owner/login';
  const upstreamTimeoutMs = ownerLogin ? 30_000 : 12_000;
  const start = process.hrtime.bigint();
  let timedOut = false;
  const elapsedMs = () => Number((process.hrtime.bigint() - start) / 1_000_000n);

  const upstream = http.request({
    hostname: '127.0.0.1', port: apiPort, method: req.method,
    path: req.url, headers,
    timeout: upstreamTimeoutMs,
  }, (upstreamResponse) => {
    res.writeHead(upstreamResponse.statusCode || 502, upstreamResponse.headers);
    upstreamResponse.pipe(res);
  });
  upstream.on('timeout', () => {
    timedOut = true;
    // This is safe operational metadata; never log raw URL/query, user name,
    // password, request/response body, cookies, or authentication headers.
    console.error('LOCAL_PROXY_UPSTREAM_TIMEOUT route='
      + (ownerLogin ? 'owner_login' : 'other')
      + ' elapsed_ms=' + elapsedMs());
    upstream.destroy(new Error('API timeout'));
  });
  upstream.on('error', (error) => {
    const safeCodes = new Set(['ECONNREFUSED', 'ECONNRESET', 'ETIMEDOUT', 'EPIPE']);
    const code = safeCodes.has(error?.code) ? error.code : 'OTHER';
    console.error('LOCAL_PROXY_UPSTREAM_ERROR route='
      + (ownerLogin ? 'owner_login' : 'other')
      + ' kind=' + (timedOut ? 'timeout' : code)
      + ' elapsed_ms=' + elapsedMs());
    if (!res.headersSent) res.writeHead(timedOut ? 504 : 502, {
      'content-type': 'application/json',
      'cache-control': 'no-store',
    });
    if (!res.writableEnded) res.end(JSON.stringify({ error: { code: 'upstream_unavailable' } }));
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
