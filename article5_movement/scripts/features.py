"""
Крок 2: tick-level parquet -> матриця ознак руху.

Одиниця спостереження = (гравець, сторона, раунд).
Дві родини ознак:
  A. МІКРО (map-agnostic) — механіка керування: контрстрейф, стрейф-перемикання,
     присідання, стрибки, шифт-хода, стоп-перед-вистрілом, динаміка yaw.
     Не залежить від конкретної мапи -> порівнянна між гравцями і мапами.
  B. МАКРО (map-specific) — просторовий слід: довжина шляху, ефективність,
     радіус розсіювання, віддалення від точки старту у часі.

Usage:
    /usr/bin/python3 movement_pattern/features.py <ticks.parquet> [-o feats.csv]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import entropy

TICKRATE = 64.0
CS_WINDOW_MS = 125.0   # мс: максимальна пауза між протилежними стрейф-клавішами
FLICK_DEG_S = 400.0    # порогова кутова швидкість для "флика"
MOVE_EPS = 5.0         # u/s: нижче цього гравець стоїть
WALK_MAX = 135.0       # u/s: верх діапазону шифт-ходи
RUN_MIN = 200.0        # u/s: біг


def _rising(x: np.ndarray) -> int:
    """Кількість фронтів 0->1 у бінарній серії."""
    if len(x) < 2:
        return 0
    return int(np.sum((x[1:] == 1) & (x[:-1] == 0)))


def _counterstrafes(lateral: np.ndarray, window: int) -> int:
    """
    Контрстрейф = зміна знаку бокової клавіші (A<->D) з паузою <= window тіків.
    lateral: -1 (left), 0, +1 (right) для кожного тіка.
    """
    nz = np.flatnonzero(lateral != 0)
    if nz.size < 2:
        return 0
    vals = lateral[nz]
    gaps = np.diff(nz)
    flips = (vals[1:] != vals[:-1]) & (gaps <= window)
    return int(np.sum(flips))


def _sign_changes(v: np.ndarray, thresh: float) -> int:
    """Кількість реверсів знаку сигналу (за модулем > thresh) — проксі jiggle/peek."""
    s = np.sign(np.where(np.abs(v) > thresh, v, 0.0))
    nz = s[s != 0]
    if nz.size < 2:
        return 0
    return int(np.sum(nz[1:] != nz[:-1]))


def _runs(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Індекси початку/кінця (виключно) неперервних послідовностей одиниць."""
    d = np.diff(np.concatenate(([0], (x > 0).astype(np.int8), [0])))
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1)


def _dwell_ms(x: np.ndarray, tickrate: float) -> tuple[float, float, int]:
    """Тривалість утримання клавіші (dwell time) — мс: середня, медіана, к-ть натискань."""
    st, en = _runs(x)
    if st.size == 0:
        return np.nan, np.nan, 0
    dur = (en - st) / tickrate * 1000.0
    return float(dur.mean()), float(np.median(dur)), int(st.size)


FLIGHT_WIN_MS = 500.0  # мс: у цьому вікні шукаємо парне натискання


def _flight_ms(a: np.ndarray, b: np.ndarray, tickrate: float,
               window_ticks: int | None = None) -> tuple[float, float]:
    """
    Латентність переходу клавіша A -> клавіша B (flight time), мс.
    Від'ємне значення = перекриття (B натиснуто до відпускання A) —
    саме так виглядає технічний контрстрейф.
    Повертає (середня латентність, частка перекриттів).
    """
    if window_ticks is None:
        window_ticks = max(1, int(round(FLIGHT_WIN_MS / 1000.0 * tickrate)))
    _, a_end = _runs(a)
    b_start, _ = _runs(b)
    if a_end.size == 0 or b_start.size == 0:
        return np.nan, np.nan
    lat, overlap = [], 0
    for e in a_end:
        nxt = b_start[(b_start >= e - window_ticks) & (b_start <= e + window_ticks)]
        if nxt.size == 0:
            continue
        j = nxt[np.argmin(np.abs(nxt - e))]
        lat.append((j - e) / tickrate * 1000.0)
        if j < e:
            overlap += 1
    if not lat:
        return np.nan, np.nan
    return float(np.mean(lat)), float(overlap / len(lat))


KNIFE_TOKENS = ("Knife", "Bayonet", "Karambit", "Daggers", "Talon", "Ursus",
                "Navaja", "Stiletto", "Nomad", "Skeleton", "Butterfly", "Falchion",
                "Huntsman", "Paracord", "Survival", "Classic", "Kukri", "Bowie",
                "Gut", "Flip", "Shadow")
NADE_TOKENS = ("Grenade", "Flashbang", "Smoke", "Molotov", "Incendiary", "Decoy")
PISTOLS = {"Glock-18", "USP-S", "P2000", "P250", "Five-SeveN", "Tec-9", "CZ75-Auto",
           "Desert Eagle", "Dual Berettas", "R8 Revolver"}
SNIPERS = {"AWP", "SSG 08", "SCAR-20", "G3SG1"}


def _weapon_class(name: str) -> str:
    if not isinstance(name, str) or not name:
        return "none"
    if any(tok in name for tok in KNIFE_TOKENS):
        return "knife"
    if any(tok in name for tok in NADE_TOKENS):
        return "nade"
    if name in PISTOLS:
        return "pistol"
    if name in SNIPERS:
        return "sniper"
    if "C4" in name or "Bomb" in name:
        return "c4"
    return "primary"


def habit_features(g: pd.DataFrame, spd: np.ndarray, secs: float,
                   tickrate: float) -> dict:
    """
    Ідіосинкразії обігу зі зброєю: перемикання, біг з ножем, Q-switch,
    перезарядка «про запас», тумблери глушника й приціла.

    Тактичного сенсу в цих діях мало, тому вони — добрі кандидати на
    індивідуальний підпис (аналог habitual gestures у поведінковій біометрії).
    ОГЛЯД ЗБРОЇ (F) виміряти неможливо: поля m_bIsLookingAtWeapon немає ні в
    GOTV-, ні у FACEIT-демках.
    """
    out: dict[str, float] = {}
    wn = g["active_weapon_name"].astype(str).to_numpy() if "active_weapon_name" in g else None
    if wn is None or len(wn) < 2:
        return out
    cls = np.array([_weapon_class(w) for w in wn])
    for c in ("knife", "pistol", "primary", "sniper", "nade"):
        out[f"wpn_{c}_frac"] = float(np.mean(cls == c))
    out["knife_run_frac"] = float(np.mean((cls == "knife") & (spd > 150)))
    out["nade_walk_frac"] = float(np.mean((cls == "nade") & (spd > 10)))

    chg = np.flatnonzero(wn[1:] != wn[:-1]) + 1
    out["switch_per_s"] = len(chg) / secs
    # Q-switch: пішов зі зброї і повернувся на неї протягом <=1 с
    win = int(tickrate)
    q = 0
    for i in chg:
        prev = wn[i - 1]
        back = np.flatnonzero(wn[i:i + win] == prev)
        if back.size:
            q += 1
    out["qswitch_per_s"] = q / secs

    if "is_in_reload" in g:
        rl = g["is_in_reload"].to_numpy(np.int8)
        starts = np.flatnonzero((rl[1:] == 1) & (rl[:-1] == 0)) + 1
        out["reload_per_s"] = len(starts) / secs
        if "active_weapon_ammo" in g and starts.size:
            ammo = g["active_weapon_ammo"].to_numpy(float)
            # запас патронів на початку перезарядки відносно максимуму для цієї зброї
            ratio = []
            for i in starts:
                w = wn[i]
                mx = np.nanmax(ammo[wn == w]) if np.any(wn == w) else np.nan
                if np.isfinite(mx) and mx > 0:
                    ratio.append(ammo[i] / mx)
            if ratio:
                out["reload_ammo_ratio"] = float(np.mean(ratio))

    if "is_silencer_on" in g:
        sil = g["is_silencer_on"].to_numpy(np.int8)
        out["silencer_toggle_per_s"] = float(np.sum(sil[1:] != sil[:-1]) / secs)
    if "zoom_lvl" in g:
        z = g["zoom_lvl"].to_numpy(np.int8)
        out["zoom_toggle_per_s"] = float(np.sum(z[1:] != z[:-1]) / secs)
        sniper = cls == "sniper"
        out["sniper_zoom_frac"] = float(np.mean(z[sniper] > 0)) if sniper.any() else np.nan
    return out


COMBO_NAMES = {
    0: "none", 1: "W", 2: "S", 3: "WS", 4: "A", 5: "WA", 6: "SA", 7: "WSA",
    8: "D", 9: "WD", 10: "SD", 11: "WSD", 12: "AD", 13: "WAD", 14: "SAD", 15: "WSAD",
}
COMBO_KEEP = ["none", "W", "S", "A", "D", "WA", "WD", "SA", "SD", "AD"]


def _wrap180(d: np.ndarray) -> np.ndarray:
    return (d + 180.0) % 360.0 - 180.0


def round_features(g: pd.DataFrame, tickrate: float = TICKRATE) -> dict | None:
    g = g.sort_values("tick")
    n = len(g)
    if n < int(5 * tickrate):          # < 5 c живого часу — пропускаємо
        return None

    secs = n / tickrate
    spd = g["speed"].to_numpy(dtype=float)
    x, y, z = (g[c].to_numpy(dtype=float) for c in ("X", "Y", "Z"))
    yaw = g["yaw"].to_numpy(dtype=float)
    vx, vy = g["velocity_X"].to_numpy(dtype=float), g["velocity_Y"].to_numpy(dtype=float)

    F = g["FORWARD"].to_numpy(dtype=np.int8)
    B = g["BACK"].to_numpy(dtype=np.int8)
    L = g["LEFT"].to_numpy(dtype=np.int8)
    R = g["RIGHT"].to_numpy(dtype=np.int8)
    J = g["JUMP"].to_numpy(dtype=np.int8)
    D = g["DUCK"].to_numpy(dtype=np.int8)
    W = g["WALK"].to_numpy(dtype=np.int8)
    FIRE = g["FIRE"].to_numpy(dtype=np.int8)
    air = g["is_airborne"].to_numpy(dtype=np.int8)
    duck_amt = g["duck_amount"].to_numpy(dtype=float)
    scoped = g["is_scoped"].to_numpy(dtype=np.int8)

    # --- A. МІКРО: механіка керування ---
    lateral = (R.astype(int) - L.astype(int))
    combo = F * 1 + B * 2 + L * 4 + R * 8                    # 16 станів клавіш
    cnt = np.bincount(combo, minlength=16).astype(float)
    key_entropy = float(entropy(cnt / cnt.sum(), base=2))

    dyaw = np.abs(_wrap180(np.diff(yaw))) * tickrate         # град/с
    # бокова складова швидкості відносно напрямку погляду
    ry = np.deg2rad(yaw)
    v_lat = vx * (-np.sin(ry)) + vy * np.cos(ry)
    v_fwd = vx * np.cos(ry) + vy * np.sin(ry)

    fire_edges = np.flatnonzero((FIRE[1:] == 1) & (FIRE[:-1] == 0)) + 1
    spd_at_fire = float(np.mean(spd[fire_edges])) if fire_edges.size else np.nan
    moving_shots = float(np.mean(spd[fire_edges] > 60)) if fire_edges.size else np.nan

    dspd = np.diff(spd) * tickrate

    # --- A2. КЛАВІАТУРНА ДИНАМІКА (аналог keystroke dynamics) ---
    keys = {"W": F, "S": B, "A": L, "D": R, "SHIFT": W, "CTRL": D, "SPACE": J}
    kd: dict[str, float] = {}
    total_presses = 0
    for kname, arr in keys.items():
        m, med, cnt = _dwell_ms(arr, tickrate)
        kd[f"dwell_{kname}_ms"] = m
        kd[f"presses_{kname}_per_s"] = cnt / secs
        total_presses += cnt
    kd["presses_total_per_s"] = total_presses / secs

    lat_ad, ovl_ad = _flight_ms(L, R, tickrate)
    lat_da, ovl_da = _flight_ms(R, L, tickrate)
    lats = [v for v in (lat_ad, lat_da) if not np.isnan(v)]
    ovls = [v for v in (ovl_ad, ovl_da) if not np.isnan(v)]
    kd["strafe_flight_ms"] = float(np.mean(lats)) if lats else np.nan
    kd["strafe_overlap_frac"] = float(np.mean(ovls)) if ovls else np.nan

    # розподіл комбінацій WASD + матриця переходів (марковська персистентність)
    counts = np.bincount(combo, minlength=16).astype(float)
    frac = counts / counts.sum()
    for idx, nm in COMBO_NAMES.items():
        if nm in COMBO_KEEP:
            kd[f"combo_{nm}"] = float(frac[idx])
    trans = np.zeros((16, 16))
    np.add.at(trans, (combo[:-1], combo[1:]), 1.0)
    rowsum = trans.sum(axis=1, keepdims=True)
    P = np.divide(trans, rowsum, out=np.zeros_like(trans), where=rowsum > 0)
    stay = np.array([P[i, i] for i in range(16) if rowsum[i, 0] > 0])
    kd["combo_persistence"] = float(stay.mean()) if stay.size else np.nan
    with np.errstate(divide="ignore", invalid="ignore"):
        rowent = np.array([entropy(P[i][P[i] > 0], base=2)
                           for i in range(16) if rowsum[i, 0] > 0])
    kd["combo_trans_entropy"] = float(rowent.mean()) if rowent.size else np.nan
    kd["combo_switch_per_s"] = float(np.sum(combo[1:] != combo[:-1]) / secs)

    # --- B. МАКРО: просторовий слід ---
    step = np.hypot(np.diff(x), np.diff(y))
    path_len = float(step.sum())
    net_disp = float(np.hypot(x[-1] - x[0], y[-1] - y[0]))
    d_from_start = np.hypot(x - x[0], y - y[0])
    rg = float(np.sqrt(np.mean((x - x.mean()) ** 2 + (y - y.mean()) ** 2)))

    def disp_at(t: float) -> float:
        i = int(t * tickrate)
        return float(d_from_start[i]) if i < n else np.nan

    out = {
        "player": g["name"].mode().iat[0],
        "steamid": int(g["steamid"].iloc[0]),
        "side": g["side"].iloc[0],
        "round": int(g["round"].iloc[0]),
        "secs_alive": round(secs, 2),
        # мікро: розподіл швидкості
        "speed_mean": spd.mean(),
        "speed_std": spd.std(),
        "speed_p90": np.percentile(spd, 90),
        "frac_still": float(np.mean(spd < MOVE_EPS)),
        "frac_walkkey": float(W.mean()),
        "frac_slowmove": float(np.mean((spd >= MOVE_EPS) & (spd < WALK_MAX))),
        "frac_run": float(np.mean(spd >= RUN_MIN)),
        "accel_std": float(np.std(dspd)),
        # мікро: клавіші
        "counterstrafe_per_s": _counterstrafes(
            lateral, max(1, int(round(CS_WINDOW_MS / 1000.0 * tickrate)))) / secs,
        "strafe_switch_per_s": (_rising(L) + _rising(R)) / secs,
        "fwd_switch_per_s": (_rising(F) + _rising(B)) / secs,
        "diag_frac": float(np.mean(((F | B) == 1) & ((L | R) == 1))),
        "key_entropy": key_entropy,
        "jump_per_s": _rising(J) / secs,
        "frac_air": float(air.mean()),
        "duck_per_s": _rising(D) / secs,
        "frac_ducked": float(np.mean(duck_amt > 0.5)),
        "crouchwalk_frac": float(np.mean((duck_amt > 0.5) & (spd > 10))),
        # мікро: погляд і мікро-пікі
        "yaw_rate_mean": float(np.mean(dyaw)),
        "yaw_rate_p95": float(np.percentile(dyaw, 95)),
        "flick_per_s": float(np.sum(dyaw > FLICK_DEG_S) / secs),
        "lat_reversal_per_s": _sign_changes(v_lat, 50.0) / secs,
        "lat_speed_frac": float(np.mean(np.abs(v_lat) > np.abs(v_fwd))),
        "frac_scoped": float(scoped.mean()),
        # мікро: дисциплина стрільби
        "speed_at_fire": spd_at_fire,
        "moving_shot_frac": moving_shots,
        "shots_per_s": float(len(fire_edges) / secs),
        # макро: просторовий слід
        "path_len": path_len,
        "path_per_s": path_len / secs,
        "path_efficiency": net_disp / path_len if path_len > 1 else np.nan,
        "radius_gyration": rg,
        "max_dist_start": float(d_from_start.max()),
        "disp_10s": disp_at(10),
        "disp_20s": disp_at(20),
        "z_range": float(z.max() - z.min()),
    }
    out.update(kd)
    out.update(habit_features(g, spd, secs, tickrate))
    return out


def build(ticks_path: str, tickrate: float | None = None) -> pd.DataFrame:
    df = pd.read_parquet(ticks_path)
    if tickrate is None:
        tickrate = (float(df["tickrate"].iloc[0]) if "tickrate" in df.columns
                    else TICKRATE)
    rows = []
    # групуємо за steamid, а не за ніком: один гравець може писати нік
    # по-різному в різних матчах (electroNic / electronic, Mzinho / mzinho)
    for (sid, side, rnd), g in df.groupby(["steamid", "side", "round"], sort=True):
        f = round_features(g, tickrate)
        if f:
            f["demo"] = Path(ticks_path).stem.replace("_ticks", "")
            rows.append(f)
    out = pd.DataFrame(rows)
    lead = ["demo", "player", "steamid", "side", "round", "secs_alive"]
    return out[lead + [c for c in out.columns if c not in lead]]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ticks")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--tickrate", type=float, default=None,
                    help="за замовчуванням береться з parquet")
    a = ap.parse_args()

    out = a.output or f"article5_movement/outputs/{Path(a.ticks).stem.replace('_ticks','')}_features.csv"
    feats = build(a.ticks, a.tickrate)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    feats.to_csv(out, index=False)
    print(f"{len(feats)} observations x {feats.shape[1]-5} features")
    print(feats.groupby(["player", "side"]).size().to_string())
    print("saved", out)
