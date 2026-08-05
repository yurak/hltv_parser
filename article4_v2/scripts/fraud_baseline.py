"""
Baseline fraud-detection pipeline for df.csv (~11k transactions, May 2015).

Pipeline:
  1. Parse + sort chronologically (time is the only safe ordering).
  2. Build features:
       - calendar  (hour, dow, weekend, night, afternoon-peak, hour sin/cos)
       - amount    (log, mod 10, mod 50, has_cents, log of mod-class)
       - velocity  (per-card, strictly PAST-only: counts / sums / gaps in windows)
       - identity  (BIN = first 6 digits; Amount as categorical-ish)
  3. Time-based train/test split (no shuffling — chronological holdout).
  4. Bayesian-smoothed target encoding for high-cardinality Amount & BIN,
     fit on TRAIN only and applied to TEST (no leakage).
  5. Two models: LogisticRegression + HistGradientBoostingClassifier.
  6. Metrics: ROC-AUC, PR-AUC, precision/recall @ top-k, feature importances.

Run:  python3 fraud_baseline.py
"""

from __future__ import annotations
import os
import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score, average_precision_score,
    precision_recall_fscore_support, confusion_matrix,
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "df.csv")
RANDOM_STATE = 42
TRAIN_FRAC = 0.75          # first 75 % of time → train, last 25 % → test


# ---------------------------------------------------------------------------
# 1. load
# ---------------------------------------------------------------------------
def load() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, index_col=0)
    df["Date"] = pd.to_datetime(df["Date"])
    df["y"] = (df["CBK"] == "Yes").astype(int)
    df["BIN"] = df["Card Number"].str[:6]
    df = df.sort_values("Date").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# 2. feature engineering
# ---------------------------------------------------------------------------
def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    df["hour"] = df["Date"].dt.hour
    df["dow"] = df["Date"].dt.dayofweek
    df["weekend"] = (df["dow"] >= 5).astype(int)
    df["night"] = df["hour"].isin(range(0, 6)).astype(int)
    df["afternoon_peak"] = df["hour"].isin([15, 16]).astype(int)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df["dow"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["dow"] / 7)
    return df


def add_amount_features(df: pd.DataFrame) -> pd.DataFrame:
    df["amount_log"]   = np.log1p(df["Amount"])
    df["amt_mod_10"]   = (df["Amount"] % 10 == 0).astype(int)
    df["amt_mod_50"]   = (df["Amount"] % 50 == 0).astype(int)
    df["amt_mod_100"]  = (df["Amount"] % 100 == 0).astype(int)
    df["has_cents"]    = (df["Amount"] % 1 != 0).astype(int)
    df["amount_gt_200"] = (df["Amount"] > 200).astype(int)
    df["amount_gt_500"] = (df["Amount"] > 500).astype(int)
    return df


def add_velocity_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    All velocity features are computed using ONLY strictly-earlier rows of the
    same card (shift(1) + rolling on time index) — no look-ahead.
    """
    df = df.sort_values(["Card Number", "Date"]).reset_index(drop=True)

    # time since previous tx on same card (minutes)
    prev_t = df.groupby("Card Number")["Date"].shift(1)
    df["gap_min_prev"] = (df["Date"] - prev_t).dt.total_seconds() / 60.0
    df["gap_min_prev"] = df["gap_min_prev"].fillna(10 * 24 * 60)       # first tx → 10 days

    # previous amount on same card
    prev_amt = df.groupby("Card Number")["Amount"].shift(1)
    df["prev_amount"]   = prev_amt
    df["same_amt_prev"] = (df["Amount"] == prev_amt).astype(int)
    df["same_amount_10min"] = (
        (df["Amount"] == prev_amt) & (df["gap_min_prev"] <= 10)
    ).astype(int)

    # rolling counts / sums on a time index per card (strictly past)
    df = df.set_index("Date")
    df["cum_card_count"] = df.groupby("Card Number").cumcount()       # excludes self
    for win in ["1h", "6h", "24h"]:
        # rolling is inclusive of current row -> subtract 1 to make it "past only"
        cnt = (
            df.groupby("Card Number")["Amount"]
              .rolling(win).count().reset_index(level=0, drop=True) - 1
        )
        amt = (
            df.groupby("Card Number")["Amount"]
              .rolling(win).sum().reset_index(level=0, drop=True) - df["Amount"]
        )
        df[f"n_tx_card_{win}"]  = cnt.clip(lower=0).fillna(0)
        df[f"sum_amt_card_{win}"] = amt.clip(lower=0).fillna(0)
    df = df.reset_index()

    # put back in chronological order for the time split
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = add_calendar_features(df)
    df = add_amount_features(df)
    df = add_velocity_features(df)
    return df


# ---------------------------------------------------------------------------
# 3. target encoding (past-only)
# ---------------------------------------------------------------------------
def smoothed_target_mean(values: pd.Series, target: pd.Series, prior: float,
                         k: float = 20.0) -> dict:
    """
    Bayesian smoothing:
        enc[v] = (sum_y + k * prior) / (count + k)
    Returns dict {value: encoded_rate}.
    """
    agg = pd.DataFrame({"v": values, "y": target}).groupby("v")["y"].agg(["sum", "count"])
    enc = (agg["sum"] + k * prior) / (agg["count"] + k)
    return enc.to_dict()


def apply_encoding(values: pd.Series, mapping: dict, default: float) -> pd.Series:
    return values.map(mapping).fillna(default).astype(float)


# ---------------------------------------------------------------------------
# 4. split + train + eval
# ---------------------------------------------------------------------------
def time_split(df: pd.DataFrame, train_frac: float = TRAIN_FRAC):
    cutoff_idx = int(len(df) * train_frac)
    cutoff_time = df["Date"].iloc[cutoff_idx]
    train = df.iloc[:cutoff_idx].copy()
    test  = df.iloc[cutoff_idx:].copy()
    print(f"[split] cutoff = {cutoff_time}   train={len(train)}   test={len(test)}")
    print(f"[split] train fraud rate = {train['y'].mean():.3%}")
    print(f"[split] test  fraud rate = {test['y'].mean():.3%}\n")
    return train, test


FEATURE_COLS = [
    # calendar
    "hour", "dow", "weekend", "night", "afternoon_peak",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    # amount
    "Amount", "amount_log",
    "amt_mod_10", "amt_mod_50", "amt_mod_100", "has_cents",
    "amount_gt_200", "amount_gt_500",
    # velocity
    "gap_min_prev", "cum_card_count",
    "n_tx_card_1h", "n_tx_card_6h", "n_tx_card_24h",
    "sum_amt_card_1h", "sum_amt_card_6h", "sum_amt_card_24h",
    "same_amt_prev", "same_amount_10min",
    # target-encoded identity
    "bin_te", "amount_te",
]


def prepare_xy(train: pd.DataFrame, test: pd.DataFrame):
    prior = train["y"].mean()

    # target encodings fit on TRAIN ONLY
    bin_enc = smoothed_target_mean(train["BIN"], train["y"], prior, k=20.0)
    amt_enc = smoothed_target_mean(train["Amount"], train["y"], prior, k=10.0)

    for part in (train, test):
        part["bin_te"]    = apply_encoding(part["BIN"], bin_enc, prior)
        part["amount_te"] = apply_encoding(part["Amount"], amt_enc, prior)

    X_tr, y_tr = train[FEATURE_COLS].values, train["y"].values
    X_te, y_te = test[FEATURE_COLS].values,  test["y"].values
    return X_tr, y_tr, X_te, y_te


def report(name: str, y_true: np.ndarray, score: np.ndarray) -> None:
    roc = roc_auc_score(y_true, score)
    ap  = average_precision_score(y_true, score)
    print(f"\n===== {name} =====")
    print(f"ROC-AUC : {roc:.4f}")
    print(f"PR-AUC  : {ap:.4f}  (base rate = {y_true.mean():.4f})")

    # precision / recall at top-k
    for k_frac in [0.01, 0.03, 0.05, 0.10]:
        k = max(1, int(len(y_true) * k_frac))
        top_idx = np.argsort(-score)[:k]
        flagged = y_true[top_idx]
        prec = flagged.mean()
        rec  = flagged.sum() / y_true.sum()
        print(f"  top-{int(k_frac*100):>2d}% (n={k:4d}) → "
              f"precision={prec:.3f}  recall={rec:.3f}  "
              f"({int(flagged.sum())}/{int(y_true.sum())} caught)")

    # classification @ 0.5 threshold (for reference only)
    pred = (score >= 0.5).astype(int)
    if pred.sum() > 0:
        p, r, f, _ = precision_recall_fscore_support(
            y_true, pred, average="binary", zero_division=0
        )
        tn, fp, fn, tp = confusion_matrix(y_true, pred).ravel()
        print(f"  @ th=0.5 → P={p:.3f} R={r:.3f} F1={f:.3f}  "
              f"TP={tp} FP={fp} FN={fn} TN={tn}")


def train_logreg(X_tr, y_tr, X_te):
    # scale for linear model
    sc = StandardScaler()
    Xtr = sc.fit_transform(X_tr)
    Xte = sc.transform(X_te)
    m = LogisticRegression(
        max_iter=2000, class_weight="balanced",
        C=1.0, random_state=RANDOM_STATE,
    )
    m.fit(Xtr, y_tr)
    return m, m.predict_proba(Xte)[:, 1], sc


def train_hgb(X_tr, y_tr, X_te):
    m = HistGradientBoostingClassifier(
        max_depth=6, learning_rate=0.05, max_iter=400,
        l2_regularization=1.0, min_samples_leaf=20,
        class_weight="balanced", random_state=RANDOM_STATE,
    )
    m.fit(X_tr, y_tr)
    return m, m.predict_proba(X_te)[:, 1]


def permutation_importance_hgb(model, X_te, y_te, n_repeats: int = 3):
    """Quick permutation importance on PR-AUC (fraud-relevant metric)."""
    rng = np.random.default_rng(RANDOM_STATE)
    base = average_precision_score(y_te, model.predict_proba(X_te)[:, 1])
    rows = []
    for j, name in enumerate(FEATURE_COLS):
        drops = []
        for _ in range(n_repeats):
            Xp = X_te.copy()
            Xp[:, j] = rng.permutation(Xp[:, j])
            ap = average_precision_score(y_te, model.predict_proba(Xp)[:, 1])
            drops.append(base - ap)
        rows.append((name, float(np.mean(drops))))
    rows.sort(key=lambda t: -t[1])
    print("\n===== feature importance (PR-AUC drop when shuffled) =====")
    for name, d in rows:
        print(f"  {name:<22s}  Δ PR-AUC = {d:+.4f}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> None:
    df = load()
    print(f"[load] {len(df)} rows   "
          f"{df['Date'].min()} → {df['Date'].max()}   "
          f"fraud={df['y'].mean():.3%}\n")

    df = build_features(df)
    train, test = time_split(df)
    X_tr, y_tr, X_te, y_te = prepare_xy(train, test)

    # baselines
    _, score_lr, _  = train_logreg(X_tr, y_tr, X_te)
    report("LogisticRegression", y_te, score_lr)

    hgb, score_hgb = train_hgb(X_tr, y_tr, X_te)
    report("HistGradientBoosting", y_te, score_hgb)

    permutation_importance_hgb(hgb, X_te, y_te, n_repeats=3)


if __name__ == "__main__":
    main()
