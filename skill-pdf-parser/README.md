# paper-pdf-parser：科研论文 PDF 结构化解析 Skill

把科研论文 PDF 解析成「可回到原文页码/区块」的结构化结果，并可按论文结构生成**可编辑学术 PPT**（含页级证据映射、讲稿备注与真实渲染预览）。面向「文献文档解析」类赛题（如 阅读01｜文献文档解析，challenge `product-arena-08-3027d350`）。

## 1. 用途与适用条件

- **用途**：解析、翻译、问答、提取、核验、知识结构化的前置步骤；把论文组织成汇报幻灯片。
- **适用**：有文字层的双栏/单栏科研 PDF；部分扫描件（配合 OCR）。
- **不适用**：加密 PDF（直接拒答）；图表与公式只做结构元素识别，不解读科学含义。

## 2. 文件结构

```
SKILL.md             Skill 本体（YAML frontmatter: name/description）
scripts/parse_pdf.py PDF -> structured.json（带坐标、列检测、阅读顺序、表格/公式/图/参考文献）
scripts/build_ppt.py structured.json -> 可编辑 PPTX + 渲染预览
README.md            本说明
requirements.txt     可选 Python 依赖（缺库时自动回退）
examples/example_usage.md  最小调用示例
```

## 3. 调用步骤

```bash
# 第 1 步：读输入
cat /input/case.json          # case_id、材料路径、output_contract、任务说明
cat /input/task.md            # 案例要求与评分证据范围（若存在）

# 第 2 步：解析 PDF
python3 scripts/parse_pdf.py <论文.pdf> /app/work
# 产出 /app/work/structured.json（blocks/pages/reading_order/sections/tables/elements/evidence）

# 第 3 步：核验（用渲染页比对阅读顺序、表格、公式）

# 第 4 步：生成可编辑学术 PPT + 渲染预览
python3 scripts/build_ppt.py /app/work/structured.json /app/output
# 产出 paper_slides.pptx、preview.pdf、preview_png/*.png

# 第 5 步：写 /app/output/result.json（含 case_id + output_contract 全部字段 + status/evidence/uncertainty/change_records）
```

## 4. 输入输出契约

**输入**：`/input/case.json`（含 `case_id`、材料路径、`output_contract` 字段清单）；`/input/task.md`；材料 PDF。

**输出** `/app/output/result.json`：

| 字段 | 说明 |
|-|-|
| `case_id` | 来自 case.json，必填 |
| `status` | `success` / `partial` / `failed` / `refused` |
| `status_reason` | partial/failed/refused 必须给出原因与可人工接管位置 |
| `result` | 结构化解析结果（逐字内容）；并覆盖 case.json `output_contract` 的所有字段 |
| `evidence` | 每个关键结论的 `{page, region, kind}` 证据映射 |
| `uncertainty` | 未报告 / 无法判断 / 材料缺失 / OCR 不确定项 |
| `change_records` | 校正动作与原因 |
| `artifacts` | structured.json / pptx / preview 路径 |

## 5. 关键方法

1. **文字层提取**：PyMuPDF(fitz) → pdfplumber → `pdftotext -bbox` → `pdftotext -layout` 四级回退，优先拿到带坐标的文本块。
2. **多栏阅读顺序**（排得对）：按页做列检测——跨中线块判为通栏，其余按 x 归属左/右栏；排序规则「通栏 → 左栏自上而下 → 右栏自上而下」；图片按 y 插入到紧随其后的文本之前。
3. **结构识别**（拆得清）：标题/章节用正则识别；表格用 pdfplumber `extract_tables` 与 PyMuPDF `find_tables`；公式按数学符号/结构特征识别；图片按 PyMuPDF 图片块识别。
4. **证据映射**（核得回）：每个文本/图片块保留 `{page, x0, y0, x1, y1, column}`，读不出的部分进 `uncertainty`，不猜。
5. **扫描件 OCR**：页面无文字层时渲染 300 DPI 图片后用 `ocr-tool`，低置信度标注。

## 6. 依赖与环境

- 首选：`pymupdf`、`pdfplumber`、`python-pptx`（见 `requirements.txt`）。
- 兜底：`pdftotext` / `pdftoppm`（poppler-utils）、`libreoffice`（渲染预览）。
- 平台声明工具：`pdf-text-tool`、`pdf-render-tool`、`ocr-tool`、`office-renderer`、`scientific-python`、`latex-compiler` 等；脚本缺库时按 SKILL.md 的「工具回退」手动完成。
- 提交约束：≤50 个 UTF-8 文本文件、单个 ≤500KB、总计 ≤2MB、无符号链接。

## 7. 异常处理

| 异常 | 处置 |
|-|-|
| 加密 PDF | `status=refused`，说明原因，不硬解 |
| 无文字层扫描件 | 渲染 + OCR，低置信度进 `uncertainty` |
| 图片型表格 | 渲染区域图保留，标注「图片型表格，未结构化」 |
| 乱码字体 / 页码错乱 | 逐字提取失败的部分如实标注，不猜测 |
| 脚本依赖缺失 | 按 SKILL.md「工具回退」用声明工具手动完成 |

## 8. 自查清单

- [ ] 覆盖标题、作者与单位、摘要、章节层级、图表与题注、公式编号、参考文献、页眉页脚与脚注
- [ ] 每个关键结论都能回到 `{page, region}`
- [ ] 未报告/无法判断项写进 `uncertainty` 而非当成事实
- [ ] 先保存诚实部分成果，再增量改进
