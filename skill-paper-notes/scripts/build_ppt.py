#!/usr/bin/env python3
"""build_ppt.py — 把结构化笔记 notes.json 组织成可编辑学术 PPT。

用法:
    python3 build_ppt.py <notes.json> <output_dir>

输入 notes.json 结构（由 DeepSeek Harness 按 SKILL.md 写出）:
{
  "title": "...",
  "paper_card": {"research_question":"...","data":"...","methods":"...",
                 "main_findings":"...","conclusions":"...","limitations":"..."},
  "sections": [{"heading":"...","page":N,"bbox":[...],
                "purpose":"...","method":"...","result":"...","conclusion":"..."}],
  "knowledge_points": [{"concept":"...","statement":"...","page":N,"evidence":"..."}],
  "references": [{"text":"..."}]
}

产出:
    <output_dir>/paper_slides.pptx   可编辑 PPTX（正文为笔记，备注含原文+证据）
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
    s = add_slide(title, ["本演示文稿为结构化笔记，备注含原文片段与页级证据"])
    s.notes_slide.notes_text_frame.text = f"标题: {title}"

    # 论文卡片页
    card = data.get("paper_card") or {}
    card_fields = [("研究问题", "research_question"), ("数据", "data"),
                   ("方法", "methods"), ("主要发现", "main_findings"),
                   ("结论", "conclusions"), ("局限", "limitations")]
    lines = [f"{label}: {card.get(key, '')}" for label, key in card_fields if card.get(key)]
    s = add_slide("论文卡片", lines or ["（论文卡片字段待提取）"])
    s.notes_slide.notes_text_frame.text = "论文卡片字段（研究问题/数据/方法/主要发现/结论/局限）"

    # 章节笔记页
    for sec in data.get("sections", []):
        hd = sec.get("heading", "章节")
        body = []
        notes = [f"章节: {hd}", _evidence(sec)]
        for label, key in [("目的", "purpose"), ("方法", "method"), ("结果", "result"), ("结论", "conclusion")]:
            if sec.get(key):
                body.append(f"{label}: {sec.get(key)}")
                notes.append(f"{label}: {sec.get(key)}")
        s = add_slide(hd, body[:12])
        s.notes_slide.notes_text_frame.text = "\n".join(notes)

    # 知识点页
    kps = data.get("knowledge_points", [])
    if kps:
        lines = [f"{kp.get('concept','')}: {kp.get('statement','')}  ({_evidence(kp)})" for kp in kps]
        s = add_slide("知识点清单", lines[:30])
        s.notes_slide.notes_text_frame.text = "\n".join(
            f"{kp.get('concept','')}: {kp.get('statement','')} · {kp.get('evidence','')} · {_evidence(kp)}"
            for kp in kps)

    # 参考文献页
    refs = data.get("references", [])
    if refs:
        add_slide("参考文献", [r.get("text", "") for r in refs][:25])

    pptx_path = out_dir / "paper_slides.pptx"
    prs.save(str(pptx_path))
    return pptx_path


def _build_html(data, out_dir):
    """python-pptx 不可用时的回退: 自包含 HTML 笔记幻灯片。"""
    title = data.get("title", "（未识别标题）")
    slides = [f"<h1>{title}</h1><p>结构化笔记</p>"]
    card = data.get("paper_card") or {}
    card_html = "".join(f"<p><b>{k}</b>: {v}</p>" for k, v in card.items() if v)
    slides.append(f"<h2>论文卡片</h2>{card_html}")
    for sec in data.get("sections", []):
        hd = sec.get("heading", "章节")
        html = f"<h2>{hd} <small>({_evidence(sec)})</small></h2>"
        for label, key in [("目的", "purpose"), ("方法", "method"), ("结果", "result"), ("结论", "conclusion")]:
            if sec.get(key):
                html += f"<p><b>{label}</b>: {sec.get(key)}</p>"
        slides.append(html)
    kps = data.get("knowledge_points", [])
    if kps:
        kp_html = "".join(f"<li>{kp.get('concept','')}: {kp.get('statement','')} <small>({_evidence(kp)})</small></li>" for kp in kps)
        slides.append(f"<h2>知识点清单</h2><ul>{kp_html}</ul>")
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
        print("usage: build_ppt.py <notes.json> <output_dir>", file=sys.stderr)
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
