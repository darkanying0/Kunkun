# 最小调用示例（示意，非正式案例结果）

以下为**示意输入与示意输出**，仅说明接口，不冒充正式案例结果。

## 输入

`/input/case.json`（示意）：

```json
{
  "case_id": "demo-notes-01",
  "material": "/input/paper.pdf",
  "task": "将论文整理成结构化笔记并生成可编辑学术 PPT",
  "output_contract": ["paper_card", "sections", "knowledge_points"]
}
```

## 调用

```bash
python3 scripts/parse_pdf.py /input/paper.pdf /app/work
# ... 由 DeepSeek Harness 按 SKILL.md 建论文卡片、章节总结、知识点，写出 /app/work/notes.json
python3 scripts/build_ppt.py /app/work/notes.json /app/output
```

## 示意输出（notes.json 片段）

```json
{
  "title": "A Study on Catalyst Design",
  "paper_card": {
    "research_question": "如何设计高活性催化剂？",
    "data": "3 组固定案例",
    "methods": "密度泛函计算 + 实验验证",
    "main_findings": "催化剂 A 活性最高",
    "conclusions": "结构决定活性",
    "limitations": "仅覆盖常温条件"
  },
  "sections": [
    {
      "heading": "1 Introduction",
      "page": 1,
      "bbox": [72, 180, 300, 194],
      "purpose": "提出问题",
      "method": "文献回顾",
      "result": "",
      "conclusion": ""
    }
  ],
  "knowledge_points": [
    {"concept": "催化活性", "statement": "催化剂 A 活性最高", "page": 3, "evidence": "图 2"}
  ]
}
```

## 示意输出（result.json）

```json
{
  "case_id": "demo-notes-01",
  "status": "success",
  "status_reason": "文字层完整，章节对齐、字段齐备",
  "result": {
    "paper_card": {},
    "sections": [],
    "knowledge_points": []
  },
  "evidence": [{"page": 1, "region": "x0=72,y0=180,x1=300,y1=194", "kind": "text"}],
  "uncertainty": [],
  "change_records": [{"action": "章节切分对齐原文", "reason": "对得上"}],
  "artifacts": {
    "structured_json": "/app/work/structured.json",
    "notes_json": "/app/work/notes.json",
    "pptx": "/app/output/paper_slides.pptx",
    "preview_pdf": "/app/output/preview.pdf"
  }
}
```

> 说明：正式测试案例、白板与对照结果由平台提供；本示例不预置任何正式笔记。
