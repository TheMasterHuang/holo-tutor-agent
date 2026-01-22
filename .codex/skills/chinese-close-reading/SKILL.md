---
name: chinese-close-reading
description: Perform Chinese text close reading via “text reverse engineering”. Chunk the passage, analyze linearly without skipping, using one of three modes (narrative / argumentative / poetry-prose). Pause after each chunk to confirm before continuing.
metadata:
  short-description: Linear close reading (no skipping) Chinese tutor.
---

## Input Rule
- If the user doesn’t provide the passage, ask them to paste it.
- If too long, ask for chunked sending.

## Mode Lock (choose one)
A) 叙事/小说：镜头语言逐行解析（场景/动作流切分）
B) 议论/说理：逻辑链条逐环扣解（论点推进切分）
C) 诗歌/散文：五感意象逐句还原（按句/意象群切分）

## Loop for EACH chunk (mandatory)
> 【原文锚点】：引用本段关键句
- 【调用视角】：A/B/C 对应的方法
- 【逆向动作】：删/替换词语或结构，看损失什么
- 【洞察】：意图/潜台词/结构功能

After each chunk:
- 输出分隔符
- 问一句：“这部分你看透了吗？要不要进入下一段？”

## End matter
✅ / ⚠️ / ➕（下一步通常是让用户发下一段）
