"""
Валідація проксі-сигналів проти нативної маски кнопок.

Працює на демках, де маска `buttons` доступна (FACEIT). Порівнює канонічні
сигнали, які extract_ticks.py обчислює для ВСІХ демок, з істинними натисканнями:

    SPACE  проксі: фронт is_airborne з vz > 100   проти  біт 1 маски
    CTRL   проксі: duck_amount > 0.1              проти  біт 2
    SHIFT  проксі: is_walking                     проти  біт 16
    W/S/A/D, ЛКМ, ПКМ: іменовані пропи            проти  бітів 3/4/9/10/0/11

Для подієвих проксі (SPACE) точність рахується на рівні ПОДІЙ: натискання
відповідає проксі, якщо фронти збігаються в межах вікна TOL тіків.

Usage:
    /usr/bin/python3 article5_movement/scripts/validate_signals.py <ticks.parquet>
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

TOL = 8      # тіків допуску для збігу подій


def rising(x: np.ndarray) -> np.ndarray:
    return np.flatnonzero((x[1:] == 1) & (x[:-1] == 0)) + 1


def event_match(a: np.ndarray, b: np.ndarray, tol: int = TOL) -> tuple[float, float]:
    """Precision/recall збігу фронтів a (проксі) з фронтами b (істина)."""
    ea, eb = rising(a), rising(b)
    if ea.size == 0 or eb.size == 0:
        return np.nan, np.nan
    hit_a = sum(1 for t in ea if np.any(np.abs(eb - t) <= tol))
    hit_b = sum(1 for t in eb if np.any(np.abs(ea - t) <= tol))
    return hit_a / ea.size, hit_b / eb.size


def main(path: str) -> None:
    df = pd.read_parquet(path).sort_values(["steamid", "round", "tick"])
    nat = [c for c in df.columns if c.startswith("native_")]
    if not nat:
        print("У цій демці немає нативної маски `buttons` — валідувати нічим.")
        return
    print(f"рядків: {len(df)}  |  нативні сигнали: {len(nat)}\n")

    # --- потікові сигнали: збіг станів ---
    print("ПОТІКОВІ СИГНАЛИ (збіг станів по тіках)")
    print(f"{'сигнал':<12} {'згода':>8} {'Jaccard':>9} {'частка проксі':>14} {'частка істини':>14}")
    for proxy, native in (("FORWARD", "native_FORWARD"), ("BACK", "native_BACK"),
                          ("LEFT", "native_LEFT"), ("RIGHT", "native_RIGHT"),
                          ("FIRE", "native_FIRE"), ("RIGHTCLICK", "native_RIGHTCLICK"),
                          ("WALK", "native_WALK"), ("DUCK", "native_DUCK")):
        if native not in df.columns:
            continue
        a = df[proxy].to_numpy(bool)
        b = df[native].to_numpy(bool)
        agree = float((a == b).mean())
        jac = float((a & b).sum() / max((a | b).sum(), 1))
        print(f"{proxy:<12} {agree:>8.4f} {jac:>9.4f} {a.mean():>14.4f} {b.mean():>14.4f}")

    # --- подієві сигнали: збіг фронтів ---
    print(f"\nПОДІЄВІ СИГНАЛИ (фронти, допуск {TOL} тіків)")
    print(f"{'сигнал':<12} {'precision':>10} {'recall':>8} {'подій проксі':>13} {'подій істини':>13}")
    for proxy, native in (("JUMP", "native_JUMP"), ("DUCK", "native_DUCK")):
        if native not in df.columns:
            continue
        P, R, na, nb = [], [], 0, 0
        for _, g in df.groupby(["steamid", "round"], sort=False):
            a = g[proxy].to_numpy(np.int8)
            b = g[native].to_numpy(np.int8)
            p, r = event_match(a, b)
            if np.isfinite(p):
                P.append(p); R.append(r)
            na += rising(a).size; nb += rising(b).size
        print(f"{proxy:<12} {np.mean(P):>10.3f} {np.mean(R):>8.3f} {na:>13} {nb:>13}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ticks")
    main(ap.parse_args().ticks)
