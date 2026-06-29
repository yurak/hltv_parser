"""
Experiments for the paper
    "Ідентифікація поведінкових шаблонів користувачів фінансових онлайн-сервісів
     на основі інженерії ознак та аналізу сепарабельності у просторі ознак"
    (Kuzhii & Furgala, LNU Electronics and Information Technologies, 2026)

Runs all quantitative experiments, writes reproducible numerical outputs to
  ./results/tables/*.csv   ./results/figures/*.png   ./results/log.txt

All claims in the paper trace back to artifacts produced here.
"""

from __future__ import annotations
import json
import os
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import f_oneway, mannwhitneyu, pearsonr, spearmanr
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, roc_auc_score,
                             silhouette_score)
from sklearn.preprocessing import StandardScaler
from statsmodels.multivariate.manova import MANOVA

warnings.filterwarnings("ignore", category=RuntimeWarning)

HERE = Path(__file__).parent
DATA = HERE / "df.csv"
OUT_DIR = HERE / "results"
OUT_DIR.mkdir(exist_ok=True)
(OUT_DIR / "tables").mkdir(exist_ok=True)
(OUT_DIR / "figures").mkdir(exist_ok=True)
LOG = (OUT_DIR / "log.txt").open("w", encoding="utf-8")

RANDOM_STATE = 42
TRAIN_FRAC = 0.75

# ---------------------------------------------------------------------------
# feature families (taxonomy — parallels CS2 paper)
# ---------------------------------------------------------------------------
TEMPORAL = ["hour_sin", "hour_cos", "dow_sin", "dow_cos",
            "weekend", "night", "afternoon_peak"]
VELOCITY = ["gap_min_prev", "cum_card_count",
            "n_tx_card_1h", "n_tx_card_6h", "n_tx_card_24h",
            "sum_amt_card_1h", "sum_amt_card_6h", "sum_amt_card_24h",
            "same_amt_prev", "same_amount_10min"]
AMOUNT   = ["amount_log", "amt_mod_10", "amt_mod_50",
            "amt_mod_100", "has_cents", "amount_gt_200", "amount_gt_500"]
IDENTITY = ["bin_te", "amount_te"]
FAMILIES = {"temporal": TEMPORAL, "velocity": VELOCITY,
            "amount": AMOUNT, "identity": IDENTITY}
ALL_FEATURES = TEMPORAL + VELOCITY + AMOUNT + IDENTITY


def log(msg: str) -> None:
    print(msg)
    LOG.write(msg + "\n")
    LOG.flush()


# ---------------------------------------------------------------------------
# 1. Load + feature engineering
# ---------------------------------------------------------------------------
def load_and_engineer() -> pd.DataFrame:
    df = pd.read_csv(DATA, index_col=0)
    df["Date"] = pd.to_datetime(df["Date"])
    df["y"] = (df["CBK"] == "Yes").astype(int)
    df["BIN"] = df["Card Number"].str[:6]
    df = df.sort_values("Date").reset_index(drop=True)

    # temporal
    h = df["Date"].dt.hour
    dow = df["Date"].dt.dayofweek
    df["hour"] = h
    df["dow"] = dow
    df["hour_sin"] = np.sin(2 * np.pi * h / 24)
    df["hour_cos"] = np.cos(2 * np.pi * h / 24)
    df["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    df["dow_cos"] = np.cos(2 * np.pi * dow / 7)
    df["weekend"] = (dow >= 5).astype(int)
    df["night"] = h.isin(range(0, 6)).astype(int)
    df["afternoon_peak"] = h.isin([15, 16]).astype(int)

    # amount
    df["amount_log"] = np.log1p(df["Amount"])
    df["amt_mod_10"] = (df["Amount"] % 10 == 0).astype(int)
    df["amt_mod_50"] = (df["Amount"] % 50 == 0).astype(int)
    df["amt_mod_100"] = (df["Amount"] % 100 == 0).astype(int)
    df["has_cents"] = (df["Amount"] % 1 != 0).astype(int)
    df["amount_gt_200"] = (df["Amount"] > 200).astype(int)
    df["amount_gt_500"] = (df["Amount"] > 500).astype(int)

    # velocity (strictly past)
    df = df.sort_values(["Card Number", "Date"]).reset_index(drop=True)
    prev_t = df.groupby("Card Number")["Date"].shift(1)
    df["gap_min_prev"] = (df["Date"] - prev_t).dt.total_seconds() / 60
    df["gap_min_prev"] = df["gap_min_prev"].fillna(14400)  # first tx → 10 days
    prev_amt = df.groupby("Card Number")["Amount"].shift(1)
    df["same_amt_prev"] = (df["Amount"] == prev_amt).astype(int)
    df["same_amount_10min"] = ((df["Amount"] == prev_amt) &
                               (df["gap_min_prev"] <= 10)).astype(int)

    df = df.set_index("Date")
    df["cum_card_count"] = df.groupby("Card Number").cumcount()
    for w in ("1h", "6h", "24h"):
        cnt = (df.groupby("Card Number")["Amount"]
                 .rolling(w).count().reset_index(level=0, drop=True) - 1)
        amt = (df.groupby("Card Number")["Amount"]
                 .rolling(w).sum().reset_index(level=0, drop=True)
               - df["Amount"])
        df[f"n_tx_card_{w}"] = cnt.clip(lower=0).fillna(0)
        df[f"sum_amt_card_{w}"] = amt.clip(lower=0).fillna(0)
    df = df.reset_index().sort_values("Date").reset_index(drop=True)
    return df


def add_target_encoding(train: pd.DataFrame, test: pd.DataFrame,
                        col: str, k: float) -> tuple[pd.Series, pd.Series]:
    prior = train["y"].mean()
    agg = train.groupby(col)["y"].agg(["sum", "count"])
    enc = (agg["sum"] + k * prior) / (agg["count"] + k)
    mapping = enc.to_dict()
    return (train[col].map(mapping).fillna(prior).astype(float),
            test[col].map(mapping).fillna(prior).astype(float))


# ---------------------------------------------------------------------------
# 2. Time-based split + target encoding (past-only)
# ---------------------------------------------------------------------------
def split_and_encode(df: pd.DataFrame):
    cutoff = int(len(df) * TRAIN_FRAC)
    train, test = df.iloc[:cutoff].copy(), df.iloc[cutoff:].copy()
    for col, k in [("BIN", 20.0), ("Amount", 10.0)]:
        te_train, te_test = add_target_encoding(train, test, col, k)
        feat = f"{col.lower()}_te" if col == "BIN" else "amount_te"
        train[feat] = te_train
        test[feat] = te_test
    return train, test


# ---------------------------------------------------------------------------
# 3. Descriptive statistics
# ---------------------------------------------------------------------------
def descriptive_stats(df: pd.DataFrame) -> None:
    log("\n=== 1. Descriptive statistics (full dataset) ===")
    n, n_fraud = len(df), int(df["y"].sum())
    log(f"N = {n}, fraud N = {n_fraud} ({n_fraud / n:.3%})")
    log(f"Date range: {df['Date'].min()} → {df['Date'].max()}")
    log(f"Unique cards: {df['Card Number'].nunique()}")
    log(f"Unique BINs: {df['BIN'].nunique()}")
    log(f"Amount: mean={df['Amount'].mean():.2f}, "
        f"median={df['Amount'].median():.2f}, "
        f"p95={df['Amount'].quantile(0.95):.2f}, "
        f"max={df['Amount'].max():.2f}")

    # group-wise stats per feature family
    rows = []
    for feat in ALL_FEATURES:
        a = df.loc[df["y"] == 0, feat].astype(float)
        b = df.loc[df["y"] == 1, feat].astype(float)
        if b.var() == 0 and a.var() == 0:
            continue
        t_f, t_p = f_oneway(a, b)
        try:
            u_stat, u_p = mannwhitneyu(a, b, alternative="two-sided")
        except ValueError:
            u_stat, u_p = np.nan, np.nan
        rows.append({
            "feature": feat,
            "family": next(k for k, v in FAMILIES.items() if feat in v),
            "mean_noncbk": a.mean(), "mean_cbk": b.mean(),
            "median_noncbk": a.median(), "median_cbk": b.median(),
            "anova_F": t_f, "anova_p": t_p,
            "mwu_U": u_stat, "mwu_p": u_p,
        })
    tbl = pd.DataFrame(rows).sort_values("anova_F", ascending=False)
    tbl.to_csv(OUT_DIR / "tables" / "T1_univariate_tests.csv", index=False)
    log(f"[saved] T1_univariate_tests.csv ({len(tbl)} features)")


# ---------------------------------------------------------------------------
# 4. PCA + visualisation
# ---------------------------------------------------------------------------
def pca_analysis(df: pd.DataFrame) -> None:
    log("\n=== 2. PCA on the full feature space ===")
    X = df[ALL_FEATURES].astype(float).values
    Xs = StandardScaler().fit_transform(X)
    pca = PCA(n_components=min(10, Xs.shape[1])).fit(Xs)
    evr = pca.explained_variance_ratio_
    cum = np.cumsum(evr)
    log("Explained variance ratio (top 10 PCs):")
    for i, (e, c) in enumerate(zip(evr, cum), 1):
        log(f"  PC{i}: {e:.4f}  (cum {c:.4f})")
    pd.DataFrame({"pc": np.arange(1, len(evr) + 1),
                  "explained_variance": evr,
                  "cumulative": cum}
                 ).to_csv(OUT_DIR / "tables" / "T2_pca_variance.csv",
                          index=False)

    # 2D projection
    Z = pca.transform(Xs)[:, :2]
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(Z[df["y"] == 0, 0], Z[df["y"] == 0, 1],
               s=6, alpha=0.30, c="#4c78a8", label="Легітимні", rasterized=True)
    ax.scatter(Z[df["y"] == 1, 0], Z[df["y"] == 1, 1],
               s=9, alpha=0.80, c="#e45756", label="Шахрайські (CBK)", rasterized=True)
    ax.set_xlabel(f"PC1 ({evr[0]*100:.1f}%)")
    ax.set_ylabel(f"PC2 ({evr[1]*100:.1f}%)")
    ax.set_title("Рис. 1. PCA-проєкція простору поведінкових ознак")
    ax.legend(loc="upper right", frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "figures" / "F1_pca_scatter.png", dpi=160)
    plt.close(fig)
    log("[saved] F1_pca_scatter.png")

    # loadings of PC1 / PC2
    loadings = pd.DataFrame(pca.components_[:2].T,
                            index=ALL_FEATURES,
                            columns=["PC1", "PC2"])
    loadings["abs_PC1"] = loadings["PC1"].abs()
    loadings.sort_values("abs_PC1", ascending=False, inplace=True)
    loadings.to_csv(OUT_DIR / "tables" / "T3_pca_loadings.csv")
    log("[saved] T3_pca_loadings.csv")


# ---------------------------------------------------------------------------
# 5. MANOVA — family-level + full space
# ---------------------------------------------------------------------------
def manova_analysis(df: pd.DataFrame) -> None:
    log("\n=== 3. MANOVA (group = CBK Yes/No) ===")
    rows = []
    for fam_name, feats in list(FAMILIES.items()) + [("all", ALL_FEATURES)]:
        sub = df[feats + ["y"]].copy()
        # keep only features with non-zero variance
        keep_cols = [c for c in feats if sub[c].var() > 0]
        sub = sub[keep_cols + ["y"]]
        formula = " + ".join([f"Q('{c}')" for c in keep_cols]) + " ~ y"
        try:
            m = MANOVA.from_formula(formula, data=sub)
            stats = m.mv_test().results["y"]["stat"]
            wilks = stats.loc["Wilks' lambda"]
            rows.append({
                "family": fam_name,
                "n_features": len(feats),
                "wilks_lambda": wilks["Value"],
                "F": wilks["F Value"],
                "num_df": wilks["Num DF"],
                "den_df": wilks["Den DF"],
                "p_value": wilks["Pr > F"],
            })
        except Exception as e:
            log(f"  MANOVA failed for '{fam_name}': {e}")
    tbl = pd.DataFrame(rows)
    tbl.to_csv(OUT_DIR / "tables" / "T4_manova.csv", index=False)
    for _, r in tbl.iterrows():
        log(f"  {r['family']:<10s}  Wilks λ = {r['wilks_lambda']:.4f}  "
            f"F = {r['F']:.2f}  p = {r['p_value']:.2e}")


# ---------------------------------------------------------------------------
# 6. Silhouette for two-group separability
# ---------------------------------------------------------------------------
def silhouette_analysis(df: pd.DataFrame) -> None:
    log("\n=== 4. Silhouette (group labels = CBK Yes/No) ===")
    rng = np.random.default_rng(RANDOM_STATE)
    idx = rng.choice(len(df), size=min(5000, len(df)), replace=False)
    rows = []
    for fam_name, feats in list(FAMILIES.items()) + [("all", ALL_FEATURES)]:
        X = StandardScaler().fit_transform(df[feats].astype(float).values)[idx]
        y = df["y"].values[idx]
        try:
            s = silhouette_score(X, y, metric="euclidean")
        except Exception:
            s = np.nan
        rows.append({"family": fam_name, "n_features": len(feats),
                     "silhouette": s})
    tbl = pd.DataFrame(rows)
    tbl.to_csv(OUT_DIR / "tables" / "T5_silhouette.csv", index=False)
    for _, r in tbl.iterrows():
        log(f"  {r['family']:<10s}  silhouette = {r['silhouette']:+.4f}")


# ---------------------------------------------------------------------------
# 7. Correlation between families
# ---------------------------------------------------------------------------
def correlation_analysis(df: pd.DataFrame) -> None:
    log("\n=== 5. Correlation matrix between feature families ===")
    fam_scores = {}
    for name, feats in FAMILIES.items():
        Xs = StandardScaler().fit_transform(df[feats].astype(float).values)
        # family score = 1st PC of standardized features (summary)
        if Xs.shape[1] >= 2:
            Xs = PCA(n_components=1).fit_transform(Xs).ravel()
        else:
            Xs = Xs.ravel()
        fam_scores[name] = Xs
    F = pd.DataFrame(fam_scores)
    corr = F.corr(method="pearson")
    corr.to_csv(OUT_DIR / "tables" / "T6_family_corr.csv")
    log(corr.round(3).to_string())


# ---------------------------------------------------------------------------
# 8. Ablation — classifier with/without each family
# ---------------------------------------------------------------------------
def ablation(train: pd.DataFrame, test: pd.DataFrame) -> None:
    log("\n=== 6. Ablation of feature families ===")
    rows = []
    configs = [("all", ALL_FEATURES)]
    for fam in FAMILIES:
        drop = FAMILIES[fam]
        keep = [f for f in ALL_FEATURES if f not in drop]
        configs.append((f"without_{fam}", keep))
    for fam, only in FAMILIES.items():
        configs.append((f"only_{fam}", only))

    for name, feats in configs:
        Xtr = train[feats].astype(float).values
        Xte = test[feats].astype(float).values
        ytr, yte = train["y"].values, test["y"].values

        # logistic regression (scaled)
        sc = StandardScaler()
        Xtr_s = sc.fit_transform(Xtr)
        Xte_s = sc.transform(Xte)
        lr = LogisticRegression(max_iter=2000, class_weight="balanced",
                                random_state=RANDOM_STATE).fit(Xtr_s, ytr)
        s_lr = lr.predict_proba(Xte_s)[:, 1]

        # hist gbm
        hgb = HistGradientBoostingClassifier(
            max_depth=6, learning_rate=0.05, max_iter=300,
            l2_regularization=1.0, class_weight="balanced",
            random_state=RANDOM_STATE).fit(Xtr, ytr)
        s_hgb = hgb.predict_proba(Xte)[:, 1]

        for m_name, score in [("LR", s_lr), ("HGB", s_hgb)]:
            roc = roc_auc_score(yte, score)
            ap = average_precision_score(yte, score)
            top1k = int(max(1, len(yte) * 0.01))
            top5k = int(max(1, len(yte) * 0.05))
            top1_prec = yte[np.argsort(-score)[:top1k]].mean()
            top5_rec = yte[np.argsort(-score)[:top5k]].sum() / yte.sum()
            rows.append({"config": name, "model": m_name,
                         "n_features": len(feats),
                         "roc_auc": roc, "pr_auc": ap,
                         "top1_precision": top1_prec,
                         "top5_recall": top5_rec})
    tbl = pd.DataFrame(rows)
    tbl.to_csv(OUT_DIR / "tables" / "T7_ablation.csv", index=False)
    log(tbl.round(3).to_string(index=False))


# ---------------------------------------------------------------------------
# 9. Permutation importance
# ---------------------------------------------------------------------------
def permutation_importance(train: pd.DataFrame, test: pd.DataFrame,
                           n_repeats: int = 5) -> None:
    log("\n=== 7. Permutation importance (HGB, PR-AUC drop) ===")
    Xtr = train[ALL_FEATURES].astype(float).values
    Xte = test[ALL_FEATURES].astype(float).values
    ytr, yte = train["y"].values, test["y"].values

    hgb = HistGradientBoostingClassifier(
        max_depth=6, learning_rate=0.05, max_iter=300,
        l2_regularization=1.0, class_weight="balanced",
        random_state=RANDOM_STATE).fit(Xtr, ytr)
    base = average_precision_score(yte, hgb.predict_proba(Xte)[:, 1])

    rng = np.random.default_rng(RANDOM_STATE)
    rows = []
    for j, name in enumerate(ALL_FEATURES):
        drops = []
        for _ in range(n_repeats):
            Xp = Xte.copy()
            Xp[:, j] = rng.permutation(Xp[:, j])
            ap = average_precision_score(yte, hgb.predict_proba(Xp)[:, 1])
            drops.append(base - ap)
        family = next(k for k, v in FAMILIES.items() if name in v)
        rows.append({"feature": name, "family": family,
                     "delta_pr_auc_mean": float(np.mean(drops)),
                     "delta_pr_auc_std": float(np.std(drops))})
    tbl = (pd.DataFrame(rows)
             .sort_values("delta_pr_auc_mean", ascending=False))
    tbl.to_csv(OUT_DIR / "tables" / "T8_permutation_importance.csv",
               index=False)
    log(tbl.round(4).to_string(index=False))

    # bar chart
    fig, ax = plt.subplots(figsize=(8, 7))
    fam_colors = {"velocity": "#4c78a8", "identity": "#54a24b",
                  "amount": "#f58518", "temporal": "#b279a2"}
    t = tbl.copy()
    t = t.iloc[::-1]
    ax.barh(t["feature"], t["delta_pr_auc_mean"],
            xerr=t["delta_pr_auc_std"],
            color=[fam_colors[f] for f in t["family"]])
    ax.axvline(0, color="k", lw=0.5)
    ax.set_xlabel("Δ PR-AUC при перестановці ознаки")
    ax.set_title("Рис. 2. Важливість ознак (permutation importance)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c, label=n)
               for n, c in fam_colors.items()]
    ax.legend(handles=handles, loc="lower right", frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "figures" / "F2_permutation_importance.png",
                dpi=160)
    plt.close(fig)
    log("[saved] F2_permutation_importance.png")


# ---------------------------------------------------------------------------
# 10. Residual analysis: are temporal features informative after controlling
#     for velocity?
# ---------------------------------------------------------------------------
def residual_analysis(train: pd.DataFrame, test: pd.DataFrame) -> None:
    log("\n=== 8. Residual analysis: temporal vs velocity ===")
    Xtr = train[VELOCITY].astype(float).values
    Xte = test[VELOCITY].astype(float).values
    ytr, yte = train["y"].values, test["y"].values
    sc = StandardScaler()
    Xtr_s = sc.fit_transform(Xtr)
    Xte_s = sc.transform(Xte)
    lr = LogisticRegression(max_iter=2000, class_weight="balanced",
                            random_state=RANDOM_STATE).fit(Xtr_s, ytr)
    logit_te = lr.decision_function(Xte_s)

    # residual y: y - sigmoid(logit_te)
    p = 1 / (1 + np.exp(-logit_te))
    resid = yte - p

    # partial correlation of each temporal feature with residual
    rows = []
    for feat in TEMPORAL:
        x = test[feat].astype(float).values
        if x.std() == 0:
            continue
        r_p, p_p = pearsonr(x, resid)
        r_s, p_s = spearmanr(x, resid)
        rows.append({"feature": feat,
                     "pearson_r_with_residual": r_p,
                     "pearson_p": p_p,
                     "spearman_r_with_residual": r_s,
                     "spearman_p": p_s})
    tbl = pd.DataFrame(rows).sort_values("pearson_r_with_residual",
                                         key=lambda s: s.abs(),
                                         ascending=False)
    tbl.to_csv(OUT_DIR / "tables" / "T9_residual_corr.csv", index=False)
    log(tbl.round(4).to_string(index=False))


# ---------------------------------------------------------------------------
# 11. Card-testing signature (qualitative, for Introduction / Discussion)
# ---------------------------------------------------------------------------
def card_testing_signature(df: pd.DataFrame) -> None:
    log("\n=== 9. Card-testing signature (joint counts) ===")
    quick_dup = (df["same_amount_10min"] == 1)
    n_quick = int(quick_dup.sum())
    n_fr_q = int(df.loc[quick_dup, "y"].sum())
    base = df["y"].mean()
    lift = (n_fr_q / n_quick) / base if n_quick > 0 else np.nan
    log(f"same_amount_10min=1 — n={n_quick}, fraud rate "
        f"{n_fr_q/n_quick:.3%}, lift over base = {lift:.2f}×")

    # joint: (n_tx_card_1h ≥ 2) AND (same_amount_10min = 1)
    mask = (df["n_tx_card_1h"] >= 2) & quick_dup
    n = int(mask.sum())
    n_f = int(df.loc[mask, "y"].sum())
    if n > 0:
        log(f"[n_tx_card_1h≥2 AND same_amount_10min=1] n={n}, "
            f"fraud rate {n_f/n:.3%}, lift {n_f/n/base:.2f}×, "
            f"catches {n_f/df['y'].sum():.1%} of all fraud.")

    # Chi-square for (weekend × fraud) before/after stratification on velocity burst
    from scipy.stats import chi2_contingency
    ct = pd.crosstab(df["weekend"], df["y"])
    chi, p, *_ = chi2_contingency(ct)
    log(f"weekend × fraud χ² = {chi:.2f}, p = {p:.2e}")
    # stratify: high-velocity only
    high_v = df[df["n_tx_card_24h"] >= 2]
    if len(high_v) > 0 and high_v["weekend"].nunique() == 2:
        ct2 = pd.crosstab(high_v["weekend"], high_v["y"])
        chi2, p2, *_ = chi2_contingency(ct2)
        log(f"  within high-velocity (n_tx_card_24h≥2): "
            f"χ² = {chi2:.2f}, p = {p2:.2e}, n = {len(high_v)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    log(f"Data: {DATA}")
    df = load_and_engineer()

    # For PCA/MANOVA/silhouette/descriptive we need the full df including
    # identity target-encodings. Acceptable here because we are describing
    # structure (hypothesis exploration), not claiming predictive leakage.
    # For the predictive ablation later we rebuild with TRAIN-only TE.
    prior_full = df["y"].mean()
    for col, k in [("BIN", 20.0), ("Amount", 10.0)]:
        agg = df.groupby(col)["y"].agg(["sum", "count"])
        enc = (agg["sum"] + k * prior_full) / (agg["count"] + k)
        feat = f"{col.lower()}_te" if col == "BIN" else "amount_te"
        df[feat] = df[col].map(enc.to_dict()).astype(float)

    descriptive_stats(df)
    pca_analysis(df)
    manova_analysis(df)
    silhouette_analysis(df)
    correlation_analysis(df)
    card_testing_signature(df)

    # predictive ablation needs train/test split with past-only TE
    train, test = split_and_encode(load_and_engineer())
    ablation(train, test)
    permutation_importance(train, test)
    residual_analysis(train, test)

    log("\n=== DONE ===")
    LOG.close()


if __name__ == "__main__":
    main()
