#!/usr/bin/env python3
"""Збирає список матчів команди з HLTV у CSV.

HLTV за Cloudflare: звичайний HTTP дає 403, тому ходимо headless-Chrome'ом
(перевірено — проходить). Один рядок = одна СЕРІЯ (bo1/bo3), а не мапа:
демка на HLTV видається одним архівом на серію.

    /usr/bin/python3 hltv_matchlist.py --team-id 9565 --team-name Vitality \
        --limit 40 --out targets_vitality.csv
"""
import argparse, csv, html, os, re, sys, time
from datetime import datetime, timezone

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

RESULT_CON = re.compile(
    r'<div class="result-con" data-zonedgrouping-entry-unix="(\d+)">\s*'
    r'<a href="(/matches/(\d+)/[^"]+)"',
    re.S,
)


def make_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    for a in ("--window-size=1920,1080", "--no-sandbox", "--disable-dev-shm-usage",
              "--disable-gpu", "--disable-blink-features=AutomationControlled"):
        opts.add_argument(a)
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    return webdriver.Chrome(options=opts)


def parse_page(page: str):
    """Витягує рядки результатів. Кожен блок ріжемо від result-con до кінця <a>."""
    rows = []
    for m in RESULT_CON.finditer(page):
        unix_ms, href, match_id = m.group(1), m.group(2), m.group(3)
        chunk = page[m.end(): m.end() + 4000]
        teams = re.findall(r'<div class="team[^"]*">([^<]+)</div>', chunk)
        event = re.search(r'<span class="event-name">([^<]+)</span>', chunk)
        score = re.findall(r'<span class="score-(?:won|lost|tie)">(\d+)</span>', chunk)
        bo = re.search(r'<div class="map map-text">([^<]+)</div>', chunk)
        if len(teams) < 2:
            continue
        rows.append({
            "match_id": match_id,
            "url": "https://www.hltv.org" + href,
            "date": datetime.fromtimestamp(int(unix_ms) / 1000, timezone.utc).strftime("%Y-%m-%d"),
            "team1": html.unescape(teams[0]).strip(),
            "team2": html.unescape(teams[1]).strip(),
            "event": html.unescape(event.group(1)).strip() if event else "",
            "score": "-".join(score[:2]),
            "format": bo.group(1).strip() if bo else "",
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team-id", required=True)
    ap.add_argument("--team-name", default="")
    ap.add_argument("--limit", type=int, default=40, help="скільки серій зібрати")
    ap.add_argument("--out", required=True)
    ap.add_argument("--delay", type=float, default=4.0, help="пауза між сторінками, с")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    d = make_driver(headless=not args.headed)
    rows, offset, seen = [], 0, set()
    try:
        while len(rows) < args.limit:
            url = f"https://www.hltv.org/results?team={args.team_id}"
            if offset:
                url += f"&offset={offset}"
            print(f"[matchlist] {url}", file=sys.stderr)
            d.get(url)
            time.sleep(args.delay)
            page = d.page_source
            if "Just a moment" in page or "results-sublist" not in page:
                print("[matchlist] сторінка не схожа на результати — стоп", file=sys.stderr)
                break
            batch = [r for r in parse_page(page) if r["match_id"] not in seen]
            if not batch:
                print("[matchlist] порожня сторінка — кінець", file=sys.stderr)
                break
            for r in batch:
                seen.add(r["match_id"])
            rows.extend(batch)
            print(f"[matchlist] +{len(batch)} (разом {len(rows)})", file=sys.stderr)
            offset += 100
    finally:
        d.quit()

    rows = rows[: args.limit]
    for r in rows:
        r["team_filter"] = args.team_name or args.team_id
        r["status"] = "todo"
        r["demo_id"] = ""
        r["note"] = ""
    fields = ["match_id", "date", "team1", "team2", "event", "format", "score",
              "team_filter", "url", "demo_id", "status", "note"]
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"[matchlist] записано {len(rows)} серій -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
