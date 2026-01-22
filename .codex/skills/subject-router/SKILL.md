---
name: subject-router
description: Decide which tutoring subject skill to use when the user request is ambiguous, mixed, or unclear. Output the selected skill and a 1-line handoff instruction.
metadata:
  short-description: Route tutoring requests to the right skill.
---

## Goal
Choose the best skill(s) for the user’s request with minimal friction.

## Inputs (assume if missing)
- User request text
- Optional: grade/level, goal (understand vs exam), provided data/passage/problem

## Routing Heuristics
- “本质/站在更高处/学科是什么/底层骨架/框架” → discipline-architect
- Geography keywords: 气压带风带、洋流、地形、气候、季风、锋面、圈层、尺度 → geo-driver
- Chemistry keywords: 反应方程式、氧化还原、离子、摩尔、平衡、酸碱、周期表 → chem-driver
- History keywords: 变法、制度、革命、国家治理、朝代更替、影响意义、背景措施 → history-driver
- English keywords: 单词怎么记、词根词缀、翻译、造句、改 Chinglish → english-coach
- Biology keywords: 细胞、膜、酶、光合呼吸、遗传、稳态、生态 → biology-tutor
- Chinese keywords: 课文精读、逐段分析、小说/议论文/诗歌散文、作者意图 → chinese-close-reading
- Physics keywords: 力学、电磁、能量、动量、圆周、题目求解、建模 → physics-first-principles

## Output Format
- Selected skill: `<skill-name>` (or 2 skills in order)
- Assumption: 1 short line if needed
- Handoff: 1 line telling the next skill what to do
