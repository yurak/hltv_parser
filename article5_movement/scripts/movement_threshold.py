#!/usr/bin/env python3
"""Поріг штрафу за рух у CS2 — виміряний, а не взятий з коду CS:GO.

Подія fire_bullets у демці CS2 несе `inaccuracy` — неточність, яку сервер
порахував для цієї кулі. Разом зі швидкістю гравця на тому самому тіку це
пряме вимірювання правила «куля точна, доки швидкість не перевищує частку t
максимальної швидкості зброї»: нижче t неточність дорівнює неточності стоячи,
вище — росте.

Беруться лише перші кулі (recoil_index == 0), на землі, без присіду, не під
час перезаряджання — щоб у неточність не домішувались віддача, стрибок і
присід. Швидкість — горизонтальна, частка — від m_flMaxSpeed зброї в руках
(у прицілі — від другого значення), таблиця features.GUN_MAX_SPEED.

Модель для кожної зброї: inacc = b + m * clip((r - t) / (u - t), 0, 1),
де r = швидкість / max. Пороги t і u шукаються сіткою, b і m — найменшими
квадратами; довірчий інтервал t — бутстреп за кулями.

    /usr/bin/python3 scripts/movement_threshold.py            # усі локальні .dem
    /usr/bin/python3 scripts/movement_threshold.py --limit 3  # швидка перевірка
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from demoparser2 import DemoParser

sys.path.insert(0, str(Path(__file__).resolve().parent))
from features import ACC_FRAC, GUN_MAX_SPEED

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "outputs" / "threshold"
MIN_SHOTS = 300
T_GRID = np.round(np.arange(0.20, 0.50001, 0.0025), 4)
U_GRID = np.round(np.arange(0.70, 1.00001, 0.01), 3)
N_BOOT = 200


PROC = ROOT / "data" / "processed"
STATE = ["tick", "steamid", "velocity_X", "velocity_Y", "active_weapon_name", "is_scoped",
         "duck_amount", "is_airborne", "is_in_reload"]


def shots_from(dem: Path) -> pd.DataFrame:
    """Кулі з fire_bullets (.dem) + стан гравця з потікового parquet.

    Швидкість НЕ можна брати з parse_ticks(ticks=<тіки пострілів>): demoparser2
    рахує velocity як зміщення між запитаними тіками, тож на рідкій вибірці
    виходить зміщення за кілька секунд (у першій спробі — до 5.8 max на землі).
    Потіковий parquet з extract_ticks.py має кожен тік, і швидкість там чесна.
    """
    tp = PROC / f"{dem.stem}_ticks.parquet"
    if not tp.exists():
        print(f"  {dem.stem}: немає {tp.name}, пропущено")
        return pd.DataFrame()
    fb = DemoParser(str(dem)).parse_event("fire_bullets")
    if fb.empty:
        return fb
    fb = fb[["tick", "user_steamid", "inaccuracy", "recoil_index"]].rename(
        columns={"user_steamid": "steamid"})
    tk = pd.read_parquet(tp, columns=STATE)
    tk["steamid"] = tk["steamid"].astype(str)
    # Постріл у CS2 — субтіковий: між тіками, а під час контрстрейфу швидкість
    # за тік змінюється на 0.15–0.2 max. Тож швидкість тіку пострілу неточна
    # саме біля порогу; сусідні тіки дають змогу відібрати постріли зі сталою
    # швидкістю (див. --stable).
    tk = tk.sort_values(["steamid", "tick"])
    sp = np.hypot(tk["velocity_X"], tk["velocity_Y"])
    g = sp.groupby(tk["steamid"])
    tk["speed_prev"], tk["speed_next"] = g.shift(1), g.shift(-1)
    fb["steamid"] = fb["steamid"].astype(str)
    s = fb.merge(tk, on=["tick", "steamid"], how="inner")
    s["demo"] = dem.stem
    return s


def fit(r: np.ndarray, y: np.ndarray, u_fixed: float | None = None
        ) -> tuple[float, float, float, float, float]:
    """(t, u, b, m, sse) з найменшою сумою квадратів. У бутстрепі u фіксується
    з основної підгонки — інакше сітка t × u на кожен повтор надто дорога."""
    best = (np.nan, np.nan, np.nan, np.nan, np.inf)
    for t in T_GRID:
        for u in ([u_fixed] if u_fixed is not None else U_GRID):
            if u <= t + 0.05:
                continue
            x = np.clip((r - t) / (u - t), 0, 1)
            X = np.c_[np.ones_like(x), x]
            coef, *_ = np.linalg.lstsq(X, y, rcond=None)
            sse = float(((X @ coef - y) ** 2).sum())
            if sse < best[4]:
                best = (float(t), float(u), float(coef[0]), float(coef[1]), sse)
    return best


SHARE_BINS = [0, 0.1, 0.2, 0.24, 0.26, 0.28, 0.30, 0.32, 0.34, 0.36, 0.38, 0.40,
              0.44, 0.5, 0.6, 0.8, 1.01]


def accurate_share(S: pd.DataFrame) -> None:
    """Частка куль із неточністю, рівною неточності стоячи, за інтервалами r.

    Без підгонки моделі: «точна» = неточність не більша за моду неточності тієї
    самої зброї при r < 0.05 (+5e-5). Окремо для всіх пострілів і для пострілів
    зі сталою швидкістю — лише там швидкість тіку відповідає субтіковій.
    """
    x = S[S["mode"] == "звичайний"]
    base = (x[x["ratio"] < 0.05].groupby("active_weapon_name")["inaccuracy"]
            .agg(lambda v: v.round(5).mode().iloc[0]))
    x = x[x["active_weapon_name"].isin(base.index)].copy()
    x["точна"] = x["inaccuracy"] <= x["active_weapon_name"].map(base) + 5e-5
    x["частка max"] = pd.cut(x["ratio"], SHARE_BINS, include_lowest=True)
    rows = []
    for span, lab in ((np.inf, "усі постріли"), (0.05, "розмах <= 0.05"),
                      (0.03, "розмах <= 0.03")):
        g = x[x["ratio_span"] <= span].groupby("частка max", observed=True)["точна"]
        t = g.agg(["size", "mean"]).reset_index()
        t.insert(0, "відбір", lab)
        rows.append(t)
    out = pd.concat(rows).rename(columns={"size": "куль", "mean": "частка точних"})
    out["частка точних"] = out["частка точних"].round(3)
    out.to_csv(OUT / "accurate_share.csv", index=False)
    full = x[x["ratio"] > 0.95].groupby("active_weapon_name")["inaccuracy"].median()
    levels = pd.DataFrame({"неточність стоячи (демка)": base,
                           "неточність при r>0.95 (демка, медіана)": full}).round(5)
    levels.to_csv(OUT / "inaccuracy_levels.csv")
    vdata_check(levels)
    print(out.to_string(index=False))


VDATA = ROOT / "references" / "game_data" / "weapons_2026-09-23.vdata"
VDATA_NAME = {"AK-47": "weapon_ak47", "M4A1-S": "weapon_m4a1_silencer", "M4A4": "weapon_m4a1",
              "Galil AR": "weapon_galilar", "FAMAS": "weapon_famas",
              "USP-S": "weapon_usp_silencer", "Glock-18": "weapon_glock",
              "Desert Eagle": "weapon_deagle", "MP9": "weapon_mp9", "P250": "weapon_p250",
              "Tec-9": "weapon_tec9", "Five-SeveN": "weapon_fiveseven", "MP7": "weapon_mp7",
              "AWP": "weapon_awp", "SSG 08": "weapon_ssg08", "CZ75-Auto": "weapon_cz75a",
              "Dual Berettas": "weapon_elite", "P2000": "weapon_hkp2000"}


def vdata_check(levels: pd.DataFrame) -> None:
    """Чи є inaccuracy з fire_bullets тією самою неточністю, що задає гра.

    У weapons.vdata поля блоку зброї стоять ПЕРЕД рядками m_szName/_class, тож
    значення беруться останні до m_szName (пошук уперед від _class дає поля
    наступної зброї — на цьому вже раз помилились). Повна неточність руху =
    стоячи + рух; пара значень — [основний режим, альтернативний] (у M4A1-S
    альтернативний — з глушником).
    """
    import re
    txt = VDATA.read_text()
    num = r"\[ ([\d.]+)(?:, ([\d.]+))? \]"
    rows = []
    for w, k in VDATA_NAME.items():
        i = txt.find(f'm_szName = "{k}"')
        if i < 0 or w not in levels.index or pd.isna(levels.loc[w].iloc[1]):
            continue
        head = txt[:i]
        st = list(re.finditer(r"m_flInaccuracyStand = " + num, head))[-1]
        mv = list(re.finditer(r"m_flInaccuracyMove = " + num, head))[-1]
        s0, m0 = float(st.group(1)), float(mv.group(1))
        m1 = float(mv.group(2) or mv.group(1))
        full = float(levels.loc[w].iloc[1])
        hit = ("основний" if abs(s0 + m0 - full) < 2e-4 else
               "альтернативний" if abs(s0 + m1 - full) < 2e-4 else "немає")
        rows.append({"зброя": w, "vdata стоячи": s0, "vdata рух (осн.)": m0,
                     "vdata рух (альт.)": m1, "демка стоячи": levels.loc[w].iloc[0],
                     "демка r>0.95 (медіана)": full, "збіг стоячи+рух": hit})
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "vdata_vs_demo.csv", index=False)
    ok = (d["збіг стоячи+рух"] != "немає") & ((d["vdata стоячи"] - d["демка стоячи"]).abs() < 2e-5)
    print(f"\nзвірка з weapons.vdata: збіглось {int(ok.sum())} з {len(d)} видів зброї")
    print(d.to_string(index=False))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--stable", type=float, default=None,
                    help="лишити постріли, де швидкість на тіках t-1..t+1 змінюється "
                         "не більше ніж на цю частку max (напр. 0.03)")
    ap.add_argument("--tag", default="", help="суфікс файлів результату")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    dems = sorted(RAW.glob("*.dem"))[: a.limit]
    parts = []
    for i, d in enumerate(dems, 1):
        s = shots_from(d)
        print(f"[{i}/{len(dems)}] {d.stem}: куль {len(s)}")
        parts.append(s)
    S = pd.concat(parts, ignore_index=True)

    S = S[S["active_weapon_name"].isin(GUN_MAX_SPEED)]
    S = S[(S["recoil_index"] == 0) & (~S["is_airborne"].astype(bool))
          & (S["duck_amount"] == 0) & (~S["is_in_reload"].astype(bool))].copy()
    sc = S["is_scoped"].astype(bool).to_numpy()
    mx = np.array([GUN_MAX_SPEED[w][1 if s else 0]
                   for w, s in zip(S["active_weapon_name"], sc)], dtype=float)
    S["speed"] = np.hypot(S["velocity_X"], S["velocity_Y"])
    S["ratio"] = S["speed"] / mx
    S["mode"] = np.where(sc, "у прицілі", "звичайний")
    nb = np.c_[S["speed_prev"], S["speed"], S["speed_next"]] / mx[:, None]
    S["ratio_span"] = np.nanmax(nb, 1) - np.nanmin(nb, 1)
    bad = ~np.isfinite(S["ratio"]) | ~np.isfinite(S["inaccuracy"])
    if bad.any():
        print(f"відкинуто куль без швидкості чи неточності: {int(bad.sum())}")
    S = S[~bad].copy()
    S.to_csv(OUT / "first_bullets.csv.gz", index=False)
    accurate_share(S)
    if a.stable is not None:
        S = S[S["ratio_span"] <= a.stable].copy()
        print(f"стала швидкість (розмах за 3 тіки <= {a.stable} max): лишилось {len(S)}")
    print(f"\nперших куль на землі без присіду: {len(S)} з {len(dems)} демок")

    rng = np.random.default_rng(0)
    rows = []
    for (w, mode), g in S.groupby(["active_weapon_name", "mode"]):
        if len(g) < MIN_SHOTS:
            continue
        r, y = g["ratio"].to_numpy(), g["inaccuracy"].to_numpy()
        t, u, b, m, _ = fit(r, y)
        boot = []
        for _ in range(N_BOOT):
            k = rng.integers(0, len(g), len(g))
            boot.append(fit(r[k], y[k], u_fixed=u)[0])
        lo, hi = np.percentile(boot, [2.5, 97.5])
        below = g.loc[g["ratio"] <= ACC_FRAC - 0.02, "inaccuracy"]
        rows.append({"зброя": w, "режим": mode, "куль": len(g),
                     "куль вище 0.34": int((g["ratio"] > ACC_FRAC).sum()),
                     "поріг t": round(t, 4), "t 95% CI": f"[{lo:.4f}; {hi:.4f}]",
                     "насичення u": round(u, 3),
                     "неточність стоячи (модель)": round(b, 5),
                     "неточність стоячи (медіана r<0.32)": round(float(below.median()), 5)
                     if len(below) else np.nan,
                     "приріст на русі m": round(m, 5)})
        print(f"{w:<14} {mode:<10} n={len(g):>5}  t={t:.4f} [{lo:.4f}; {hi:.4f}]  "
              f"u={u:.2f}  b={b:.5f}  m={m:.5f}")
    res = pd.DataFrame(rows).sort_values("куль", ascending=False)
    res.to_csv(OUT / f"threshold_by_weapon{a.tag}.csv", index=False)

    # пулінг: надлишок над неточністю стоячи, нормований на приріст m своєї зброї
    keep = {(x["зброя"], x["режим"]): x for x in rows}
    P = S[[k in keep for k in zip(S["active_weapon_name"], S["mode"])]].copy()
    P["excess"] = [(y - keep[k]["неточність стоячи (модель)"]) / keep[k]["приріст на русі m"]
                   for y, k in zip(P["inaccuracy"], zip(P["active_weapon_name"], P["mode"]))]
    bins = np.arange(0, 1.0001, 0.02)
    P["bin"] = pd.cut(P["ratio"], bins, include_lowest=True)
    curve = (P.groupby("bin", observed=True)["excess"]
              .agg(["size", "median", lambda s: s.quantile(.9)]).reset_index())
    curve.columns = ["частка max", "куль", "надлишок медіана", "надлишок p90"]
    curve.to_csv(OUT / f"pooled_curve{a.tag}.csv", index=False)
    print("\nкрива (усі зброї разом, надлишок / m):")
    print(curve.round(4).to_string(index=False))
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
