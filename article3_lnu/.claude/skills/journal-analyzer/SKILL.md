---
name: journal-analyzer
description: Use when the target venue changes or its rules need re-extracting into paper/journal_requirements.md and paper/submission_checklist.md.
context: fork
allowed-tools: Read, Write, Grep, Glob
argument-hint: "Journal guideline source to parse"
---

Read references/journal_guidelines/. Extract exact requirements (word limits, structure, fonts,
margins, reference style, required statements, file formats, deadlines, APC) into
paper/journal_requirements.md and paper/submission_checklist.md. Target: journal №69 «Вісник ЛНУ»
(ЛНУ ім. Франка). Its rules are split between the submissions page and the LaTeX template itself
(VISNYK2019.rar) — read both; the formatting parameters exist only inside the template.
Anything newly made mechanical belongs in scripts/check_compliance.py, not only in the checklist.
Do not summarize vaguely; preserve every concrete constraint and flag anything needing confirmation.
