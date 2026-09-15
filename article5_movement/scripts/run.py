#!/usr/bin/env python3
"""Єдина точка входу пайплайну статті 5.

    run.py sync       дотягнути з S3 те, чого бракує локально
    run.py registry   перебудувати реєстр демок/гравців/сесій
    run.py featurize  тіки -> ознаки й події (інкрементно, за хешем)
    run.py dataset    ознаки + реєстр -> датасет і когорта
    run.py analyze    протоколи
    run.py all        усе підряд

Кожна стадія ідемпотентна: без змін на вході робить нічого й каже про це.
Сирі `.dem` не потрібні жодній стадії, крім `sync --tier raw`.

Прогін пишеться в outputs/runs/<run_id>/ разом із manifest.json, у якому
зафіксовано склад датасету, версія коду ознак і головні числа. Без цього
неможливо відповісти, чому метрика змінилась між прогонами — через нові дані
чи через правку детектора.
"""
from __future__ import annotations

import argparse, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJ = ROOT.parent
SCRIPTS = ROOT / "scripts"
PROC = ROOT / "data" / "processed"
REG = ROOT / "data" / "registry"
DATASET = ROOT / "outputs" / "dataset"
RUNS = ROOT / "outputs" / "runs"
BUCKET = "s3://democs2phd"
PY = "/usr/bin/python3"


def aws_env() -> dict:
    env = dict(os.environ)
    env |= {"AWS_CONFIG_FILE": str(PROJ / ".aws" / "config"),
            "AWS_SHARED_CREDENTIALS_FILE": str(PROJ / ".aws" / "credentials"),
            "AWS_PROFILE": "democs2phd", "AWS_REGION": "eu-central-1"}
    return env


def sh(cmd: list[str], **kw) -> int:
    print(f"$ {' '.join(str(c) for c in cmd)}")
    return subprocess.run([str(c) for c in cmd], **kw).returncode


def stage_sync(a) -> int:
    """Тягне з бакета лише те, чого немає локально (`aws s3 sync` сам це вміє)."""
    if a.tier == "raw":
        src, dst, pat = f"{BUCKET}/raw/", ROOT / "data" / "raw", "*.dem"
    else:
        src, dst, pat = f"{BUCKET}/processed/", PROC, "*.parquet"
    dst.mkdir(parents=True, exist_ok=True)
    before = len(list(dst.glob(pat)))
    rc = sh(["aws", "s3", "sync", src, str(dst), "--exclude", "*", "--include", pat]
            + (["--dryrun"] if a.dry_run else []), env=aws_env())
    after = len(list(dst.glob(pat)))
    print(f"{a.tier}: було {before}, стало {after} файлів")
    return rc


def stage_registry(a) -> int:
    return sh([PY, SCRIPTS / "registry.py"] + (["--quiet"] if a.quiet else []))


def stage_featurize(a) -> int:
    return sh([PY, SCRIPTS / "featurize.py", "-j", a.jobs]
              + (["--force"] if a.force else []) + (["--quiet"] if a.quiet else []))


def stage_dataset(a) -> int:
    return sh([PY, SCRIPTS / "assemble.py",
               "--min-sessions", a.min_sessions, "--min-rounds", a.min_rounds])


def cohort_slice(a, out: Path) -> tuple[Path, Path]:
    """Зріз датасету під когорту — окремими файлами в теці прогону.

    Аналіз ганяється не на всіх, хто трапився в демках, а на ядрі когорти.
    Причини дві. Методологічна: гравець, якого видно в одній мапі, не дає
    відрізнити свій підпис від підпису матчу, але сидить у знаменнику
    випадкового рівня 1/N і розбавляє його. Обчислювальна: попарний крок в
    analyze.py — це класифікатор на кожну пару гравців, тобто O(N^2); 201
    гравець дає 20 100 пар, 32 — 496.

    Зріз кладеться поруч із результатами, тож із маніфесту завжди видно, на
    кому саме пораховані числа.
    """
    import pandas as pd
    feats = pd.read_parquet(DATASET / "features.parquet")
    evs = pd.read_parquet(DATASET / "event_features.parquet")
    if a.cohort != "all":
        coh = pd.read_csv(DATASET / "cohort.csv")
        col = "in_core_strict" if a.cohort == "strict" else "in_core"
        keep = set(coh.loc[coh[col], "steamid"])
        before = feats.player.nunique()
        feats = feats[feats.steamid.isin(keep)].copy()
        evs = evs[evs.steamid.isin(keep)].copy()
        print(f"когорта '{a.cohort}': {feats.player.nunique()} гравців із {before}, "
              f"{len(feats)} спостережень")
    fp = out / f"features_{a.cohort}.parquet"
    ep = out / f"event_features_{a.cohort}.parquet"
    feats.to_parquet(fp, index=False)
    evs.to_parquet(ep, index=False)
    return fp, ep


def stage_analyze(a) -> int:
    """P1 closed-set, P2 verification, P4 родини, P5 крива — у теку прогону."""
    if not (DATASET / "features.parquet").exists():
        print("Немає датасету. Спершу: run.py dataset", file=sys.stderr)
        return 1
    out = RUNS / a.run_id
    (out / "logs").mkdir(parents=True, exist_ok=True)
    feats, evs = cohort_slice(a, out)

    jobs = [
        ("analyze", [PY, SCRIPTS / "analyze.py", feats, "--events", evs,
                     "--side", a.side, "--outdir", out]),
        ("cross_match_series", [PY, SCRIPTS / "cross_match.py", feats, "--events", evs,
                                "--side", a.side, "--group", "series_id",
                                "--z-by", "match", "--outdir", out]),
        # та сама перевірка з групуванням за мапою — щоб бачити ціну витоку
        ("cross_match_map", [PY, SCRIPTS / "cross_match.py", feats, "--events", evs,
                             "--side", a.side, "--group", "match_id",
                             "--z-by", "match", "--outdir", out]),
        ("verification", [PY, SCRIPTS / "compare_profiles.py", feats, "--events", evs,
                          "--side", a.side, "--block", "series_id",
                          "--z-by", "match", "--outdir", out]),
        ("sample_size", [PY, SCRIPTS / "sample_size.py", feats, "--events", evs,
                         "--side", a.side, "--outdir", out]),
    ]
    failed = []
    for name, cmd in jobs:
        print(f"\n=== {name} ===")
        log = out / "logs" / f"{name}.log"
        t0 = time.time()
        # -u обов'язковий: Python буферизує stdout, коли той іде у файл, тож без
        # цього журнал лишається порожнім до самого кінця стадії і стежити за
        # довгим прогоном неможливо
        with log.open("w") as f:
            rc = subprocess.run([str(cmd[0]), "-u"] + [str(c) for c in cmd[1:]],
                                stdout=f, stderr=subprocess.STDOUT).returncode
        tail = log.read_text().strip().splitlines()[-3:]
        print("\n".join(tail))
        print(f"[{name}] rc={rc}, {time.time()-t0:.0f}с -> {log.relative_to(ROOT)}")
        if rc < 0:
            # Від'ємний код = стадію вбито сигналом, тобто ззовні і навмисне.
            # Переходити до наступної стадії в такому разі не можна: саме через
            # це два вбитих прогони продовжили жити далі по черзі стадій і
            # разом навантажили машину.
            print(f"стадію {name} вбито сигналом {-rc} — пайплайн зупинено",
                  file=sys.stderr)
            failed.append(name)
            break
        if rc != 0:
            failed.append(name)
    if failed:
        print(f"\nвпали: {', '.join(failed)} (деталі в logs/)")
    write_manifest(a, out, failed)
    return 0


def git_sha() -> str:
    try:
        return subprocess.run(["git", "-C", str(PROJ), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return ""


def write_manifest(a, out: Path, failed: list[str]) -> None:
    man = {"run_id": a.run_id, "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "git_sha": git_sha(), "params": {"side": a.side, "cohort": a.cohort,
                                            "min_sessions": a.min_sessions,
                                            "min_rounds": a.min_rounds},
           "failed_stages": failed}
    s = DATASET / "summary.json"
    if s.exists():
        man["dataset"] = json.loads(s.read_text())
    res = {}
    rep = out / f"report_{a.side}.json"
    if rep.exists():
        d = json.loads(rep.read_text())
        res["closed_set_within"] = d
    ver = out / f"verification_{a.side}.json"
    if ver.exists():
        v = json.loads(ver.read_text())
        res["verification"] = {k: v.get(k) for k in
                               ("eer", "auc", "dprime", "n_genuine", "n_impostor",
                                "block_unit", "genuine_same_map", "genuine_cross_map")}
    for tag, g in (("cross_series", "series_id"), ("cross_map", "match_id")):
        f = out / f"cross_{g}_{a.side}_match.csv"
        if f.exists():
            import csv as _csv
            rows = list(_csv.DictReader(f.open()))
            best = next((r for r in rows if r.get("family") == "all"), rows[0] if rows else None)
            if best:
                res[tag] = best
    man["results"] = res
    (out / "manifest.json").write_text(json.dumps(man, indent=2, ensure_ascii=False))
    print(f"\nманіфест -> {(out / 'manifest.json').relative_to(ROOT)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["sync", "registry", "featurize", "dataset",
                                      "analyze", "all"])
    ap.add_argument("--tier", default="ticks", choices=["ticks", "raw"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("-j", "--jobs", default="4")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--min-sessions", default="3")
    ap.add_argument("--min-rounds", default="24")
    ap.add_argument("--side", default="both", choices=["both", "T", "CT"])
    ap.add_argument("--cohort", default="core", choices=["core", "strict", "all"],
                    help="на кому рахувати протоколи (типово ядро когорти)")
    ap.add_argument("--run-id", default=None)
    a = ap.parse_args()

    if not a.run_id:
        n = len(list(PROC.glob("*_ticks.parquet")))
        a.run_id = f"{time.strftime('%Y-%m-%d')}_n{n}"

    stages = {"sync": stage_sync, "registry": stage_registry,
              "featurize": stage_featurize, "dataset": stage_dataset,
              "analyze": stage_analyze}
    seq = ["sync", "registry", "featurize", "dataset", "analyze"] if a.stage == "all" \
        else [a.stage]
    for name in seq:
        print(f"\n{'='*60}\n### {name}\n{'='*60}")
        rc = stages[name](a)
        if rc:
            print(f"стадія {name} впала (rc={rc})", file=sys.stderr)
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
