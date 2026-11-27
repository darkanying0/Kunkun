#!/usr/bin/env python3
"""build_ppt.py — 按给定模板（master/layout）把页级大纲 outline.json 改编成可编辑学术 PPT。

用法:
    python3 build_ppt.py <outline.json> <output_dir> [--template template.pptx] [--deck deck.pptx]

outline.json 结构（由 DeepSeek Harness 按 SKILL.md 写出）:
{
  "title": "论文标题",
  "main_thread": "一句话主线",
  "slides": [
    {"title":"研究问题","claim":"...","points":["...","..."],
     "evidence":{"kind":"figure|table|section|data","ref":"Fig.1","page":3,"quote":"...","note":"..."},
     "notes":"讲解备注（不重复页面文字）"}
  ]
}

产出:
    <output_dir>/paper_slides.pptx   可编辑 PPTX（继承模板版式/页脚/配色）
    <output_dir>/preview.pdf         PPTX 渲染 PDF 预览
    <output_dir>/preview_png/*.png   逐页 PNG 预览
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _find_layout(prs, want_title=True):
    """在模板布局中挑一个合适的：优先标题页/标题+内容，否则回退前两个布局。"""
    from pptx.enum.shapes import PP_PLACEHOLDER
    layouts = prs.slide_layouts
    if want_title:
        for ly in layouts:
            for ph in ly.placeholders:
                if ph.placeholder_format.type == PP_PLACEHOLDER.TITLE and \
                   ph.placeholder_format.idx == 0:
                    # 标题页布局通常只有一个 title 占位符且无 body
                    has_body = any(p.placeholder_format.idx == 1 for p in ly.placeholders)
                    if not has_body:
                        return ly
    # 标题+内容布局
    for ly in layouts:
        has_title = any(p.placeholder_format.type == PP_PLACEHOLDER.TITLE or p.placeholder_format.idx == 0
                        for p in ly.placeholders)
        has_body = any(p.placeholder_format.idx == 1 or p.placeholder_format.type == PP_PLACEHOLDER.BODY
                       for p in ly.placeholders)
        if has_title and has_body:
            return ly
    return layouts[0] if layouts else None


def _set_title(slide, text):
    from pptx.enum.shapes import PP_PLACEHOLDER
    for ph in slide.placeholders:
        if ph.placeholder_format.type == PP_PLACEHOLDER.TITLE or ph.placeholder_format.idx == 0:
            ph.text = text[:200]
            return


def _set_body(slide, points):
    from pptx.enum.shapes import PP_PLACEHOLDER
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == 1 or ph.placeholder_format.type == PP_PLACEHOLDER.BODY:
            tf = ph.text_frame
            tf.clear()
            for i, p in enumerate(points):
                para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                para.text = str(p)[:400]
                para.level = 0
            return
    # 无 body 占位符时退到第一个非 title 占位符，或自建文本框
    for ph in slide.placeholders:
        if ph.placeholder_format.idx not in (0,) and ph.placeholder_format.type != PP_PLACEHOLDER.TITLE:
            ph.text = "\n".join(str(p) for p in points)[:2000]
            return


def _set_notes(slide, notes, evidence):
    parts = []
    if notes:
        parts.append(notes)
    if evidence:
        ev = evidence
        loc = f"第{ev.get('page','?')}页" if ev.get("page") is not None else ""
        parts.append(f"[证据] {ev.get('kind','')} {ev.get('ref','')} {loc} {ev.get('note','')}".strip())
        if ev.get("quote"):
            parts.append(f"[原文] {ev.get('quote','')}")
    if parts:
        slide.notes_slide.notes_text_frame.text = "\n".join(parts)


def _build_pptx(data, template, deck, out_dir):
    from pptx import Presentation

    # 起始 deck 优先（在其上改编）；否则加载模板；否则新建
    src = deck or template
    if src and Path(src).exists():
        prs = Presentation(str(src))
    else:
        prs = Presentation()

    title_layout = _find_layout(prs, want_title=True)
    content_layout = _find_layout(prs, want_title=False) or title_layout

    # 标题页
    if title_layout is not None:
        s = prs.slides.add_slide(title_layout)
        _set_title(s, data.get("title", "（未命名）"))
        _set_notes(s, data.get("main_thread", ""), None)

    # 内容页
    for sl in data.get("slides", []):
        if content_layout is None:
            continue
        s = prs.slides.add_slide(content_layout)
        _set_title(s, sl.get("title", "") or sl.get("claim", ""))
        pts = sl.get("points") or ([sl.get("claim")] if sl.get("claim") else [])
        _set_body(s, pts)
        _set_notes(s, sl.get("notes", ""), sl.get("evidence"))

    pptx_path = out_dir / "paper_slides.pptx"
    prs.save(str(pptx_path))
    return pptx_path


def _build_html(data, out_dir):
    """python-pptx 不可用时的回退: 自包含 HTML 幻灯片。"""
    slides = [f"<h1>{data.get('title','(未命名)')}</h1><p>{data.get('main_thread','')}</p>"]
    for sl in data.get("slides", []):
        pts = "".join(f"<li>{p}</li>" for p in sl.get("points", []))
        ev = sl.get("evidence") or {}
        html = (f"<h2>{sl.get('title','')}</h2><p><b>{sl.get('claim','')}</b></p><ul>{pts}</ul>"
                f"<p><small>证据: {ev.get('kind','')} {ev.get('ref','')} · {ev.get('note','')}</small></p>")
        slides.append(html)
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
    """HTML 回退幻灯片转 PDF/PNG（尽力而为）。"""
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
    ap = argparse.ArgumentParser()
    ap.add_argument("outline")
    ap.add_argument("out_dir")
    ap.add_argument("--template", default=None)
    ap.add_argument("--deck", default=None)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = _load(args.outline)
    artifacts = {}

    pptx_path = None
    try:
        pptx_path = _build_pptx(data, args.template, args.deck, out_dir)
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
