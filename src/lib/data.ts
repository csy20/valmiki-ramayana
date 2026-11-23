import fs from 'node:fs';
import path from 'node:path';
import SanscriptPkg from '@indic-transliteration/sanscript';
import { padSarga } from './url';

const Sanscript = (SanscriptPkg as unknown as { default?: typeof SanscriptPkg }).default ?? SanscriptPkg;

export interface SargaIndexEntry {
  n: number;
  verses: number;
  en: 'ocr_unreviewed' | 'see_sarga' | 'missing' | 'community_verified';
  preview: string;
}

export interface KandaIndexEntry {
  n: number;
  slug: string;
  name_sa: string;
  name_iast: string;
  name_en: string;
  name_hi: string;
  verse_count: number;
  sargas: SargaIndexEntry[];
}

export interface CorpusIndex {
  schema: number;
  title: string;
  kandas: KandaIndexEntry[];
  totals: {
    sargas: number;
    verses: number;
    hi_generated: number;
    hi_verified: number;
    en_sargas: number;
  };
}

export interface VerseEntry {
  n: number;
  sa: string;
  iast: string;
  hi: string | null;
  hi_source: 'pending' | 'generated_from_pd_v1' | 'community_verified';
  hi_verified: boolean;
  hi_flag?: string;
}

export interface SargaDoc {
  schema: number;
  kanda: number;
  slug: string;
  sarga: number;
  sa_source: {
    site: string;
    page: string;
    revid: number;
  };
  en: {
    source: string;
    status: 'ocr_unreviewed' | 'see_sarga' | 'missing' | 'community_verified';
    covers?: number[];
    ref?: number;
    paragraphs: string[];
  };
  verses: VerseEntry[];
}

export interface SargaNavTarget {
  slug: string;
  sarga: number;
  kandaName: string;
}

const DATA_DIR = path.resolve(process.cwd(), 'data');

let cachedIndex: CorpusIndex | null = null;

export function getIndex(): CorpusIndex {
  if (!cachedIndex) {
    cachedIndex = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'index.json'), 'utf8')) as CorpusIndex;
  }
  return cachedIndex;
}

export function getKanda(slug: string): KandaIndexEntry | undefined {
  return getIndex().kandas.find((k) => k.slug === slug);
}

export function getSarga(slug: string, sargaN: number): SargaDoc {
  const file = path.join(DATA_DIR, slug, `${padSarga(sargaN)}.json`);
  const raw = JSON.parse(fs.readFileSync(file, 'utf8')) as Omit<SargaDoc, 'verses'> & {
    verses: (Omit<VerseEntry, 'iast'> & { iast?: string })[];
  };
  const verses: VerseEntry[] = raw.verses.map((v) => ({
    ...v,
    iast: v.iast ?? Sanscript.t(v.sa, 'devanagari', 'iast'),
  }));
  return { ...raw, verses };
}

export function getProvenance(): Record<string, unknown> {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'provenance.json'), 'utf8')) as Record<string, unknown>;
}

const DEVA_DIGITS = ['०', '१', '२', '३', '४', '५', '६', '७', '८', '९'];
export function intToDeva(n: number): string {
  return String(n)
    .split('')
    .map((d) => DEVA_DIGITS[Number(d)] ?? d)
    .join('');
}

export function getFlatSargaList(): { slug: string; sarga: number; kandaName: string }[] {
  const idx = getIndex();
  const out: { slug: string; sarga: number; kandaName: string }[] = [];
  for (const k of idx.kandas) {
    for (const s of k.sargas) {
      out.push({ slug: k.slug, sarga: s.n, kandaName: k.name_iast });
    }
  }
  return out;
}

export function getPrevNextSarga(
  slug: string,
  sargaN: number,
): { prev: SargaNavTarget | null; next: SargaNavTarget | null } {
  const list = getFlatSargaList();
  const pos = list.findIndex((item) => item.slug === slug && item.sarga === sargaN);
  if (pos === -1) return { prev: null, next: null };
  return {
    prev: pos > 0 ? list[pos - 1] : null,
    next: pos + 1 < list.length ? list[pos + 1] : null,
  };
}

export function formatEnSourceLabel(sourceTag: string): string {
  const yearMatch = sourceTag.match(/(\d{4})/);
  const year = yearMatch ? yearMatch[1] : '1891–1894';
  return `M. N. Dutt (${year}), uncorrected OCR — sarga-level prose`;
}
