---
name: paper-pdf-parser
description: 将科研论文 PDF 解析成可复核的结构化结果，并按论文结构生成可编辑学术 PPT（含页级证据映射、讲稿备注与真实渲染预览）。当任务要求逐字提取正文、修正多栏阅读顺序、还原表格/公式结构、或把论文组织成汇报幻灯片时使用。适用于 Reading/解析类科研案例，输入为 PDF，输出为 result.json + 结构化中间产物 + 幻灯片。
---

# paper-pdf-parser：科研论文 PDF 结构化解析

本 Skill 把一份科研论文 PDF 解析成「可回到原文页码/区块」的结构化结果，并可把它组织成一份**可编辑的学术 PPT**（每页一张/多张幻灯片，正文逐字保留在备注里，附页级证据映射与真实渲染预览）。核心原则：**逐字保真、顺序正确、结构清晰、证据可复核；读不出的部分如实标注，绝不靠猜补齐。**

## 何时使用
- 任务要求解析、翻译、问答、提取、核验或知识结构化一份科研 PDF。
- 任务要求交付可编辑幻灯片、且需要真实渲染预览（PDF/PNG）供检查。

## 执行流程（严格按顺序）

### 第 1 步：读输入与任务边界
1. 读 `/input/case.json`：拿到 `case_id`、材料路径（PDF 或其所在目录）、任务说明、`output_contract`（结果必须覆盖的字段清单）。
2. 读 `/input/task.md`（若存在）：拿到本案例具体要求与评分证据范围。
3. 只依据实际输入文件与原文；不依据错误领域标签补造数据。

### 第 2 步：运行解析脚本
```bash
python3 /skills/weekly-skill/scripts/parse_pdf.py <PDF路径> /app/work
```
脚本产出 `/app/work/structured.json`，包含：
- `pages`：每页尺寸、是否含文字层、是否疑似扫描件；
- `blocks`：每个文本/图片块及其 `{page, x0, y0, x1, y1, column, kind, text}`；
- `reading_order`：修正多栏/跨页后的阅读顺序（块 id 序列）；
- `sections` / `tables` / `formulas` / `figures` / `references`：结构元素（尽力而为）；
- `evidence`：每个单元到 `{page, region, kind}` 的证据映射。

若脚本报错（如缺少 PDF 库），不要放弃，按「工具回退」小节用声明工具（pdf-text-tool / pdf-render-tool / ocr-tool）手动完成同样的解析。

### 第 3 步：核验与校正（关键）
1. 用 `pdf-render-tool` 渲染原 PDF 页面为 PNG，逐页与 `structured.json` 的阅读顺序比对：
   - 双栏/多栏：确认没有「串栏」（左栏第1段后面跟了右栏第1段再跳回左栏第2段）——标准顺序是：通栏块（标题/摘要）→ 左栏自上而下 → 右栏自上而下 → 参考文献。
   - 确认页眉页脚没有混入正文；脚注、图表题注、参考文献逐字保留。
2. 表格：确认行列与合并单元格归属正确；跨页续表要合并并标注续表来源页。
3. 公式：按结构元素识别（保留其文本/LaTeX 或渲染区域图），不要求理解科学含义。
4. 读不出的部分：在 `uncertainty` 里如实列出，不猜。

### 第 4 步：生成可编辑学术 PPT（推荐，默认执行）
```bash
python3 /skills/weekly-skill/scripts/build_ppt.py /app/work/structured.json /app/output
```
产出：
- `/app/output/paper_slides.pptx`：可编辑 PPTX，按论文结构分页（标题页、每节、每图/表、参考文献），每页备注写入该单元**逐字正文 + 页码/区块证据**；
- `/app/output/preview.pdf` 与 `/app/output/preview_png/*.png`：真实渲染预览（用 office-renderer 把 PPTX 转 PDF，再用 pdf-render-tool 转 PNG）。

若 `build_ppt.py` 因缺 `python-pptx` 失败：改用「工具回退」里的 HTML 幻灯片方案，仍要产出可打开、可检查的预览。

### 第 5 步：写 result.json
写 `/app/output/result.json`，必须包含：
```json
{
  "case_id": "<来自 case.json>",
  "status": "success|partial|failed|refused",
  "status_reason": "<简述；partial/failed/refused 必须给出原因与可人工接管位置>",
  "result": { ...结构化解析结果，逐字内容... },
  "evidence": [ {"page": N, "region": "...", "kind": "text|table|figure|formula", "note": "..."} ],
  "uncertainty": [ {"item": "...", "reason": "未报告|无法判断|材料缺失|OCR 不确定"} ],
  "change_records": [ {"action": "...", "reason": "..."} ],
  "artifacts": {
    "structured_json": "/app/work/structured.json",
    "pptx": "/app/output/paper_slides.pptx",
    "preview_pdf": "/app/output/preview.pdf",
    "preview_png": ["/app/output/preview_png/..." ]
  }
}
```
**必须**再从 `/input/case.json` 的 `output_contract` 里读取所有字段名，把它们的值一并写入 `result`（或顶层），一个都不能漏。`case_id` 必填。`result` 中每个关键结论都要能在 `evidence` 里回到原文页码/区块；无法判断的内容写进 `uncertainty`，不要写成事实。

### 第 6 步：自查
- 结构化结果是否覆盖：标题、作者与单位、摘要、章节层级、图表与题注、公式编号、参考文献、页眉页脚与脚注。
- 每个关键结论是否都能指回 `{page, region}`。
- 是否诚实地记录了 partial/失败与原因。

## 工具回退（脚本依赖缺失时）
- **文字层提取**：优先 `pdf-text-tool`（若支持带坐标输出）；否则 `pdftotext -bbox` 解析词级坐标；都不行则 `pdftotext -layout`。
- **渲染页面**：`pdf-render-tool`（或 `pdftoppm -r 150`）。
- **扫描件 OCR**：页面无文字层时，先渲染 300 DPI 图片，再 `ocr-tool`；OCR 结果标注置信度，低置信度写入 `uncertainty`。
- **幻灯片回退**：若 `python-pptx` 不可用，生成自包含 HTML 幻灯片（`slides.html`，内嵌样式），再用 office-renderer 转 PDF/PNG 作为预览。
- **加密/损坏 PDF**：识别后直接 `status=refused` 并说明原因，不硬解。

## 限制与边界
- 图表与公式只做**结构元素识别**，不解读科学含义。
- 只提交 Skill 与必要资源；正式案例、白板与对照结果由平台提供，不预置任何正式答案。
- 运行预算有限（模型请求、时长、token 均有上限）：先落地结构化结果，再增量改进；始终先保存诚实的部分成果。
