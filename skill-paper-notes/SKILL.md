---
name: paper-structured-notes
description: 把科研论文 PDF 整理成与章节对齐、字段齐备、可回到原文的结构化笔记，并按论文结构生成可编辑学术 PPT（含页级证据映射、讲稿备注与真实渲染预览）。当任务要求章节总结、论文卡片、知识点提取或来源回链时使用。输入为 PDF，输出为 result.json + 结构化笔记 + 幻灯片。
---

# paper-structured-notes：科研论文结构化笔记

本 Skill 把一份科研论文整理成**与论文自身章节对齐**的结构化笔记（论文卡片 + 章节总结 + 知识点清单 + 来源锚点），并可组织成一份**可编辑学术 PPT**（正文为笔记，讲稿备注保留原文片段 + 页级证据）。核心原则：**对得上、留得住、找得回、用得上；不确定处明确标注，绝不用通用模板硬套或编造。**

## 何时使用
- 任务要求章节总结、论文卡片、知识点提取、来源回链或可检索笔记一份科研 PDF。
- 任务要求交付可编辑幻灯片、且需要真实渲染预览（PDF/PNG）供检查。

## 执行流程（严格按顺序）

### 第 1 步：读输入与任务边界
1. 读 `/input/case.json`：拿 `case_id`、材料路径、任务说明、`output_contract` 字段清单。
2. 读 `/input/task.md`（若存在）：拿评分证据范围与笔记要求（字段口径、锚点粒度）。
3. 只依据实际输入文件与原文；不依据错误领域标签补造数据。

### 第 2 步：解析原文（复用解析脚本）
```bash
python3 /skills/weekly-skill/scripts/parse_pdf.py <PDF路径> /app/work
```
产出 `/app/work/structured.json`（`sections`/`reading_order`/`tables`/`elements`，每块带 `{page,x0,y0,x1,y1,column}`）。这一步保证「对得上」：笔记骨架跟随论文自身章节与论证顺序。

### 第 3 步：建论文卡片（留得住）
从原文抽取并填入统一字段（同一领域多篇可并排比较）：
```json
{
  "research_question": "...", "data": "...", "methods": "...",
  "main_findings": "...", "conclusions": "...", "limitations": "..."
}
```
必须保留**让结论成立的前提条件**（方法条件、数据范围、假设），不丢失、不夸大。

### 第 4 步：按章节做总结 + 知识点提取（对得上 + 用得上）
1. 按原文章节顺序，逐节提炼「目的/方法/结果/结论」，保留章节间承接关系。
2. 把重要概念、变量、方法和结论拆成**可检索的知识点条目**，处理术语/缩写/同义表述，避免条目重复或自相矛盾。
3. 每条知识点：`{concept, definition/statement, page, evidence, relation}`。

### 第 5 步：来源回链 + 复核（找得回）
- 每条关键笔记/知识点/数值/变量都要带锚点 `{page, region, kind}`，指回原文具体章节、段落、页码或图表。
- 锚点粒度与可核验性匹配；能机器判定与必须人工确认的字段分别说明。
- 不确定、缺失、冲突处写进 `uncertainty`，不写成事实。

### 第 6 步：生成可编辑学术 PPT（推荐，默认执行）
把笔记写成 `/app/work/notes.json`（格式见 `README.md`），然后：
```bash
python3 /skills/weekly-skill/scripts/build_ppt.py /app/work/notes.json /app/output
```
产出：
- `/app/output/paper_slides.pptx`：可编辑 PPTX，按论文结构分页（标题页、论文卡片、每节笔记、知识点、参考文献），**讲稿备注保留原文片段 + 页级证据**；
- `/app/output/preview.pdf` 与 `/app/output/preview_png/*.png`：真实渲染预览（office-renderer 转 PDF，pdf-render-tool 转 PNG）。

### 第 7 步：写 result.json
写 `/app/output/result.json`，必须包含：
```json
{
  "case_id": "<来自 case.json>",
  "status": "success|partial|failed|refused",
  "status_reason": "<简述；partial/failed/refused 给出原因与可人工接管位置>",
  "result": { "paper_card": {...}, "sections": [...], "knowledge_points": [...], "verification": [...] },
  "evidence": [ {"page": N, "region": "...", "kind": "text|table|figure|formula"} ],
  "uncertainty": [ {"item": "...", "reason": "未报告|无法判断|材料缺失|冲突"} ],
  "change_records": [ {"action": "...", "reason": "..."} ],
  "artifacts": { "structured_json": "...", "notes_json": "...", "pptx": "...", "preview_pdf": "..." }
}
```
**必须**再从 `/input/case.json` 的 `output_contract` 读取所有字段名，把它们的值一并写入 `result`，一个都不能漏。每条笔记都要能在 `evidence` 里指回原文。

## 工具回退（脚本依赖缺失时）
- **文字层提取**：`pdf-text-tool` → `pdftotext -bbox` → `pdftotext -layout`。
- **渲染页面**：`pdf-render-tool`（或 `pdftoppm -r 150`）。
- **扫描件 OCR**：无文字层时渲染 300 DPI 后 `ocr-tool`，低置信度进 `uncertainty`。
- **幻灯片回退**：`python-pptx` 不可用时生成自包含 HTML 幻灯片，再用 office-renderer 转 PDF/PNG。
- **加密/损坏 PDF**：`status=refused` 并说明原因，不硬解。

## 限制与边界
- 只提交 Skill 与必要资源；正式案例、白板与对照结果由平台提供，不预置任何正式笔记。
- 笔记是对原文的结构化提炼，不是压缩式通读摘要；不得脱离原文编造结论。
- 运行预算有限：先落地完整结构化笔记，再增量改进；始终先保存诚实的部分成果。
