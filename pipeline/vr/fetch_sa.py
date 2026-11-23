from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

import requests

from .common import (
    KANDAS,
    RAW_DIR,
    deva_to_int,
    dump_pretty_json,
    load_json,
)

API_URL = "https://sa.wikisource.org/w/api.php"
USER_AGENT = "valmiki-ramayana-reader/0.1 (https://github.com/csy20/valmiki-ramayana)"
SARGA_TITLE_RE = re.compile(r"^रामायणम्/([^/]+)/सर्गः\s+([०-९]+)$")


def api_request(session: requests.Session, params: dict[str, Any], method: str = "GET") -> dict[str, Any]:
    req_params = {"format": "json", "maxlag": 5, **params}
    last_err: Exception | None = None
    for attempt in range(5):
        if attempt > 0:
            time.sleep(2 ** attempt)
        try:
            if method == "POST":
                resp = session.post(API_URL, data=req_params, timeout=30)
            else:
                resp = session.get(API_URL, params=req_params, timeout=30)
            if resp.status_code == 429 or resp.status_code >= 500:
                last_err = RuntimeError(f"HTTP {resp.status_code}")
                continue
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]!r}")
            try:
                data = resp.json()
            except Exception:
                last_err = RuntimeError(f"Non-JSON response ({resp.status_code}): {resp.text[:200]!r}")
                continue
            if "error" in data:
                err_code = data["error"].get("code", "")
                if err_code == "maxlag" or "rate" in err_code:
                    last_err = RuntimeError(f"MediaWiki error: {data['error']}")
                    continue
                raise RuntimeError(f"MediaWiki API error: {data['error']}")
            return data
        except requests.RequestException as exc:
            last_err = exc
    raise RuntimeError(f"Failed MediaWiki API call after retries: {last_err}")


def list_kanda_sargas(session: requests.Session, kanda_name_sa: str) -> list[tuple[int, str]]:
    prefix = f"रामायणम्/{kanda_name_sa}/"
    pages: list[tuple[int, str]] = []
    apcontinue: str | None = None
    while True:
        params: dict[str, Any] = {
            "action": "query",
            "list": "allpages",
            "apprefix": prefix,
            "aplimit": "max",
        }
        if apcontinue:
            params["apcontinue"] = apcontinue
        data = api_request(session, params, method="GET")
        for item in data.get("query", {}).get("allpages", []):
            title = item["title"]
            m = SARGA_TITLE_RE.match(title)
            if m and m.group(1) == kanda_name_sa:
                sarga_n = deva_to_int(m.group(2))
                pages.append((sarga_n, title))
        cont = data.get("continue", {})
        if "apcontinue" in cont:
            apcontinue = cont["apcontinue"]
            time.sleep(1.0)
        else:
            break
    pages.sort(key=lambda x: x[0])
    return pages


def fetch_revisions_batch(session: requests.Session, titles: list[str]) -> dict[str, tuple[int, str]]:
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content|ids",
        "rvslots": "main",
        "titles": "|".join(titles),
    }
    data = api_request(session, params, method="POST")
    results: dict[str, tuple[int, str]] = {}
    for page in data.get("query", {}).get("pages", {}).values():
        if "missing" in page:
            continue
        title = page["title"]
        revs = page.get("revisions", [])
        if not revs:
            continue
        rev = revs[0]
        revid = int(rev["revid"])
        slots = rev.get("slots", {})
        content = slots.get("main", {}).get("*", "")
        results[title] = (revid, content)
    return results


def fetch_sa(force: bool = False) -> dict[str, Any]:
    out_root = RAW_DIR / "wikisource"
    out_root.mkdir(parents=True, exist_ok=True)
    revids_path = out_root / "revids.json"
    revids: dict[str, Any] = load_json(revids_path, default={}) if not force else {}

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    summary: dict[str, int] = {}
    for kanda in KANDAS:
        kdir = out_root / kanda.slug
        kdir.mkdir(parents=True, exist_ok=True)
        pages = list_kanda_sargas(session, kanda.name_sa)
        time.sleep(1.0)
        summary[kanda.slug] = len(pages)

        existing_k = revids.setdefault(kanda.slug, {})
        to_fetch: list[tuple[int, str]] = []
        for sarga_n, title in pages:
            wfile = kdir / f"{sarga_n:03d}.wiki"
            key = f"{sarga_n:03d}"
            if not force and wfile.exists() and key in existing_k:
                continue
            to_fetch.append((sarga_n, title))

        for i in range(0, len(to_fetch), 50):
            batch = to_fetch[i : i + 50]
            titles = [t for _, t in batch]
            fetched = fetch_revisions_batch(session, titles)
            for sarga_n, title in batch:
                if title not in fetched:
                    raise RuntimeError(f"Missing revision content for {title}")
                revid, content = fetched[title]
                wfile = kdir / f"{sarga_n:03d}.wiki"
                wfile.write_text(content, encoding="utf-8")
                existing_k[f"{sarga_n:03d}"] = {
                    "sarga": sarga_n,
                    "title": title,
                    "revid": revid,
                }
            dump_pretty_json(revids_path, revids)
            time.sleep(1.0)

        print(f"[fetch-sa] {kanda.slug}: {len(pages)} sargas (fetched {len(to_fetch)})")

    dump_pretty_json(revids_path, revids)
    return summary
