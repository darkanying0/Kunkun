---
name: literature-knowledge-graph
description: 从多篇科研论文（JATS 段落化文本）抽取实体与关系、绑定段落级证据，构建可查询、可回溯的知识图谱，并按图谱结构生成可编辑学术 PPT（含证据映射、讲稿备注与真实渲染预览）。当任务要求实体关系抽取、别名归一、来源绑定、图谱查询或增量更新时使用。输入为 corpus-manifest + 段落化 JSON，输出为 result.json + 图谱结构 + 幻灯片。
---

# literature-knowledge-graph：文献知识图谱构建

本 Skill 从多篇科研论文的段落化文本（JATS）中抽取实体与关系、绑定段落级证据，构建**可查询、可回溯**的知识图谱，并可把图谱组织成一份**可编辑学术 PPT**（正文为实体/关系/查询结果，讲稿备注保留原文短引+来源定位）。核心原则：**抽得准、连得对、对得齐、查得到回得去；找不到证据或证据冲突的明确标注，绝不编造。**

## 何时使用
- 任务要求实体关系抽取、实体对齐、来源绑定、图谱查询或增量更新一批论文。
- 任务要求交付图谱可视化幻灯片、且需要真实渲染预览（PDF/PNG）供检查。

## 输入约定（重要，本题为段落化 JSON，非 PDF）
输入位于 `/input/`：
- `corpus-manifest.json`：各论文的 DOI、作者、来源哈希、许可证；
- `material.json`：两篇正文段落的汇总索引；
- `primary-material.json`：第一篇论文正文（**根 DOI/title/authors 属于本篇**）；
- `secondary-material.json`：第二篇（新增）论文正文。

**证据定位用 JATS 段落 ID（`paragraph_id`），不是 PDF 页码**；本包无 PDF 页码，不得把自建「第 1 页」当作原 PDF 页。正文行内公式/上下标已线性化；不提供图像像素、补充附件、底层临床/实验数据，不得推断其中数值。未报告和源内冲突明确保留。

## 执行流程（严格按顺序）

### 第 1 步：读输入与任务边界
1. 读 `/input/case.json`：拿 `case_id`、`output_contract` 字段清单。
2. 读 `/input/task.md`：拿评分证据范围与图谱要求。
3. 读 `/input/corpus-manifest.json` 确认各论文 `source_id`（primary / secondary）。

### 第 2 步：加载段落化正文
```bash
python3 /skills/weekly-skill/scripts/load_material.py /input /app/work
```
产出 `/app/work/materials.json`（每段带 `source_id`、`paragraph_id`、`text`），供后续抽取使用。两篇论文分别保留独立 `source_id`，不得把第一篇的 DOI/title/authors 套到第二篇。

### 第 3 步：实体识别（抽得准）
抽取**论文里真实出现**的科研对象：研究者、材料、方法、任务、指标、结论；保留原文表述与 `paragraph_id`。不凭常识补全论文未出现的概念；区分作者自述与他人转述。

### 第 4 步：关系抽取（连得对）
只建立有证据支持的关系；关系类型用受控词表（如 使用/比较/优于/支持/矛盾），明确**方向**与**适用条件**。共现、综述转述、推测不得当成直接证据。

### 第 5 步：实体对齐（对得齐）
1. 跨篇处理别名、缩写、大小写、全称与简称、同名实体。
2. **只合并有依据的同一概念**，记录合并依据；不同对象、同名冲突**不得合并**，记录冲突原因。
3. 相同通用方法/材料术语≠相同物理样品、模型实例、数据集或实验条件；不得把不同论文的条件、样本、数值结果合成一个结论。
4. 同篇多种文件格式不算跨篇证据。

### 第 6 步：来源绑定（查得到回得去）
每个节点和每条边带 `{source_id, paragraph_id, quote}`（原文短引）。合并与冲突处置写入 `change_records`。

### 第 7 步：构建并导出图谱
把图谱写成 `/app/work/graph.json`（`nodes` + `edges`，见 `README.md`），然后：
```bash
python3 /skills/weekly-skill/scripts/export_graph.py /app/work/graph.json /app/work
```
产出可读的 `graph.md` 与 `graph.graphml`。**至少执行 3 个真实查询**（如「材料 X 与哪些对象有比较关系」「方法 M 在哪些论文中被使用」「指标 K 由哪些结论支持」），每个查询给出结果子图、支撑证据与无法确定的关系。

### 第 8 步：生成可编辑学术 PPT（推荐，默认执行）
```bash
python3 /skills/weekly-skill/scripts/build_ppt.py /app/work/graph.json /app/output
```
产出：
- `/app/output/paper_slides.pptx`：可编辑 PPTX，按图谱结构分页（标题/实体/关系/查询结果），**讲稿备注保留原文短引 + source_id/paragraph_id 证据**；
- `/app/output/preview.pdf` 与 `/app/output/preview_png/*.png`：真实渲染预览（office-renderer 转 PDF，pdf-render-tool 转 PNG）。

### 第 9 步：写 result.json
写 `/app/output/result.json`，必须包含：
```json
{
  "case_id": "<来自 case.json>",
  "status": "success|partial|failed|refused",
  "status_reason": "<简述；partial/failed/refused 给出原因与可人工接管位置>",
  "result": { "nodes": [...], "edges": [...], "queries": [...], "merges": [...], "conflicts": [...] },
  "evidence": [ {"source_id": "...", "paragraph_id": "...", "quote": "..."} ],
  "uncertainty": [ {"item": "...", "reason": "证据不足|来源缺失|冲突|未报告"} ],
  "change_records": [ {"action": "...", "reason": "..."} ],
  "artifacts": { "graph_json": "...", "graph_md": "...", "pptx": "...", "preview_pdf": "..." }
}
```
**必须**再从 `/input/case.json` 的 `output_contract` 读取所有字段名，把它们的值一并写入 `result`，一个都不能漏。每个节点/边都要能在 `evidence` 里回到原文段落。

## 工具回退（脚本依赖缺失时）
- 段落文本直接读 JSON，无需 PDF 工具；若正文混入 XML，可用 `latex-compiler`/文本工具辅助还原行内公式。
- **幻灯片回退**：`python-pptx` 不可用时生成自包含 HTML 幻灯片，再用 office-renderer 转 PDF/PNG。
- **图谱导出回退**：GraphML 不可生成时至少导出 JSON + Markdown。

## 限制与边界
- 只提交 Skill 与必要资源；正式案例与对照由平台提供，不预置任何图谱答案。
- 实体/关系必须忠实原文；不推断图像/补充/底层数据中的数值；不合成跨篇结论。
- 运行预算有限：先落地节点+边+查询，再增量改进；始终先保存诚实的部分成果。
