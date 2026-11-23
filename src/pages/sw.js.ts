import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import type { APIRoute } from 'astro';
import { withBase } from '../lib/url';

export const GET: APIRoute = () => {
  const indexRaw = fs.readFileSync(path.resolve(process.cwd(), 'data/index.json'));
  const dataHash = crypto.createHash('sha256').update(indexRaw).digest('hex').slice(0, 8);
  const sha = (process.env.GITHUB_SHA || 'dev').slice(0, 7);
  const version = `${dataHash}-${sha}`;
  const base = withBase('');

  const code = `const VERSION = ${JSON.stringify(version)};
const BASE = ${JSON.stringify(base)};
const SHELL_CACHE = 'vr-shell-' + VERSION;
const PAGES_CACHE = 'vr-pages-' + VERSION;
const PAGEFIND_CACHE = 'vr-pagefind-' + VERSION;
const SHELL_URLS = [
  BASE,
  BASE + 'offline/',
  BASE + 'search/',
  BASE + 'sources/',
  BASE + 'icon.svg',
  BASE + 'manifest.webmanifest'
];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(SHELL_CACHE);
    const assetUrls = new Set();
    for (const url of SHELL_URLS) {
      try {
        const res = await fetch(url, { credentials: 'same-origin' });
        if (res.ok) {
          await cache.put(url, res.clone());
          const ct = res.headers.get('content-type') || '';
          if (ct.includes('text/html')) {
            const html = await res.text();
            const re = /(?:href|src)=["']([^"']*\\/_astro\\/[^"']+\\.(?:css|js|woff2))["']/g;
            let m;
            while ((m = re.exec(html)) !== null) {
              assetUrls.add(m[1]);
            }
          }
        }
      } catch {}
    }
    for (const asset of assetUrls) {
      try {
        const res = await fetch(asset, { credentials: 'same-origin' });
        if (res.ok) {
          await cache.put(asset, res.clone());
          if (asset.endsWith('.css')) {
            const css = await res.text();
            const fontRe = /url\\(([^)]+\\.woff2)\\)/g;
            let fm;
            while ((fm = fontRe.exec(css)) !== null) {
              const fUrl = fm[1].replace(/["']/g, '');
              if (fUrl.includes('latin') || fUrl.includes('devanagari')) {
                try {
                  const fr = await fetch(fUrl, { credentials: 'same-origin' });
                  if (fr.ok) await cache.put(fUrl, fr);
                } catch {}
              }
            }
          }
        }
      } catch {}
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(
      keys.map((key) => {
        if (key.startsWith('vr-kanda-')) return Promise.resolve();
        if (key !== SHELL_CACHE && key !== PAGES_CACHE && key !== PAGEFIND_CACHE) {
          return caches.delete(key);
        }
        return Promise.resolve();
      })
    );
    await self.clients.claim();
  })());
});

async function networkWithTimeout(request, ms) {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), ms);
  try {
    return await fetch(request, { signal: ctrl.signal });
  } finally {
    clearTimeout(id);
  }
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || !url.pathname.startsWith(BASE)) return;

  if (req.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        const net = await networkWithTimeout(req, 3000);
        if (net && net.ok) {
          const cache = await caches.open(PAGES_CACHE);
          cache.put(req, net.clone());
        }
        return net;
      } catch {
        const cached = await caches.match(req, { ignoreSearch: true });
        if (cached) return cached;
        const offline = await caches.match(BASE + 'offline/');
        return offline || new Response('Offline', { status: 503, headers: { 'Content-Type': 'text/plain' } });
      }
    })());
    return;
  }

  if (url.pathname.includes('/_astro/') || url.pathname.endsWith('.woff2') || url.pathname.endsWith('/icon.svg')) {
    event.respondWith((async () => {
      const cached = await caches.match(req);
      if (cached) return cached;
      const net = await fetch(req);
      if (net && net.ok) {
        const cache = await caches.open(SHELL_CACHE);
        cache.put(req, net.clone());
      }
      return net;
    })());
    return;
  }

  if (url.pathname.includes('/pagefind/')) {
    event.respondWith((async () => {
      const cache = await caches.open(PAGEFIND_CACHE);
      const cached = await cache.match(req);
      const fetchPromise = fetch(req).then((net) => {
        if (net && net.ok) cache.put(req, net.clone());
        return net;
      }).catch(() => cached);
      return cached || fetchPromise;
    })());
  }
});
`;

  return new Response(code, {
    headers: { 'Content-Type': 'application/javascript; charset=utf-8' },
  });
};
