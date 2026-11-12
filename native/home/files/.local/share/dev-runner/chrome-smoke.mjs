import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const output = process.env.DEV_RUNNER_ARTIFACTS;
const baseURL = process.env.PLAYWRIGHT_BASE_URL;
if (!output || !baseURL) throw new Error('Use dev-remote --port PORT chrome');
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome', headless: false, args: ['--ozone-platform=x11', `--class=${process.env.DEV_RUNNER_CHROME_CLASS}`] });
const errors = [];
let context;
let page;
let response;
let failure;
try {
  context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  await context.tracing.start({ screenshots: true, snapshots: true });
  page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  // Dev servers and polling apps need not ever become network-idle.
  response = await page.goto(baseURL, { waitUntil: 'load', timeout: 60000 });
  const ready = process.env.DEV_RUNNER_READY_SELECTOR ||
    'main:visible, [role="main"]:visible, button:visible, a[href]:visible, input:visible';
  await page.locator(ready).first().waitFor({ state: 'visible', timeout: 120000 });
  if (process.env.DEV_RUNNER_EXPECT_ADMIN === '1') {
    const sessionResponse = await context.request.get(new URL('/api/auth/get-session', baseURL).href);
    const session = await sessionResponse.json();
    const user = session?.user;
    await writeFile(path.join(output, 'auth.json'), JSON.stringify({ id: user?.id, role: user?.role }, null, 2));
    if (user?.id !== 'hype-local-agent-admin') {
      throw new Error('Expected Hype local admin session; admin verification failed');
    }
    const adminResponse = await page.goto(new URL('/admin', baseURL).href, { waitUntil: 'load' });
    if (!adminResponse?.ok()) throw new Error('Admin panel returned an unsuccessful response');
    if (!new URL(page.url()).pathname.startsWith('/admin')) throw new Error('Admin panel redirected away');
    await page.locator(ready).first().waitFor({ state: 'visible', timeout: 120000 });
  }
  await page.screenshot({ path: path.join(output, 'desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(output, 'mobile.png'), fullPage: true });
} catch (error) {
  failure = String(error);
  await page?.screenshot({ path: path.join(output, 'failure.png'), timeout: 5000 }).catch(() => {});
} finally {
  const result = { browser: browser.version(), channel: 'chrome', url: page?.url(),
    title: await page?.title().catch(() => ''), status: response?.status(), errors, failure };
  await writeFile(path.join(output, 'smoke.json'), JSON.stringify(result, null, 2));
  await context?.tracing.stop({ path: path.join(output, 'trace.zip') });
  console.log(JSON.stringify(result));
  if (failure || !response?.ok() || errors.length) process.exitCode = 1;
  await browser.close();
}
