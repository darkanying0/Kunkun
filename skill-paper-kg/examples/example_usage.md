# 最小调用示例（示意，非正式案例结果）

以下为**示意输入与示意输出**，仅说明接口，不冒充正式案例结果。

## 输入（示意）

`/input/corpus-manifest.json`：

```json
[
  {"source_id": "primary", "doi": "10.xxxx/1", "title": "Paper A", "authors": ["Doe"], "year": "2024"},
  {"source_id": "secondary", "doi": "10.xxxx/2", "title": "Paper B", "authors": ["Smith"], "year": "2025"}
]
```

`/input/primary-material.json` / `secondary-material.json` 为段落化正文（每段含 `paragraph_id` 与 `text`）。

## 调用

```bash
python3 scripts/load_material.py /input /app/work
# ... 由 DeepSeek Harness 按 SKILL.md 抽取实体/关系、对齐、绑定证据，写出 /app/work/graph.json
python3 scripts/export_graph.py /app/work/graph.json /app/work
python3 scripts/build_ppt.py /app/work/graph.json /app/output
```

## 示意输出（graph.json 片段）

```json
{
  "topic": "催化剂设计",
  "nodes": [
    {"id": "n1", "label": "催化剂 A", "type": "material",
     "source_id": "primary", "paragraph_id": "sec2-p1", "quote": "Catalyst A was synthesized..."}
  ],
  "edges": [
    {"id": "e1", "source": "n1", "target": "n2", "relation": "outperforms",
     "direction": "n1→n2", "condition": "常温下",
     "source_id": "primary", "paragraph_id": "sec3-p2", "quote": "A outperformed B..."}
  ],
  "queries": [
    {"query": "哪些材料存在比较关系", "result_node_ids": ["n1", "n2"], "evidence": ["sec3-p2"], "unresolved": ""}
  ]
}
```

## 示意输出（result.json）

```json
{
  "case_id": "demo-kg-01",
  "status": "success",
  "status_reason": "实体/关系已抽取并绑定段落级证据",
  "result": {"nodes": [], "edges": [], "queries": [], "merges": [], "conflicts": []},
  "evidence": [{"source_id": "primary", "paragraph_id": "sec2-p1", "quote": "..."}],
  "uncertainty": [],
  "change_records": [{"action": "实体对齐", "reason": "对得齐"}],
  "artifacts": {
    "graph_json": "/app/work/graph.json",
    "graph_md": "/app/work/graph.md",
    "pptx": "/app/output/paper_slides.pptx",
    "preview_pdf": "/app/output/preview.pdf"
  }
}
```

> 说明：正式案例与对照结果由平台提供；本示例不预置任何正式图谱答案。
