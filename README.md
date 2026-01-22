# Holo Tutor Agent (Codex Skills)

This repo packages a single tutoring agent behavior via `AGENTS.md` and multiple subject skills under `.codex/skills/`.

## How it works
- Codex reads `AGENTS.md` before doing work (project instructions).
- Codex discovers skills in `.codex/skills/**/SKILL.md` (repo-scoped skills).
- Each skill has YAML front matter: `name`, `description`, optional `metadata`.

## Quick test prompts
Try any of these:
- “解释一下海陆风的形成机制，并画 ASCII 图。”
- “为什么 NaCl 是离子化合物？用很直观的方式讲。”
- “如何评价商鞅变法？给我一段故事+高分答题模板。”
- “abandon 这个词怎么记？顺便拓展同根词。”
- “解释细胞膜的流动镶嵌模型，并给一道典型非选择题示范答案。”
- “我发一篇《背影》，你带我逐段精读（我会分段发）。”
- “一个物体做匀速圆周运动，向心力从哪来？怎么建模？”

## Notes
After adding or editing skills, restart Codex so it reloads skill metadata.\
灵感来源——【李继刚】老师
