"""
Верифікація бітів маски `buttons` у CS2 на конкретній демці.

demoparser2 не віддає JUMP/DUCK/WALK окремими пропами, тому їх дістаємо з
бітмаски. Щоб не вірити константам на слово, кожен біт зіставляється:
  - з іменованими пропами, які парсер таки віддає (FORWARD/BACK/LEFT/RIGHT/
    FIRE/RIGHTCLICK) — очікуємо Jaccard = 1.00;
  - з фізикою руху для решти: JUMP проти is_airborne, DUCK проти duck_amount,
    WALK проти діапазону швидкості шифт-ходи.

Запускати на кожному новому патчі демок.

Usage:
    /usr/bin/python3 article5_movement/scripts/calibrate_buttons.py <demo.dem>
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from demoparser2 import DemoParser

PROPS = ["buttons", "FORWARD", "BACK", "LEFT", "RIGHT", "FIRE", "RIGHTCLICK",
         "is_airborne", "duck_amount", "velocity_X", "velocity_Y", "is_alive"]


def main(demo: str, every_n: int, max_bit: int) -> None:
    p = DemoParser(demo)
    h = p.parse_header()
    d = p.parse_ticks(PROPS)
    d = d[d["is_alive"] == True].dropna(subset=["buttons"]).iloc[::every_n]
    b = d["buttons"].to_numpy(dtype="uint64")
    spd = np.hypot(d["velocity_X"], d["velocity_Y"]).to_numpy()

    ref = {
        "FORWARD": d["FORWARD"].to_numpy(bool),
        "BACK": d["BACK"].to_numpy(bool),
        "LEFT": d["LEFT"].to_numpy(bool),
        "RIGHT": d["RIGHT"].to_numpy(bool),
        "FIRE": d["FIRE"].to_numpy(bool),
        "RIGHTCLICK": d["RIGHTCLICK"].to_numpy(bool),
        "AIRBORNE": d["is_airborne"].to_numpy(bool),
        "DUCK_AMT>0.1": (d["duck_amount"].to_numpy() > 0.1),
        "WALK_BAND(40..140)": ((spd > 40) & (spd < 140)),
    }

    print(f"демка: {demo}")
    print(f"мапа: {h.get('map_name')}  патч: {h.get('patch_version')}  рядків: {len(d)}\n")
    print(f"{'біт':>4} {'частота':>9}  найкращі відповідності (Jaccard / P(ref|bit))")
    for bit in range(max_bit):
        m = ((b >> np.uint64(bit)) & np.uint64(1)).astype(bool)
        if m.mean() < 1e-5 or m.mean() > 0.999:
            continue
        scored = []
        for k, v in ref.items():
            inter = int((m & v).sum())
            scored.append((k, inter / max(int((m | v).sum()), 1), inter / max(int(m.sum()), 1)))
        scored.sort(key=lambda t: -t[1])
        top = "  ".join(f"{k} {j:.2f}/{c:.2f}" for k, j, c in scored[:2])
        print(f"{bit:>4} {m.mean():>9.5f}  {top}")

    print("\nОчікувані біти: FIRE=0  JUMP=1  DUCK=2  FORWARD=3  BACK=4"
          "  MOVELEFT=9  MOVERIGHT=10  ATTACK2=11  WALK=16")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("demo")
    ap.add_argument("-n", "--every-n", type=int, default=4)
    ap.add_argument("--max-bit", type=int, default=34)
    a = ap.parse_args()
    main(a.demo, a.every_n, a.max_bit)
