"""
Extract per-tick movement patterns (button presses + position) from a CS2 demo file.

Outputs a single CSV with columns:
    tick, round, player, team, alive, X, Y, Z,
    vel_x, vel_y, vel_z, yaw, pitch,
    forward, back, left, right, jump, duck

Usage:
    python3 extract_movement.py <demo.dem> [--output movement.csv]
    python3 extract_movement.py <demo.dem> --player "s1mple"
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from demoparser2 import DemoParser

# CS2 button bitmask (Source 2 engine)
BUTTON_BITS = {
    "attack":   0,   # IN_ATTACK
    "jump":     1,   # IN_JUMP
    "duck":     2,   # IN_DUCK
    "forward":  3,   # IN_FORWARD
    "back":     4,   # IN_BACK
    "left":     9,   # IN_MOVELEFT
    "right":    10,  # IN_MOVERIGHT
    "attack2":  11,  # IN_ATTACK2 (scope / secondary)
}

# Properties we want from each tick
TICK_PROPS = [
    "X", "Y", "Z",
    "velocity_X", "velocity_Y", "velocity_Z",
    "eye_angle_0", "eye_angle_1",     # pitch, yaw
    "is_alive",
    "team_num",
    "buttons",
    "name",
    "total_rounds_played",
]

CSV_HEADER = [
    "tick", "round", "player", "team", "alive",
    "X", "Y", "Z", "vel_x", "vel_y", "vel_z",
    "yaw", "pitch",
    "forward", "back", "left", "right",
    "jump", "duck", "attack", "attack2",
]


def decode_buttons(buttons_val):
    """Return dict of button states from bitmask."""
    val = int(buttons_val) if buttons_val is not None else 0
    return {name: int(bool(val & (1 << bit))) for name, bit in BUTTON_BITS.items()}


def team_label(team_num):
    mapping = {2: "T", 3: "CT"}
    return mapping.get(team_num, str(team_num))


def extract(demo_path: str, output_path: str, player_filter: str | None = None,
            every_n: int = 1):
    """
    Parse demo and write movement CSV.

    Args:
        demo_path:      path to .dem file
        output_path:    path for output CSV
        player_filter:  optional substring to filter player names
        every_n:        write every N-th tick (1 = all ticks, 2 = every other, etc.)
    """
    parser = DemoParser(demo_path)

    print(f"Parsing ticks from {demo_path} …")
    df = parser.parse_ticks(TICK_PROPS)
    print(f"  got {len(df)} tick-rows")

    if player_filter:
        mask = df["name"].str.contains(player_filter, case=False, na=False)
        df = df[mask]
        print(f"  filtered to {len(df)} rows for '{player_filter}'")

    if df.empty:
        print("No data — exiting.")
        sys.exit(1)

    # Subsample if requested
    if every_n > 1:
        df = df.iloc[::every_n]
        print(f"  subsampled to {len(df)} rows (every {every_n})")

    written = 0
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)

        for row in df.itertuples(index=False):
            rd = row._asdict()
            btns = decode_buttons(rd.get("buttons"))
            alive = 1 if rd.get("is_alive") else 0

            writer.writerow([
                rd.get("tick", 0),
                rd.get("total_rounds_played", 0),
                rd.get("name", ""),
                team_label(rd.get("team_num", 0)),
                alive,
                round(rd.get("X", 0), 1),
                round(rd.get("Y", 0), 1),
                round(rd.get("Z", 0), 1),
                round(rd.get("velocity_X", 0), 1),
                round(rd.get("velocity_Y", 0), 1),
                round(rd.get("velocity_Z", 0), 1),
                round(rd.get("eye_angle_1", 0), 2),
                round(rd.get("eye_angle_0", 0), 2),
                btns["forward"], btns["back"],
                btns["left"], btns["right"],
                btns["jump"], btns["duck"],
                btns["attack"], btns["attack2"],
            ])
            written += 1

    print(f"Done — wrote {written} rows to {output_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Extract movement patterns from CS2 demo")
    ap.add_argument("demo", help="Path to .dem file")
    ap.add_argument("-o", "--output", default=None,
                    help="Output CSV path (default: movement_pattern/<demo_stem>_movement.csv)")
    ap.add_argument("-p", "--player", default=None,
                    help="Filter by player name (substring, case-insensitive)")
    ap.add_argument("-n", "--every-n", type=int, default=1,
                    help="Record every N-th tick to reduce file size (default: 1 = all)")
    args = ap.parse_args()

    if args.output is None:
        stem = Path(args.demo).stem
        out_dir = Path(__file__).parent
        args.output = str(out_dir / f"{stem}_movement.csv")

    extract(args.demo, args.output, args.player, args.every_n)
