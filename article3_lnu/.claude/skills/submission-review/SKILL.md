---
name: submission-review
description: Use when the manuscript is about to be submitted or resubmitted to journal No. 69, when reviewer comments have arrived, or when anything in latex/, scripts/ or outputs/ changed and the submission may no longer be consistent.
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
argument-hint: "optional: path to reviewer comments"
---

# Submission review

Three phases, in order. Never skip phase 1 — it decides how much of phase 2 is even worth doing.

**The submission version is `latex/article_en.tex` (English).** `latex/article.tex` (Ukrainian) is
frozen reference. Reviewer comments are applied to the English version ONLY; do not sync back.

## Phase 1 — mechanical compliance

```bash
python3 scripts/check_compliance.py        # English submission version
python3 scripts/check_compliance.py uk     # Ukrainian reference version (optional)
```

The script rebuilds the PDF and checks four groups: BUILD, JOURNAL (No. 69 rules **and template
integrity** — `.sty` files byte-identical to the journal's copy, every edit to `VisnykAMI.tex`
annotated, the three bugfixes still applied, page geometry untouched, shipped figures equal to the
current `build_figures.py` output), CONSISTENCY, PROVENANCE (every share, count and effect size
recomputed from `outputs/tables/`; Table 1 rebuilt from the CSVs). Exit 0 = clean.
Currently 78 checks for `article_en.tex`, 76 for `article.tex`.

The script always rebuilds with `make -B`. Never check a PDF that `make` decided was up to date:
a PDF built from since-reverted sources will pass every source-level check while the page is
visibly broken. One such `article_en.pdf` was committed before this was enforced.

**Do not review by eye anything the script checks.** If you find yourself counting keywords or
comparing a number against a CSV by hand, stop and run the script. If a rule is checkable and the
script does not check it, add the check to the script rather than to the review.

Every FAIL is fixed before phase 2. A failing build makes the rest of the review meaningless.

## Phase 2 — judgement review

Only what the script cannot decide. Write to `review/reviewer_N.md`, one numbered comment per
issue, each marked BLOCKING / MAJOR / MINOR and pointing at a line in `latex/article_en.tex`.

Check for:

- **Claims wider than the evidence.** Correlational data, causal wording. The paper's own
  §Limitations must still cover every weakness a reviewer could name.
- **Invariance defined one way, used another.** Effect size is the criterion everywhere — text,
  tables, figures. p-values are reference only. This was the defect the article3 audit found.
- **Confounds left unaddressed.** Game version confounds the map analysis; the sensitivity
  analysis must still be present and still support the claim.
- **Method/result mismatch.** Rank test paired with a parametric effect size, paired vs
  independent thresholds — already disclosed in §2.3; check the disclosure survived edits.
- **English quality.** Literal translations from Ukrainian, term drift (a metric named two ways),
  articles and tense in the abstract.
- **Figures earning their place.** Every panel readable at 13.5 cm, no figure that the text does
  not interpret.

## Phase 3 — apply comments

- Edit `latex/article_en.tex` only.
- **A number in the text is never edited to match a reviewer's expectation.** Numbers come from
  `outputs/`. If a number is wrong, the analysis is wrong: fix `scripts/`, rerun
  `scripts/analyze.py` and `scripts/build_figures.py` (both languages), then let the text follow.
- Figure changes go through `scripts/build_figures.py`; rebuild both languages and copy into
  `latex/figures/` and `latex/figures_en/`. Never edit a figure by hand.
- Log every applied comment in `review/revision_log.md`: comment number, what changed, which file.
- **Re-run phase 1 after the last edit.** Not optional — most fixes move page breaks, and the
  template's spacing bugs surface exactly there.

## Red flags — stop

| Rationalisation | Reality |
|---|---|
| "Just this one number, the CSV is stale" | Then regenerate the CSV. Hand-edited numbers are how provenance dies. |
| "I'll re-run the checker at the end of the session" | Run it after the last edit. An unverified fix is not a fix. |
| "The reviewer is wrong, skip it" | Answer it in `review/revision_log.md` with a reason. Silent dismissal reads as sloppiness. |
| "I'll sync the fix into the Ukrainian version too" | No. It is frozen. Two diverging sources is worse than one stale one. |
| "The build warning is cosmetic" | The template prints headings over paragraphs when the page is tight. Check the PDF. |
| "Sources are fixed, the PDF must be fine" | Only if it was rebuilt. `make` skips a PDF newer than its sources; the checker forces `-B` for exactly this reason. |
| "I restored the file after testing, done" | Restoring a source does not rebuild what it produced. Re-run the checker, then look at the page. |
| "I'll re-copy the template, it's cleaner" | It carries two bugs. The annotated fixes are in `latex/VisnykAMI.tex`; a fresh copy reintroduces a build crash and a heading printed over a paragraph. |

## What the script cannot check

Plagiarism report; no second article by the same author in the same issue; article length and
deadline confirmed with the editors (journal No. 69 publishes neither); the two template bugs
reported to the editors — see `latex/README.md`.
