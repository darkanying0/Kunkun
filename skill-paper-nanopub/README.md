# paper-nanopublication：科研论文断言拆解与证据绑定 Skill

把科研论文关键结论拆成**可独立判断真假的断言**，为每条断言绑定**最小充分证据片段**与**来源元数据**，输出**可机器读取**的 Nanopublication 结构，并按论文结构生成**可编辑学术 PPT**（正文为断言、讲稿备注保留证据片段+页级证据、真实渲染预览）。面向「Nanopublication」类赛题（如 阅读14｜Nanopublication，challenge `product-arena-09-0e8befd4`）。

## 1. 用途与适用条件

- **用途**：断言拆解、证据绑定、来源元数据、质量检查、结构化导出；把论文组织成汇报幻灯片。
- **适用**：有文字层的单/双栏科研 PDF；部分扫描件（配合 OCR）。
- **不适用**：加密 PDF（直接拒答）；断言必须忠实原文，不编造支撑。

## 2. 文件结构

```
SKILL.md              Skill 本体（frontmatter + 断言流程 + 回退与异常）
scripts/parse_pdf.py   PDF -> structured.json（阅读顺序 + 页级证据，复用解析器）
scripts/build_ppt.py   nanopub.json -> 可编辑断言 PPT + 渲染预览
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

# 3) 拆断言、绑证据、记来源（由 DeepSeek Harness 按 SKILL.md 完成）
#    产出 /app/work/nanopub.json

# 4) 生成可编辑学术 PPT + 渲染预览
python3 scripts/build_ppt.py /app/work/nanopub.json /app/output
# -> paper_slides.pptx、preview.pdf、preview_png/*.png

# 5) 写 /app/output/result.json（case_id + output_contract 全字段 + evidence/uncertainty/change_records）
```

## 4. 输入输出契约

**输入**：`/input/case.json`（`case_id`、材料路径、`output_contract`）；`/input/task.md`；材料 PDF。

**中间产物 `/app/work/nanopub.json`**：

| 字段 | 说明 |
|-|-|
| `title` | 论文标题 |
| `provenance` | `{paper, authors, year, version, identifier}` 来源元数据 |
| `nanopublications` | `[{id, subject, relation, object, assertion, evidence, page, bbox, evidence_type, confidence}]` |
| `quality_checks` | `[{check, status, detail}]` 质量检查记录 |
| `references` | 参考文献 |

**输出 `/app/output/result.json`**：

| 字段 | 说明 |
|-|-|
| `case_id` | 必填 |
| `status` | `success` / `partial` / `failed` / `refused` |
| `status_reason` | partial/failed/refused 给出原因与可人工接管位置 |
| `result` | nanopublications + quality_checks + provenance，并覆盖 `output_contract` 全字段 |
| `evidence` | 每条断言的 `{page, region, kind}` 锚点 |
| `uncertainty` | 证据不足/来源缺失/断言过宽/无法判断 |
| `change_records` | 拆解、归并、去重、锚点校验等动作 |
| `artifacts` | structured/nanopub/pptx/preview 路径 |

## 5. 关键方法（对应四能力点）

1. **拆得细**：把结论拆成单一可验证断言，保留条件与限定范围，处理复合句并列/因果/让步。
2. **对得上**：每条断言绑定最小充分证据片段，区分直接证据与间接推论，指回原文 `{page, region}`。
3. **追得回**：断言→证据→论文/作者/年份/版本→标识符 链路完整，可回原文逐条核验。
4. **读得懂**：受控词表关系类型、字段与序列化形态规范，下游程序可直接解析。

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
| 证据跨图表/公式 | 标注图片型，指回图表位置 |
| 断言找不到支撑片段 | 进 `uncertainty`，不编造证据 |
| 断言与证据冲突 | 质量检查记录，标注冲突 |
| 字段缺失 | 进 `uncertainty`，说明原因 |

## 8. 自查清单

- [ ] 断言单一、可验证，条件与限定范围保留（拆得细）
- [ ] 每条断言绑定最小充分证据片段并指回原文（对得上）
- [ ] 断言/证据/来源/标识符链路完整（追得回）
- [ ] 导出结构符合字段与序列化约定，可机器解析（读得懂）
- [ ] 先保存诚实部分成果，再增量改进
