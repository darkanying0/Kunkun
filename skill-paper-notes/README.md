# paper-structured-notes：科研论文结构化笔记 Skill

把科研论文整理成**与论文章节对齐、字段齐备、可回到原文**的结构化笔记，并可按论文结构生成**可编辑学术 PPT**（正文为笔记、讲稿备注保留原文片段+页级证据、真实渲染预览）。面向「文献总结与结构化笔记」类赛题（如 阅读10｜文献总结与结构化笔记，challenge `product-arena-06-6d8cf72b`）。

## 1. 用途与适用条件

- **用途**：章节总结、论文卡片、知识点提取、来源回链、可检索笔记；把论文组织成汇报幻灯片。
- **适用**：有文字层的单/双栏科研 PDF；部分扫描件（配合 OCR）。
- **不适用**：加密 PDF（直接拒答）；笔记是对原文的结构化提炼，不是压缩式通读摘要。

## 2. 文件结构

```
SKILL.md              Skill 本体（frontmatter + 笔记流程 + 回退与异常）
scripts/parse_pdf.py   PDF -> structured.json（阅读顺序 + 页级证据，复用解析器）
scripts/build_ppt.py   notes.json -> 可编辑笔记 PPT + 渲染预览
README.md              本说明
requirements.txt       可选 Python 依赖
examples/example_usage.md  最小调用示例
```

## 3. 调用步骤

```bash
# 1) 读输入
cat /input/case.json      # case_id、材料路径、output_contract、字段口径
cat /input/task.md

# 2) 解析原文（对得上）
python3 scripts/parse_pdf.py <论文.pdf> /app/work   # -> /app/work/structured.json

# 3) 建论文卡片、章节总结、知识点（由 DeepSeek Harness 按 SKILL.md 完成）
#    产出 /app/work/notes.json

# 4) 生成可编辑学术 PPT + 渲染预览
python3 scripts/build_ppt.py /app/work/notes.json /app/output
# -> paper_slides.pptx、preview.pdf、preview_png/*.png

# 5) 写 /app/output/result.json（case_id + output_contract 全字段 + evidence/uncertainty/change_records）
```

## 4. 输入输出契约

**输入**：`/input/case.json`（`case_id`、材料路径、`output_contract`）；`/input/task.md`；材料 PDF。

**中间产物 `/app/work/notes.json`**：

| 字段 | 说明 |
|-|-|
| `title` | 论文标题 |
| `paper_card` | `{research_question, data, methods, main_findings, conclusions, limitations}` 统一字段 |
| `sections` | 每节 `{heading, page, bbox, purpose, method, result, conclusion}` |
| `knowledge_points` | `[{concept, statement, page, evidence, relation}]` 可检索条目 |
| `references` | 参考文献 |

**输出 `/app/output/result.json`**：

| 字段 | 说明 |
|-|-|
| `case_id` | 必填 |
| `status` | `success` / `partial` / `failed` / `refused` |
| `status_reason` | partial/failed/refused 给出原因与可人工接管位置 |
| `result` | 结构化笔记，并覆盖 `output_contract` 全字段 |
| `evidence` | 每条笔记的 `{page, region, kind}` 锚点 |
| `uncertainty` | 未报告/无法判断/材料缺失/冲突 |
| `change_records` | 章节切分、知识点归并、锚点校验等动作 |
| `artifacts` | structured/notes/pptx/preview 路径 |

## 5. 关键方法（对应四能力点）

1. **对得上**：复用 `parse_pdf.py` 的章节/阅读顺序识别，笔记骨架跟随论文自身章节与论证顺序，不用通用模板硬套。
2. **留得住**：论文卡片记录研究问题、数据、方法、主要发现、结论、局限；保留让结论成立的前提条件。
3. **找得回**：每条笔记/知识点/数值带 `{page, region, kind}` 锚点，指回具体章节、段落、页码或图表。
4. **用得上**：知识点拆成可检索条目，处理术语/缩写/同义表述，避免重复与矛盾；字段可并排比较。

## 6. 依赖与环境

- 首选：`pymupdf`、`pdfplumber`、`python-pptx`（见 `requirements.txt`）。
- 兜底：`pdftotext`/`pdftoppm`（poppler-utils）、`libreoffice`（渲染预览）。
- 平台声明工具：`pdf-text-tool`、`pdf-render-tool`、`ocr-tool`、`office-renderer`、`scientific-python` 等；缺库时按 SKILL.md「工具回退」手动完成。
- 提交约束：≤50 个 UTF-8 文本文件、单文件≤500KB、总计≤2MB、无符号链接。

## 7. 异常处理

| 异常 | 处置 |
|-|-|
| 加密 PDF | `status=refused`，说明原因，不硬解 |
| 无文字层扫描件 | 渲染 + OCR，低置信度进 `uncertainty` |
| 双栏错序 | 复用 parse_pdf.py 阅读顺序校正 |
| 图表/公式缺失 | 标注「图片型/未结构化」，不编造 |
| 超长文 / 非中文论文 | 分段处理；语言不影响结构提取 |
| 原文残缺/冲突 | 进 `uncertainty`，不写成事实 |

## 8. 自查清单

- [ ] 笔记骨架与论文章节/论证顺序一致（对得上）
- [ ] 研究问题/数据/方法/发现/结论/局限齐备（留得住）
- [ ] 每条关键笔记/数值/变量可回到原文锚点（找得回）
- [ ] 知识点可检索、术语一致、无重复/矛盾（用得上）
- [ ] 先保存诚实部分成果，再增量改进
