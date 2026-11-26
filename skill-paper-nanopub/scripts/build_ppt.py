#!/usr/bin/env python3
"""build_ppt.py — 把 nanopub.json（断言+证据+来源）组织成可编辑学术 PPT。

用法:
    python3 build_ppt.py <nanopub.json> <output_dir>

输入 nanopub.json 结构（由 DeepSeek Harness 按 SKILL.md 写出）:
{
  "title": "...",
  "provenance": {"paper":"...","authors":[...],"year":"...","version":"...","identifier":"..."},
  "nanopublications": [
    {"id":"np1","subject":"...","relation":"...","object":"...",
     "assertion":"...","evidence":"...","page":N,"bbox":[...],
     "evidence_type":"direct|indirect","confidence":"..."}
  ],
  "quality_checks": [{"check":"...","status":"ok|issue","detail":"..."}],
  "references": [{"text":"..."}]
}

产出:
    <output_dir>/paper_slides.pptx   可编辑 PPTX（正文为断言，备注含证据+来源+页级证据）
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


def _evidence(unit):
    bbox = unit.get("bbox") or []
    page = unit.get("page", "?")
    if bbox and len(bbox) >= 4:
        return f"证据: 第{page}页 区域 x0={bbox[0]},y0={bbox[1]},x1={bbox[2]},y1={bbox[3]}"
    return f"证据: 第{page}页"


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
    title = data.get("title", "（未识别标题）")
    prov = data.get("provenance") or {}
    s = add_slide(title, [f"来源: {prov.get('paper','')} ({prov.get('year','')})",
                          "本演示文稿为断言清单，备注含证据片段与页级证据"])
    s.notes_slide.notes_text_frame.text = "来源元数据: " + json.dumps(prov, ensure_ascii=False)

    # 断言清单页
    nps = data.get("nanopublications", [])
    for np_ in nps:
        body = [
            f"断言: {np_.get('assertion','')}",
            f"主体: {np_.get('subject','')} | 关系: {np_.get('relation','')} | 客体: {np_.get('object','')}",
            f"证据类型: {np_.get('evidence_type','')} | 置信度依据: {np_.get('confidence','')}",
        ]
        notes = (f"[{np_.get('id','')}] 断言: {np_.get('assertion','')}\n"
                 f"证据片段: {np_.get('evidence','')}\n"
                 f"{_evidence(np_)} · 证据类型: {np_.get('evidence_type','')}")
        s = add_slide(np_.get("assertion", "")[:80] or "断言", body)
        s.notes_slide.notes_text_frame.text = notes

    # 质量检查页
    qcs = data.get("quality_checks", [])
    if qcs:
        lines = [f"{qc.get('check','')}: {qc.get('status','')} {qc.get('detail','')}" for qc in qcs]
        add_slide("质量检查", lines[:30])

    # 参考文献页
    refs = data.get("references", [])
    if refs:
        add_slide("参考文献", [r.get("text", "") for r in refs][:25])

    pptx_path = out_dir / "paper_slides.pptx"
    prs.save(str(pptx_path))
    return pptx_path


def _build_html(data, out_dir):
    """python-pptx 不可用时的回退: 自包含 HTML 断言幻灯片。"""
    title = data.get("title", "（未识别标题）")
    prov = data.get("provenance") or {}
    slides = [f"<h1>{title}</h1><p>来源: {prov.get('paper','')} ({prov.get('year','')})</p>"]
    for np_ in data.get("nanopublications", []):
        html = (f"<h2>{np_.get('assertion','')[:80]}</h2>"
                f"<p><b>主体</b> {np_.get('subject','')} · <b>关系</b> {np_.get('relation','')} · <b>客体</b> {np_.get('object','')}</p>"
                f"<p><small>证据: {np_.get('evidence','')} · {_evidence(np_)} · {np_.get('evidence_type','')}</small></p>")
        slides.append(html)
    if data.get("quality_checks"):
        qc = "".join(f"<li>{q.get('check','')}: {q.get('status','')} {q.get('detail','')}</li>" for q in data["quality_checks"])
        slides.append(f"<h2>质量检查</h2><ul>{qc}</ul>")
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
        print("usage: build_ppt.py <nanopub.json> <output_dir>", file=sys.stderr)
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
