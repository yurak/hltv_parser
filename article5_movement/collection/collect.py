#!/usr/bin/env python3
"""Єдина точка входу для збору демок будь-якої команди.

    /usr/bin/python3 collect.py --team navi --limit 25 --max-maps 30
    /usr/bin/python3 collect.py --team "Natus Vincere" --list-only

Робить три речі:
  1. резолвить назву команди в hltv_id через teams.csv (рейтинг HLTV);
  2. збирає список серій у targets/<slug>.csv;
  3. позначає як `skip` серії, ВЖЕ завантажені в межах іншої команди, і
     запускає fetch_demos.py.

Крок 3 — не косметика. Серія Vitality–NAVI потрапляє і в список Vitality,
і в список NAVI, але під різними іменами файлів (HLTV ставить першою ту
команду, за якою фільтрували). Дедуплікація за іменем тут не працює —
тому звіряємось за `match_id`, який у HLTV глобально унікальний.
"""
from __future__ import annotations

import argparse, csv, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGETS = HERE / "targets"
PY = "/usr/bin/python3"


def all_target_files():
    """Усі списки цілей: і нові в targets/, і старі плоскі targets_*.csv."""
    return sorted(TARGETS.glob("*.csv")) + sorted(HERE.glob("targets_*.csv"))


def fetched_match_ids(exclude: Path | None = None):
    """match_id -> (звідки, примітка) для всього, що вже завантажено."""
    out = {}
    for f in all_target_files():
        if exclude and f.resolve() == exclude.resolve():
            continue
        try:
            for r in csv.DictReader(f.open()):
                if r.get("status") == "done" and r.get("match_id"):
                    out[r["match_id"]] = (f.name, r.get("note", "")[:60])
        except Exception:                                   # noqa: BLE001
            continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", required=True, help="назва, слаг або hltv_id")
    ap.add_argument("--limit", type=int, default=25, help="скільки серій у список")
    ap.add_argument("--max-maps", type=int, default=30, help="бюджет завантаження, .dem")
    ap.add_argument("--delay", type=float, default=10.0)
    ap.add_argument("--list-only", action="store_true", help="лише зібрати список")
    ap.add_argument("--refresh-list", action="store_true", help="перезібрати список цілей")
    a = ap.parse_args()

    import hltv_teams
    hits = hltv_teams.find(a.team)
    if not hits:
        sys.exit(f"команду '{a.team}' не знайдено в teams.csv "
                 f"(оновіть: {PY} hltv_teams.py --refresh)")
    if len(hits) > 1:
        exact = [h for h in hits if h["slug"] == a.team.lower().replace(" ", "-")]
        if len(exact) != 1:
            print("кілька збігів, уточніть:", file=sys.stderr)
            for h in hits:
                print(f"  {h['slug']:<20} id={h['hltv_id']}  #{h['rank']}", file=sys.stderr)
            sys.exit(1)
        hits = exact
    team = hits[0]
    print(f"[collect] {team['name']} (#{team['rank']}, id={team['hltv_id']})", file=sys.stderr)

    TARGETS.mkdir(exist_ok=True)
    tf = TARGETS / f"{team['slug']}.csv"

    if a.refresh_list or not tf.exists():
        subprocess.run([PY, str(HERE / "hltv_matchlist.py"),
                        "--team-id", team["hltv_id"], "--team-name", team["name"],
                        "--limit", str(a.limit), "--out", str(tf)], check=True)

    # --- дедуплікація за match_id ---
    rows = list(csv.DictReader(tf.open()))
    known = fetched_match_ids(exclude=tf)
    marked = 0
    for r in rows:
        if r["status"] == "todo" and r["match_id"] in known:
            src, note = known[r["match_id"]]
            r["status"] = "skip"
            r["note"] = f"вже зібрано в {src}"
            marked += 1
    if marked:
        with tf.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader(); w.writerows(rows)
    print(f"[collect] {len(rows)} серій у списку; {marked} уже є в інших командах "
          f"-> skip", file=sys.stderr)

    if a.list_only:
        for r in rows:
            print(f"  {r['status']:<7} {r['date']}  {r['team1']} vs {r['team2']:<16} {r['event']}")
        return

    subprocess.run([PY, str(HERE / "fetch_demos.py"), "--targets", str(tf),
                    "--max-maps", str(a.max_maps), "--delay", str(a.delay)], check=True)


if __name__ == "__main__":
    main()
