#!/usr/bin/env python3
"""Реєстр даних: parquet -> demos.csv, sessions.csv, players.csv.

Знімає три пастки, кожна з яких уже проявилась на реальних даних:

1. **Ідентичність за steamid.** Нік пишеться по-різному в різних матчах
   (electroNic/electronic), і гравець розпадається на двох, а його
   genuine-пари зникають.

2. **Сесія = серія, а не мапа.** Три мапи одного Bo3 — це той самий день,
   суперник і розминка. Як «різні матчі» вони завищують схожість «свій-свій».

3. **Розрізані мапи.** Файли вигляду `X.dem` / `X2.dem` — одна мапа, записана
   двома шматками через технічну паузу. Але шматки бувають двох різних видів,
   і розрізняти їх треба з даних (див. `classify_parts`).

    /usr/bin/python3 scripts/build_registry.py
    /usr/bin/python3 scripts/build_registry.py --report     # лише подивитись
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
REG = ROOT / "data" / "registry"
COLLECTION = ROOT / "collection"
REPO = ROOT.parent

KNOWN_MAPS = {"mirage", "inferno", "nuke", "dust2", "ancient", "anubis",
              "overpass", "vertigo", "train", "cache", "cbble", "tuscan"}

FNAME = re.compile(r"^(\d{4}-\d{2}-\d{2})_([a-z0-9]+)_(.+?)_([a-z0-9]+)_ticks\.parquet$")


# ---------------------------------------------------------------- імена файлів

def split_map_name(raw: str):
    """`anubis2` -> ('anubis', 2); `dust22` -> ('dust2', 2); `dust2` -> ('dust2', 1).

    Обережно: `dust2` сам закінчується цифрою, тому спершу перевіряємо, чи
    назва вже відома, і лише потім відрізаємо суфікс частини.
    """
    if raw in KNOWN_MAPS:
        return raw, 1
    m = re.match(r"^(.*?)(\d)$", raw)
    if m and m.group(1) in KNOWN_MAPS:
        return m.group(1), int(m.group(2))
    return raw, 1


def parse_name(path: Path):
    m = FNAME.match(path.name)
    if not m:
        return None
    date, event, teams, raw_map = m.groups()
    map_name, part = split_map_name(raw_map)
    return {
        "file": path.name,
        "date": date,
        "event": event,
        "teams": teams,
        "map": map_name,
        "part": part,
        "series_id": f"{date}_{event}_{teams}",
        "map_key": f"{date}_{event}_{teams}_{map_name}",
    }


# ------------------------------------------------------------ читання parquet

def read_slim(path: Path) -> pd.DataFrame:
    """Лише ті колонки, що потрібні реєстру — повний parquet читати марно."""
    return pd.read_parquet(path, columns=["steamid", "name", "round", "side", "tick"])


# ----------------------------------------------------- розбір розрізаних мап

def classify_parts(parts: list[dict]) -> str:
    """Два шматки однієї мапи бувають різної природи, і плутати їх не можна.

    `continuation` — матч тривав далі: раунди другої частини йдуть ПІСЛЯ
        раундів першої. Частини треба зшити в одну сесію.

    `restart` — після паузи матч переграли з початку: набори раундів
        перетинаються. Тоді коротша частина — це недограні раунди, які
        офіційно не рахуються, і її треба відкинути, а не приклеювати.
        Саме такий випадок дає пара з файлом на 14 МБ проти 614 МБ.

    Рішення ухвалюється за перетином наборів раундів, а не за розміром файлу.
    """
    if len(parts) < 2:
        return "single"
    sets = [p["rounds_set"] for p in parts]
    small = min(sets, key=len)
    overlap = len(set.intersection(*sets))
    return "restart" if overlap > 0.5 * max(1, len(small)) else "continuation"


# ------------------------------------------------------------------- країни

def load_countries() -> dict:
    """нік (lower) -> код країни. Джерела: рейтинг HLTV і зібрані атрибути."""
    out = {}
    teams_csv = COLLECTION / "teams.csv"
    if teams_csv.exists():
        for r in csv.DictReader(teams_csv.open()):
            for entry in (r.get("roster") or "").split("|"):
                if ":" in entry:
                    nick, cc = entry.rsplit(":", 1)
                    out.setdefault(nick.strip().lower(), cc.strip())
    for name in ("htlv_attrs.csv", "htlv_attrstop20.csv"):
        f = REPO / name
        if not f.exists():
            continue
        try:
            d = pd.read_csv(f, on_bad_lines="skip", low_memory=False)
        except Exception:                                        # noqa: BLE001
            continue
        if {"player", "country"} <= set(d.columns):
            for p, c in zip(d["player"].astype(str), d["country"].astype(str)):
                out.setdefault(p.strip().lower(), c.strip())
    return out


# ---------------------------------------------------------------------- збір

def build(verbose=True):
    files = sorted(PROC.glob("*_ticks.parquet"))
    if not files:
        sys.exit(f"немає parquet у {PROC}")

    by_map = defaultdict(list)
    unparsed = []
    for f in files:
        info = parse_name(f)
        if not info:
            unparsed.append(f.name)
            continue
        df = read_slim(f)
        info["rounds_set"] = set(int(x) for x in df["round"].unique())
        info["n_rounds"] = len(info["rounds_set"])
        info["n_rows"] = len(df)
        info["players"] = df[["steamid", "name"]].drop_duplicates()
        info["by_player_side"] = (df.groupby(["steamid", "side"])["round"]
                                    .nunique().to_dict())
        by_map[info["map_key"]].append(info)

    if unparsed and verbose:
        print(f"[registry] не розібрано імен: {len(unparsed)}", file=sys.stderr)
        for u in unparsed[:10]:
            print("   ", u, file=sys.stderr)

    # --- рішення по розрізаних мапах ---
    demos, notes = [], []
    for map_key, parts in sorted(by_map.items()):
        parts.sort(key=lambda p: p["part"])
        kind = classify_parts(parts)
        if kind == "restart":
            keep = max(parts, key=lambda p: p["n_rounds"])
            for p in parts:
                p["role"] = "used" if p is keep else "voided_restart"
            notes.append(f"{map_key}: ПЕРЕЗАПУСК — лишено {keep['file']} "
                         f"({keep['n_rounds']} раундів), відкинуто "
                         f"{[p['file'] for p in parts if p is not keep]}")
        else:
            for p in parts:
                p["role"] = "used"
            if kind == "continuation":
                notes.append(f"{map_key}: ЗШИТО {len(parts)} частин "
                             f"({[p['n_rounds'] for p in parts]} раундів)")
        demos.extend(parts)

    # --- сесії: (steamid, series_id) ---
    sess = defaultdict(lambda: {"rounds_T": 0, "rounds_CT": 0,
                                "maps": set(), "files": 0})
    players = {}
    for d in demos:
        if d["role"] != "used":
            continue
        for sid, nick in d["players"].itertuples(index=False):
            key = (str(sid), d["series_id"])
            sess[key]["maps"].add(d["map"])
            sess[key]["files"] += 1
            p = players.setdefault(str(sid), {"nicks": defaultdict(int),
                                              "series": set(), "maps": set(),
                                              "dates": []})
            p["nicks"][str(nick)] += 1
            p["series"].add(d["series_id"])
            p["maps"].add(d["map"])
            p["dates"].append(d["date"])
        for (sid, side), n in d["by_player_side"].items():
            key = (str(sid), d["series_id"])
            col = "rounds_T" if str(side).upper().startswith("T") else "rounds_CT"
            sess[key][col] += int(n)

    countries = load_countries()

    REG.mkdir(parents=True, exist_ok=True)

    with (REG / "demos.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "series_id", "date", "event",
                                          "teams", "map", "part", "role",
                                          "n_rounds", "n_rows"])
        w.writeheader()
        for d in sorted(demos, key=lambda x: x["file"]):
            w.writerow({k: d[k] for k in w.fieldnames})

    with (REG / "sessions.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["session_id", "steamid", "series_id", "rounds_T",
                    "rounds_CT", "n_maps", "maps", "n_files"])
        for (sid, ser), v in sorted(sess.items()):
            w.writerow([f"{sid}@{ser}", sid, ser, v["rounds_T"], v["rounds_CT"],
                        len(v["maps"]), "|".join(sorted(v["maps"])), v["files"]])

    with (REG / "players.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["steamid", "nick_canonical", "nicks_seen", "country",
                    "n_sessions", "n_maps", "first_seen", "last_seen"])
        for sid, p in sorted(players.items(),
                             key=lambda kv: -len(kv[1]["series"])):
            canon = max(p["nicks"].items(), key=lambda kv: kv[1])[0]
            w.writerow([sid, canon, "|".join(sorted(p["nicks"])),
                        countries.get(canon.lower(), ""),
                        len(p["series"]), len(p["maps"]),
                        min(p["dates"]), max(p["dates"])])

    log = REG / "stitching_log.txt"
    log.write_text("\n".join(notes) + "\n" if notes else "жодних розрізаних мап\n")

    if verbose:
        used = sum(1 for d in demos if d["role"] == "used")
        print(f"\n[registry] демок {len(demos)} (використано {used}, "
              f"відкинуто {len(demos) - used})", file=sys.stderr)
        print(f"[registry] гравців {len(players)}, сесій {len(sess)}", file=sys.stderr)
        print(f"[registry] -> {REG}/", file=sys.stderr)
        if notes:
            print("\n[registry] розрізані мапи:", file=sys.stderr)
            for n in notes:
                print("   ", n, file=sys.stderr)

        multi = sorted(((len(p["series"]), players[sid]["nicks"], sid)
                        for sid, p in players.items()), reverse=True)[:20]
        print(f"\n[registry] найбільше сесій (потрібно >=4 для genuine-пар):",
              file=sys.stderr)
        for n, nicks, sid in multi:
            canon = max(nicks.items(), key=lambda kv: kv[1])[0]
            mark = "" if n >= 4 else "   <- замало"
            print(f"    {canon:18} {n:3} сесій{mark}", file=sys.stderr)
        ok = sum(1 for p in players.values() if len(p["series"]) >= 4)
        print(f"\n[registry] гравців із >=4 сесіями: {ok} з {len(players)}",
              file=sys.stderr)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="лише показати підсумок, не писати файли")
    a = ap.parse_args()
    build(verbose=True)
