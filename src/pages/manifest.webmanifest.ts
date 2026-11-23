import type { APIRoute } from 'astro';
import { withBase } from '../lib/url';

export const GET: APIRoute = () => {
  const base = withBase('');
  const manifest = {
    name: 'Vālmīki Rāmāyaṇa Reader',
    short_name: 'Rāmāyaṇa',
    description:
      'Complete Vālmīki Rāmāyaṇa in Sanskrit (Devanagari & IAST), public-domain English prose (M.N. Dutt), and CC0 Hindi drafts.',
    start_url: base,
    scope: base,
    display: 'standalone',
    background_color: '#fbf8f1',
    theme_color: '#a3471a',
    icons: [
      {
        src: `${base}icon.svg`,
        sizes: 'any',
        type: 'image/svg+xml',
      },
    ],
  };
  return new Response(JSON.stringify(manifest, null, 2) + '\n', {
    headers: { 'Content-Type': 'application/manifest+json; charset=utf-8' },
  });
};
