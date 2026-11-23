import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const DATA_DIR = path.resolve(process.cwd(), 'data');
const INDEX_PATH = path.join(DATA_DIR, 'index.json');
const MAX_JSON_GZIP_BYTES = 30 * 1024; // 30 KB hard limit

const VALID_EN_STATUS = new Set([
  'ocr_unreviewed',
  'see_sarga',
  'missing',
  'community_verified',
]);

const VALID_HI_SOURCE = new Set([
  'pending',
  'generated_from_pd_v1',
  'community_verified',
]);

function fail(msg) {
  console.error(`ERROR: ${msg}`);
  process.exitCode = 1;
}

if (!fs.existsSync(INDEX_PATH)) {
  console.error(`Missing ${INDEX_PATH}`);
  process.exit(1);
}

const index = JSON.parse(fs.readFileSync(INDEX_PATH, 'utf8'));
if (index.schema !== 1 || !Array.isArray(index.kandas) || index.kandas.length !== 7) {
  fail('data/index.json: invalid schema or kandas count !== 7');
}

let countedSargas = 0;
let countedVerses = 0;
let countedHiGenerated = 0;
let countedHiVerified = 0;
let countedEnSargas = 0;
const sizes = [];

for (const kanda of index.kandas) {
  let kVerses = 0;
  for (const sMeta of kanda.sargas) {
    countedSargas += 1;
    const pad = String(sMeta.n).padStart(3, '0');
    const filePath = path.join(DATA_DIR, kanda.slug, `${pad}.json`);
    if (!fs.existsSync(filePath)) {
      fail(`Missing sarga file: ${kanda.slug}/${pad}.json`);
      continue;
    }

    const raw = fs.readFileSync(filePath);
    const gzBytes = zlib.gzipSync(raw, { level: 9 }).length;
    sizes.push({ file: `${kanda.slug}/${pad}.json`, rawBytes: raw.length, gzBytes });
    if (gzBytes > MAX_JSON_GZIP_BYTES) {
      fail(`${kanda.slug}/${pad}.json gzip-9 size ${gzBytes} B exceeds 30 KB (${MAX_JSON_GZIP_BYTES} B)`);
    }

    const doc = JSON.parse(raw.toString('utf8'));
    if (doc.schema !== 1) fail(`${kanda.slug}/${pad}.json: schema !== 1`);
    if (doc.kanda !== kanda.n || doc.slug !== kanda.slug || doc.sarga !== sMeta.n) {
      fail(`${kanda.slug}/${pad}.json: kanda/slug/sarga mismatch`);
    }
    if (!doc.sa_source || typeof doc.sa_source.revid !== 'number') {
      fail(`${kanda.slug}/${pad}.json: missing sa_source.revid`);
    }
    if (!doc.en || !VALID_EN_STATUS.has(doc.en.status)) {
      fail(`${kanda.slug}/${pad}.json: invalid en.status=${doc.en?.status}`);
    } else {
      if (doc.en.status === 'see_sarga') {
        if (typeof doc.en.ref !== 'number' || !Array.isArray(doc.en.paragraphs) || doc.en.paragraphs.length !== 0) {
          fail(`${kanda.slug}/${pad}.json: see_sarga must have numeric ref and empty paragraphs`);
        }
      }
      if (doc.en.status === 'ocr_unreviewed' || doc.en.status === 'community_verified') {
        countedEnSargas += 1;
        if (!Array.isArray(doc.en.paragraphs) || doc.en.paragraphs.length === 0) {
          fail(`${kanda.slug}/${pad}.json: ${doc.en.status} must have non-empty paragraphs`);
        }
      }
    }

    if (!Array.isArray(doc.verses) || doc.verses.length === 0) {
      fail(`${kanda.slug}/${pad}.json: empty verses`);
      continue;
    }
    if (doc.verses.length !== sMeta.verses) {
      fail(`${kanda.slug}/${pad}.json: verse count ${doc.verses.length} !== index ${sMeta.verses}`);
    }

    for (let i = 0; i < doc.verses.length; i++) {
      const v = doc.verses[i];
      if (v.n !== i + 1) {
        fail(`${kanda.slug}/${pad}.json: non-contiguous verse n=${v.n} at idx=${i}`);
        break;
      }
      if (typeof v.sa !== 'string' || !v.sa.trim()) {
        fail(`${kanda.slug}/${pad}.json v${v.n}: empty sa`);
      }
      if (typeof v.hi_verified !== 'boolean') {
        fail(`${kanda.slug}/${pad}.json v${v.n}: hi_verified must be boolean`);
      }
      if (!VALID_HI_SOURCE.has(v.hi_source)) {
        fail(`${kanda.slug}/${pad}.json v${v.n}: invalid hi_source=${v.hi_source}`);
      }
      if (v.hi_source === 'pending' && v.hi !== null) {
        fail(`${kanda.slug}/${pad}.json v${v.n}: hi_source=pending requires hi=null`);
      }
      if (v.hi_source !== 'pending' && (typeof v.hi !== 'string' || !v.hi.trim())) {
        fail(`${kanda.slug}/${pad}.json v${v.n}: non-pending hi_source requires non-empty hi string`);
      }
      if (v.en !== undefined && v.en !== null && (typeof v.en !== 'string' || !v.en.trim())) {
        fail(`${kanda.slug}/${pad}.json v${v.n}: optional en must be a non-empty string or null`);
      }
      if (v.hi_source !== 'pending') countedHiGenerated += 1;
      if (v.hi_verified) countedHiVerified += 1;
    }

    kVerses += doc.verses.length;
    countedVerses += doc.verses.length;
  }

  if (kVerses !== kanda.verse_count) {
    fail(`${kanda.slug}: verse_count ${kanda.verse_count} !== summed ${kVerses}`);
  }
}

if (index.totals) {
  if (index.totals.sargas !== countedSargas) fail(`totals.sargas ${index.totals.sargas} !== ${countedSargas}`);
  if (index.totals.verses !== countedVerses) fail(`totals.verses ${index.totals.verses} !== ${countedVerses}`);
  if (index.totals.hi_generated !== countedHiGenerated) fail(`totals.hi_generated ${index.totals.hi_generated} !== ${countedHiGenerated}`);
  if (index.totals.hi_verified !== countedHiVerified) fail(`totals.hi_verified ${index.totals.hi_verified} !== ${countedHiVerified}`);
  if (index.totals.en_sargas !== countedEnSargas) fail(`totals.en_sargas ${index.totals.en_sargas} !== ${countedEnSargas}`);
}

sizes.sort((a, b) => b.gzBytes - a.gzBytes);
console.log(`Validated ${countedSargas} sargas, ${countedVerses} verses (en=${countedEnSargas}, hi=${countedHiGenerated}).`);
console.log('Top 10 sarga JSON sizes (gzip-9):');
for (const s of sizes.slice(0, 10)) {
  console.log(`  ${s.file}: ${(s.gzBytes / 1024).toFixed(2)} KB gz (${(s.rawBytes / 1024).toFixed(2)} KB raw)`);
}
if (process.exitCode) {
  process.exit(process.exitCode);
}
