#!/usr/bin/env python3
"""build_ppt.py — 把知识图谱 graph.json 组织成可编辑学术 PPT。

用法:
    python3 build_ppt.py <graph.json> <output_dir>

输入 graph.json 结构（由 DeepSeek Harness 按 SKILL.md 写出）:
{
  "topic": "...",
  "nodes": [{"id":"n1","label":"...","type":"...","source_id":"primary","paragraph_id":"...","quote":"..."}],
  "edges": [{"id":"e1","source":"n1","target":"n2","relation":"...","direction":"...","condition":"...",
             "source_id":"...","paragraph_id":"...","quote":"..."}],
  "queries": [{"query":"...","result_node_ids":[...],"evidence":[...],"unresolved":"..."}]
}

产出:
    <output_dir>/paper_slides.pptx   可编辑 PPTX（正文为图谱，备注含原文短引+来源定位）
    <output_dir>/preview.pdf         PPTX 渲染 PDF 预览
    <output_dir>/preview_png/*.png   逐页 PNG 预览
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _src(n):
    return f"{n.get('source_id','')}/{n.get('paragraph_id','')}"


def _build_pptx(data, out_dir):
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    blank = prs.slide_layouts[6]

    def add_slide(title_text, body_lines):
        s = prs.slides.add_slide(blank)
        if title_text:
            tb = s.shapes.add_textbox(Inches(0.4), Inches(0.3), Inches(12.5), Inches(0.9))
            tb.text_frame.text = title_text[:200]
        if body_lines:
            body = s.shapes.add_textbox(Inches(0.4), Inches(1.4), Inches(12.5), Inches(6.2))
            btf = body.text_frame
            btf.word_wrap = True
            for i, line in enumerate(body_lines):
                p = btf.paragraphs[0] if i == 0 else btf.add_paragraph()
                p.text = line
        return s

    # 标题页
    s = add_slide(data.get("topic", "（未命名主题）"), ["本演示文稿为知识图谱，备注含原文短引与来源定位"])
    s.notes_slide.notes_text_frame.text = "主题: " + data.get("topic", "")

    # 实体页
    for n in data.get("nodes", []):
        body = [f"实体: {n.get('label','')}", f"类型: {n.get('type','')}", f"来源: {_src(n)}"]
        s = add_slide(n.get("label", "")[:80] or "实体", body)
        s.notes_slide.notes_text_frame.text = f"[{n.get('id','')}] {n.get('label','')} · {_src(n)} · “{n.get('quote','')}”"

    # 关系页
    for e in data.get("edges", []):
        cond = f" (条件: {e.get('condition')})" if e.get("condition") else ""
        body = [f"{e.get('source')} -[{e.get('relation','')}]-> {e.get('target')}{cond}",
                f"来源: {_src(e)}"]
        s = add_slide(f"{e.get('relation','')}: {e.get('source')} → {e.get('target')}", body)
        s.notes_slide.notes_text_frame.text = f"[{e.get('id','')}] {e.get('source')} -[{e.get('relation','')}]-> {e.get('target')}{cond} · {_src(e)} · “{e.get('quote','')}”"

    # 查询页
    for q in data.get("queries", []):
        body = [f"查询: {q.get('query','')}", f"结果节点: {q.get('result_node_ids', [])}"]
        if q.get("unresolved"):
            body.append(f"无法确定: {q.get('unresolved')}")
        s = add_slide(f"查询: {q.get('query','')[:60]}", body)
        s.notes_slide.notes_text_frame.text = json.dumps(q, ensure_ascii=False)

    pptx_path = out_dir / "paper_slides.pptx"
    prs.save(str(pptx_path))
    return pptx_path


def _build_html(data, out_dir):
    """python-pptx 不可用时的回退: 自包含 HTML 图谱幻灯片。"""
    slides = [f"<h1>{data.get('topic','(未命名)')}</h1><p>知识图谱</p>"]
    for n in data.get("nodes", []):
        slides.append(f"<h2>{n.get('label','')}</h2><p>类型: {n.get('type','')} · {_src(n)}</p><p><small>“{n.get('quote','')}”</small></p>")
    for e in data.get("edges", []):
        slides.append(f"<h2>{e.get('relation','')}: {e.get('source')} → {e.get('target')}</h2><p><small>{_src(e)} · “{e.get('quote','')}”</small></p>")
    for q in data.get("queries", []):
        slides.append(f"<h2>查询: {q.get('query','')}</h2><p>结果: {q.get('result_node_ids', [])}</p>")
    doc = ("<html><head><meta charset='utf-8'><style>body{font-family:sans-serif;max-width:900px;margin:auto}"
           "section{page-break-after:always;padding:20px}small{color:#666}</style></head><body>"
           + "".join(f"<section>{s}</section>" for s in slides) + "</body></html>")
    html_path = out_dir / "slides.html"
    html_path.write_text(doc, encoding="utf-8")
    return html_path


def _render_previews(pptx_path, out_dir):
    pdf_path = out_dir / "preview.pdf"
    png_dir = out_dir / "preview_png"
    png_dir.mkdir(exist_ok=True)
    lo = shutil.which("libreoffice") or shutil.which("soffice")
    if lo:
        subprocess.run([lo, "--headless", "--convert-to", "pdf",
                        "--outdir", str(out_dir), str(pptx_path)],
                       capture_output=True, timeout=180)
        same = out_dir / (pptx_path.stem + ".pdf")
        if same.exists() and not pdf_path.exists():
            same.rename(pdf_path)
    if pdf_path.exists():
        subprocess.run(["pdftoppm", "-png", "-r", "120", str(pdf_path), str(png_dir / "page")],
                       capture_output=True, timeout=180)
    return pdf_path if pdf_path.exists() else None, png_dir


def render_html_to_pdf(html_path, out_dir):
    """把 HTML 回退幻灯片用 LibreOffice 转 PDF/PNG（尽力而为），保证真实渲染预览。"""
    lo = shutil.which("libreoffice") or shutil.which("soffice")
    if not lo:
        return None
    subprocess.run([lo, "--headless", "--convert-to", "pdf",
                    "--outdir", str(out_dir), str(html_path)],
                   capture_output=True, timeout=180)
    same = out_dir / (Path(html_path).stem + ".pdf")
    pdf_path = out_dir / "preview.pdf"
    if same.exists() and not pdf_path.exists():
        same.rename(pdf_path)
    if pdf_path.exists():
        png_dir = out_dir / "preview_png"
        png_dir.mkdir(exist_ok=True)
        subprocess.run(["pdftoppm", "-png", "-r", "120", str(pdf_path), str(png_dir / "page")],
                       capture_output=True, timeout=180)
    return str(pdf_path) if pdf_path.exists() else None

def main():
    if len(sys.argv) < 3:
        print("usage: build_ppt.py <graph.json> <output_dir>", file=sys.stderr)
        sys.exit(2)
    src = sys.argv[1]
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    data = _load(src)
    artifacts = {}
    pptx_path = None
    try:
        pptx_path = _build_pptx(data, out_dir)
    except Exception as e:  # noqa
        try:
            artifacts["html_fallback"] = str(_build_html(data, out_dir))
            artifacts["preview_pdf"] = render_html_to_pdf(artifacts["html_fallback"], out_dir)
            pptx_path = None
        except Exception as e2:  # noqa
            print(f"build failed: {e}; {e2}", file=sys.stderr)
            sys.exit(1)
    if pptx_path:
        artifacts["pptx"] = str(pptx_path)
        pdf_path, png_dir = _render_previews(pptx_path, out_dir)
        artifacts["preview_pdf"] = str(pdf_path) if pdf_path else None
        artifacts["preview_png_dir"] = str(png_dir)
    print(json.dumps(artifacts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
