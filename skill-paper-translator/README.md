# paper-pdf-translator：科研论文 PDF 翻译 Skill

把科研论文 PDF 翻译成**可回到原文页码/段落**的双语对照结果，并可按论文结构生成**可编辑学术 PPT**（正文用译文、讲稿备注保留原文+术语+页级证据、真实渲染预览）。面向「文献翻译」类赛题（如 阅读03｜文献翻译，challenge `product-arena-01-5a9928c1`）。

## 1. 用途与适用条件

- **用途**：术语一致的文献翻译、长文分段续译、双语段落对照、译文核验；把论文组织成汇报幻灯片。
- **适用**：有文字层的单/双栏科研 PDF（目标语言通常为中文）；部分扫描件（配合 OCR）。
- **不适用**：加密 PDF（直接拒答）；图表与公式只保留编号/位置/原文形式，不解读科学含义。

## 2. 文件结构

```
SKILL.md              Skill 本体（frontmatter + 翻译流程 + 回退与异常）
scripts/parse_pdf.py   PDF -> structured.json（阅读顺序 + 页级证据，复用解析器）
scripts/build_ppt.py   translation.json -> 可编辑双语 PPT + 渲染预览
README.md              本说明
requirements.txt       可选 Python 依赖
examples/example_usage.md  最小调用示例
```

## 3. 调用步骤

```bash
# 1) 读输入
cat /input/case.json      # case_id、材料路径、output_contract、目标语言/术语口径
cat /input/task.md

# 2) 解析原文（段落全）
python3 scripts/parse_pdf.py <论文.pdf> /app/work   # -> /app/work/structured.json

# 3) 建术语表并逐段翻译（由 DeepSeek Harness 按 SKILL.md 完成）
#    产出 /app/work/translation.json（双语对照 + 术语表 + 核验记录）

# 4) 生成可编辑学术 PPT + 渲染预览
python3 scripts/build_ppt.py /app/work/translation.json /app/output
# -> paper_slides.pptx、preview.pdf、preview_png/*.png

# 5) 写 /app/output/result.json（case_id + output_contract 全字段 + evidence/uncertainty/change_records）
```

## 4. 输入输出契约

**输入**：`/input/case.json`（`case_id`、材料路径、`output_contract`）；`/input/task.md`；材料 PDF。

**中间产物 `/app/work/translation.json`**（由翻译环节写出）：

| 字段 | 说明 |
|-|-|
| `title` | `{source, translation}` |
| `term_table` | `[{source, target, note}]` 术语表（全篇锁定同一译名） |
| `sections` | 每节 `heading{source,translation}` + `paragraphs[]` |
| `paragraphs[i]` | `{id, source, translation, page, bbox, terms[], verification{status,note}}` |
| `references` | 参考文献 `{text, translation}` |

**输出 `/app/output/result.json`**：

| 字段 | 说明 |
|-|-|
| `case_id` | 必填 |
| `status` | `success` / `partial` / `failed` / `refused` |
| `status_reason` | partial/failed/refused 给出原因与可人工接管位置 |
| `result` | 双语对照结果，并覆盖 `output_contract` 全字段 |
| `evidence` | 每段译文的 `{page, region, kind}` 证据 |
| `uncertainty` | 未报告/无法判断/材料缺失/译法有歧义 |
| `change_records` | 术语回填、段落拼接、核验修正等动作 |
| `artifacts` | structured/translation/pptx/preview 路径 |

## 5. 关键方法（对应四能力点）

1. **术语稳**：先抽术语建表，标题/摘要/正文/图注/结论统一译名；每段声明 `terms`，新术语定名后回填已译段落。
2. **段落全**：复用 `parse_pdf.py` 的阅读顺序校正（通栏→左栏→右栏→参考文献），跨页/跨栏段落先拼接完整再译，段号一一对应。
3. **关系准**：携带上下文翻译，指代/否定/限定/因果/让步与原文一致；数字、单位、公式、图表编号、文献标记 `[n]` 逐字保留。
4. **可核验**：每段译文带 `page/bbox` 证据 + `verification` 核验记录；译不准处进 `uncertainty`，不写含糊事实。

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
| 公式/表格为图片 | 保留编号与位置，标注「图片型，未结构化」 |
| 原文残缺/语言混杂 | 残缺处标注，不补造 |
| 译法有歧义 | 进 `uncertainty` 并给出可人工确认清单 |

## 8. 自查清单

- [ ] 术语在标题/摘要/正文/图注/结论中一致，术语表被真正执行
- [ ] 跨页/跨栏段落完整、段号一一对应、无漏译/重复
- [ ] 数字/单位/公式/图表编号/文献标记与原文一致
- [ ] 每段译文可回到原文页码/段落，译不准处已标注
- [ ] 先保存诚实部分成果，再增量改进
