"""
Крок 7: профіль одного гравця в розрізі мап.

Питання: що в руховому патерні гравця тримається на будь-якій мапі (моторика),
а що визначається мапою (позиційна гра, утиліта, зброя)?

Для кожної родини ознак рахується:
  mean по мапі — саме значення;
  CV_map      — коефіцієнт варіації середніх між мапами (розкид профілю);
  z_spread    — той самий розкид, але у одиницях загального SD по всіх гравцях;
                це дає порівнюваність: якщо z_spread по мапах менший за типову
                відстань між гравцями, ознака придатна для міжмапової
                ідентифікації.
Плюс власні відстані гравця: між матчами на тій самій мапі проти між мапами.

Usage:
    /usr/bin/python3 article5_movement/scripts/player_map_profile.py \
        outputs/dataset_features.csv --events outputs/dataset_event_features.csv \
        --player s1mple
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from dataio import read_table

sys.path.insert(0, str(Path(__file__).parent))
import analyze as A

SHOW = {
    "keydyn": ["presses_total_per_s", "dwell_A_ms", "dwell_D_ms", "dwell_W_ms",
               "strafe_flight_ms", "strafe_overlap_frac", "combo_switch_per_s",
               "combo_persistence", "combo_trans_entropy"],
    "micro": ["counterstrafe_per_s", "strafe_switch_per_s", "frac_walkkey",
              "frac_run", "speed_mean", "yaw_rate_p95", "duck_per_s"],
    "habit": ["switch_per_s", "qswitch_per_s", "knife_run_frac", "wpn_sniper_frac",
              "reload_per_s"],
    "event": ["stop_counterstrafe_frac", "stop_ms_mean", "stop_speed_at_shot",
              "peeks_per_s", "peek_depth_mean", "peek_jiggle_frac", "wide_peek_per_s"],
    "macro": ["path_per_s", "radius_gyration", "path_efficiency", "disp_10s"],
}


def main(args) -> None:
    df = read_table(args.features)
    if args.events and Path(args.events).exists():
        ev = read_table(args.events)
        ecols = [c for c in ev.columns if c not in A.EVENT_KEYS]
        keys = [k for k in ("demo", "match_id", "map", "player", "side", "round")
                if k in df.columns and k in ev.columns]
        df = df.merge(ev[keys + ecols], on=keys, how="left")
        for c in ecols:
            df[c] = df[c].fillna(0.0 if c.endswith(("_per_s", "_frac")) else df[c].median())
    df = df[df["secs_alive"] >= A.MIN_SECS].copy()
    if args.side != "both":
        df = df[df["side"] == args.side]

    pl = df[df["player"] == args.player]
    if pl.empty:
        print(f"Гравця {args.player} у датасеті немає.")
        return
    maps = sorted(pl["map"].unique())
    print(f"{args.player}: {len(pl)} раундів, мапи {maps}, "
          f"матчів {pl.match_id.nunique()}, сторона={args.side}\n")

    for fam, cols in SHOW.items():
        cols = [c for c in cols if c in df.columns]
        if not cols:
            continue
        tab = pl.groupby("map")[cols].mean().T
        sd_all = df[cols].std()
        tab["CV_map"] = (tab[maps].std(axis=1) / tab[maps].mean(axis=1).abs()).round(3)
        tab["z_spread"] = (tab[maps].std(axis=1) / sd_all).round(3)
        print(f"--- {fam.upper()} ---")
        print(tab.round(3).to_string())
        print()

    # власні відстані: та сама мапа (інший матч) проти іншої мапи
    feats = [c for c in A.MICRO + A.KEYDYN + A.HABIT
             if c in df.columns and df[c].std(skipna=True) > 0]
    icc = {c: A.icc1(df, c) for c in feats}
    use = [c for c in feats if np.isfinite(icc[c]) and icc[c] >= 0.10]
    z = df.copy()
    z[use] = z.groupby("match_id")[use].transform(lambda s: (s - s.mean()) / (s.std() + 1e-9))
    prof = (z[z.player == args.player].groupby(["match_id", "map"])[use].mean()
            .reset_index())
    # ознаки, що не визначені для цього гравця (напр. подій такого типу не було),
    # інакше вони отруюють усі відстані значенням nan
    use = [c for c in use if prof[c].notna().all()]
    same, cross = [], []
    for (i, a), (j, b) in itertools.combinations(prof.iterrows(), 2):
        d = float(np.linalg.norm(a[use].to_numpy(float) - b[use].to_numpy(float))
                  / np.sqrt(len(use)))
        (same if a["map"] == b["map"] else cross).append(d)
    others = z[z.player != args.player].groupby(["player", "match_id"])[use].mean().dropna()
    mine = np.nan_to_num(prof[use].mean().to_numpy(float))
    imp = [float(np.linalg.norm(mine - r.to_numpy(float)) / np.sqrt(len(use)))
           for _, r in others.iterrows()]
    print(f"--- СТАБІЛЬНІСТЬ ПРОФІЛЮ ({len(use)} ознак з ICC>=0.10, "
          f"keydyn+micro+habit) ---")
    if same:
        print(f"той самий гравець, та сама мапа, інший матч: {np.mean(same):.3f}"
              f"  (n={len(same)})")
    if cross:
        print(f"той самий гравець, інша мапа:                {np.mean(cross):.3f}"
              f"  (n={len(cross)})")
    print(f"інші гравці:                                 {np.mean(imp):.3f}"
          f"  (n={len(imp)})")

    # повний рейтинг: що тримається на будь-якій мапі, а що визначається мапою
    allf = [c for c in df.columns if df[c].dtype.kind in "fi"
            and c not in ("round", "secs_alive", "steamid")]
    tab = pl.groupby("map")[allf].mean().T
    sd = df[allf].std()
    spread = (tab.std(axis=1) / sd).dropna().sort_values()
    print(f"\n--- НАЙСТАБІЛЬНІШІ МІЖ МАПАМИ (z_spread) ---")
    print(spread.head(12).round(3).to_string())
    print(f"\n--- НАЙБІЛЬШ ЗАЛЕЖНІ ВІД МАПИ ---")
    print(spread.tail(12).round(3).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("features")
    ap.add_argument("--events", default=None)
    ap.add_argument("--player", required=True)
    ap.add_argument("--side", default="both", choices=["T", "CT", "both"])
    main(ap.parse_args())
