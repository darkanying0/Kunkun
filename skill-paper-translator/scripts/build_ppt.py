#!/usr/bin/env python3
"""build_ppt.py — 把双语对照结果 translation.json 组织成可编辑学术 PPT。

用法:
    python3 build_ppt.py <translation.json> <output_dir>

输入 translation.json 结构（由 DeepSeek Harness 按 SKILL.md 写出）:
{
  "title": {"source": "...", "translation": "..."},
  "term_table": [{"source": "...", "target": "...", "note": "..."}],
  "sections": [{"heading": {"source":"...","translation":"..."},
                "paragraphs": [{"id":"p1","source":"...","translation":"...",
                                "page":N,"bbox":[...],"terms":[...],
                                "verification":{"status":"ok","note":"..."}}]}],
  "references": [{"text":"...", "translation":"..."}]
}

产出:
    <output_dir>/paper_slides.pptx   可编辑 PPTX（正文用译文，备注含原文+术语+证据）
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
    title = data.get("title", {})
    src_title = title.get("source", "")
    tr_title = title.get("translation", "")
    slide = add_slide(tr_title or "（未识别标题）", [f"原文: {src_title}", "本演示文稿正文为译文，备注含原文、术语与页级证据"])
    slide.notes_slide.notes_text_frame.text = f"原文标题: {src_title}\n译文标题: {tr_title}"

    # 章节 + 段落
    for sec in data.get("sections", []):
        hd = sec.get("heading", {})
        sec_body = [hd.get("translation", "")]
        sec_notes = [f"原文标题: {hd.get('source','')}", _evidence(sec)]
        for para in sec.get("paragraphs", []):
            sec_body.append(para.get("translation", ""))
            note = (f"[{para.get('id','')}] 原文: {para.get('source','')}\n"
                    f"  术语: {', '.join(para.get('terms', []))}\n"
                    f"  {_evidence(para)}")
            v = para.get("verification") or {}
            if v.get("status") == "issue":
                note += f"\n  核验问题: {v.get('note','')}"
            sec_notes.append(note)
        s = add_slide(hd.get("translation", "章节"), sec_body[:12])
        s.notes_slide.notes_text_frame.text = "\n".join(sec_notes)

    # 术语表页
    terms = data.get("term_table", [])
    if terms:
        lines = [f"{t.get('source','')} → {t.get('target','')}" + (f"  ({t.get('note','')})" if t.get("note") else "")
                 for t in terms]
        add_slide("术语表", lines[:30])

    # 参考文献页
    refs = data.get("references", [])
    if refs:
        add_slide("参考文献", [r.get("translation", "") or r.get("text", "") for r in refs][:25])

    pptx_path = out_dir / "paper_slides.pptx"
    prs.save(str(pptx_path))
    return pptx_path


def _build_html(data, out_dir):
    """python-pptx 不可用时的回退: 自包含 HTML 双语幻灯片。"""
    title = data.get("title", {})
    slides = [f"<h1>{title.get('translation','')}</h1><p>原文: {title.get('source','')}</p>"]
    for sec in data.get("sections", []):
        hd = sec.get("heading", {})
        html = f"<h2>{hd.get('translation','')} <small>({_evidence(sec)})</small></h2>"
        for para in sec.get("paragraphs", []):
            html += (f"<p><b>{para.get('translation','')}</b><br>"
                     f"<small>{para.get('source','')} · 术语: {', '.join(para.get('terms',[]))} "
                     f"· {_evidence(para)}</small></p>")
        slides.append(html)
    if data.get("term_table"):
        rows = "".join(f"<tr><td>{t.get('source','')}</td><td>{t.get('target','')}</td><td>{t.get('note','')}</td></tr>"
                       for t in data["term_table"])
        slides.append(f"<h2>术语表</h2><table>{rows}</table>")
    doc = ("<html><head><meta charset='utf-8'><style>body{font-family:sans-serif;max-width:900px;margin:auto}"
           "section{page-break-after:always;padding:20px}small{color:#666}table{border-collapse:collapse}td{border:1px solid #ccc;padding:4px}</style>"
           "</head><body>" + "".join(f"<section>{s}</section>" for s in slides) + "</body></html>")
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
        print("usage: build_ppt.py <translation.json> <output_dir>", file=sys.stderr)
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
