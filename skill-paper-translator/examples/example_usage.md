# 最小调用示例（示意，非正式案例结果）

以下为**示意输入与示意输出**，仅说明接口，不冒充正式案例结果。

## 输入

`/input/case.json`（示意）：

```json
{
  "case_id": "demo-translate-01",
  "material": "/input/paper.pdf",
  "target_language": "zh",
  "task": "将论文翻译成中文双语对照，并生成可编辑学术 PPT",
  "output_contract": ["title", "term_table", "paragraphs"]
}
```

## 调用

```bash
python3 scripts/parse_pdf.py /input/paper.pdf /app/work
# ... 由 DeepSeek Harness 按 SKILL.md 建术语表、逐段翻译，写出 /app/work/translation.json
python3 scripts/build_ppt.py /app/work/translation.json /app/output
```

## 示意输出（translation.json 片段）

```json
{
  "title": {"source": "A Study on Catalyst Design", "translation": "催化剂设计研究"},
  "term_table": [
    {"source": "catalyst", "target": "催化剂", "note": "全文统一译名"}
  ],
  "sections": [
    {
      "heading": {"source": "1 Introduction", "translation": "1 引言"},
      "paragraphs": [
        {
          "id": "p1",
          "source": "We design a catalyst.",
          "translation": "我们设计了一种催化剂。",
          "page": 1,
          "bbox": [72, 180, 300, 194],
          "terms": ["catalyst"],
          "verification": {"status": "ok", "note": "数字/单位/公式已核对"}
        }
      ]
    }
  ]
}
```

## 示意输出（result.json）

```json
{
  "case_id": "demo-translate-01",
  "status": "success",
  "status_reason": "文字层完整，术语表已锁定，逐段翻译完成",
  "result": {
    "title": {"source": "A Study on Catalyst Design", "translation": "催化剂设计研究"},
    "term_table": [],
    "paragraphs": []
  },
  "evidence": [{"page": 1, "region": "x0=72,y0=180,x1=300,y1=194", "kind": "text"}],
  "uncertainty": [],
  "change_records": [{"action": "术语 catalyst 全篇回填为 催化剂", "reason": "术语一致"}],
  "artifacts": {
    "structured_json": "/app/work/structured.json",
    "translation_json": "/app/work/translation.json",
    "pptx": "/app/output/paper_slides.pptx",
    "preview_pdf": "/app/output/preview.pdf"
  }
}
```

> 说明：正式测试案例、白板与对照结果由平台提供；本示例不预置任何正式译文。
