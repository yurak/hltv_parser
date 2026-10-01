#!/usr/bin/env python3
"""Одна команда: прогін -> повний зліпок артефактів статті.

    /usr/bin/python3 scripts/build_paper.py --run-id 2026-09-16_mirage_n136

Збирає outputs/paper/{tables,figures,logs,numbers.json,run_id.txt} і, якщо
рукопис уже існує, проганяє перевірки provenance/citation.

Саме цей скрипт треба запустити після перезбирання датасету. Все, що він
друкує в кінці, — це різниця між тим, що стверджує текст, і тим, що дають дані.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paperlib as P

PY_BIN = "/usr/bin/python3"       # системний Python: саме в ньому pyarrow і demoparser2


def sh(args: list[str], cwd: Path) -> int:
    print(f"\n$ {' '.join(args)}")
    return subprocess.call(args, cwd=str(cwd))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--replica-run", default=None,
                    help="прогін на другій мапі для чисел d2_ (build_tables.py)")
    ap.add_argument("--skip-review", action="store_true",
                    help="не проганяти provenance/citation навіть якщо рукопис є")
    a = ap.parse_args()

    root = P.ROOT
    P.manifest(a.run_id)          # впаде рано й зрозуміло, якщо прогін не завершений

    rc = 0
    rep = ["--replica-run", a.replica_run] if a.replica_run else []
    for step in (["scripts/build_tables.py", *rep], ["scripts/build_figures.py"]):
        rc |= sh([PY_BIN, *step, "--run-id", a.run_id], root)

    manuscript = root / "paper" / "manuscript.md"
    if manuscript.exists() and not a.skip_review:
        rc |= sh([PY_BIN, "scripts/provenance_map.py", "manuscript.md"], root)
        rc |= sh([PY_BIN, "scripts/citation_map.py", "manuscript.md"], root)
    else:
        print(f"\n(рукопису {manuscript.relative_to(root)} ще немає — "
              "перевірки provenance/citation пропущено)")

    tables = sorted((P.PAPER / "tables").glob("*.csv"))
    figures = sorted((P.PAPER / "figures").glob("*.png"))
    print(f"\n=== зліпок {a.run_id} ===")
    print(f"таблиць: {len(tables)} | рисунків: {len(figures)}")
    print(f"-> {P.PAPER.relative_to(root)}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
