/**
 * Normalize an internal path against Astro's BASE_URL cleanly whether
 * deployed at `/` (custom domain) or `/<repo>/` (GitHub Pages subpath).
 */
export function withBase(path: string): string {
  const base = (import.meta.env.BASE_URL || '/').replace(/\/+$/, '');
  const clean = path.replace(/^\/+/, '');
  if (!clean) {
    return base ? `${base}/` : '/';
  }
  return base ? `${base}/${clean}` : `/${clean}`;
}

export function padSarga(n: number): string {
  return String(n).padStart(3, '0');
}

export function kandaUrl(slug: string): string {
  return withBase(`${slug}/`);
}

export function sargaUrl(slug: string, sarga: number): string {
  return withBase(`${slug}/${padSarga(sarga)}/`);
}
