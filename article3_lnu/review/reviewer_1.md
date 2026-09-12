# Reviewer 1 — Independent Review

**Manuscript:** «Ідентифікація контекстно-інваріантних метрик майстерності гравця у кіберспорті на основі аналізу розмірів ефекту»
**Target journal:** №85 «Комп'ютерно-інтегровані технології» (ЛНТУ), category Б
**Reviewer role:** strict independent academic reviewer
**Date:** 2026-06-29

---

## Summary verdict

**MAJOR REVISION.**

The science is sound and — notably — the manuscript is *fully reproducible at the number level*: every numerical claim I checked in the abstract, Results, Discussion and Conclusions matches the source CSVs in `outputs/tables/` to displayed precision. Internal consistency of the invariance counts (35/76.1 %, 43/93.5 %, 22/47.8 %, universal 33, triple 16) is exact across all sections and the summary table. The methodology (effect-size criterion over p-values, paired test for sides, version-stratified sensitivity check) is appropriate and correctly described, and directly remediates both defects flagged in the article3 audit.

The verdict is **Major** rather than **Minor** for two hard, blocking reasons that are independent of the analysis quality:

1. **Three core references are unwritten** (`TODO:CITATION_NEEDED` for [1], [2], [3] in *both* reference blocks). The first three in-text citations therefore point at nothing. A category-Б journal cannot accept a manuscript whose Introduction is uncited.
2. **Both abstracts fall short of the journal's 200-word requirement** (UKR 154 words, ENG 172 words — measured below), and the ORCID is a placeholder (`0000-0000-0000-0000`).

These are mechanical to fix but are genuine non-compliance items, so the manuscript cannot be accepted as-is. Once [1]–[3] are supplied, the abstracts expanded to ~200 words, and the ORCID corrected, this is a clean accept candidate.

---

## Provenance check

Every number cited in the abstract and §§2–3 was verified against the source CSVs. All checks **OK**.

| # | Manuscript claim (location) | Source file:value | Verdict |
|---|---|---|---|
| 1 | n = 3486 (abstract, §2.1, §5) | logs / all CSVs (n_cs2 1820 + n_csgo 1666 = 3486) | OK |
| 2 | CS2 1820, CSGO 1666 (abstract, §2.1) | version_invariance.csv n_cs2=1820, n_csgo=1666 | OK |
| 3 | 8 maps de_* (§2.1) | analysis_plan §2 (8 maps) | OK |
| 4 | 46 metrics (abstract, §2.1, §3) | each CSV has 46 feature rows | OK |
| 5 | Map invariant 35 = 76.1 % (abstract, §3.1, §5) | summary.csv map: 35/46=76.1; recomputed 35/46=76.1 | OK |
| 6 | Version invariant 43 = 93.5 % (abstract, §3.2, §5) | summary.csv version: 43/46=93.5 | OK |
| 7 | Side invariant 22 = 47.8 % (abstract, §3.3, §5) | summary.csv side: 22/46=47.8 | OK |
| 8 | Universal (map∩version) = 33 (§3.4) | summary.csv universal_map_version=33; recomputed 33 | OK |
| 9 | Triple-invariant = 16 (abstract, §3.4, §5) | summary.csv triple=16; recomputed map∩version∩side=16 | OK |
| 10 | Table 1 lists the 16 triple features | exact set match to summary.csv triple list | OK |
| 11 | map opening_deaths_per_round η²=0.001 (§3.1) | map_invariance.csv 0.000575 → 0.001 | OK |
| 12 | map opening_attempts η²=0.001 (§3.1) | map_invariance.csv 0.000892 → 0.001 | OK |
| 13 | map 1on1_win_percentage η²=0.001 (§3.1) | map_invariance.csv 0.000935 → 0.001 | OK |
| 14 | map utility η²=0.247 (§3.1) | map_invariance.csv 0.24709 → 0.247 | OK |
| 15 | map utility_damage_per_round η²=0.243 (§3.1) | map_invariance.csv 0.24282 → 0.243 | OK |
| 16 | map flashes_thrown_per_round η²=0.209 (§3.1) | map_invariance.csv 0.20901 → 0.209 | OK |
| 17 | version opening_deaths_per_round d=0.003 (§3.2) | version_invariance.csv 0.002961 → 0.003 | OK |
| 18 | version utility d=0.004 (§3.2) | version_invariance.csv 0.003654 → 0.004 | OK |
| 19 | version last_alive_percentage d=0.015 (§3.2) | version_invariance.csv 0.015202 → 0.015 | OK |
| 20 | version assisted_kills_percentage d=2.51 (§3.2) | version_invariance.csv 2.51121 → 2.51 | OK |
| 21 | version assisted_kills 27.1 % CS2 vs 17.8 % CSGO (§3.2) | version_invariance.csv 27.058 / 17.838 | OK |
| 22 | version assists_per_round d=1.80 (§3.2) | version_invariance.csv 1.80130 → 1.80 | OK |
| 23 | version support_rounds d=0.96 (§3.2) | version_invariance.csv 0.96342 → 0.96 | OK |
| 24 | side opening_attempts d=0.001 (§3.3) | side_invariance.csv 0.000729 → 0.001 | OK |
| 25 | side entrying d=0.005 (§3.3) | side_invariance.csv 0.004692 → 0.005 | OK |
| 26 | side pistol_round_rating d=0.009 (§3.3) | side_invariance.csv 0.008622 → 0.009 | OK |
| 27 | side saves_per_round_loss d=1.96 (§3.3) | side_invariance.csv 1.96341 → 1.96 | OK |
| 28 | side trade_kills_percentage d=1.00 (§3.3) | side_invariance.csv 1.00406 → 1.00 | OK |
| 29 | side saved_by_teammate_per_round d=0.98 (§3.3) | side_invariance.csv 0.97763 → 0.98 | OK |
| 30 | side flashes_thrown_per_round d=0.97 (§3.3) | side_invariance.csv 0.97034 → 0.97 | OK |
| 31 | PCA PC1 23.1 %, PC2 18.2 %, Σ 41.3 % (§3.5) | captions.md PC1 23.1 %, PC2 18.2 % (sum 41.3) | OK |
| 32 | Sensitivity: CS2 71.7 %, CSGO 76.1 % (§3.5) | map_invariance_by_version.csv cs2 33→71.7, csgo 35→76.1 | OK |
| 33 | Discussion variant shares: version 7 %, map 24 %, side 52 % (§4) | 100−93.5=6.5≈7; 100−76.1=23.9≈24; 100−47.8=52.2≈52 | OK |

**No provenance mismatches found.** The manuscript's provenance note (lines 140–142) is accurate.

### One presentational caveat (not a mismatch)
- The "η² = 0,001" figures (rows 11–13) are rounded from values like 0.000575/0.000892/0.000935 that round to **0.001** but differ in the third significant figure. Reporting all three as "0,001" is defensible but hides that they are not equal; consider an extra digit or "< 0.001" framing for the smallest. Cosmetic only.
- §3.5 reports CS2 sensitivity = **71.7 %**, which is numerically identical to the universal (map∩version) percentage (also 71.7 %, because both are 33/46). These are *different quantities* that coincide. Not an error, but a reader could be confused; a half-sentence clarifying they are distinct would help.

---

## Journal-compliance checklist (vs `journal_requirements.md`)

| Requirement | Status | Notes |
|---|---|---|
| IMRAD structure | **PASS** | Вступ → Матеріали і методи → Результати → Обговорення → Висновки (manuscript §§1–5) |
| УДК | **PASS** | line 1: `УДК 004.85:519.237.8` |
| ORCID | **FAIL** | line 3: placeholder `0000-0000-0000-0000`; co-author Furgala has **no** ORCID at all (req §5 item 2 lists ORCID for authors) |
| Bilingual title | **PASS** | UKR line 6, ENG line 8 |
| Authors: ПІБ, ступінь, місце роботи | **PASS** | lines 3–4 (Kuzhii — аспірант; Furgala — канд. техн. наук, доцент; LNU) — note: affiliation is **Львівський** (Ivan Franko), while target journal is **Луцький** (LNTU). Allowed, but confirm intended. |
| Bilingual abstract ~200 words | **FAIL** | UKR = **154 words**, ENG = **172 words** (both measured; target 200). Both under-length; UKR especially short. |
| Keywords 5–10, bilingual | **PASS** | UKR 8 keywords (line 16), ENG 8 keywords (line 22) |
| ДСТУ 8302 numeric citations `[1]` | **PASS (format)** | in-text uses `[1]`, `[1, 2]`, `[2-3]`-style ranges |
| Two reference blocks (original + romanized References) | **PASS (structure) / FAIL (content)** | Both blocks present (lines 120–136); but [1]–[3] are `TODO:CITATION_NEEDED` in both |
| Length plausibly 5–10 pages | **PASS (likely)** | ~1865 words + 1 table + 4 figure callouts; at 11 pt single-spacing this is plausibly 5–7 pp. Cannot confirm exactly from Markdown — verify after .docx layout. |
| File format `.docx`, A4, TNR 11 pt, margins | **N/A here** | Source is Markdown; formatting must be applied in the Word template before submission |
| No page numbers; MS Word equation editor | **N/A here** | Apply at .docx stage |
| Plagiarism check | **OPEN** | Required by §10; not evidenced in repo |

**Compliance summary:** structurally compliant; blocked by (a) placeholder/missing ORCID, (b) under-length abstracts, (c) unwritten references [1]–[3].

---

## Methodology issues

Overall the methodology is **sound and correctly described**. Specific assessments:

1. **Effect-size criterion (η² < 0.06; Cohen's d < 0.5).** Correct and well-motivated for n ≈ 3486. Thresholds are Cohen's conventional "medium" boundaries and are stated consistently in §2.2–2.3, the plan, and CLAUDE.md. The CSV `invariant` flags were independently recomputed and agree with these thresholds. **OK.**

2. **Test selection.** One-way ANOVA + η² for 8 maps, Mann–Whitney + Cohen's d for versions, paired t-test + paired d for sides — all appropriate. The paired design for sides (same player's CT/T profile) is correctly justified (§2.3) and reflected in n_pairs in `side_invariance.csv`. **OK.**

3. **Inconsistency between test family and effect size (minor).** For versions the *test* is Mann–Whitney (rank-based, justified by non-normality/outliers), but the *effect size* is parametric Cohen's d on raw means/SDs. This is internally serviceable but slightly mismatched: a rank-based effect size (e.g., rank-biserial / Cliff's δ) would be more coherent with a non-parametric test. Not wrong, but the manuscript should acknowledge the choice in one sentence. Likewise, paired Cohen's d defined as |μ_diff|/σ_diff (§2.3) is the *within-subject* (drz) form — fine, but state explicitly that thresholds borrowed from Cohen's independent-samples conventions are being applied to a paired d, which inflates magnitudes relative to the independent-samples d. This affects interpretation of the side dimension specifically.

4. **Confounding / sensitivity handling.** The map–version confound is correctly identified (§2.3, §3.5) and addressed by re-computing map invariance *within* each version (`map_invariance_by_version.csv`). Results (71.7 % / 76.1 % vs 76.1 % pooled) support the robustness claim. This properly closes audit minor-note #1. **OK.** One gap: the sensitivity check is reported only as aggregate percentages; it does not state whether the *same* features flip in/out across versions. Recommend one sentence on set stability, or note it as a limitation.

5. **Missing-data handling.** §2.1 states ≤1 % missing for most metrics, 9–21 % for derived sniper percentages, logged in cleaning. Limitation §(3) acknowledges up to 21 %. Adequate, but the manuscript does not state how NaNs were handled in each test (pairwise deletion? the n columns in the CSVs vary — e.g., 1on1_win_percentage version n_cs2=1754 not 1820, side n_pairs=3026). This is correctly *reflected* in the data but **not explained in Methods**. Add a sentence: tests use available cases per feature; report this matches audit minor-note #2 ("different denominators … must be explicitly described in Methods"), which is currently only partially satisfied.

6. **Causal language — mostly disciplined, two soft overstatements.**
   - §3.1: "результативність перших боїв відображає індивідуальний скіл" and §3.2: "оновлена механіка CS2 змінила переважно патерни асистів" are *interpretive/causal* claims placed in **Results**. They belong in Discussion (see Writing). The CS2-"changed"-mechanics phrasing is causal and is correctly hedged elsewhere (Limitation §4 says analysis is correlational) — but the Results wording does not hedge.
   - Abstract: "відображає внутрішні здібності гравця" — acceptable as a framed interpretation, and Discussion §104 and Limitation §4 appropriately temper it. **OK overall** given the explicit correlational caveat.

7. **No multiple-comparisons / CI reporting.** 46 features × 3 dimensions = 138 tests; p-values are shown but explicitly demoted (correct given the effect-size paradigm), so no correction is needed for the *invariance decision*. However, no confidence intervals on η²/d are reported. For an effect-size–driven paper, bootstrap CIs (or at least noting their absence) would strengthen the central methodological claim. Optional but recommended.

---

## Citations

1. **BLOCKING — three unwritten references.** `[1]`, `[2]`, `[3]` are `TODO:CITATION_NEEDED` in **both** the original list (lines 122–124) and the romanized References (lines 131–133). These back the entire Introduction (lines 28, 30, 32: ML in esports analytics; outcome prediction/scouting; feature invariance / domain shift). The paper cannot stand without them. Supply real, verifiable sources.
2. **No fabricated references detected.** The three concrete sources are real and correctly formatted:
   - [4] Jolliffe, *Principal Component Analysis*, 2nd ed., Springer 2002 — genuine.
   - [5] Cohen, *Statistical Power Analysis for the Behavioral Sciences*, 2nd ed., 1988 — genuine.
   - [6] Sullivan & Feinn, "Using effect size — or why the p value is not enough," *J Grad Med Educ* 4(3):279–282, 2012 — genuine.
   Good practice: no invented DOIs or page numbers. The honest `TODO` markers (per repo citation rules) are the correct interim state but must be resolved before submission.
3. **Citation [6] usage.** Cited in §1 (line 32) alongside [5]; appropriate. Note [6] appears only once — fine.
4. **ДСТУ block parity.** Both blocks have 6 entries with matching keys; once [1]–[3] are filled, ensure the original-language and romanized entries describe the *same* sources in the same order.

---

## Writing

1. **Results/Discussion mixing (fix).** Two interpretive sentences sit in Results:
   - §3.1 (line 66): "…різні карти потребують різних гранатних стратегій, тоді як результативність перших боїв відображає індивідуальний скіл." — interpretation → move to Discussion.
   - §3.2 (line 70): "Тобто базові механічні навички переносяться між версіями, а оновлена механіка CS2 змінила переважно патерни асистів і підтримки." — interpretation/causal → move to Discussion.
   - §3.3 (line 74): "CT-сторона більше зберігає зброю (захист економіки)…" — borderline interpretive; consider trimming the parenthetical rationales from Results.
   Results should state the numbers; the "why" belongs in §4, which already covers these themes and would absorb them cleanly.
2. **Abstract under-length (fix, tied to compliance).** Expand both abstracts to ~200 words. Natural additions: one sentence on the dataset/source period, one on the sensitivity check result, one on the practical scouting implication. Keep UKR and ENG parallel.
3. **§3.5 potential reader confusion (minor).** Clarify that the 71.7 % CS2 sensitivity figure and the 71.7 % universal-set figure are distinct quantities that happen to coincide (both 33/46).
4. **"η² = 0,001" triple (cosmetic).** As noted in Provenance, three different values all display as 0,001; consider an extra significant figure.
5. **Figure cross-references.** Figures 1–4 are called out (lines 95–98) and match `captions.md`; ensure the actual PNGs exist in `outputs/figures/` at submission (not verifiable from Markdown). Caption text in `captions.md` is consistent with the unified effect-size coding (good — this closes audit defect #2).

---

## Required changes (numbered, prioritized)

1. **[BLOCKING] Supply references [1], [2], [3]** in both reference blocks with real, verifiable sources; keep original-language and romanized entries aligned. (Citations §1; manuscript lines 122–124, 131–133.)
2. **[BLOCKING] Provide a real ORCID** for Kuzhii (replace `0000-0000-0000-0000`, line 3) and add an ORCID for co-author Furgala, or state its absence per journal policy. (Compliance.)
3. **[BLOCKING] Expand both abstracts to ~200 words** (currently UKR 154, ENG 172) while keeping them parallel. (Compliance §5; manuscript lines 14, 20.)
4. **[HIGH] Move interpretive/causal sentences out of Results** into Discussion (lines 66, 70; trim line 74). (Writing §1.)
5. **[HIGH] Add a Methods sentence on missing-data handling** (available-case/pairwise deletion; explain why per-feature n varies, e.g. 1on1_win_percentage, sniper percentages) — fully satisfies audit minor-note #2. (Methodology §5.)
6. **[MEDIUM] Add one sentence reconciling the non-parametric version test with the parametric Cohen's d**, and explicitly flag that paired d uses thresholds borrowed from independent-samples conventions. (Methodology §3.)
7. **[MEDIUM] State whether the same features remain map-invariant within each version** in the sensitivity check, or note set-stability as a limitation. (Methodology §4.)
8. **[MEDIUM] Confirm affiliation** (Ivan Franko LNU) vs the LNTU-published target journal, and confirm the co-authored manuscript's APC/fee-waiver status (journal_requirements §8 flags the waiver likely does not apply). (Compliance.)
9. **[LOW] Verify final .docx length is 5–10 pp** and apply the journal template (A4, TNR 11 pt / abstracts 9 pt, margins, no page numbers, equation editor). (Compliance.)
10. **[LOW] Confirm all four figure PNGs exist** in `outputs/figures/` with the unified effect-size color coding described in `captions.md`. (Writing §5.)

---

## Optional improvements

- Report bootstrap confidence intervals for η² and Cohen's d to reinforce the effect-size paradigm that is the paper's central methodological contribution.
- Consider a rank-based effect size (Cliff's δ / rank-biserial) for the version dimension to match the Mann–Whitney test.
- Add one extra significant figure (or "< 0.001") for the three smallest η² values so equal-looking values are distinguishable.
- In §3.5, briefly note how many features overlap between the per-version map-invariant sets to substantiate "об'єднання версій не спотворює висновків."
- A short paragraph connecting the 16 triple-invariant features to the planned downstream skill/scouting model (the publication line's next episode) would strengthen the "Перспектива" in §5.
- Consider citing a domain-shift / invariant-feature-learning reference for [3] that directly supports the framing in line 30, rather than a generic feature-selection source.

---

### Reviewer's overall note
This is a careful, honest, reproducible piece of work whose numerical backbone is exemplary — I could not find a single fabricated or mismatched statistic, and the v2 design correctly fixes both audit defects. The Major-revision verdict rests entirely on compliance/citation completeness (references, ORCID, abstract length) plus a modest Results/Discussion cleanup. None of these touch the analysis. Resolve items 1–5 and this is publishable.
