import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const DIST_DIR = path.resolve(process.cwd(), 'dist');
const MAX_HTML_GZIP_BYTES = 40 * 1024; // 40 KB hard limit
const MAX_DIST_BYTES = 1024 * 1024 * 1024; // 1 GB hard limit
const WARN_DIST_BYTES = 300 * 1024 * 1024; // 300 MB warning

function walk(dir) {
  const out = [];
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) out.push(...walk(p));
    else out.push(p);
  }
  return out;
}

if (!fs.existsSync(DIST_DIR)) {
  console.error(`Missing ${DIST_DIR}`);
  process.exit(1);
}

const files = walk(DIST_DIR);
let totalBytes = 0;
let pagefindBytes = 0;
const sargaHtmls = [];

const sargaRe = /^0[1-7]-[a-z]+\/\d{3}\/index\.html$/;

for (const f of files) {
  const rel = path.relative(DIST_DIR, f).split(path.sep).join('/');
  const st = fs.statSync(f);
  totalBytes += st.size;
  if (rel.startsWith('pagefind/')) {
    pagefindBytes += st.size;
  }
  if (sargaRe.test(rel)) {
    const raw = fs.readFileSync(f);
    const gzBytes = zlib.gzipSync(raw, { level: 9 }).length;
    sargaHtmls.push({ file: rel, rawBytes: raw.length, gzBytes });
  }
}

sargaHtmls.sort((a, b) => a.gzBytes - b.gzBytes);
if (sargaHtmls.length === 0) {
  console.error('ERROR: No sarga HTML pages found in dist/');
  process.exit(1);
}

const p50 = sargaHtmls[Math.floor(sargaHtmls.length * 0.5)].gzBytes;
const p95 = sargaHtmls[Math.floor(sargaHtmls.length * 0.95)].gzBytes;
const max = sargaHtmls[sargaHtmls.length - 1].gzBytes;

console.log(`Sarga HTML pages: ${sargaHtmls.length}`);
console.log(`  p50 gzip-9: ${(p50 / 1024).toFixed(2)} KB`);
console.log(`  p95 gzip-9: ${(p95 / 1024).toFixed(2)} KB`);
console.log(`  max gzip-9: ${(max / 1024).toFixed(2)} KB`);
console.log('Top 10 largest sarga HTML pages (gzip-9):');
for (const item of sargaHtmls.slice(-10).reverse()) {
  console.log(`  ${item.file}: ${(item.gzBytes / 1024).toFixed(2)} KB gz (${(item.rawBytes / 1024).toFixed(2)} KB raw)`);
}

console.log(`Pagefind dir size: ${(pagefindBytes / (1024 * 1024)).toFixed(2)} MB`);
console.log(`Total dist/ size: ${(totalBytes / (1024 * 1024)).toFixed(2)} MB (${files.length} files)`);

let failed = false;
for (const item of sargaHtmls) {
  if (item.gzBytes > MAX_HTML_GZIP_BYTES) {
    console.error(`ERROR: ${item.file} gzip-9 ${item.gzBytes} B exceeds 40 KB (${MAX_HTML_GZIP_BYTES} B)`);
    failed = true;
  }
}

if (totalBytes > WARN_DIST_BYTES) {
  console.warn(`WARNING: dist/ size ${(totalBytes / (1024 * 1024)).toFixed(2)} MB exceeds 300 MB`);
}
if (totalBytes >= MAX_DIST_BYTES) {
  console.error(`ERROR: dist/ size ${totalBytes} B >= 1 GB`);
  failed = true;
}

if (failed) process.exit(1);
