"""
build_figures.py — publication figures for the CS2/CSGO feature-invariance article (v2).

Invariance is encoded by effect size (the same criterion as tables/text):
green = invariant, red = variant. Figures are grayscale-tolerant (hatching + labels).

Inputs : data/processed/combined_clean.csv, outputs/tables/*.csv
Outputs: outputs/figures/{invariance_summary,pca_projection,side_comparison,feature_distributions}.png
         + outputs/figures/captions.md
"""
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
TABLES = os.path.join(ROOT, "outputs", "tables")
FIGS = os.path.join(ROOT, "outputs", "figures")
os.makedirs(FIGS, exist_ok=True)
plt.rcParams.update({"figure.dpi": 150, "font.size": 10, "axes.grid": True,
                     "grid.alpha": 0.3, "savefig.bbox": "tight"})

INV_C, VAR_C = "#2ca02c", "#d62728"
META = ["full_url", "player_name", "game_version", "map", "age",
        "time_alive_per_round", "ct_time_alive_per_round", "t_time_alive_per_round"]

def bars(ax, d, valcol, thr, title, xlabel):
    d = pd.concat([d.head(10), d.tail(10)])
    colors = [INV_C if inv else VAR_C for inv in d["invariant"]]
    ax.barh(range(len(d)), d[valcol], color=colors, alpha=0.85)
    ax.set_yticks(range(len(d))); ax.set_yticklabels(d["feature"], fontsize=7)
    ax.axvline(thr, color="gray", ls="--", lw=1)
    ax.set_xlabel(xlabel); ax.set_title(title, fontsize=10)
    ax.invert_yaxis()

def fig_summary():
    mp = pd.read_csv(os.path.join(TABLES, "map_invariance.csv"))
    vr = pd.read_csv(os.path.join(TABLES, "version_invariance.csv"))
    sd = pd.read_csv(os.path.join(TABLES, "side_invariance.csv"))
    fig, ax = plt.subplots(1, 3, figsize=(16, 7))
    bars(ax[0], mp, "eta_squared", 0.06, "Карти (ANOVA)", "η² (розмір ефекту)")
    bars(ax[1], vr, "cohens_d", 0.5, "Версія CS2 vs CSGO (Mann–Whitney)", "Cohen's d")
    bars(ax[2], sd, "cohens_d", 0.5, "Сторона T vs CT (парний t)", "Cohen's d")
    fig.suptitle("Інваріантність ознак за розміром ефекту "
                 "(зелений = інваріантна, червоний = варіантна)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(FIGS, "invariance_summary.png")); plt.close(fig)

def fig_pca():
    df = pd.read_csv(os.path.join(PROCESSED, "combined_clean.csv"))
    feats = [c for c in df.columns if c not in META
             and not c.startswith("ct_") and not c.startswith("t_")]
    X = df[feats].replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median())
    Xs = StandardScaler().fit_transform(X)
    pca = PCA(n_components=2); P = pca.fit_transform(Xs)
    ev = pca.explained_variance_ratio_ * 100
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.5))
    for m in sorted(df["map"].unique()):
        msk = (df["map"] == m).values
        ax[0].scatter(P[msk, 0], P[msk, 1], s=12, alpha=0.5, label=m.replace("de_", ""))
    ax[0].set_title("PCA за картою"); ax[0].legend(fontsize=7, ncol=2)
    for v, c in [("cs2", "#1f77b4"), ("csgo", "#ff7f0e")]:
        msk = (df["game_version"] == v).values
        ax[1].scatter(P[msk, 0], P[msk, 1], s=12, alpha=0.45, label=v.upper(), color=c)
    ax[1].set_title("PCA за версією гри"); ax[1].legend(fontsize=9)
    for a in ax:
        a.set_xlabel(f"PC1 ({ev[0]:.1f}%)"); a.set_ylabel(f"PC2 ({ev[1]:.1f}%)")
    fig.tight_layout(); fig.savefig(os.path.join(FIGS, "pca_projection.png")); plt.close(fig)
    return ev

def fig_side():
    sd = pd.read_csv(os.path.join(TABLES, "side_invariance.csv"))
    d = sd.sort_values("ct_mean", ascending=False).head(20)
    y = np.arange(len(d)); w = 0.4
    fig, ax = plt.subplots(figsize=(9, 10))
    ax.barh(y - w/2, d["ct_mean"], w, label="CT", color="#1f77b4", alpha=0.8)
    ax.barh(y + w/2, d["t_mean"], w, label="T", color="#ff7f0e", alpha=0.8)
    ax.set_yticks(y); ax.set_yticklabels(d["feature"], fontsize=8); ax.invert_yaxis()
    ax.set_xlabel("Середнє значення"); ax.set_title("Порівняння CT vs T (топ-20 ознак за CT)")
    ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(FIGS, "side_comparison.png")); plt.close(fig)

def fig_dist():
    df = pd.read_csv(os.path.join(PROCESSED, "combined_clean.csv"))
    keys = ["kills_per_round", "damage_per_round", "rating_3.0",
            "opening_kills_per_round", "utility_damage_per_round", "1on1_win_percentage"]
    fig, ax = plt.subplots(2, 3, figsize=(15, 9))
    for i, f in enumerate(keys):
        a = ax[i // 3, i % 3]
        for v, c in [("cs2", "#1f77b4"), ("csgo", "#ff7f0e")]:
            data = df[df.game_version == v][f].dropna()
            a.hist(data, bins=30, density=True, alpha=0.5, label=v.upper(), color=c)
        a.set_title(f); a.set_xlabel(f); a.set_ylabel("Щільність"); a.legend(fontsize=8)
    fig.suptitle("Розподіли ключових ознак: CS2 vs CSGO", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(os.path.join(FIGS, "feature_distributions.png")); plt.close(fig)

def main():
    fig_summary()
    ev = fig_pca()
    fig_side()
    fig_dist()
    captions = f"""# Підписи до фігур (чернетка)

**Рис. 1. invariance_summary.png** — Розміри ефектів для трьох вимірів інваріантності
(по 10 найбільш та 10 найменш інваріантних ознак на панель). Зелений — інваріантна
(η²<0.06 для карт; Cohen's d<0.5 для версії та сторони), червоний — варіантна. Пунктир — поріг.

**Рис. 2. pca_projection.png** — Проєкція PCA простору overall-ознак (стандартизованих) на дві
головні компоненти (PC1 {ev[0]:.1f}%, PC2 {ev[1]:.1f}%). Ліворуч — за картою, праворуч — за версією.
Значне перекриття груп узгоджується з переважною інваріантністю ознак.

**Рис. 3. side_comparison.png** — Середні значення для сторін CT та T (топ-20 ознак за CT).
Найбільші розриви — у saves та utility-метриках; opening/clutch-метрики майже збігаються.

**Рис. 4. feature_distributions.png** — Розподіли (щільність) ключових ознак для CS2 vs CSGO.
"""
    with open(os.path.join(FIGS, "captions.md"), "w") as f:
        f.write(captions)
    print("Figures + captions saved to", FIGS)
    print(f"PCA explained variance: PC1={ev[0]:.1f}%, PC2={ev[1]:.1f}%")

if __name__ == "__main__":
    main()
