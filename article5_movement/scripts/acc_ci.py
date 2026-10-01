#!/usr/bin/env python3
"""95 % довірчі інтервали точності між серіями (рецензія v0.2, зауваження C).

Досі інтервал мав лише EER; точності груп і підмножин друкувались точковими
оцінками. Незалежна одиниця — серія, тому бутстреп кластерний: ресемплюються
серії з поверненням, а точність рахується за всіма раундами вибраних серій.
Передбачення — ті самі, що в ablate_channel.py (кожна серія по черзі тестова,
z у межах матчу, кращий із RF і LDA), тож точкові оцінки збігаються з T5/T11.

    /usr/bin/python3 scripts/acc_ci.py --run-id 2026-09-27_mirage_n136_fix
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, cross_val_predict

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze as A
import paperlib as P
from cross_match import _clf
from review_checks import channels, load

N_BOOT = 2000


def predict(Z: pd.DataFrame, cols: list[str], kind: str) -> np.ndarray:
    g = Z["series_id"].to_numpy()
    return cross_val_predict(_clf(kind), Z[cols].to_numpy(), Z["player"].to_numpy(),
                             cv=GroupKFold(n_splits=len(np.unique(g))), groups=g, n_jobs=1)


def cluster_ci(correct: np.ndarray, series: np.ndarray, n: int, seed: int = 0) -> tuple[float, float]:
    ids, inv = np.unique(series, return_inverse=True)
    hits = np.bincount(inv, weights=correct)
    size = np.bincount(inv)
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(ids), size=(n, len(ids)))
    acc = hits[pick].sum(1) / size[pick].sum(1)
    return float(np.percentile(acc, 2.5)), float(np.percentile(acc, 97.5))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    a = ap.parse_args()

    raw, feats, ecols = load(a.run_id)
    Z = raw.copy()
    Z[feats] = Z.groupby("match_id")[feats].transform(lambda s: (s - s.mean()) / (s.std() + 1e-9))
    ch = channels(feats, ecols)
    sets = {"all": ch["all"], "keydyn": ch["keydyn"],
            "micro": [c for c in A.MICRO if c in feats],
            "micro_clean": ch["micro_clean"],
            "habit": [c for c in A.HABIT if c in feats], "event": ecols,
            "macro": [c for c in A.MACRO if c in feats],
            "loco": ch["loco"], "combat": ch["combat"]}
    y, s = Z["player"].to_numpy(), Z["series_id"].to_numpy()
    rows = []
    for name, cols in sets.items():
        best = None
        for kind in ("rf", "lda"):
            ok = (predict(Z, cols, kind) == y).astype(float)
            if best is None or ok.mean() > best[1].mean():
                best = (kind, ok)
        kind, ok = best
        lo, hi = cluster_ci(ok, s, a.n_boot)
        rows.append({"набір": name, "ознак": len(cols), "класифікатор": kind,
                     "між серіями": round(float(ok.mean()), 4),
                     "CI_low": round(lo, 4), "CI_high": round(hi, 4)})
        print(f"{name:<12} {len(cols):>3} {kind:<3} {ok.mean():.4f} [{lo:.4f}; {hi:.4f}]")
    out = P.run_dir(a.run_id) / "acc_ci.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
