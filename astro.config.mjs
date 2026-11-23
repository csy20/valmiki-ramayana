import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

function normalizeBase(raw) {
  if (!raw || raw === '/') return '/';
  const clean = raw.replace(/^\/+|\/+$/g, '');
  return clean ? `/${clean}` : '/';
}

export default defineConfig({
  output: 'static',
  site: process.env.SITE_URL ?? 'https://csy20.github.io',
  base: normalizeBase(process.env.BASE_PATH ?? '/valmiki-ramayana'),
  trailingSlash: 'always',
  build: {
    format: 'directory',
  },
  prefetch: {
    prefetchAll: false,
    defaultStrategy: 'hover',
  },
  vite: {
    plugins: [tailwindcss()],
  },
});
