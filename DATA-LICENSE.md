# Data Licensing & Provenance

All source code, pipeline scripts, and Astro templates in this repository are licensed under the [MIT License](LICENSE). The textual data under `data/` has distinct provenance by layer:

## 1. Sanskrit Text (`sa`)
- **Source:** Sanskrit Wikisource (`sa.wikisource.org`, `रामायणम्/*`), Southern/vulgate recension.
- **Status:** The underlying classical text of the Valmiki Rāmāyaṇa is in the public domain worldwide. The Wikisource digital transcription and markup are shared by Wikisource contributors under **CC BY-SA 4.0** (see individual revision IDs stored in `sa_source.revid` in each chapter JSON and `data/provenance.json`).
- Editorial footnotes and commentary templates are stripped by `pipeline/vr/parse_sa.py`.

## 2. IAST Transliteration (`iast`)
- Generated deterministically from the Sanskrit Devanagari text using `indic-transliteration` (`sanscript.DEVANAGARI -> sanscript.IAST`).
- Any derivative transliteration additions follow the CC BY-SA 4.0 / public-domain status of the underlying Sanskrit text.

## 3. English Prose Translation (`en`)
- **Source:** Manmatha Nath (M. N.) Dutt, *The Ramayana: Translated into English Prose from the Original Sanskrit of Valmiki*, Calcutta, 1891–1894 (7 volumes), digitized via the Internet Archive (`archive.org`).
- **Status:** **Public Domain** (published 1891–1894; author died 1914).
- Stored strictly at **sarga level** as uncorrected OCR prose with explicit status flags (`ocr_unreviewed`, `see_sarga`, `missing`, `community_verified`).

## 4. Hindi Drafts (`hi`)
- **Source:** Generated offline deterministically per shloka strictly from the public-domain Sanskrit text using AI4Bharat `indictrans2-indic-indic-dist-320M` (MIT License).
- **Status:** Released into the public domain under **CC0 1.0 Universal** (`https://creativecommons.org/publicdomain/zero/1.0/`).
- Every verse tracks `"hi_source"` (`"pending"`, `"generated_from_pd_v1"`, or `"community_verified"`) and `"hi_verified"` (boolean).

## 5. Fonts
- Self-hosted variable fonts (`Source Serif 4` and `Noto Serif Devanagari`) via Fontsource, licensed under the **SIL Open Font License 1.1**.

## Excluded Sources
No copyrighted translations, modern portals, or commentaries (including Gita Press, Bibek Debroy, Robert Goldman, `valmikiramayan.net`, or IIT Kanpur translations) are used anywhere in this project.
