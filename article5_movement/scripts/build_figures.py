#!/usr/bin/env python3
"""Прогін -> рисунки статті (outputs/paper/figures/*.png).

Жодного рисунка руками. Після перезбирання датасету:

    /usr/bin/python3 scripts/build_figures.py --run-id <новий прогін>

F7 (open-set DIR@FAR) не будується, поки немає протоколу P3.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paperlib as P
import analyze as A

plt.rcParams.update({"figure.dpi": 160, "font.size": 9,
                     "axes.grid": True, "grid.alpha": 0.25,
                     "axes.spines.top": False, "axes.spines.right": False})
KEYS = {"demo", "player", "steamid", "side", "round", "secs_alive", "series_id",
        "map", "context", "date", "match_id", "series_source", "tickrate"}


def _feat_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns
            if c not in KEYS and pd.api.types.is_numeric_dtype(df[c])
            and df[c].std(skipna=True) > 0]


def f1_pca(run_id: str, figs: Path, nums: dict) -> str | None:
    """Чи видно гравців як згустки в просторі ознак."""
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    d = P.features(run_id)
    if d is None:
        return None
    cols = _feat_cols(d)
    X = StandardScaler().fit_transform(d[cols].fillna(d[cols].median()))
    pca = PCA(n_components=2, random_state=0)
    Z = pca.fit_transform(X)
    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    players = d["player"].value_counts().index.tolist()
    cmap = plt.get_cmap("tab20")
    for k, pl in enumerate(players):
        m = (d["player"] == pl).to_numpy()
        ax.scatter(Z[m, 0], Z[m, 1], s=7, alpha=0.55, color=cmap(k % 20), label=pl,
                   linewidths=0)
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% дисперсії)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
    ax.set_title("Простір ознак моторики: спостереження за гравцями")
    ax.legend(fontsize=6, ncol=2, loc="best", framealpha=0.85)
    fig.tight_layout(); fig.savefig(figs / "F1_pca_scatter.png"); plt.close(fig)
    nums["f1_pca_var2d"] = round(float(pca.explained_variance_ratio_[:2].sum()), 4)
    return "F1_pca_scatter.png"


def f2_distributions(run_id: str, figs: Path, nums: dict) -> str | None:
    """Головний рисунок верифікації: перекриття genuine і impostor."""
    gi = P.genuine_impostor(run_id)
    if gi is None:
        return None
    g, i = gi
    eer, thr = P.eer_from(g, i)
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    bins = np.linspace(0, max(g.max(), i.max()), 60)
    ax.hist(i, bins=bins, density=True, alpha=0.55, label=f"impostor (n={i.size})")
    ax.hist(g, bins=bins, density=True, alpha=0.75, label=f"genuine (n={g.size})")
    ax.axvline(thr, color="k", ls="--", lw=1.2,
               label=f"поріг EER = {thr:.3f}  (EER = {eer:.3f})")
    ax.set_xlabel("відстань між профілями")
    ax.set_ylabel("щільність")
    ax.set_title("Розподіли відстаней: свої проти чужих")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(figs / "F2_genuine_impostor.png"); plt.close(fig)
    return "F2_genuine_impostor.png"


def f3_roc_det(run_id: str, figs: Path, nums: dict) -> str | None:
    from sklearn.metrics import roc_curve, roc_auc_score
    gi = P.genuine_impostor(run_id)
    if gi is None:
        return None
    g, i = gi
    y = np.r_[np.ones(g.size), np.zeros(i.size)]
    s = np.r_[-g, -i]
    fpr, tpr, _ = roc_curve(y, s)
    auc = roc_auc_score(y, s)
    eer, _ = P.eer_from(g, i)
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    axes[0].plot(fpr, tpr, lw=1.6)
    axes[0].plot([0, 1], [0, 1], ls=":", color="gray", lw=1)
    axes[0].set_xlabel("FAR"); axes[0].set_ylabel("1 − FRR")
    axes[0].set_title(f"ROC (AUC = {auc:.3f})")
    axes[1].plot(fpr, 1 - tpr, lw=1.6)
    axes[1].plot([eer], [eer], "o", ms=5, color="k")
    axes[1].annotate(f"EER = {eer:.3f}", (eer, eer), textcoords="offset points",
                     xytext=(8, 8), fontsize=8)
    axes[1].set_xscale("log"); axes[1].set_yscale("log")
    axes[1].set_xlabel("FAR"); axes[1].set_ylabel("FRR")
    axes[1].set_title("DET")
    fig.tight_layout(); fig.savefig(figs / "F3_roc_det.png"); plt.close(fig)
    nums["f3_auc"] = round(float(auc), 4)
    return "F3_roc_det.png"


def f4_cmc(run_id: str, figs: Path, nums: dict) -> str | None:
    """CMC: closed-set не лише за rank-1. Спліт групується за серією —
    той самий матч ніколи не потрапляє і в навчання, і в тест."""
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    d = P.features(run_id)
    if d is None or "series_id" not in d.columns:
        return None
    cols = _feat_cols(d)
    X = d[cols].fillna(d[cols].median()).to_numpy()
    y = d["player"].to_numpy()
    groups = d["series_id"].astype(str).to_numpy()
    n_splits = min(5, len(np.unique(groups)))
    ranks = []
    for tr, te in GroupKFold(n_splits=n_splits).split(X, y, groups):
        m = make_pipeline(StandardScaler(),
                          LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"))
        m.fit(X[tr], y[tr])
        proba = m.predict_proba(X[te])
        classes = list(m.classes_)
        for row, true in zip(proba, y[te]):
            if true not in classes:
                continue
            order = np.argsort(row)[::-1]
            ranks.append(int(np.where(order == classes.index(true))[0][0]) + 1)
    if not ranks:
        return None
    ranks = np.array(ranks)
    n_cls = len(np.unique(y))
    ks = np.arange(1, n_cls + 1)
    cmc = [(ranks <= k).mean() for k in ks]
    fig, ax = plt.subplots(figsize=(5.4, 3.8))
    ax.plot(ks, cmc, marker="o", ms=3.5, lw=1.5)
    ax.axhline(1 / n_cls, ls=":", color="gray", lw=1, label=f"випадково (1/{n_cls})")
    ax.set_xlabel("ранг k"); ax.set_ylabel("частка правильних у топ-k")
    ax.set_ylim(0, 1.02)
    ax.set_title(f"CMC-крива, {n_cls} гравців")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(figs / "F4_cmc.png"); plt.close(fig)
    nums.update({"f4_rank1": round(float(cmc[0]), 4),
                 "f4_rank5": round(float(cmc[min(4, n_cls - 1)]), 4),
                 "f4_n_classes": int(n_cls)})
    return "F4_cmc.png"


def f5_probe(run_id: str, figs: Path, nums: dict) -> str | None:
    lc = P.read_csv(run_id, "learning_curve_both.csv")
    if lc is None:
        return None
    fig, ax = plt.subplots(figsize=(5.4, 3.8))
    ax.errorbar(lc["rounds"], lc["acc_mean"], yerr=lc.get("acc_sd"),
                marker="o", ms=3.5, lw=1.5, capsize=2)
    ax.set_xlabel("раундів у профілі"); ax.set_ylabel("точність")
    ax.set_title("Скільки раундів треба, щоб упізнати")
    fig.tight_layout(); fig.savefig(figs / "F5_probe_length.png"); plt.close(fig)
    return "F5_probe_length.png"


def f6_families(run_id: str, figs: Path, nums: dict) -> str | None:
    """Внесок родин ознак — рисунок під головну тезу статті."""
    d = P.read_csv(run_id, "cross_series_id_both_match.csv")
    if d is None:
        return None
    d = d[d.family != "all"].copy()
    d["ua"] = d["family"].map(lambda f: P.FAMILY_UA.get(f, f))
    d = d.sort_values("across_match")
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    ax.barh(d["ua"], d["across_match"], color="#4878a8")
    for y_, v, n in zip(range(len(d)), d["across_match"], d["n_feat"]):
        ax.text(v + 0.008, y_, f"{v:.3f}  ({n} озн.)", va="center", fontsize=7.5)
    ax.set_xlabel("точність між серіями")
    ax.set_xlim(0, max(d["across_match"]) * 1.30)
    ax.set_title("Що саме ідентифікує: внесок родин ознак")
    fig.tight_layout(); fig.savefig(figs / "F6_families.png"); plt.close(fig)
    return "F6_families.png"


def f8_degradation(run_id: str, figs: Path, nums: dict) -> str | None:
    d = P.read_csv(run_id, "cross_series_id_both_match.csv")
    if d is None:
        return None
    d = d.copy()
    d["ua"] = d["family"].map(lambda f: P.FAMILY_UA.get(f, f))
    x = np.arange(len(d)); w = 0.38
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    ax.bar(x - w/2, d["within_match"], w, label="усередині серії")
    ax.bar(x + w/2, d["across_match"], w, label="між серіями")
    ax.set_xticks(x); ax.set_xticklabels(d["ua"], rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("точність")
    ax.set_title("Чи переживає підпис зміну матчу")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(figs / "F8_degradation.png"); plt.close(fig)
    return "F8_degradation.png"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    a = ap.parse_args()
    _, figs, logs = P.out_dirs()
    P.manifest(a.run_id)
    nums: dict = {}
    made, skipped = [], []
    for fn in (f1_pca, f2_distributions, f3_roc_det, f4_cmc, f5_probe,
               f6_families, f8_degradation):
        try:
            name = fn(a.run_id, figs, nums)
        except Exception as e:                      # рисунок не має валити збірку
            name, e_ = None, f"{fn.__name__}: {type(e).__name__}: {e}"
            skipped.append(e_)
            continue
        (made if name else skipped).append(name or f"{fn.__name__}: немає даних")
    skipped.append("F7_open_set (протоколу P3 ще немає)")
    P.save_numbers(nums)
    log = [f"прогін: {a.run_id}", f"рисунків зібрано: {len(made)}"]
    log += [f"  + {x}" for x in made] + [f"  - пропущено: {x}" for x in skipped]
    text = "\n".join(log)
    (logs / "build_figures.log").write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
