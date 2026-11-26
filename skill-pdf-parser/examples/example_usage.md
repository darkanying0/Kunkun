# 最小调用示例（示意，非正式案例结果）

以下为**示意输入与示意输出**，仅用于说明接口，不冒充正式案例结果。

## 输入

`/input/case.json`（示意）：

```json
{
  "case_id": "demo-case-01",
  "material": "/input/paper.pdf",
  "task": "解析论文的正文、章节、表格与公式，并给出页级证据",
  "output_contract": ["title", "sections", "tables", "formulas"]
}
```

## 调用

```bash
python3 scripts/parse_pdf.py /input/paper.pdf /app/work
python3 scripts/build_ppt.py /app/work/structured.json /app/output
```

## 示意输出（structured.json 片段）

```json
{
  "pages": [{"page": 1, "width": 612.0, "height": 792.0, "has_text_layer": true}],
  "blocks": [
    {"page": 1, "x0": 72.0, "y0": 90.0, "x1": 300.0, "y1": 110.0,
     "column": "left", "kind": "text", "text": "1  Introduction"}
  ],
  "reading_order": [0],
  "sections": [
    {"heading": "1  Introduction", "page": 1,
     "bbox": [72.0, 90.0, 300.0, 110.0], "paragraphs": []}
  ],
  "evidence_note": "每个 block 均带 page/x0/y0/x1/y1/column，可直接回到原文位置。"
}
```

## 示意输出（result.json）

```json
{
  "case_id": "demo-case-01",
  "status": "success",
  "status_reason": "文字层完整，双栏顺序已校正",
  "result": {
    "title": "（示意标题）",
    "sections": [],
    "tables": [],
    "formulas": []
  },
  "evidence": [{"page": 1, "region": "x0=72,y0=90,x1=300,y1=110", "kind": "text"}],
  "uncertainty": [],
  "change_records": [{"action": "校正双栏阅读顺序", "reason": "左栏优先"}],
  "artifacts": {
    "structured_json": "/app/work/structured.json",
    "pptx": "/app/output/paper_slides.pptx",
    "preview_pdf": "/app/output/preview.pdf"
  }
}
```

> 说明：正式测试案例、白板与对照结果由平台提供；本示例不预置任何正式答案。
