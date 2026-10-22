import { mkdir, readFile, writeFile, copyFile } from 'node:fs/promises';

// Only built public assets go into this directory; never .env, data or the guide.
const output = 'dist-vercel';
await mkdir(output, { recursive: true });
const launch = process.argv[2] ? new URL(process.argv[2]) : null;
if (
  launch &&
  (launch.protocol !== 'https:' ||
    launch.username ||
    launch.password ||
    launch.pathname !== '/' ||
    launch.search ||
    launch.hash ||
    launch.hostname.endsWith('.vercel.app'))
) {
  throw Error('Supply an HTTPS backend origin without credentials, path, query or fragment.');
}
let html = (await readFile('dist/index.html', 'utf8')).replace(/\r\n/g, '\n');
if (launch) {
  const safeUrl = launch.origin.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
  // Keep a working browser fallback even if the deployment API omits route config.
  // No app forms or API calls may run on the static Vercel origin.
  html = `<!doctype html><html lang="en"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="mrbd-web-app-capable" content="yes">
    <meta http-equiv="refresh" content="0;url=${safeUrl}/">
    <title>Lensly</title><link rel="stylesheet" href="/style.css"></head>
    <body><main class="app"><h1>Opening Lensly…</h1>
    <p>Keep your laptop and Cloudflare connection running.</p>
    <a href="${safeUrl}/">Open connected app</a></main></body></html>`;
}
if (!launch) {
  html = html.replace(/<script[^>]*src="\/(?:main|boot)\.js"[^>]*><\/script>/g, '');
  html = html.replace('>LOCAL</span>', '>BACKEND OFFLINE</span>');
  html = html.replace('Pair your glasses.', 'Backend offline.');
  html = html.replace(
    'On your laptop, open LensAgent Settings and create a pairing code.',
    'The web interface is online. A connection to your laptop is still needed for chat and pairing.',
  );
  html = html.replace(
    /(<form id="(?:connect|pair)-form"[^>]*>)([\s\S]*?)(<\/form>)/g,
    '$1<fieldset disabled class="stack">$2</fieldset>$3',
  );
  html = html.replace('Loading controls…', 'Connect the laptop backend before pairing.');
}
await writeFile(`${output}/index.html`, html);
await Promise.all(
  ['main.js', 'style.css', 'boot.js', 'display-check.html', 'display-check.css'].map((name) => copyFile(`dist/${name}`, `${output}/${name}`)),
);
const config = {
  ...(launch
    ? {
        redirects: [
          { source: '/', destination: `${launch.origin}/`, permanent: false },
        ],
      }
    : {}),
  headers: [
    {
      source: '/(.*)',
      headers: [
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'Referrer-Policy', value: 'no-referrer' },
        { key: 'Cache-Control', value: 'no-store' },
        {
          key: 'Content-Security-Policy',
          value:
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        },
      ],
    },
  ],
};
await writeFile(`${output}/vercel.json`, JSON.stringify(config, null, 2));
console.log(
  launch
    ? `Prepared temporary redirect to ${launch.origin}`
    : 'Prepared offline interface; no backend connected.',
);
