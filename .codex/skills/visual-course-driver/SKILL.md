---
name: visual-course-driver
description: Generate VisualSpec v1.1 JSON then compile to HTML + Lecture DOCX + Quiz DOCX + ZIP via course-artifacts builder.
---

## Purpose
When the user requests an interactive visual course (HTML + DOCX handouts + quiz set), produce a VisualSpec v1.1 JSON that passes schema validation and then compile it using the repository builder.

## Output contract (strict)
You must output TWO artifacts:

### A) VisualSpec JSON (raw JSON, no code fences)
- spec_version: 1.1
- meta.title present
- sections: exactly 4 (Part 1~4)
- content_md is preferred for each section (content allowed as fallback)
- quiz_bank: 30 questions total
  - single_choice: 10
  - fill_blank: 10
  - true_false: 10
  Each question includes stem, answer, explanation. single_choice includes options.
- interactive: parabola quadratic sliders
  - params.a/b/c: min/max/step/default
  - domain (x range), optional plot_config (samples/grid)

### B) Build commands (PowerShell)
python course-artifacts\scripts\builder.py <json_path> --validate-only
python course-artifacts\scripts\builder.py <json_path> --outdir ..\output
