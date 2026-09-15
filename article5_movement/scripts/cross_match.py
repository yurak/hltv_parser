"""
Крок 6: міжматчева валідація — головний тест гіпотези.

Усі попередні оцінки точності робились із групуванням за раундами В МЕЖАХ
матчу. Це не доводить існування підпису: модель могла вивчити не гравця, а
контекст матчу (суперник, сервер, тактика на цей день). Справжня перевірка —
навчити на ОДНОМУ матчі й розпізнати гравця в ІНШОМУ.

Беруться лише гравці, що мають >=2 матчі. Схема: leave-one-match-out
(GroupKFold за match_id). Порівняння з випадковим рівнем 1/n_players і з
permutation-нулем (перемішані мітки гравців у межах матчу).

Додатково рахується деградація: точність усередині матчу проти точності між
матчами на тій самій підвибірці гравців — це і є розмір ефекту матчу.

Usage:
    /usr/bin/python3 article5_movement/scripts/cross_match.py \
        outputs/dataset_features.csv --events outputs/dataset_event_features.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from dataio import read_table
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
import analyze as A

RNG = 0


def _clf(kind: str):
    if kind == "rf":
        return make_pipeline(StandardScaler(), RandomForestClassifier(
            n_estimators=500, min_samples_leaf=2, random_state=RNG, n_jobs=-1))
    return make_pipeline(StandardScaler(),
                         LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"))


def cv_acc(X, y, groups, kind: str, by_match: bool) -> float:
    n = len(np.unique(groups))
    if n < 2:
        return np.nan
    cv = (GroupKFold(n_splits=n) if by_match else
          StratifiedGroupKFold(n_splits=min(5, n), shuffle=True, random_state=RNG))
    try:
        pred = cross_val_predict(_clf(kind), X, y, cv=cv, groups=groups, n_jobs=1)
    except ValueError:
        return np.nan
    return float(np.mean(pred == y))


def main(args) -> None:
    df = read_table(args.features)
    ecols: list[str] = []
    if args.events and Path(args.events).exists():
        ev = read_table(args.events)
        ecols = [c for c in ev.columns if c not in A.EVENT_KEYS]
        keys = [k for k in ("demo", "match_id", "player", "side", "round")
                if k in df.columns and k in ev.columns]
        df = df.merge(ev[keys + ecols], on=keys, how="left")
        for c in ecols:
            df[c] = df[c].fillna(0.0 if c.endswith(("_per_s", "_frac")) else df[c].median())
    df = df[df["secs_alive"] >= A.MIN_SECS].copy()
    if args.context != "all" and "context" in df.columns:
        df = df[df["context"] == args.context].copy()
    if "match_id" not in df.columns:
        df["match_id"] = df["demo"]
    grp = args.group
    if grp not in df.columns:
        raise SystemExit(f"немає колонки {grp} — перебудуй датасет: run.py dataset")
    if args.side != "both":
        df = df[df["side"] == args.side].copy()

    # лише гравці, яких видно в кількох матчах
    nm = df.groupby("player")[grp].nunique()
    multi = nm[nm >= 2].index.tolist()
    df = df[df["player"].isin(multi)].copy()
    if df.empty or len(multi) < 2:
        print("Немає гравців із >=2 матчами — міжматчева перевірка неможлива.")
        return

    feats = [c for c in A.MICRO + A.KEYDYN + A.HABIT + A.MACRO + ecols
             if c in df.columns and df[c].std(skipna=True) > 0]
    df[feats] = df[feats].apply(lambda s: s.fillna(s.median()))
    if args.z_by == "match":
        df[feats] = df.groupby("match_id")[feats].transform(
            lambda s: (s - s.mean()) / (s.std() + 1e-9))

    y = df["player"].to_numpy()
    chance = 1.0 / len(multi)
    print(f"сторона={args.side}  нормалізація={args.z_by}")
    print(f"гравців із >=2 значеннями {grp}: {len(multi)} ({', '.join(sorted(multi))})")
    print(f"спостережень: {len(df)}  {grp}: {df[grp].nunique()}  "
          f"випадковий рівень: {chance:.3f}\n")

    fams = {
        "all": feats,
        "keydyn": [c for c in A.KEYDYN if c in feats],
        "micro": [c for c in A.MICRO if c in feats],
        "habit": [c for c in A.HABIT if c in feats],
        "event": [c for c in ecols if c in feats],
        "macro": [c for c in A.MACRO if c in feats],
    }
    print(f"{'родина':<8} {'n ознак':>8} {'між ' + grp:>13} {'у межах матчу':>15} "
          f"{'деградація':>12}")
    rows = []
    for name, cols in fams.items():
        if not cols:
            continue
        X = df[cols].to_numpy()
        across = max(cv_acc(X, y, df[grp].to_numpy(), "rf", True),
                     cv_acc(X, y, df[grp].to_numpy(), "lda", True))
        within = max(cv_acc(X, y, df["round"].to_numpy(), "rf", False),
                     cv_acc(X, y, df["round"].to_numpy(), "lda", False))
        drop = within - across if np.isfinite(within) and np.isfinite(across) else np.nan
        rows.append({"family": name, "n_feat": len(cols), "across_match": across,
                     "within_match": within, "degradation": drop})
        print(f"{name:<8} {len(cols):>8} {across:>13.3f} {within:>15.3f} {drop:>12.3f}")

    # permutation-нуль для міжматчевої схеми
    X = df[feats].to_numpy()
    rs = np.random.default_rng(RNG)
    null = []
    for _ in range(args.perms):
        yp = df.groupby(grp)["player"].transform(
            lambda s: pd.Series(rs.permutation(s.values), index=s.index)).to_numpy()
        a = cv_acc(X, yp, df[grp].to_numpy(), "lda", True)
        if np.isfinite(a):
            null.append(a)
    if null:
        print(f"\npermutation-нуль (між матчами): середнє {np.mean(null):.3f}, "
              f"95-й перцентиль {np.percentile(null, 95):.3f}")

    out = Path(args.outdir) / f"cross_{grp}_{args.side}_{args.z_by}.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"збережено {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("features")
    ap.add_argument("--events", default=None)
    ap.add_argument("--side", default="both", choices=["T", "CT", "both"])
    ap.add_argument("--z-by", default="match", choices=["pooled", "match"], dest="z_by")
    ap.add_argument("--group", default="series_id",
                    choices=["series_id", "match_id", "map"],
                    help="що вважати 'іншим контекстом': інший матч або інша мапа")
    ap.add_argument("--context", default="tournament", choices=["tournament", "platform", "all"])
    ap.add_argument("--perms", type=int, default=20)
    ap.add_argument("--outdir", default="article5_movement/outputs")
    main(ap.parse_args())
