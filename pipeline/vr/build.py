from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .common import (
    CACHE_DIR,
    DATA_DIR,
    KANDAS,
    RAW_DIR,
    dump_compact_json,
    dump_pretty_json,
    load_json,
)

HINDI_MODEL_ID = "ai4bharat/indictrans2-indic-indic-dist-320M"
HINDI_MODEL_REV = "ffb7582b6d43791f1fb26b2153fc065f2e9ea575"


def normalize_sa_for_hindi(sa: str) -> str:
    cleaned = sa.replace("।", " ").replace("॥", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def hindi_cache_key(sa: str, rev: str = HINDI_MODEL_REV) -> tuple[str, str]:
    norm = normalize_sa_for_hindi(sa)
    digest = hashlib.sha256(f"{rev}|v1|{norm}".encode("utf-8")).hexdigest()
    return digest, norm


def load_hindi_cache(cache_path: Path) -> dict[str, dict[str, Any]]:
    import json

    cache: dict[str, dict[str, Any]] = {}
    if not cache_path.exists():
        return cache
    with cache_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if "key" in rec and rec.get("hi"):
                cache[rec["key"]] = rec
    return cache


def make_preview(en_rec: dict[str, Any], verses: list[dict[str, Any]]) -> str:
    paras = en_rec.get("paragraphs") or []
    if paras:
        txt = re.sub(r"\s+", " ", paras[0]).strip()
    elif verses:
        first_line = verses[0]["iast"].splitlines()[0].strip()
        txt = first_line
    else:
        return ""
    if len(txt) <= 90:
        return txt
    cut = txt[:89].rsplit(" ", 1)[0]
    return f"{cut}…"


def build_data() -> dict[str, Any]:
    sa_root = CACHE_DIR / "sa"
    en_root = CACHE_DIR / "en"
    hi_cache = load_hindi_cache(CACHE_DIR / "hi.jsonl")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    index_kandas: list[dict[str, Any]] = []
    total_sargas = 0
    total_verses = 0
    total_hi_gen = 0
    total_hi_ver = 0
    total_en_sargas = 0
    revids_summary: dict[str, dict[str, int]] = {}

    for kanda in KANDAS:
        sa_dir = sa_root / kanda.slug
        en_dir = en_root / kanda.slug
        out_kdir = DATA_DIR / kanda.slug
        out_kdir.mkdir(parents=True, exist_ok=True)

        sa_files = sorted(sa_dir.glob("*.json"))
        k_verse_count = 0
        k_sargas_index: list[dict[str, Any]] = []
        k_revids: dict[str, int] = {}

        for sf in sa_files:
            sa_doc = load_json(sf)
            sn = int(sa_doc["sarga"])
            pad = f"{sn:03d}"
            out_file = out_kdir / f"{pad}.json"
            existing = load_json(out_file, default={}) or {}

            # English: preserve community_verified existing content
            existing_en = existing.get("en")
            if isinstance(existing_en, dict) and existing_en.get("status") == "community_verified":
                en_obj = existing_en
            else:
                en_obj = load_json(en_dir / f"{pad}.json")
                if not en_obj:
                    en_obj = {"source": "mn_dutt_1891", "status": "missing", "paragraphs": []}

            if en_obj.get("status") in ("ocr_unreviewed", "community_verified"):
                total_en_sargas += 1

            # Verses: merge existing hi* / community_verified, then apply hi_cache
            existing_verses = {
                v["n"]: v for v in existing.get("verses", []) if isinstance(v, dict) and "n" in v
            }
            merged_verses: list[dict[str, Any]] = []
            for v in sa_doc["verses"]:
                vn = int(v["n"])
                prev_v = existing_verses.get(vn, {})
                hi_val = None
                hi_source = "pending"
                hi_verified = False
                hi_flag = None

                if prev_v.get("hi_source") == "community_verified" and prev_v.get("hi"):
                    hi_val = prev_v["hi"]
                    hi_source = "community_verified"
                    hi_verified = bool(prev_v.get("hi_verified", True))
                    hi_flag = prev_v.get("hi_flag")
                else:
                    ckey, _ = hindi_cache_key(v["sa"])
                    if ckey in hi_cache:
                        crec = hi_cache[ckey]
                        hi_val = crec["hi"]
                        hi_source = "generated_from_pd_v1"
                        hi_verified = False
                        hi_flag = crec.get("hi_flag")
                    elif prev_v.get("hi") and prev_v.get("hi_source") != "pending":
                        hi_val = prev_v["hi"]
                        hi_source = prev_v.get("hi_source", "generated_from_pd_v1")
                        hi_verified = bool(prev_v.get("hi_verified", False))
                        hi_flag = prev_v.get("hi_flag")

                if hi_source != "pending" and hi_val is not None:
                    total_hi_gen += 1
                if hi_verified:
                    total_hi_ver += 1

                v_out: dict[str, Any] = {
                    "n": vn,
                    "sa": v["sa"],
                    "hi": hi_val,
                    "hi_source": hi_source,
                    "hi_verified": hi_verified,
                }
                if hi_flag:
                    v_out["hi_flag"] = hi_flag
                merged_verses.append(v_out)

            k_revids[pad] = int(sa_doc.get("revid", 0))
            sarga_doc = {
                "schema": 1,
                "kanda": kanda.n,
                "slug": kanda.slug,
                "sarga": sn,
                "sa_source": {
                    "site": "sa.wikisource.org",
                    "page": sa_doc["page"],
                    "revid": int(sa_doc.get("revid", 0)),
                },
                "en": en_obj,
                "verses": merged_verses,
            }
            dump_compact_json(out_file, sarga_doc)

            vc = len(merged_verses)
            k_verse_count += vc
            total_verses += vc
            total_sargas += 1

            k_sargas_index.append({
                "n": sn,
                "verses": vc,
                "en": en_obj["status"],
                "preview": make_preview(en_obj, sa_doc["verses"]),
            })

        revids_summary[kanda.slug] = k_revids
        index_kandas.append({
            "n": kanda.n,
            "slug": kanda.slug,
            "name_sa": kanda.name_sa,
            "name_iast": kanda.name_iast,
            "name_en": kanda.name_en,
            "name_hi": kanda.name_hi,
            "verse_count": k_verse_count,
            "sargas": k_sargas_index,
        })

    index_doc = {
        "schema": 1,
        "title": "Vālmīki Rāmāyaṇa",
        "kandas": index_kandas,
        "totals": {
            "sargas": total_sargas,
            "verses": total_verses,
            "hi_generated": total_hi_gen,
            "hi_verified": total_hi_ver,
            "en_sargas": total_en_sargas,
        },
    }
    dump_compact_json(DATA_DIR / "index.json", index_doc)

    dutt_sources = load_json(RAW_DIR / "dutt" / "sources.json", default={})
    provenance_doc = {
        "pipeline_version": __version__,
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sanskrit": {
            "site": "sa.wikisource.org",
            "sargas": total_sargas,
            "verses": total_verses,
            "revids": revids_summary,
        },
        "english": {
            "edition": "Manmatha Nath Dutt, The Ramayana Translated into English Prose (Calcutta, 1891-1894)",
            "volumes": dutt_sources,
        },
        "hindi": {
            "model_id": HINDI_MODEL_ID,
            "revision": HINDI_MODEL_REV,
            "hi_generated": total_hi_gen,
            "hi_verified": total_hi_ver,
        },
    }
    dump_pretty_json(DATA_DIR / "provenance.json", provenance_doc)
    print(
        f"[build] Built {total_sargas} sargas, {total_verses} verses "
        f"(en_sargas={total_en_sargas}, hi_generated={total_hi_gen}, hi_verified={total_hi_ver})"
    )
    return index_doc
