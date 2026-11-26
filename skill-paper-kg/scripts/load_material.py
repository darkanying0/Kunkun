#!/usr/bin/env python3
"""load_material.py — 加载段落化论文正文，输出统一的可抽取视图。

用法:
    python3 load_material.py <input_dir> <work_dir>

输入（在 <input_dir> 下）:
    corpus-manifest.json    各论文 DOI/作者/来源哈希/许可证
    material.json           两篇正文段落汇总索引
    primary-material.json   第一篇论文正文
    secondary-material.json 第二篇论文正文

输出:
    <work_dir>/materials.json   每段 {source_id, paragraph_id, text, paper_meta}
"""
import json
import sys
from pathlib import Path


def _load_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception as e:  # noqa
        return {"_error": f"{type(e).__name__}: {e}"}


def _flatten_paragraphs(doc, source_id, paper_meta):
    """把一篇论文的段落 JSON 展平为 [{source_id, paragraph_id, text}]。"""
    paras = []
    if isinstance(doc, list):
        for item in doc:
            if isinstance(item, dict) and ("text" in item or "paragraph" in item or "content" in item):
                text = item.get("text") or item.get("paragraph") or item.get("content") or ""
                pid = item.get("paragraph_id") or item.get("id") or item.get("pid") or ""
                paras.append({"source_id": source_id, "paragraph_id": str(pid), "text": text,
                              "paper_meta": paper_meta})
            elif isinstance(item, str):
                paras.append({"source_id": source_id, "paragraph_id": "", "text": item,
                              "paper_meta": paper_meta})
    elif isinstance(doc, dict):
        # 常见形态: {"paragraphs": [...], "sections": [...]}
        for key in ("paragraphs", "sections", "items", "content"):
            v = doc.get(key)
            if isinstance(v, list):
                paras.extend(_flatten_paragraphs(v, source_id, paper_meta))
        if not paras:
            text = doc.get("text") or doc.get("paragraph") or doc.get("content")
            if text:
                paras.append({"source_id": source_id, "paragraph_id": str(doc.get("paragraph_id") or ""),
                              "text": text, "paper_meta": paper_meta})
    return paras


def main():
    if len(sys.argv) < 3:
        print("usage: load_material.py <input_dir> <work_dir>", file=sys.stderr)
        sys.exit(2)
    inp = Path(sys.argv[1])
    work = Path(sys.argv[2])
    work.mkdir(parents=True, exist_ok=True)

    manifest = _load_json(inp / "corpus-manifest.json")
    primary = _load_json(inp / "primary-material.json")
    secondary = _load_json(inp / "secondary-material.json")

    # manifest 可能直接是数组或 dict
    manifest_list = manifest if isinstance(manifest, list) else manifest.get("papers") or manifest.get("items") or [manifest]
    meta_by_id = {}
    for i, m in enumerate(manifest_list):
        if isinstance(m, dict):
            sid = m.get("source_id") or m.get("id") or f"p{i+1}"
            meta_by_id[sid] = {k: m.get(k) for k in ("doi", "title", "authors", "license", "year") if m.get(k)}

    primary_meta = meta_by_id.get("primary") or meta_by_id.get("p1") or (manifest_list[0] if manifest_list else {}) or {}
    secondary_meta = meta_by_id.get("secondary") or meta_by_id.get("p2") or (manifest_list[1] if len(manifest_list) > 1 else {}) or {}

    primary_paras = _flatten_paragraphs(primary, "primary", primary_meta)
    secondary_paras = _flatten_paragraphs(secondary, "secondary", secondary_meta)

    out = {
        "manifest": manifest,
        "primary_paras": primary_paras,
        "secondary_paras": secondary_paras,
        "n_primary": len(primary_paras),
        "n_secondary": len(secondary_paras),
    }
    out_path = work / "materials.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps({
        "status": "ok",
        "materials_json": str(out_path),
        "n_primary_paragraphs": len(primary_paras),
        "n_secondary_paragraphs": len(secondary_paras),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
