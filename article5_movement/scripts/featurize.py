#!/usr/bin/env python3
"""Стадія 3: тіки -> ознаки й події, по одній демці, з кешем.

Кеш ключується парою (sha256 тіків, версія коду ознак). Це дає дві речі:
демка, яку вже порахували, не рахується вдруге; а правка порогу детектора
автоматично відкриває нову гілку кешу, не затираючи попередні числа — тож
питання «EER змінився через нові дані чи через правку детектора?» вирішується
звіркою feat_ver, а не пам'яттю.

    data/features/<demo_id>/<feat_ver>/{feats,events,evagg}.parquet + meta.json

Вартість: ~4 с на демку (2.7 ознаки + 1.3 події), тобто весь теплий ярус
перераховується за хвилини. Тому кеш тут — зручність, а не необхідність, і
--force безпечний.

    /usr/bin/python3 scripts/featurize.py -j 4
    /usr/bin/python3 scripts/featurize.py --force
"""
from __future__ import annotations

import argparse, hashlib, json, os, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FEAT = ROOT / "data" / "features"
SCRIPTS = Path(__file__).resolve().parent

# файли, від яких залежать числа; зміна будь-якого дає новий feat_ver
CODE = ["features.py", "events.py", "extract_ticks.py"]


def feat_ver() -> str:
    h = hashlib.sha256()
    for name in CODE:
        h.update((SCRIPTS / name).read_bytes())
    return h.hexdigest()[:10]


def file_sha(p: Path, chunk: int = 8 << 20) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def outdir(demo_id: str, ver: str) -> Path:
    return FEAT / demo_id / ver


def is_fresh(demo_id: str, ver: str, ticks_sha: str) -> bool:
    m = outdir(demo_id, ver) / "meta.json"
    if not m.exists():
        return False
    try:
        d = json.loads(m.read_text())
    except json.JSONDecodeError:                    # обірваний запис
        return False
    return (d.get("ticks_sha256") == ticks_sha
            and all((outdir(demo_id, ver) / f"{n}.parquet").exists()
                    for n in ("feats", "events", "evagg")))


def one(demo_id: str, ver: str) -> tuple[str, str, float, int]:
    """Рахує одну демку. Виконується у власному процесі."""
    t0 = time.time()
    sys.path.insert(0, str(SCRIPTS))
    import features as FT, events as EV

    pq = PROC / f"{demo_id}_ticks.parquet"
    sha = file_sha(pq)
    if is_fresh(demo_id, ver, sha):
        return demo_id, "кеш", 0.0, 0

    d = outdir(demo_id, ver)
    d.mkdir(parents=True, exist_ok=True)
    feats = FT.build(str(pq))
    ev, agg = EV.build(str(pq))
    feats.to_parquet(d / "feats.parquet", index=False)
    ev.to_parquet(d / "events.parquet", index=False)
    agg.to_parquet(d / "evagg.parquet", index=False)
    (d / "meta.json").write_text(json.dumps({
        "demo_id": demo_id, "feat_ver": ver, "ticks_sha256": sha,
        "n_obs": int(len(feats)), "n_events": int(len(ev)),
        "n_features": int(feats.shape[1]), "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }, indent=2))
    return demo_id, "пораховано", time.time() - t0, len(feats)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", "--jobs", type=int, default=max(1, (os.cpu_count() or 4) // 3))
    ap.add_argument("--force", action="store_true", help="перерахувати попри кеш")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    ver = feat_ver()
    demos = sorted(p.name[: -len("_ticks.parquet")] for p in PROC.glob("*_ticks.parquet"))
    if not demos:
        print(f"Немає тіків у {PROC}. Спершу: run.py sync", file=sys.stderr)
        return 1
    if a.force:
        for d in demos:
            m = outdir(d, ver) / "meta.json"
            if m.exists():
                m.unlink()

    print(f"feat_ver {ver} | демок {len(demos)} | воркерів {a.jobs}")
    t0, done, cached, obs = time.time(), 0, 0, 0
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        futs = {ex.submit(one, d, ver): d for d in demos}
        for f in as_completed(futs):
            demo_id, how, dt, n = f.result()
            obs += n
            if how == "кеш":
                cached += 1
            else:
                done += 1
            if not a.quiet and (done + cached) % 20 == 0:
                print(f"  {done+cached}/{len(demos)}  {time.time()-t0:.0f}с")

    print(f"пораховано {done}, з кешу {cached}, {obs} нових спостережень, "
          f"{time.time()-t0:.0f}с")
    (FEAT / "CURRENT_VER").write_text(ver)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
