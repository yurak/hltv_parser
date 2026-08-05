---
paths: ["scripts/**/*.py"]
---

- Scripts must be reproducible and safe to rerun.
- Do not hardcode absolute local paths; resolve relative to the project root.
- Load *_clean.csv and apply pd.to_numeric(col, errors='coerce') to all stat columns before analysis.
- Do NOT use warnings.filterwarnings('ignore') — surface warnings.
- Save generated artifacts under outputs/ or data/processed/.
- Define invariance by effect size only (eta-squared, Cohen's d), never by p-value.
- Log sample sizes (n) at every cleaning/filtering step.
- Print or save enough logging to reconstruct the analysis.
- Prefer clear variable names and comments for statistical assumptions.
