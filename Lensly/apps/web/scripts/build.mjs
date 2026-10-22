import { copyFile, mkdir } from 'node:fs/promises';
await mkdir('dist', { recursive: true });
await Promise.all(['index.html', 'style.css', 'boot.js', 'display-check.html', 'display-check.css'].map((name) => copyFile(name, `dist/${name}`)));
