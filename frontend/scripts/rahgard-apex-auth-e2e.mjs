// Only called with a Docker ID created by the guarded VPS restore rehearsal.
import { execFileSync, spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { chromium } from 'playwright-core';

const payload = JSON.parse((await Array.fromAsync(process.stdin)).join(''));
if (!/^[0-9a-f]{64}$/.test(payload.container) || !['invite', 'signup'].includes(payload.mode)) {
  throw new Error('Invalid isolated apex browser identity');
}
const [fixtureName, label, network] = execFileSync('docker', ['inspect', '-f',
  '{{.Name}}|{{index .Config.Labels "rahgard.apex.auth-test"}}|{{.HostConfig.NetworkMode}}',
  payload.container], { encoding: 'utf8', windowsHide: true }).trim().split('|');
if (!/^[0-9a-f]{12}$/.test(label) || fixtureName !== `/rahgard-apex-${payload.mode}-${label}`
    || !/^container:[0-9a-f]{64}$/.test(network)) throw new Error('Invalid isolated apex browser container');
const targetNetwork = execFileSync('docker', ['inspect', '-f',
  '{{.Name}}|{{.HostConfig.NetworkMode}}', network.slice('container:'.length)],
  { encoding: 'utf8', windowsHide: true }).trim();
if (!/^\/rahgard-v2-restore-[0-9a-f]{20}\|none$/.test(targetNetwork)) {
  throw new Error('Apex browser target must be a networkless restored database fixture');
}

const pump = `
import os, socket, sys, threading
conn = socket.create_connection(('127.0.0.1', 443), timeout=10)
conn.settimeout(35)
def upload():
    try:
        while block := os.read(0, 32768):
            conn.sendall(block)
    except OSError:
        pass
    finally:
        try: conn.shutdown(socket.SHUT_WR)
        except OSError: pass
threading.Thread(target=upload, daemon=True).start()
with conn:
    while block := conn.recv(32768):
        sys.stdout.buffer.write(block)
        sys.stdout.buffer.flush()
`;
const sockets = new Set();
const children = new Set();
const proxy = createServer(socket => {
  sockets.add(socket);
  socket.on('close', () => sockets.delete(socket));
  socket.on('error', () => {});
  socket.setTimeout(40_000, () => socket.destroy());
  let header = Buffer.alloc(0);
  const connect = chunk => {
    header = Buffer.concat([header, chunk]);
    if (header.length > 4096) return socket.destroy();
    const end = header.indexOf('\r\n\r\n');
    if (end === -1) return;
    socket.off('data', connect);
    if (!/^CONNECT hinaa\.ir:443 HTTP\/1\.[01]\r\n/.test(header.toString('latin1'))) {
      return socket.end('HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n');
    }
    socket.pause();
    const relay = spawn('docker', ['exec', '-i', payload.container, 'python', '-I', '-c', pump],
      { stdio: ['pipe', 'pipe', 'ignore'], windowsHide: true });
    children.add(relay);
    relay.once('close', () => { children.delete(relay); socket.destroy(); });
    relay.on('error', () => socket.destroy());
    relay.stdin.on('error', () => socket.destroy());
    socket.on('close', () => relay.stdin.end());
    socket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
    const remainder = header.subarray(end + 4);
    if (remainder.length) relay.stdin.write(remainder);
    relay.stdout.pipe(socket);
    socket.pipe(relay.stdin);
    socket.resume();
  };
  socket.on('data', connect);
});

const origin = 'https://hinaa.ir';
let browser;
let phase = 'proxy';
try {
  await new Promise((resolve, reject) => {
    proxy.once('error', reject);
    proxy.listen(0, '127.0.0.1', resolve);
  });
  browser = await chromium.launch({
    executablePath: process.env.E2E_CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    proxy: { server: `http://127.0.0.1:${proxy.address().port}` },
    args: ['--disable-background-networking', '--disable-quic', '--host-resolver-rules=MAP hinaa.ir ~NOTFOUND'],
  });
  phase = 'page';
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
  const page = await context.newPage();
  page.setDefaultTimeout(15_000);
  let registrations = 0;
  page.on('request', request => {
    if (request.method() === 'POST' && new URL(request.url()).pathname.endsWith('/staging/register')) registrations++;
  });
  const initial = await page.goto(origin, { waitUntil: 'domcontentloaded' });
  if (initial?.status() !== 200 || page.url() !== origin + '/') throw new Error('apex_root_status');
  await page.locator('#locale').selectOption('en-US');
  await page.locator('.auth-entry > button').first().click();
  phase = 'auth_form';
  const signup = page.getByRole('button', { name: 'Create a pilot email account', exact: true });
  const submit = async endpoint => {
    const response = page.waitForResponse(r => r.url() === origin + '/api/v1/auth/staging/' + endpoint
      && r.request().method() === 'POST');
    await page.locator('.auth-panel form button[type="submit"]').click();
    if ((await response).status() !== 200) throw new Error('auth_response_status');
    await page.locator('.auth-signed-in').waitFor();
  };
  if (payload.mode === 'invite') {
    await page.locator('#auth-stage-email').waitFor();
    if (await signup.count()) throw new Error('registration_visible_with_flag_off');
    await page.locator('#auth-stage-email').fill(payload.email);
    await page.locator('#auth-stage-password').fill(payload.password);
    await submit('login');
  } else {
    await signup.click();
    await page.locator('#auth-stage-email').fill(payload.email);
    for (const length of [7, 257]) {
      await page.locator('#auth-stage-password').fill('🌿'.repeat(length));
      await page.locator('.auth-panel form button[type="submit"]').click();
      await page.getByText('Use between 8 and 256 characters for a new password.', { exact: true }).waitFor();
      if (registrations !== 0) throw new Error('out_of_bounds_password_submitted');
    }
    await page.locator('#auth-stage-password').fill('🌿'.repeat(256));
    await submit('register');
    if (registrations !== 1) throw new Error('duplicate_or_missing_registration');
  }
  const cookies = await context.cookies(origin);
  phase = 'cookie_and_reload';
  const cookie = cookies.find(item => item.name === '__Host-rahgard_session');
  if (!cookie?.secure || !cookie.httpOnly || cookie.domain !== 'hinaa.ir' || cookie.path !== '/') {
    throw new Error('secure_cookie_shape');
  }
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('.auth-signed-in').waitFor();
  const manifest = await page.evaluate(async () => {
    const result = await fetch('/manifest.webmanifest');
    return { status: result.status, start: (await result.json()).start_url };
  });
  if (manifest.status !== 200 || new URL(manifest.start, origin + '/').href !== origin + '/') {
    throw new Error('wrong_manifest_start');
  }
  await context.close();
  process.stdout.write(JSON.stringify({ mode: payload.mode, chromium: browser.version(), origin,
    signedInAfterReload: true, secureHostCookie: true, manifestRoot: true,
    unicodeBoundaries: payload.mode === 'signup' ? { '7': 'client_rejected', '256': 'registered', '257': 'client_rejected' } : null,
  }) + '\n');
} catch {
  // Never log Playwright request content, cookies or fixture passwords.
  process.stderr.write(`Exact apex Chromium fixture failed in ${phase}.\n`);
  process.exitCode = 1;
} finally {
  await browser?.close();
  for (const socket of sockets) socket.destroy();
  for (const child of children) child.kill();
  proxy.close();
}
