"""
analyze.py — feature-invariance analysis (corrected v2).

Invariance is defined STRICTLY by effect size (audit fix #2):
  - Maps:    one-way ANOVA, invariant if eta-squared < 0.06
  - Version: Mann-Whitney U, invariant if Cohen's d < 0.5
  - Side:    paired t-test, invariant if paired Cohen's d < 0.5
p-values are reported for reference only, never as the invariance criterion.

Inputs : data/processed/combined_clean.csv
Outputs: outputs/tables/{map,version,side}_invariance.csv,
         outputs/tables/invariant_features_summary.csv,
         outputs/tables/map_invariance_by_version.csv  (sensitivity),
         outputs/logs/analysis_log.txt
"""
import os
import pandas as pd
import numpy as np
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
TABLES = os.path.join(ROOT, "outputs", "tables")
LOGS = os.path.join(ROOT, "outputs", "logs")
os.makedirs(TABLES, exist_ok=True)

META_COLS = ["full_url", "player_name", "game_version", "map", "age"]
TIME_COLS = ["time_alive_per_round", "ct_time_alive_per_round", "t_time_alive_per_round"]
ETA_THRESH = 0.06
D_THRESH = 0.5

log_lines = []
def log(m):
    print(m); log_lines.append(m)

def feature_cols(df):
    return [c for c in df.columns if c not in META_COLS + TIME_COLS]

def overall_features(cols):
    return [c for c in cols if not c.startswith("ct_") and not c.startswith("t_")]

def eta_squared(groups):
    alld = pd.concat([pd.Series(g) for g in groups])
    gm = alld.mean()
    ssb = sum(len(g) * (g.mean() - gm) ** 2 for g in groups)
    sst = ((alld - gm) ** 2).sum()
    return ssb / sst if sst > 0 else 0.0

def cohens_d_independent(a, b):
    ps = np.sqrt((a.std() ** 2 + b.std() ** 2) / 2)
    return abs(a.mean() - b.mean()) / ps if ps > 0 else 0.0

def map_invariance(df, feats, label="map_invariance"):
    maps = df["map"].unique()
    rows = []
    for f in feats:
        groups = [df[df["map"] == m][f].dropna() for m in maps]
        groups = [g for g in groups if len(g) > 1]
        if len(groups) < 2:
            continue
        F, p = stats.f_oneway(*groups)
        eta = eta_squared(groups)
        rows.append({"feature": f, "f_statistic": F, "p_value": p,
                     "eta_squared": eta, "invariant": eta < ETA_THRESH})
    out = pd.DataFrame(rows).sort_values("eta_squared").reset_index(drop=True)
    return out

def version_invariance(df, feats):
    a_ = df[df.game_version == "cs2"]; b_ = df[df.game_version == "csgo"]
    rows = []
    for f in feats:
        a = a_[f].dropna(); b = b_[f].dropna()
        if len(a) < 10 or len(b) < 10:
            continue
        U, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        d = cohens_d_independent(a, b)
        rows.append({"feature": f, "cs2_mean": a.mean(), "csgo_mean": b.mean(),
                     "difference": a.mean() - b.mean(), "n_cs2": len(a), "n_csgo": len(b),
                     "p_value": p, "cohens_d": d, "invariant": d < D_THRESH})
    return pd.DataFrame(rows).sort_values("cohens_d").reset_index(drop=True)

def side_invariance(df, cols):
    bases = set()
    for c in cols:
        if c.startswith("ct_"): bases.add(c[3:])
        elif c.startswith("t_"): bases.add(c[2:])
        else: bases.add(c)
    rows = []
    for bf in sorted(bases):
        ctc, tc = f"ct_{bf}", f"t_{bf}"
        if ctc not in df.columns or tc not in df.columns:
            continue
        m = df[ctc].notna() & df[tc].notna()
        cv, tv = df.loc[m, ctc], df.loc[m, tc]
        if len(cv) < 10:
            continue
        t_stat, p = stats.ttest_rel(cv, tv)
        diff = cv - tv
        d = abs(diff.mean()) / diff.std() if diff.std() > 0 else 0.0
        rows.append({"feature": bf, "ct_mean": cv.mean(), "t_mean": tv.mean(),
                     "difference": cv.mean() - tv.mean(), "n_pairs": len(cv),
                     "t_statistic": t_stat, "p_value": p, "cohens_d": d,
                     "invariant": d < D_THRESH})
    return pd.DataFrame(rows).sort_values("cohens_d").reset_index(drop=True)

def main():
    df = pd.read_csv(os.path.join(PROCESSED, "combined_clean.csv"))
    cols = feature_cols(df)
    feats = overall_features(cols)
    log("=" * 60)
    log("FEATURE INVARIANCE ANALYSIS (corrected v2)")
    log("=" * 60)
    log(f"Rows: {len(df)} (cs2={int((df.game_version=='cs2').sum())}, "
        f"csgo={int((df.game_version=='csgo').sum())})")
    log(f"Numeric stat columns: {len(cols)} | overall (base) features: {len(feats)}")
    log(f"Invariance criteria: eta^2<{ETA_THRESH} (maps); Cohen's d<{D_THRESH} (version, side)")

    mp = map_invariance(df, feats)
    vr = version_invariance(df, feats)
    sd = side_invariance(df, cols)

    mp.to_csv(os.path.join(TABLES, "map_invariance.csv"), index=False)
    vr.to_csv(os.path.join(TABLES, "version_invariance.csv"), index=False)
    sd.to_csv(os.path.join(TABLES, "side_invariance.csv"), index=False)

    map_inv = set(mp[mp.invariant].feature)
    ver_inv = set(vr[vr.invariant].feature)
    side_inv = set(sd[sd.invariant].feature)
    universal = map_inv & ver_inv
    triple = universal & side_inv

    log("\n--- RESULTS ---")
    log(f"Map-invariant   : {len(map_inv)}/{len(mp)} ({len(map_inv)/len(mp)*100:.1f}%)")
    log(f"Version-invariant: {len(ver_inv)}/{len(vr)} ({len(ver_inv)/len(vr)*100:.1f}%)")
    log(f"Side-invariant  : {len(side_inv)}/{len(sd)} ({len(side_inv)/len(sd)*100:.1f}%)")
    log(f"Universal (map & version): {len(universal)}")
    log(f"Triple (map & version & side): {len(triple)}")
    log(f"  triple set: {sorted(triple)}")

    # Sensitivity: map invariance within each game version (version is a confound when pooled)
    sens_rows = []
    for ver in ["cs2", "csgo"]:
        sub = df[df.game_version == ver]
        mv = map_invariance(sub, feats)
        inv = set(mv[mv.invariant].feature)
        sens_rows.append({"version": ver, "n_features": len(mv), "n_map_invariant": len(inv),
                          "pct": round(len(inv)/len(mv)*100, 1)})
        mv["version"] = ver
        sens_rows_df = mv
        mv.to_csv(os.path.join(TABLES, f"map_invariance_{ver}.csv"), index=False)
    sens = pd.DataFrame(sens_rows)
    sens.to_csv(os.path.join(TABLES, "map_invariance_by_version.csv"), index=False)
    log("\nSensitivity (map invariance within each version):")
    for _, r in sens.iterrows():
        log(f"  {r['version']}: {int(r['n_map_invariant'])}/{int(r['n_features'])} ({r['pct']}%)")

    # Summary table (long form)
    def rows_for(name, s, total):
        return {"dimension": name, "n_invariant": len(s), "n_total": total,
                "pct": round(len(s)/total*100, 1), "features": "; ".join(sorted(s))}
    summary = pd.DataFrame([
        rows_for("map", map_inv, len(mp)),
        rows_for("version", ver_inv, len(vr)),
        rows_for("side", side_inv, len(sd)),
        rows_for("universal_map_version", universal, len(mp)),
        rows_for("triple_map_version_side", triple, len(sd)),
    ])
    summary.to_csv(os.path.join(TABLES, "invariant_features_summary.csv"), index=False)

    with open(os.path.join(LOGS, "analysis_log.txt"), "w") as f:
        f.write("\n".join(log_lines) + "\n")
    log(f"\nTables saved to {TABLES}")

if __name__ == "__main__":
    main()
