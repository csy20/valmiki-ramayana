import fs from 'node:fs';
import path from 'node:path';

const DIST_DIR = path.resolve(process.cwd(), 'dist');
const RASTER_EXTS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif', '.bmp', '.ico', '.tif', '.tiff']);

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

let failed = false;
for (const f of walk(DIST_DIR)) {
  const rel = path.relative(DIST_DIR, f).split(path.sep).join('/');
  const ext = path.extname(f).toLowerCase();

  if (RASTER_EXTS.has(ext)) {
    console.error(`ERROR: Forbidden raster image in dist/: ${rel}`);
    failed = true;
  }
  if (ext === '.svg' && rel !== 'icon.svg') {
    console.error(`ERROR: Forbidden SVG in dist/ (only icon.svg allow-listed): ${rel}`);
    failed = true;
  }

  if (ext === '.html' || ext === '.css') {
    const text = fs.readFileSync(f, 'utf8');
    if (ext === '.html' && (/<img[\s>/]/i.test(text) || /<picture[\s>/]/i.test(text))) {
      console.error(`ERROR: Forbidden <img> or <picture> tag in ${rel}`);
      failed = true;
    }
    if (/background-image\s*:\s*url\s*\(/i.test(text)) {
      console.error(`ERROR: Forbidden background-image:url( in ${rel}`);
      failed = true;
    }
  }
}

if (failed) process.exit(1);
console.log('No-image policy check passed (0 raster assets, 0 <img>/<picture>, only allow-listed icon.svg).');
