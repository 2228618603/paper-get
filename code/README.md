# 每日 Paper Loop Engineering

这套流程用于每天北京时间 07:00 生成具身智能与大模型前沿简报。

## 文件

- `prompt.md`：给检索与写作代理的完整任务规范。
- `sources.json`：企业、实验室、关键词和优先级配置。
- `generate_report.py`：以 Hugging Face Papers API 为主、arXiv API 为补充，抓取近一周论文元数据、HF 热度、项目页/GitHub 线索、企业官网索引，并生成候选论文包；可作为每日任务的第一步。
- `render_report_from_packet.py`：把候选包和人工核验后的排序规则渲染成 HTML，并维护当月去重日志。
- `translate_abstracts.py`：逐句补全摘要中文翻译缓存；可断点续跑，避免翻译服务阻塞日报生成。
- `YYYY-MM/seen-YYYY-MM.md`：当前月份的去重日志；每日只读写当月文件，避免重复报道。

## 手动运行

在本目录的上一级执行：

```bash
python3 code/generate_report.py --output-root . --use-hf-mirror
```

也可以固定报告日期：

```bash
python3 code/generate_report.py --date 2026-09-17 --days 7 --limit 200 --output-root . --use-hf-mirror
```

脚本会把候选论文包写入对应月份目录的 `research-packet-YYYY-MM-DD.json`。候选包里：

- `paper_candidates`：HF-first 的主候选列表，已按相关性、HF 热度、代码/项目页线索、真机关键词、硬性关注对象和新鲜度做粗排。
- `arxiv_candidates`：兼容旧渲染器/翻译器的同一候选列表。
- `official_news_candidates`：企业官网首页/新闻页的快速索引线索，用于后续网页核验。
- `source_health` / `source_errors`：当天数据源健康度与失败原因，低数量日报必须先看这里。

最终 HTML 仍需经过网页、项目页、代码仓库、作者背景和真机证据核验后生成，不能把候选包里的粗筛标签直接当最终结论。

当前版本也提供一个本地渲染器，可用于把已经核验/排序后的候选包输出为 HTML：

```bash
python3 code/render_report_from_packet.py --date 2026-09-16 --root .
```

如果摘要翻译缓存或最终 HTML 中有“待补”句子，可单独运行：

```bash
python3 code/translate_abstracts.py --date 2026-09-16 --root . --source html --all --sleep 1.2
```

该脚本会直接扫描当天最终 HTML 的“摘要逐句对照翻译”折叠块，补齐中文翻译；如果英文仍是占位句，会尝试按 arXiv 链接重新抓取真实摘要再翻译。公共翻译服务可能限流，因此脚本支持多次断点续跑。若由本地 renderer 生成，也可以用 `--source both --all` 同步 `YYYY-MM/abstract-translations-YYYY-MM-DD.json` 缓存。

## 本地离线翻译

为了避免公共翻译 API 限流，推荐在新设备上先安装本地翻译环境：

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -r requirements-local-translation.txt
.venv/bin/python code/setup_local_translator.py
```

模型会缓存到 Hugging Face 本地缓存。之后翻译日报时使用：

```bash
.venv/bin/python code/translate_abstracts.py --date 2026-09-17 --root . --source html --translator local --all
```

`--translator local` 不调用在线翻译服务；如果需要自动兜底，可以改成 `--translator auto`。

## 自动运行

桌面端定时任务使用 `prompt.md` 作为代理任务说明。代理每次运行时应：

1. 读取 `sources.json`；
2. 读取或创建 `YYYY-MM/seen-YYYY-MM.md`，用于本月去重；
3. 运行 `generate_report.py --use-hf-mirror` 获取 HF-first 候选；
4. 先检查候选包健康度；若出现 HF Daily Papers、HF search、arXiv 429/timeout、候选数量异常偏低或正文数量异常偏低，必须重试并换用 hf-mirror、网页/RSS/Semantic Scholar/Papers with Code/机构官网等 fallback 补抓，不能直接交付低数量报告；
5. 使用网页检索核验近 7 天新闻、企业官网、实验室主页、作者背景、项目页、代码仓库、Hugging Face 模型/数据集/Spaces 和真机证据；
6. 先分别整理三部分：与你课题强相关的论文、扩展补充论文、News，再合并成 HTML；
7. 强相关论文最多 30 篇，扩展补充论文最多 10 篇，News 最多 20 条，但不强行填满；
8. 对每篇论文标注研究机构/团队、机构简介、代码状态、真机状态、实验设置和编辑评述；一作/通讯背调只作为后台排序依据，不在页面展示；
9. 每篇论文只保留摘要折叠块，摘要需保留英文原句并做中文逐句对照；正文 HTML 生成后优先运行 `.venv/bin/python code/translate_abstracts.py --source html --translator local --all` 做本地离线修补与校验；翻译缓存不足时明确标注待补，不得用概括译述冒充逐句翻译；不再翻译 Introduction；
10. 生成 `YYYY-MM/YYYY-MM-DD-风向总结.html`；
11. 更新当前月去重日志。

如果需要脱离 Codex 桌面端运行，建议在环境中设置 `OPENAI_API_KEY`，再把检索包交给自己的报告生成器。当前版本不把任何未验证的企业描述当成事实。
