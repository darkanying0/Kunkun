---
name: paper-to-academic-ppt
description: 把一篇论文组织成可讲解、可核验、可编辑的学术 PPT：提取论文主线、设计页级主张与图表引用、按给定模板（master/layout）改编版面、生成与页面分离的讲稿备注，并产出真实渲染 PDF/PNG 预览与页级证据映射。当任务要求论文转汇报幻灯片、按模板生成演示文件或做页级证据追溯时使用。输入为论文 PDF + 模板/起始 deck，输出为 result.json + 可编辑 PPTX + 预览 + 页级证据映射。
---

# paper-to-academic-ppt：论文转学术 PPT

本 Skill 把一篇论文组织成**可讲解、可核验、可编辑的学术 PPT**：提取论文主线、设计页级主张、为每页挂论文图/表/章节证据、按给定模板（master/layout）改编版面、生成**与页面文字分离**的讲稿备注，并产出真实渲染预览。核心原则：**主线要立得住、每页回得去、模板排得下、打开就能放映**；不是把段落切块贴进页面。

## 何时使用
- 任务要求论文转汇报幻灯片、按模板生成可编辑演示文件、页级证据追溯或讲解备注生成。
- 任务要求交付可编辑演示文件、且需要真实渲染预览（PDF/PNG）供检查。
- **纯问答/润色/绘图美化等非"论文转 PPT"场景不触发**。

## 执行流程（严格按顺序）

### 第 1 步：读输入与任务边界
1. 读 `/input/case.json`：拿 `case_id`、论文路径、**模板路径（master/layout 型 .pptx）**、起始 deck 路径（若有）、听众/时长/页数上限、`output_contract`。
2. 读 `/input/task.md`（若存在）：拿评分口径与约束（固定听众、时长、页数）。
3. 确认交付目标：围绕论文主线讲清楚，而非按段落顺序搬运。

### 第 2 步：解析论文（证据来源）
```bash
python3 /skills/weekly-skill/scripts/parse_pdf.py <论文.pdf> /app/work
```
产出 `/app/work/structured.json`（章节/阅读顺序/图表/段落，每块带页级 `{page,x0,y0,x1,y1}`）。**图表编号、单位、图注、数据来源都从这里取，防止张冠李戴。**

### 第 3 步：提取主线（主线立得住）
识别论文要解决的问题、核心做法、关键证据、结论与限制，形成**页序可讲的叙事骨架**：区分主结论与支撑性细节，不逐段搬运摘要。

### 第 4 步：设计页级主张 + 图表引用（每页回得去）
1. 一页一个主张；每页写清要点数量与层级，长段落改写为可讲述短语，控制单页信息密度。
2. 每页挂论文的图/表/公式/数据来源：保留**编号、单位、图注、必要条件说明**；示意图不当实验数据展示，不搬改数值与单位。

### 第 5 步：写讲稿备注（与页面分离）
为每页生成**不重复页面文字**的讲稿：说明过渡、强调点、被问到时能补充的证据。页面讲什么、备注讲"怎么讲"。

### 第 6 步：按模板改编版面（模板排得下）
把页级大纲写成 `/app/work/outline.json`（格式见 `README.md`），然后：
```bash
python3 /skills/weekly-skill/scripts/build_ppt.py /app/work/outline.json /app/output --template <模板.pptx> [--deck <起始deck.pptx>]
```
脚本**加载给定模板的 slide master/layout** 增页并填占位符，保留模板的标题/页脚/配色/字号层级；起始 deck 若提供则在其上改编。产出：
- `/app/output/paper_slides.pptx`：可编辑演示文件（继承模板版式）；
- `/app/output/preview.pdf` 与 `/app/output/preview_png/*.png`：真实渲染预览（office-renderer 转 PDF，pdf-render-tool 转 PNG）。

### 第 7 步：写 result.json（可核验）
写 `/app/output/result.json`，必须包含：
```json
{
  "case_id": "<来自 case.json>",
  "status": "success|partial|failed|refused",
  "status_reason": "<简述；partial/failed/refused 给出原因与可人工接管位置>",
  "result": {
    "deliverable": {"pptx": "...", "main_thread": "..."},
    "slides": [ {"page":1, "title":"...", "claim":"...", "points":[...],
                 "evidence":{"kind":"figure|table|section|data","ref":"Fig.1","page":3,"quote":"...","note":"..."},
                 "notes":"..."} ],
    "render": {"preview_pdf": "...", "font_template": "..."}
  },
  "evidence": [ {"page":1, "kind":"figure", "ref":"Fig.1", "source_page":3} ],
  "uncertainty": [ {"item":"...", "reason":"图表无法提取|公式为图片|模板占位符不足|字体缺失"} ],
  "change_records": [ {"action":"...", "reason":"..."} ],
  "artifacts": { "pptx":"...", "preview_pdf":"...", "outline_json":"..." }
}
```
**必须**再从 `/input/case.json` 的 `output_contract` 读取所有字段名，把它们的值一并写入 `result`。每页都能回溯到论文的具体图/表/章节/数据，不改写事实。

## 工具回退（脚本依赖缺失时）
- **论文文字提取**：`pdf-text-tool` → `pdftotext -bbox` → `pdftotext -layout`；图表/公式为图片时标注，不硬提取数值。
- **PPT 生成回退**：`python-pptx` 不可用时生成自包含 HTML 幻灯片，再用 office-renderer 转 PDF/PNG；**模板约束优先，无模板时用最接近版式**。
- **渲染回退**：无 office-renderer 时至少交付可编辑源文件 + 说明。

## 限制与边界
- 只提交 Skill 与必要资源；正式案例、模板与对照由平台提供，不预置任何正式幻灯片。
- 不负责论文精读结论生成、科研绘图美化、学术润色；只负责"论文内容如何变成可讲、可核验、可编辑的 PPT"。
- 不搬改数值/单位；图表编号与正文引用一致；模板被覆盖时优先恢复模板版式。
- 运行预算有限：先落地主线必需页 + 证据映射，再增量改进；始终先保存诚实的部分成果。
