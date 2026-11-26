---
name: paper-pdf-translator
description: 把科研论文 PDF 翻译成可复核的双语对照结果，并按论文结构生成可编辑学术 PPT（含术语表、页级证据映射、讲稿备注与真实渲染预览）。当任务要求术语一致的文献翻译、长文分段续译、双语段落对照或译文核验时使用。输入为 PDF，输出为 result.json + 双语对照中间产物 + 幻灯片。
---

# paper-pdf-translator：科研论文 PDF 翻译

本 Skill 把一份科研论文 PDF 翻译成**可回到原文页码/段落**的双语对照结果，并可组织成一份**可编辑的学术 PPT**（正文用译文，讲稿备注保留原文 + 术语对照 + 页级证据）。核心原则：**术语稳、段落全、关系准、可核验；译不准的明确标注，绝不含混或改写大意。**

## 何时使用
- 任务要求翻译、双语对照、术语抽取与锁定、长文分段续译或译文核验一份科研 PDF。
- 任务要求交付可编辑幻灯片、且需要真实渲染预览（PDF/PNG）供检查。

## 执行流程（严格按顺序）

### 第 1 步：读输入与任务边界
1. 读 `/input/case.json`：拿到 `case_id`、材料路径、任务说明、`output_contract` 字段清单。
2. 读 `/input/task.md`（若存在）：拿到评分证据范围与翻译要求（目标语言、术语口径等）。
3. 只依据实际输入文件与原文；不依据错误领域标签补造数据。

### 第 2 步：解析原文（复用解析脚本）
```bash
python3 /skills/weekly-skill/scripts/parse_pdf.py <PDF路径> /app/work
```
产出 `/app/work/structured.json`（含 `blocks`/`reading_order`/`sections`/`tables`/`elements`，每个块带 `{page,x0,y0,x1,y1,column}`）。这一步保证**段落全**：跨页、跨栏、跨章节不丢段、不重复、不错位。

### 第 3 步：建术语表并全篇锁定（术语稳）
1. 从原文抽取领域术语（含缩写、专名、方法名、化合物/材料名、指标名），建立术语表 `term_table`：
   ```json
   [{"source": "原文术语", "target": "统一译名", "note": "依据/来源（页码）"}]
   ```
2. **术语表必须真正执行**：标题、摘要、正文、图注、表头、结论中使用同一译名。翻译时每段声明用到的术语（`terms` 字段），便于核验。
3. 术语表可持续追加：遇到新术语先定译名、回填到已译段落。

### 第 4 步：逐段翻译（段落全 + 关系准）
1. 按 `reading_order` 顺序逐段翻译；**跨页/跨栏的段落先拼接完整再译**，避免半句翻译。
2. 携带上下文：上一段的已定术语 + 当前段的指代对象。指代对象、否定与限定条件、因果与让步关系必须与原文一致。
3. **逐字保留**：数字、单位、公式（保留 LaTeX/原文形式）、图表编号、文献引用标记 `[n]` 不得改动或丢失。
4. 每段输出：原文 `source`、译文 `translation`、`page`/`bbox` 证据、用到的 `terms`、`verification` 说明。

### 第 5 步：译文核验（可核验）
逐段自检并记录：
- 数字/单位是否与原文一致；
- 公式与文献编号是否保留；
- 否定关系、限定条件、因果/让步关系是否准确；
- 译不准、有歧义、材料缺失处是否标注（进 `uncertainty`，不写成事实）。

### 第 6 步：生成可编辑学术 PPT（推荐，默认执行）
把双语结果写成 `/app/work/translation.json`（格式见 `README.md`），然后：
```bash
python3 /skills/weekly-skill/scripts/build_ppt.py /app/work/translation.json /app/output
```
产出：
- `/app/output/paper_slides.pptx`：可编辑 PPTX，正文用译文，按论文结构分页（标题页、每节、每图/表、术语表、参考文献），**讲稿备注保留原文 + 术语对照 + 页级证据**；
- `/app/output/preview.pdf` 与 `/app/output/preview_png/*.png`：真实渲染预览（office-renderer 转 PDF，pdf-render-tool 转 PNG）。

### 第 7 步：写 result.json
写 `/app/output/result.json`，必须包含：
```json
{
  "case_id": "<来自 case.json>",
  "status": "success|partial|failed|refused",
  "status_reason": "<简述；partial/failed/refused 给出原因与可人工接管位置>",
  "result": { "title": {...}, "term_table": [...], "paragraphs": [...], "verification_summary": [...] },
  "evidence": [ {"page": N, "region": "...", "kind": "text|table|figure|formula"} ],
  "uncertainty": [ {"item": "...", "reason": "未报告|无法判断|材料缺失|译法有歧义"} ],
  "change_records": [ {"action": "...", "reason": "..."} ],
  "artifacts": { "structured_json": "...", "translation_json": "...", "pptx": "...", "preview_pdf": "..." }
}
```
**必须**再从 `/input/case.json` 的 `output_contract` 里读取所有字段名，把它们的值一并写入 `result`，一个都不能漏。每段译文都要能在 `evidence` 里指回原文页码/段落。

## 工具回退（脚本依赖缺失时）
- **文字层提取**：`pdf-text-tool` → `pdftotext -bbox` → `pdftotext -layout`。
- **渲染页面**：`pdf-render-tool`（或 `pdftoppm -r 150`）。
- **扫描件 OCR**：无文字层时渲染 300 DPI 后用 `ocr-tool`，低置信度进 `uncertainty`。
- **幻灯片回退**：`python-pptx` 不可用时生成自包含 HTML 幻灯片，再用 office-renderer 转 PDF/PNG。
- **加密/损坏 PDF**：`status=refused` 并说明原因，不硬解。

## 限制与边界
- 只提交 Skill 与必要资源；正式案例、白板与对照结果由平台提供，不预置任何正式译文。
- 运行预算有限：先落地完整双语对照，再增量改进；始终先保存诚实的部分成果。
- 图表与公式只做结构保留（编号/位置/原文形式），不解读其科学含义。
