"""
Крок 8: порівняння групи гравців між собою.

Дає три речі:
  1. Матрицю попарних відстаней між профілями (нормалізація в межах матчу),
     кожна відстань — з перцентилем у розподілі всіх impostor-пар когорти.
  2. Власний масштаб кожного гравця: відстань його профілю до себе ж в інших
     матчах (genuine). Без цього числа матриця не читається.
  3. Ознаки, що розділяють саме цю групу (eta^2 по підвибірці), із середніми в
     природних одиницях, і «підпис» кожного гравця — найбільш екстремальні
     ознаки відносно всієї когорти (у z-одиницях).

Роли: data/roster.csv (генерується з даних) + необов'язковий
data/roles_manual.csv, який має приоритет.

Usage:
    /usr/bin/python3 article5_movement/scripts/compare_group.py \
        outputs/dataset_features.csv --events outputs/dataset_event_features.csv \
        --players ropz s1mple ZywOo flameZ
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from dataio import read_table
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
import analyze as A

ICC_MIN = 0.10
MIN_ROUNDS = 5


def load(args) -> tuple[pd.DataFrame, list[str]]:
    df = read_table(args.features)
    ecols: list[str] = []
    if args.events and Path(args.events).exists():
        ev = read_table(args.events)
        ecols = [c for c in ev.columns if c not in A.EVENT_KEYS]
        keys = [k for k in ("demo", "match_id", "map", "player", "side", "round")
                if k in df.columns and k in ev.columns]
        df = df.merge(ev[keys + ecols], on=keys, how="left")
        for c in ecols:
            df[c] = df[c].fillna(0.0 if c.endswith(("_per_s", "_frac")) else df[c].median())
    df = df[df["secs_alive"] >= A.MIN_SECS].copy()
    if getattr(args, "context", "all") != "all" and "context" in df.columns:
        df = df[df["context"] == args.context].copy()
    if args.side != "both":
        df = df[df["side"] == args.side].copy()
    fam_map = {"micro": A.MICRO, "keydyn": A.KEYDYN, "habit": A.HABIT, "macro": A.MACRO}
    allowed: list[str] = []
    for f in args.families:
        allowed += fam_map.get(f, [])
    if "event" in args.families:
        allowed += ecols
    feats = [c for c in allowed if c in df.columns and df[c].std(skipna=True) > 0]
    df[feats] = df[feats].apply(lambda s: s.fillna(s.median()))
    return df, feats


def roles(base: str, manual: str) -> dict[str, str]:
    r: dict[str, str] = {}
    for path in (base, manual):
        if path and Path(path).exists():
            t = read_table(path)
            r.update(dict(zip(t["player"], t["role"])))
    return r


def main(args) -> None:
    df, feats = load(args)
    icc = {c: A.icc1(df, c) for c in feats}
    use = [c for c in feats if np.isfinite(icc[c]) and icc[c] >= ICC_MIN]
    rl = roles(args.roster, args.roles_manual)

    z = df.copy()
    z[use] = z.groupby("match_id")[use].transform(lambda s: (s - s.mean()) / (s.std() + 1e-9))
    prof = []
    for (p, b), g in z.groupby(["player", "match_id"]):
        if len(g) < MIN_ROUNDS:
            continue
        prof.append({"player": p, "block": b, "map": g["map"].iloc[0],
                     "context": g["context"].iloc[0] if "context" in g.columns else "official",
                     "n_rounds": len(g), **g[use].mean().to_dict()})
    prof = pd.DataFrame(prof).dropna(subset=use)

    def dist(a, b) -> float:
        return float(np.linalg.norm(a - b) / np.sqrt(len(use)))

    # розподіл усіх impostor-пар когорти — це масштаб
    imp, gen = [], {}
    for (i, a), (j, b) in itertools.combinations(prof.iterrows(), 2):
        d = dist(a[use].to_numpy(float), b[use].to_numpy(float))
        if a["player"] == b["player"]:
            gen.setdefault(a["player"], []).append(d)
        else:
            imp.append(d)
    imp = np.array(imp)

    # ніки можуть починатися з дефіса (напр. "-DAMIENNNNNN") — тоді їх передають
    # з ведучим пробілом, щоб argparse не сприйняв за прапорець
    wanted = [p.strip() for p in args.players]
    sel = [p for p in wanted if p in set(prof["player"])]
    missing = [p for p in wanted if p not in sel]
    if missing:
        print(f"немає в даних або мало раундів: {', '.join(missing)}\n")

    print(f"когорта: {prof.player.nunique()} гравців, {len(prof)} профілів, "
          f"{len(imp)} impostor-пар | ознак у профілі: {len(use)} (ICC>={ICC_MIN})")
    print(f"масштаб: impostor-пари {imp.mean():.3f} ± {imp.std():.3f}\n")

    print("ВЛАСНИЙ МАСШТАБ (свій профіль в інших матчах)")
    print(f"{'гравець':<10} {'роль':<9} {'genuine':>8} {'матчів':>7}")
    for p in sel:
        g = gen.get(p, [])
        n = int((prof.player == p).sum())
        print(f"{p:<10} {rl.get(p,'?'):<9} {np.mean(g) if g else np.nan:>8.3f} {n:>7}")

    print("\nМАТРИЦЯ ВІДСТАНЕЙ (у дужках — перцентиль серед impostor-пар когорти)")
    cent = {p: prof.loc[prof.player == p, use].mean().to_numpy(float) for p in sel}
    hdr = " " * 10 + "".join(f"{p:>18}" for p in sel)
    print(hdr)
    for a in sel:
        row = f"{a:<10}"
        for b in sel:
            if a == b:
                g = gen.get(a, [])
                row += f"{('[' + format(np.mean(g), '.3f') + ']') if g else '—':>18}"
            else:
                d = dist(cent[a], cent[b])
                pct = (imp < d).mean() * 100
                row += f"{format(d, '.3f') + f' ({pct:.0f}%)':>18}"
        print(row)
    print("на діагоналі у [дужках] — genuine-відстань гравця до себе")

    if args.self_matrix:
        for p in sel:
            sub = prof[prof.player == p].sort_values("block")
            if len(sub) < 2:
                continue
            lbl = [f"{b.split('_')[0][5:]} {m.replace('de_','')}"
                   + ("*" if c == "platform" else "")
                   for b, m, c in zip(sub["block"], sub["map"], sub["context"])]
            print(f"\nВЛАСНІ ВІДСТАНІ МІЖ ДЕМКАМИ: {p} "
                  f"({len(sub)} матчів, роль {rl.get(p,'?')})")
            print(" " * 14 + "".join(f"{x:>14}" for x in lbl))
            M = sub[use].to_numpy(float)
            vals = []
            for i, li in enumerate(lbl):
                row = f"{li:<14}"
                for j in range(len(lbl)):
                    if i == j:
                        row += f"{'—':>14}"
                    else:
                        d = dist(M[i], M[j])
                        row += f"{d:>14.3f}"
                        if j > i:
                            vals.append(d)
                print(row)
            v = np.array(vals)
            same = [dist(M[i], M[j]) for i in range(len(M)) for j in range(i + 1, len(M))
                    if sub["map"].iloc[i] == sub["map"].iloc[j]]
            diff = [dist(M[i], M[j]) for i in range(len(M)) for j in range(i + 1, len(M))
                    if sub["map"].iloc[i] != sub["map"].iloc[j]]
            print(f"  свої пари: середнє {v.mean():.3f}, розкид {v.min():.3f}-{v.max():.3f}"
                  f"  |  та сама мапа: {np.mean(same):.3f} (n={len(same)})"
                  f"  |  інші мапи: {np.mean(diff):.3f} (n={len(diff)})")
            print(f"  для порівняння: чужі пари когорти {imp.mean():.3f} "
                  f"(медіана {np.median(imp):.3f})")
            if (sub["context"] == "platform").any():
                fx = [dist(M[i], M[j]) for i in range(len(M)) for j in range(len(M))
                      if i != j and (sub["context"].iloc[i] == "platform") != (sub["context"].iloc[j] == "platform")]
                oo = [dist(M[i], M[j]) for i in range(len(M)) for j in range(i + 1, len(M))
                      if sub["context"].iloc[i] == sub["context"].iloc[j] == "tournament"]
                print(f"  * позатурнірні: до турнірних {np.mean(fx):.3f} (n={len(fx)})"
                      f"  |  турнірні між собою {np.mean(oo):.3f} (n={len(oo)})")

    # що розділяє саме цю групу
    sub = df[df.player.isin(sel)]
    rows = []
    for c in use:
        groups = [sub.loc[sub.player == p, c].dropna().to_numpy() for p in sel]
        groups = [g for g in groups if len(g) > 1]
        if len(groups) < 2 or np.ptp(np.concatenate(groups)) == 0:
            continue
        h, pv = stats.kruskal(*groups)
        n, k = sum(len(g) for g in groups), len(groups)
        rows.append({"feature": c, "eta2": max((h - k + 1) / (n - k), 0), "p": pv,
                     **{p: sub.loc[sub.player == p, c].mean() for p in sel}})
    tab = pd.DataFrame(rows).sort_values("eta2", ascending=False)
    tab.to_csv(Path(args.outdir) / f"group_{'_'.join(sel)}_{args.side}.csv", index=False)
    print(f"\nОЗНАКИ, ЩО РОЗДІЛЯЮТЬ ГРУПУ (топ-{args.top} за eta^2, природні одиниці)")
    print(tab.head(args.top).drop(columns="p").round(3).to_string(index=False))

    print("\nПІДПИС КОЖНОГО (найбільш екстремальні ознаки відносно когорти, у SD)")
    pooled = df.groupby("player")[use].mean()
    zz = (pooled - pooled.mean()) / pooled.std()
    for p in sel:
        s = zz.loc[p].dropna().sort_values()
        top = list(s.head(3).items()) + list(s.tail(3).items())[::-1]
        txt = ", ".join(f"{k} {v:+.2f}" for k, v in top)
        print(f"  {p:<8} {txt}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("features")
    ap.add_argument("--events", default=None)
    ap.add_argument("--players", nargs="+", required=True)
    ap.add_argument("--side", default="both", choices=["T", "CT", "both"])
    ap.add_argument("--roster", default="article5_movement/data/roster.csv")
    ap.add_argument("--roles-manual", default="article5_movement/data/roles_manual.csv",
                    dest="roles_manual")
    ap.add_argument("--families", nargs="+", default=["keydyn", "micro", "habit", "event"],
                    choices=["keydyn", "micro", "habit", "macro", "event"])
    ap.add_argument("--context", default="tournament", choices=["tournament", "platform", "all"],
                    help="турнірний матч чи позатурнірна гра; за замовчуванням не змішуються")
    ap.add_argument("--top", type=int, default=14)
    ap.add_argument("--self-matrix", action="store_true", dest="self_matrix",
                    help="матриці відстаней гравця між його власними матчами")
    ap.add_argument("--outdir", default="article5_movement/outputs")
    main(ap.parse_args())
