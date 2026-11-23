from __future__ import annotations

import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from .build import (
    HINDI_MODEL_ID,
    HINDI_MODEL_REV,
    hindi_cache_key,
    load_hindi_cache,
    normalize_sa_for_hindi,
)
from .common import CACHE_DIR, DATA_DIR, KANDAS, REPORTS_DIR, load_json


def is_suspect_hindi(hi: str, norm_sa: str) -> bool:
    if not hi.strip():
        return True
    ratio = len(hi) / max(len(norm_sa), 1)
    if ratio > 4.0 or ratio < 0.25:
        return True
    words = hi.split()
    if len(words) >= 6:
        trigrams = Counter(tuple(words[i : i + 3]) for i in range(len(words) - 2))
        if trigrams and trigrams.most_common(1)[0][1] > 3:
            return True
    return False


def clean_hindi_output(text: str) -> str:
    s = re.sub(r"\s+", " ", text).strip()
    if not s:
        return s
    if s[-1] not in ("।", "॥", "?", "!"):
        # Replace trailing ASCII period with Devanagari danda if present
        if s.endswith("."):
            s = s[:-1].rstrip() + " ।"
        else:
            s = s + " ।"
    return s


def write_hindi_report(
    total_verses: int,
    cache: dict[str, dict[str, Any]],
    verse_refs: list[tuple[str, str, str]],
    throughput_vps: float | None = None,
    num_beams: int | None = None,
) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generated = 0
    suspect_refs: list[tuple[str, str, str]] = []
    for ref, key, sa in verse_refs:
        rec = cache.get(key)
        if rec and rec.get("hi"):
            generated += 1
            if rec.get("hi_flag") == "suspect" and len(suspect_refs) < 15:
                suspect_refs.append((ref, sa.replace("\n", " "), rec["hi"]))

    suspect_total = sum(
        1 for _, key, _ in verse_refs if (cache.get(key) or {}).get("hi_flag") == "suspect"
    )
    lines = [
        "# Hindi Generation Report (IndicTrans2)",
        "",
        f"- Model ID: `{HINDI_MODEL_ID}`",
        f"- Pinned Revision: `{HINDI_MODEL_REV}`",
        f"- Direction: `san_Deva` -> `hin_Deva`",
        f"- Total corpus verses: **{total_verses}**",
        f"- Generated in cache: **{generated}** ({100 * generated / max(total_verses, 1):.1f}%)",
        f"- Flagged `suspect`: **{suspect_total}**",
    ]
    if num_beams is not None:
        lines.append(f"- Decoding: deterministic greedy/beam (`num_beams={num_beams}`, `do_sample=False`)")
    if throughput_vps is not None:
        lines.append(f"- Measured throughput: **{throughput_vps:.2f} verses/sec**")
    lines.extend(["", "## Sample Suspect Verses (up to 15)", ""])
    if suspect_refs:
        for ref, sa_line, hi_line in suspect_refs:
            lines.append(f"- **{ref}**: SA=`{sa_line[:80]}` -> HI=`{hi_line[:120]}`")
    else:
        lines.append("None.")
    (REPORTS_DIR / "hindi.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_hindi(
    kanda: str | None = None,
    limit: int | None = None,
    num_beams: int = 4,
    batch_size: int = 32,
    quantize: bool = False,
) -> dict[str, Any]:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    from IndicTransToolkit.processor import IndicProcessor

    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(8)

    cache_path = CACHE_DIR / "hi.jsonl"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = load_hindi_cache(cache_path)

    target_kandas = [km for km in KANDAS if kanda is None or km.slug == kanda]
    if not target_kandas:
        raise ValueError(f"Unknown kanda slug: {kanda}")

    all_refs: list[tuple[str, str, str]] = []
    todo_by_key: dict[str, tuple[str, str]] = {}  # key -> (ref, norm_sa)
    total_verses = 0

    for km in target_kandas:
        sa_dir = CACHE_DIR / "sa" / km.slug
        for sf in sorted(sa_dir.glob("*.json")):
            sa_doc = load_json(sf)
            sn = int(sa_doc["sarga"])
            data_doc = load_json(DATA_DIR / km.slug / f"{sn:03d}.json", default={}) or {}
            verified_nums = {
                v["n"]
                for v in data_doc.get("verses", [])
                if v.get("hi_source") == "community_verified"
            }
            for v in sa_doc["verses"]:
                total_verses += 1
                vn = int(v["n"])
                ref = f"{km.n}.{sn}.{vn}"
                key, norm_sa = hindi_cache_key(v["sa"])
                all_refs.append((ref, key, v["sa"]))
                if vn in verified_nums:
                    continue
                if key in cache or key in todo_by_key:
                    continue
                todo_by_key[key] = (ref, norm_sa)

    todo_items = [(key, ref, norm_sa) for key, (ref, norm_sa) in todo_by_key.items()]
    if limit is not None:
        todo_items = todo_items[:limit]

    # Sort by input length to minimize batch padding overhead
    todo_items.sort(key=lambda item: len(item[2]))
    print(
        f"[hindi] Target verses={total_verses}, already cached={len(all_refs) - len(todo_by_key)}, "
        f"to generate={len(todo_items)} (beams={num_beams}, batch={batch_size}, quantize={quantize})"
    )

    if not todo_items:
        write_hindi_report(total_verses, cache, all_refs, num_beams=num_beams)
        return {"generated_now": 0, "total_cached": len(cache)}

    tokenizer = AutoTokenizer.from_pretrained(
        HINDI_MODEL_ID,
        revision=HINDI_MODEL_REV,
        trust_remote_code=True,
    )
    model = AutoModelForSeq2SeqLM.from_pretrained(
        HINDI_MODEL_ID,
        revision=HINDI_MODEL_REV,
        trust_remote_code=True,
    )
    model.eval()
    if quantize:
        model = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)

    ip = IndicProcessor(inference=True)

    t0 = time.monotonic()
    done_now = 0
    with cache_path.open("a", encoding="utf-8") as fout, torch.inference_mode():
        for i in range(0, len(todo_items), batch_size):
            batch = todo_items[i : i + batch_size]
            raw_texts = [norm_sa for _, _, norm_sa in batch]
            prepped = ip.preprocess_batch(raw_texts, src_lang="san_Deva", tgt_lang="hin_Deva")
            inputs = tokenizer(
                prepped,
                truncation=True,
                padding="longest",
                max_length=256,
                return_tensors="pt",
            )
            generated_tokens = model.generate(
                **inputs,
                use_cache=True,
                num_beams=num_beams,
                do_sample=False,
                repetition_penalty=1.2,
                no_repeat_ngram_size=3,
                max_new_tokens=256,
            )
            with tokenizer.as_target_tokenizer():
                decoded = tokenizer.batch_decode(
                    generated_tokens.detach().cpu().tolist(),
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=True,
                )
            post = ip.postprocess_batch(decoded, lang="hin_Deva")

            for (key, ref, norm_sa), hi_raw in zip(batch, post):
                hi_clean = clean_hindi_output(hi_raw)
                flag = "suspect" if is_suspect_hindi(hi_clean, norm_sa) else None
                rec: dict[str, Any] = {"key": key, "hi": hi_clean}
                if flag:
                    rec["hi_flag"] = flag
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                cache[key] = rec
            fout.flush()

            done_now += len(batch)
            elapsed = max(time.monotonic() - t0, 1e-6)
            vps = done_now / elapsed
            eta_min = (len(todo_items) - done_now) / vps / 60.0 if vps > 0 else 0.0
            print(
                f"[hindi] {done_now}/{len(todo_items)} ({100*done_now/len(todo_items):.1f}%) | "
                f"{vps:.2f} verses/s | ETA {eta_min:.1f} min",
                flush=True,
            )

    total_elapsed = max(time.monotonic() - t0, 1e-6)
    vps_final = done_now / total_elapsed
    write_hindi_report(total_verses, cache, all_refs, throughput_vps=vps_final, num_beams=num_beams)
    print(f"[hindi] Finished {done_now} verses in {total_elapsed:.1f}s ({vps_final:.2f} verses/s)")
    return {"generated_now": done_now, "vps": vps_final}
