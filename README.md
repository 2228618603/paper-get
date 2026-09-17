# paper-get

Daily loop engineering workflow for tracking embodied intelligence, VLA/WAM,
self-improving agents, robotics infrastructure, and broader AI news.

## What is included

- `code/prompt.md`: daily research and writing specification.
- `code/sources.json`: watchlist of companies, labs, keywords, and official sources.
- `code/generate_report.py`: HF Papers-first candidate collector with arXiv and
  official-source supplements.
- `code/render_report_from_packet.py`: local HTML renderer and monthly dedup log updater.
- `YYYY-MM/seen-YYYY-MM.md`: monthly deduplication log.
- `YYYY-MM/*.html`: generated daily reports.

## Current workflow

The Codex desktop automation starts before 07:00 Beijing time. It reads the
prompt and source configuration, checks the current monthly dedup log, collects
recent Hugging Face Papers and arXiv candidates, verifies important papers/news,
uses the local offline translator for sentence-level abstract translation, and
writes a daily HTML report.

## Reproduce on a new machine

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -r requirements-local-translation.txt
.venv/bin/python code/setup_local_translator.py
python3 code/generate_report.py --days 7 --limit 200 --output-root . --use-hf-mirror
```

After the HTML is generated, patch/check abstract translations with:

```bash
.venv/bin/python code/translate_abstracts.py --date YYYY-MM-DD --root . --source html --translator local --all --sleep 0
```
