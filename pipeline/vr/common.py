from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PIPELINE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = PIPELINE_DIR.parent
RAW_DIR = PIPELINE_DIR / "raw"
CACHE_DIR = PIPELINE_DIR / "cache"
OVERRIDES_DIR = PIPELINE_DIR / "overrides"
REPORTS_DIR = PIPELINE_DIR / "reports"
DATA_DIR = REPO_DIR / "data"

DEVA_TO_ASCII = str.maketrans("०१२३४५६७८९", "0123456789")
ASCII_TO_DEVA = str.maketrans("0123456789", "०१२३४५६७८९")


@dataclass(frozen=True)
class KandaMeta:
    n: int
    slug: str
    name_sa: str
    name_iast: str
    name_en: str
    name_hi: str
    short_en: str


KANDAS: tuple[KandaMeta, ...] = (
    KandaMeta(1, "01-bala", "बालकाण्डम्", "Bālakāṇḍa", "Bala Kanda", "बालकाण्ड", "Bala"),
    KandaMeta(2, "02-ayodhya", "अयोध्याकाण्डम्", "Ayodhyākāṇḍa", "Ayodhya Kanda", "अयोध्याकाण्ड", "Ayodhya"),
    KandaMeta(3, "03-aranya", "अरण्यकाण्डम्", "Araṇyakāṇḍa", "Aranya Kanda", "अरण्यकाण्ड", "Aranya"),
    KandaMeta(4, "04-kishkindha", "किष्किन्धाकाण्डम्", "Kiṣkindhākāṇḍa", "Kishkindha Kanda", "किष्किन्धाकाण्ड", "Kishkindha"),
    KandaMeta(5, "05-sundara", "सुन्दरकाण्डम्", "Sundarakāṇḍa", "Sundara Kanda", "सुन्दरकाण्ड", "Sundara"),
    KandaMeta(6, "06-yuddha", "युद्धकाण्डम्", "Yuddhakāṇḍa", "Yuddha Kanda", "युद्धकाण्ड", "Yuddha"),
    KandaMeta(7, "07-uttara", "उत्तरकाण्डम्", "Uttarakāṇḍa", "Uttara Kanda", "उत्तरकाण्ड", "Uttara"),
)

KANDA_BY_SLUG: dict[str, KandaMeta] = {k.slug: k for k in KANDAS}
KANDA_BY_N: dict[int, KandaMeta] = {k.n: k for k in KANDAS}


def deva_to_int(s: str) -> int:
    return int(s.strip().translate(DEVA_TO_ASCII))


def int_to_deva(n: int) -> str:
    return str(n).translate(ASCII_TO_DEVA)


def dump_compact_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")


def dump_pretty_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
