import type { APIRoute } from 'astro';
import { getIndex } from '../../lib/data';
import { kandaUrl, sargaUrl } from '../../lib/url';

export function getStaticPaths() {
  return getIndex().kandas.map((kanda) => ({
    params: { kanda: kanda.slug },
    props: { kanda },
  }));
}

export const GET: APIRoute = ({ props }) => {
  const kanda = props.kanda as ReturnType<typeof getIndex>['kandas'][number];
  const urls = [
    kandaUrl(kanda.slug),
    ...kanda.sargas.map((s) => sargaUrl(kanda.slug, s.n)),
  ];
  return new Response(
    JSON.stringify({ slug: kanda.slug, count: urls.length, urls }),
    { headers: { 'Content-Type': 'application/json; charset=utf-8' } },
  );
};
