"""
Крок 1: демка (.dem) -> tick-level parquet з рухом усіх гравців.

ВАЖЛИВО про співставність джерел. Різні демки віддають різний набір полів:
  - FACEIT-демки мають сиру маску `buttons`, але не мають m_nLastJumpTick;
  - офіційні GOTV-демки (ESL/HLTV) не мають ні `buttons`, ні `velocity_*`;
  - `velocity_*` у demoparser2 0.42 не віддається взагалі.
Тому всі сигнали обчислюються з **спільного знаменника**, однаково для будь-якої
демки — інакше профілі гравців з різних джерел непорівнянні:

  клавіші W/S/A/D, ЛКМ, ПКМ  <- іменовані пропи FORWARD/BACK/LEFT/RIGHT/FIRE/RIGHTCLICK
  SHIFT (тиха хода)          <- is_walking
  CTRL (присід)              <- duck_amount > 0.1   (стан, не натискання)
  SPACE (стрибок)            <- відрив від землі з піком vz > JUMP_VZ (відсікає уступи)
  швидкість                  <- різниця позицій зі зсувом 1 тік

Підміна швидкості перевірена на демці, де є нативний velocity: Pearson 0.9998,
MAE 0.01 u/s після відсіву телепортів (>400 u/s). Проксі для SPACE/CTRL/SHIFT
перевіряються скриптом validate_signals.py на демках із нативною маскою кнопок.

Usage:
    /usr/bin/python3 article5_movement/scripts/extract_ticks.py <demo.dem> [-o out.parquet]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from demoparser2 import DemoParser

CORE = ["X", "Y", "Z", "yaw", "pitch", "is_alive", "team_num",
        "total_rounds_played", "is_freeze_period", "is_warmup_period", "game_time"]
KEYS = ["FORWARD", "BACK", "LEFT", "RIGHT", "FIRE", "RIGHTCLICK"]
STATE = ["is_walking", "duck_amount", "is_airborne", "is_scoped", "shots_fired",
         "health", "active_weapon_name", "active_weapon_ammo", "is_in_reload",
         "is_silencer_on", "zoom_lvl"]
# СВІДОМО НЕ БЕРЕМО: weapon_float, weapon_paint_seed, item_def_idx — це параметри
# скінів. Вони ідентифікують інвентар гравця тривіально й не є поведінкою;
# їхнє включення зробило б задачу ідентифікації беззмістовною.
OPTIONAL = ["buttons", "velocity_X", "velocity_Y", "velocity_Z"]

TEAM = {2: "T", 3: "CT"}
VEL_MAX = 400.0        # u/s — вище цього це телепорт/розрив тіків, не рух
JUMP_VZ = 200.0        # u/s — імпульс стрибка в CS2 ~301 u/s; уступ/падіння дає <=0
JUMP_WIN_MS = 62.5     # мс: у цьому вікні після відриву шукаємо пік vz

# Біти маски `buttons` (лише для валідації, коли маска є).
BUTTON_BITS = {"FIRE": 0, "JUMP": 1, "DUCK": 2, "FORWARD": 3, "BACK": 4,
               "LEFT": 9, "RIGHT": 10, "RIGHTCLICK": 11, "WALK": 16}


# Тіки для проби наявності пропів. Кілька масштабів навмисно: демка,
# розрізана технічною паузою, буває коротшою за 100k тіків (26 хв), і проба
# лише на 100000 потрапляла в порожнечу -> скрипт вирішував, що демка не
# віддає ЖОДНОГО пропа, і падав на цілком справних даних.
PROBE_TICKS = [100000, 100001, 50000, 20000, 5000, 2000, 500, 200, 100]


def _available(parser: DemoParser, props: list[str]) -> list[str]:
    """Які пропи демка реально віддає (проба на тіках різного масштабу)."""
    try:
        cols = set(parser.parse_ticks(props, ticks=PROBE_TICKS).columns)
    except Exception:
        cols = set()
        for p in props:
            try:
                cols |= set(parser.parse_ticks([p], ticks=PROBE_TICKS).columns)
            except Exception:
                pass
    return [p for p in props if p in cols]


def _derive_velocity(df: pd.DataFrame, tickrate: float) -> pd.DataFrame:
    """Швидкість із різниці позицій. vel(t) = (pos(t-1) - pos(t-2)) * tickrate."""
    g = df.groupby(["steamid", "round"], sort=False)
    for axis in ("X", "Y", "Z"):
        step = g[axis].diff() * tickrate
        df[f"velocity_{axis}"] = step.groupby([df["steamid"], df["round"]]).shift(1)
    bad = (df[["velocity_X", "velocity_Y", "velocity_Z"]].abs() > VEL_MAX).any(axis=1)
    df.loc[bad, ["velocity_X", "velocity_Y", "velocity_Z"]] = np.nan
    df[["velocity_X", "velocity_Y", "velocity_Z"]] = (
        df.groupby(["steamid", "round"], sort=False)[["velocity_X", "velocity_Y", "velocity_Z"]]
        .transform(lambda s: s.ffill().bfill().fillna(0.0)))
    df["speed"] = np.hypot(df["velocity_X"], df["velocity_Y"])
    return df


def _derive_jump(df: pd.DataFrame, tickrate: float = 64.0) -> pd.Series:
    """
    Стрибок = відрив від землі з імпульсом угору.

    Фронт is_airborne сам по собі не годиться: 18% таких фронтів — це сходинки
    й падіння з уступів. Розрізняє їх вертикальна швидкість. Через зсув
    швидкості на 1 тік на самому тіку відриву vz ще нульова, тому беремо
    максимум vz у вікні JUMP_WIN тіків після відриву.

    Нативна маска кнопок для стрибків НЕ є надійним ground truth: у CS2
    subtick-натискання коротше за тік у маску не потрапляє, тому маска бачить
    лише 33% реальних стрибків. Зате 99.2% натискань з маски покриваються цим
    визначенням — тобто маска є його підмножиною.
    """
    air = df["is_airborne"].astype(np.int8)
    prev = air.groupby([df["steamid"], df["round"]], sort=False).shift(1).fillna(0)
    onset = (air == 1) & (prev == 0)
    win = max(2, int(round(JUMP_WIN_MS / 1000.0 * tickrate)))
    fwd_max = (df.groupby(["steamid", "round"], sort=False)["velocity_Z"]
               .transform(lambda s: s[::-1].rolling(win, min_periods=1).max()[::-1]))
    return (onset & (fwd_max > JUMP_VZ)).astype(np.int8)


def extract(demo_path: str) -> tuple[pd.DataFrame, dict]:
    parser = DemoParser(demo_path)
    header = parser.parse_header()
    have = _available(parser, CORE + KEYS + STATE + OPTIONAL)
    missing_core = [p for p in CORE if p not in have]
    if missing_core:
        raise RuntimeError(f"демка не віддає обов'язкові пропи: {missing_core}")

    df = parser.parse_ticks(have)
    meta = {
        "demo": Path(demo_path).name,
        "map": header.get("map_name", "?"),
        "server": header.get("server_name", "?"),
        "patch": header.get("patch_version", "?"),
        "raw_rows": len(df),
        "props_available": have,
        "props_missing": [p for p in CORE + KEYS + STATE + OPTIONAL if p not in have],
    }

    df = df[(df["is_warmup_period"] != True) & (df["is_freeze_period"] != True)]
    df = df[df["is_alive"] == True]
    df = df[df["team_num"].isin([2, 3])]
    df = df.dropna(subset=["X", "Y", "Z"])

    g = df.groupby("tick")["game_time"].first().sort_index()
    dt, dtick = np.diff(g.values), np.diff(g.index.values)
    ok = (dtick > 0) & (dt > 0)
    tickrate = float(np.round(np.median(dtick[ok] / dt[ok]))) if ok.any() else 64.0
    meta["tickrate"] = tickrate

    # тікрейт їде разом із даними: усі вікна детекторів залежать від нього,
    # а FACEIT/сторонні демки можуть бути не 64-тіковими
    df["tickrate"] = np.float32(tickrate)
    df["side"] = df["team_num"].map(TEAM)
    df["round"] = df["total_rounds_played"].astype("int16")
    df = df.sort_values(["steamid", "round", "tick"])

    # --- канонічні сигнали ---
    src: dict[str, str] = {}
    df = _derive_velocity(df, tickrate)
    src["velocity"] = "різниця позицій (зсув 1 тік)"

    if "buttons" in have:
        btn = df["buttons"].fillna(0).astype("uint64").to_numpy()
        for name, bit in BUTTON_BITS.items():
            df[f"native_{name}"] = ((btn >> np.uint64(bit)) & np.uint64(1)).astype("int8")

    for k in KEYS:
        if k in have:
            df[k] = df[k].fillna(False).astype("int8")
            src[k] = "нативний проп"
        elif "buttons" in have:
            df[k] = df[f"native_{k}"]
            src[k] = "маска buttons"
        else:
            df[k] = np.int8(0)
            src[k] = "НЕДОСТУПНО (нулі)"

    df["WALK"] = (df["is_walking"].fillna(False).astype("int8") if "is_walking" in have
                  else np.int8(0))
    src["WALK"] = "is_walking" if "is_walking" in have else "НЕДОСТУПНО"

    df["DUCK"] = ((df["duck_amount"].fillna(0) > 0.1).astype("int8") if "duck_amount" in have
                  else np.int8(0))
    src["DUCK"] = "duck_amount > 0.1 (стан)" if "duck_amount" in have else "НЕДОСТУПНО"

    if "is_airborne" in have:
        df["is_airborne"] = df["is_airborne"].fillna(False).astype("int8")
        df["JUMP"] = _derive_jump(df, tickrate)
        src["JUMP"] = f"відрив із піком vz > {JUMP_VZ} у {JUMP_WIN_MS} мс"
    else:
        df["is_airborne"] = np.int8(0)
        df["JUMP"] = np.int8(0)
        src["JUMP"] = "НЕДОСТУПНО"

    for c, default in (("duck_amount", 0.0), ("is_scoped", 0), ("shots_fired", 0.0),
                       ("health", 100.0)):
        if c not in df.columns:
            df[c] = default
    df["is_scoped"] = df["is_scoped"].fillna(False).astype("int8")
    meta["signal_sources"] = src

    for c, default in (("active_weapon_name", ""), ("active_weapon_ammo", np.nan),
                       ("is_in_reload", 0), ("is_silencer_on", 0), ("zoom_lvl", 0.0)):
        if c not in df.columns:
            df[c] = default
    df["is_in_reload"] = df["is_in_reload"].fillna(False).astype("int8")
    df["is_silencer_on"] = df["is_silencer_on"].fillna(False).astype("int8")
    df["zoom_lvl"] = df["zoom_lvl"].fillna(0).astype("int8")

    keep = ["tick", "round", "name", "steamid", "side", "tickrate",
            "X", "Y", "Z", "velocity_X", "velocity_Y", "velocity_Z", "speed",
            "yaw", "pitch", "FORWARD", "BACK", "LEFT", "RIGHT", "JUMP", "DUCK",
            "WALK", "FIRE", "RIGHTCLICK", "is_airborne", "duck_amount",
            "is_scoped", "shots_fired", "health",
            "active_weapon_name", "active_weapon_ammo", "is_in_reload",
            "is_silencer_on", "zoom_lvl"]
    keep += [c for c in df.columns if c.startswith("native_")]
    df = df[[c for c in keep if c in df.columns]].sort_values(["name", "round", "tick"])

    for c in df.columns:
        if df[c].dtype == "float64":
            df[c] = df[c].astype("float32")
        elif df[c].dtype == "bool":
            df[c] = df[c].astype("int8")

    meta["kept_rows"] = len(df)
    meta["players"] = sorted(df["name"].unique().tolist())
    meta["rounds"] = int(df["round"].max()) + 1
    return df, meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("demo")
    ap.add_argument("-o", "--output", default=None)
    a = ap.parse_args()

    out = a.output or f"article5_movement/data/processed/{Path(a.demo).stem}_ticks.parquet"
    df, meta = extract(a.demo)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)

    # шлях від розташування скрипта, не від CWD: інакше запуск із іншої
    # теки створює вкладену article5_movement/article5_movement/...
    log = (Path(__file__).resolve().parent.parent / "outputs" / "logs"
           / f"{Path(a.demo).stem}_signals.json")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    print(f"map={meta['map']}  patch={meta['patch']}  tickrate={meta['tickrate']}  "
          f"rounds={meta['rounds']}")
    print(f"rows: {meta['raw_rows']} -> {meta['kept_rows']}")
    print("немає пропів:", meta["props_missing"])
    print("джерела сигналів:", json.dumps(meta["signal_sources"], ensure_ascii=False))
    print("players:", ", ".join(meta["players"]))
    print("saved", out, "| лог", log)
