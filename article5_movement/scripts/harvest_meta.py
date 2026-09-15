#!/usr/bin/env python3
"""Знімає з локальних .dem усе, що існує тільки всередині них, — до видалення.

Мапа, сервер і патч читаються з заголовка демки (`parse_header`, ~0.00 с:
читається лише заголовок, не тіло). Після того як .dem поїдуть у S3 і зникнуть
з диска, ці поля нізвідки взяти, не качаючи 42 ГБ назад.

sha256 рахується тут же: ETag у S3 для multipart-завантажень не є md5 файлу,
тож звірка цілісності перед видаленням можлива лише за власним хешем.

    /usr/bin/python3 scripts/harvest_meta.py
    /usr/bin/python3 scripts/harvest_meta.py --no-hash   # швидко, без sha256
"""
from __future__ import annotations

import argparse, csv, hashlib, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
LOGS = ROOT / "outputs" / "logs"
REG = ROOT / "data" / "registry"

FIELDS = ["demo_id", "map", "server", "patch", "bytes", "sha256",
          "tickrate", "rounds", "n_players", "meta_source"]


def sha256(path: Path, chunk: int = 8 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def from_signals(demo_id: str) -> dict:
    """Метадані з signals.json, якщо демка парсилась після появи логування."""
    p = LOGS / f"{demo_id}_signals.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text())
    return {"map": d.get("map"), "server": d.get("server"), "patch": d.get("patch"),
            "tickrate": d.get("tickrate"), "rounds": d.get("rounds"),
            "n_players": len(d.get("players", [])) or None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-hash", action="store_true", help="пропустити sha256")
    ap.add_argument("-o", "--output", default=str(REG / "demos_header.csv"))
    a = ap.parse_args()

    demos = sorted(RAW.glob("*.dem"))
    if not demos:
        print(f"У {RAW} немає .dem — нема чого знімати.")
        return 1

    sys.path.insert(0, str(Path(__file__).parent))
    from demoparser2 import DemoParser

    rows, t0 = [], time.time()
    for i, d in enumerate(demos, 1):
        sig = from_signals(d.stem)
        try:
            hdr = DemoParser(str(d)).parse_header()
            head = {"map": hdr.get("map_name"), "server": hdr.get("server_name"),
                    "patch": hdr.get("patch_version")}
            src = "header+signals" if sig else "header"
        except Exception as e:                      # пошкоджена або обрізана демка
            print(f"  ! {d.name}: заголовок не читається ({e})")
            head, src = {}, "signals" if sig else "НЕМАЄ"

        # заголовок — авторитетніший за лог: лог міг писатись іншою версією коду
        row = {"demo_id": d.stem, "bytes": d.stat().st_size, "meta_source": src}
        row |= {k: v for k, v in sig.items() if v is not None}
        row |= {k: v for k, v in head.items() if v is not None}
        row["sha256"] = "" if a.no_hash else sha256(d)
        rows.append(row)
        if i % 10 == 0 or i == len(demos):
            print(f"  {i}/{len(demos)}  {time.time()-t0:.0f}с")

    REG.mkdir(parents=True, exist_ok=True)
    out = Path(a.output)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    no_map = [r["demo_id"] for r in rows if not r.get("map")]
    no_pq = [r["demo_id"] for r in rows
             if not (PROC / f"{r['demo_id']}_ticks.parquet").exists()]
    print(f"\n{out.relative_to(ROOT)}: {len(rows)} демок, {time.time()-t0:.0f}с")
    print(f"джерела: " + ", ".join(
        f"{s}={sum(r['meta_source'] == s for r in rows)}"
        for s in sorted({r["meta_source"] for r in rows})))
    if no_map:
        print(f"БЕЗ МАПИ ({len(no_map)}): {', '.join(no_map)}")
    if no_pq:
        print(f"БЕЗ PARQUET — не видаляти! ({len(no_pq)}): {', '.join(no_pq)}")
    if not no_map and not no_pq:
        print("Усі демки мають мапу й parquet — метадані знято повністю.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
