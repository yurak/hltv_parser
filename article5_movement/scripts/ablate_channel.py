#!/usr/bin/env python3
"""Чи ідентифікує ЧИСТА локомоція — рух, повністю відчеплений від бою.

Питання поставлене через Zhang (2026, arXiv:2608.24893): усі його ознаки
пересування прив'язані до пострілу («падіння швидкості за 250 мс до пострілу»,
контрстрейф перед пострілом). Каналу, де руху не торкається бойовий контекст,
не міряв ніхто. Якщо він тримає точність — це вісь нашої статті.

Методологія повторює cross_match.py один в один (ті самі спліти за серією, ті
самі класифікатори), міняється лише набір колонок.

    /usr/bin/python3 scripts/ablate_channel.py --run-id 2026-09-16_mirage_n136
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze as A
import paperlib as P
from cross_match import cv_acc

# Ознаки MICRO, які торкаються бою або прицілу. Саме їх треба прибрати,
# щоб твердження «без прицілювання» було буквальним, а не приблизним.
COMBAT_COUPLED = ["yaw_rate_mean", "yaw_rate_p95", "flick_per_s",
                  "frac_scoped", "moving_shot_frac", "shots_per_s"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--group", default="series_id")
    a = ap.parse_args()

    run = P.run_dir(a.run_id)
    df = P.features(a.run_id)
    if df is None:
        raise SystemExit(f"{a.run_id}: немає features_*.parquet")

    ev_hits = sorted(run.glob("event_features_*.parquet"))
    ecols: list[str] = []
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
    grp = a.group
    nm = df.groupby("player")[grp].nunique()
    multi = nm[nm >= 2].index.tolist()
    df = df[df["player"].isin(multi)].copy()

    feats = [c for c in A.MICRO + A.KEYDYN + A.HABIT + A.MACRO + ecols
             if c in df.columns and df[c].std(skipna=True) > 0]
    df[feats] = df[feats].apply(lambda s: s.fillna(s.median()))
    # нормалізація в межах матчу — як у cross_match.py за замовчуванням
    df[feats] = df.groupby("match_id")[feats].transform(
        lambda s: (s - s.mean()) / (s.std() + 1e-9))

    keydyn = [c for c in A.KEYDYN if c in feats]
    micro = [c for c in A.MICRO if c in feats]
    combat = [c for c in COMBAT_COUPLED if c in feats]
    micro_clean = [c for c in micro if c not in combat]

    channels = {
        "all": (feats, "усе, що є"),
        "keydyn": (keydyn, "лише клавіатура"),
        "micro": (micro, "мікрорух як є (з бойовими)"),
        "micro_clean": (micro_clean, "мікрорух без бойових"),
        "loco": (keydyn + micro_clean, "ЧИСТА ЛОКОМОЦІЯ: клавіатура + рух без бою"),
        "combat": (combat, "лише бойові/прицільні"),
    }

    y = df["player"].to_numpy()
    chance = 1.0 / len(multi)
    print(f"прогін {a.run_id}: гравців {len(multi)}, спостережень {len(df)}, "
          f"{grp} {df[grp].nunique()}, випадковий рівень {chance:.3f}")
    print(f"бойових ознак прибрано з micro: {len(combat)} ({', '.join(combat)})\n")
    print(f"{'канал':<12} {'ознак':>6} {'між серіями':>12} {'у межах':>9} {'деград.':>8}  опис")

    rows = []
    for name, (cols, desc) in channels.items():
        if not cols:
            continue
        X = df[cols].to_numpy()
        across = max(cv_acc(X, y, df[grp].to_numpy(), "rf", True),
                     cv_acc(X, y, df[grp].to_numpy(), "lda", True))
        within = max(cv_acc(X, y, df["round"].to_numpy(), "rf", False),
                     cv_acc(X, y, df["round"].to_numpy(), "lda", False))
        rows.append({"channel": name, "n_feat": len(cols), "across_series": across,
                     "within_match": within, "degradation": within - across,
                     "chance": chance, "desc": desc})
        print(f"{name:<12} {len(cols):>6} {across:>12.3f} {within:>9.3f} "
              f"{within - across:>8.3f}  {desc}")

    out = run / "channel_ablation.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\n-> {out}")

    r = {x["channel"]: x for x in rows}
    if "loco" in r and "all" in r:
        keep = r["loco"]["across_series"] / r["all"]["across_series"]
        print(f"\nЧиста локомоція тримає {keep:.1%} від точності повного набору "
              f"({r['loco']['across_series']:.3f} проти {r['all']['across_series']:.3f})")
    if "combat" in r:
        print(f"Лише бойові/прицільні ознаки: {r['combat']['across_series']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
