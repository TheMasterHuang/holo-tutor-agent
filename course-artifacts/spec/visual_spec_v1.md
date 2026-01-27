# VisualSpec v1（holo-tutor-agent 可视化输出协议）

目标：让任意学科（biology/chem/physics/...）在“正常答题/讲解”的同时，输出一份结构化 JSON。
该 JSON 由渲染器（builder.py）生成：
- 交互 HTML（可视化）
- PDF（可打印讲义，带水印）
- DOCX（可编辑讲义，带水印）
- ZIP（包含以上文件 + manifest.json）

---

## 1. 顶层结构

VisualSpec 是一个 JSON 对象，包含：

- meta：课程/讲解元信息
- answer：给聊天展示的核心文本（可选）
- sections：分章节内容（用于 PDF/DOCX 正文）
- visuals：可视化模块列表（用于 HTML，可降级到 PDF/DOCX）
- exports：导出配置
- assets：静态资源（可选，如图片/公式截图等，v1 可先不做）

---

## 2. 字段说明

### 2.1 meta（必填）
```json
{
  "title": "抛物线方程",
  "subject": "math|physics|chem|bio|history|geo|chinese|english",
  "skill": "physics-first-principles",
  "generated_at": "2026-01-23",
  "watermark": "holo-tutor-agent · internal",
  "lang": "zh-CN"
}
