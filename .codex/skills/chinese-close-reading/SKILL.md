---
name: chinese-close-reading
description: Chinese close reading via text reverse engineering. Choose mode (narrative / argumentative / poetry-prose), analyze linearly, pause after each chunk.
---

# Chinese Close Reading

## Input rule
- If no passage provided: ask the user to paste it.
- If too long: ask the user to send in chunks.

## Mode lock (choose one)
- **Mode A (Narrative/Novel)**: camera language + scene/action cuts
- **Mode B (Argumentative/Expository)**: logic chain + claim/evidence progression
- **Mode C (Poetry/Prose)**: imagery clusters + sensory reconstruction

## Loop for EACH chunk (mandatory)
1. **【Anchor】**: quote key sentences/words from the chunk
2. **【Lens】**: state which mode/lens you are using
3. **【Reverse move】**: delete/replace a word/structure → explain what meaning/function is lost
4. **【Insight】**: intention / subtext / structural function → convert to exam-scoring language

After each chunk:
- Output a separator line
- Ask: “这部分你看透了吗？要不要进入下一段？”

## Exam-ready ending
Usually the next step is: ask for next chunk, or give a mini exercise.

## Style rules
- No greetings, no self-intro.
- Linear reading: no skipping.
