#!/usr/bin/env python3
"""Паралельний парсинг усіх нерозпарсених демок.

Одна демка їсть ~2.4 ядра, тому 4 воркери на 12-ядерній машині — розумна
стеля. Парсинг іде під час завантажень (процесор інакше простоює).

    /usr/bin/python3 scripts/parse_all.py            # усе, чого бракує
    /usr/bin/python3 scripts/parse_all.py -j 6       # більше воркерів
    /usr/bin/python3 scripts/parse_all.py --dry-run
"""
import argparse, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
SCRIPT = ROOT / "scripts" / "extract_ticks.py"


def pending():
    done = {p.name[:-len("_ticks.parquet")] for p in PROC.glob("*_ticks.parquet")}
    return sorted(p for p in RAW.glob("*.dem") if p.stem not in done)


def run(demo: str):
    out = PROC / f"{Path(demo).stem}_ticks.parquet"
    t0 = time.time()
    r = subprocess.run(["/usr/bin/python3", str(SCRIPT), demo, "-o", str(out)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stderr.strip().splitlines() or ["?"])[-1]
        return demo, False, time.time() - t0, tail[:160]
    return demo, True, time.time() - t0, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", "--jobs", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    todo = pending()
    print(f"[parse] до парсингу: {len(todo)} демок, воркерів {a.jobs}", file=sys.stderr)
    if a.dry_run or not todo:
        for p in todo:
            print("  ", p.name)
        return

    t0, ok, bad = time.time(), 0, []
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        futs = {ex.submit(run, str(p)): p for p in todo}
        for i, f in enumerate(as_completed(futs), 1):
            demo, good, dt, err = f.result()
            name = Path(demo).name
            if good:
                ok += 1
                print(f"[{i}/{len(todo)}] {name[:52]:54} {dt:5.1f}s", file=sys.stderr)
            else:
                bad.append((name, err))
                print(f"[{i}/{len(todo)}] {name[:52]:54} ПОМИЛКА: {err}", file=sys.stderr)

    total = time.time() - t0
    print(f"\n[parse] успішно {ok}, помилок {len(bad)}, "
          f"{total:.0f} с ({total/max(1,len(todo)):.1f} с/демку сумарно)", file=sys.stderr)
    for n, e in bad:
        print(f"  ! {n}: {e}", file=sys.stderr)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
