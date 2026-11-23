from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vr", description="Valmiki Ramayana data pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_fs = sub.add_parser("fetch-sa", help="Fetch Sanskrit Wikisource pages")
    p_fs.add_argument("--force", action="store_true")

    sub.add_parser("parse-sa", help="Parse Sanskrit Wikisource wikitext")

    p_fe = sub.add_parser("fetch-en", help="Fetch M.N. Dutt English OCR from Archive.org")
    p_fe.add_argument("--force", action="store_true")

    sub.add_parser("parse-en", help="Parse M.N. Dutt English OCR")

    p_hi = sub.add_parser("hindi", help="Generate Hindi drafts via IndicTrans2")
    p_hi.add_argument("--kanda", help="Filter by kanda slug (e.g. 01-bala)")
    p_hi.add_argument("--limit", type=int, help="Max uncached verses to process")
    p_hi.add_argument("--beams", type=int, default=4, help="Beam width (default 4)")

    sub.add_parser("build", help="Build data/ JSON files")

    args = parser.parse_args(argv)
    if args.cmd == "fetch-sa":
        from .fetch_sa import fetch_sa
        fetch_sa(force=args.force)
    elif args.cmd == "parse-sa":
        from .parse_sa import parse_sa
        parse_sa()
    elif args.cmd == "fetch-en":
        from .fetch_en import fetch_en
        fetch_en(force=args.force)
    elif args.cmd == "parse-en":
        from .parse_en import parse_en
        parse_en()
    elif args.cmd == "hindi":
        from .hindi import run_hindi
        run_hindi(kanda=args.kanda, limit=args.limit, num_beams=args.beams)
    elif args.cmd == "build":
        from .build import build_data
        build_data()
    return 0


if __name__ == "__main__":
    sys.exit(main())
