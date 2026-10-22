import { chromium } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const env = await readFile(path.join(root, '.env'), 'utf8');
const token = env.match(/^LENSAGENT_API_TOKEN=(.+)$/m)?.[1].trim();
if (!token) throw new Error('No local access token configured');
const proof = JSON.parse(await readFile(path.join(root, 'work/live-local-smoke.json'), 'utf8'));
const browser = await chromium.launch({ channel: 'msedge' });
try {
  const page = await browser.newPage({ viewport: { width: 600, height: 600 } });
  const failures = [];
  page.on('pageerror', (error) => failures.push(error.message));
  await page.goto('http://127.0.0.1:8765');
  await page.evaluate(
    ({ token, id }) => {
      sessionStorage.setItem('lensagent.token', token);
      localStorage.setItem('lensagent.conversation', id);
    },
    { token, id: proof.conversation_id },
  );
  await page.reload();
  await page.locator('#workspace').waitFor();
  const oldTurns = await page.locator('#messages .message').count();
  if (oldTurns < proof.stored_messages)
    throw new Error(
      `Expected at least ${proof.stored_messages} persisted turns after restart, got ${oldTurns}`,
    );
  const oldAnswers = await page.locator('#messages .assistant').count();
  await page.getByRole('button', { name: 'Images', exact: true }).click();
  await page.getByRole('button', { name: /^(Use image|Selected)$/ }).click();
  await page.getByLabel('Your question').fill('Describe this image in one short sentence.');
  await page.getByRole('button', { name: 'Ask →', exact: true }).click();
  await page.waitForFunction(
    (expected) => document.querySelectorAll('#messages .assistant').length === expected,
    oldAnswers + 1,
    { timeout: 100000 },
  );
  const reply = await page.locator('#messages .assistant').last().innerText();
  if (!/red/i.test(reply) || !/blue/i.test(reply))
    throw new Error(`Unexpected live vision result: ${reply}`);
  await page.screenshot({ path: path.join(root, 'work/live-interface.png') });
  await page.getByRole('button', { name: 'Images', exact: true }).click();
  await page.locator('.image-item img').waitFor();
  await page.screenshot({
    path: path.join(root, 'work/live-image-history.png'),
  });
  const result = {
    provider: 'ollama',
    model: proof.model,
    persisted_turns_loaded: oldTurns,
    live_browser_reply: reply,
    browser_errors: failures,
  };
  if (failures.length) throw new Error(JSON.stringify(failures));
  await writeFile(path.join(root, 'work/live-browser-proof.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
} finally {
  await browser.close();
}
