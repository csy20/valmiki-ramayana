from __future__ import annotations

import re
import statistics
import unicodedata
from pathlib import Path
from typing import Any

from .common import (
    CACHE_DIR,
    KANDA_BY_SLUG,
    OVERRIDES_DIR,
    RAW_DIR,
    REPORTS_DIR,
    dump_compact_json,
    dump_pretty_json,
    load_json,
)

# Match SECTION lines allowing OCR garbles like SCTION, SECTIION, SEiCflON, SECTtON
SECTION_LINE_RE = re.compile(
    r"^\s*S\s*[E€i]?[C©]?\s*T\s*[I1lίtfl]{1,2}\s*O\s*N\s+(.+?)\s*$",
    re.IGNORECASE,
)

RUNNING_HEAD_RE = re.compile(
    r"^(?:THE\s+)?(?:R[AĀa]M[AĀa]YANA|B[AĀIl]LAK[AĀIl]NDAM|AYODHY[AĀ]K[AĀ]NDAM|"
    r"ARANYAK[AĀ]NDAM|AEANYAKANDAM|KISHKINDH[AĀ]\s*K[AĀ]NDAM|SUNDARAK[AĀ]NDAM|"
    r"YUDDHAK[AĀ]NDAM|UTTARAK[AĀ]NDAM|VTTARAKANDAM|XJTTARA.*)$",
    re.IGNORECASE,
)

ROMAN_VAL = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

EN_STOPWORDS = frozenset({
    "the", "and", "then", "having", "hearing", "thus", "that", "those", "these", "there",
    "when", "where", "which", "while", "with", "after", "from", "into", "unto", "upon",
    "what", "who", "whom", "whose", "why", "how", "for", "but", "not", "now", "all",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "great", "mighty", "high", "king", "prince", "lord", "sage", "saint", "ascetic",
    "hero", "son", "daughter", "wife", "brother", "father", "mother", "city", "forest",
    "mountain", "river", "earth", "heaven", "world", "gods", "deities", "celestials",
    "rakshasas", "rakshasa", "monkeys", "monkey", "bears", "section", "said", "spake",
    "replied", "addressed", "answered", "behold", "alas", "this", "they", "their", "them",
    "him", "his", "her", "hers", "she", "were", "was", "been", "being", "will", "shall",
    "should", "would", "could", "here", "thereupon", "thereat", "seeing", "beholding",
    "gone", "went", "came", "come", "going", "saying", "spoken", "words", "speech",
    "thousand", "hundred", "army", "hosts", "chariot", "arrows", "shafts", "bow",
    "battle", "fight", "slain", "killed", "exclaimed", "cried", "asked", "unto",
})


def parse_roman_strict(s: str) -> int | None:
    if not s or any(ch not in ROMAN_VAL for ch in s):
        return None
    total = 0
    prev = 0
    for ch in reversed(s):
        v = ROMAN_VAL[ch]
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    if total <= 0 or total > 300:
        return None
    return total


def _translate_roman(s: str, l_as_fifty: bool = False) -> int | None:
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "l":
            out.append("L" if l_as_fifty else "I")
        elif ch in ("1", "f", "t", "|", "ί", "¡", "!"):
            out.append("I")
        elif ch in ("n", "u", "H", "U"):
            out.append("II")
        elif ch == "m":
            out.append("III")
        elif ch == "M":
            if i + 1 < len(s) and s[i + 1] in ("l", "1", "I", "i", "L"):
                out.append("II")
                if s[i + 1] == "L":
                    out.append("I")
                    i += 1
            else:
                out.append("III")
        elif ch == "r" and i > 0 and s[i - 1].lower() == "i":
            out.append("I")
        elif ch in ("e", "E", "G") and i == 0:
            out.append("C")
        elif ch in ("i", "v", "x", "c", "I", "V", "X", "L", "C"):
            out.append(ch.upper())
        elif ch == "K" and i == len(s) - 1:
            out.append("I")
        elif ch == "2" and i == 0 and len(s) > 1:
            out.append("X")
        else:
            out.append(ch.upper())
        i += 1
    cand = "".join(out)
    val = parse_roman_strict(cand)
    if val is not None:
        return val
    cand2 = "".join(c for c in cand if c in "IVXLC")
    return parse_roman_strict(cand2)


def fuzzy_roman_candidates(raw_heading: str) -> list[int]:
    head = re.split(r"\s+[—–-]{1,}\s+", raw_heading.strip())[0]
    s = re.sub(r"[\s.,;:'\"`~^*<>()\[\]{}—–-]+", "", head)
    if not s:
        return []
    cands: list[int] = []
    has_l_fifty_cue = bool(re.match(r"^(?:[xX]l|l[xXvV])", s))
    order = (True, False) if ((has_l_fifty_cue and "1" in s) or re.match(r"^l[xXvV]", s)) else (False, True)
    for flag in order:
        v = _translate_roman(s, l_as_fifty=flag)
        if v is not None and v not in cands:
            cands.append(v)
    return cands


def fuzzy_parse_roman(raw_heading: str) -> int | None:
    cands = fuzzy_roman_candidates(raw_heading)
    return cands[0] if cands else None


def is_noise_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    low = s.lower()
    if "digitized by" in low or ("google" in low and ("books" in low or "search" in low)):
        return True
    if SECTION_LINE_RE.match(s):
        return False
    if s[0] in ("♦", "*", "†", "‡", "•"):
        return True
    if re.search(r"(?:—|--|-)\s*T\s*[.,]?\s*$", s):
        return True
    if re.fullmatch(r"[\d\s.,;:!?()\[\]{}\-—–_=+*^~`'\"|/\\<>•♦†‡]+", s):
        return True
    if len(s) <= 3 and not re.match(r"^[A-Za-z]{2,3}[.,!?]?$", s):
        return True
    words = s.split()
    alpha_chars = [c for c in s if c.isalpha()]
    if len(words) <= 4 and alpha_chars:
        upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
        cleaned_head = re.sub(r"[^A-Za-z\s]", "", s).strip()
        if RUNNING_HEAD_RE.match(cleaned_head):
            return True
        if upper_ratio >= 0.8 and len(s) <= 36 and not s.endswith("."):
            if any(k in cleaned_head.upper() for k in ("KANDA", "RAMAYANA", "BOOK", "PART", "VOLUME", "PAGE", "CHAPTER", "END OF")):
                return True
            if len(words) <= 2 and len(cleaned_head) <= 18 and re.search(r"K[AĀ]ND|R[AĀ]M[AĀ]Y", cleaned_head, re.I):
                return True
    return False


def clean_volume_lines(raw_text: str) -> list[str]:
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.splitlines()
    start_idx = 0
    for idx, ln in enumerate(lines):
        m = SECTION_LINE_RE.match(ln)
        if m and fuzzy_parse_roman(m.group(1)) == 1:
            start_idx = idx
            break

    cleaned: list[str] = []
    for ln in lines[start_idx:]:
        if is_noise_line(ln):
            continue
        cleaned.append(ln.rstrip())
    return cleaned


def clean_section_body(lines: list[str]) -> str:
    trimmed = list(lines)
    while trimmed and (not trimmed[-1].strip() or re.match(r"^\s*(?:END OF|THE END|FINIS)", trimmed[-1], re.I)):
        trimmed.pop()
    text = "\n".join(trimmed)
    text = re.sub(r"([A-Za-z])-\s*\n+\s*([a-z])", r"\1\2", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^[~^*•|]+\s*", "", text)
    return text


def split_into_paragraphs(text: str, target_min: int = 120, target_max: int = 180) -> list[str]:
    if not text.strip():
        return []
    sentences = re.split(
        r'(?<=[.!?])\s+(?=[A-Z“"‘])|(?<=[.!?]["”’])\s+(?=[A-Z“"‘])',
        text.strip(),
    )
    paragraphs: list[str] = []
    buf: list[str] = []
    wc = 0
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        sw = len(sent.split())
        if buf and (wc + sw > target_max and wc >= target_min):
            paragraphs.append(" ".join(buf))
            buf = [sent]
            wc = sw
        else:
            buf.append(sent)
            wc += sw
            if target_min <= wc <= target_max:
                paragraphs.append(" ".join(buf))
                buf = []
                wc = 0
    if buf:
        if paragraphs and wc < 40:
            paragraphs[-1] = f"{paragraphs[-1]} {' '.join(buf)}"
        else:
            paragraphs.append(" ".join(buf))
    return paragraphs


def split_raw_volume_by_kandas(raw_text: str, expected_kandas: list[tuple[str, int]]) -> list[str]:
    """Pre-split multi-kanda OCR volumes using title-page boundaries when present."""
    if len(expected_kandas) == 1:
        return [raw_text]
    slugs = [s for s, _ in expected_kandas]
    if slugs == ["01-bala", "02-ayodhya"]:
        m = re.search(r"EDITED AND PUBLISHED BY\s+MANMATHA NATH DUTT.*?AYODHYA KANDAM|Sanskrit op Valmiki\.\s+AYODHYA KANDAM", raw_text, re.S | re.I)
        if m:
            # Find SECTION I after title page
            sec1 = re.search(r"^\s*S\s*[E€i]?[C©]?\s*T\s*[I1lίtfl]{1,2}\s*O\s*N\s+[I1]\b", raw_text[m.start():], re.M | re.I)
            cut = m.start() + (sec1.start() if sec1 else 0)
            return [raw_text[:m.start()], raw_text[cut:]]
    if slugs == ["03-aranya", "04-kishkindha", "05-sundara"]:
        m_kish = re.search(r"KISHKINDHA\s+KANDAM\.\s*\n+\s*SECTION\s+I\b", raw_text, re.I)
        m_sund = re.search(r"VOL\.\s*V\..*?CALCUTTA\.\s*\n+\s*1892", raw_text, re.S | re.I)
        if m_kish and m_sund:
            # Sundara starts after the Vol V title-page / subscription block (look for "874" or "heart upon his journey")
            after = raw_text[m_sund.end():]
            m_body = re.search(r"(?:heart upon his journey|SECTION\s+I)", after, re.I)
            sund_start = m_sund.end() + (m_body.start() if m_body else 0)
            return [raw_text[:m_kish.start()], raw_text[m_kish.start():m_sund.start()], raw_text[sund_start:]]
    return [raw_text]


def extract_single_kanda_sections(raw_text: str, max_sec: int, assume_leading_s1: bool = False) -> dict[int, str]:
    lines = clean_volume_lines(raw_text) if not assume_leading_s1 else [
        ln.rstrip() for ln in raw_text.replace("\r\n", "\n").splitlines() if not is_noise_line(ln)
    ]
    raw_headings: list[tuple[int, str, list[int]]] = []
    for idx, ln in enumerate(lines):
        m = SECTION_LINE_RE.match(ln)
        if m:
            raw_headings.append((idx, m.group(1), fuzzy_roman_candidates(m.group(1))))

    if not raw_headings:
        return {}

    all_positions = [h[0] for h in raw_headings] + [len(lines)]
    pos_to_end = {raw_headings[i][0]: all_positions[i + 1] for i in range(len(raw_headings))}

    sec_map: dict[int, str] = {}
    # If title page led straight into Section 1 prose (missing page with heading "SECTION I") before heading II
    first_cands = raw_headings[0][2]
    if assume_leading_s1 and 1 not in first_cands and (2 in first_cands or 3 in first_cands):
        leading = clean_section_body(lines[: raw_headings[0][0]])
        if len(leading.split()) >= 40:
            sec_map[1] = leading

    prev = 1 if 1 in sec_map else 0
    assigned: list[tuple[int, int, int]] = []
    for j, (line_idx, raw_h, cands) in enumerate(raw_headings):
        end_line = pos_to_end[line_idx]
        next_parsed = None
        for _, _, nc in raw_headings[j + 1 : j + 4]:
            valid_nc = [v for v in nc if prev < v <= max_sec + 25]
            if valid_nc:
                next_parsed = min(valid_nc, key=lambda v: v - prev)
                break

        fitting = [v for v in cands if prev < v <= prev + 6]
        parsed = fitting[0] if fitting else (cands[0] if cands else None)
        if (prev + 1) in fitting:
            parsed = prev + 1

        sec_num: int | None = None
        if parsed is not None and prev < parsed <= prev + 6:
            if next_parsed is not None and next_parsed == prev + 2 and parsed != prev + 1:
                sec_num = prev + 1
            else:
                sec_num = parsed
        elif parsed is None or parsed <= prev or parsed > prev + 6:
            if next_parsed is None or next_parsed >= prev + 2:
                sec_num = prev + 1
            else:
                sec_num = None

        if sec_num is not None:
            assigned.append((sec_num, line_idx + 1, end_line))
            prev = sec_num

    for sec_num, s_line, e_line in assigned:
        body = clean_section_body(lines[s_line:e_line])
        if sec_num in sec_map and body:
            sec_map[sec_num] = f"{sec_map[sec_num]} {body}".strip()
        else:
            sec_map[sec_num] = body
    return sec_map


def fold_for_match(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(ch for ch in nfd if not unicodedata.combining(ch))
    stripped = stripped.replace("ṛ", "r").replace("ṝ", "r").replace("ḷ", "l")
    stripped = stripped.replace("sh", "s").replace("w", "v")
    stripped = re.sub(r"([bcdfgjklmnpqrstvwxz])h", r"\1", stripped)
    return stripped


def extract_proper_tokens(en_text: str) -> list[str]:
    raw_words = re.findall(r"\b([A-Z][A-Za-zāīūṛśṣṇṭḍñṅ]{3,})\b", en_text)
    seen: set[str] = set()
    tokens: list[str] = []
    for w in raw_words:
        low = fold_for_match(w)
        if len(low) < 4 or w.lower() in EN_STOPWORDS or low in EN_STOPWORDS:
            continue
        if low not in seen:
            seen.add(low)
            tokens.append(low)
    return tokens


def score_dutt_vs_sarga(en_tokens: list[str], folded_iast: str) -> float:
    if not en_tokens:
        return 0.0
    hits = 0
    for tok in en_tokens:
        root = tok[:5] if len(tok) >= 5 else tok
        if root in folded_iast:
            hits += 1
    return hits / len(en_tokens)


def align_monotonic_dp(
    dutt_keys: list[int],
    ws_count: int,
    score_matrix: list[list[float]],
    skip_ws_penalty: float = -0.02,
) -> tuple[dict[int, list[int]], list[int]]:
    """
    Global monotonic sequence alignment between dutt_keys (len M) and WS sargas 1..N.
    Returns ({ws_sarga: [matched_dutt_keys]}, dropped_dutt_keys).
    """
    m = len(dutt_keys)
    n = ws_count
    dp = [[0.0] * (n + 1) for _ in range(m + 1)]
    bp = [[0] * (n + 1) for _ in range(m + 1)]  # 1=diag(match), 2=skip_d, 3=skip_s

    for j in range(1, n + 1):
        dp[0][j] = dp[0][j - 1] + skip_ws_penalty
        bp[0][j] = 3
    for i in range(1, m + 1):
        dp[i][0] = dp[i - 1][0]
        bp[i][0] = 2

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            sc = score_matrix[i - 1][j - 1]
            # Tiny diagonal bias breaks exact 0-score ties monotonically
            tie = 1e-4 * (1.0 - abs((i / max(m, 1)) - (j / max(n, 1))))
            v_match = dp[i - 1][j - 1] + sc + tie
            v_skip_d = dp[i - 1][j]
            v_skip_s = dp[i][j - 1] + skip_ws_penalty
            if v_match >= v_skip_d and v_match >= v_skip_s:
                dp[i][j] = v_match
                bp[i][j] = 1
            elif v_skip_d >= v_skip_s:
                dp[i][j] = v_skip_d
                bp[i][j] = 2
            else:
                dp[i][j] = v_skip_s
                bp[i][j] = 3

    i, j = m, n
    ws_to_dutt: dict[int, list[int]] = {}
    dropped_dutt: list[int] = []
    while i > 0 or j > 0:
        act = bp[i][j]
        if act == 1:
            ws_to_dutt.setdefault(j, []).append(dutt_keys[i - 1])
            i -= 1
            j -= 1
        elif act == 2:
            dropped_dutt.append(dutt_keys[i - 1])
            i -= 1
        else:
            j -= 1

    for k in ws_to_dutt:
        ws_to_dutt[k].sort()
    dropped_dutt.reverse()
    return ws_to_dutt, dropped_dutt


def build_offset_runs(ws_to_dutt: dict[int, list[int]]) -> list[dict[str, int]]:
    pairs: list[tuple[int, int]] = []
    for ws_n in sorted(ws_to_dutt):
        for dn in ws_to_dutt[ws_n]:
            pairs.append((dn, ws_n - dn))
    if not pairs:
        return []
    runs: list[dict[str, int]] = []
    cur_from, cur_delta = pairs[0]
    cur_to = cur_from
    for dn, delta in pairs[1:]:
        if delta == cur_delta:
            cur_to = dn
        else:
            if cur_delta != 0:
                runs.append({"dutt_from": cur_from, "dutt_to": cur_to, "delta": cur_delta})
            cur_from = cur_to = dn
            cur_delta = delta
    if cur_delta != 0:
        runs.append({"dutt_from": cur_from, "dutt_to": cur_to, "delta": cur_delta})
    return runs


def apply_heading_overrides(
    sec_map: dict[int, str],
    overrides: dict[str, str],
) -> dict[int, str]:
    if not overrides:
        return sec_map
    out = dict(sec_map)
    for sarga_str in sorted(overrides.keys(), key=lambda x: int(x)):
        target_n = int(sarga_str)
        anchor = overrides[sarga_str].strip()
        if not anchor or target_n in out:
            continue
        owner = None
        for cand in range(target_n - 1, 0, -1):
            if cand in out:
                owner = cand
                break
        if owner is None:
            continue
        text = out[owner]
        idx = text.find(anchor)
        if idx == -1:
            pat = re.compile(r"\s+".join(re.escape(w) for w in anchor.split()))
            m = pat.search(text)
            if m:
                idx = m.start()
        if idx > 0:
            out[owner] = text[:idx].strip()
            out[target_n] = text[idx:].strip()
    return out


def spot_check_alignment(slug: str, sec_records: dict[int, dict[str, Any]], sa_docs: dict[int, dict[str, Any]]) -> list[str]:
    sarga_nums = sorted(sa_docs.keys())
    if not sarga_nums:
        return []
    picks = [sarga_nums[0], sarga_nums[len(sarga_nums) // 2], sarga_nums[-1]]
    notes: list[str] = []
    for sn in picks:
        en_rec = sec_records.get(sn, {})
        en_text = " ".join(en_rec.get("paragraphs", []))
        folded_iast = fold_for_match(" ".join(v["iast"] for v in sa_docs[sn]["verses"]))
        raw_cands = re.findall(r"\b([A-Z][A-Za-zāīūṛśṣṇṭḍñṅ]{3,})\b", en_text)
        hits: list[str] = []
        for nm in raw_cands:
            tok = fold_for_match(nm)
            if len(tok) < 4 or nm.lower() in EN_STOPWORDS or tok in EN_STOPWORDS:
                continue
            root = tok[:5] if len(tok) >= 5 else tok
            if root in folded_iast and nm not in hits:
                hits.append(nm)
            if len(hits) >= 4:
                break
        notes.append(f"sarga {sn} ({en_rec.get('status')}): matched {hits}")
    return notes


def parse_en() -> dict[str, Any]:
    dutt_dir = RAW_DIR / "dutt"
    out_cache = CACHE_DIR / "en"
    out_cache.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    heading_overrides = load_json(OVERRIDES_DIR / "english_headings.json", default={})

    vol_specs = [
        ("vol1_2_bala_ayodhya.txt", [("01-bala", 77), ("02-ayodhya", 119)]),
        ("vol3_5_aranya_kishkindha_sundara.txt", [("03-aranya", 75), ("04-kishkindha", 67), ("05-sundara", 68)]),
        ("vol6_yuddha.txt", [("06-yuddha", 132)]),
        ("vol7_uttara.txt", [("07-uttara", 126)]),
    ]
    source_tag_by_slug = {
        "01-bala": "mn_dutt_1891",
        "02-ayodhya": "mn_dutt_1891",
        "03-aranya": "mn_dutt_1891",
        "04-kishkindha": "mn_dutt_1892",
        "05-sundara": "mn_dutt_1892",
        "06-yuddha": "mn_dutt_1893",
        "07-uttara": "mn_dutt_1894",
    }

    parsed_by_slug: dict[str, dict[int, str]] = {}
    for fname, specs in vol_specs:
        raw_text = (dutt_dir / fname).read_text(encoding="utf-8", errors="replace")
        chunks = split_raw_volume_by_kandas(raw_text, specs)
        for idx, ((slug, max_sec), chunk) in enumerate(zip(specs, chunks)):
            sec_map = extract_single_kanda_sections(
                chunk,
                max_sec=max_sec,
                assume_leading_s1=(slug == "05-sundara"),
            )
            ov = heading_overrides.get(slug, {})
            parsed_by_slug[slug] = apply_heading_overrides(sec_map, ov)

    # Preload Sanskrit docs and compute diagonal sanity scores per Kanda
    sa_by_slug: dict[str, dict[int, dict[str, Any]]] = {}
    folded_iast_by_slug: dict[str, dict[int, str]] = {}
    dutt_tokens_by_slug: dict[str, dict[int, list[str]]] = {}
    diag_means: dict[str, float] = {}

    for slug in source_tag_by_slug:
        sa_docs = {
            doc["sarga"]: doc
            for sf in sorted((CACHE_DIR / "sa" / slug).glob("*.json"))
            for doc in [load_json(sf)]
        }
        sa_by_slug[slug] = sa_docs
        folded_iast_by_slug[slug] = {
            sn: fold_for_match(" ".join(v["iast"] for v in doc["verses"]))
            for sn, doc in sa_docs.items()
        }
        dutt_map = parsed_by_slug.get(slug, {})
        dutt_tokens_by_slug[slug] = {
            dn: extract_proper_tokens(txt) for dn, txt in dutt_map.items()
        }
        diag_scores = [
            score_dutt_vs_sarga(dutt_tokens_by_slug[slug][sn], folded_iast_by_slug[slug][sn])
            for sn in sa_docs
            if sn in dutt_map
        ]
        diag_means[slug] = statistics.mean(diag_scores) if diag_scores else 0.0

    median_diag = statistics.median(diag_means.values()) if diag_means else 0.0

    computed_offsets: dict[str, list[dict[str, int]]] = {}
    report_rows: list[str] = []
    report_details: list[str] = []
    total_ws_sargas = 0
    total_own_text = 0

    for slug, src_tag in source_tag_by_slug.items():
        sa_docs = sa_by_slug[slug]
        ws_count = len(sa_docs)
        total_ws_sargas += ws_count
        dutt_map = parsed_by_slug.get(slug, {})
        dutt_keys = sorted(dutt_map.keys())
        dutt_max = max(dutt_keys) if dutt_keys else 0
        diag_mean = diag_means[slug]

        use_dp = (dutt_max != ws_count) or (len(dutt_keys) > ws_count) or (diag_mean < 0.65 * median_diag)
        dropped_dutt: list[int] = []
        ws_to_dutt: dict[int, list[int]] = {}
        matched_scores: dict[int, float] = {}

        if use_dp and dutt_keys:
            score_matrix: list[list[float]] = []
            for dn in dutt_keys:
                toks = dutt_tokens_by_slug[slug][dn]
                row = [
                    score_dutt_vs_sarga(toks, folded_iast_by_slug[slug][sn])
                    for sn in range(1, ws_count + 1)
                ]
                score_matrix.append(row)
            ws_to_dutt, dropped_dutt = align_monotonic_dp(dutt_keys, ws_count, score_matrix)
            for sn, dns in ws_to_dutt.items():
                toks = []
                for dn in dns:
                    toks.extend(dutt_tokens_by_slug[slug][dn])
                matched_scores[sn] = score_dutt_vs_sarga(toks, folded_iast_by_slug[slug][sn])
            runs = build_offset_runs(ws_to_dutt)
            if runs:
                computed_offsets[slug] = runs
        else:
            for dn in dutt_keys:
                if 1 <= dn <= ws_count:
                    ws_to_dutt[dn] = [dn]
                    matched_scores[dn] = score_dutt_vs_sarga(
                        dutt_tokens_by_slug[slug][dn], folded_iast_by_slug[slug][dn]
                    )

        # Reject zero-score mismatches when neighbors match well and tokens are plentiful
        suspect_rejected: list[int] = []
        if use_dp:
            for sn in list(ws_to_dutt.keys()):
                dns = ws_to_dutt[sn]
                toks = []
                for dn in dns:
                    toks.extend(dutt_tokens_by_slug[slug][dn])
                if len(toks) >= 6 and matched_scores.get(sn, 0.0) == 0.0:
                    prev_ok = matched_scores.get(sn - 1, 0.0) >= 0.10
                    next_ok = matched_scores.get(sn + 1, 0.0) >= 0.10
                    if prev_ok or next_ok:
                        dropped_dutt.extend(dns)
                        del ws_to_dutt[sn]
                        suspect_rejected.append(sn)
            dropped_dutt = sorted(set(dropped_dutt))

        records: dict[int, dict[str, Any]] = {}
        own_count = 0
        see_count = 0
        miss_count = 0
        gaps: list[int] = []
        word_counts: list[tuple[int, int]] = []
        last_owner: int | None = None

        for sn in range(1, ws_count + 1):
            dns = ws_to_dutt.get(sn, [])
            texts = [dutt_map[dn] for dn in dns if dutt_map.get(dn, "").strip()]
            if texts:
                combined = " ".join(texts).strip()
                paras = split_into_paragraphs(combined)
                records[sn] = {
                    "source": src_tag,
                    "status": "ocr_unreviewed",
                    "covers": [sn],
                    "paragraphs": paras,
                }
                # Only treat subsequent missing WS sarga as merged if NOT a DP-skipped sarga
                last_owner = sn if not use_dp else None
                own_count += 1
                word_counts.append((sn, len(combined.split())))
            else:
                gaps.append(sn)
                if not use_dp and last_owner is not None:
                    records[sn] = {
                        "source": src_tag,
                        "status": "see_sarga",
                        "ref": last_owner,
                        "paragraphs": [],
                    }
                    records[last_owner]["covers"].append(sn)
                    see_count += 1
                else:
                    records[sn] = {
                        "source": src_tag,
                        "status": "missing",
                        "paragraphs": [],
                    }
                    miss_count += 1

        # In DP mode, if a contiguous Dutt section wasn't split (OCR missed heading like 40, 72, 106),
        # mark the skipped sarga as see_sarga pointing to the matched owner when appropriate
        if use_dp:
            for sn in list(gaps):
                if sn > 1 and (sn - 1) in ws_to_dutt and sn not in suspect_rejected:
                    # Check if sn-1 absorbed an OCR gap (no dutt heading for sn-1+1 in raw dutt_map)
                    owner_dns = ws_to_dutt[sn - 1]
                    if owner_dns and (owner_dns[-1] + 1) not in dutt_map:
                        records[sn] = {
                            "source": src_tag,
                            "status": "see_sarga",
                            "ref": sn - 1,
                            "paragraphs": [],
                        }
                        records[sn - 1]["covers"].append(sn)
                        see_count += 1
                        miss_count -= 1

        total_own_text += own_count
        k_out = out_cache / slug
        k_out.mkdir(parents=True, exist_ok=True)
        for sn, rec in sorted(records.items()):
            dump_compact_json(k_out / f"{sn:03d}.json", rec)

        wcs = [w for _, w in word_counts]
        med = statistics.median(wcs) if wcs else 0
        outliers = [(sn, w) for sn, w in word_counts if w < 80 or (med > 0 and w > 3 * med)]
        align_notes = spot_check_alignment(slug, records, sa_docs)

        report_rows.append(
            f"| {slug} | {ws_count} | {len(dutt_map)} (max {dutt_max}) | {diag_mean:.3f} | {'DP' if use_dp else 'direct'} | {own_count} ({100*own_count/ws_count:.1f}%) | {see_count} | {miss_count} |"
        )
        report_details.extend([
            f"### {slug} ({KANDA_BY_SLUG[slug].name_en})",
            f"- Wikisource sargas: {ws_count} | Dutt headings parsed: {len(dutt_map)} (max section {dutt_max}) | Mean diagonal score: {diag_mean:.3f} | Mode: {'DP monotonic alignment' if use_dp else 'direct 1:1'}",
            f"- Unmatched WS sargas (`see_sarga`/`missing`): {gaps if gaps else 'None'}",
            f"- Dutt-only sections (not in Wikisource text): {dropped_dutt if dropped_dutt else 'None'}",
            f"- Rejected zero-score suspect sargas: {suspect_rejected if suspect_rejected else 'None'}",
            f"- Median words/sarga: {med:.0f} | Outliers (<80 or >3x median): {outliers[:15]}",
            f"- Alignment spot-check: " + "; ".join(align_notes),
            "",
        ])
        print(
            f"[parse-en] {slug}: ws={ws_count}, dutt={len(dutt_map)} (max={dutt_max}), diag={diag_mean:.3f}, "
            f"mode={'DP' if use_dp else 'direct'}, own={own_count}/{ws_count} ({100*own_count/ws_count:.1f}%)"
        )

    dump_pretty_json(OVERRIDES_DIR / "english_offsets.json", computed_offsets)

    pct = 100 * total_own_text / total_ws_sargas if total_ws_sargas else 0
    report = [
        "# English (M. N. Dutt, 1891–1894) Parsing Report",
        "",
        f"- Total Wikisource sargas: **{total_ws_sargas}**",
        f"- Sargas with direct `ocr_unreviewed` prose: **{total_own_text} ({pct:.1f}%)**",
        f"- Median kanda diagonal name-match score: **{median_diag:.3f}**",
        "",
        "| Kanda | WS Sargas | Dutt Headings | Diag Score | Mode | Own Text | `see_sarga` | `missing` |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
        *report_rows,
        "",
        "## Per-Kanda Details & Alignment Spot-Check",
        "",
        *report_details,
    ]
    (REPORTS_DIR / "english.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return {"total_sargas": total_ws_sargas, "own_text": total_own_text, "pct": pct}
