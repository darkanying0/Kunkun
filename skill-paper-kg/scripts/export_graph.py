#!/usr/bin/env python3
"""export_graph.py — 校验图谱 JSON 并导出可读 Markdown 与 GraphML。

用法:
    python3 export_graph.py <graph.json> <work_dir>

graph.json 结构（由 DeepSeek Harness 按 SKILL.md 写出）:
{
  "topic": "...",
  "nodes": [{"id":"n1","label":"...","type":"material|method|task|metric|researcher|conclusion",
             "source_id":"primary","paragraph_id":"...","quote":"..."}],
  "edges": [{"id":"e1","source":"n1","target":"n2","relation":"uses|compares|outperforms|supports|contradicts",
             "direction":"...","condition":"...","source_id":"...","paragraph_id":"...","quote":"..."}],
  "queries": [{"query":"...","result_node_ids":[...],"evidence":[...],"unresolved":"..."}]
}

输出:
    <work_dir>/graph.md       可读图谱
    <work_dir>/graph.graphml  可导入图数据库的 GraphML
"""
import json
import sys
from pathlib import Path


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _escape_xml(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _to_markdown(g):
    lines = [f"# 知识图谱: {g.get('topic', '(未命名)')}", ""]
    lines.append("## 节点")
    for n in g.get("nodes", []):
        src = f"{n.get('source_id','')}/{n.get('paragraph_id','')}"
        lines.append(f"- **{n.get('id')}** [{n.get('type','')}] {n.get('label','')} — {src} “{n.get('quote','')}”")
    lines.append("")
    lines.append("## 边（关系）")
    for e in g.get("edges", []):
        cond = f" (条件: {e.get('condition')})" if e.get("condition") else ""
        lines.append(f"- {e.get('source')} -[{e.get('relation','')}]-> {e.get('target')}{cond} "
                     f"— {e.get('source_id','')}/{e.get('paragraph_id','')} “{e.get('quote','')}”")
    lines.append("")
    lines.append("## 查询")
    for q in g.get("queries", []):
        lines.append(f"- Q: {q.get('query')} → {q.get('result_node_ids', [])}")
        if q.get("unresolved"):
            lines.append(f"  无法确定: {q.get('unresolved')}")
    return "\n".join(lines)


def _to_graphml(g):
    nodes = g.get("nodes", [])
    edges = g.get("edges", [])
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
           '  <key id="label" for="node" attr.name="label" attr.type="string"/>',
           '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
           '  <key id="relation" for="edge" attr.name="relation" attr.type="string"/>',
           '  <graph id="G" edgedefault="directed">']
    for n in nodes:
        out.append(f'    <node id="{_escape_xml(n.get("id"))}">')
        out.append(f'      <data key="label">{_escape_xml(n.get("label",""))}</data>')
        out.append(f'      <data key="type">{_escape_xml(n.get("type",""))}</data>')
        out.append('    </node>')
    for e in edges:
        out.append(f'    <edge id="{_escape_xml(e.get("id"))}" source="{_escape_xml(e.get("source"))}" target="{_escape_xml(e.get("target"))}">')
        out.append(f'      <data key="relation">{_escape_xml(e.get("relation",""))}</data>')
        out.append('    </edge>')
    out.append('  </graph>')
    out.append('</graphml>')
    return "\n".join(out)


def main():
    if len(sys.argv) < 3:
        print("usage: export_graph.py <graph.json> <work_dir>", file=sys.stderr)
        sys.exit(2)
    g = _load(sys.argv[1])
    work = Path(sys.argv[2])
    work.mkdir(parents=True, exist_ok=True)

    md_path = work / "graph.md"
    md_path.write_text(_to_markdown(g), encoding="utf-8")
    gml_path = work / "graph.graphml"
    gml_path.write_text(_to_graphml(g), encoding="utf-8")

    print(json.dumps({
        "status": "ok",
        "graph_md": str(md_path),
        "graph_graphml": str(gml_path),
        "n_nodes": len(g.get("nodes", [])),
        "n_edges": len(g.get("edges", [])),
        "n_queries": len(g.get("queries", [])),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
