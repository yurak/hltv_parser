"""
load_external.py — adapt the IEEE-CIS Fraud Detection dataset (Vesta, real data)
to the 4-column schema used by analyze.py, keeping only the fields the velocity
method needs and dropping the other ~390 anonymised columns.

IEEE-CIS field            ->  our schema
  card1 (card id proxy)   ->  Card Number   (per-card entity for velocity features)
  card5 (issuer proxy)    ->  BIN           (target-encoding "identity" family proxy)
  TransactionDT (seconds) ->  Date          (= reference date + offset; only relative
                                             time matters for velocity gaps)
  TransactionAmt          ->  Amount
  isFraud (0/1)           ->  CBK ("Yes"/"No")

LIMITATIONS (declare these in the manuscript):
  * IEEE-CIS has no clean card number; card1 is a card-id PROXY → velocity features
    are computed per card1 (entity-resolution approximation).
  * No real BIN; card5 is an issuer-level PROXY for the identity family.
  * TransactionDT is an offset in seconds from an undisclosed reference; the community
    consensus reference is 2017-12-01. Absolute date does not affect velocity gaps;
    it only sets the phase of hour/day-of-week features.

Usage:
  python scripts/load_external.py \
      --input data/raw/train_transaction.csv \
      --output data/raw/df_ieeecis.csv

Then run the full pipeline on it WITHOUT overwriting the primary outputs:
  FRAUD_DATA=$PWD/data/raw/df_ieeecis.csv FRAUD_OUT=$PWD/outputs_ieeecis \
      python scripts/analyze.py
"""
from __future__ import annotations
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DATE = "2017-12-01"          # community consensus for TransactionDT=0
KEEP = ["TransactionID", "isFraud", "TransactionDT", "TransactionAmt",
        "card1", "card5"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default=str(ROOT / "data" / "raw" / "train_transaction.csv"),
                    help="path to IEEE-CIS train_transaction.csv")
    ap.add_argument("--output", default=str(ROOT / "data" / "raw" / "df_ieeecis.csv"))
    ap.add_argument("--reference-date", default=REFERENCE_DATE)
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        raise SystemExit(
            f"[load_external] not found: {src}\n"
            "Download IEEE-CIS train_transaction.csv from Kaggle "
            "(competition: ieee-fraud-detection) and place it there, then rerun."
        )

    # read only the columns we keep — avoids loading 393 columns / saves memory
    usecols = [c for c in KEEP]
    df = pd.read_csv(src, usecols=lambda c: c in usecols)
    n0 = len(df)

    # drop rows without a card-id proxy (cannot place them in a card sequence)
    df = df.dropna(subset=["card1"]).copy()
    n1 = len(df)

    ref = pd.Timestamp(args.reference_date)
    out = pd.DataFrame({
        "Card Number": df["card1"].astype("Int64").astype(str),
        "Date": ref + pd.to_timedelta(df["TransactionDT"].astype("int64"), unit="s"),
        "Amount": df["TransactionAmt"].astype(float),
        "CBK": df["isFraud"].map({0: "No", 1: "Yes"}),
        # issuer proxy; missing card5 → "UNK" sentinel so the group is not dropped
        "BIN": df["card5"].astype("Int64").astype(str).replace("<NA>", "UNK"),
    })
    out["BIN"] = out["BIN"].fillna("UNK")
    out = out.sort_values("Date").reset_index(drop=True)
    out.to_csv(args.output)  # index written → analyze.py reads with index_col=0

    fr = (out["CBK"] == "Yes").mean()
    print(f"[load_external] input rows: {n0}; kept (card1 present): {n1}")
    print(f"[load_external] unique card1: {out['Card Number'].nunique()}; "
          f"unique card5(BIN proxy): {out['BIN'].nunique()}")
    print(f"[load_external] fraud rate: {fr:.3%}; "
          f"date range: {out['Date'].min()} -> {out['Date'].max()}")
    print(f"[load_external] amount: mean={out['Amount'].mean():.2f}, "
          f"median={out['Amount'].median():.2f}, max={out['Amount'].max():.2f}")
    print(f"[saved] {args.output}  ({len(out)} rows, 5 columns)")


if __name__ == "__main__":
    main()
