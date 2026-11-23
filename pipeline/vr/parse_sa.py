from __future__ import annotations

import re
from typing import Any

from indic_transliteration import sanscript

from .common import CACHE_DIR, KANDAS, RAW_DIR, REPORTS_DIR, deva_to_int, dump_compact_json, load_json

POEM_RE = re.compile(r"<poem[^>]*>(.*?)</poem>", re.DOTALL | re.IGNORECASE)
PRE_CLOSED_RE = re.compile(r"<pre[^>]*>(.*?)</pre>", re.DOTALL | re.IGNORECASE)
PRE_OPEN_RE = re.compile(r"<pre[^>]*>(.*)$", re.DOTALL | re.IGNORECASE)
POEM_OPEN_RE = re.compile(r"<poem[^>]*>(.*)$", re.DOTALL | re.IGNORECASE)

FOOTER_SPLIT_RE = re.compile(r"==\s*(?:स्रोतः|सन्दर्भ|टिप्पणी|बाह्य).*$", re.DOTALL)
CATEGORY_RE = re.compile(r"\[\[(?:वर्गः|Category):[^\]]*\]\]", re.IGNORECASE)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
REF_RE = re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/?>", re.DOTALL | re.IGNORECASE)
FILE_LINK_RE = re.compile(r"\[\[(?:File|Image|चित्रम्):[^\]]*\]\]+", re.IGNORECASE)
EXT_LINK_RE = re.compile(r"\[https?://[^\]]+\]")
TEMPLATE_RE = re.compile(r"\{\{[^{}]*\}\}")
BOLD_LINE_RE = re.compile(r"^[ \t]*(?:'''|”’|’”|\"')[^\n]*$", re.MULTILINE)
COLOPHON_LINE_RE = re.compile(
    r"^[ \t]*(?:'''|”’|’”|\"'|॥|\|\||।।)?\s*(?:इत्यार्षे|इति\s+(?:श्री|वाल्मीकि)|इत्ययोध्याकाण्ड|इत्युत्तरकाण्ड|श्रीमद्वाल्मीक|श्रीमद्रामायणे|श्रीसीतारामचन्द्रार्पणमस्तु).*$",
    re.MULTILINE,
)
MARKER_RE = re.compile(
    r"(?:॥|\|\||।।)\s*(?:([०-९0-9]+)\s*[-–.]\s*([०-९0-9]+)\s*[-–.]\s*)?([०-९0-9]+)\s*(?:॥|\|\||।।)"
)
HTML_TAG_RE = re.compile(r"</?(?:br|p|div|span|center|b|i|small|big|poem|pre|font|u|sup|sub)[^>]*/?>", re.IGNORECASE)


def parse_number(s: str) -> int:
    return deva_to_int(s)


def extract_poem_body(wikitext: str) -> tuple[str, bool]:
    trimmed = FOOTER_SPLIT_RE.sub("", wikitext)
    trimmed = CATEGORY_RE.sub("", trimmed)

    poems = POEM_RE.findall(trimmed)
    if poems:
        return "\n".join(poems), True

    pres = PRE_CLOSED_RE.findall(trimmed)
    if pres:
        return "\n".join(pres), True

    m_open_poem = POEM_OPEN_RE.search(trimmed)
    if m_open_poem:
        return m_open_poem.group(1), True

    m_open_pre = PRE_OPEN_RE.search(trimmed)
    if m_open_pre:
        return m_open_pre.group(1), True

    return trimmed, False


def clean_wikitext(raw_body: str) -> str:
    text = COMMENT_RE.sub("", raw_body)
    text = REF_RE.sub("", text)
    text = FILE_LINK_RE.sub("", text)
    text = EXT_LINK_RE.sub("", text)
    for _ in range(5):
        new_text = TEMPLATE_RE.sub("", text)
        if new_text == text:
            break
        text = new_text
    text = HTML_TAG_RE.sub("\n", text)
    text = COLOPHON_LINE_RE.sub("", text)
    text = BOLD_LINE_RE.sub("", text)
    text = text.replace("'''", "").replace("”’", "").replace("’”", "")
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"^[:\s]+", "", line).rstrip()
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def split_verses(
    cleaned_text: str,
    expected_kanda: int,
    expected_sarga: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    anomalies: list[str] = []
    verses: list[dict[str, Any]] = []
    pos = 0
    matches = list(MARKER_RE.finditer(cleaned_text))
    if not matches:
        if cleaned_text.strip():
            anomalies.append(f"no_markers (text_len={len(cleaned_text.strip())})")
        return verses, anomalies

    raw_nums: list[int] = []
    for idx, m in enumerate(matches, start=1):
        chunk = cleaned_text[pos : m.start()]
        pos = m.end()
        if m.group(1) is not None and m.group(2) is not None:
            mk = parse_number(m.group(1))
            ms = parse_number(m.group(2))
            if mk != expected_kanda or ms != expected_sarga:
                anomalies.append(f"marker_mismatch got={mk}-{ms}-{parse_number(m.group(3))} expected={expected_kanda}-{expected_sarga}")
        mn = parse_number(m.group(3))

        lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
        if not lines:
            anomalies.append(f"empty_verse raw_n={mn}")
            continue
        lines[-1] = re.sub(r"[\s।|॥]+$", "", lines[-1]).strip()
        lines = [ln for ln in lines if ln]
        if not lines:
            anomalies.append(f"empty_verse_after_trim raw_n={mn}")
            continue
        lines[-1] = f"{lines[-1]} ॥"
        sa = "\n".join(lines)
        iast = sanscript.transliterate(sa, sanscript.DEVANAGARI, sanscript.IAST)

        raw_nums.append(mn)
        verses.append({"n": len(verses) + 1, "sa": sa, "iast": iast})

    trailing = cleaned_text[pos:].strip()
    if trailing:
        trailing_stripped = re.sub(r"(?:॥|\|\||।।)?\s*[०-९0-9]+(?:\s*[-–.]\s*[०-९0-9]+)?\s*(?:॥|\|\||।।)?", "", trailing).strip()
        if trailing_stripped:
            anomalies.append(f"trailing_text: {trailing_stripped[:120]!r}")

    expected = list(range(1, len(raw_nums) + 1))
    if raw_nums != expected:
        dups = len(raw_nums) - len(set(raw_nums))
        missing = sorted(set(range(1, (max(raw_nums) if raw_nums else 0) + 1)) - set(raw_nums))
        anomalies.append(
            f"source_num_mismatch count={len(raw_nums)} max={max(raw_nums) if raw_nums else 0} dups={dups} missing={missing[:10]}"
        )

    return verses, anomalies


def parse_sa() -> dict[str, Any]:
    raw_ws = RAW_DIR / "wikisource"
    revids = load_json(raw_ws / "revids.json", default={})
    out_cache = CACHE_DIR / "sa"
    out_cache.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    total_sargas = 0
    total_verses = 0
    anomaly_lines: list[str] = []
    kanda_stats: list[dict[str, Any]] = []

    for kanda in KANDAS:
        kdir = raw_ws / kanda.slug
        k_out = out_cache / kanda.slug
        k_out.mkdir(parents=True, exist_ok=True)
        k_revids = revids.get(kanda.slug, {})

        wiki_files = sorted(kdir.glob("*.wiki"))
        k_verses = 0
        k_anomalies = 0
        sarga_nums: list[int] = []
        for wf in wiki_files:
            sarga_n = int(wf.stem)
            sarga_nums.append(sarga_n)
            wikitext = wf.read_text(encoding="utf-8")
            body, has_wrapper = extract_poem_body(wikitext)
            cleaned = clean_wikitext(body)
            verses, anomalies = split_verses(cleaned, kanda.n, sarga_n)
            if not has_wrapper:
                anomalies.insert(0, "no_poem_or_pre_wrapper")
            if anomalies:
                k_anomalies += 1
                anomaly_lines.append(f"- **{kanda.slug}/{sarga_n:03d}**: " + "; ".join(anomalies))

            meta = k_revids.get(f"{sarga_n:03d}", {})
            record = {
                "kanda": kanda.n,
                "slug": kanda.slug,
                "sarga": sarga_n,
                "page": meta.get("title", f"रामायणम्/{kanda.name_sa}/सर्गः {sarga_n}"),
                "revid": meta.get("revid", 0),
                "verses": verses,
            }
            dump_compact_json(k_out / f"{sarga_n:03d}.json", record)
            k_verses += len(verses)

        expected_sargas = list(range(1, len(sarga_nums) + 1))
        if sarga_nums != expected_sargas:
            missing_s = sorted(set(range(1, max(sarga_nums, default=0) + 1)) - set(sarga_nums))
            anomaly_lines.append(f"- **{kanda.slug} sarga gaps**: missing={missing_s}")

        total_sargas += len(wiki_files)
        total_verses += k_verses
        kanda_stats.append({
            "slug": kanda.slug,
            "sargas": len(wiki_files),
            "verses": k_verses,
            "anomalous_sargas": k_anomalies,
        })
        print(f"[parse-sa] {kanda.slug}: {len(wiki_files)} sargas, {k_verses} verses, {k_anomalies} anomalous")

    report = [
        "# Sanskrit Parsing Report",
        "",
        f"- Total sargas: **{total_sargas}**",
        f"- Total verses: **{total_verses}**",
        f"- Sargas with anomalies: **{len(anomaly_lines)}**",
        "",
        "## Per-Kanda Summary",
        "",
        "| Kanda | Sargas | Verses | Sargas w/ anomalies |",
        "| --- | ---: | ---: | ---: |",
    ]
    for st in kanda_stats:
        report.append(f"| {st['slug']} | {st['sargas']} | {st['verses']} | {st['anomalous_sargas']} |")
    report.extend(["", "## Anomalies", ""])
    if anomaly_lines:
        report.extend(anomaly_lines)
    else:
        report.append("None.")
    (REPORTS_DIR / "sanskrit.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    return {"sargas": total_sargas, "verses": total_verses, "kandas": kanda_stats}
