# Research Article Workflow Architecture

Claude Code setup for a reproducible research-paper pipeline.

## 1. Recommended approach

Use the existing repository as the source of truth, and create a separate folder for the article. Claude Code should coordinate reproducible work: scripts, data outputs, figures, manuscript files, review logs, and exports. Regular Claude chat can still be used for thinking, text polishing, and high-level discussion, but final artifacts should return to the repository.

Core rules:

- Do not keep critical article content only in a chat session; save it to files.
- Do not let the model invent statistical results; every numerical claim must trace to generated tables, figures, or logs.
- Use plan mode for large tasks: article structure, analysis plan, major revisions, journal compliance.
- Use direct execution for small local edits: fixing a caption, updating a table reference, formatting a section.
- Use an independent reviewer pass separate from the writer context.

## 2. Proposed folder structure

Create one top-level folder in the existing repository, for example `research_article/` or `paper_article/`.

```text
research_article/
  CLAUDE.md
  README.md

  .claude/
    commands/
      journal-requirements.md
      analysis-plan.md
      analyze-data.md
      build-figures.md
      draft-paper.md
      reviewer.md
      revise.md
      export-docx.md
      supervisor-package.md
    skills/
      journal-analyzer/SKILL.md
      stats-analyst/SKILL.md
      figure-builder/SKILL.md
      academic-writer/SKILL.md
      reviewer-agent/SKILL.md
    rules/
      paper-style.md
      python-analysis.md
      citations.md

  data/
    raw/
    processed/

  scripts/
    clean_data.py
    analyze.py
    build_figures.py
    export_docx.py

  outputs/
    tables/
    figures/
    logs/

  paper/
    journal_requirements.md
    submission_checklist.md
    analysis_plan.md
    outline.md
    methods.md
    results.md
    discussion.md
    manuscript.md
    manuscript_revised.md
    manuscript.docx

  references/
    journal_guidelines/
    papers/
    bibliography.bib

  review/
    reviewer_1.md
    reviewer_2.md
    revision_log.md
    supervisor_summary.md
```

## 3. Agent / skill architecture

| Role | Input | Output | Main responsibility |
|---|---|---|---|
| Coordinator | All project files | Plans, commands, updated files | Main Claude Code session. Chooses plan mode or direct execution and routes work to skills/subagents. |
| Journal Analyzer | Journal guidelines, author instructions | `journal_requirements.md`, `submission_checklist.md` | Extract exact requirements: word limits, structure, references, figures, ethics, data availability, file formats. |
| Stats Analyst | `data/raw`, previous research scripts | processed data, tables, analysis logs | Build reproducible analysis scripts. Never change raw data. Record assumptions and decisions. |
| Figure Builder | processed data, analysis outputs | publication figures, captions | Create consistent figures and figure notes based on journal rules. |
| Academic Writer | requirements, outputs, references | manuscript sections | Draft manuscript using only supported results and cited claims. |
| Reviewer Agent | manuscript, requirements, outputs | reviewer comments | Independent review: logic, unsupported claims, methods gaps, journal compliance, overstatements. |
| Revision Agent | review comments, manuscript | revised manuscript, revision log | Apply changes with traceability and mark unresolved issues for supervisor. |
| Export Agent | manuscript, figures, tables, bibliography | DOCX/PDF package | Generate final files reproducibly with scripts or Pandoc, then check required elements. |

## 4. End-to-end workflow

1. Create the `research_article` folder and copy existing datasets/scripts or link them clearly from prior research folders.
2. Add journal guidelines to `references/journal_guidelines/`.
3. Run `/journal-requirements` to create a requirements checklist.
4. Run `/analysis-plan` in plan mode before final statistical calculations.
5. Run `/analyze-data` to generate reproducible tables and logs.
6. Run `/build-figures` to create figures and captions.
7. Run `/draft-paper` to create `manuscript.md` based on results, figures, and references.
8. Run `/reviewer` in a fresh or forked context for independent critique.
9. Run `/revise` to apply reviewer feedback and maintain `revision_log.md`.
10. Run `/export-docx` to generate `manuscript.docx` and prepare a supervisor package.

## 5. Root CLAUDE.md template

Place this file inside `research_article/CLAUDE.md`.

```md
# Research Article Project Instructions

This folder contains a reproducible research article workflow.

## Non-negotiable rules

- Never invent statistical results, p-values, effect sizes, sample sizes, dates, or percentages.
- Every numerical claim in Results must be traceable to outputs/tables, outputs/figures, or outputs/logs.
- If a value is missing, write "not available" and mark it as unresolved.
- Do not modify files in data/raw. Create derived files in data/processed.
- Use plan mode before major analysis, manuscript restructuring, or journal-compliance work.
- Use direct execution only for small, well-scoped edits.
- Keep review/revision_log.md updated for every substantial change.
- Preserve citations and figure/table references.
- Distinguish results from interpretation. Avoid unsupported causal claims.

## Project structure

- data/raw: original datasets, never edit directly.
- data/processed: cleaned or derived datasets.
- scripts: reproducible analysis, plotting, and export scripts.
- outputs/tables: generated statistical tables.
- outputs/figures: generated figures.
- outputs/logs: analysis logs and assumptions.
- paper: manuscript sections and final drafts.
- references: journal guidelines, source papers, bibliography.
- review: reviewer comments, revision logs, supervisor summaries.

## Writing rules

- Academic tone.
- Prefer clear, concise paragraphs.
- Do not overstate findings.
- Do not introduce claims without citations or internal result provenance.
- Abstract, Methods, Results, Discussion, figures, and tables must align with journal_requirements.md.

## Analysis rules

- Prefer scripts over manual calculations.
- Save every generated artifact to outputs/.
- Document assumptions in paper/analysis_plan.md or outputs/logs/.
- If analysis depends on a choice, explain the choice before running final calculations.
```

## 6. Suggested Claude Code slash commands

### `.claude/commands/journal-requirements.md`

```text
Read references/journal_guidelines/. Extract exact journal requirements into paper/journal_requirements.md and paper/submission_checklist.md. Preserve word limits, structure, reference style, figure/table rules, required statements, file formats, and submission constraints. Do not summarize vaguely.
```

### `.claude/commands/analysis-plan.md`

```text
Use plan mode. Inspect available datasets and prior research files. Create paper/analysis_plan.md with variables, cleaning steps, statistical tests, expected tables, expected figures, assumptions, and risks. Do not calculate final results yet.
```

### `.claude/commands/analyze-data.md`

```text
Inspect data/raw and scripts. Create or update reproducible analysis scripts. Generate cleaned data, statistical tables, and analysis logs. Do not edit raw data. Save results to data/processed, outputs/tables, and outputs/logs. Explain assumptions in paper/methods_notes.md.
```

### `.claude/commands/build-figures.md`

```text
Generate publication-ready figures based on processed data and analysis outputs. Save figures to outputs/figures. For each figure, create a caption draft and interpretation note. Ensure figures match paper/journal_requirements.md.
```

### `.claude/commands/draft-paper.md`

```text
Draft or update paper/manuscript.md using journal requirements, analysis outputs, tables, figures, and references. Do not invent results. Every numerical claim must be traceable to outputs/tables, outputs/figures, or outputs/logs.
```

### `.claude/commands/reviewer.md`

```text
Act as a strict independent academic reviewer. Review paper/manuscript.md against paper/journal_requirements.md and available analysis outputs. Identify unsupported claims, missing citations, weak methodology, overstatements, formatting issues, and unclear argumentation. Write comments to review/reviewer_1.md.
```

### `.claude/commands/revise.md`

```text
Apply reviewer comments from review/reviewer_1.md to paper/manuscript.md. Create paper/manuscript_revised.md. Maintain review/revision_log.md with each issue, action taken, files changed, and status. Do not silently remove claims; support them, soften them, or mark them for supervisor review.
```

### `.claude/commands/export-docx.md`

```text
Export the current manuscript to DOCX using scripts/export_docx.py or Pandoc. Verify that figures, tables, headings, references, and required statements are present. Save output as paper/manuscript.docx.
```

### `.claude/commands/supervisor-package.md`

```text
Create review/supervisor_summary.md summarizing research question, dataset, methods, key results, figures, limitations, unresolved questions, and what feedback is needed from the supervisor.
```

## 7. Skill templates

```md
# .claude/skills/stats-analyst/SKILL.md
---
name: stats-analyst
description: Reproducible dataset inspection, cleaning, statistical analysis, and result-table generation for the research article.
context: fork
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "Describe the dataset and analysis goal"
---

You are responsible for reproducible statistical analysis.
Never edit data/raw. Write scripts and outputs only to the approved project paths.
Every generated result must have provenance: source data, script name, output path, and assumptions.

# .claude/skills/reviewer-agent/SKILL.md
---
name: reviewer-agent
description: Independent academic reviewer for manuscript quality, journal compliance, provenance, and methodological consistency.
context: fork
allowed-tools: Read, Write, Grep, Glob
argument-hint: "Manuscript file and review focus"
---

Act as a strict but constructive reviewer.
Check whether every result claim is supported by outputs.
Flag unsupported claims, unclear methods, weak citations, overstatements, missing limitations, and journal requirement violations.
Write comments to review/reviewer_1.md.
```

## 8. Path-specific rules

```md
# .claude/rules/python-analysis.md
---
paths: ["scripts/**/*.py"]
---

- Scripts must be reproducible and safe to rerun.
- Do not hardcode absolute local paths.
- Save generated artifacts under outputs/ or data/processed/.
- Print or save enough logging to reconstruct the analysis.
- Prefer clear variable names and comments for statistical assumptions.

# .claude/rules/paper-style.md
---
paths: ["paper/**/*.md"]
---

- Academic tone.
- Do not invent results.
- Keep Results factual and Discussion interpretive.
- Every table/figure reference must point to an existing output.
- Preserve numerical precision from source outputs.

# .claude/rules/citations.md
---
paths: ["paper/**/*.md", "references/**/*.bib"]
---

- Do not fabricate citations.
- Mark missing citations as TODO:CITATION_NEEDED.
- Preserve claim-source relationships.
- Keep bibliography keys stable.
```

## 9. First prompts to run in Claude Code

```text
Use plan mode. This is a research article workflow inside an existing repository.
Inspect the current repository structure and propose how to place this article folder without breaking prior research.
Do not modify files yet. Create a step-by-step implementation plan.

Then:

Create the research_article folder structure from the approved plan.
Add CLAUDE.md, README.md, .claude/commands, .claude/rules, and placeholder paper/review/output folders.
Do not move or modify existing prior research files unless explicitly instructed.
```

## 10. Claude Code vs regular Claude

| Task | Best tool | Reason |
|---|---|---|
| Repository setup, scripts, figures, generated tables | Claude Code | Needs file operations, reproducibility, and version control. |
| Statistical calculations from dataset | Claude Code | Should be implemented as rerunnable scripts, not chat-only calculations. |
| Manuscript drafting from saved outputs | Claude Code | Keeps text, results, figures, and revision history in the repo. |
| Abstract polishing, title ideas, wording alternatives | Regular Claude or Claude Code | Can be discussed conversationally, then saved back to the repo. |
| DOCX generation | Claude Code + script/Pandoc | Final document should be reproducible and regenerable. |
| Letter or message to supervisor | Regular Claude | Good for communication drafting; save final version in `review/supervisor_summary.md`. |

## 11. Quality gates before sending to supervisor

- `paper/journal_requirements.md` exists and has exact constraints.
- `paper/analysis_plan.md` explains variables, tests, assumptions, expected tables, and expected figures.
- `outputs/tables` contains generated result tables.
- `outputs/figures` contains final candidate figures.
- `paper/manuscript.md` or `manuscript_revised.md` contains no unsupported numerical claims.
- `review/reviewer_1.md` contains independent critique.
- `review/revision_log.md` documents what was changed and what remains unresolved.
- `paper/manuscript.docx` is generated reproducibly.
- `review/supervisor_summary.md` clearly explains what feedback is needed.

## 12. Minimal README.md for the article folder

```md
# Research Article Workflow

This folder contains the reproducible workflow for the article.

## Main stages

1. Journal requirements extraction
2. Dataset inspection and analysis plan
3. Reproducible analysis scripts
4. Tables and figures
5. Manuscript drafting
6. Independent review
7. Revisions and revision log
8. DOCX export and supervisor package

## Important paths

- data/raw: original data, never edit
- data/processed: cleaned data
- scripts: analysis/export scripts
- outputs/tables: generated tables
- outputs/figures: generated figures
- paper: manuscript and article materials
- review: reviewer comments and revision logs
- references: guidelines, source papers, bibliography

## Key rule

Do not write manuscript results before the corresponding analysis outputs exist.
```

## 13. Recommended first milestone

The first milestone is not to write the paper. The first milestone is to create a controlled workspace: folder structure, `CLAUDE.md`, journal requirement checklist, and analysis plan. After that, analysis and writing become much safer because every later step has provenance and review checkpoints.
