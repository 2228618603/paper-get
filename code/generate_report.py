#!/usr/bin/env python3
"""Collect a HF-first research packet for the daily embodied-AI report.

The packet is evidence for the writing agent. Hugging Face Papers is the
primary discovery source because it exposes paper metadata plus project/GitHub
signals. arXiv remains a fallback and abstract-enrichment source.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

DEFAULT_HF_BASE = "https://huggingface.co"
DEFAULT_HF_MIRROR_BASE = "https://hf-mirror.com"

STRONG_PATTERNS = (
    "vision-language-action",
    "vision language action",
    "vla",
    "world-action",
    "world action",
    "wam",
    "robot foundation model",
    "embodied foundation",
    "self-improvement",
    "self improving",
    "self-evolving",
    "robot data",
    "mobile manipulation",
    "humanoid",
    "whole-body",
    "real robot",
)

SUPPLEMENT_PATTERNS = (
    "tactile",
    "force",
    "dexterous",
    "gripper",
    "hand",
    "simulation",
    "simulator",
    "benchmark",
    "dataset",
    "teleoperation",
    "hardware",
    "safety",
    "deployment",
    "inference",
)


def fetch_json(url: str, timeout: int, retries: int, sleep: float) -> Any:
    last_error: Exception | None = None
    headers = {
        "User-Agent": "paper-get/0.2 (daily research workflow)",
        "Accept": "application/json,*/*;q=0.5",
    }
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(sleep * (attempt + 1))
    raise RuntimeError(f"{type(last_error).__name__}: {last_error}")


def fetch_text(url: str, timeout: int, retries: int, sleep: float) -> str:
    last_error: Exception | None = None
    headers = {
        "User-Agent": "paper-get/0.2 (daily research workflow)",
        "Accept": "text/html,application/xml;q=0.9,*/*;q=0.5",
    }
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response.text
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(sleep * (attempt + 1))
    raise RuntimeError(f"{type(last_error).__name__}: {last_error}")


def date_range(start: dt.datetime, end: dt.datetime) -> list[str]:
    cursor = start.date()
    final = end.date()
    days: list[str] = []
    while cursor <= final:
        days.append(cursor.isoformat())
        cursor += dt.timedelta(days=1)
    return days


def parse_datetime(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(normalized)
    except ValueError:
        try:
            return dt.datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
        except ValueError:
            return None


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def norm_arxiv_id(value: str | None) -> str:
    if not value:
        return ""
    raw = value.strip()
    raw = raw.split("/abs/")[-1].split("/pdf/")[-1]
    raw = raw.removesuffix(".pdf")
    match = re.search(r"(\d{4}\.\d{4,5})(?:v\d+)?", raw)
    return match.group(1) if match else raw.split("v")[0]


def entry_key(entry: dict) -> str:
    arxiv_id = entry.get("arxiv_id") or norm_arxiv_id(entry.get("id"))
    if arxiv_id:
        return f"arxiv:{arxiv_id}"
    return f"title:{normalize_title(entry.get('title', ''))}"


def extract_author_names(authors: Any) -> list[str]:
    names: list[str] = []
    for author in authors or []:
        if isinstance(author, str):
            name = author
        else:
            name = author.get("name") or author.get("user", {}).get("fullname") or ""
        if name:
            names.append(" ".join(str(name).split()))
    return names


def paper_url(arxiv_id: str, hf_url: str | None = None) -> str:
    if arxiv_id:
        return f"https://arxiv.org/abs/{arxiv_id}"
    return hf_url or ""


def normalize_hf_item(raw: dict, source: str, query: str | None = None) -> dict:
    paper = raw.get("paper", raw)
    arxiv_id = norm_arxiv_id(paper.get("id"))
    hf_url = f"https://huggingface.co/papers/{arxiv_id}" if arxiv_id else ""
    links = [item for item in [hf_url, paper.get("projectPage"), paper.get("githubRepo")] if item]
    return {
        "title": " ".join((paper.get("title") or raw.get("title") or "").split()),
        "summary": " ".join((paper.get("summary") or raw.get("summary") or "").split()),
        "published": paper.get("publishedAt") or raw.get("publishedAt") or "",
        "id": paper_url(arxiv_id, hf_url),
        "arxiv_id": arxiv_id,
        "authors": extract_author_names(paper.get("authors")),
        "comments": [],
        "links": links,
        "source_platforms": [source],
        "discovery_query": query,
        "hf": {
            "url": hf_url,
            "upvotes": paper.get("upvotes") or 0,
            "num_comments": raw.get("numComments") or paper.get("numComments") or 0,
            "discussion_id": paper.get("discussionId"),
            "submitted_on_daily_at": paper.get("submittedOnDailyAt"),
            "github_repo": paper.get("githubRepo"),
            "github_stars": paper.get("githubStars"),
            "project_page": paper.get("projectPage"),
            "organization": paper.get("organization") or raw.get("organization"),
        },
        "project_page": paper.get("projectPage"),
        "github_repo": paper.get("githubRepo"),
        "github_stars": paper.get("githubStars"),
    }


def parse_arxiv_entry(entry: ET.Element) -> dict:
    title = " ".join((entry.findtext("atom:title", default="", namespaces=ARXIV_NS)).split())
    summary = " ".join((entry.findtext("atom:summary", default="", namespaces=ARXIV_NS)).split())
    published = entry.findtext("atom:published", default="", namespaces=ARXIV_NS)
    identifier = entry.findtext("atom:id", default="", namespaces=ARXIV_NS).replace("http://", "https://")
    arxiv_id = norm_arxiv_id(identifier)
    authors = [
        name.text.strip()
        for name in entry.findall("atom:author/atom:name", ARXIV_NS)
        if name.text
    ]
    comments = [
        " ".join(comment.text.split())
        for comment in entry.findall("arxiv:comment", ARXIV_NS)
        if comment.text
    ]
    links = [
        link.attrib.get("href", "").replace("http://", "https://")
        for link in entry.findall("atom:link", ARXIV_NS)
        if link.attrib.get("href")
    ]
    return {
        "title": title,
        "summary": summary,
        "published": published,
        "id": identifier,
        "arxiv_id": arxiv_id,
        "authors": authors,
        "comments": comments,
        "links": links,
        "source_platforms": ["arxiv_api"],
    }


def query_arxiv(category: str, start: dt.datetime, end: dt.datetime, timeout: int, retries: int) -> list[dict]:
    query = (
        f"cat:{category} AND submittedDate:"
        f"[{start.strftime('%Y%m%d%H%M')} TO {end.strftime('%Y%m%d%H%M')}]"
    )
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": 0,
            "max_results": 120,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    url = f"https://export.arxiv.org/api/query?{params}"
    text = fetch_text(url, timeout=timeout, retries=retries, sleep=2.0)
    root = ET.fromstring(text)
    return [parse_arxiv_entry(entry) for entry in root.findall("atom:entry", ARXIV_NS)]


def collect_hf_daily(
    api_bases: list[str],
    start: dt.datetime,
    end: dt.datetime,
    timeout: int,
    retries: int,
    source_health: list[dict],
    errors: list[str],
) -> list[dict]:
    entries: list[dict] = []
    for date_value in date_range(start, end):
        for base in api_bases:
            url = f"{base.rstrip('/')}/api/daily_papers?{urllib.parse.urlencode({'date': date_value})}"
            try:
                data = fetch_json(url, timeout=timeout, retries=retries, sleep=1.0)
                day_entries = [normalize_hf_item(item, "huggingface_daily", date_value) for item in data]
                entries.extend(day_entries)
                source_health.append(
                    {
                        "source": "huggingface_daily",
                        "base": base,
                        "date": date_value,
                        "status": "ok",
                        "count": len(day_entries),
                    }
                )
                break
            except Exception as exc:
                errors.append(f"hf daily {base} {date_value}: {exc}")
                source_health.append(
                    {
                        "source": "huggingface_daily",
                        "base": base,
                        "date": date_value,
                        "status": "error",
                        "error": str(exc),
                    }
                )
    return entries


def collect_hf_search(
    api_bases: list[str],
    queries: list[str],
    start: dt.datetime,
    end: dt.datetime,
    timeout: int,
    retries: int,
    per_query_limit: int,
    source_health: list[dict],
    errors: list[str],
) -> list[dict]:
    entries: list[dict] = []
    for query in queries:
        for base in api_bases:
            url = f"{base.rstrip('/')}/api/papers/search?{urllib.parse.urlencode({'q': query})}"
            try:
                data = fetch_json(url, timeout=timeout, retries=retries, sleep=1.0)
                query_entries: list[dict] = []
                for raw in data[:per_query_limit]:
                    item = normalize_hf_item(raw, "huggingface_search", query)
                    published = parse_datetime(item.get("published"))
                    if published and not (start - dt.timedelta(days=1) <= published <= end + dt.timedelta(days=1)):
                        continue
                    query_entries.append(item)
                entries.extend(query_entries)
                source_health.append(
                    {
                        "source": "huggingface_search",
                        "base": base,
                        "query": query,
                        "status": "ok",
                        "count": len(query_entries),
                        "raw_count": len(data),
                    }
                )
                break
            except Exception as exc:
                errors.append(f"hf search {base} {query}: {exc}")
                source_health.append(
                    {
                        "source": "huggingface_search",
                        "base": base,
                        "query": query,
                        "status": "error",
                        "error": str(exc),
                    }
                )
    return entries


def collect_official_news(
    urls: list[str],
    keywords: list[str],
    timeout: int,
    retries: int,
    limit: int,
    source_health: list[dict],
    errors: list[str],
) -> list[dict]:
    news: list[dict] = []
    escaped = [re.escape(k) for k in keywords if len(k) >= 3]
    keyword_pattern = re.compile("|".join(escaped), re.I) if escaped else None
    for url in urls:
        try:
            text = fetch_text(url, timeout=timeout, retries=retries, sleep=1.0)
            soup = BeautifulSoup(text, "html.parser")
            page_title = soup.title.get_text(" ", strip=True) if soup.title else url
            description = ""
            meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if meta and meta.get("content"):
                description = " ".join(meta["content"].split())
            candidates = []
            for link in soup.find_all("a", href=True):
                label = " ".join(link.get_text(" ", strip=True).split())
                href = urllib.parse.urljoin(url, link["href"])
                if len(label) < 8:
                    continue
                if keyword_pattern and keyword_pattern.search(f"{label} {href}"):
                    candidates.append({"title": label[:180], "url": href})
                if len(candidates) >= limit:
                    break
            news.append(
                {
                    "source_url": url,
                    "page_title": page_title,
                    "description": description,
                    "keyword_links": candidates,
                }
            )
            source_health.append({"source": "official_news_page", "url": url, "status": "ok", "count": len(candidates)})
        except Exception as exc:
            errors.append(f"official page {url}: {exc}")
            source_health.append({"source": "official_news_page", "url": url, "status": "error", "error": str(exc)})
    return news


def merge_entries(entries: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for entry in entries:
        if not entry.get("title"):
            continue
        key = entry_key(entry)
        if not key:
            continue
        if key not in merged:
            merged[key] = entry
            continue
        current = merged[key]
        for field in ("summary", "published", "id", "arxiv_id", "project_page", "github_repo", "github_stars"):
            if not current.get(field) and entry.get(field):
                current[field] = entry[field]
        current["authors"] = list(dict.fromkeys(current.get("authors", []) + entry.get("authors", [])))
        current["comments"] = list(dict.fromkeys(current.get("comments", []) + entry.get("comments", [])))
        current["links"] = list(dict.fromkeys(current.get("links", []) + entry.get("links", [])))
        current["source_platforms"] = list(dict.fromkeys(current.get("source_platforms", []) + entry.get("source_platforms", [])))
        if entry.get("hf"):
            current.setdefault("hf", {}).update({k: v for k, v in entry["hf"].items() if v is not None})
        if entry.get("discovery_query"):
            current.setdefault("discovery_queries", [])
            current["discovery_queries"].append(entry["discovery_query"])
    return list(merged.values())


def score(entry: dict, config: dict, end: dt.datetime) -> tuple[int, list[str], str]:
    text = " ".join(
        [
            entry.get("title", ""),
            entry.get("summary", ""),
            " ".join(entry.get("comments", [])),
            " ".join(entry.get("authors", [])),
            entry.get("project_page") or "",
            entry.get("github_repo") or "",
        ]
    ).lower()
    points = 0
    reasons: list[str] = []
    for keyword in config.get("keywords", []):
        lower = keyword.lower()
        if lower in text:
            gain = 4 if lower in entry.get("title", "").lower() else 2
            points += gain
            reasons.append(f"keyword:{keyword}")
    for pattern in STRONG_PATTERNS:
        if pattern in text:
            points += 5
            reasons.append(f"strong:{pattern}")
    for pattern in SUPPLEMENT_PATTERNS:
        if pattern in text:
            points += 2
            reasons.append(f"supplement:{pattern}")
    if re.search(r"\b(real[- ]world|real[- ]robot|hardware|physical robot|robot)\b", text):
        points += 4
        reasons.append("evidence:real_robot_or_hardware_term")
    if entry.get("github_repo"):
        points += 5
        reasons.append("evidence:github_repo")
    elif re.search(r"\b(code|github|repository|project page)\b", text) or entry.get("project_page"):
        points += 2
        reasons.append("evidence:project_or_code_term")
    hf = entry.get("hf", {})
    upvotes = int(hf.get("upvotes") or 0)
    stars = int(hf.get("github_stars") or 0)
    if upvotes:
        points += min(8, int(math.log2(upvotes + 1)) + 1)
        reasons.append(f"hf_upvotes:{upvotes}")
    if stars:
        points += min(6, int(math.log10(stars + 1)) + 1)
        reasons.append(f"github_stars:{stars}")
    for watched in config.get("companies", []) + config.get("academic_watch", []):
        if watched.lower() in text:
            points += 6
            reasons.append(f"watchlist:{watched}")
    published = parse_datetime(entry.get("published"))
    if published:
        published_utc = published.astimezone(dt.timezone.utc)
        end_utc = end.astimezone(dt.timezone.utc)
        age_days = max(0, (end_utc - published_utc).days)
        if age_days <= 3:
            points += 4
            reasons.append("fresh:3d")
        elif age_days <= 7:
            points += 2
            reasons.append("fresh:7d")
    strong = any(reason.startswith("strong:") for reason in reasons)
    supplement = any(reason.startswith("supplement:") for reason in reasons)
    bucket = "strong_related" if strong else "supplement" if supplement else "other_ai"
    return points, reasons, bucket


def read_seen_keys(root: Path, date: str) -> set[str]:
    seen_path = root / date[:7] / f"seen-{date[:7]}.md"
    if not seen_path.exists():
        return set()
    text = seen_path.read_text(encoding="utf-8")
    keys = set()
    for match in re.finditer(r"https://arxiv\.org/abs/(\d{4}\.\d{4,5})(?:v\d+)?", text):
        keys.add(f"arxiv:{match.group(1)}")
    for line in text.splitlines():
        if "|" in line:
            title = line.split("|", 1)[0].lstrip("- ").strip()
            if title:
                keys.add(f"title:{normalize_title(title)}")
    return keys


def build_packet(args: argparse.Namespace) -> dict:
    tz = ZoneInfo("Asia/Shanghai")
    today = (
        dt.datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=tz)
        if args.date
        else dt.datetime.now(tz)
    )
    start = today - dt.timedelta(days=args.days - 1)
    end = today + dt.timedelta(days=1) - dt.timedelta(minutes=1)
    root = Path(args.output_root)
    config_path = Path(__file__).with_name("sources.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))

    hf_config = config.get("huggingface", {})
    api_bases = [hf_config.get("api_base", DEFAULT_HF_BASE)]
    if args.use_hf_mirror:
        api_bases.append(hf_config.get("mirror_api_base", DEFAULT_HF_MIRROR_BASE))
    if args.hf_base:
        api_bases.insert(0, args.hf_base)
    api_bases = list(dict.fromkeys(base for base in api_bases if base))

    search_queries = hf_config.get("search_queries") or config.get("keywords", [])
    entries: list[dict] = []
    errors: list[str] = []
    source_health: list[dict] = []

    if not args.no_hf_daily:
        entries.extend(
            collect_hf_daily(
                api_bases=api_bases,
                start=start,
                end=end,
                timeout=args.timeout,
                retries=args.retries,
                source_health=source_health,
                errors=errors,
            )
        )
    if not args.no_hf_search:
        entries.extend(
            collect_hf_search(
                api_bases=api_bases,
                queries=search_queries,
                start=start,
                end=end,
                timeout=args.timeout,
                retries=args.retries,
                per_query_limit=args.hf_search_limit,
                source_health=source_health,
                errors=errors,
            )
        )

    if not args.no_arxiv:
        for category in config.get("arxiv_categories", []):
            try:
                result = query_arxiv(category, start, end, timeout=args.timeout, retries=args.retries)
                entries.extend(result)
                source_health.append({"source": "arxiv_api", "category": category, "status": "ok", "count": len(result)})
            except Exception as exc:
                errors.append(f"arxiv {category}: {exc}")
                source_health.append({"source": "arxiv_api", "category": category, "status": "error", "error": str(exc)})

    entries = merge_entries(entries)
    seen_keys = read_seen_keys(root, today.strftime("%Y-%m-%d"))
    for entry in entries:
        points, reasons, bucket = score(entry, config, end)
        entry["relevance_score"] = points
        entry["relevance_reasons"] = reasons[:24]
        entry["bucket_hint"] = bucket
        entry["seen_in_month"] = entry_key(entry) in seen_keys
    entries.sort(
        key=lambda item: (
            item.get("seen_in_month") is False,
            item.get("relevance_score", 0),
            item.get("published", ""),
        ),
        reverse=True,
    )

    official_news = []
    official_urls = config.get("official_news_pages", [])
    if not args.skip_official_news:
        official_news = collect_official_news(
            urls=official_urls,
            keywords=config.get("keywords", []) + config.get("companies", []),
            timeout=args.timeout,
            retries=max(0, min(args.retries, 1)),
            limit=args.official_links_per_page,
            source_health=source_health,
            errors=errors,
        )

    strong_count = sum(1 for item in entries if item.get("bucket_hint") == "strong_related")
    supplement_count = sum(1 for item in entries if item.get("bucket_hint") == "supplement")
    return {
        "generated_at": today.isoformat(),
        "window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": args.days,
        },
        "config": config,
        "source_strategy": {
            "primary": "huggingface_papers_api",
            "fallbacks": ["arxiv_api", "official_news_pages", "web_verification_by_agent"],
            "hf_api_bases": api_bases,
            "local_translation": ".venv/bin/python code/translate_abstracts.py --translator local",
        },
        "source_counts": {
            "paper_candidates_total": len(entries),
            "strong_related_hint": strong_count,
            "supplement_hint": supplement_count,
            "seen_in_month": sum(1 for item in entries if item.get("seen_in_month")),
            "official_pages_checked": 0 if args.skip_official_news else len(official_urls),
            "official_pages_accessible": len(official_news),
        },
        "paper_candidates": entries[: args.limit],
        "arxiv_candidates": entries[: args.limit],
        "official_news_candidates": official_news,
        "source_health": source_health,
        "source_errors": errors,
        "next_step": (
            "Use paper_candidates as the HF-first discovery set. Verify paper PDF, "
            "affiliations, author/team background, project pages, direct code/model "
            "links, real-robot evidence, company news, and community reaction before "
            "writing HTML. Then run the local abstract translator on the final HTML."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Report date in YYYY-MM-DD; defaults to today in Asia/Shanghai.")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--limit", type=int, default=160)
    parser.add_argument("--output-root", default=".")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--hf-base", help="Override Hugging Face-compatible API base URL.")
    parser.add_argument("--use-hf-mirror", action="store_true", help="Try hf-mirror after the configured HF base.")
    parser.add_argument("--hf-search-limit", type=int, default=120)
    parser.add_argument("--official-links-per-page", type=int, default=12)
    parser.add_argument("--no-hf-daily", action="store_true")
    parser.add_argument("--no-hf-search", action="store_true")
    parser.add_argument("--no-arxiv", action="store_true")
    parser.add_argument("--skip-official-news", action="store_true")
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days must be positive")
    packet = build_packet(args)
    report_date = packet["generated_at"][:10]
    month_dir = Path(args.output_root) / report_date[:7]
    month_dir.mkdir(parents=True, exist_ok=True)
    output = month_dir / f"research-packet-{report_date}.json"
    output.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(html.escape(str(output.resolve())))
    print(
        "candidates={paper_candidates_total} strong_hint={strong_related_hint} "
        "supplement_hint={supplement_hint} seen_in_month={seen_in_month}".format(
            **packet["source_counts"]
        )
    )
    if packet["source_errors"]:
        print("source_errors=" + "; ".join(packet["source_errors"][:8]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
