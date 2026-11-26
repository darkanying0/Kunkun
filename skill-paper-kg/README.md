# literature-knowledge-graph：文献知识图谱构建 Skill

从多篇科研论文（JATS 段落化文本）抽取实体与关系、绑定段落级证据，构建**可查询、可回溯**的知识图谱，并按图谱结构生成**可编辑学术 PPT**（正文为图谱、讲稿备注保留原文短引+来源定位、真实渲染预览）。面向「文献知识图谱构建」类赛题（如 阅读15｜文献知识图谱构建，challenge `product-arena-10-760d1a0b`）。

## 1. 用途与适用条件

- **用途**：实体识别、实体对齐、关系抽取、来源绑定、图谱查询、增量更新。
- **适用**：有段落化正文（JATS JSON）的多篇论文；输入为 `corpus-manifest.json` + `material.json` + `primary-material.json` + `secondary-material.json`。
- **不适用**：实体/关系必须忠实原文，不推断图像/补充/底层数据中的数值，不合成跨篇结论。

## 2. 文件结构

```
SKILL.md                Skill 本体（frontmatter + 图谱流程 + 回退与异常）
scripts/load_material.py  段落化正文 -> materials.json（source_id + paragraph_id + text）
scripts/export_graph.py    graph.json -> graph.md + graph.graphml
scripts/build_ppt.py       graph.json -> 可编辑图谱 PPT + 渲染预览
README.md                  本说明
requirements.txt           可选 Python 依赖
examples/example_usage.md  最小调用示例
```

## 3. 调用步骤

```bash
# 1) 读输入
cat /input/case.json /input/task.md
cat /input/corpus-manifest.json

# 2) 加载段落化正文
python3 scripts/load_material.py /input /app/work   # -> /app/work/materials.json

# 3) 抽取实体/关系、对齐、绑定证据（由 DeepSeek Harness 按 SKILL.md 完成）
#    产出 /app/work/graph.json

# 4) 导出图谱
python3 scripts/export_graph.py /app/work/graph.json /app/work
# -> /app/work/graph.md、graph.graphml

# 5) 生成可编辑图谱 PPT + 渲染预览
python3 scripts/build_ppt.py /app/work/graph.json /app/output

# 6) 写 /app/output/result.json（case_id + output_contract 全字段 + evidence/uncertainty/change_records）
```

## 4. 输入输出契约

**输入**：`/input/case.json`（`case_id`、`output_contract`）；`/input/task.md`；`corpus-manifest.json`；`material.json`；`primary-material.json`；`secondary-material.json`。

**中间产物 `/app/work/graph.json`**：

| 字段 | 说明 |
|-|-|
| `topic` | 图谱主题 |
| `nodes` | `[{id, label, type, source_id, paragraph_id, quote}]`（type: researcher/material/method/task/metric/conclusion） |
| `edges` | `[{id, source, target, relation, direction, condition, source_id, paragraph_id, quote}]` |
| `queries` | `[{query, result_node_ids, evidence, unresolved}]` ≥3 个真实查询 |

**输出 `/app/output/result.json`**：

| 字段 | 说明 |
|-|-|
| `case_id` | 必填 |
| `status` | `success` / `partial` / `failed` / `refused` |
| `status_reason` | partial/failed/refused 给出原因与可人工接管位置 |
| `result` | nodes + edges + queries + merges + conflicts，并覆盖 `output_contract` 全字段 |
| `evidence` | 每个节点/边的 `{source_id, paragraph_id, quote}` |
| `uncertainty` | 证据不足/来源缺失/冲突/未报告 |
| `change_records` | 合并、去重、冲突处置等动作 |
| `artifacts` | graph_json/graph_md/pptx/preview 路径 |

## 5. 关键方法（对应四能力点）

1. **抽得准**：只抽论文真实出现的实体，保留原文表述与 `paragraph_id`，不凭常识补全。
2. **连得对**：受控词表关系类型（使用/比较/优于/支持/矛盾）+ 方向 + 适用条件；共现/转述/推测不当直接证据。
3. **对得齐**：别名/缩写/大小写处理，只合并有依据的同一概念，同名冲突不合并；不同论文的条件/样本/数值不合成。
4. **查得到、回得去**：每个节点/边带 `{source_id, paragraph_id, quote}`，≥3 个查询给出结果子图与证据。

## 6. 依赖与环境

- 首选：`python-pptx`（PPT 生成）；其余脚本仅用标准库。
- 兜底：`libreoffice`（渲染预览）；无 `python-pptx` 时走 HTML 回退。
- 平台声明工具：`office-renderer`、`scientific-python` 等。
- 提交约束：≤50 个 UTF-8 文本文件、单文件≤500KB、总计≤2MB、无符号链接。

## 7. 异常处理

| 异常 | 处置 |
|-|-|
| 文献缺失/无法解析 | `status=refused`/`partial`，说明原因 |
| 实体同名冲突 | 不合并，记录冲突 |
| 关系证据冲突 | 进 `uncertainty`，标注 |
| 查询无结果 | 如实返回空 + 说明 |
| 别名无合并依据 | 不强合并，记录候选 |
| 证据不足/来源缺失 | 进 `uncertainty`，不编造 |

## 8. 自查清单

- [ ] 实体真实出现在论文中，未凭常识补全（抽得准）
- [ ] 关系类型/方向/条件与原文一致（连得对）
- [ ] 别名/同名/大小写处理正确，无重复节点、无误合并（对得齐）
- [ ] 每个节点/边可回到 `source_id + paragraph_id + 原文短引`（查得到回得去）
- [ ] ≥3 个查询已执行并给出结果与证据
- [ ] 先保存诚实部分成果，再增量改进
