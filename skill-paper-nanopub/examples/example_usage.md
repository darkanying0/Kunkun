# 最小调用示例（示意，非正式案例结果）

以下为**示意输入与示意输出**，仅说明接口，不冒充正式案例结果。

## 输入

`/input/case.json`（示意）：

```json
{
  "case_id": "demo-nanopub-01",
  "material": "/input/paper.pdf",
  "task": "将论文结论拆成断言并绑定证据与来源，导出机器可读结构",
  "output_contract": ["nanopublications", "provenance", "quality_checks"]
}
```

## 调用

```bash
python3 scripts/parse_pdf.py /input/paper.pdf /app/work
# ... 由 DeepSeek Harness 按 SKILL.md 拆断言、绑证据、记来源，写出 /app/work/nanopub.json
python3 scripts/build_ppt.py /app/work/nanopub.json /app/output
```

## 示意输出（nanopub.json 片段）

```json
{
  "title": "A Study on Catalyst Design",
  "provenance": {
    "paper": "A Study on Catalyst Design",
    "authors": ["Doe, J."],
    "year": "2024",
    "version": "v1",
    "identifier": "DOI:10.xxxx/xxxx"
  },
  "nanopublications": [
    {
      "id": "np1",
      "subject": "催化剂 A",
      "relation": "has_higher_activity_than",
      "object": "催化剂 B",
      "assertion": "催化剂 A 的活性高于催化剂 B",
      "evidence": "图 2 显示催化剂 A 的转化率更高",
      "page": 3,
      "bbox": [72, 400, 300, 420],
      "evidence_type": "direct",
      "confidence": "原文直接报告"
    }
  ],
  "quality_checks": [
    {"check": "证据充分性", "status": "ok", "detail": "图 2 直接支撑"}
  ]
}
```

## 示意输出（result.json）

```json
{
  "case_id": "demo-nanopub-01",
  "status": "success",
  "status_reason": "文字层完整，断言已拆分并绑定证据",
  "result": {
    "nanopublications": [],
    "provenance": {},
    "quality_checks": []
  },
  "evidence": [{"page": 3, "region": "x0=72,y0=400,x1=300,y1=420", "kind": "figure"}],
  "uncertainty": [],
  "change_records": [{"action": "断言拆分", "reason": "拆得细"}],
  "artifacts": {
    "structured_json": "/app/work/structured.json",
    "nanopub_json": "/app/work/nanopub.json",
    "pptx": "/app/output/paper_slides.pptx",
    "preview_pdf": "/app/output/preview.pdf"
  }
}
```

> 说明：正式测试案例、白板与对照结果由平台提供；本示例不预置任何正式断言。
