import fs from 'node:fs';
import path from 'node:path';
import * as pagefind from 'pagefind';
import SanscriptPkg from '@indic-transliteration/sanscript';

const Sanscript = SanscriptPkg.default ?? SanscriptPkg;

const DATA_DIR = path.resolve(process.cwd(), 'data');
const DIST_DIR = path.resolve(process.cwd(), 'dist');
const INDEX_PATH = path.join(DATA_DIR, 'index.json');

function foldDiacritics(input) {
  return input
    .normalize('NFD')
    .replace(/\p{M}+/gu, '')
    .replace(/ṛ/gi, 'r')
    .replace(/ṝ/gi, 'r')
    .replace(/ḷ/gi, 'l')
    .toLowerCase();
}

const indexData = JSON.parse(fs.readFileSync(INDEX_PATH, 'utf8'));
const { index, errors } = await pagefind.createIndex({ forceLanguage: 'en' });
if (errors?.length || !index) {
  console.error('Failed to create Pagefind index:', errors);
  process.exit(1);
}

let verseCount = 0;
let enParaCount = 0;

for (const kanda of indexData.kandas) {
  const shortKanda = kanda.name_en.replace(/\s+Kanda$/, '');
  for (const sMeta of kanda.sargas) {
    const pad = String(sMeta.n).padStart(3, '0');
    const sargaDoc = JSON.parse(
      fs.readFileSync(path.join(DATA_DIR, kanda.slug, `${pad}.json`), 'utf8')
    );

    for (const v of sargaDoc.verses) {
      const iast = v.iast ?? Sanscript.t(v.sa, 'devanagari', 'iast');
      const content = [v.sa, iast, foldDiacritics(iast), v.hi ?? '']
        .filter(Boolean)
        .join(' ');
      const res = await index.addCustomRecord({
        url: `${kanda.slug}/${pad}/#v${v.n}`,
        language: 'en',
        content,
        meta: {
          title: `${kanda.name_iast} ${kanda.n}.${sMeta.n}.${v.n}`,
          kanda: shortKanda,
        },
        filters: {
          kanda: [shortKanda],
        },
      });
      if (res.errors?.length) {
        console.error('Pagefind verse record error:', res.errors);
        process.exit(1);
      }
      verseCount += 1;
    }

    if (Array.isArray(sargaDoc.en?.paragraphs)) {
      for (let i = 0; i < sargaDoc.en.paragraphs.length; i++) {
        const para = sargaDoc.en.paragraphs[i];
        const res = await index.addCustomRecord({
          url: `${kanda.slug}/${pad}/#en-${i + 1}`,
          language: 'en',
          content: para,
          meta: {
            title: `${kanda.name_en} · Sarga ${sMeta.n} · Dutt ¶${i + 1}`,
            kanda: shortKanda,
          },
          filters: {
            kanda: [shortKanda],
          },
        });
        if (res.errors?.length) {
          console.error('Pagefind en record error:', res.errors);
          process.exit(1);
        }
        enParaCount += 1;
      }
    }
  }
}

const outPath = path.join(DIST_DIR, 'pagefind');
const writeRes = await index.writeFiles({ outputPath: outPath });
if (writeRes.errors?.length) {
  console.error('Pagefind writeFiles error:', writeRes.errors);
  process.exit(1);
}
await pagefind.close();

console.log(`Built Pagefind index at ${outPath}: ${verseCount} verses, ${enParaCount} English paragraphs.`);
