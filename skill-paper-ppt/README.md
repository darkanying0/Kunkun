# paper-to-academic-ppt：论文转学术 PPT Skill

把一篇论文组织成**可讲解、可核验、可编辑的学术 PPT**：提取主线、设计页级主张与图表引用、按给定模板（master/layout）改编版面、生成与页面分离的讲稿备注，并产出真实渲染 PDF/PNG 预览与页级证据映射。面向「论文转学术 PPT」类赛题（challenge `ppt-c7b80f0d`）。

## 1. 用途与适用条件

- **用途**：论文主线提取、页结构与信息分层、图表引用与证据保留、讲解逻辑与备注、模板约束与版面适配、导出渲染与可编辑性。
- **适用**：论文 PDF + 给定模板（master/layout 型 .pptx）+ 可选起始 deck；固定听众/时长/页数约束。
- **不适用**：不负责精读结论生成、科研绘图美化、学术润色；不搬改数值/单位。

## 2. 文件结构

```
SKILL.md              Skill 本体（frontmatter + 论文转 PPT 流程 + 回退与异常）
scripts/parse_pdf.py   论文 PDF -> structured.json（页级证据基础，复用解析器）
scripts/build_ppt.py    outline.json -> 按模板改编的可编辑 PPTX + 渲染预览
README.md               本说明
requirements.txt        可选 Python 依赖
examples/example_usage.md  最小调用示例
```

## 3. 调用步骤

```bash
# 1) 读输入
cat /input/case.json      # case_id、论文路径、模板路径、deck 路径、听众/时长/页数、output_contract
cat /input/task.md

# 2) 解析论文（证据来源）
python3 scripts/parse_pdf.py <论文.pdf> /app/work      # -> /app/work/structured.json

# 3) 提取主线、设计页级主张+图表引用、写讲稿（由 DeepSeek Harness 按 SKILL.md 完成）
#    产出 /app/work/outline.json

# 4) 按模板改编版面 + 渲染预览
python3 scripts/build_ppt.py /app/work/outline.json /app/output --template <模板.pptx> [--deck <deck.pptx>]

# 5) 写 /app/output/result.json（case_id + output_contract 全字段 + 页级证据映射）
```

## 4. 输入输出契约

**输入**：`/input/case.json`（`case_id`、论文路径、模板路径、deck 路径、听众/时长/页数、`output_contract`）；`/input/task.md`；论文 PDF；模板 .pptx。

**中间产物 `/app/work/outline.json`**：

| 字段 | 说明 |
|-|-|
| `title` | 论文标题 |
| `main_thread` | 一句话主线 |
| `slides` | `[{title, claim, points, evidence{kind,ref,page,quote,note}, notes}]` |

**输出 `/app/output/result.json`**：

| 字段 | 说明 |
|-|-|
| `case_id` | 必填 |
| `status` | `success` / `partial` / `failed` / `refused` |
| `status_reason` | partial/failed/refused 给出原因与可人工接管位置 |
| `result` | deliverable + slides + render，并覆盖 `output_contract` 全字段 |
| `evidence` | 每页 `{page, kind, ref, source_page}` 页级证据映射 |
| `uncertainty` | 图表无法提取/公式为图片/模板占位符不足/字体缺失 |
| `change_records` | 页级改动与理由 |
| `artifacts` | pptx/preview_pdf/outline_json 路径 |

## 5. 关键方法（对应六要素）

1. **主线提取**：识别问题/做法/证据/结论/限制，形成页序可讲叙事骨架，区分主结论与支撑细节。
2. **页结构与信息分层**：一页一主张，控制单页信息密度，长段落改写成可讲述短语。
3. **图表引用与证据保留**：每页挂图/表/公式/数据来源，保留编号/单位/图注/必要条件，防张冠李戴。
4. **讲解逻辑与备注**：备注不重复页面文字，说明过渡、强调点与可补充证据。
5. **模板约束与版面适配**：加载模板 slide master/layout 增页填占位符，保留页脚/配色/字号。
6. **导出渲染与可编辑性**：真实 PDF/PNG 预览，源文件可逐页编辑、可复跑同一版式。

## 6. 依赖与环境

- 首选：`python-pptx`（PPT 生成）、`pymupdf`/`pdfplumber`（PDF 提取）。
- 兜底：`pdftotext`/`pdftoppm`、`libreoffice`（渲染预览）。
- 平台声明工具：`pdf-text-tool`、`office-renderer`、`scientific-python` 等。
- 提交约束：≤50 个 UTF-8 文本文件、单文件≤500KB、总计≤2MB、无符号链接。

## 7. 异常处理

| 异常 | 处置 |
|-|-|
| 图表无法提取 | 标注图片型证据，不硬提取数值 |
| 公式为图片 | 保留原图引用，不重排 |
| PDF 加密 | `status=refused`，说明原因 |
| 模板占位符不足 | 自建文本框兜底，优先恢复模板版式 |
| 字体缺失 | 标注，用最接近字体 |
| 页数超限 | 合并支撑性细节页，保主线必需页 |

## 8. 自查清单

- [ ] 主线与论文自身贡献一致，非按段落顺序搬运
- [ ] 每页可回溯到图/表/章节/数据，编号/单位/图注一致
- [ ] 讲稿备注与页面文字分离
- [ ] 模板页脚/配色/字号层级被保留
- [ ] 有真实 PDF/PNG 渲染预览，源文件可编辑
- [ ] 先保存诚实部分成果，再增量改进
