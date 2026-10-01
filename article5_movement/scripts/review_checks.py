#!/usr/bin/env python3
"""Перевірки, яких вимагала рецензія чорнетки v0.2 (29.09.2026).

Кожен блок відповідає на конкретне зауваження; числа лягають у теку прогону
(`review_checks.json` + CSV), звідки їх бере build_tables.py.

    A1  верифікація (EER/AUC/FAR) окремо для кожного каналу, зокрема для
        ознак керування пересуванням. Досі EER рахувався на 45 ознаках
        keydyn+event+micro+habit, тобто разом із бойовими.
    A4  особа чи команда: закрита множина всередині однієї команди, частка
        помилок на партнера по команді, EER окремо для пар партнерів.
    B1  канал керування пересуванням без контрстрейфу.
    B2  базова лінія: випадкові підмножини ознак того самого розміру (6 і 49).
    B10 верифікація за часовим проміжком між серіями.

Методологія класифікації — cross_match.cv_acc (групування за серією, z у
межах матчу), профілі — як у compare_profiles.py (ICC >= 0.10, >= 5 раундів
на блок, z у межах матчу, відстань = евклідова / sqrt(n)).

    /usr/bin/python3 scripts/review_checks.py --run-id 2026-09-27_mirage_n136_fix
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze as A
import paperlib as P
from ablate_channel import COMBAT_COUPLED
from compare_profiles import ICC_MIN, MIN_ROUNDS_PER_BLOCK
from cross_match import cv_acc

N_RANDOM = 200
COUNTERSTRAFE = ["counterstrafe_per_s"]
GAP_BUCKETS = [(0, 1), (1, 2), (2, 3), (3, 99)]   # місяці між серіями пари


def load(run_id: str) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Те саме завантаження, що в ablate_channel.py: сирі й z-нормовані ознаки."""
    run = P.run_dir(run_id)
    df = P.features(run_id)
    ecols: list[str] = []
    ev_hits = sorted(run.glob("event_features_*.parquet"))
    if ev_hits:
        ev = pd.read_parquet(ev_hits[0])
        ecols = [c for c in ev.columns if c not in A.EVENT_KEYS]
        keys = [k for k in ("demo", "player", "side", "round")
                if k in df.columns and k in ev.columns]
        df = df.merge(ev[keys + ecols], on=keys, how="left")
        for c in ecols:
            df[c] = df[c].fillna(0.0 if c.endswith(("_per_s", "_frac")) else df[c].median())
    df = df[df["secs_alive"] >= A.MIN_SECS].copy()
    if "match_id" not in df.columns:
        df["match_id"] = df["demo"]
    nm = df.groupby("player")["series_id"].nunique()
    df = df[df["player"].isin(nm[nm >= 2].index)].copy()
    feats = [c for c in A.MICRO + A.KEYDYN + A.HABIT + A.MACRO + ecols
             if c in df.columns and df[c].std(skipna=True) > 0]
    df[feats] = df[feats].apply(lambda s: s.fillna(s.median()))
    return df, feats, [c for c in ecols if c in feats]


def channels(feats: list[str], ecols: list[str]) -> dict[str, list[str]]:
    keydyn = [c for c in A.KEYDYN if c in feats]
    micro = [c for c in A.MICRO if c in feats]
    combat = [c for c in COMBAT_COUPLED if c in feats]
    micro_clean = [c for c in micro if c not in combat]
    habit = [c for c in A.HABIT if c in feats]
    loco = keydyn + micro_clean
    return {
        "all": feats,
        "verif_default": keydyn + ecols + micro + habit,   # як у compare_profiles
        "loco": loco,
        "loco_no_cs": [c for c in loco if c not in COUNTERSTRAFE],
        "keydyn": keydyn,
        "micro_clean": micro_clean,
        "combat": combat,
    }


# ---------------------------------------------------------------- верифікація

def profiles(raw: pd.DataFrame, cols: list[str]) -> tuple[pd.DataFrame, list[str]]:
    icc = {c: A.icc1(raw, c) for c in cols}
    use = [c for c in cols if np.isfinite(icc[c]) and icc[c] >= ICC_MIN]
    z = raw.copy()
    z[use] = z.groupby("match_id")[use].transform(lambda s: (s - s.mean()) / (s.std() + 1e-9))
    agg = z.groupby(["player", "side", "series_id"])
    prof = agg[use].mean()
    prof["n_rounds"] = agg.size()
    prof["date"] = pd.to_datetime(agg["date"].min())
    prof = prof[prof["n_rounds"] >= MIN_ROUNDS_PER_BLOCK].reset_index()
    return prof, use


def pairs(prof: pd.DataFrame, use: list[str], team: dict[str, str]) -> pd.DataFrame:
    X = prof[use].to_numpy(float)
    pl, sd, bl = (prof[k].to_numpy() for k in ("player", "side", "series_id"))
    dt = prof["date"].to_numpy()
    i, j = np.triu_indices(len(prof), 1)
    keep = (sd[i] == sd[j]) & ~((pl[i] == pl[j]) & (bl[i] == bl[j]))
    i, j = i[keep], j[keep]
    d = np.linalg.norm(X[i] - X[j], axis=1) / np.sqrt(len(use))
    tm = np.array([team.get(p, "?") for p in pl])
    gap = np.abs((dt[i] - dt[j]).astype("timedelta64[D]").astype(float)) / 30.44
    return pd.DataFrame({"a": pl[i], "b": pl[j], "dist": d,
                         "genuine": pl[i] == pl[j],
                         "teammate": (pl[i] != pl[j]) & (tm[i] == tm[j]) & (tm[i] != "?"),
                         "gap_months": gap})


def verif_metrics(g: np.ndarray, i: np.ndarray, boot: bool = True) -> dict:
    e, thr = P.eer_from(g, i)
    y = np.r_[np.ones(g.size), np.zeros(i.size)]
    out = {"n_genuine": int(g.size), "n_impostor": int(i.size),
           "eer": round(e, 4), "auc": round(float(roc_auc_score(y, np.r_[-g, -i])), 4),
           "dprime": round(float((i.mean() - g.mean()) / np.sqrt((g.var() + i.var()) / 2)), 3),
           "far_at_frr01": round(P.far_at_frr(g, i, 0.01), 4),
           "far_at_frr10": round(P.far_at_frr(g, i, 0.10), 4)}
    if boot:
        lo, hi = P.bootstrap_eer(g, i)
        out["eer_ci"] = [round(lo, 4), round(hi, 4)]
    return out


# ---------------------------------------------------------------- класифікація

def lda_acc(Z: pd.DataFrame, cols: list[str]) -> float:
    return cv_acc(Z[cols].to_numpy(), Z["player"].to_numpy(),
                  Z["series_id"].to_numpy(), "lda", True)


def best_acc(Z: pd.DataFrame, cols: list[str]) -> float:
    """Як в ablate_channel.py: краще з RF і LDA."""
    X, y, g = Z[cols].to_numpy(), Z["player"].to_numpy(), Z["series_id"].to_numpy()
    return max(cv_acc(X, y, g, "rf", True), cv_acc(X, y, g, "lda", True))


def teammate_errors(Z: pd.DataFrame, cols: list[str], team: dict[str, str]) -> dict:
    """Куди йдуть помилки: на партнера по команді чи на чужого."""
    X, y, g = Z[cols].to_numpy(), Z["player"].to_numpy(), Z["series_id"].to_numpy()
    clf = make_pipeline(StandardScaler(),
                        LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"))
    pred = cross_val_predict(clf, X, y, cv=GroupKFold(n_splits=len(np.unique(g))), groups=g)
    wrong = pred != y
    to_mate = np.array([team.get(a) == team.get(b) for a, b in zip(y, pred)])[wrong]
    players = sorted(set(y))
    # очікувана частка, якби помилка падала на будь-кого з решти рівноймовірно
    exp = np.mean([(sum(team.get(q) == team.get(p) for q in players) - 1) / (len(players) - 1)
                   for p in y[wrong]])
    return {"n_errors": int(wrong.sum()), "to_teammate": round(float(to_mate.mean()), 4),
            "expected_if_random": round(float(exp), 4)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--n-random", type=int, default=N_RANDOM)
    a = ap.parse_args()
    run = P.run_dir(a.run_id)

    raw, feats, ecols = load(a.run_id)
    coh = P.cohort(a.run_id)
    team = dict(zip(coh["nick_canonical"], coh["team"]))
    ch = channels(feats, ecols)
    Z = raw.copy()
    Z[feats] = Z.groupby("match_id")[feats].transform(lambda s: (s - s.mean()) / (s.std() + 1e-9))
    players = sorted(Z["player"].unique())
    res: dict = {"run_id": a.run_id, "n_players": len(players),
                 "n_obs": int(len(Z)), "n_series": int(Z["series_id"].nunique()),
                 "chance": round(1 / len(players), 4),
                 "n_features": {k: len(v) for k, v in ch.items()}}
    print(f"{a.run_id}: гравців {len(players)}, спостережень {len(Z)}, "
          f"серій {res['n_series']}, ознак {len(feats)}")

    # A1 + B1 + A4(верифікація) + B10 -------------------------------------
    print("\n[A1] верифікація за каналами")
    ver, gap_rows = {}, []
    for name in ("verif_default", "all", "loco", "loco_no_cs", "keydyn", "combat"):
        prof, use = profiles(raw, ch[name])
        pr = pairs(prof, use, team)
        g, i = pr.loc[pr.genuine, "dist"].to_numpy(), pr.loc[~pr.genuine, "dist"].to_numpy()
        m = verif_metrics(g, i)
        m["n_features_icc"] = len(use)
        m["n_profiles"] = int(len(prof))
        imt = pr.loc[pr.teammate, "dist"].to_numpy()
        iot = pr.loc[~pr.genuine & ~pr.teammate, "dist"].to_numpy()
        m["vs_teammates"] = verif_metrics(g, imt, boot=False)
        m["vs_other_teams"] = verif_metrics(g, iot, boot=False)
        ver[name] = m
        print(f"  {name:<14} ознак {len(use):>3}  EER {m['eer']:.4f} {m['eer_ci']}  "
              f"AUC {m['auc']:.4f}  FAR@FRR1% {m['far_at_frr01']:.3f}  "
              f"| партнери EER {m['vs_teammates']['eer']:.4f}, "
              f"інші {m['vs_other_teams']['eer']:.4f}")
        if name in ("verif_default", "loco"):
            for lo, hi in GAP_BUCKETS:
                gb = pr.loc[pr.genuine & (pr.gap_months >= lo) & (pr.gap_months < hi), "dist"]
                if len(gb) < 10:
                    continue
                mm = verif_metrics(gb.to_numpy(), i, boot=False)
                gap_rows.append({"канал": name, "проміжок_міс": f"{lo}–{hi}" if hi < 99 else f"≥{lo}",
                                 "genuine_пар": mm["n_genuine"], "EER": mm["eer"], "AUC": mm["auc"],
                                 "genuine_середня_відстань": round(float(gb.mean()), 4)})
    res["verification"] = ver
    gap = pd.DataFrame(gap_rows)
    gap.to_csv(run / "review_time_gap.csv", index=False)
    print("\n[B10] за часовим проміжком\n" + gap.to_string(index=False))

    # A4 закрита множина всередині команди --------------------------------
    print("\n[A4] всередині команди (між серіями)")
    within = []
    for t, n in coh[coh["nick_canonical"].isin(players)]["team"].value_counts().items():
        if n < 3:
            continue
        sub = Z[Z["player"].map(team) == t]
        for name in ("all", "loco"):
            acc = best_acc(sub, ch[name])
            within.append({"команда": t, "гравців": int(n), "канал": name,
                           "між серіями": round(acc, 4), "випадковий рівень": round(1 / n, 4)})
            print(f"  {t:<14} n={n} {name:<5} {acc:.4f} (випадково {1/n:.3f})")
    res["within_team"] = within
    pd.DataFrame(within).to_csv(run / "review_within_team.csv", index=False)
    res["teammate_errors"] = {k: teammate_errors(Z, ch[k], team) for k in ("all", "loco")}
    print(f"  помилки на партнера: {res['teammate_errors']}")

    # B1 канали класифікації ----------------------------------------------
    print("\n[B1] класифікація без контрстрейфу")
    res["closed_set"] = {k: round(best_acc(Z, ch[k]), 4) for k in ("loco", "loco_no_cs")}
    print(f"  {res['closed_set']}")

    # B2 випадкові підмножини ----------------------------------------------
    print(f"\n[B2] випадкові підмножини, {a.n_random} на розмір (LDA)")
    rng = np.random.default_rng(0)
    rand_rows, base = [], {}
    for name in ("combat", "loco"):
        k = len(ch[name])
        real = lda_acc(Z, ch[name])
        accs = np.array([lda_acc(Z, list(rng.choice(feats, k, replace=False)))
                         for _ in range(a.n_random)])
        base[name] = {"k": k, "real_lda": round(real, 4),
                      "random_mean": round(float(accs.mean()), 4),
                      "random_p05": round(float(np.percentile(accs, 5)), 4),
                      "random_p95": round(float(np.percentile(accs, 95)), 4),
                      "percentile_of_real": round(float((accs < real).mean() * 100), 1)}
        rand_rows += [{"канал": name, "k": k, "acc": x} for x in accs]
        print(f"  {name:<6} k={k:>2}: реальний {real:.4f} | випадкові "
              f"{accs.mean():.4f} [{base[name]['random_p05']:.4f}; {base[name]['random_p95']:.4f}] "
              f"-> перцентиль {base[name]['percentile_of_real']}")
    res["random_subsets"] = base
    pd.DataFrame(rand_rows).to_csv(run / "review_random_subsets.csv", index=False)

    out = run / "review_checks.json"
    out.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float))
    print(f"\n-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
