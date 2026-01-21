# Feature Invariance Analysis for CS2/CSGO Player Statistics

## Overview

This analysis investigates the **invariance properties** of player performance features across three dimensions:
1. **Maps** (de_train, de_nuke, de_inferno, de_mirage, de_dust2, de_vertigo, de_ancient, de_anubis)
2. **Game versions** (Counter-Strike 2 vs Counter-Strike: Global Offensive)
3. **Sides** (Terrorist vs Counter-Terrorist)

Understanding feature invariance is crucial for:
- Building robust player skill models that generalize across contexts
- Identifying which metrics truly capture individual player ability vs situational factors
- Feature selection for machine learning models in esports analytics

## Dataset

| Parameter | Value |
|-----------|-------|
| Total records | 3,486 |
| CS2 records | 1,820 |
| CSGO records | 1,666 |
| Maps | 8 |
| Numeric features | 104 |

Features include performance metrics across categories: firepower, trading, opening duels, clutching, sniping, and utility usage.

## Methods

### 1. Map Invariance: ANOVA with Eta-squared

**Method:** One-way ANOVA (Analysis of Variance) with eta-squared (η²) effect size

**Why this method:**
- ANOVA is the standard approach for comparing means across **more than two groups** (8 maps)
- The F-test determines if there are statistically significant differences between map groups
- **Eta-squared** provides a measure of effect size independent of sample size

**Interpretation of η²:**
| η² Value | Effect Size |
|----------|-------------|
| < 0.01 | Negligible |
| 0.01 - 0.06 | Small |
| 0.06 - 0.14 | Medium |
| > 0.14 | Large |

**Threshold chosen:** η² < 0.06 (small effect) indicates map-invariant features

**Formula:**
```
η² = SS_between / SS_total
```

Where:
- SS_between = Σ nᵢ(x̄ᵢ - x̄)² (variance between groups)
- SS_total = Σ(xᵢⱼ - x̄)² (total variance)

### 2. Game Version Invariance: Mann-Whitney U with Cohen's d

**Method:** Mann-Whitney U test (non-parametric) with Cohen's d effect size

**Why this method:**
- Mann-Whitney U is **robust to non-normal distributions**, common in gaming statistics
- Unlike t-test, it doesn't assume equal variances or normality
- Works well with the moderate sample sizes in each group (~1,700-1,800)
- **Cohen's d** quantifies the practical significance of differences

**Interpretation of Cohen's d:**
| d Value | Effect Size |
|---------|-------------|
| < 0.2 | Negligible |
| 0.2 - 0.5 | Small |
| 0.5 - 0.8 | Medium |
| > 0.8 | Large |

**Threshold chosen:** d < 0.5 (small-to-medium effect) indicates version-invariant features

**Formula:**
```
d = |μ₁ - μ₂| / σ_pooled

where σ_pooled = √((σ₁² + σ₂²) / 2)
```

### 3. Side Invariance: Paired t-test with Cohen's d

**Method:** Paired samples t-test with Cohen's d for paired data

**Why this method:**
- Each player has **paired observations** (CT stats and T stats from the same matches)
- Paired t-test accounts for within-subject correlation, increasing statistical power
- More appropriate than independent samples test when data is naturally paired
- Reduces variance from individual player differences

**Formula for paired Cohen's d:**
```
d = |μ_diff| / σ_diff

where μ_diff = mean(CT - T) and σ_diff = std(CT - T)
```

### 4. Dimensionality Reduction: PCA

**Method:** Principal Component Analysis (PCA)

**Why this method:**
- Visualizes high-dimensional feature space in 2D
- Reveals clustering patterns by maps/versions without supervision
- Shows whether groups are separable in feature space
- PC1 and PC2 capture maximum variance directions

## Results Summary

### Map Invariance
- **27 features (75%)** are map-invariant
- Most invariant: `opening_deaths_per_round`, `opening_attempts`, `opening_kills_per_round`
- Most variant: `utility`, `utility_damage_per_round`, `flashes_thrown_per_round`

**Interpretation:** Opening duel statistics are consistent across maps, while utility usage varies significantly (different maps require different grenade strategies).

### Game Version Invariance (CS2 vs CSGO)
- **33 features (91.7%)** are version-invariant
- Most invariant: `opening_deaths_per_round`, `utility`, `clutch_points_per_round`
- Most variant: `assisted_kills_percentage`, `assists_per_round`, `support_rounds`

**Interpretation:** Core mechanical skills transfer between game versions, but CS2's updated mechanics changed team coordination patterns (assists, support).

### Side Invariance (T vs CT)
- **14 features (48.3%)** are side-invariant
- Most invariant: `opening_attempts`, `entrying`, `pistol_round_rating`, `clutching`
- Most variant: `saves_per_round_loss`, `utility_damage_per_round`, `flashes_thrown_per_round`

**Interpretation:** Side has the largest impact on feature distributions. CT side saves more (defending economy), uses more utility damage (holding positions), while T side throws fewer flashes (less need to clear angles).

### Universal Invariant Features (all three dimensions)

These 11 features are stable across maps, game versions, AND sides:

| Feature | Description |
|---------|-------------|
| `rating_3.0` | Overall player rating |
| `firepower` | Raw fragging ability |
| `opening` | Opening duel involvement |
| `opening_attempts` | Frequency of first fights |
| `pistol_round_rating` | Performance in pistol rounds |
| `clutching` | Clutch situation handling |
| `clutch_points_per_round` | Clutch contribution |
| `entrying` | Entry fragging tendency |
| `sniping` | AWP/sniper usage style |
| `sniper_multi_kill_rounds` | Multi-kill rounds with sniper |
| `sniper_opening_kills_per_round` | Opening kills with sniper |

**Key insight:** These features represent **intrinsic player skills** that persist regardless of context. They are ideal candidates for player skill modeling and talent scouting.

## Visualizations

### 1. Invariance Summary (`invariance_summary.png`)
Three horizontal bar charts showing effect sizes for each analysis dimension. Green bars indicate invariant features, red bars indicate variant features.

### 2. PCA Visualization (`pca_visualization.png`)
- Left: Points colored by map - shows map clustering is minimal
- Center: Points colored by game version - CS2 and CSGO overlap significantly
- Right: Points colored by game+map combination

### 3. Side Comparison (`side_comparison.png`)
Paired bar chart comparing CT vs T mean values for top 25 features. Notable differences in `damage_per_round`, `saves_per_round_loss`, and `utility_damage_per_round`.

### 4. Feature Distributions (`feature_distributions.png`)
Density histograms comparing CS2 vs CSGO distributions for key features: kills_per_round, damage_per_round, rating_3.0, opening_kills_per_round, utility_damage_per_round, sniper_kills_per_round.

## Files

| File | Description |
|------|-------------|
| `feature_invariance_analysis.py` | Main analysis script |
| `map_invariance_results.csv` | Detailed ANOVA results per feature |
| `version_invariance_results.csv` | Detailed Mann-Whitney results per feature |
| `side_invariance_results.csv` | Detailed paired t-test results per feature |
| `invariant_features_summary.txt` | Text summary of invariant feature lists |
| `invariance_summary.png` | Effect size comparison visualization |
| `pca_visualization.png` | PCA projections by grouping |
| `side_comparison.png` | CT vs T feature comparison |
| `feature_distributions.png` | CS2 vs CSGO distribution plots |

## Method Selection Rationale

### Why not just use p-values?

P-values alone are problematic because:
1. With large samples (n > 3000), even tiny differences become "statistically significant"
2. P-values don't indicate practical importance
3. They depend heavily on sample size

**Solution:** We use effect sizes (η², Cohen's d) which are scale-independent measures of practical significance.

### Why different tests for each analysis?

| Analysis | Groups | Data Structure | Appropriate Test |
|----------|--------|----------------|------------------|
| Maps | 8 groups | Independent | ANOVA |
| Versions | 2 groups | Independent | Mann-Whitney U |
| Sides | 2 groups | Paired (same player) | Paired t-test |

### Why non-parametric for version comparison?

Gaming statistics often have:
- Skewed distributions (many average players, few elite)
- Outliers (exceptional performances)
- Non-normal residuals

Mann-Whitney U makes no distributional assumptions, making it more robust for this data.

## Conclusions

1. **Most features are map and version invariant** - player skill largely transfers across contexts
2. **Side has the biggest impact** - T and CT require fundamentally different playstyles
3. **11 "universal" features** capture context-independent player ability
4. **Utility-related features** are most context-dependent (map and side specific)
5. **Opening duel statistics** are highly stable - individual skill in first fights is consistent

## Usage

```bash
python3 feature_invariance_analysis.py
```

Requirements: pandas, numpy, scipy, sklearn, matplotlib, seaborn

## Citation

Data source: HLTV.org player statistics
Analysis period: CS2 (2023-09-27 to 2025-12-31), CSGO (2012-08-21 to 2023-09-26)
