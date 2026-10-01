#!/usr/bin/env python3
"""Спільне для build_tables.py і build_figures.py.

Одна відповідальність: знайти прогін, прочитати його артефакти й віддати їх
у вигляді, з якого будуються таблиці й рисунки. Жодних обчислень статті тут
немає — тільки читання й дрібні перетворення.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "outputs" / "runs"
PAPER = ROOT / "outputs" / "paper"
REG = ROOT / "data" / "registry"

FAMILY_UA = {"all": "усі", "keydyn": "клавіатурна динаміка", "micro": "мікрорух",
             "habit": "звички спорядження", "event": "подієві", "macro": "геометрія маршруту"}


def run_dir(run_id: str) -> Path:
    d = RUNS / run_id
    if not d.exists():
        raise SystemExit(f"немає прогону {run_id}; є: "
                         + ", ".join(sorted(p.name for p in RUNS.iterdir() if p.is_dir())))
    return d


def manifest(run_id: str) -> dict:
    p = run_dir(run_id) / "manifest.json"
    if not p.exists():
        raise SystemExit(f"{run_id}: немає manifest.json — прогін не завершений, "
                         "таблиці з нього будувати не можна")
    return json.loads(p.read_text())


def read_csv(run_id: str, name: str) -> pd.DataFrame | None:
    p = run_dir(run_id) / name
    return pd.read_csv(p) if p.exists() else None


def read_json(run_id: str, name: str) -> dict | None:
    p = run_dir(run_id) / name
    return json.loads(p.read_text()) if p.exists() else None


def features(run_id: str) -> pd.DataFrame | None:
    """Ознаки когорти цього прогону (features_<cohort>.parquet)."""
    hits = sorted(run_dir(run_id).glob("features_*.parquet"))
    return pd.read_parquet(hits[0]) if hits else None


def cohort(run_id: str) -> pd.DataFrame | None:
    hits = sorted(run_dir(run_id).glob("cohort_*.csv"))
    return pd.read_csv(hits[0]) if hits else None


def profile_pairs(run_id: str) -> pd.DataFrame | None:
    return read_csv(run_id, "profile_pairs_both.csv")


def genuine_impostor(run_id: str) -> tuple[np.ndarray, np.ndarray] | None:
    """Відстані genuine- і impostor-пар. Основа всієї верифікації."""
    d = profile_pairs(run_id)
    if d is None or "kind" not in d.columns:
        return None
    g = d.loc[d.kind.str.startswith("genuine"), "dist"].to_numpy()
    i = d.loc[d.kind.str.startswith("impostor"), "dist"].to_numpy()
    return (g, i) if g.size and i.size else None


def eer_from(g: np.ndarray, i: np.ndarray) -> tuple[float, float]:
    """EER і поріг. Мала відстань = 'та сама людина', тому скор беремо зі знаком мінус."""
    from sklearn.metrics import roc_curve
    y = np.r_[np.ones(g.size), np.zeros(i.size)]
    s = np.r_[-g, -i]
    fpr, tpr, thr = roc_curve(y, s)
    fnr = 1 - tpr
    k = int(np.nanargmin(np.abs(fnr - fpr)))
    return float((fpr[k] + fnr[k]) / 2), float(-thr[k])


def bootstrap_eer(g: np.ndarray, i: np.ndarray, n: int = 2000, seed: int = 0) -> tuple[float, float]:
    """Бутстреп-CI для EER. PLAN.md вимагає інтервал, а не точкову оцінку.

    Ресемплюються genuine і impostor окремо — це зберігає їхнє співвідношення,
    яке в нас сильно незбалансоване (1117 проти 14160).
    """
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        gb = rng.choice(g, g.size, replace=True)
        ib = rng.choice(i, i.size, replace=True)
        out.append(eer_from(gb, ib)[0])
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def far_at_frr(g: np.ndarray, i: np.ndarray, frr_target: float) -> float:
    """FAR при заданому FRR — робоча точка, яку просить PLAN.md (1% і 10%)."""
    # FRR=f означає, що ми приймаємо (1-f) genuine-пар, тож поріг — квантиль 1-f
    thr = float(np.quantile(g, 1.0 - frr_target))
    return float((i < thr).mean())


def out_dirs() -> tuple[Path, Path, Path]:
    tables, figures, logs = PAPER / "tables", PAPER / "figures", PAPER / "logs"
    for d in (tables, figures, logs):
        d.mkdir(parents=True, exist_ok=True)
    return tables, figures, logs


def save_numbers(new: dict) -> Path:
    """numbers.json накопичується: таблиці й рисунки пишуть у нього незалежно."""
    p = PAPER / "numbers.json"
    cur = json.loads(p.read_text()) if p.exists() else {}
    cur.update(new)
    p.write_text(json.dumps(cur, indent=2, ensure_ascii=False, sort_keys=True))
    return p
