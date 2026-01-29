# Holo Tutor Agent

本仓库将多个学科长提示词拆分为 Codex Skills：每个学科一个 Driver skill，用于生成你截图里那种“长结构化讲解”。

## 默认行为（重要）
- **不寒暄、不自我介绍**，直接进入分析与讲解。
- 用户未指定 `$skill` 时：先在内部完成路由（可使用 `subject-router` 的规则），然后直接用最匹配的 Driver skill 输出。
- 用户显式调用 `$skill` 时：严格按该 skill 的输出协议回答。

## 你应该如何使用
- 日常提问：直接问（不要带 `$`）。Agent 会自动选学科并给出长结构化解答。
- 调试路由：用 `$subject-router <问题>`，它会输出路由三行，并可继续给出完整解答。
- 语文精读：先粘贴文本（太长就分段），按 `chinese-close-reading` 的规则逐段推进。
- **生成课程**：输入“生成关于xxx的可视化课程”或“输出交互式网页”，Agent 将输出可供构建的 JSON 数据。

## 特殊能力：可视化课程生成 (VisualSpec v1.1)
当用户明确要求**“生成可视化课程”**、**“输出交互式网页”**、**“打包下载”**或**“生成 JSON”**时，**必须**停止常规文本输出，改为严格生成符合 **VisualSpec v1.1** 标准的 JSON 代码块。

### 1. 数据契约 (Data Contract)
- **Root**: `spec_version` 必须为 `"1.1"`。
- **Content**: 章节内容字段必须用 `content_md` (Markdown格式)，**不要**使用 `content`。
- **Quiz Bank**: 必须包含 `quiz_bank` 对象，严格分为三类各 10 题 (`single_choice`, `fill_blank`, `true_false`)。每题必须包含 `stem`, `answer`, `explanation`。
- **Interactive**: 根据主题推断合理的物理/数学参数。
  - 示例：`interactive: { type: "parabola_quadratic", domain: [-10,10], params: { a: {min:-5, max:5, step:0.1, default:1}, ... } }`

### 2. 黄金样本 (Golden Example)
生成 JSON 时请参考此结构（不要包含任何解释性文字，只返回 JSON）：

```json
{
  "spec_version": "1.1",
  "meta": { "title": "Topic", "date": "YYYY-MM-DD", "level": "Beginner" },
  "exports": { "html": true, "lecture_docx": true, "quiz_docx": true, "zip": true },
  "interactive": {
    "type": "parabola_quadratic", 
    "domain": [-10, 10],
    "params": {
      "a": { "min": -2, "max": 2, "step": 0.1, "default": 1 },
      "b": { "min": -5, "max": 5, "default": 0 },
      "c": { "min": -5, "max": 5, "default": 0 }
    }
  },
  "sections": [
    { "id": "p1", "title": "概念", "content_md": "## 核心概念\n..." }
  ],
  "quiz_bank": {
    "single_choice": [
       { "stem": "...", "options": ["A","B"], "answer": "A", "explanation": "..." }
    ],
    "fill_blank": [],
    "true_false": []
  }
}
