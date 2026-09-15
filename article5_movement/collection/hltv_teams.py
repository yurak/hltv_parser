#!/usr/bin/env python3
"""Реєстр команд: світовий рейтинг HLTV -> teams.csv.

Рейтинг узятий навмисно: у PLAN.md рамка відбору когорти — топ HLTV, а не
довільний список. teams.csv дає резолвер «назва команди -> hltv_id», щоб
збір запускався як `collect.py --team navi`, без ручного пошуку id.

    /usr/bin/python3 hltv_teams.py --refresh
    /usr/bin/python3 hltv_teams.py --find navi
"""
import argparse, csv, html, re, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAMS = HERE / "teams.csv"


def scrape():
    from hltv_matchlist import make_driver
    d = make_driver(headless=True)
    try:
        d.get("https://www.hltv.org/ranking/teams")
        time.sleep(6)
        page = d.page_source
    finally:
        d.quit()
    if "Just a moment" in page:
        sys.exit("Cloudflare не пустив — спробуйте ще раз")

    # Блок команди: ranked-team ... #ранг ... <span class="name"> ... нікнейми ...
    # ... /team/ID/slug у "HLTV Team profile". Гравці йдуть з прапорцями країн.
    rows = []
    blocks = page.split('<div class="ranked-team standard-box">')[1:]
    for b in blocks:
        rank = re.search(r'<span class="position[^"]*">#(\d+)</span>', b)
        name = re.search(r'<span class="name">([^<]+)</span>', b)
        team = re.search(r'/team/(\d+)/([a-z0-9\-]+)', b)
        if not (rank and name and team):
            continue
        nicks = re.findall(r'<div class="rankingNicknames"><span>([^<]+)</span></div>', b)
        flags = re.findall(r'flags/30x20/([A-Z]{2})\.gif" class="gtSmartphone-only flag" '
                           r'title="([^"]+)">([^<]+)</div>', b)
        by_nick = {n: (cc, cn) for cc, cn, n in flags}
        roster = [f"{n}:{by_nick.get(n, ('', ''))[0]}" for n in nicks]
        rows.append({
            "rank": int(rank.group(1)),
            "hltv_id": team.group(1),
            "slug": team.group(2),
            "name": html.unescape(name.group(1)).strip(),
            "roster": "|".join(roster),
        })
    return rows


def load():
    if not TEAMS.exists():
        return []
    return list(csv.DictReader(TEAMS.open()))


ALIASES = {
    "navi": "natus-vincere", "na'vi": "natus-vincere", "na-vi": "natus-vincere",
    "nip": "ninjas-in-pyjamas", "vita": "vitality", "tsm": "team-spirit",
    "big": "big", "3dmax": "3dmax",
}


def find(query: str):
    """Пошук команди. Точні збіги мають пріоритет над підрядком, щоб
    'navi' не давало 'NAVI Junior' замість Natus Vincere."""
    rows = load()
    q = query.strip().lower()
    qs = ALIASES.get(q, q).replace(" ", "-")

    for r in rows:                                   # 1. точний id
        if q == r["hltv_id"]:
            return [r]
    for r in rows:                                   # 2. точний слаг
        if qs == r["slug"]:
            return [r]
    for r in rows:                                   # 3. точна назва
        if qs == r["name"].lower().replace(" ", "-"):
            return [r]
    hits = [r for r in rows                          # 4. підрядок
            if qs in r["slug"] or qs in r["name"].lower().replace(" ", "-")]
    hits.sort(key=lambda r: int(r["rank"]))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="перечитати рейтинг з HLTV")
    ap.add_argument("--find", help="знайти команду за назвою")
    a = ap.parse_args()

    if a.refresh:
        rows = scrape()
        if not rows:
            sys.exit("не вдалося розібрати рейтинг — розмітка HLTV змінилась")
        with TEAMS.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["rank", "hltv_id", "slug", "name", "roster"])
            w.writeheader(); w.writerows(rows)
        print(f"записано {len(rows)} команд -> {TEAMS.name}")

    if a.find:
        hits = find(a.find)
        if not hits:
            sys.exit(f"не знайдено: {a.find}")
        for h in hits:
            print(f"#{h['rank']:>2}  id={h['hltv_id']:<6} {h['slug']:<20} {h['name']}")
    elif not a.refresh:
        for r in load():
            print(f"#{r['rank']:>2}  id={r['hltv_id']:<6} {r['slug']:<20} {r['name']}")


if __name__ == "__main__":
    main()
