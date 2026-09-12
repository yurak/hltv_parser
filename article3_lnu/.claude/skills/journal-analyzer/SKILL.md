---
name: journal-analyzer
description: Extract exact journal submission requirements into a checklist for the target venue — journal №85 «Computer-Integrated Technologies» (LNTU, Lutsk).
context: fork
allowed-tools: Read, Write, Grep, Glob
argument-hint: "Journal guideline source to parse"
---

Read references/journal_guidelines/. Extract exact requirements (word limits, structure, fonts,
margins, reference style, required statements, file formats, deadlines, APC) into
paper/journal_requirements.md and paper/submission_checklist.md. Target: journal №85 (ЛНТУ).
Do not summarize vaguely; preserve every concrete constraint and flag anything needing confirmation.
