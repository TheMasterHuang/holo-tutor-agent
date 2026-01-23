---
name: subject-router
description: Route the user request to the most suitable subject skill; optionally continue answering using the selected driver’s format.
---

# Subject Router

## Purpose
- Route the request to **one** best-matching subject driver.
- If the user explicitly invokes `$subject-router`, **first print routing lines**, then:
  - If the question is clear: you may continue with the selected driver’s full answer format.
  - If key info is missing: ask **one** most important clarifying question and stop.

## Routing Rules (priority)
1. Chinese close reading / text analysis / 阅读题 / “逐段精读、赏析、批注” → `chinese-close-reading`
2. English vocab / translation / sentence making / correction → `english-coach`
3. History events / institutions / material-based questions → `history-driver`
4. Geography (atmosphere/circulation/climate/landform/hydrology, local circulation like sea-land breeze) → `geo-driver`
5. Chemistry (electrolyte/reaction/mole/solution/redox/electrochemistry) → `chem-driver`
6. Biology (cell/genetics/homeostasis/ecology/metabolism) → `biology-tutor`
7. Physics (mechanics/EM/thermo/optics/waves/quantitative problems/first-principles) → `physics-first-principles`
8. Meta “what is the essence/framework/learning path” → `discipline-architect`

## Output (Routing Lines)
When invoked as `$subject-router ...`, print exactly the following 3 lines first:

- `Selected skill: <skill-name>`
- `Assumption: <one short sentence or "none">`
- `Handoff: <repeat the user question in one line>`

Then follow the continuation rule:
- If clear: continue **using the selected skill’s output structure**.
- If unclear: ask **one** clarifying question and stop.
