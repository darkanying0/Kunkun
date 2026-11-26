---
name: paper-nanopublication
description: 把科研论文的关键结论拆成可独立验证的断言（Nanopublication），逐条绑定最小证据片段与来源元数据，输出可机器读取的结构，并按论文结构生成可编辑学术 PPT（含页级证据映射、讲稿备注与真实渲染预览）。当任务要求断言拆解、证据绑定、来源追溯或结构化导出时使用。输入为 PDF，输出为 result.json + nanopublications 结构 + 幻灯片。
---

# paper-nanopublication：科研论文断言拆解与证据绑定

本 Skill 把论文关键结论拆成**一条条可独立判断真假的断言**，为每条断言绑定**最小充分证据片段**和**来源元数据**，输出**可机器读取**的 Nanopublication 结构，并可组织成一份**可编辑学术 PPT**（正文为断言，讲稿备注保留证据片段+页级证据）。核心原则：**拆得细、对得上、追得回、读得懂；找不到证据或证据不足的明确标注，绝不编造。**

## 何时使用
- 任务要求把论文结论拆成 Nanopublication、断言校验、证据绑定、来源检索或结构化导出。
- 任务要求交付可编辑幻灯片、且需要真实渲染预览（PDF/PNG）供检查。

## 执行流程（严格按顺序）

### 第 1 步：读输入与任务边界
1. 读 `/input/case.json`：拿 `case_id`、材料路径、任务说明、`output_contract` 字段清单。
2. 读 `/input/task.md`（若存在）：拿评分证据范围与导出字段口径。
3. 只依据实际输入文件与原文；不依据错误领域标签补造数据。

### 第 2 步：解析原文（复用解析脚本）
```bash
python3 /skills/weekly-skill/scripts/parse_pdf.py <PDF路径> /app/work
```
产出 `/app/work/structured.json`（`sections`/`reading_order`/`tables`/`elements`，每块带 `{page,x0,y0,x1,y1,column}`）。这一步为「对得上」提供原文位置。

### 第 3 步：断言拆解（拆得细）
1. 从结论、结果、讨论段落中拆出**单一、可验证的科研断言**，不把整段塞进一个字段。
2. 保留条件和限定范围；处理复合句中的并列、因果、让步结构，拆成独立断言。
3. 每条断言标出**主体（subject）→ 关系（relation，用受控词表）→ 客体（object）**。

### 第 4 步：证据绑定 + 来源元数据（对得上 + 追得回）
1. 为每条断言找到**真正支撑它的最小证据片段**，并指回原文 `{page, region}`。
2. 区分**直接证据**与**间接推论**（`evidence_type: direct|indirect`）。
3. 记录来源元数据：论文、作者、年份、版本、标识符、数据来源（`provenance`）。
4. 证据不足、断言过宽、主体混淆、来源缺失的，进质量检查记录或 `uncertainty`。

### 第 5 步：质量检查（读得懂）
逐条自检：断言是否过宽、证据是否不足、关系类型是否错误、主体是否混淆、来源是否缺失；给出**可复现的判定依据**。导出结构必须符合约定字段与序列化形态，下游程序可直接解析。

### 第 6 步：生成可编辑学术 PPT（推荐，默认执行）
把结果写成 `/app/work/nanopub.json`（格式见 `README.md`），然后：
```bash
python3 /skills/weekly-skill/scripts/build_ppt.py /app/work/nanopub.json /app/output
```
产出：
- `/app/output/paper_slides.pptx`：可编辑 PPTX，按断言分页（标题页、断言清单、证据与来源、质量检查），**讲稿备注保留证据片段 + 页级证据**；
- `/app/output/preview.pdf` 与 `/app/output/preview_png/*.png`：真实渲染预览（office-renderer 转 PDF，pdf-render-tool 转 PNG）。

### 第 7 步：写 result.json
写 `/app/output/result.json`，必须包含：
```json
{
  "case_id": "<来自 case.json>",
  "status": "success|partial|failed|refused",
  "status_reason": "<简述；partial/failed/refused 给出原因与可人工接管位置>",
  "result": { "nanopublications": [...], "quality_checks": [...], "provenance": {...} },
  "evidence": [ {"page": N, "region": "...", "kind": "text|table|figure|formula"} ],
  "uncertainty": [ {"item": "...", "reason": "证据不足|来源缺失|断言过宽|无法判断"} ],
  "change_records": [ {"action": "...", "reason": "..."} ],
  "artifacts": { "structured_json": "...", "nanopub_json": "...", "pptx": "...", "preview_pdf": "..." }
}
```
**必须**再从 `/input/case.json` 的 `output_contract` 读取所有字段名，把它们的值一并写入 `result`，一个都不能漏。每条断言都要能在 `evidence` 里指回原文。

## 工具回退（脚本依赖缺失时）
- **文字层提取**：`pdf-text-tool` → `pdftotext -bbox` → `pdftotext -layout`。
- **渲染页面**：`pdf-render-tool`（或 `pdftoppm -r 150`）。
- **扫描件 OCR**：无文字层时渲染 300 DPI 后 `ocr-tool`，低置信度进 `uncertainty`。
- **幻灯片回退**：`python-pptx` 不可用时生成自包含 HTML 幻灯片，再用 office-renderer 转 PDF/PNG。
- **加密/损坏 PDF**：`status=refused` 并说明原因，不硬解。

## 限制与边界
- 只提交 Skill 与必要资源；正式案例、白板与对照结果由平台提供，不预置任何正式断言。
- 断言必须忠实原文；找不到证据、证据不足的明确标注，不编造支撑。
- 运行预算有限：先落地完整断言结构，再增量改进；始终先保存诚实的部分成果。
