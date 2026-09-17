#!/usr/bin/env python3
"""Incrementally translate arXiv abstracts sentence by sentence.

This script is intentionally separate from HTML rendering so a slow translation
endpoint cannot block evidence collection. It can update the structured
translation cache and, when the report was written directly by the agent, patch
the final HTML's abstract blocks in place.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from render_report_from_packet import (
    FALLBACK_ITEMS,
    STRONG_RELATED_IDS,
    SUPPLEMENT_IDS,
    find_packet,
    norm_id,
    split_sentences,
)


PENDING_MARKERS = ("待补", "不可用", "未返回", "请运行", "QUERY LENGTH LIMIT EXCEEDED")
PLACEHOLDER_EN_MARKERS = ("Abstract sentence to be verified",)
MAX_TRANSLATION_CHARS = 450
LOCAL_MODEL_NAME = "Helsinki-NLP/opus-mt-en-zh"
_LOCAL_TRANSLATOR = None


GLOSSARY_REPLACEMENTS = {
    "愿景-语言-行动": "视觉-语言-动作",
    "视觉-语言-行动": "视觉-语言-动作",
    "视觉语言动作": "视觉-语言-动作",
    "世界行动模型": "世界-动作模型",
    "世界行动模式": "世界-动作模型",
    "政策": "策略",
    "实施例": "本体",
    "机器人操纵": "机器人操作",
    "实际世界": "真实世界",
    "法学硕士": "大语言模型",
}


def plain_text(node) -> str:
    clone = BeautifulSoup(str(node), "html.parser")
    for label in clone.select(".label"):
        label.decompose()
    return " ".join(clone.get_text(" ", strip=True).split())


def is_pending(text: str) -> bool:
    return (not text.strip()) or any(marker in text for marker in PENDING_MARKERS)


def normalize_translation(text: str) -> str:
    normalized = text
    for src, dst in GLOSSARY_REPLACEMENTS.items():
        normalized = normalized.replace(src, dst)
    return normalized


def is_placeholder_english(text: str) -> bool:
    return any(marker.lower() in text.lower() for marker in PLACEHOLDER_EN_MARKERS)


def chunk_sentence(sentence: str, limit: int = MAX_TRANSLATION_CHARS) -> list[str]:
    if len(sentence) <= limit:
        return [sentence]
    chunks: list[str] = []
    current = ""
    for piece in re.split(r"(?<=[,;:])\s+", sentence):
        if not current:
            current = piece
        elif len(current) + 1 + len(piece) <= limit:
            current = f"{current} {piece}"
        else:
            chunks.append(current)
            current = piece
    if current:
        chunks.append(current)
    final: list[str] = []
    for chunk in chunks:
        while len(chunk) > limit:
            final.append(chunk[:limit].rstrip())
            chunk = chunk[limit:].lstrip()
        if chunk:
            final.append(chunk)
    return final


def load_local_translator():
    global _LOCAL_TRANSLATOR
    if _LOCAL_TRANSLATOR is not None:
        return _LOCAL_TRANSLATOR
    from transformers import MarianMTModel, MarianTokenizer

    tokenizer = MarianTokenizer.from_pretrained(LOCAL_MODEL_NAME, local_files_only=True)
    model = MarianMTModel.from_pretrained(LOCAL_MODEL_NAME, local_files_only=True)
    model.eval()
    _LOCAL_TRANSLATOR = (tokenizer, model)
    return _LOCAL_TRANSLATOR


def translate_local(text: str) -> str:
    tokenizer, model = load_local_translator()
    inputs = tokenizer([text], return_tensors="pt", padding=True, truncation=True)
    output = model.generate(**inputs, max_new_tokens=256)
    translated = tokenizer.decode(output[0], skip_special_tokens=True).strip()
    if (not translated) or is_pending(translated):
        raise RuntimeError("empty or invalid local translation")
    return normalize_translation(translated)


def translate_online(text: str, timeout: int) -> str:
    google_error: Exception | None = None
    try:
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "en",
                "tl": "zh-CN",
                "dt": "t",
                "q": text,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        translated = "".join(part[0] for part in data[0] if part and part[0]).strip()
        if translated and not is_pending(translated):
            return normalize_translation(translated)
        raise RuntimeError("empty or invalid google translation")
    except Exception as exc:
        google_error = exc

    response = requests.get(
        "https://api.mymemory.translated.net/get",
        params={"q": text, "langpair": "en|zh-CN"},
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    translated = data.get("responseData", {}).get("translatedText", "").strip()
    status = data.get("responseStatus")
    if status and int(status) >= 400:
        raise RuntimeError(data.get("responseDetails") or f"translation status {status}")
    if (not translated) or is_pending(translated):
        raise RuntimeError(f"empty or invalid translation; google fallback failed: {google_error}")
    return normalize_translation(translated)


def translate_short(text: str, timeout: int, translator: str) -> str:
    local_error: Exception | None = None
    if translator in ("auto", "local"):
        try:
            return translate_local(text)
        except Exception as exc:
            local_error = exc
            if translator == "local":
                raise
    try:
        return translate_online(text, timeout)
    except Exception as exc:
        if local_error:
            raise RuntimeError(f"online translation failed after local fallback failed: {local_error}; {exc}") from exc
        raise


def translate_one(sentence: str, timeout: int, translator: str) -> str:
    chunks = chunk_sentence(sentence)
    if len(chunks) == 1:
        return translate_short(chunks[0], timeout, translator)
    return "".join(translate_short(chunk, timeout, translator) for chunk in chunks)


def fetch_arxiv_abstract(arxiv_id: str, timeout: int) -> str:
    """Fetch the canonical abstract for a single arXiv id."""
    api_url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    headers = {"User-Agent": "daily-paper-loop/1.0 (abstract repair)"}
    try:
        response = requests.get(api_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        match = re.search(
            r"<summary>\s*(.*?)\s*</summary>",
            response.text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if match:
            return html.unescape(re.sub(r"\s+", " ", match.group(1))).strip()
    except requests.RequestException:
        pass

    abs_url = f"https://arxiv.org/abs/{arxiv_id}"
    response = requests.get(abs_url, headers=headers, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    abstract = soup.select_one("blockquote.abstract")
    if not abstract:
        raise RuntimeError(f"missing arXiv abstract for {arxiv_id}")
    label = abstract.select_one(".descriptor")
    if label:
        label.decompose()
    return " ".join(abstract.get_text(" ", strip=True).split())


def set_labeled_text(soup: BeautifulSoup, div, label: str, text: str) -> None:
    div.clear()
    span = soup.new_tag("span", attrs={"class": "label"})
    span.string = label
    div.append(span)
    div.append(text)


def build_pair(soup: BeautifulSoup, index: int, sentence: str, translation: str):
    pair = soup.new_tag("div", attrs={"class": "abstract-pair"})
    en_div = soup.new_tag("div")
    zh_div = soup.new_tag("div")
    set_labeled_text(soup, en_div, f"EN {index}", sentence)
    set_labeled_text(soup, zh_div, f"ZH {index}", translation)
    pair.append(en_div)
    pair.append(zh_div)
    return pair


def arxiv_id_from_article(article) -> str | None:
    link = article.select_one('a[href*="arxiv.org/abs/"]')
    if not link:
        return None
    href = link.get("href", "")
    return norm_id(href)


def translate_cache(args: argparse.Namespace, root: Path) -> dict:
    packet_path = find_packet(root, args.date)
    if not packet_path.exists():
        return {"translated": 0, "failed": 0, "pending": 0, "skipped": 0}
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    by_id = {norm_id(item["id"]): item for item in packet["arxiv_candidates"]}
    by_id.update(FALLBACK_ITEMS)
    ids = [aid for aid in STRONG_RELATED_IDS + SUPPLEMENT_IDS if aid in by_id]

    cache_path = root / args.date[:7] / f"abstract-translations-{args.date}.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    translated_count = 0
    failed_count = 0
    skipped_count = 0
    sentence_budget = None if args.all else args.max_sentences
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
            if sentence_budget is not None and translated_count >= sentence_budget:
                break
            if not is_pending(zh[index]):
                skipped_count += 1
                continue
            if is_placeholder_english(sentence):
                failed_count += 1
                continue
            try:
                zh[index] = translate_one(sentence, args.timeout, args.translator)
                translated_count += 1
                print(f"cache translated {aid} #{index + 1}: {zh[index][:80]}")
            except Exception as exc:
                failed_count += 1
                print(f"cache failed {aid} #{index + 1}: {type(exc).__name__}: {exc}")
            record["zh"] = zh
            record["mode"] = "machine_translation" if all(not is_pending(item) for item in zh) else "partial_machine_translation"
            cache[aid] = record
            cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
            time.sleep(args.sleep)
        if sentence_budget is not None and translated_count >= sentence_budget:
            break

    expected_pending = 0
    for aid in ids:
        sentences = split_sentences(by_id[aid].get("summary", ""))
        record = cache.get(aid, {})
        zh = record.get("zh", [])
        expected_pending += sum(
            1
            for index in range(len(sentences))
            if index >= len(zh) or is_pending(zh[index])
        )
    return {
        "translated": translated_count,
        "failed": failed_count,
        "pending": expected_pending,
        "skipped": skipped_count,
    }


def find_latest_html(root: Path, date: str) -> Path | None:
    month_dir = root / date[:7]
    candidates = sorted(
        month_dir.glob(f"{date}-*.html"),
        key=lambda path: (path.stat().st_size, path.stat().st_mtime),
        reverse=True,
    )
    return candidates[0] if candidates else None


def translate_html(args: argparse.Namespace, root: Path) -> dict:
    html_path = Path(args.html_file) if args.html_file else find_latest_html(root, args.date)
    if not html_path:
        return {"translated": 0, "failed": 0, "pending": 0, "skipped": 0, "html_path": ""}

    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    translated_count = 0
    failed_count = 0
    skipped_count = 0
    changed = False
    sentence_budget = None if args.all else args.max_sentences

    for article in soup.select("article.paper"):
        detail_body = article.select_one("details .detail-body")
        if not detail_body:
            continue
        pairs = detail_body.select(".abstract-pair")
        english_sentences = []
        placeholder_found = False
        for pair in pairs:
            divs = pair.find_all("div", recursive=False)
            if len(divs) < 2:
                continue
            en_text = plain_text(divs[0])
            english_sentences.append(en_text)
            placeholder_found = placeholder_found or is_placeholder_english(en_text)

        if placeholder_found:
            aid = arxiv_id_from_article(article)
            if aid:
                try:
                    abstract = fetch_arxiv_abstract(aid, args.timeout)
                    english_sentences = split_sentences(abstract)
                    detail_body.clear()
                    for index, sentence in enumerate(english_sentences, 1):
                        detail_body.append(
                            build_pair(
                                soup,
                                index,
                                sentence,
                                "中文逐句翻译待补；请先对照左侧英文原文阅读。",
                            )
                        )
                    pairs = detail_body.select(".abstract-pair")
                    changed = True
                    if not args.dry_run:
                        html_path.write_text(str(soup), encoding="utf-8")
                    print(f"html repaired abstract {aid}: {len(english_sentences)} sentences")
                    time.sleep(args.sleep)
                except Exception as exc:
                    failed_count += 1
                    print(f"html failed to fetch abstract {aid}: {type(exc).__name__}: {exc}")

        for pair in pairs:
            if sentence_budget is not None and translated_count >= sentence_budget:
                break
            divs = pair.find_all("div", recursive=False)
            if len(divs) < 2:
                continue
            en_text = plain_text(divs[0])
            zh_text = plain_text(divs[1])
            if not is_pending(zh_text):
                skipped_count += 1
                continue
            if is_placeholder_english(en_text):
                failed_count += 1
                continue
            try:
                zh = translate_one(en_text, args.timeout, args.translator)
                label = divs[1].select_one(".label")
                label_text = label.get_text(strip=True) if label else "ZH"
                set_labeled_text(soup, divs[1], label_text, zh)
                translated_count += 1
                changed = True
                if not args.dry_run:
                    html_path.write_text(str(soup), encoding="utf-8")
                print(f"html translated #{translated_count}: {zh[:80]}")
            except Exception as exc:
                failed_count += 1
                print(f"html failed: {type(exc).__name__}: {exc}")
            time.sleep(args.sleep)
        if sentence_budget is not None and translated_count >= sentence_budget:
            break

    pending = 0
    for pair in soup.select(".abstract-pair"):
        divs = pair.find_all("div", recursive=False)
        if len(divs) >= 2 and is_pending(plain_text(divs[1])):
            pending += 1

    if changed and not args.dry_run:
        html_path.write_text(str(soup), encoding="utf-8")

    return {
        "translated": translated_count,
        "failed": failed_count,
        "pending": pending,
        "skipped": skipped_count,
        "html_path": str(html_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--source", choices=("cache", "html", "both"), default="both")
    parser.add_argument("--translator", choices=("auto", "local", "online"), default="auto")
    parser.add_argument("--html-file", help="Specific report HTML to patch. Defaults to the largest report for the date.")
    parser.add_argument("--all", action="store_true", help="Translate every pending sentence instead of stopping at --max-sentences.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-sentences", type=int, default=40)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=12)
    args = parser.parse_args()

    root = Path(args.root)
    started = time.monotonic()
    totals = {"translated": 0, "failed": 0, "pending": 0, "skipped": 0}
    if args.source in ("cache", "both"):
        stats = translate_cache(args, root)
        totals = {key: totals[key] + stats.get(key, 0) for key in totals}
    if args.source in ("html", "both"):
        stats = translate_html(args, root)
        totals = {key: totals[key] + stats.get(key, 0) for key in totals}
        if stats.get("html_path"):
            print(f"html_path={stats['html_path']}")

    elapsed = time.monotonic() - started
    print(
        "translated={translated} failed={failed} pending={pending} "
        "skipped={skipped} elapsed_seconds={elapsed:.2f}".format(
            elapsed=elapsed,
            **totals,
        )
    )
    return 1 if totals["pending"] or totals["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
