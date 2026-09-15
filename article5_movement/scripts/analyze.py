"""
Крок 3: аналіз розділимості гравців у просторі ознак руху.

Що робить:
  1. ICC(1) — компоненти дисперсії: скільки варіації ознаки припадає на
     відмінності МІЖ гравцями, а скільки на розкид раунд-до-раунду ВСЕРЕДИНІ
     гравця. Це головний критерій "чи ознака взагалі несе підпис гравця".
  2. Kruskal-Wallis + eta^2 з поправкою BH-FDR — які ознаки значуще
     відрізняються між гравцями.
  3. PCA + silhouette — геометрична розділимість у 2D.
  4. Ідентифікація гравця (RandomForest / LDA) з StratifiedGroupKFold за
     раундами; порівняння з випадковим рівнем та permutation-тестом.
  5. Попарне порівняння: стандартизована відстань між центроїдами,
     Mahalanobis, і CV-AUC бінарного класифікатора для кожної пари.
  6. Крива навчання за кількістю раундів -> емпіричне обґрунтування обсягу
     вибірки (скільки демок потрібно).

Usage:
    /usr/bin/python3 article5_movement/scripts/analyze.py <features.csv> [--side T|CT|both]
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from dataio import read_table
from scipy import stats
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.decomposition import PCA
from joblib import Parallel, delayed
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score, silhouette_score
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

MICRO = [
    "speed_mean", "speed_std", "speed_p90", "frac_still", "frac_walkkey",
    "frac_slowmove", "frac_run", "accel_std", "counterstrafe_per_s",
    "strafe_switch_per_s", "fwd_switch_per_s", "diag_frac", "key_entropy",
    "jump_per_s", "frac_air", "duck_per_s", "frac_ducked", "crouchwalk_frac",
    "yaw_rate_mean", "yaw_rate_p95", "flick_per_s", "lat_reversal_per_s",
    "lat_speed_frac", "frac_scoped", "moving_shot_frac", "shots_per_s",
]
MACRO = [
    "path_len", "path_per_s", "path_efficiency", "radius_gyration",
    "max_dist_start", "disp_10s", "disp_20s", "z_range",
]
KEYDYN = [
    "dwell_W_ms", "dwell_S_ms", "dwell_A_ms", "dwell_D_ms", "dwell_SHIFT_ms",
    "dwell_CTRL_ms", "dwell_SPACE_ms",
    "presses_W_per_s", "presses_S_per_s", "presses_A_per_s", "presses_D_per_s",
    "presses_SHIFT_per_s", "presses_CTRL_per_s", "presses_SPACE_per_s",
    "presses_total_per_s", "strafe_flight_ms", "strafe_overlap_frac",
    "combo_none", "combo_W", "combo_S", "combo_A", "combo_D", "combo_WA",
    "combo_WD", "combo_SA", "combo_SD", "combo_AD",
    "combo_persistence", "combo_trans_entropy", "combo_switch_per_s",
]
HABIT = [
    "wpn_knife_frac", "wpn_pistol_frac", "wpn_primary_frac", "wpn_sniper_frac",
    "wpn_nade_frac", "knife_run_frac", "nade_walk_frac", "switch_per_s",
    "qswitch_per_s", "reload_per_s", "reload_ammo_ratio",
    "silencer_toggle_per_s", "zoom_toggle_per_s", "sniper_zoom_frac",
]
MIN_SECS = 10.0
RNG = 0


def icc1(df: pd.DataFrame, feat: str, group: str = "player") -> float:
    """ICC(1) = sigma^2_between / (sigma^2_between + sigma^2_within), one-way ANOVA."""
    groups = [g[feat].dropna().to_numpy() for _, g in df.groupby(group)]
    groups = [g for g in groups if len(g) > 1]
    if len(groups) < 2:
        return np.nan
    k = len(groups)
    n = np.mean([len(g) for g in groups])
    grand = np.concatenate(groups).mean()
    ms_b = sum(len(g) * (g.mean() - grand) ** 2 for g in groups) / (k - 1)
    ms_w = sum(((g - g.mean()) ** 2).sum() for g in groups) / (sum(len(g) for g in groups) - k)
    if ms_w <= 0:
        return np.nan
    val = (ms_b - ms_w) / (ms_b + (n - 1) * ms_w)
    return float(np.clip(val, 0, 1))


def eta_squared_kw(df: pd.DataFrame, feat: str, group: str = "player") -> tuple[float, float]:
    groups = [g[feat].dropna().to_numpy() for _, g in df.groupby(group)]
    groups = [g for g in groups if len(g) > 1]
    if len(groups) < 2 or np.ptp(np.concatenate(groups)) == 0:
        return np.nan, np.nan
    h, p = stats.kruskal(*groups)
    n = sum(len(g) for g in groups)
    k = len(groups)
    eta2 = (h - k + 1) / (n - k)                 # eta^2_H
    return float(max(eta2, 0)), float(p)


def bh_fdr(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    ok = ~np.isnan(p)
    q = np.full_like(p, np.nan)
    pv = p[ok]
    m = pv.size
    order = np.argsort(pv)
    ranked = pv[order] * m / (np.arange(m) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.clip(ranked, 0, 1)
    q[ok] = out
    return q


def cv_identify(X, y, groups, model="rf", inner_jobs=-1):
    """Ідентифікація з групуванням за переданою одиницею.

    Одиниця групування визначає, що саме міряється. За раундом — «чи різняться
    гравці в межах тих самих матчів» (описова величина, навчання й перевірка
    ділять матч). За серією — власне ідентифікація: перевірка на сесії, якої
    не було в навчанні. Пайплайн типово групує за серією, щоб усі числа
    означали те саме; `--group-by round` лишено для звірки з прогонами до
    вересня 2026.
    """
    n_splits = min(5, len(np.unique(groups)), int(pd.Series(y).value_counts().min()))
    if n_splits < 2:
        return np.nan, None
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=RNG)
    clf = (make_pipeline(StandardScaler(), RandomForestClassifier(
                n_estimators=500, min_samples_leaf=2, random_state=RNG,
                n_jobs=inner_jobs))
           if model == "rf" else
           make_pipeline(StandardScaler(), LinearDiscriminantAnalysis(solver="lsqr",
                                                                     shrinkage="auto")))
    try:
        pred = cross_val_predict(clf, X, y, cv=cv, groups=groups, n_jobs=1)
    except ValueError:
        return np.nan, None
    return float(np.mean(pred == y)), pred


def pair_auc(df: pd.DataFrame, feats: list[str], a: str, b: str,
             gcol: str = "round") -> float:
    sub = df[df["player"].isin([a, b])]
    X = sub[feats].to_numpy()
    y = (sub["player"] == a).astype(int).to_numpy()
    groups = sub[gcol].to_numpy()
    n_splits = min(5, len(np.unique(groups)), int(pd.Series(y).value_counts().min()))
    if n_splits < 2:
        return np.nan
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=RNG)
    clf = make_pipeline(StandardScaler(), LinearDiscriminantAnalysis(solver="lsqr",
                                                                    shrinkage="auto"))
    try:
        prob = cross_val_predict(clf, X, y, cv=cv, groups=groups,
                                 method="predict_proba")[:, 1]
    except ValueError:
        return np.nan
    return float(roc_auc_score(y, prob))


# Усе, що НЕ є ознакою події. Список жорсткий, тому будь-яка нова метаколонка
# в шарі подій інакше поїхала б у модель як предиктор — саме так і сталося,
# коли датасет отримав колонки реєстру.
EVENT_KEYS = {"demo", "demo_id", "player", "steamid", "side", "round", "secs_alive",
              "match_id", "series_id", "series_source", "map", "context", "server",
              "date", "tournament", "team1", "team2", "format", "tickrate"}


def run(feat_csv: str, side: str, outdir: Path, events_csv: str | None = None,
        group_by: str = "series_id") -> dict:
    df = read_table(feat_csv)
    event_cols: list[str] = []
    if events_csv and Path(events_csv).exists():
        ev = read_table(events_csv)
        event_cols = [c for c in ev.columns if c not in EVENT_KEYS]
        keys = [k for k in ("demo", "match_id", "player", "side", "round")
                if k in df.columns and k in ev.columns]
        df = df.merge(ev[keys + event_cols], on=keys, how="left")
        for c in event_cols:
            if c.endswith(("_per_s", "_frac")):
                df[c] = df[c].fillna(0.0)                 # подій не було = нульова частота
            else:
                df[c] = df[c].fillna(df[c].median())      # метрика невизначена
    df = df[df["secs_alive"] >= MIN_SECS].copy()
    if side != "both":
        df = df[df["side"] == side].copy()
    feats_all = [c for c in MICRO + MACRO + KEYDYN + HABIT + event_cols if c in df.columns]
    feats_all = [c for c in feats_all if df[c].notna().any() and df[c].std(skipna=True) > 0]
    df[feats_all] = df[feats_all].apply(lambda s: s.fillna(s.median()))
    # z-нормалізація в межах сторони, щоб T/CT різниця не маскувала гравця
    if side == "both":
        df[feats_all] = df.groupby("side")[feats_all].transform(
            lambda s: (s - s.mean()) / (s.std() + 1e-9))

    report: dict = {"side": side, "n_obs": len(df),
                    "n_players": df["player"].nunique(),
                    "obs_per_player": df["player"].value_counts().to_dict()}

    # --- 1-2. ICC + Kruskal-Wallis ---
    rows = []
    for f in feats_all:
        e2, p = eta_squared_kw(df, f)
        rows.append({"feature": f,
                     "family": ("micro" if f in MICRO else "keydyn" if f in KEYDYN
                                else "habit" if f in HABIT
                                else "macro" if f in MACRO else "event"),
                     "icc1": icc1(df, f), "eta2_H": e2, "p_kw": p,
                     "mean": df[f].mean(), "sd": df[f].std()})
    stat = pd.DataFrame(rows)
    stat["q_bh"] = bh_fdr(stat["p_kw"].to_numpy())
    stat = stat.sort_values("icc1", ascending=False)
    stat.to_csv(outdir / f"feature_stats_{side}.csv", index=False)

    # --- 3. PCA + silhouette ---
    X = StandardScaler().fit_transform(df[feats_all].to_numpy())
    y = df["player"].to_numpy()
    pcs = PCA(n_components=min(10, X.shape[1])).fit(X)
    Z = pcs.transform(X)
    report["pca_var_2d"] = float(pcs.explained_variance_ratio_[:2].sum())
    report["silhouette_full"] = float(silhouette_score(X, y))
    report["silhouette_pca2"] = float(silhouette_score(Z[:, :2], y))

    # --- 4. ідентифікація ---
    gcol = group_by if group_by in df.columns else "round"
    if gcol != group_by:
        print(f"УВАГА: колонки {group_by} немає — групую за round")
    groups = df[gcol].to_numpy()
    report["group_by"] = gcol
    report["n_groups"] = int(df[gcol].nunique())
    for tag, cols in (("all", feats_all),
                      ("micro", [c for c in MICRO if c in df.columns]),
                      ("keydyn", [c for c in KEYDYN if c in df.columns]),
                      ("habit", [c for c in HABIT if c in df.columns]),
                      ("event", [c for c in event_cols if c in df.columns]),
                      ("macro", [c for c in MACRO if c in df.columns])):
        if not cols:
            continue
        acc, _ = cv_identify(df[cols].to_numpy(), y, groups, "rf")
        report[f"acc_rf_{tag}"] = acc
        acc_l, _ = cv_identify(df[cols].to_numpy(), y, groups, "lda")
        report[f"acc_lda_{tag}"] = acc_l
    report["chance"] = 1.0 / df["player"].nunique()

    # permutation-тест значущості точності
    rs = np.random.default_rng(RNG)
    perms = [rs.permutation(y) for _ in range(30)]
    accs = Parallel(n_jobs=-1, prefer="processes")(
        delayed(lambda yp: cv_identify(X, yp, groups, "lda")[0])(yp) for yp in perms)
    report["acc_lda_all_permnull_mean"] = float(np.nanmean(accs))
    report["acc_lda_all_permnull_p95"] = float(np.nanpercentile(accs, 95))

    # важливість ознак
    clf = make_pipeline(StandardScaler(), RandomForestClassifier(
        n_estimators=500, min_samples_leaf=2, random_state=RNG, n_jobs=-1)).fit(X, y)
    # Підгонка забирає всі ядра, а ось далі — ні: permutation_importance сам
    # розкидає повтори по воркерах, і якщо ліс усередині кожного знову проситиме
    # всі 12 ядер, вони конкуруватимуть між собою. Саме через це joblib і
    # скаржився на зупинених воркерів, а завантаження не піднімалось вище ~465%.
    clf[-1].set_params(n_jobs=1)
    imp = permutation_importance(clf, X, y, n_repeats=20, random_state=RNG, n_jobs=-1)
    pd.DataFrame({"feature": feats_all, "perm_importance": imp.importances_mean,
                  "sd": imp.importances_std}).sort_values(
        "perm_importance", ascending=False).to_csv(
        outdir / f"perm_importance_{side}.csv", index=False)

    # --- 5. попарні відстані + AUC ---
    Xz = pd.DataFrame(X, columns=feats_all, index=df.index)
    Xz["player"] = y
    cent = Xz.groupby("player")[feats_all].mean()
    cov = np.cov(X.T) + np.eye(len(feats_all)) * 1e-6
    inv = np.linalg.pinv(cov)
    combos = list(itertools.combinations(sorted(cent.index), 2))
    # Пари незалежні між собою, тож цикл розкидається по ядрах. Послідовно це
    # N*(N-1)/2 крос-валідацій одна за одною: 496 пар на 32 гравцях, 4 950 на
    # ста — крок, який і робить аналіз годинним.
    print(f"попарний крок: {len(combos)} пар, групування за {gcol}")
    aucs = Parallel(n_jobs=-1, prefer="processes")(
        delayed(pair_auc)(df[["player", gcol] + feats_all], feats_all, a, b, gcol)
        for a, b in combos)
    pairs = []
    for (a, b), auc_ab in zip(combos, aucs):
        d = cent.loc[a].to_numpy() - cent.loc[b].to_numpy()
        pairs.append({"a": a, "b": b,
                      "euclid_z": float(np.linalg.norm(d)),
                      "euclid_z_norm": float(np.linalg.norm(d) / np.sqrt(len(feats_all))),
                      "mahalanobis": float(np.sqrt(d @ inv @ d)),
                      "cv_auc": auc_ab})
    pdf = pd.DataFrame(pairs).sort_values("euclid_z")
    pdf.to_csv(outdir / f"pairwise_{side}.csv", index=False)
    report["pair_dist_median"] = float(pdf["euclid_z"].median())
    report["pair_dist_min"] = float(pdf["euclid_z"].min())
    report["pair_dist_max"] = float(pdf["euclid_z"].max())
    report["pair_auc_median"] = float(pdf["cv_auc"].median())

    # внутрішньогравцевий розкид проти міжгравцевого
    intra = float(np.mean([np.linalg.norm(Xz.loc[i, feats_all].to_numpy()
                                          - cent.loc[Xz.loc[i, "player"]].to_numpy())
                           for i in Xz.index]))
    report["intra_player_spread"] = intra
    report["separability_ratio"] = report["pair_dist_median"] / intra

    # --- 6. крива навчання за кількістю раундів ---
    curve = []
    rounds_all = np.sort(df["round"].unique())
    for k in range(3, len(rounds_all) + 1, 2):
        accs_k = []
        for rep in range(8):
            r = np.random.default_rng(RNG + rep).choice(rounds_all, size=k, replace=False)
            sub = df[df["round"].isin(r)]
            if sub["player"].value_counts().min() < 2:
                continue
            a, _ = cv_identify(sub[feats_all].to_numpy(), sub["player"].to_numpy(),
                               sub[gcol].to_numpy(), "lda")
            if not np.isnan(a):
                accs_k.append(a)
        if accs_k:
            curve.append({"rounds": k, "obs": k * df["player"].nunique(),
                          "acc_mean": float(np.mean(accs_k)),
                          "acc_sd": float(np.std(accs_k))})
    pd.DataFrame(curve).to_csv(outdir / f"learning_curve_{side}.csv", index=False)

    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("features")
    ap.add_argument("--side", default="both", choices=["T", "CT", "both"])
    ap.add_argument("--events", default=None, help="CSV з event_features")
    ap.add_argument("--outdir", default="article5_movement/outputs")
    ap.add_argument("--group-by", default="series_id",
                    choices=["series_id", "match_id", "round"], dest="group_by",
                    help="одиниця групування сплітів (типово серія)")
    a = ap.parse_args()

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rep = run(a.features, a.side, outdir, a.events, a.group_by)
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    (outdir / f"report_{a.side}.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False))
