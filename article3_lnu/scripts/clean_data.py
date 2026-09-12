"""
clean_data.py — reproducible cleaning for the CS2/CSGO feature-invariance article.

Fixes the two defects found in the article3 audit:
  1. Loads the *_clean.csv base AND coerces every stat column to numeric
     (pd.to_numeric errors='coerce'), so no feature is silently dropped due to '-' tokens.
  2. Logs sample sizes (n) at every filtering step.

Output: data/processed/combined_clean.csv  +  outputs/logs/cleaning_log.txt
"""
import os
import pandas as pd
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
PROCESSED = os.path.join(ROOT, "data", "processed")
LOGS = os.path.join(ROOT, "outputs", "logs")
os.makedirs(PROCESSED, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

META_COLS = ["full_url", "player_name", "game_version", "map", "age"]
# time_alive columns are textual ("1m 6s") — excluded from numeric analysis here.
TIME_COLS = ["time_alive_per_round", "ct_time_alive_per_round", "t_time_alive_per_round"]

log_lines = []
def log(msg):
    print(msg)
    log_lines.append(msg)

def load():
    cs2 = pd.read_csv(os.path.join(RAW, "map_stats_cs2_clean.csv"))
    csgo = pd.read_csv(os.path.join(RAW, "map_stats_csgo_clean.csv"))
    log(f"Loaded cs2_clean: {cs2.shape[0]} rows x {cs2.shape[1]} cols")
    log(f"Loaded csgo_clean: {csgo.shape[0]} rows x {csgo.shape[1]} cols")
    return cs2, csgo

def coerce_numeric(df):
    """Coerce every non-metadata, non-time column to numeric. Returns df + NaN report."""
    stat_cols = [c for c in df.columns if c not in META_COLS + TIME_COLS]
    nan_before = int(df[stat_cols].isna().sum().sum())
    for c in stat_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    nan_after = int(df[stat_cols].isna().sum().sum())
    return df, stat_cols, nan_before, nan_after

def main():
    cs2, csgo = load()
    combined = pd.concat([cs2, csgo], ignore_index=True)
    log(f"\nConcatenated: {combined.shape[0]} rows")

    # Filter: valid de_ maps + non-null game_version
    n0 = len(combined)
    combined = combined[combined["map"].str.startswith("de_", na=False)].copy()
    log(f"After keeping de_ maps only: {len(combined)} rows (dropped {n0 - len(combined)})")
    n1 = len(combined)
    combined = combined.dropna(subset=["game_version"]).copy()
    log(f"After dropping null game_version: {len(combined)} rows (dropped {n1 - len(combined)})")

    log(f"  cs2={int((combined.game_version=='cs2').sum())}, "
        f"csgo={int((combined.game_version=='csgo').sum())}")
    log(f"  maps ({combined['map'].nunique()}): {sorted(combined['map'].unique())}")

    # Coerce all stat columns to numeric (the key fix)
    combined, stat_cols, nb, na = coerce_numeric(combined)
    log(f"\nCoerced {len(stat_cols)} stat columns to numeric.")
    log(f"  NaN cells in stat columns: before={nb}, after coercion={na} "
        f"(added {na - nb} from '-'/garbage tokens)")

    # Per-feature NaN share (top offenders) — for the limitations section
    nan_share = (combined[stat_cols].isna().mean().sort_values(ascending=False) * 100).round(2)
    top = nan_share[nan_share > 0].head(15)
    log("\nTop columns by % NaN (after coercion):")
    for c, v in top.items():
        log(f"  {c}: {v}%")

    out = os.path.join(PROCESSED, "combined_clean.csv")
    combined.to_csv(out, index=False)
    log(f"\nSaved processed dataset: {out} ({combined.shape[0]} x {combined.shape[1]})")

    with open(os.path.join(LOGS, "cleaning_log.txt"), "w") as f:
        f.write("\n".join(log_lines) + "\n")

if __name__ == "__main__":
    main()
