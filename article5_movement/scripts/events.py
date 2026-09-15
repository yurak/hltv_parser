"""
Крок 2b: детектор ПОДІЙ руху — контрстрейфи (стопи) та піки.

Ідея: усереднені частки по раунду згладжують саме те, що робить гравця
вузнаваним. Тому виділяємо дискретні події і описуємо кожну окремо, а вже
потім агрегуємо розподіли.

ПОДІЯ "СТОП" (техніка гасіння швидкості перед вистрілом):
    швидкість падає з >SPEED_HI до <SPEED_LO за <=STOP_WIN тіків.
    Класифікація техніки за клавішами у вікні гасіння:
      counterstrafe — натиснуто протилежну боковій (A після D / D після A)
      counter_fwd   — протилежну до W/S
      crouch_stop   — гасіння присіданням (CTRL)
      release       — просто відпустив клавіші
    Метрики: тривалість гасіння, залишкова швидкість, чи був вистріл у
    вікні SHOT_WIN після стопу і з якою швидкістю, перерегулювання (overshoot).

ПОДІЯ "ПІК" (вихід з-за укриття):
    від якірної точки (гравець стояв >=ANCHOR_MIN тіків) — екскурсія:
    вихід на глибину depth і, можливо, повернення в межі RETURN_R.
      jiggle  depth <  60 u  (шолдер/джигл-пік)
      narrow  60..160 u
      wide    >160 u         (пік "на широкому")
    Якщо не повернувся у вікні PEEK_WIN -> тип "commit" (свінг/забіг).
    Метрики: глибина, час виходу, макс. швидкість, чи тримав SHIFT,
    зміна yaw під час виходу (пре-айм проти доводки), вистріли.

Usage:
    /usr/bin/python3 article5_movement/scripts/events.py <ticks.parquet>
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

TICKRATE = 64.0
# --- стопи ---
SPEED_HI = 150.0      # u/s — рух
SPEED_LO = 35.0       # u/s — фактично стоїть
STOP_WIN_MS = 375.0   # мс на гасіння
SHOT_WIN_MS = 375.0   # мс після стопу, де шукаємо вистріл
# --- піки ---
ANCHOR_MIN_MS = 250.0 # мс стояння, щоб вважати точку укриттям
PEEK_WIN_MS = 5000.0  # мс — максимальне вікно спостереження за піком
OUT_WIN_MS = 1500.0   # мс — у цьому вікні шукаємо вершину виходу
DEC_MS = 94.0         # стільки мс спаду підтверджують вершину піка
RETURN_R = 45.0       # u — радіус повернення в укриття
DEPTH_JIGGLE = 60.0
DEPTH_WIDE = 160.0
DEPTH_MAX = 320.0     # u — глибше це вже не пік, а ротація/забіг
LAT_RATIO_MIN = 1.0   # рух боком мусить домінувати над рухом уперед


def _runs(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    d = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1)


def _wrap180(a: np.ndarray) -> np.ndarray:
    return (a + 180.0) % 360.0 - 180.0


def _ticks(ms: float, tr: float, lo: int = 1) -> int:
    return max(lo, int(round(ms / 1000.0 * tr)))


def stop_events(g: pd.DataFrame, tr: float = TICKRATE) -> list[dict]:
    spd = g["speed"].to_numpy(float)
    L, R = g["LEFT"].to_numpy(np.int8), g["RIGHT"].to_numpy(np.int8)
    F, B = g["FORWARD"].to_numpy(np.int8), g["BACK"].to_numpy(np.int8)
    DK = g["DUCK"].to_numpy(np.int8)
    FIRE = g["FIRE"].to_numpy(np.int8)
    yaw = g["yaw"].to_numpy(float)
    vx, vy = g["velocity_X"].to_numpy(float), g["velocity_Y"].to_numpy(float)
    ry = np.deg2rad(yaw)
    v_lat = vx * (-np.sin(ry)) + vy * np.cos(ry)
    n = len(spd)

    stop_win, shot_win = _ticks(STOP_WIN_MS, tr), _ticks(SHOT_WIN_MS, tr)
    slow_start, _ = _runs(spd < SPEED_LO)
    out = []
    for lo in slow_start:
        hi_zone = np.flatnonzero(spd[max(0, lo - stop_win):lo] > SPEED_HI)
        if hi_zone.size == 0:
            continue
        hi = max(0, lo - stop_win) + hi_zone[-1]
        w = slice(hi, min(lo + 2, n))
        pre = slice(max(0, hi - 8), hi + 1)
        # домінантна бокова клавіша до гасіння
        pre_dir = int(np.sign(R[pre].sum() - L[pre].sum()))
        opp = (L[w].any() if pre_dir > 0 else R[w].any() if pre_dir < 0 else False)
        opp_fwd = bool((B[w].any() and F[pre].any()) or (F[w].any() and B[pre].any()))
        tech = ("counterstrafe" if opp else
                "counter_fwd" if opp_fwd else
                "crouch_stop" if DK[w].any() else
                "release")
        shot_idx = np.flatnonzero((FIRE[lo:lo + shot_win] == 1))
        shot = shot_idx.size > 0
        # перерегулювання: зміна знаку бокової швидкості після стопу
        post = v_lat[lo:min(lo + 12, n)]
        overshoot = bool(np.any(np.sign(post) == -np.sign(v_lat[hi])) and abs(v_lat[hi]) > 50)
        out.append({
            "event": "stop",
            "tick": int(g["tick"].iloc[lo]),
            "technique": tech,
            "stop_ms": (lo - hi) / tr * 1000.0,
            "speed_before": float(spd[hi]),
            "speed_after": float(spd[lo]),
            "crouch": int(bool(DK[w].any())),
            "shot_after": int(shot),
            "shot_delay_ms": float(shot_idx[0] / tr * 1000.0) if shot else np.nan,
            "speed_at_shot": float(spd[min(lo + int(shot_idx[0]), n - 1)]) if shot else np.nan,
            "overshoot": int(overshoot),
            "yaw_move_deg": float(np.sum(np.abs(_wrap180(np.diff(yaw[hi:lo + 1]))))) if lo > hi else 0.0,
        })
    return out


def peek_events(g: pd.DataFrame, tr: float = TICKRATE) -> list[dict]:
    spd = g["speed"].to_numpy(float)
    x, y = g["X"].to_numpy(float), g["Y"].to_numpy(float)
    yaw = g["yaw"].to_numpy(float)
    W = g["WALK"].to_numpy(np.int8)
    FIRE = g["FIRE"].to_numpy(np.int8)
    vx, vy = g["velocity_X"].to_numpy(float), g["velocity_Y"].to_numpy(float)
    ry = np.deg2rad(yaw)
    v_lat = vx * (-np.sin(ry)) + vy * np.cos(ry)      # боком відносно погляду
    v_fwd = vx * np.cos(ry) + vy * np.sin(ry)         # уперед відносно погляду
    n = len(spd)

    anchor_min = _ticks(ANCHOR_MIN_MS, tr)
    peek_win, out_win = _ticks(PEEK_WIN_MS, tr), _ticks(OUT_WIN_MS, tr)
    dec = _ticks(DEC_MS, tr, 2)
    still = spd < SPEED_LO
    st, en = _runs(still)
    anchors = [(s, e) for s, e in zip(st, en) if (e - s) >= anchor_min and e < n - 8]

    out = []
    cursor = -1
    for _, e in anchors:
        if e <= cursor:                      # не накладаємо піки один на одний
            continue
        j = min(e + peek_win, n)
        d = np.hypot(x[e:j] - x[e], y[e:j] - y[e])
        if d.size < 8 or d.max() < 20:
            continue
        # вершина = ПЕРШИЙ локальний максимум віддалення (а не глобальний у 5 с):
        # інакше "піком" стає весь маршрут гравця до наступної позиції
        lim = min(out_win, d.size - dec - 1)
        apex = -1
        for i in range(2, max(lim, 3)):
            if d[i] >= d[:i].max() and np.all(d[i + 1:i + 1 + dec] < d[i]) and d[i] > 20:
                apex = i
                break
        if apex < 0:
            apex = int(np.argmax(d[:max(lim, 3)]))
        depth = float(d[apex])
        back = np.flatnonzero(d[apex:] < RETURN_R)
        returned = back.size > 0
        t_end = apex + int(back[0]) if returned else int(d.size - 1)
        seg = slice(e, e + apex + 1)
        if apex < 2:
            continue
        lat_ratio = float(np.mean(np.abs(v_lat[seg])) / (np.mean(np.abs(v_fwd[seg])) + 1.0))
        # рух уперед у напрямку погляду = ротація/забіг, а не пік
        if lat_ratio < LAT_RATIO_MIN or depth > DEPTH_MAX:
            kind = "traversal"
        elif not returned:
            kind = "commit"
        elif depth < DEPTH_JIGGLE:
            kind = "jiggle"
        elif depth > DEPTH_WIDE:
            kind = "wide"
        else:
            kind = "narrow"
        yaw_seg = yaw[seg]
        out.append({
            "event": "peek",
            "tick": int(g["tick"].iloc[e]),
            "kind": kind,
            "depth_u": depth,
            "out_ms": (apex / tr) * 1000.0,
            "total_ms": (t_end / tr) * 1000.0,
            "returned": int(returned),
            "peak_speed": float(spd[seg].max()) if apex > 0 else float(spd[e]),
            "walk_frac": float(W[seg].mean()) if apex > 0 else float(W[e]),
            "yaw_swing_deg": float(np.sum(np.abs(_wrap180(np.diff(yaw_seg))))) if apex > 1 else 0.0,
            "shots": int(np.sum((FIRE[e:e + t_end + 1][1:] == 1) &
                                (FIRE[e:e + t_end + 1][:-1] == 0))),
            "lat_ratio": lat_ratio,
            "shift_peek": int(float(W[seg].mean()) > 0.5),
        })
        cursor = e + t_end
    return out


def build(ticks_path: str, tr: float | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_parquet(ticks_path)
    if tr is None:
        tr = float(df["tickrate"].iloc[0]) if "tickrate" in df.columns else TICKRATE
    demo = Path(ticks_path).stem.replace("_ticks", "")
    rows = []
    # групування за steamid — див. коментар у features.build()
    for (sid, side, rnd), g in df.groupby(["steamid", "side", "round"], sort=True):
        g = g.sort_values("tick")
        secs = len(g) / tr
        if secs < 5:
            continue
        base = {"demo": demo, "player": g["name"].mode().iat[0], "steamid": int(sid),
                "side": side, "round": int(rnd), "secs_alive": secs}
        for ev in stop_events(g, tr) + peek_events(g, tr):
            rows.append({**base, **ev})
    ev_df = pd.DataFrame(rows)

    # --- агрегація до (гравець, сторона, раунд) ---
    agg_rows = []
    for (d, sid, s, r), g in ev_df.groupby(["demo", "steamid", "side", "round"]):
        secs = g["secs_alive"].iloc[0]
        stops = g[g["event"] == "stop"]
        peeks = g[g["event"] == "peek"]
        rec = {"demo": d, "player": g["player"].iloc[0], "steamid": sid,
               "side": s, "round": r}
        rec["stops_per_s"] = len(stops) / secs
        if len(stops):
            tech = stops["technique"].value_counts(normalize=True)
            for t in ("counterstrafe", "counter_fwd", "crouch_stop", "release"):
                rec[f"stop_{t}_frac"] = float(tech.get(t, 0.0))
            rec["stop_ms_mean"] = stops["stop_ms"].mean()
            rec["stop_speed_before"] = stops["speed_before"].mean()
            rec["stop_overshoot_frac"] = stops["overshoot"].mean()
            rec["stop_shot_frac"] = stops["shot_after"].mean()
            rec["stop_shot_delay_ms"] = stops["shot_delay_ms"].mean()
            rec["stop_speed_at_shot"] = stops["speed_at_shot"].mean()
        trav = peeks[peeks["kind"] == "traversal"]
        peeks = peeks[peeks["kind"] != "traversal"]
        rec["traversals_per_s"] = len(trav) / secs
        rec["peeks_per_s"] = len(peeks) / secs
        if len(peeks):
            kind = peeks["kind"].value_counts(normalize=True)
            for k in ("jiggle", "narrow", "wide", "commit"):  # частки типів піків
                rec[f"peek_{k}_frac"] = float(kind.get(k, 0.0))
            rec["peek_depth_mean"] = peeks["depth_u"].mean()
            rec["peek_depth_p90"] = peeks["depth_u"].quantile(0.9)
            rec["peek_out_ms_mean"] = peeks["out_ms"].mean()
            rec["peek_return_frac"] = peeks["returned"].mean()
            rec["peek_peak_speed"] = peeks["peak_speed"].mean()
            rec["peek_walk_frac"] = peeks["walk_frac"].mean()
            rec["peek_yaw_swing"] = peeks["yaw_swing_deg"].mean()
            rec["peek_shots_mean"] = peeks["shots"].mean()
            rec["peek_shift_frac"] = peeks["shift_peek"].mean()
            rec["peek_lat_ratio"] = peeks["lat_ratio"].mean()
            wide = peeks[peeks["kind"] == "wide"]
            rec["wide_peek_per_s"] = len(wide) / secs
            if len(wide):
                rec["wide_depth_mean"] = wide["depth_u"].mean()
                rec["wide_peak_speed"] = wide["peak_speed"].mean()
                rec["wide_return_frac"] = wide["returned"].mean()
        agg_rows.append(rec)
    return ev_df, pd.DataFrame(agg_rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ticks")
    ap.add_argument("--outdir", default="article5_movement/outputs")
    a = ap.parse_args()
    stem = Path(a.ticks).stem.replace("_ticks", "")
    ev, agg = build(a.ticks)
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    ev.to_csv(out / f"{stem}_events.csv", index=False)
    agg.to_csv(out / f"{stem}_event_features.csv", index=False)
    print(f"{len(ev)} подій; стопів={int((ev.event=='stop').sum())}, піків={int((ev.event=='peek').sum())}")
    print(ev[ev.event == "stop"]["technique"].value_counts(normalize=True).round(3).to_string())
    print(ev[ev.event == "peek"]["kind"].value_counts(normalize=True).round(3).to_string())
    print(f"агрегат: {agg.shape[0]} x {agg.shape[1]}")
