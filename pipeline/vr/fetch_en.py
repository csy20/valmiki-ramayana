from __future__ import annotations

import time
import urllib.parse
from pathlib import Path
from typing import Any

import requests

from .common import RAW_DIR, dump_pretty_json, load_json, sha256_file

USER_AGENT = "valmiki-ramayana-reader/0.1 (https://github.com/csy20/valmiki-ramayana)"

DUTT_VOLUMES: list[dict[str, str]] = [
    {
        "key": "vol1_2",
        "filename": "vol1_2_bala_ayodhya.txt",
        "ia_item": "Valmiki_Ramayana_English_Prose_Translation_7_volumes_by_Manmatha_Nath_Dutt_1891_to_1894",
        "ia_file": "Valmiki Ramayana - MN Dutt - Volume 1 & 2 - Bala & Ayodhya Kandas 1891_djvu.txt",
        "years": "1891",
    },
    {
        "key": "vol3_5",
        "filename": "vol3_5_aranya_kishkindha_sundara.txt",
        "ia_item": "Valmiki_Ramayana_English_Prose_Translation_7_volumes_by_Manmatha_Nath_Dutt_1891_to_1894",
        "ia_file": "Valmiki Ramayana - MN Dutt - Volume 3 to 5 - Aranya, Kishkandha & Sundara Kandas 1891_djvu.txt",
        "years": "1891–1892",
    },
    {
        "key": "vol6",
        "filename": "vol6_yuddha.txt",
        "ia_item": "Valmiki_Ramayana_English_Prose_Translation_7_volumes_by_Manmatha_Nath_Dutt_1891_to_1894",
        "ia_file": "Valmiki Ramayana - MN Dutt - Volume 6 - Yuddha Kanda 1893_djvu.txt",
        "years": "1893",
    },
    {
        "key": "vol7",
        "filename": "vol7_uttara.txt",
        "ia_item": "in.ernet.dli.2015.277390",
        "ia_file": "2015.277390.368_W_O_djvu.txt",
        "years": "1894",
    },
]


def download_with_retries(session: requests.Session, url: str) -> bytes:
    last_err: Exception | None = None
    for attempt in range(5):
        if attempt > 0:
            time.sleep(2 ** attempt)
        try:
            resp = session.get(url, timeout=(15, 30))
            if resp.status_code == 429 or resp.status_code >= 500:
                last_err = RuntimeError(f"HTTP {resp.status_code} from {resp.url}")
                continue
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:
            last_err = exc
    raise RuntimeError(f"Failed download {url}: {last_err}")


def fetch_en(force: bool = False) -> dict[str, Any]:
    out_dir = RAW_DIR / "dutt"
    out_dir.mkdir(parents=True, exist_ok=True)
    sources_path = out_dir / "sources.json"
    sources: dict[str, Any] = load_json(sources_path, default={}) if not force else {}

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for vol in DUTT_VOLUMES:
        dest = out_dir / vol["filename"]
        url = f"https://archive.org/download/{vol['ia_item']}/{urllib.parse.quote(vol['ia_file'])}"
        if force or not dest.exists():
            print(f"[fetch-en] Downloading {vol['ia_item']}/{vol['ia_file']}...")
            dest.write_bytes(download_with_retries(session, url))
        sources[vol["key"]] = {
            "ia_item": vol["ia_item"],
            "ia_file": vol["ia_file"],
            "url": url,
            "local_file": vol["filename"],
            "years": vol["years"],
            "bytes": dest.stat().st_size,
            "sha256": sha256_file(dest),
        }
        print(f"[fetch-en] {vol['key']}: {dest.stat().st_size} bytes (sha256={sources[vol['key']]['sha256'][:12]})")

    dump_pretty_json(sources_path, sources)
    return sources
