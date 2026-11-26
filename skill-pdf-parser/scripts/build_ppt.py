#!/usr/bin/env python3
"""build_ppt.py — 把 parse_pdf.py 的 structured.json 组织成可编辑学术 PPT。

用法:
    python3 build_ppt.py <structured.json> <output_dir>

产出:
    <output_dir>/paper_slides.pptx   可编辑 PPTX（含讲稿备注 + 页级证据）
    <output_dir>/preview.pdf         PPTX 渲染出的 PDF 预览
    <output_dir>/preview_png/*.png   逐页 PNG 预览

设计: 按论文结构分页, 每页正文逐字写入备注, 并在备注里带 {page, region} 证据映射;
渲染预览用 office-renderer(LibreOffice) + pdf-render-tool/pdftoppm。
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

EVIDENCE = "证据"  # 备注里证据标签


def _load(struct_path):
    return json.loads(Path(struct_path).read_text(encoding="utf-8"))


def _notes_evidence(unit):
    """生成一条证据字符串: 页码 + 区域。"""
    bbox = unit.get("bbox") or []
    page = unit.get("page", "?")
    if bbox and len(bbox) >= 4:
        return f"{EVIDENCE}: 第{page}页 区域 x0={bbox[0]},y0={bbox[1]},x1={bbox[2]},y1={bbox[3]}"
    return f"{EVIDENCE}: 第{page}页"


def build_pptx(data, out_dir):
    """用 python-pptx 构建可编辑 PPTX。"""
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    blank = prs.slide_layouts[6]  # 空白版式

    def add_slide(title_text, body_lines):
        s = prs.slides.add_slide(blank)
        # 标题
        if title_text:
            tb = s.shapes.add_textbox(Inches(0.4), Inches(0.3), Inches(12.5), Inches(0.9))
            tf = tb.text_frame
            tf.text = title_text[:200]
        # 正文
        if body_lines:
            body = s.shapes.add_textbox(Inches(0.4), Inches(1.4), Inches(12.5), Inches(6.2))
            btf = body.text_frame
            btf.word_wrap = True
            for i, line in enumerate(body_lines):
                p = btf.paragraphs[0] if i == 0 else btf.add_paragraph()
                p.text = line
        return s

    # 1) 标题页
    title = "（未识别标题）"
    authors = ""
    for b in data.get("blocks", []):
        t = (b.get("text") or "").strip()
        if t and b.get("y0", 0) < 200 and len(t) > 10 and len(t) < 200:
            title = t
            break
    add_slide(title, ["来源: " + data.get("source_pdf", ""),
                      "本演示文稿按论文结构组织, 备注含逐字正文与页级证据映射"])

    # 2) 章节页 + 段落
    for sec in data.get("sections", []):
        notes = [sec.get("heading", ""), _notes_evidence(sec)]
        body = []
        for p in sec.get("paragraphs", []):
            body.append(p.get("text", ""))
            notes.append(p.get("text", "") + "  [" + _notes_evidence(p) + "]")
        slide = add_slide(sec.get("heading", "章节"), body[:12])
        slide.notes_slide.notes_text_frame.text = "\n".join(notes)

    # 3) 表格页
    for i, t in enumerate(data.get("tables", [])):
        lines = []
        rows = t.get("rows") or []
        for r in rows[:20]:
            cells = [str(c) if c is not None else "" for c in r]
            lines.append(" | ".join(cells))
        slide = add_slide(f"表格 {i+1} (第{t.get('page','?')}页)", lines)
        slide.notes_slide.notes_text_frame.text = "\n".join(lines + [_notes_evidence(t)])

    # 4) 图页
    figs = [e for e in data.get("elements", []) if e.get("kind") == "figure"]
    for i, f in enumerate(figs):
        slide = add_slide(f"图 {i+1} (第{f.get('page','?')}页)", [f.get("caption", "") or "(题注待识别)"])
        slide.notes_slide.notes_text_frame.text = _notes_evidence(f)

    # 5) 参考文献页
    refs = [e.get("text", "") for e in data.get("elements", []) if e.get("kind") == "reference"]
    if refs:
        slide = add_slide("参考文献", refs[:25])
        ref_notes = []
        for e in data.get("elements", []):
            if e.get("kind") == "reference":
                ref_notes.append(e.get("text", "") + "  [" + _notes_evidence(e) + "]")
        slide.notes_slide.notes_text_frame.text = "\n".join(ref_notes)

    pptx_path = out_dir / "paper_slides.pptx"
    prs.save(str(pptx_path))
    return pptx_path


def build_html(data, out_dir):
    """python-pptx 不可用时的回退: 自包含 HTML 幻灯片。"""
    title = "（未识别标题）"
    for b in data.get("blocks", []):
        t = (b.get("text") or "").strip()
        if t and b.get("y0", 0) < 200 and 10 < len(t) < 200:
            title = t
            break
    slides = [f"<h1>{title}</h1><p>来源: {data.get('source_pdf','')}</p>"]
    for sec in data.get("sections", []):
        html = f"<h2>{sec.get('heading','')} <small>({_notes_evidence(sec)})</small></h2>"
        for p in sec.get("paragraphs", []):
            html += f"<p>{p.get('text','')} <small>({_notes_evidence(p)})</small></p>"
        slides.append(html)
    for i, t in enumerate(data.get("tables", [])):
        rows = [" | ".join(str(c) if c is not None else "" for c in r) for r in (t.get("rows") or [])]
        slides.append(f"<h2>表格 {i+1} ({_notes_evidence(t)})</h2><pre>{chr(10).join(rows[:20])}</pre>")
    doc = "<html><head><meta charset='utf-8'><style>body{font-family:sans-serif;max-width:900px;margin:auto}" \
          "section{page-break-after:always;padding:20px}small{color:#666}</style></head><body>" + \
          "".join(f"<section>{s}</section>" for s in slides) + "</body></html>"
    html_path = out_dir / "slides.html"
    html_path.write_text(doc, encoding="utf-8")
    return html_path


def render_previews(pptx_path, out_dir):
    """用 LibreOffice(office-renderer) 把 PPTX 转 PDF, 再转 PNG。"""
    pdf_path = out_dir / "preview.pdf"
    png_dir = out_dir / "preview_png"
    png_dir.mkdir(exist_ok=True)
    lo = shutil.which("libreoffice") or shutil.which("soffice")
    if lo:
        subprocess.run(
            [lo, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx_path)],
            capture_output=True, timeout=180,
        )
        # LibreOffice 按同名输出 <basename>.pdf, 归一化到 preview.pdf
        same_name_pdf = out_dir / (pptx_path.stem + ".pdf")
        if same_name_pdf.exists() and not pdf_path.exists():
            same_name_pdf.rename(pdf_path)
    if not pdf_path.exists():
        pdf_path = None
    if pdf_path and pdf_path.exists():
        subprocess.run(
            ["pdftoppm", "-png", "-r", "120", str(pdf_path), str(png_dir / "page")],
            capture_output=True, timeout=180,
        )
    return pdf_path, png_dir


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
        print("usage: build_ppt.py <structured.json> <output_dir>", file=sys.stderr)
        sys.exit(2)
    struct_path = sys.argv[1]
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    data = _load(struct_path)
    artifacts = {}
    pptx_path = None
    try:
        pptx_path = build_pptx(data, out_dir)
    except Exception as e:  # noqa
        try:
            artifacts["html_fallback"] = str(build_html(data, out_dir))
            artifacts["preview_pdf"] = render_html_to_pdf(artifacts["html_fallback"], out_dir)
        except Exception as e2:  # noqa
            print(f"build failed: {e}; {e2}", file=sys.stderr)
            sys.exit(1)

    if pptx_path:
        artifacts["pptx"] = str(pptx_path)
        pdf_path, png_dir = render_previews(pptx_path, out_dir)
        artifacts["preview_pdf"] = str(pdf_path) if pdf_path else None
        artifacts["preview_png_dir"] = str(png_dir)

    print(json.dumps(artifacts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
