#!/usr/bin/env python3
"""Collect a recent arXiv candidate packet for the daily embodied-AI report.

This script intentionally stops at evidence collection. The final report needs
web verification for affiliations, code repositories, real-robot experiments,
and company news, so it should be written by the scheduled research agent after
reading the packet.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo


ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def fetch(url: str, timeout: int = 45) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "daily-paper-loop/1.0 (research workflow)",
            "Accept": "application/atom+xml,text/html;q=0.9,*/*;q=0.5",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def parse_entry(entry: ET.Element) -> dict:
    title = " ".join((entry.findtext("atom:title", default="", namespaces=ARXIV_NS)).split())
    summary = " ".join((entry.findtext("atom:summary", default="", namespaces=ARXIV_NS)).split())
    published = entry.findtext("atom:published", default="", namespaces=ARXIV_NS)
    identifier = entry.findtext("atom:id", default="", namespaces=ARXIV_NS)
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
        link.attrib.get("href", "")
        for link in entry.findall("atom:link", ARXIV_NS)
        if link.attrib.get("href")
    ]
    return {
        "title": title,
        "summary": summary,
        "published": published,
        "id": identifier.replace("http://", "https://"),
        "authors": authors,
        "comments": comments,
        "links": links,
    }


def query_arxiv(category: str, start: dt.datetime, end: dt.datetime) -> list[dict]:
    query = (
        f"cat:{category} AND submittedDate:"
        f"[{start.strftime('%Y%m%d%H%M')} TO {end.strftime('%Y%m%d%H%M')}]"
    )
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": 0,
            "max_results": 100,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    url = f"https://export.arxiv.org/api/query?{params}"
    root = ET.fromstring(fetch(url))
    return [parse_entry(entry) for entry in root.findall("atom:entry", ARXIV_NS)]


def score(entry: dict, keywords: list[str]) -> int:
    haystack = f"{entry['title']} {entry['summary']} {' '.join(entry['comments'])}".lower()
    points = 0
    for keyword in keywords:
        if keyword.lower() in haystack:
            points += 2 if keyword.lower() in entry["title"].lower() else 1
    if re.search(r"\b(real[- ]robot|hardware|physical|robot)\b", haystack):
        points += 2
    if re.search(r"\b(code|github|project page)\b", haystack):
        points += 1
    return points


def deduplicate(entries: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for entry in entries:
        key = re.sub(r"[^a-z0-9]+", " ", entry["title"].lower()).strip()
        if key and key not in seen:
            seen.add(key)
            result.append(entry)
    return result


def build_packet(args: argparse.Namespace) -> dict:
    tz = ZoneInfo("Asia/Shanghai")
    today = (
        dt.datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=tz)
        if args.date
        else dt.datetime.now(tz)
    )
    start = today - dt.timedelta(days=args.days)
    end = today + dt.timedelta(days=1) - dt.timedelta(minutes=1)
    config_path = Path(__file__).with_name("sources.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    entries: list[dict] = []
    errors: list[str] = []
    for category in config["arxiv_categories"]:
        try:
            entries.extend(query_arxiv(category, start, end))
        except Exception as exc:  # Keep one failed source from stopping the loop.
            errors.append(f"{category}: {type(exc).__name__}: {exc}")
    entries = deduplicate(entries)
    for entry in entries:
        entry["relevance_score"] = score(entry, config["keywords"])
    entries.sort(
        key=lambda item: (item["relevance_score"], item["published"]),
        reverse=True,
    )
    return {
        "generated_at": today.isoformat(),
        "window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": args.days,
        },
        "config": config,
        "arxiv_candidates": entries[: args.limit],
        "source_errors": errors,
        "next_step": (
            "Verify project pages, direct repositories, affiliations, real-robot "
            "evidence, and official company news before writing HTML."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Report date in YYYY-MM-DD; defaults to today in Asia/Shanghai.")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--output-root", default=".")
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
    print(f"candidates={len(packet['arxiv_candidates'])}")
    if packet["source_errors"]:
        print("source_errors=" + "; ".join(packet["source_errors"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
