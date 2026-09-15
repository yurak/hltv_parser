#!/usr/bin/env python3
"""Качає GOTV-демки HLTV за списком серій і розкладає їх у data/raw/.

HLTV віддає ОДИН .rar на серію (усі мапи разом). Cloudflare пускає лише
браузер, тому сторінку матчу відкриваємо Selenium'ом, а далі переносимо
його cookies у requests і тягнемо архів потоково (з докачуванням).

Скрипт ідемпотентний: стан пишеться в той самий CSV (`status`), уже наявні
.dem не перезавантажуються. Можна зупиняти й перезапускати.

    /usr/bin/python3 fetch_demos.py --targets targets_vitality.csv \
        --max-maps 30 --delay 8
"""
import argparse, csv, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import inventory

ROOT = Path(__file__).resolve().parent.parent          # article5_movement/
RAW = ROOT / "data" / "raw"
ARCH = RAW / "_archives"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")

EVENT_SLUG = [
    ("esports world cup", "ewc"), ("blast", "blast"), ("iem", "iem"),
    ("esl pro league", "epl"), ("pgl", "pgl"), ("elisa", "elisa"),
    ("thunderpick", "tp"), ("gamers8", "g8"), ("cct", "cct"),
]


def make_driver(download_dir: Path, headless=True):
    """Chrome, налаштований качати .rar у задану теку без діалогів."""
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    for a in ("--window-size=1920,1080", "--no-sandbox", "--disable-dev-shm-usage",
              "--disable-gpu", "--disable-blink-features=AutomationControlled"):
        opts.add_argument(a)
    opts.add_argument(f"user-agent={UA}")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("prefs", {
        "download.default_directory": str(download_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })
    d = webdriver.Chrome(options=opts)
    # headless Chrome за замовчуванням блокує завантаження — вмикаємо явно
    try:
        d.execute_cdp_cmd("Page.setDownloadBehavior",
                          {"behavior": "allow", "downloadPath": str(download_dir)})
    except Exception:
        pass
    return d


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def event_slug(name: str) -> str:
    low = name.lower()
    for key, val in EVENT_SLUG:
        if key in low:
            return val
    return slug(name.split()[0]) if name.split() else "event"


def base_name(row) -> str:
    return f"{row['date']}_{event_slug(row['event'])}_{slug(row['team1'])}-vs-{slug(row['team2'])}"


def find_demo_id(driver, url, tries=2):
    """Відкриває сторінку матчу, повертає (demo_id, [мапи])."""
    for attempt in range(tries):
        driver.get(url)
        time.sleep(5)
        page = driver.page_source
        if "Just a moment" in page:
            time.sleep(8)
            continue
        m = re.search(r"/download/demo/(\d+)", page)
        maps = re.findall(r'class="mapname">([^<]+)<', page)
        if m:
            return m.group(1), [x.strip() for x in maps]
        if "Demo" in page:            # сторінка відкрилась, але демки нема
            return None, [x.strip() for x in maps]
    return None, []


def download(driver, demo_id, dest: Path, timeout=900):
    """Качає архів САМИМ браузером: requests ловить 403 на TLS-фінгерпринті."""
    before = {p.name for p in ARCH.iterdir()}
    driver.get(f"https://www.hltv.org/download/demo/{demo_id}")

    start, last_size, stalled = time.time(), -1, 0
    while time.time() - start < timeout:
        time.sleep(3)
        files = {p.name for p in ARCH.iterdir()} - before
        partial = [f for f in files if f.endswith((".crdownload", ".tmp"))]
        finished = [f for f in files if not f.endswith((".crdownload", ".tmp"))]
        if finished and not partial:
            src = ARCH / finished[0]
            if src != dest:
                src.rename(dest)
            return dest
        if partial:
            size = (ARCH / partial[0]).stat().st_size
            print(f"\r    {size/1e6:8.1f} MB", end="", file=sys.stderr, flush=True)
            stalled = stalled + 1 if size == last_size else 0
            last_size = size
            if stalled > 40:                      # ~2 хв без руху
                raise RuntimeError("завантаження зупинилось")
        elif time.time() - start > 60:
            raise RuntimeError("браузер не почав завантаження (можливо 403/капча)")
    raise RuntimeError(f"таймаут {timeout} с")


def extract(archive: Path, row) -> list:
    """Розпаковує .rar і перейменовує .dem за конвенцією проєкту."""
    out = []
    with tempfile.TemporaryDirectory() as td:
        res = subprocess.run(["unar", "-q", "-o", td, str(archive)],
                             capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"unar: {res.stderr.strip()[:200]}")
        dems = sorted(Path(td).rglob("*.dem"))
        if not dems:
            raise RuntimeError("в архіві немає .dem")
        for d in dems:
            mp = re.search(r"(mirage|inferno|nuke|dust2|ancient|anubis|overpass|"
                           r"vertigo|train|cache|cbble|tuscan)", d.name, re.I)
            mapname = mp.group(1).lower() if mp else slug(d.stem)[-12:]
            target = RAW / f"{base_name(row)}_{mapname}.dem"
            n = 2
            while target.exists():
                target = RAW / f"{base_name(row)}_{mapname}{n}.dem"
                n += 1
            shutil.move(str(d), target)
            out.append(target.name)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--max-maps", type=int, default=30, help="бюджет у .dem-файлах")
    ap.add_argument("--delay", type=float, default=8.0, help="пауза між матчами, с")
    ap.add_argument("--keep-archives", action="store_true")
    ap.add_argument("--no-s3-check", action="store_true",
                    help="не звірятися з бакетом перед завантаженням")
    ap.add_argument("--max-errors", type=int, default=3,
                    help="скільки помилок поспіль перед зупинкою")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    ARCH.mkdir(parents=True, exist_ok=True)

    path = Path(args.targets)
    rows = list(csv.DictReader(path.open()))
    fields = list(rows[0].keys())

    inv = inventory.build() if not args.no_s3_check else {"series": {}, "s3_available": False}
    if inv.get("s3_available"):
        print(f"[fetch] облік: у S3 {len(inv['s3_raw'])} .dem, "
              f"локально {len(inv['local_raw'])}", file=sys.stderr)

    got = len(list(RAW.glob("*.dem")))
    print(f"[fetch] у data/raw уже {got} .dem; бюджет цього запуску {args.max_maps}",
          file=sys.stderr)

    driver = make_driver(ARCH, headless=True)
    new_maps, errors = 0, 0
    try:
        driver.get("https://www.hltv.org/")
        time.sleep(5)
        for row in rows:
            if new_maps >= args.max_maps:
                print(f"[fetch] бюджет {args.max_maps} мап вичерпано", file=sys.stderr)
                break
            if errors >= args.max_errors:
                print(f"[fetch] {errors} помилок поспіль — зупиняюсь, "
                      f"HLTV найпевніше обмежив доступ", file=sys.stderr)
                break
            if row["status"] in ("done", "missing", "skip"):
                continue
            where = inventory.have_series(inv, base_name(row)) if inv.get("series") else ""
            if where:
                row["status"] = "done"
                row["note"] = f"вже є ({where}) — не перекачую"
                print(f"[fetch] {row['date']} {row['team1']} vs {row['team2']}: "
                      f"вже є ({where})", file=sys.stderr)
                continue
            print(f"[fetch] {row['date']} {row['team1']} vs {row['team2']} "
                  f"({row['event']}, {row['format']})", file=sys.stderr)
            try:
                demo_id, maps = find_demo_id(driver, row["url"])
                if not demo_id:
                    row["status"], row["note"] = "missing", "немає посилання на демку"
                    print("    -> демки немає", file=sys.stderr)
                    continue
                row["demo_id"] = demo_id
                arch = ARCH / f"{base_name(row)}.rar"
                if not arch.exists():
                    download(driver, demo_id, arch)
                names = extract(arch, row)
                new_maps += len(names)
                row["status"], row["note"] = "done", f"{len(names)} мап: " + ",".join(names)
                errors = 0
                print(f"    -> {len(names)} мап (усього нових {new_maps})", file=sys.stderr)
                if not args.keep_archives:
                    arch.unlink(missing_ok=True)
            except Exception as e:
                row["status"], row["note"] = "error", str(e)[:200]
                errors += 1
                print(f"    !! {e}", file=sys.stderr)
            finally:
                with path.open("w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=fields)
                    w.writeheader(); w.writerows(rows)
                time.sleep(args.delay)
    finally:
        driver.quit()

    done = sum(1 for r in rows if r["status"] == "done")
    print(f"\n[fetch] серій готово {done}/{len(rows)}; нових .dem {new_maps}; "
          f"разом у raw {len(list(RAW.glob('*.dem')))}", file=sys.stderr)


if __name__ == "__main__":
    main()
