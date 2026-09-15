"""
Крок 5: порівняння профілів — біометрична драбина відстаней.

Профіль = усереднення ознак гравця по раундах у межах одного блоку
(блок = матч, або половина матчу, якщо матч один — режим --split-half).

Три типи пар профілів:
    genuine          той самий гравець, різні блоки/матчі  -> нижня межа відстані
    impostor_same    різні гравці, ОДНАКОВА роль
    impostor_diff    різні гравці, РІЗНІ ролі               -> верхня межа

Гіпотеза дослідження: genuine < impostor_same < impostor_diff.
Якщо genuine не менший за impostor — руховий підпис не існує, і далі йти нема куди.

Метрики:
    EER    — рівень рівної помилки для розділення genuine/impostor
    AUC    — площа під ROC для того самого розділення
    d'     — (mu_imp - mu_gen) / sqrt((sd_gen^2 + sd_imp^2)/2)
    для конкретної пари гравців: відстань + перцентиль у impostor-розподілі
             + таблиця Hedges' g по кожній ознаці (де саме різниця)

Роли беруться з data/roster.csv (колонки: player,role). Без нього всі
impostor-пари вважаються "різні ролі невідомі" і об'єднуються.

Usage:
    # перевірка механіки на одній демці (блок = половина матчу):
    /usr/bin/python3 article5_movement/scripts/compare_profiles.py \
        outputs/pilot_mirage_features.csv --events outputs/pilot_mirage_event_features.csv \
        --split-half --side both
    # реальний режим (блок = матч):
    /usr/bin/python3 article5_movement/scripts/compare_profiles.py \
        outputs/dataset_features.csv --events outputs/dataset_event_features.csv \
        --roster data/roster.csv --pair ropz s1mple
"""
from __future__ import annotations

import argparse
import json
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from dataio import read_table
from sklearn.metrics import roc_auc_score, roc_curve

sys.path.insert(0, str(Path(__file__).parent))
import analyze as A

ICC_MIN = 0.10          # ознаки з меншим ICC — шум, у профіль не беруться
MIN_ROUNDS_PER_BLOCK = 5


def load(feat_csv: str, events_csv: str | None, side: str,
         context: str = "tournament") -> tuple[pd.DataFrame, list[str]]:
    df = read_table(feat_csv)
    ecols: list[str] = []
    if events_csv and Path(events_csv).exists():
        ev = read_table(events_csv)
        ecols = [c for c in ev.columns if c not in A.EVENT_KEYS and c != "match_id"]
        keys = [k for k in ("match_id", "demo", "player", "side", "round") if k in df.columns and k in ev.columns]
        df = df.merge(ev[keys + ecols], on=keys, how="left")
        for c in ecols:
            df[c] = df[c].fillna(0.0 if c.endswith(("_per_s", "_frac")) else df[c].median())
    df = df[df["secs_alive"] >= A.MIN_SECS].copy()
    if context != "all" and "context" in df.columns:
        df = df[df["context"] == context].copy()
    if side != "both":
        df = df[df["side"] == side].copy()
    if "match_id" not in df.columns:
        df["match_id"] = df["demo"]
    feats = [c for c in A.MICRO + A.KEYDYN + A.MACRO + A.HABIT + ecols
             if c in df.columns and df[c].std(skipna=True) > 0]
    df[feats] = df[feats].apply(lambda s: s.fillna(s.median()))
    return df, feats


def make_blocks(df: pd.DataFrame, split_half: bool,
                unit: str = "series_id") -> pd.DataFrame:
    """Блок = СЕРІЯ (одиниця незалежної сесії), не окрема мапа.

    Три мапи одного Bo3 — це один день, той самий суперник, та сама розминка й
    ті самі налаштування миші. Якщо брати їх як різні блоки, genuine-пари
    "інша мапа" виявляються здебільшого парами всередині однієї серії, і
    схожість "свій-свій" завищується. `unit="match_id"` лишено для звірки з
    попередніми прогонами — саме так рахувалось до вересня 2026.
    """
    if unit not in df.columns:
        unit = "match_id"
    if not split_half:
        df["block"] = df[unit]
        return df
    parts = []
    for (m, p, s), g in df.groupby([unit, "player", "side"]):
        g = g.sort_values("round").copy()
        half = len(g) // 2
        g["block"] = [f"{m}#A"] * half + [f"{m}#B"] * (len(g) - half)
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def profiles(df: pd.DataFrame, feats: list[str], families: list[str],
             z_by: str = "pooled") -> tuple[pd.DataFrame, list[str]]:
    """
    Профілі (гравець, сторона, блок) у z-шкалі, лише інформативні ознаки.

    z_by="pooled" — нормалізація по всьому датасету. Просто, але відстань між
    гравцями з РІЗНИХ матчів вбирає ще й ефект матчу: інший сервер, інші
    опоненти, інший рівень турніру.
    z_by="match"  — нормалізація в межах кожного матчу. Знімає ефект матчу,
    але робить профіль відносним: «наскільки гравець відрізняється від інших
    дев'ятьох у своїй же грі». Для порівняння гравців, що ніколи не грали в
    одному матчі, це чесніший варіант.
    """
    fam_map = {"micro": A.MICRO, "keydyn": A.KEYDYN, "macro": A.MACRO, "habit": A.HABIT}
    allowed = set()
    for f in families:
        allowed |= set(fam_map.get(f, []))
    if "event" in families:
        allowed |= {c for c in feats if c not in A.MICRO + A.KEYDYN + A.MACRO + A.HABIT}
    use = [c for c in feats if c in allowed]

    icc = {c: A.icc1(df, c) for c in use}
    use = [c for c in use if np.isfinite(icc[c]) and icc[c] >= ICC_MIN]

    z = df.copy()
    if z_by == "match" and "match_id" in z.columns:
        z[use] = z.groupby("match_id")[use].transform(
            lambda s: (s - s.mean()) / (s.std() + 1e-9))
    else:
        z[use] = (z[use] - z[use].mean()) / (z[use].std() + 1e-9)
    rows = []
    for (p, s, b), g in z.groupby(["player", "side", "block"]):
        if len(g) < MIN_ROUNDS_PER_BLOCK:
            continue
        rec = {"player": p, "side": s, "block": b, "n_rounds": len(g),
               "map": g["map"].iloc[0] if "map" in g.columns else "?"}
        rec.update(g[use].mean().to_dict())
        rows.append(rec)
    return pd.DataFrame(rows), use


def eer(y: np.ndarray, score: np.ndarray) -> tuple[float, float]:
    """y=1 -> impostor. Повертає (EER, порог)."""
    fpr, tpr, thr = roc_curve(y, score)
    i = int(np.nanargmin(np.abs((1 - tpr) - fpr)))
    return float((fpr[i] + (1 - tpr[i])) / 2), float(thr[i])


def main(args) -> None:
    df, feats = load(args.features, args.events, args.side, args.context)
    df = make_blocks(df, args.split_half, args.block)
    prof, used = profiles(df, feats, args.families, args.z_by)
    if prof.empty:
        print("Профілів не побудовано — мало раундів на блок.")
        return

    roles: dict[str, str] = {}
    if args.roster and Path(args.roster).exists():
        r = read_table(args.roster)
        roles = dict(zip(r["player"], r["role"]))

    rows = []
    for (i, a), (j, b) in itertools.combinations(prof.iterrows(), 2):
        if a["side"] != b["side"]:
            continue
        if a["player"] == b["player"] and a["block"] == b["block"]:
            continue
        d = float(np.linalg.norm(a[used].to_numpy(float) - b[used].to_numpy(float))
                  / np.sqrt(len(used)))
        same_map = a.get("map") == b.get("map")
        if a["player"] == b["player"]:
            kind = "genuine_same_map" if same_map else "genuine_cross_map"
        elif roles and roles.get(a["player"]) and roles.get(b["player"]):
            kind = ("impostor_same_role" if roles[a["player"]] == roles[b["player"]]
                    else "impostor_diff_role")
        else:
            kind = "impostor_same_map" if same_map else "impostor_cross_map"
        rows.append({"a": a["player"], "b": b["player"], "side": a["side"],
                     "block_a": a["block"], "block_b": b["block"],
                     "map_a": a.get("map"), "map_b": b.get("map"),
                     "same_map": int(same_map), "kind": kind, "dist": d})
    pairs = pd.DataFrame(rows)
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(out / f"profile_pairs_{args.side}.csv", index=False)

    print(f"Ознак у профілі (ICC>={ICC_MIN}): {len(used)} з родин {args.families}")
    print(f"Профілів: {len(prof)}  |  пар: {len(pairs)}\n")
    print(pairs.groupby("kind")["dist"].agg(["count", "mean", "std", "median"]).round(3).to_string())

    gen = pairs[pairs.kind.str.startswith("genuine")]["dist"].to_numpy()
    imp = pairs[~pairs.kind.str.startswith("genuine")]["dist"].to_numpy()
    # чи переживає підпис зміну мапи: свій профіль на іншій мапі проти чужого
    gsm = pairs[pairs.kind == "genuine_same_map"]["dist"]
    gcm = pairs[pairs.kind == "genuine_cross_map"]["dist"]
    if len(gsm) and len(gcm):
        print(f"\nінваріантність до мапи: свій на тій самій мапі {gsm.mean():.3f}"
              f" | свій на іншій мапі {gcm.mean():.3f}"
              f" | чужий {imp.mean():.3f}")

    if gen.size and imp.size:
        y = np.r_[np.zeros(gen.size), np.ones(imp.size)]
        sc = np.r_[gen, imp]
        auc = roc_auc_score(y, sc)
        e, thr = eer(y, sc)
        dprime = (imp.mean() - gen.mean()) / np.sqrt((gen.var() + imp.var()) / 2)
        print(f"\ngenuine проти impostor:  AUC={auc:.3f}  EER={e:.3f}  d'={dprime:.2f}"
              f"  (порог відстані {thr:.3f})")
        # у файл, а не лише в консоль: маніфест прогону має читати це машинно
        (out / f"verification_{args.side}.json").write_text(json.dumps({
            "side": args.side, "block_unit": args.block, "z_by": args.z_by,
            "context": args.context, "families": args.families,
            "n_features": len(used), "n_profiles": int(len(prof)),
            "n_genuine": int(gen.size), "n_impostor": int(imp.size),
            "auc": round(float(auc), 4), "eer": round(float(e), 4),
            "dprime": round(float(dprime), 3), "threshold": round(float(thr), 4),
            "genuine_same_map": round(float(gsm.mean()), 4) if len(gsm) else None,
            "genuine_cross_map": round(float(gcm.mean()), 4) if len(gcm) else None,
        }, indent=2, ensure_ascii=False))
    else:
        print("\nНемає genuine-пар: потрібно >=2 блоки (матчі) на гравця.")

    if args.pair:
        a, b = args.pair
        sel = pairs[((pairs.a == a) & (pairs.b == b)) | ((pairs.a == b) & (pairs.b == a))]
        if sel.empty:
            print(f"\nПари {a}–{b} у даних немає.")
        else:
            d = sel["dist"].mean()
            pct = float((imp < d).mean() * 100) if imp.size else np.nan
            print(f"\n=== {a} проти {b} ===")
            print(f"відстань профілів: {d:.3f}  -> перцентиль серед impostor-пар: {pct:.0f}%")
            print("(нижчий перцентиль = схожіші, ніж типова пара різних гравців)")
            sub = df[df.player.isin([a, b])]
            gr = []
            for c in used:
                x = sub.loc[sub.player == a, c].to_numpy(float)
                yv = sub.loc[sub.player == b, c].to_numpy(float)
                if len(x) > 1 and len(yv) > 1:
                    sp = np.sqrt(((len(x) - 1) * x.var(ddof=1) + (len(yv) - 1) * yv.var(ddof=1))
                                 / (len(x) + len(yv) - 2))
                    if sp > 0:
                        gr.append({"feature": c, "g": (x.mean() - yv.mean()) / sp,
                                   f"mean_{a}": x.mean(), f"mean_{b}": yv.mean()})
            gt = pd.DataFrame(gr)
            gt["abs_g"] = gt["g"].abs()
            gt = gt.sort_values("abs_g", ascending=False)
            gt.to_csv(out / f"pair_{a}_vs_{b}_{args.side}.csv", index=False)
            print("\nНайбільші розбіжності (Hedges' g):")
            print(gt.head(12).drop(columns="abs_g").round(3).to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("features")
    ap.add_argument("--events", default=None)
    ap.add_argument("--roster", default="article5_movement/data/roster.csv")
    ap.add_argument("--side", default="both", choices=["T", "CT", "both"])
    ap.add_argument("--families", nargs="+", default=["keydyn", "event", "micro", "habit"],
                    choices=["keydyn", "event", "micro", "macro", "habit"])
    ap.add_argument("--z-by", default="pooled", choices=["pooled", "match"],
                    dest="z_by", help="нормалізація: по всьому датасету або в межах матчу")
    ap.add_argument("--block", default="series_id",
                    choices=["series_id", "match_id"],
                    help="одиниця незалежної сесії (типово серія)")
    ap.add_argument("--split-half", action="store_true",
                    help="ділити кожен матч на дві половини (для перевірки на одній демці)")
    ap.add_argument("--context", default="tournament", choices=["tournament", "platform", "all"],
                    help="турнірний матч чи позатурнірна гра; за замовчуванням не змішуються")
    ap.add_argument("--pair", nargs=2, default=None, metavar=("A", "B"))
    ap.add_argument("--outdir", default="article5_movement/outputs")
    main(ap.parse_args())
