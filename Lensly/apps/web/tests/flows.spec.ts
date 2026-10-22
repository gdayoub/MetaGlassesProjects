import { test, expect, type Page } from '@playwright/test';

const token = 'browser-test-token-only-not-for-deployment';
const pixel = {
  name: 'pixel.png',
  mimeType: 'image/png',
  buffer: Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aP1sAAAAASUVORK5CYII=',
    'base64',
  ),
};
async function connect(page: Page) {
  await page.goto('/');
  await page.getByText('Laptop administrator login', { exact: true }).click();
  await page.getByLabel('Server access token').fill(token);
  await page.getByRole('button', { name: 'Connect', exact: true }).click();
  await expect(page.locator('#workspace')).toBeVisible();
}

test('auth boundary, real provider configuration error, session restoration and disconnect', async ({
  page,
}) => {
  await page.goto('/');
  await page.getByText('Laptop administrator login', { exact: true }).click();
  await page.getByLabel('Server access token').fill('wrong');
  await page.getByRole('button', { name: 'Connect', exact: true }).click();
  await expect(page.locator('#status')).toHaveClass(/error/);
  await connect(page);
  expect(await page.evaluate(() => localStorage.getItem('lensagent.remembered-device'))).toBeNull();
  await page.getByLabel('Your question').fill('What is in this image?');
  await page.getByRole('button', { name: 'Ask →', exact: true }).click();
  await expect(page.locator('#status')).toHaveClass(/error/);
  await expect(page.locator('#status')).toContainText(/Gemini|configured|enabled/i);
  await expect(page.locator('#messages .assistant')).toHaveCount(0);
  await page.reload();
  await expect(page.locator('#workspace')).toBeVisible();
  await page.getByRole('button', { name: 'Settings', exact: true }).click();
  await page.getByRole('button', { name: 'Disconnect this browser' }).click();
  await expect(page.getByLabel('One-time code from Settings')).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('lensagent.token'))).toBeNull();
});

test('composer plus button uploads, previews and sends the selected image through the real API', async ({
  page,
}) => {
  await connect(page);
  await page.getByLabel('Your question').fill('What is in this picture?');
  await page.getByRole('button', { name: 'Add image', exact: true }).click();
  await expect(page.locator('#attachment-menu')).toBeVisible();
  const chooser = page.waitForEvent('filechooser');
  await page.getByRole('button', { name: /Upload image From this device/ }).click();
  await (await chooser).setFiles(pixel);
  await expect(page.locator('#attachment-preview')).toBeVisible();
  await expect(page.locator('#attachment-image')).toBeVisible();
  await expect
    .poll(() =>
      page.locator('#attachment-image').evaluate((img: HTMLImageElement) => img.naturalWidth),
    )
    .toBeGreaterThan(0);
  await expect(page.getByLabel('Your question')).toHaveValue('What is in this picture?');
  const sent = page.waitForRequest(
    (req) => req.url().endsWith('/messages') && req.method() === 'POST',
  );
  await page.getByRole('button', { name: 'Ask →', exact: true }).click();
  const body = (await sent).postDataJSON();
  expect(body.image_id).toMatch(/^[0-9a-f-]{36}$/);
  expect(body.use_recent_image).toBe(false);
  await expect(page.locator('#status')).toContainText(/configured|enabled/i);
  await page.getByRole('button', { name: 'Add image', exact: true }).click();
  await page.getByRole('button', { name: /Saved images In this chat/ }).click();
  await expect(page.locator('.image-item')).toHaveCount(1);
  await page.getByRole('button', { name: 'Selected', exact: true }).click();
  await expect(page.locator('#context-label')).toContainText('Image selected');
  await page.getByRole('button', { name: 'Clear image' }).click();
  await expect(page.locator('#context-label')).toContainText('Text only');
  await expect(page.locator('#attachment-preview')).toBeHidden();
  await page.getByRole('button', { name: 'Images', exact: true }).click();
  await page.getByRole('button', { name: 'Use image', exact: true }).click();
  await expect(page.locator('#context-label')).toContainText('Image selected');
  await page.getByRole('button', { name: 'Images', exact: true }).click();
  await page.getByRole('button', { name: /^Delete image/ }).click();
  await page.getByRole('button', { name: 'Confirm', exact: true }).click();
  await expect(page.locator('.image-item')).toHaveCount(0);
  await page.reload();
  await page.getByRole('button', { name: 'Images', exact: true }).click();
  await expect(page.getByText('No images in this conversation yet.')).toBeVisible();
});

test('upload errors preserve the draft and an in-flight upload blocks sending and switching chats', async ({
  page,
}) => {
  await connect(page);
  await page.getByLabel('Your question').fill('Keep this draft');
  await page.route('**/api/conversations/*/images', async (route) => {
    if (route.request().method() !== 'POST') return route.continue();
    await route.fulfill({
      status: 413,
      contentType: 'application/json',
      body: JSON.stringify({ error: { message: 'Test upload rejected.' } }),
    });
  });
  await page.locator('#image-file').setInputFiles(pixel);
  await expect(page.locator('#status')).toContainText('Test upload rejected.');
  await expect(page.getByLabel('Your question')).toHaveValue('Keep this draft');
  await expect(page.getByRole('button', { name: 'Ask →', exact: true })).toBeEnabled();
  await page.unroute('**/api/conversations/*/images');
  let releaseUpload!: () => void;
  const gate = new Promise<void>((resolve) => {
    releaseUpload = resolve;
  });
  await page.route('**/api/conversations/*/images', async (route) => {
    if (route.request().method() === 'POST') await gate;
    await route.continue();
  });
  try {
    await page.locator('#image-file').setInputFiles(pixel);
    await expect(page.locator('#status')).toHaveText('Uploading image…');
    await expect(page.getByRole('button', { name: 'Ask →', exact: true })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'New conversation' })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'History', exact: true })).toBeDisabled();
  } finally {
    releaseUpload();
  }
  await expect(page.locator('#attachment-image')).toBeVisible();
  await expect(page.getByLabel('Your question')).toHaveValue('Keep this draft');
  await expect(page.getByRole('button', { name: 'Ask →', exact: true })).toBeEnabled();
});

test('remember a paired device across browser sessions, preserve its conversation and revoke access', async ({
  page,
  browser,
}) => {
  await connect(page);
  await expect(page).toHaveTitle('Lensly');
  const wordmark = await page.locator('.brand').boundingBox();
  expect(Math.abs(wordmark!.x + wordmark!.width / 2 - 300)).toBeLessThan(2);
  await expect(page.locator('.topbar')).toHaveText('Lensly');
  await page.getByRole('button', { name: 'Settings', exact: true }).click();
  await page.getByRole('button', { name: 'Create glasses pairing code' }).click();
  await expect(page.locator('#pairing-result')).toContainText('Code:');
  const code = (await page.locator('#pairing-result').innerText()).match(/\d{8}/)![0];
  let device = await browser.newContext();
  let glasses = await device.newPage();
  await glasses.goto('http://127.0.0.1:8766');
  await expect(glasses.getByRole('checkbox', { name: /Remember this device/ })).toBeChecked();
  await glasses.getByLabel('One-time code from Settings').fill(code);
  await glasses.getByRole('button', { name: 'Pair this device' }).click();
  await expect(glasses.locator('#workspace')).toBeVisible();
  await glasses.getByRole('button', { name: 'Settings', exact: true }).click();
  await glasses.getByRole('button', { name: 'Create glasses pairing code' }).click();
  await expect(glasses.locator('#status')).toHaveClass(/error/);
  const conversationId = await glasses.evaluate(() =>
    localStorage.getItem('lensagent.conversation'),
  );
  // storageState carries durable browser data, but deliberately excludes sessionStorage.
  const saved = await device.storageState();
  await device.close();
  device = await browser.newContext({ storageState: saved });
  glasses = await device.newPage();
  await glasses.goto('http://127.0.0.1:8766');
  await expect(glasses.locator('#workspace')).toBeVisible();
  expect(await glasses.evaluate(() => localStorage.getItem('lensagent.conversation'))).toBe(
    conversationId,
  );
  await glasses.getByRole('button', { name: 'Settings', exact: true }).click();
  await expect(glasses.locator('#remembered-status')).toContainText('stays signed in until');
  // Exercise local sign-out from a copy of this profile without another code redemption.
  const forgettable = await browser.newContext({ storageState: saved });
  let signedOut = await forgettable.newPage();
  await signedOut.goto('http://127.0.0.1:8766');
  await signedOut.getByRole('button', { name: 'Settings', exact: true }).click();
  await signedOut.getByRole('button', { name: 'Disconnect this browser' }).click();
  expect(await signedOut.evaluate(() => sessionStorage.getItem('lensagent.token'))).toBeNull();
  expect(
    await signedOut.evaluate(() => localStorage.getItem('lensagent.remembered-device')),
  ).toBeNull();
  await signedOut.close();
  signedOut = await forgettable.newPage();
  await signedOut.goto('http://127.0.0.1:8766');
  await expect(signedOut.locator('#connection')).toHaveText('PAIR DEVICE');
  await forgettable.close();
  await page.getByRole('button', { name: 'Revoke paired devices' }).click();
  await page.getByRole('button', { name: 'Confirm', exact: true }).click();
  await expect(page.locator('#status')).toContainText('revoked');
  await glasses.reload();
  await expect(glasses.getByLabel('One-time code from Settings')).toBeVisible();
  expect(
    await glasses.evaluate(() => localStorage.getItem('lensagent.remembered-device')),
  ).toBeNull();
  expect(await glasses.evaluate(() => sessionStorage.getItem('lensagent.token'))).toBeNull();
  await device.close();
});

test('opting out keeps pairing session-only', async ({ page, browser }) => {
  await connect(page);
  await page.getByRole('button', { name: 'Settings', exact: true }).click();
  const device = await browser.newContext();
  let glasses = await device.newPage();
  const pairingResponse = page.waitForResponse(
    (response) => response.url().endsWith('/api/pairing') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Create glasses pairing code' }).click();
  const { code } = await (await pairingResponse).json();
  await glasses.goto('http://127.0.0.1:8766');
  await glasses.getByRole('checkbox', { name: /Remember this device/ }).uncheck();
  await glasses.getByLabel('One-time code from Settings').fill(code);
  await glasses.getByRole('button', { name: 'Pair this device' }).click();
  await expect(glasses.locator('#workspace')).toBeVisible();
  expect(await glasses.evaluate(() => !!localStorage.getItem('lensagent.remembered-device'))).toBe(
    false,
  );
  await glasses.reload();
  await expect(glasses.locator('#workspace')).toBeVisible();
  await glasses.close();
  glasses = await device.newPage();
  await glasses.goto('http://127.0.0.1:8766');
  await expect(glasses.getByLabel('One-time code from Settings')).toBeVisible();
  await expect(glasses.locator('#connection')).toHaveText('PAIR DEVICE');
  await device.close();
});

for (const record of [
  '{broken',
  JSON.stringify({ token: 'expired-test-credential', expires_at: '2000-01-01T00:00:00Z' }),
]) {
  test(`discard ${record === '{broken' ? 'damaged' : 'expired'} remembered login before making authenticated requests`, async ({
    page,
  }) => {
    let configRequests = 0;
    page.on('request', (request) => {
      if (request.url().endsWith('/api/config')) configRequests += 1;
    });
    await page.addInitScript(
      (value) => localStorage.setItem('lensagent.remembered-device', value),
      record,
    );
    await page.goto('/');
    await expect(page.locator('#startup-status')).toContainText('Ready');
    await expect(page.locator('#connection')).toHaveText('PAIR DEVICE');
    expect(
      await page.evaluate(() => localStorage.getItem('lensagent.remembered-device')),
    ).toBeNull();
    expect(configRequests).toBe(0);
  });
}

test('600px display and phone layout expose composer without horizontal overflow', async ({
  page,
}) => {
  await connect(page);
  await expect(page.getByLabel('Your question')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(600);
  const send = await page.getByRole('button', { name: 'Ask →', exact: true }).boundingBox();
  expect(send!.y + send!.height).toBeLessThanOrEqual(600);
  await page.getByRole('button', { name: 'Add image', exact: true }).click();
  const menu = await page.locator('#attachment-menu').boundingBox();
  expect(menu!.y).toBeGreaterThanOrEqual(0);
  expect(menu!.x + menu!.width).toBeLessThanOrEqual(600);
  await page.keyboard.press('Escape');
  await expect(page.locator('#attachment-menu')).toBeHidden();
  await page.setViewportSize({ width: 375, height: 812 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
  await page.screenshot({
    path: '../../work/phone-interface.png',
    fullPage: true,
  });
});

test('a simulated unknown provider outcome requires explicit approval for a new request ID', async ({
  page,
}) => {
  const ids: string[] = [];
  await page.route('**/api/conversations/*/messages', async (route) => {
    ids.push(route.request().postDataJSON().request_id);
    await route.fulfill({
      status: 504,
      contentType: 'application/json',
      body: JSON.stringify({
        error: {
          code: 'provider_timeout',
          message: 'Explicit test fixture: provider outcome unknown.',
        },
      }),
    });
  });
  await connect(page);
  await page.getByLabel('Your question').fill('Test timeout handling');
  await page.getByRole('button', { name: 'Ask →', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Retry as a new request' })).toBeVisible();
  await page.getByRole('button', { name: 'Ask →', exact: true }).click();
  await expect.poll(() => ids.length).toBe(2);
  expect(ids[0]).toBe(ids[1]);
  await page.getByRole('button', { name: 'Retry as a new request' }).click();
  await expect(page.getByText(/Cloud providers may charge again/)).toBeVisible();
  await page.getByRole('button', { name: 'Confirm', exact: true }).click();
  await expect.poll(() => ids.length).toBe(3);
  expect(ids[2]).not.toBe(ids[0]);
});

test('glasses entry exposes pairing first and remains usable when storage is denied', async ({
  page,
}) => {
  await page.addInitScript(() => {
    for (const name of ['sessionStorage', 'localStorage']) {
      Object.defineProperty(window, name, {
        get() {
          throw new DOMException('Storage denied', 'SecurityError');
        },
      });
    }
  });
  await page.goto('/');
  await expect(page.getByLabel('One-time code from Settings')).toBeFocused();
  await expect(page.locator('#startup-status')).toContainText('Ready');
  const pair = await page.getByRole('button', { name: 'Pair this device' }).boundingBox();
  expect(pair!.y + pair!.height).toBeLessThanOrEqual(600);
  const response = await page.request.post('/api/pairing', {
    headers: { Authorization: `Bearer ${token}`, Origin: 'http://127.0.0.1:8766' },
  });
  expect(response.ok()).toBeTruthy();
  const { code } = await response.json();
  await page.getByLabel('One-time code from Settings').fill(code);
  await page.getByRole('button', { name: 'Pair this device' }).click();
  await expect(page.locator('#workspace')).toBeVisible();
  await expect(page.locator('#status')).toContainText('could not remember your login');
  await expect(page.getByLabel('Your question')).toBeVisible();
});

test('failed main module leaves a readable startup error instead of an endless loader', async ({
  page,
}) => {
  await page.route('**/main.js', (route) => route.abort());
  await page.goto('/');
  await expect(page.locator('#startup-status')).toContainText('Controls did not load', {
    timeout: 20000,
  });
  await expect(page.getByLabel('One-time code from Settings')).toBeVisible();
});
