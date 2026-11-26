#!/usr/bin/env python3
"""parse_pdf.py — 将科研论文 PDF 解析成带页级证据的结构化 JSON。

用法:
    python3 parse_pdf.py <input.pdf> <work_dir>

输出:
    <work_dir>/structured.json

设计目标（对应赛题四个能力点）:
  提得全 — 正文/题注/脚注/参考文献逐字提取，不把页眉页脚混进正文;
  排得对 — 双栏/多栏按阅读顺序输出，不串栏、不错行;
  拆得清 — 章节/表格/公式/图表按结构元素分离;
  核得回 — 每个块带 {page, x0, y0, x1, y1, column}，可回到原文位置。

依赖回退链: PyMuPDF(fitz) -> pdfplumber -> pdftotext(poppler) -> pdftotext -layout。
"""
import json
import os
import re
import sys
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# 底层提取: 优先拿"带坐标的文本块"
# ---------------------------------------------------------------------------

def _extract_with_fitz(pdf_path):
    """PyMuPDF: 返回 (blocks, pages_meta)。block = dict(page,x0,y0,x1,y1,kind,text)。"""
    import fitz  # noqa
    doc = fitz.open(pdf_path)
    blocks = []
    pages_meta = []
    for pno, page in enumerate(doc, start=1):
        rect = page.rect
        has_text = bool(page.get_text("text").strip())
        d = page.get_text("dict")
        pages_meta.append({
            "page": pno,
            "width": float(rect.width),
            "height": float(rect.height),
            "has_text_layer": has_text,
        })
        for b in d.get("blocks", []):
            if b.get("type") == 0:  # 文本块
                text = "".join(
                    span.get("text", "") for line in b.get("lines", [])
                    for span in line.get("spans", [])
                )
                if not text.strip():
                    continue
                blocks.append({
                    "page": pno,
                    "x0": round(float(b["bbox"][0]), 1),
                    "y0": round(float(b["bbox"][1]), 1),
                    "x1": round(float(b["bbox"][2]), 1),
                    "y1": round(float(b["bbox"][3]), 1),
                    "kind": "text",
                    "text": text,
                })
            elif b.get("type") == 1:  # 图片块
                blocks.append({
                    "page": pno,
                    "x0": round(float(b["bbox"][0]), 1),
                    "y0": round(float(b["bbox"][1]), 1),
                    "x1": round(float(b["bbox"][2]), 1),
                    "y1": round(float(b["bbox"][3]), 1),
                    "kind": "image",
                    "text": "",
                })
    doc.close()
    return blocks, pages_meta


def _extract_with_pdfplumber(pdf_path):
    import pdfplumber  # noqa
    blocks = []
    pages_meta = []
    with pdfplumber.open(pdf_path) as pdf:
        for pno, page in enumerate(pdf.pages, start=1):
            has_text = bool((page.extract_text() or "").strip())
            pages_meta.append({
                "page": pno,
                "width": float(page.width),
                "height": float(page.height),
                "has_text_layer": has_text,
            })
            # 用词合并成行/块（按行聚类）
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            if not words:
                continue
            rows = _cluster_words_to_rows(words)
            for row in rows:
                text = " ".join(w["text"] for w in row)
                blocks.append({
                    "page": pno,
                    "x0": round(min(w["x0"] for w in row), 1),
                    "y0": round(min(w["top"] for w in row), 1),
                    "x1": round(max(w["x1"] for w in row), 1),
                    "y1": round(max(w["bottom"] for w in row), 1),
                    "kind": "text",
                    "text": text,
                })
            for img in page.images:
                blocks.append({
                    "page": pno,
                    "x0": round(float(img["x0"]), 1),
                    "y0": round(float(img["top"]), 1),
                    "x1": round(float(img["x1"]), 1),
                    "y1": round(float(img["bottom"]), 1),
                    "kind": "image",
                    "text": "",
                })
    return blocks, pages_meta


def _cluster_words_to_rows(words, y_tol=3.0):
    rows = []
    cur = []
    last_bottom = None
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if last_bottom is None or abs(w["top"] - last_bottom) <= y_tol:
            cur.append(w)
        else:
            rows.append(sorted(cur, key=lambda w: w["x0"]))
            cur = [w]
        last_bottom = max(last_bottom or 0, w["bottom"])
    if cur:
        rows.append(sorted(cur, key=lambda w: w["x0"]))
    return rows


def _extract_with_pdftotext_bbox(pdf_path):
    """pdftotext -bbox 输出 XHTML，词级坐标；这里按行粗聚类为块。"""
    html = subprocess.run(
        ["pdftotext", "-bbox", pdf_path, "-"],
        capture_output=True, text=True,
    ).stdout
    # 解析 <word xMin=.. yMin=.. xMax=.. yMax=..>text</word> 和 <page>
    page_re = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">')
    word_re = re.compile(
        r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>',
        re.S,
    )
    blocks = []
    pages_meta = []
    pno = 0
    width = height = 0.0
    for m in page_re.finditer(html):
        pno += 1
        width, height = float(m.group(1)), float(m.group(2))
        pages_meta.append({
            "page": pno, "width": width, "height": height,
            "has_text_layer": True,
        })
    # 逐页聚词为行：重新按 page 切分
    parts = re.split(r'<page [^>]*>', html)
    for idx, part in enumerate(parts[1:], start=1):
        words = []
        for m in word_re.finditer(part):
            words.append({
                "x0": float(m.group(1)), "top": float(m.group(2)),
                "x1": float(m.group(3)), "bottom": float(m.group(4)),
                "text": m.group(5),
            })
        for row in _cluster_words_to_rows(words):
            blocks.append({
                "page": idx,
                "x0": round(min(w["x0"] for w in row), 1),
                "y0": round(min(w["top"] for w in row), 1),
                "x1": round(max(w["x1"] for w in row), 1),
                "y1": round(max(w["bottom"] for w in row), 1),
                "kind": "text",
                "text": " ".join(w["text"] for w in row),
            })
    return blocks, pages_meta


def _extract_with_pdftotext_layout(pdf_path):
    """最后兜底: 只有纯文本, 无坐标。"""
    text = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        capture_output=True, text=True,
    ).stdout
    pages = text.split("\f")
    blocks = []
    pages_meta = []
    for pno, ptxt in enumerate(pages, start=1):
        pages_meta.append({"page": pno, "width": 0, "height": 0, "has_text_layer": bool(ptxt.strip())})
        for i, line in enumerate(ptxt.splitlines()):
            if line.strip():
                blocks.append({
                    "page": pno, "x0": 0, "y0": i * 10, "x1": 0, "y1": i * 10 + 10,
                    "kind": "text", "text": line.rstrip(),
                })
    return blocks, pages_meta


def extract_blocks(pdf_path):
    errors = []
    for name, fn in [
        ("fitz", _extract_with_fitz),
        ("pdfplumber", _extract_with_pdfplumber),
        ("pdftotext_bbox", _extract_with_pdftotext_bbox),
        ("pdftotext_layout", _extract_with_pdftotext_layout),
    ]:
        try:
            blocks, pages_meta = fn(pdf_path)
            if blocks or pages_meta:
                return blocks, pages_meta, name, errors
        except Exception as e:  # noqa
            errors.append(f"{name}: {type(e).__name__}: {e}")
    return [], [], "none", errors

# ---------------------------------------------------------------------------
# 版面分析: 列检测 + 阅读顺序
# ---------------------------------------------------------------------------

def _column_split(blocks, page_width, page_height):
    """把一页文本块分成 通栏/左/右（最多两栏）。返回 {'full','left','right'} 归属。"""
    tb = [b for b in blocks if b["kind"] == "text"]
    if not tb:
        return {}
    # 用块的水平中心估计栏边界
    centers = [(b["x0"] + b["x1"]) / 2.0 for b in tb]
    mid = page_width / 2.0 if page_width else 0
    assignment = {}
    left = [b for b in tb if b["x1"] <= mid + 2]
    right = [b for b in tb if b["x0"] >= mid - 2]
    # 只有一侧有内容则单栏
    if not left or not right:
        for b in tb:
            assignment[id(b)] = "full"
        return assignment
    # 跨过中线的块视为通栏
    for b in tb:
        if b["x0"] < mid and b["x1"] > mid:
            assignment[id(b)] = "full"
        elif b["x1"] <= mid + 2:
            assignment[id(b)] = "left"
        else:
            assignment[id(b)] = "right"
    return assignment


def compute_reading_order(blocks, pages_meta):
    """返回按阅读顺序排序的块 id 列表（带全局索引）。"""
    ordered = []
    # 给每个 block 一个全局 index
    for i, b in enumerate(blocks):
        b["_idx"] = i
    for pmeta in pages_meta:
        pno = pmeta["page"]
        pblocks = [b for b in blocks if b["page"] == pno]
        if not pblocks:
            continue
        w = pmeta.get("width") or 0
        h = pmeta.get("height") or 0
        assign = _column_split(pblocks, w, h)
        full = [b for b in pblocks if assign.get(id(b)) == "full" and b["kind"] == "text"]
        left = [b for b in pblocks if assign.get(id(b)) == "left"]
        right = [b for b in pblocks if assign.get(id(b)) == "right"]
        images = [b for b in pblocks if b["kind"] == "image"]
        # 参考文献块（按内容）单独抽出，放到整页最后
        refs = [b for b in pblocks if b["kind"] == "text" and _is_reference_block(b["text"] or "")]
        left = [b for b in left if b not in refs]
        right = [b for b in right if b not in refs]
        full = [b for b in full if b not in refs]
        # 单栏情况
        if not left and not right:
            page_ordered = sorted([b for b in pblocks if b not in refs],
                                  key=lambda b: (b["y0"], b["x0"]))
            page_ordered += sorted(refs, key=lambda b: (b["y0"], b["x0"]))
        else:
            # 正文左右栏的 y 范围
            body_top = min(b["y0"] for b in left + right)
            body_bottom = max(b["y1"] for b in left + right)
            top_full = sorted([b for b in full if b["y1"] <= body_top],
                              key=lambda b: (b["y0"], b["x0"]))
            bottom_full = sorted([b for b in full if b["y0"] >= body_bottom],
                                 key=lambda b: (b["y0"], b["x0"]))
            mid_full = sorted([b for b in full if b not in top_full and b not in bottom_full],
                              key=lambda b: (b["y0"], b["x0"]))
            left_sorted = sorted(left, key=lambda b: (b["y0"], b["x0"]))
            right_sorted = sorted(right, key=lambda b: (b["y0"], b["x0"]))
            # 主顺序：通栏顶（标题/摘要）→ 左栏 → 右栏 → 通栏底（附录）→ 参考文献
            page_ordered = top_full + left_sorted + right_sorted + bottom_full
            # 中间的通栏块与图片按 y 插入
            for b in mid_full + images:
                pos = 0
                for j, x in enumerate(page_ordered):
                    if x["y0"] > b["y1"]:
                        pos = j
                        break
                    pos = j + 1
                page_ordered.insert(pos, b)
            page_ordered += sorted(refs, key=lambda b: (b["y0"], b["x0"]))
        for b in page_ordered:
            b["column"] = assign.get(id(b), "full") if b["kind"] == "text" else "figure"
            ordered.append(b["_idx"])
    return ordered

# ---------------------------------------------------------------------------
# 结构识别: 章节 / 表格 / 公式 / 图 / 参考文献
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(
    r"^\s*((\d+(\.\d+)*)|[IVX]+\.?)\s+[A-Z\u4e00-\u9fff].*|"
    r"^\s*(abstract|introduction|method|methods|results?|discussion|conclusion|"
    r"references?|acknowledg|appendix|摘要|引言|方法|结果|讨论|结论|参考文献|致谢).*",
    re.IGNORECASE,
)
_REF_RE = re.compile(r"^\s*\[\d+\]\s+")
_REF_HEADING_RE = re.compile(r"^\s*(references?|参考文献)\s*[:：]?\s*$", re.IGNORECASE)


def _is_reference_block(text):
    """判断文本块是否属于参考文献（按内容，不按几何）。"""
    return bool(_REF_RE.match(text)) or bool(_REF_HEADING_RE.match(text))
_MATH_RE = re.compile(r"[=<>≤≥±×÷∑∏∫√∂∇∞≈≠αβγδεζηθλμνξπρστφχψωΩΣΠ]|\\frac|\\sum|\\int")

def _detect_tables(pdf_path):
    """尽力抽取表格（pdfplumber 优先）。返回 list[dict]。"""
    tables = []
    try:
        import pdfplumber  # noqa
        with pdfplumber.open(pdf_path) as pdf:
            for pno, page in enumerate(pdf.pages, start=1):
                for t in page.extract_tables():
                    if t:
                        tables.append({"page": pno, "kind": "table", "rows": t})
    except Exception:
        pass
    if tables:
        return tables
    try:
        import fitz  # noqa
        doc = fitz.open(pdf_path)
        for pno, page in enumerate(doc, start=1):
            for t in page.find_tables().tables:
                tables.append({
                    "page": pno, "kind": "table",
                    "rows": t.extract(),
                    "bbox": [round(float(v), 1) for v in t.bbox],
                })
        doc.close()
    except Exception:
        pass
    return tables


def detect_structure(blocks, ordered):
    """把有序块归类为 section/paragraph/figure/table/formula/reference。"""
    seq = [blocks[i] for i in ordered]
    sections = []
    current_section = None
    elements = []
    ref_started = False
    for b in seq:
        if b["kind"] == "image":
            elements.append({"kind": "figure", "page": b["page"],
                             "bbox": [b["x0"], b["y0"], b["x1"], b["y1"]],
                             "caption": ""})
            continue
        text = (b["text"] or "").strip()
        if not text:
            continue
        if _HEADING_RE.match(text) and len(text) < 120:
            current_section = {"heading": text, "page": b["page"],
                               "bbox": [b["x0"], b["y0"], b["x1"], b["y1"]],
                               "paragraphs": []}
            sections.append(current_section)
        elif _REF_RE.match(text) or ref_started:
            ref_started = True
            elements.append({"kind": "reference", "text": text, "page": b["page"],
                             "bbox": [b["x0"], b["y0"], b["x1"], b["y1"]]})
        else:
            kind = "formula" if _MATH_RE.search(text) else "paragraph"
            para = {"kind": kind, "text": text, "page": b["page"],
                    "bbox": [b["x0"], b["y0"], b["x1"], b["y1"]]}
            if current_section is not None and kind == "paragraph":
                current_section["paragraphs"].append(para)
            else:
                elements.append(para)
    return sections, elements

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print("usage: parse_pdf.py <input.pdf> <work_dir>", file=sys.stderr)
        sys.exit(2)
    pdf_path = sys.argv[1]
    work_dir = Path(sys.argv[2])
    work_dir.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(pdf_path):
        result = {"error": f"PDF not found: {pdf_path}",
                  "status": "failed", "case_id": None}
        (work_dir / "structured.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    blocks, pages_meta, backend, errors = extract_blocks(pdf_path)
    ordered = compute_reading_order(blocks, pages_meta)
    tables = _detect_tables(pdf_path)
    sections, elements = detect_structure(blocks, ordered)

    # 清理内部字段
    for b in blocks:
        b.pop("_idx", None)

    out = {
        "source_pdf": pdf_path,
        "backend": backend,
        "backend_errors": errors,
        "pages": pages_meta,
        "blocks": blocks,
        "reading_order": ordered,
        "sections": sections,
        "tables": tables,
        "elements": elements,
        "evidence_note": "每个 block 均带 page/x0/y0/x1/y1/column，可直接回到原文位置。",
    }
    out_path = work_dir / "structured.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps({
        "status": "ok",
        "structured_json": str(out_path),
        "n_pages": len(pages_meta),
        "n_blocks": len(blocks),
        "n_tables": len(tables),
        "backend": backend,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
