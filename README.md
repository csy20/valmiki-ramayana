# Vālmīki Rāmāyaṇa

A zero-image, ultra-fast, offline-capable static web reader for the complete **Vālmīki Rāmāyaṇa** in **Sanskrit (Devanagari + IAST)**, **English prose (M. N. Dutt, 1891–1894, public domain)**, and **CC0 Hindi machine drafts**, built with Astro, Tailwind CSS, and Pagefind.

## Copyright & Data Guardrails

- **Sanskrit:** Public-domain shlokas transcribed on Sanskrit Wikisource (CC BY-SA 4.0 transcription), with editorial footnotes and commentary templates stripped. Every sarga JSON records its Wikisource `revid`.
- **English:** Public-domain prose translation by Manmatha Nath Dutt (Calcutta, 1891–1894), digitized via the Internet Archive (`archive.org`), stored strictly at **sarga level** as uncorrected OCR prose (`ocr_unreviewed`, `see_sarga`, or `missing`).
- **Hindi:** Deterministic offline translations generated per shloka strictly from the public-domain Sanskrit text using AI4Bharat `indictrans2-indic-indic-dist-320M` (MIT license), released under **CC0 1.0**. Every verse stores `"hi_source"` and `"hi_verified"`.
- **No copyrighted sources:** Gita Press, Bibek Debroy, Robert Goldman, `valmikiramayan.net`, and modern portals are excluded.

See [`DATA-LICENSE.md`](DATA-LICENSE.md) and the live `/sources/` page for full provenance and attribution.

## Architecture & Size-Budget Decisions

- **Partitioned JSON (`data/`):** Sargas are partitioned under `data/<slug>/<NNN>.json` (`01-bala` through `07-uttara`).
- **Build-time IAST:** To keep every sarga JSON strictly under the **30 KB gzip-9** budget (including the 200+ verse sargas in Sundara & Yuddha Kāṇḍas, even once Hindi text is populated), `iast` is omitted from the committed JSON files and computed deterministically at Astro & Pagefind build time using `@indic-transliteration/sanscript`.
- **Zero Images:** No `<img>`, `<picture>`, raster assets, or CSS `background-image: url(...)`. Only `public/icon.svg` is allow-listed for the browser tab favicon and PWA manifest.
- **Offline PWA:** Hand-written Service Worker (`/sw.js`) caches visited pages and lets users download any complete Kāṇḍa via Cache Storage without Workbox bloat.
- **Static Search:** Built at CI time with Pagefind (`scripts/build-search.mjs`) indexing Devanagari, IAST, ASCII-folded IAST, Hindi, and English paragraphs.

## Local Development

```bash
npm ci
npm run validate
npm run build
npm run preview
```

## Re-running the Data Pipeline

```bash
cd pipeline
uv sync
uv run pytest
uv run python -m vr fetch-sa
uv run python -m vr parse-sa
uv run python -m vr fetch-en
uv run python -m vr parse-en
uv run python -m vr build
```

## Custom Domain & GitHub Pages

`.github/workflows/deploy.yml` uses `actions/configure-pages@v5` and passes `SITE_URL` and `BASE_PATH` dynamically (`/` when a custom domain is configured in **Repository Settings → Pages**, or `/<repo>/` on `github.io`).
