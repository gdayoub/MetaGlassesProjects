import { chromium, request } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';

const origin = process.argv[2];
if (!origin || new URL(origin).protocol !== 'https:') throw Error('Supply the exact HTTPS origin');
const env = await readFile('../../.env', 'utf8');
const adminToken = env.match(/^LENSAGENT_API_TOKEN=(.+)$/m)?.[1].trim();
if (!adminToken) throw Error('Missing local administrator token');
const admin = await request.newContext({
  baseURL: origin,
  extraHTTPHeaders: { Authorization: `Bearer ${adminToken}`, Origin: origin },
});
const browser = await chromium.launch({ channel: 'msedge' });
let cid;
let deviceId;
try {
  const oldDevicesResponse = await admin.get('/api/devices');
  if (!oldDevicesResponse.ok())
    throw Error(`Admin origin/auth failed: ${oldDevicesResponse.status()}`);
  const pairResponse = await admin.post('/api/pairing');
  if (!pairResponse.ok()) throw Error(`Pair creation failed: ${pairResponse.status()}`);
  const { code } = await pairResponse.json();
  const page = await browser.newPage({ viewport: { width: 600, height: 600 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(origin);
  await page.getByLabel('One-time code from Settings').fill(code);
  const redeemed = page.waitForResponse(
    (r) => r.url() === `${origin}/api/pairing/redeem` && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Pair this device', exact: true }).click();
  const redemption = await redeemed;
  if (!redemption.ok()) throw Error(`Pair redemption failed: ${redemption.status()}`);
  deviceId = (await redemption.json()).device_id;
  await page.locator('#workspace').waitFor({ timeout: 20000 });
  cid = await page.evaluate(() => localStorage.getItem('lensagent.conversation'));
  const start = performance.now();
  await page.getByLabel('Your question').fill('What is 19 plus 23? Answer with the number only.');
  await page.getByRole('button', { name: 'Ask →', exact: true }).click();
  await page.locator('#messages .assistant').waitFor({ timeout: 100000 });
  const answer = await page.locator('#messages .assistant').innerText();
  if (!/\b42\b/.test(answer)) throw Error(`Unexpected answer: ${answer}`);
  await page.screenshot({ path: '../../work/public-paired-proof.png' });
  const proof = {
    origin,
    pairing: 'passed',
    text_answer: answer,
    elapsed_seconds: (performance.now() - start) / 1000,
    browser_errors: errors,
    hardware_verified: false,
  };
  if (errors.length) throw Error('Browser exceptions');
  await writeFile('../../work/public-paired-proof.json', JSON.stringify(proof, null, 2));
  console.log(JSON.stringify(proof, null, 2));
} finally {
  if (cid) await admin.delete(`/api/conversations/${cid}`);
  if (deviceId) await admin.delete(`/api/devices/${deviceId}`);
  await browser.close();
  await admin.dispose();
}
