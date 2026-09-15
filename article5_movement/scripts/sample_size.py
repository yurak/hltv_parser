"""
Крок 4: обґрунтування обсягу вибірки (скільки раундів / демок потрібно).

Три незалежні аргументи, усі — з пілотних даних:

  1. НАДІЙНІСТЬ ПРОФІЛЮ (Spearman-Brown). Профіль гравця = усереднення ознаки
     по k раундах. Якщо надійність одного раунду = ICC(1) = rho, то надійність
     середнього по k раундах: R_k = k*rho / (1 + (k-1)*rho).
     Звідси k = R(1-rho) / (rho(1-R)) для цільової R (беремо 0.8 і 0.9).

  2. ПОТУЖНІСТЬ ПОПАРНОГО ПОРІВНЯННЯ. Для кожної ознаки беремо спостережений
     розмір ефекту (Hedges' g) між двома найвіддаленішими гравцями і рахуємо n
     на групу для power=0.8 при alpha=0.05 та при поправці Бонферроні
     (alpha/m, m = число ознак).

  3. ЕМПІРИЧНА КРИВА НАВЧАННЯ — точність ідентифікації як функція числа
     раундів (learning_curve_*.csv з analyze.py): де вона виходить на плато,
     там і достатній обсяг.

Перерахунок раундів у демки: у демці гравець грає ~R_side раундів за сторону
(--rounds-per-side, 12 для MR12 / 15 для MR15).

Usage:
    /usr/bin/python3 article5_movement/scripts/sample_size.py <features.csv> [--events ...]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from dataio import read_table
from statsmodels.stats.power import TTestIndPower

sys.path.insert(0, str(Path(__file__).parent))
import analyze as A


def spearman_brown_k(rho: float, target: float) -> float:
    if not (0 < rho < 1):
        return np.nan
    return target * (1 - rho) / (rho * (1 - target))


def hedges_g(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return np.nan
    sp = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    if sp == 0:
        return np.nan
    d = (a.mean() - b.mean()) / sp
    return float(d * (1 - 3 / (4 * (na + nb) - 9)))


def main(feat_csv: str, events_csv: str | None, side: str,
         rounds_per_side: int, outdir: Path) -> None:
    df = read_table(feat_csv)
    ecols = []
    if events_csv and Path(events_csv).exists():
        ev = read_table(events_csv)
        ecols = [c for c in ev.columns if c not in A.EVENT_KEYS]
        df = df.merge(ev, on=["demo", "player", "side", "round"], how="left")
        for c in ecols:
            df[c] = df[c].fillna(0.0 if c.endswith(("_per_s", "_frac")) else df[c].median())
    df = df[df["secs_alive"] >= A.MIN_SECS]
    if side != "both":
        df = df[df["side"] == side]
    feats = [c for c in A.MICRO + A.MACRO + A.KEYDYN + A.HABIT + ecols
             if c in df.columns and df[c].std(skipna=True) > 0]
    df[feats] = df[feats].apply(lambda s: s.fillna(s.median()))

    m = len(feats)
    power = TTestIndPower()
    rows = []
    for f in feats:
        rho = A.icc1(df, f)
        e2, _ = A.eta_squared_kw(df, f)
        means = df.groupby("player")[f].mean()
        lo, hi = means.idxmin(), means.idxmax()
        g = abs(hedges_g(df.loc[df.player == hi, f].to_numpy(),
                         df.loc[df.player == lo, f].to_numpy()))

        def n_for(alpha: float) -> float:
            if not np.isfinite(g) or g < 0.05:
                return np.nan
            try:
                return float(power.solve_power(effect_size=g, alpha=alpha,
                                               power=0.8, alternative="two-sided"))
            except Exception:
                return np.nan

        rows.append({
            "feature": f,
            "family": ("micro" if f in A.MICRO else "keydyn" if f in A.KEYDYN
                       else "habit" if f in A.HABIT
                       else "macro" if f in A.MACRO else "event"),
            "icc1": rho, "eta2_H": e2,
            "k_rounds_R80": spearman_brown_k(rho, 0.80),
            "k_rounds_R90": spearman_brown_k(rho, 0.90),
            "g_max_pair": g,
            "n_per_player_a05": n_for(0.05),
            "n_per_player_bonf": n_for(0.05 / max(m, 1)),
        })
    res = pd.DataFrame(rows).sort_values("icc1", ascending=False)
    res.to_csv(outdir / f"sample_size_{side}.csv", index=False)

    sig = res[res["icc1"] >= 0.10]
    print(f"[side={side}] ознак усього {m}; з ICC>=0.10: {len(sig)}")
    print("\nТОП-12 за ICC — скільки раундів на гравця для надійного профілю:")
    print(sig.head(12)[["feature", "family", "icc1", "k_rounds_R80", "k_rounds_R90",
                        "g_max_pair", "n_per_player_bonf"]].round(2).to_string(index=False))

    for q, lbl in ((0.5, "медіана"), (0.75, "75-й перцентиль")):
        k80, k90 = sig["k_rounds_R80"].quantile(q), sig["k_rounds_R90"].quantile(q)
        nb = sig["n_per_player_bonf"].quantile(q)
        print(f"\n{lbl} по інформативних ознаках:")
        print(f"  раундів на гравця для надійності профілю 0.8: {k80:.0f}"
              f"   -> демок на сторону: {k80 / rounds_per_side:.1f}")
        print(f"  раундів на гравця для надійності профілю 0.9: {k90:.0f}"
              f"   -> демок на сторону: {k90 / rounds_per_side:.1f}")
        print(f"  раундів для power=0.8 попарного тесту (Бонферроні): {nb:.0f}"
              f"   -> демок на сторону: {nb / rounds_per_side:.1f}")

    lc = outdir / f"learning_curve_{side}.csv"
    if lc.exists():
        c = read_table(lc)
        best = c["acc_mean"].max()
        plateau = c[c["acc_mean"] >= 0.95 * best]["rounds"].min()
        print(f"\nЕмпірична крива навчання: плато з {plateau} раундів "
              f"(точність {best:.2f} проти випадкової {1 / df.player.nunique():.2f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("features")
    ap.add_argument("--events", default=None)
    ap.add_argument("--side", default="both", choices=["T", "CT", "both"])
    ap.add_argument("--rounds-per-side", type=int, default=12)
    ap.add_argument("--outdir", default="article5_movement/outputs")
    a = ap.parse_args()
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    main(a.features, a.events, a.side, a.rounds_per_side, out)
