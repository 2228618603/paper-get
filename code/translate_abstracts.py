#!/usr/bin/env python3
"""Incrementally translate cached arXiv abstracts sentence by sentence.

This script is intentionally separate from HTML rendering so a slow public
translation endpoint cannot block the daily report. It updates
`YYYY-MM/abstract-translations-YYYY-MM-DD.json` in place and can be rerun.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests

from render_report_from_packet import (
    FALLBACK_ITEMS,
    STRONG_RELATED_IDS,
    SUPPLEMENT_IDS,
    find_packet,
    norm_id,
    split_sentences,
)


PENDING_MARKERS = ("待补", "不可用", "未返回")


def is_pending(text: str) -> bool:
    return (not text.strip()) or any(marker in text for marker in PENDING_MARKERS)


def translate_one(sentence: str, timeout: int) -> str:
    response = requests.get(
        "https://api.mymemory.translated.net/get",
        params={"q": sentence, "langpair": "en|zh-CN"},
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    translated = data.get("responseData", {}).get("translatedText", "").strip()
    if not translated:
        raise RuntimeError("empty translation")
    return translated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--max-sentences", type=int, default=40)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=12)
    args = parser.parse_args()

    root = Path(args.root)
    packet = json.loads(find_packet(root, args.date).read_text(encoding="utf-8"))
    by_id = {norm_id(item["id"]): item for item in packet["arxiv_candidates"]}
    by_id.update(FALLBACK_ITEMS)
    ids = [aid for aid in STRONG_RELATED_IDS + SUPPLEMENT_IDS if aid in by_id]

    cache_path = root / args.date[:7] / f"abstract-translations-{args.date}.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    translated_count = 0
    failed_count = 0
    for aid in ids:
        sentences = split_sentences(by_id[aid].get("summary", ""))
        record = cache.get(aid, {})
        if record.get("en") != sentences:
            record = {
                "en": sentences,
                "zh": ["中文逐句翻译待补；请先对照左侧英文原文阅读。" for _ in sentences],
                "mode": "pending_translation",
            }
        zh = list(record.get("zh", []))
        while len(zh) < len(sentences):
            zh.append("中文逐句翻译待补；请先对照左侧英文原文阅读。")

        for index, sentence in enumerate(sentences):
            if translated_count >= args.max_sentences:
                break
            if not is_pending(zh[index]):
                continue
            try:
                zh[index] = translate_one(sentence, args.timeout)
                translated_count += 1
                print(f"translated {aid} #{index + 1}: {zh[index][:80]}")
            except Exception as exc:
                failed_count += 1
                print(f"failed {aid} #{index + 1}: {type(exc).__name__}: {exc}")
            record["zh"] = zh
            record["mode"] = "machine_translation" if all(not is_pending(item) for item in zh) else "partial_machine_translation"
            cache[aid] = record
            cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
            time.sleep(args.sleep)
        if translated_count >= args.max_sentences:
            break

    pending = sum(is_pending(item) for record in cache.values() for item in record.get("zh", []))
    print(f"translated={translated_count} failed={failed_count} pending={pending}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
