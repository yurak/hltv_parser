#!/usr/bin/env python3
"""Стадія 2: реєстр — єдине джерело правди про демки, гравців і сесії.

Замінює розбір імені файлу регулярним виразом, який ламається на масштабі.
Складається з чотирьох джерел:

    data/registry/demos_header.csv   мапа, сервер, патч, sha256 (harvest_meta.py)
    collection/targets*.csv          HLTV match_id -> серія, дата, івент, команди
    data/processed/*_ticks.parquet   steamid, ніки, раунди на сторону
    collection/teams.csv             команда й країна гравця (243 команди)

Одиниця сесії — СЕРІЯ, не мапа: три мапи одного Bo3 — це один день, той самий
суперник, та сама розминка й ті самі налаштування миші. Рахувати їх як
незалежні сесії — витік, через який genuine-пари виглядають кращими, ніж є.

    /usr/bin/python3 scripts/registry.py
    /usr/bin/python3 scripts/registry.py --quiet
"""
from __future__ import annotations

import argparse, csv, re, sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
REG = ROOT / "data" / "registry"
COLLECT = ROOT / "collection"
HEADER_CSV = REG / "demos_header.csv"

DEMO_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)_([a-z0-9]+)$")


def target_rows() -> dict[str, dict]:
    """demo_id -> метадані серії з таргетів. HLTV match_id глобально унікальний,
    тож він і є series_id скрізь, де матч прийшов з HLTV."""
    out: dict[str, dict] = {}
    files = sorted((COLLECT / "targets").glob("*.csv")) + sorted(COLLECT.glob("targets_*.csv"))
    for f in files:
        for r in csv.DictReader(f.open()):
            if r.get("status") != "done" or not r.get("note"):
                continue
            # note: "3 мап: a.dem,b.dem,c.dem"
            names = re.findall(r"([^\s,]+)\.dem", r["note"])
            for n in names:
                out[n] = {"series_id": r["match_id"], "series_source": "hltv",
                          "date": r["date"], "event": r["event"],
                          "team1": r["team1"], "team2": r["team2"],
                          "format": r.get("format", ""),
                          "hltv_url": r.get("url", "")}
    return out


def synthetic_series(demo_id: str) -> dict:
    """Для демок поза таргетами (позатурнірні, ранній ручний збір) серія
    відновлюється з імені: дата + середні токени без токена мапи."""
    m = DEMO_RE.match(demo_id)
    if not m:
        return {"series_id": f"x_{demo_id}", "series_source": "filename",
                "date": "", "event": "", "team1": "", "team2": "", "format": "",
                "hltv_url": ""}
    date, middle, _map_token = m.groups()
    ev, _, teams = middle.partition("_")
    t1, _, t2 = teams.partition("-vs-")
    return {"series_id": f"x_{date}_{middle}", "series_source": "filename",
            "date": date, "event": ev, "team1": t1, "team2": t2,
            "format": "", "hltv_url": ""}


def nkey(nick: str) -> str:
    """Ключ для звірки ніків між джерелами. HLTV пише `huNter-` і `electroNic`,
    у демці той самий гравець — `huNter` і `electronic`: регістр і хвостова
    пунктуація не є частиною ідентичності. Всередині датасету ідентичність
    однаково тримається на steamid — це лише міст до зовнішньої таблиці."""
    return re.sub(r"[^a-z0-9]", "", nick.lower())


def player_country_team() -> dict[str, tuple[str, str]]:
    """нік -> (команда, країна) з рейтингового зрізу HLTV."""
    out: dict[str, tuple[str, str]] = {}
    f = COLLECT / "teams.csv"
    if not f.exists():
        return out
    for r in csv.DictReader(f.open()):
        for ent in (r.get("roster") or "").split("|"):
            nick, _, cc = ent.partition(":")
            if nick and nkey(nick) not in out:      # вищий ранг виграє
                out[nkey(nick)] = (r["name"], cc)
    return out


def scan_ticks(demo_ids: list[str], quiet: bool) -> pd.DataFrame:
    """(demo_id, steamid, name, side) -> кількість раундів. Читаються чотири
    колонки зі 34, тому прохід по всьому теплому ярусу — секунди, не хвилини."""
    rows = []
    for i, d in enumerate(demo_ids, 1):
        p = PROC / f"{d}_ticks.parquet"
        if not p.exists():
            continue
        t = pd.read_parquet(p, columns=["steamid", "name", "side", "round", "tickrate"])
        g = (t.groupby(["steamid", "name", "side"])["round"]
               .nunique().reset_index(name="rounds"))
        g["demo_id"] = d
        g["tickrate_ticks"] = float(t.tickrate.iloc[0])
        rows.append(g)
        if not quiet and (i % 25 == 0 or i == len(demo_ids)):
            print(f"  тіки {i}/{len(demo_ids)}")
    if not rows:
        return pd.DataFrame(columns=["steamid", "name", "side", "rounds", "demo_id"])
    return pd.concat(rows, ignore_index=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if not HEADER_CSV.exists():
        print(f"Немає {HEADER_CSV}. Спершу: scripts/harvest_meta.py", file=sys.stderr)
        return 1

    hdr = pd.read_csv(HEADER_CSV, dtype={"patch": "string"})
    tg = target_rows()

    # --- demos.csv ---
    meta = []
    for d in hdr["demo_id"]:
        m = dict(tg.get(d) or synthetic_series(d))
        m["demo_id"] = d
        m["context"] = "platform" if "platform" in d else "tournament"
        meta.append(m)
    demos = hdr.merge(pd.DataFrame(meta), on="demo_id", how="left")
    demos["has_ticks"] = [(PROC / f"{d}_ticks.parquet").exists() for d in demos.demo_id]
    demos = demos[["demo_id", "series_id", "series_source", "date", "event",
                   "team1", "team2", "format", "map", "context", "tickrate",
                   "rounds", "n_players", "server", "patch", "bytes", "sha256",
                   "hltv_url", "has_ticks"]].sort_values(["date", "demo_id"])

    # --- сирий скан тіків ---
    tk = scan_ticks(demos.demo_id.tolist(), a.quiet)
    if len(tk):
        tr = tk.groupby("demo_id")["tickrate_ticks"].first()
        demos["tickrate"] = demos.demo_id.map(tr).fillna(demos.tickrate)
    tk = tk.merge(demos[["demo_id", "series_id", "date", "event", "context", "map"]],
                  on="demo_id", how="left")

    # --- players.csv: одна особа = один steamid ---
    canon = (tk.groupby("steamid")["name"]
               .agg(lambda s: s.value_counts().idxmax()).rename("nick_canonical"))
    nicks = (tk.groupby("steamid")["name"]
               .agg(lambda s: "|".join(sorted(set(s)))).rename("nicks_seen"))
    players = pd.concat([canon, nicks], axis=1).reset_index()

    pct = player_country_team()
    players["team"] = players.nick_canonical.map(lambda n: pct.get(nkey(n), ("", ""))[0])
    players["country"] = players.nick_canonical.map(lambda n: pct.get(nkey(n), ("", ""))[1])

    # --- sessions.csv: одиниця = (гравець, серія) ---
    piv = (tk.pivot_table(index=["steamid", "series_id"], columns="side",
                          values="rounds", aggfunc="sum", fill_value=0)
             .reset_index())
    for s in ("T", "CT"):
        if s not in piv.columns:
            piv[s] = 0
    piv = piv.rename(columns={"T": "rounds_T", "CT": "rounds_CT"})
    extra = (tk.groupby(["steamid", "series_id"])
               .agg(n_maps=("demo_id", "nunique"), date=("date", "first"),
                    event=("event", "first"), context=("context", "first"))
               .reset_index())
    sessions = piv.merge(extra, on=["steamid", "series_id"])
    sessions = sessions.merge(players[["steamid", "nick_canonical"]], on="steamid")

    # S = число незалежних серій; ядро когорти — те, на чому взагалі можливий протокол
    S = sessions.groupby("steamid").size().rename("n_sessions")
    players = players.merge(S, on="steamid", how="left").fillna({"n_sessions": 0})
    players["n_sessions"] = players.n_sessions.astype(int)
    ok = (sessions.rounds_T >= 24) & (sessions.rounds_CT >= 24)
    players = players.merge(sessions[ok].groupby("steamid").size()
                            .rename("n_sessions_full").reset_index(),
                            on="steamid", how="left").fillna({"n_sessions_full": 0})
    players["n_sessions_full"] = players.n_sessions_full.astype(int)
    players["cohort"] = ["core" if s >= 3 else "impostor" for s in players.n_sessions]
    players = players.sort_values(["n_sessions", "nick_canonical"], ascending=[False, True])

    REG.mkdir(parents=True, exist_ok=True)
    demos.to_csv(REG / "demos.csv", index=False)
    players.to_csv(REG / "players.csv", index=False)
    sessions.sort_values(["steamid", "date"]).to_csv(REG / "sessions.csv", index=False)

    if not a.quiet:
        n_hltv = (demos.series_source == "hltv").sum()
        print(f"\ndemos.csv     {len(demos)} демок, {demos.series_id.nunique()} серій "
              f"({n_hltv} з HLTV match_id, {len(demos)-n_hltv} з імені файлу)")
        print(f"players.csv   {len(players)} гравців, "
              f"{(players.cohort=='core').sum()} у ядрі когорти (S>=3)")
        print(f"sessions.csv  {len(sessions)} сесій (гравець, серія)")
        print("\nмапи:", demos["map"].value_counts().to_dict())
        print("контекст:", demos.context.value_counts().to_dict())
        print("тікрейт:", demos.tickrate.value_counts().to_dict())
        top = players[players.cohort == "core"].head(15)
        print(f"\nтоп когорти:\n{top[['nick_canonical','team','country','n_sessions','n_sessions_full']].to_string(index=False)}")
        nocc = players[(players.cohort == 'core') & (players.country == '')]
        if len(nocc):
            print(f"\nбез країни/команди в teams.csv ({len(nocc)}): "
                  + ", ".join(nocc.nick_canonical.head(20)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
