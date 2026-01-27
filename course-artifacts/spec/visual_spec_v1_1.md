# VisualSpec v1.1（数据契约）

目标：让 agent 输出一份结构化 JSON，构建器可稳定生成：
- `course_interactive.html`
- `<title>_讲稿.docx`
- `<title>_习题集.docx`
- `course_notes.pdf`（可选）
- `manifest.json` + `bundle.zip`（可选）

## 1) 顶层字段（必需）

- `spec_version`: `"1.1"`（或 `"v1.1"`）
- `meta`: 元信息（见下）
- `exports`: 导出开关（见下）
- `interactive`: 交互模块配置（见下）
- `sections`: 正文分段（至少 4 个）
- `quiz_bank`: 题库（30 题：三类各 10）

## 2) meta（必需）

- `meta.title`: 课程标题
- `meta.date`: 生成日期/时间（字符串即可）
- `meta.watermark`: 水印（可选；默认 `holo-tutor-agent`）
- `meta.level`: 难度（可选）

兼容字段：
- `meta.generated_at` 会被当作 `meta.date`（向后兼容）

## 3) exports（必需）

```json
{
  "html": true,
  "lecture_docx": true,
  "quiz_docx": true,
  "pdf": false,
  "zip": true,
  "zip_name": "bundle.zip"
}
```

兼容字段：
- `exports.docx` 会被当作 `exports.lecture_docx`

CLI 覆盖：
- `--only html,lecture_docx` 会忽略 `exports`，只生成指定产物。

## 4) interactive（必需）

交互模块完全数据驱动（滑块范围/步长、绘图区范围、采样点数等）。

```json
{
  "type": "parabola_quadratic",
  "domain": { "x_min": -10, "x_max": 10 },
  "range": { "y_min": -10, "y_max": 10 },
  "params": {
    "a": { "min": -5, "max": 5, "step": 0.01, "default": 1.5 },
    "b": { "min": -10, "max": 10, "step": 0.01, "default": 0 },
    "c": { "min": -10, "max": 10, "step": 0.01, "default": 0 }
  },
  "plot_config": { "samples": 800, "grid": true },
  "features": { "show_vertex": true, "show_axis": true, "show_intercepts": false }
}
```

## 5) sections / lecture_notes

每段包含：
- `id`
- `title`
- `content_md`（主字段）
- `content`（兼容字段，`content_md` 缺失时 fallback）

`lecture_notes` 可选；若存在，讲稿 DOCX 优先使用它，否则使用 `sections`。

## 6) quiz_bank（必需）

```json
{
  "single_choice": [ ...10题... ],
  "fill_blank":   [ ...10题... ],
  "true_false":   [ ...10题... ]
}
```

题目字段：
- 单选题：`stem`、`options`、`answer`、`explanation`
- 填空题：`stem`、`answer`、`explanation`
- 判断题：`stem`、`answer`、`explanation`（`answer` 可为 boolean 或 `"正确"/"错误"` 等）

## 7) Schema

JSON Schema 文件：`course-artifacts/spec/visual_spec_v1_1.schema.json`
