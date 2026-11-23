# Contributing

Thank you for helping improve the accuracy of this public-domain edition of the Vālmīki Rāmāyaṇa!

## Copyright Rule (Non-Negotiable)

Never submit text copied from copyrighted translations, commentaries, or modern portals (including Gita Press, Bibek Debroy, Robert Goldman, `valmikiramayan.net`, or IIT Kanpur translations). Corrections must come strictly from public-domain sources (Sanskrit Wikisource, M. N. Dutt's 1891–1894 volumes) or your own original Hindi translation work contributed under CC0.

## Submitting a Verse or Translation Fix via PR

1. Locate the sarga JSON under `data/<kanda-slug>/<NNN>.json` (for example, `data/01-bala/001.json`).
2. Edit the target verse or English paragraph:
   - **Verified Hindi:** Update `"hi"` and set:
     ```json
     "hi_source": "community_verified",
     "hi_verified": true
     ```
     Remove `"hi_flag"` if present.
   - **Verified English OCR cleanup:** Clean OCR typos in `"en.paragraphs"` and set `"en.status": "community_verified"`.
   - **Sanskrit:** Update `"sa"` (keep Devanagari double danda ` ॥` at the end; IAST is derived automatically at build time).
3. Run data validation and tests before opening your PR:
   ```bash
   npm run validate
   npm run build
   ```

Note: `python -m vr build` in the pipeline automatically preserves `"community_verified"` entries for both `"hi"` and `"en"` so pipeline re-runs never overwrite human review.

## Re-running the Pipeline

```bash
cd pipeline
uv run pytest
uv run python -m vr build
```

For English section split fixes without re-editing OCR text directly, you can add section opening phrases to `pipeline/overrides/english_headings.json` (`{"01-bala": {"11": "exact first words..."}}`) and rerun `uv run python -m vr parse-en && uv run python -m vr build`.
