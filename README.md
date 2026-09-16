# paper-get

Daily loop engineering workflow for tracking embodied intelligence, VLA/WAM,
self-improving agents, robotics infrastructure, and broader AI news.

## What is included

- `code/prompt.md`: daily research and writing specification.
- `code/sources.json`: watchlist of companies, labs, keywords, and official sources.
- `code/generate_report.py`: arXiv candidate collector.
- `code/render_report_from_packet.py`: local HTML renderer and monthly dedup log updater.
- `YYYY-MM/seen-YYYY-MM.md`: monthly deduplication log.
- `YYYY-MM/*.html`: generated daily reports.

## Current workflow

The Codex desktop automation runs every day at 07:00 Beijing time. It reads the
prompt and source configuration, checks the current monthly dedup log, collects
recent arXiv candidates, verifies important papers/news, and writes a daily HTML
report.

