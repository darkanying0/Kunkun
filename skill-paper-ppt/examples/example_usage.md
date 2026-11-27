# 最小调用示例（示意，非正式案例结果）

以下为**示意输入与示意输出**，仅说明接口，不冒充正式案例结果。

## 输入

`/input/case.json`（示意）：

```json
{
  "case_id": "demo-ppt-01",
  "paper": "/input/paper.pdf",
  "template": "/input/template.pptx",
  "audience": "同行评审",
  "minutes": 15,
  "max_slides": 12,
  "output_contract": ["deliverable", "slides", "render"]
}
```

## 调用

```bash
python3 scripts/parse_pdf.py /input/paper.pdf /app/work
# ... 由 DeepSeek Harness 按 SKILL.md 提取主线、设计页级主张+图表引用、写讲稿，写出 /app/work/outline.json
python3 scripts/build_ppt.py /app/work/outline.json /app/output --template /input/template.pptx
```

## 示意输出（outline.json 片段）

```json
{
  "title": "A Study on Catalyst Design",
  "main_thread": "针对催化活性预测，本文提出方法 X，在数据集 D 上比基线高 3.2%。",
  "slides": [
    {
      "title": "研究问题",
      "claim": "现有方法未覆盖高温条件",
      "points": ["现有方法仅覆盖常温", "高温下误差增大"],
      "evidence": {"kind": "section", "ref": "§1 引言", "page": 1, "quote": "...", "note": ""},
      "notes": "先用一句话点出缺口，再引出本文；被问时可补充图1高温误差曲线。"
    },
    {
      "title": "主要结果",
      "claim": "方法 X 在数据集 D 上准确率提升 3.2%",
      "points": ["准确率 0.91 → 0.942", "同预算对比基线"],
      "evidence": {"kind": "table", "ref": "Table 2", "page": 6, "quote": "...", "note": "单位 %，同预算"},
      "notes": "强调数字来自 Table 2，注明同预算条件，不要读成示意图。"
    }
  ]
}
```

## 示意输出（result.json）

```json
{
  "case_id": "demo-ppt-01",
  "status": "success",
  "status_reason": "主线成立，页级证据映射完整，模板版式保留",
  "result": {
    "deliverable": {"pptx": "...", "main_thread": "..."},
    "slides": [],
    "render": {"preview_pdf": "..."}
  },
  "evidence": [{"page": 1, "kind": "section", "ref": "§1", "source_page": 1}],
  "uncertainty": [],
  "change_records": [{"action": "页级主张设计", "reason": "一页一主张"}],
  "artifacts": {
    "pptx": "/app/output/paper_slides.pptx",
    "preview_pdf": "/app/output/preview.pdf"
  }
}
```

> 说明：正式案例、模板与对照结果由平台提供；本示例不预置任何正式幻灯片。
