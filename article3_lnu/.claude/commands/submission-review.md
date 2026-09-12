Invoke the `submission-review` skill and run it end to end for journal №69.

Phase 1: `python3 scripts/check_compliance.py` — fix every FAIL before going further.
Phase 2: judgement review of `latex/article_en.tex` into `review/reviewer_N.md`.
Phase 3: apply the comments to the English version only, log them in `review/revision_log.md`,
then re-run phase 1.

If reviewer comments were supplied as an argument, start at phase 3 but still run phase 1 first
to establish a clean baseline.
