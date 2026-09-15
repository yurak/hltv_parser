#!/usr/bin/env python3
"""Єдиний облік демок: локальний диск + бакет S3.

Після того як локальні .dem видаляються після заливання, диск перестає бути
джерелом правди. Цей модуль зводить три місця — S3, локальний raw,
локальний processed — в одну картину і дає `have_series()`, яким
fetch_demos.py вирішує, чи качати серію взагалі.

    /usr/bin/python3 inventory.py            # таблиця
    /usr/bin/python3 inventory.py --json     # для скриптів
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # hltv_parser/
DATA = ROOT / "article5_movement" / "data"
BUCKET = "s3://democs2phd"


def _aws_env():
    env = dict(os.environ)
    env["AWS_CONFIG_FILE"] = str(ROOT / ".aws" / "config")
    env["AWS_SHARED_CREDENTIALS_FILE"] = str(ROOT / ".aws" / "credentials")
    env["AWS_PROFILE"] = "democs2phd"
    env["AWS_REGION"] = "eu-central-1"
    return env


def s3_list(prefix="raw/"):
    """Імена об'єктів у бакеті. Порожній список, якщо S3 недоступний."""
    try:
        r = subprocess.run(
            ["aws", "s3", "ls", f"{BUCKET}/{prefix}", "--recursive"],
            capture_output=True, text=True, env=_aws_env(), timeout=120)
        if r.returncode != 0:
            if not r.stderr.strip():        # порожній префікс — не помилка
                return {}
            print(f"[inventory] S3 недоступний: {r.stderr.strip()[:120]}", file=sys.stderr)
            return None
        out = {}
        for line in r.stdout.splitlines():
            parts = line.split(None, 3)
            if len(parts) == 4:
                out[Path(parts[3]).name] = int(parts[2])
        return out
    except Exception as e:                                  # noqa: BLE001
        print(f"[inventory] S3 недоступний: {e}", file=sys.stderr)
        return None


def local(sub, ext):
    d = DATA / sub
    return {p.name: p.stat().st_size for p in d.glob(f"*{ext}")} if d.exists() else {}


def series_key(filename: str):
    """`2026-08-29_blast_vitality-vs-9z_nuke.dem` -> префікс серії."""
    m = re.match(r"(\d{4}-\d{2}-\d{2}_[a-z0-9]+_.+?)_[a-z0-9]+\.(dem|parquet)$", filename)
    return m.group(1) if m else None


def build():
    s3_raw = s3_list("raw/")
    s3_proc = s3_list("processed/")
    inv = {
        "s3_raw": s3_raw if s3_raw is not None else {},
        "s3_processed": s3_proc if s3_proc is not None else {},
        "s3_available": s3_raw is not None,
        "local_raw": local("raw", ".dem"),
        "local_processed": local("processed", ".parquet"),
    }
    series = {}
    for place, names in (("s3", inv["s3_raw"]), ("local", inv["local_raw"])):
        for n in names:
            k = series_key(n)
            if k:
                series.setdefault(k, {"s3": [], "local": []})[place].append(n)
    inv["series"] = series
    return inv


def have_series(inv, prefix: str) -> str:
    """Де лежить серія: 's3' | 'local' | 'both' | ''."""
    e = inv["series"].get(prefix)
    if not e:
        return ""
    if e["s3"] and e["local"]:
        return "both"
    return "s3" if e["s3"] else "local"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    inv = build()
    if a.json:
        print(json.dumps(inv, ensure_ascii=False, indent=2))
        return
    gb = lambda d: sum(d.values()) / 1e9
    print(f"S3 доступний: {'так' if inv['s3_available'] else 'НІ'}")
    print(f"  s3://raw/        {len(inv['s3_raw']):3} файлів  {gb(inv['s3_raw']):6.2f} ГБ")
    print(f"  s3://processed/  {len(inv['s3_processed']):3} файлів  {gb(inv['s3_processed']):6.2f} ГБ")
    print(f"  локально raw     {len(inv['local_raw']):3} файлів  {gb(inv['local_raw']):6.2f} ГБ")
    print(f"  локально parquet {len(inv['local_processed']):3} файлів  {gb(inv['local_processed']):6.2f} ГБ")
    print(f"\nсерій усього: {len(inv['series'])}")
    only_local = [k for k in inv["series"] if have_series(inv, k) == "local"]
    only_s3 = [k for k in inv["series"] if have_series(inv, k) == "s3"]
    both = [k for k in inv["series"] if have_series(inv, k) == "both"]
    print(f"  і там і там: {len(both)}   тільки S3: {len(only_s3)}   тільки локально: {len(only_local)}")
    if only_local:
        print("\nще не залиті в S3:")
        for k in sorted(only_local):
            print("  ", k)


if __name__ == "__main__":
    main()
