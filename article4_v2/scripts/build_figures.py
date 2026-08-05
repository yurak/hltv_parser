"""
build_figures.py — publication figures for the paper (journal №47).

Addresses the reviewer comments on figure/table informativeness:
  F1  PCA, TWO panels: full 26-feature space vs behavioural space WITHOUT identity
      (shows that the striking diagonal is driven by target-encoded identity leakage).
  F2  Feature-family separability: silhouette + Wilks' λ per family (replaces two tables
      with one chart); identity bar flagged as leakage-affected.
  F3  Permutation importance (re-rendered from T8_permutation_importance.csv).
  F4  Confounding effect (the headline result): fraud rate weekday vs weekend,
      full dataset vs high-velocity subset — the weekend effect vanishes under control.
  F5  Card-testing signature: fraud rate / lift of base → same-amount → composite,
      with coverage annotation.

Also writes T10_ablation_ci.csv — bootstrap 95% CIs of PR-AUC for key ablation configs,
so the single-split point estimates in Table 6 get a measure of spread.

Reproducible: reuses feature engineering from analyze.py. Reads data/raw/df.csv,
writes outputs/figures/*.png, outputs/tables/T10_*.csv, outputs/logs/figures_log.txt.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.preprocessing import StandardScaler

import analyze as az  # feature engineering, family taxonomy, split/encode

ROOT = Path(__file__).resolve().parent.parent
# Figure language: "uk" (default) for manuscript.md, "en" for manuscript_en.md.
# `python scripts/build_figures.py en` or FIG_LANG=en.
LANG = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FIG_LANG", "uk")).lower()
if LANG not in ("uk", "en"):
    raise SystemExit(f"unknown figure language: {LANG!r} (expected 'uk' or 'en')")
FIGS = ROOT / "outputs" / ("figures_en" if LANG == "en" else "figures")
TABLES = ROOT / "outputs" / "tables"
LOGS = ROOT / "outputs" / "logs"
for d in (FIGS, TABLES, LOGS):
    d.mkdir(parents=True, exist_ok=True)
_LOG = (LOGS / f"figures_log{'_en' if LANG == 'en' else ''}.txt").open("w", encoding="utf-8")

# English renderings of every in-figure string. Figure titles map to "" because the
# DOCX already carries a numbered caption under each figure — an in-image "Fig. N."
# would duplicate it (and waste vertical space against the 10–20 page limit).
_EN = {
    # F1
    "Повний простір (26 ознак)": "Full space (26 features)",
    "Поведінковий простір без ідентифікаційних (24)":
        "Behavioral space without identity features (24)",
    "Легітимні": "Legitimate",
    "Шахрайські (CBK)": "Fraudulent (CBK)",
    "Рис. 1. PCA-проєкція простору поведінкових ознак": "",
    # F2
    "Часові": "Temporal", "За сумою": "Amount",
    "Ідентиф.*": "Identity*", "Швидкісні": "Velocity",
    "Silhouette (CBK vs легітимні)": "Silhouette (CBK vs legitimate)",
    "(а) Геометрична відокремленість": "(a) Geometric separation",
    "Wilks' λ (менше = сильніше розділення)": "Wilks' λ (lower = stronger separation)",
    "(б) Значущість розділення (MANOVA)": "(b) Significance of separation (MANOVA)",
    "Рис. 2. Розділювальна сила за сімействами ознак": "",
    "* ідентифікаційне сімейство (target-encoded) завищене через витік мітки":
        "* the identity family (target-encoded) is inflated by label leakage",
    # F3
    "Δ PR-AUC при перестановці ознаки": "Δ PR-AUC under feature permutation",
    "Рис. 3. Важливість ознак (permutation importance)": "",
    # F4
    "Повний набір": "Full dataset", "Високошвидкісні": "High-velocity",
    "Будні": "Weekdays", "Вихідні": "Weekends",
    "Частка шахрайства, %": "Fraud rate, %",
    "Рис. 4. Ефект «вихідних» зникає під контролем швидкісного шаблону": "",
    "(значущий)": "(significant)", "(незначущий)": "(not significant)",
    # F5
    "Базова\nчастота": "Base\nrate",
    "≥2/год AND\nsame_amount_10min": "≥2/hour AND\nsame_amount_10min",
    "lift ×{lift}\nохоплює {cov}%\nусього фроду": "lift ×{lift}\ncovers {cov}%\nof all fraud",
    "Рис. 5. Підпис card-testing: частка шахрайства та покриття": "",
    # F6
    "count C\n(поведінкове)": "count C\n(behavioral)",
    "timedelta D\n(поведінкове)": "timedelta D\n(behavioral)",
    "Рис. 6. IEEE-CIS: розділювальна сила рідних сімейств ознак\n"
    "(поведінкові C/D домінують над amount/temporal)": "",
}


def tr(s: str) -> str:
    """Ukrainian source string → current figure language."""
    if LANG == "uk":
        return s
    if s not in _EN:
        raise KeyError(f"no English rendering for figure string: {s!r}")
    return _EN[s]


def title(fig_or_ax, text: str, **kw) -> None:
    """Set a figure/axes title, skipping it when the language drops it (see _EN)."""
    text = tr(text)
    if not text:
        return
    setter = getattr(fig_or_ax, "suptitle", None) or fig_or_ax.set_title
    setter(text, **kw)

FAM_COLORS = {"velocity": "#4c78a8", "identity": "#54a24b",
              "amount": "#f58518", "temporal": "#b279a2"}
BLUE, RED = "#4c78a8", "#e45756"


def log(msg: str) -> None:
    print(msg); _LOG.write(msg + "\n"); _LOG.flush()


def df_with_full_te() -> pd.DataFrame:
    """Engineered df with identity target-encodings fit on the whole set
    (descriptive only — mirrors analyze.main for the structural figures)."""
    df = az.load_and_engineer()
    prior = df["y"].mean()
    for col, k in [("BIN", 20.0), ("Amount", 10.0)]:
        agg = df.groupby(col)["y"].agg(["sum", "count"])
        enc = (agg["sum"] + k * prior) / (agg["count"] + k)
        feat = "bin_te" if col == "BIN" else "amount_te"
        df[feat] = df[col].map(enc.to_dict()).astype(float)
    return df


# ---------------------------------------------------------------------------
def fig1_pca_two_panel(df: pd.DataFrame) -> None:
    log("\n=== F1: PCA two-panel (full vs no-identity) ===")
    behavioural = az.TEMPORAL + az.VELOCITY + az.AMOUNT          # no identity
    panels = [("Повний простір (26 ознак)", az.ALL_FEATURES),
              ("Поведінковий простір без ідентифікаційних (24)", behavioural)]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    for ax, (panel, feats) in zip(axes, panels):
        Xs = StandardScaler().fit_transform(df[feats].astype(float).values)
        pca = PCA(n_components=2).fit(Xs)
        Z = pca.transform(Xs)
        evr = pca.explained_variance_ratio_
        y = df["y"].values
        ax.scatter(Z[y == 0, 0], Z[y == 0, 1], s=6, alpha=0.25,
                   c=BLUE, label=tr("Легітимні"), rasterized=True)
        ax.scatter(Z[y == 1, 0], Z[y == 1, 1], s=10, alpha=0.80,
                   c=RED, label=tr("Шахрайські (CBK)"), rasterized=True)
        ax.set_xlabel(f"PC1 ({evr[0]*100:.1f}%)")
        ax.set_ylabel(f"PC2 ({evr[1]*100:.1f}%)")
        ax.set_title(tr(panel), fontsize=11)
        log(f"  {panel}: PC1={evr[0]*100:.1f}%, PC2={evr[1]*100:.1f}%, "
            f"cum2={(evr[0]+evr[1])*100:.1f}%")
    axes[0].legend(loc="upper right", frameon=False, fontsize=9)
    title(fig, "Рис. 1. PCA-проєкція простору поведінкових ознак", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96) if LANG == "uk" else None)
    fig.savefig(FIGS / "F1_pca_scatter.png", dpi=160)
    plt.close(fig)
    log("[saved] F1_pca_scatter.png")


def fig2_family_separability() -> None:
    log("\n=== F2: family separability (silhouette + Wilks λ) ===")
    sil = pd.read_csv(TABLES / "T5_silhouette.csv").set_index("family")
    man = pd.read_csv(TABLES / "T4_manova.csv").set_index("family")
    order = ["temporal", "amount", "identity", "velocity"]
    labels = {"temporal": tr("Часові"), "amount": tr("За сумою"),
              "identity": tr("Ідентиф.*"), "velocity": tr("Швидкісні")}
    colors = [FAM_COLORS[f] for f in order]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.8))

    s = [sil.loc[f, "silhouette"] for f in order]
    a1.bar([labels[f] for f in order], s, color=colors)
    for i, v in enumerate(s):
        a1.text(i, v + 0.02, f"{v:+.2f}", ha="center", fontsize=9)
    a1.set_ylabel(tr("Silhouette (CBK vs легітимні)"))
    a1.set_title(tr("(а) Геометрична відокремленість"), fontsize=11)
    a1.axhline(0, color="k", lw=0.5)

    w = [man.loc[f, "wilks_lambda"] for f in order]
    a2.bar([labels[f] for f in order], w, color=colors)
    for i, v in enumerate(w):
        a2.text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)
    a2.set_ylabel(tr("Wilks' λ (менше = сильніше розділення)"))
    a2.set_title(tr("(б) Значущість розділення (MANOVA)"), fontsize=11)
    a2.set_ylim(0, 1.05)

    title(fig, "Рис. 2. Розділювальна сила за сімействами ознак", fontsize=12)
    fig.text(0.5, 0.005,
             tr("* ідентифікаційне сімейство (target-encoded) завищене через витік мітки"),
             ha="center", fontsize=8, style="italic")
    fig.tight_layout(rect=(0, 0.04, 1, 0.95) if LANG == "uk" else (0, 0.04, 1, 1))
    fig.savefig(FIGS / "F2_family_separability.png", dpi=160)
    plt.close(fig)
    log("[saved] F2_family_separability.png")


def fig3_permutation_importance() -> None:
    log("\n=== F3: permutation importance (from T8) ===")
    t = pd.read_csv(TABLES / "T8_permutation_importance.csv")
    # keep the 12 features with the largest |ΔPR-AUC| — the tail is flat at ~0 and only
    # costs page height; the full ranking stays in T8_permutation_importance.csv
    t = (t.reindex(t["delta_pr_auc_mean"].abs().sort_values(ascending=False).index)
          .head(12)
          .sort_values("delta_pr_auc_mean").reset_index(drop=True))
    log(f"  plotting top {len(t)} features by |Δ PR-AUC| (full ranking in T8)")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.barh(t["feature"], t["delta_pr_auc_mean"], xerr=t["delta_pr_auc_std"],
            color=[FAM_COLORS[f] for f in t["family"]])
    ax.axvline(0, color="k", lw=0.5)
    ax.set_xlabel(tr("Δ PR-AUC при перестановці ознаки"))
    title(ax, "Рис. 3. Важливість ознак (permutation importance)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c, label=n)
               for n, c in FAM_COLORS.items()]
    ax.legend(handles=handles, loc="lower right", frameon=False)
    fig.tight_layout()
    fig.savefig(FIGS / "F3_permutation_importance.png", dpi=160)
    plt.close(fig)
    log("[saved] F3_permutation_importance.png")


def fig4_confounding(df: pd.DataFrame) -> None:
    log("\n=== F4: confounding (weekend effect under velocity control) ===")
    def rates(sub):
        wd = sub.loc[sub["weekend"] == 0, "y"].mean() * 100
        we = sub.loc[sub["weekend"] == 1, "y"].mean() * 100
        chi, p, *_ = chi2_contingency(pd.crosstab(sub["weekend"], sub["y"]))
        return wd, we, chi, p

    full = df
    high_v = df[df["n_tx_card_24h"] >= 2]
    wd_f, we_f, chi_f, p_f = rates(full)
    wd_h, we_h, chi_h, p_h = rates(high_v)
    log(f"  full:         weekday {wd_f:.2f}% weekend {we_f:.2f}% "
        f"χ²={chi_f:.2f} p={p_f:.2e}")
    log(f"  high-velocity weekday {wd_h:.2f}% weekend {we_h:.2f}% "
        f"χ²={chi_h:.2f} p={p_h:.2e} (n={len(high_v)})")

    groups = [tr("Повний набір"), f"{tr('Високошвидкісні')}\n(n_tx_24h≥2, n={len(high_v)})"]
    weekday = [wd_f, wd_h]; weekend = [we_f, we_h]
    x = np.arange(len(groups)); w = 0.36
    fig, ax = plt.subplots(figsize=(7.2, 5))
    ax.bar(x - w/2, weekday, w, label=tr("Будні"), color=BLUE)
    ax.bar(x + w/2, weekend, w, label=tr("Вихідні"), color=RED)
    for i in range(len(groups)):
        ax.text(x[i]-w/2, weekday[i]+0.5, f"{weekday[i]:.1f}%", ha="center", fontsize=9)
        ax.text(x[i]+w/2, weekend[i]+0.5, f"{weekend[i]:.1f}%", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(groups)
    ax.set_ylabel(tr("Частка шахрайства, %"))
    title(ax, "Рис. 4. Ефект «вихідних» зникає під контролем швидкісного шаблону")
    ax.legend(frameon=False)
    # annotations sit above the value labels (which are at +0.5) with enough
    # headroom that the two-line χ² note cannot overlap the bar percentages
    ax.annotate(f"χ²={chi_f:.1f}, p<0.001\n{tr('(значущий)')}",
                (0, max(weekday[0], weekend[0])+3.0), ha="center", va="bottom",
                fontsize=8.5)
    ax.annotate(f"χ²={chi_h:.2f}, p={p_h:.2f}\n{tr('(незначущий)')}",
                (1, max(weekday[1], weekend[1])+3.0), ha="center", va="bottom",
                fontsize=8.5)
    ax.set_ylim(0, max(weekend)+12)
    fig.tight_layout()
    fig.savefig(FIGS / "F4_confounding.png", dpi=160)
    plt.close(fig)
    log("[saved] F4_confounding.png")


def fig5_card_testing(df: pd.DataFrame) -> None:
    log("\n=== F5: card-testing signature ===")
    base = df["y"].mean() * 100
    m_same = df["same_amount_10min"] == 1
    m_comp = (df["n_tx_card_1h"] >= 2) & m_same
    r_same = df.loc[m_same, "y"].mean() * 100
    r_comp = df.loc[m_comp, "y"].mean() * 100
    cov = df.loc[m_comp, "y"].sum() / df["y"].sum() * 100
    n_comp = int(m_comp.sum())
    log(f"  base {base:.2f}% | same_amt_10min {r_same:.1f}% (n={int(m_same.sum())}) | "
        f"composite {r_comp:.1f}% (n={n_comp}, coverage {cov:.1f}%)")

    labels = [tr("Базова\nчастота"),
              "same_amount\n_10min",
              tr("≥2/год AND\nsame_amount_10min")]
    vals = [base, r_same, r_comp]
    colors = ["#bab0ac", "#f58518", RED]
    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(labels, vals, color=colors)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+1.5, f"{v:.1f}%", ha="center", fontsize=10)
    ax.text(2, r_comp/2,
            tr("lift ×{lift}\nохоплює {cov}%\nусього фроду").format(
                lift=f"{r_comp/base:.0f}", cov=f"{cov:.0f}"),
            ha="center", va="center", color="white", fontsize=9, weight="bold")
    ax.set_ylabel(tr("Частка шахрайства, %"))
    title(ax, "Рис. 5. Підпис card-testing: частка шахрайства та покриття")
    ax.set_ylim(0, 100)
    fig.tight_layout()
    fig.savefig(FIGS / "F5_card_testing.png", dpi=160)
    plt.close(fig)
    log("[saved] F5_card_testing.png")


def fig6_external_validation() -> None:
    """IEEE-CIS, NATIVE behavioral families: a behavioral family (count C) again
    tops separability, while amount/temporal stay weak — the thesis holds on a
    second real dataset. Skipped if the native exploration output is absent."""
    ext = ROOT / "outputs_ieeecis_native" / "tables" / "family_separability.csv"
    if not ext.exists():
        log("\n=== F6: skipped (outputs_ieeecis_native/.../family_separability.csv not found) ===")
        return
    log("\n=== F6: IEEE-CIS native behavioral families ===")
    t = pd.read_csv(ext)
    short = {"count C (зв'язки картка/адреса)": tr("count C\n(поведінкове)"),
             "timedelta D (інтервали подій)": tr("timedelta D\n(поведінкове)"),
             "amount (структура суми)": "amount",
             "temporal (час доби/тижня)": "temporal"}
    t["lbl"] = t["family"].map(short).fillna(t["family"])
    t = t.sort_values("silhouette", ascending=False)
    beh = t["family"].str.startswith(("count", "timedelta"))
    colors = [BLUE if b else "#bab0ac" for b in beh]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    bars = ax.bar(t["lbl"], t["silhouette"], color=colors)
    for b, v, f in zip(bars, t["silhouette"], t["mean_anova_F"]):
        ax.text(b.get_x()+b.get_width()/2, v+0.008,
                f"sil={v:.2f}\nF̄={f:.0f}", ha="center", fontsize=8.5)
    ax.set_ylabel(tr("Silhouette (CBK vs легітимні)"))
    title(ax, "Рис. 6. IEEE-CIS: розділювальна сила рідних сімейств ознак\n"
              "(поведінкові C/D домінують над amount/temporal)")
    ax.set_ylim(0, max(t["silhouette"])*1.25)
    fig.tight_layout()
    fig.savefig(FIGS / "F6_external_validation.png", dpi=160)
    plt.close(fig)
    log("[saved] F6_external_validation.png")


def ablation_bootstrap_ci(n_boot: int = 1000) -> None:
    log("\n=== T10: bootstrap 95% CI of PR-AUC (key ablation configs, LR) ===")
    train, test = az.split_and_encode(az.load_and_engineer())
    yte = test["y"].values
    configs = {
        "all": az.ALL_FEATURES,
        "only_velocity": az.VELOCITY,
        "without_velocity": [f for f in az.ALL_FEATURES if f not in az.VELOCITY],
        "only_temporal": az.TEMPORAL,
        "only_identity": az.IDENTITY,
    }
    rng = np.random.default_rng(az.RANDOM_STATE)
    n = len(yte)
    boot_idx = [rng.integers(0, n, n) for _ in range(n_boot)]
    rows = []
    for name, feats in configs.items():
        sc = StandardScaler()
        Xtr = sc.fit_transform(train[feats].astype(float).values)
        Xte = sc.transform(test[feats].astype(float).values)
        lr = LogisticRegression(max_iter=2000, class_weight="balanced",
                                random_state=az.RANDOM_STATE).fit(Xtr, train["y"].values)
        score = lr.predict_proba(Xte)[:, 1]
        point = average_precision_score(yte, score)
        boots = []
        for idx in boot_idx:
            if yte[idx].sum() == 0:
                continue
            boots.append(average_precision_score(yte[idx], score[idx]))
        lo, hi = np.percentile(boots, [2.5, 97.5])
        rows.append({"config": name, "pr_auc": round(point, 3),
                     "ci_low": round(lo, 3), "ci_high": round(hi, 3)})
        log(f"  {name:<18s} PR-AUC = {point:.3f}  95% CI [{lo:.3f}, {hi:.3f}]")
    pd.DataFrame(rows).to_csv(TABLES / "T10_ablation_ci.csv", index=False)
    log("[saved] T10_ablation_ci.csv")


def main() -> None:
    df = df_with_full_te()
    fig1_pca_two_panel(df)
    fig2_family_separability()
    fig3_permutation_importance()
    fig4_confounding(df)
    fig5_card_testing(df)
    fig6_external_validation()
    if LANG == "uk":          # tables are language-independent — build them once
        ablation_bootstrap_ci()
    # remove the stale single-panel permutation figure (now F3)
    old = FIGS / "F2_permutation_importance.png"
    if old.exists():
        old.unlink()
        log(f"[removed stale] {old.name}")
    log("\n=== FIGURES DONE ===")
    _LOG.close()


if __name__ == "__main__":
    main()
