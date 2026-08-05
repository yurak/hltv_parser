"""
explore_ieeecis.py — understand the NATURE of fraud in IEEE-CIS using the
dataset's OWN behavioral features (not the Brazilian card1-velocity proxy).

Groups IEEE-CIS native features into behavioral families and measures which
family separates fraud, then characterises the fraud regime with interpretable
cuts (product type, card network/type, card age, billing-shipping distance).

Writes outputs_ieeecis_native/{tables,logs}. Read-only on the raw file.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import f_oneway
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

RAW = Path.home() / "Downloads" / "ieee-fraud-detection" / "train_transaction.csv"
OUT = Path(__file__).resolve().parent.parent / "outputs_ieeecis_native"
(OUT / "tables").mkdir(parents=True, exist_ok=True)
(OUT / "logs").mkdir(parents=True, exist_ok=True)
_LOG = (OUT / "logs" / "explore_log.txt").open("w", encoding="utf-8")
def log(m): print(m); _LOG.write(m + "\n"); _LOG.flush()

C = [f"C{i}" for i in range(1, 15)]            # entity-linkage counts (velocity-type)
D = [f"D{i}" for i in range(1, 16)]            # event timedeltas (velocity-type)
USE = (["isFraud", "TransactionDT", "TransactionAmt", "ProductCD",
        "card1", "card2", "card3", "card4", "card5", "card6",
        "addr1", "dist1"] + C + D)


def main():
    df = pd.read_csv(RAW, usecols=lambda c: c in USE)
    y = df["isFraud"].values
    base = y.mean()
    log(f"N={len(df)}, fraud={y.sum()} ({base:.3%})")

    # temporal from TransactionDT (ref 2017-12-01)
    dt = pd.Timestamp("2017-12-01") + pd.to_timedelta(df["TransactionDT"], unit="s")
    h, dow = dt.dt.hour, dt.dt.dayofweek
    tmp = pd.DataFrame({
        "hour_sin": np.sin(2*np.pi*h/24), "hour_cos": np.cos(2*np.pi*h/24),
        "dow_sin": np.sin(2*np.pi*dow/7), "dow_cos": np.cos(2*np.pi*dow/7),
        "weekend": (dow >= 5).astype(int), "night": h.isin(range(0, 6)).astype(int)})
    amt = pd.DataFrame({"amount_log": np.log1p(df["TransactionAmt"]),
                        "has_cents": (df["TransactionAmt"] % 1 != 0).astype(int)})

    families = {
        "temporal (час доби/тижня)": tmp,
        "timedelta D (інтервали подій)": df[D].apply(pd.to_numeric, errors="coerce"),
        "count C (зв'язки картка/адреса)": df[C].apply(pd.to_numeric, errors="coerce"),
        "amount (структура суми)": amt,
    }

    # ---- per-family separability ----
    log("\n=== Розділювальна сила сімейств (рідні ознаки IEEE-CIS) ===")
    rng = np.random.default_rng(42)
    idx = rng.choice(len(df), size=5000, replace=False)
    rows = []
    for name, X in families.items():
        Xi = X.fillna(X.median(numeric_only=True)).to_numpy(dtype=float)
        Xs = StandardScaler().fit_transform(Xi)
        sil = silhouette_score(Xs[idx], y[idx])
        # mean univariate F across the family
        Fs = []
        for j in range(Xi.shape[1]):
            a, b = Xi[y == 0, j], Xi[y == 1, j]
            if a.var() == 0 and b.var() == 0:
                continue
            Fs.append(f_oneway(a, b)[0])
        rows.append({"family": name, "n_features": X.shape[1],
                     "silhouette": round(sil, 3), "mean_anova_F": round(np.nanmean(Fs), 1)})
    tbl = pd.DataFrame(rows).sort_values("silhouette", ascending=False)
    tbl.to_csv(OUT / "tables" / "family_separability.csv", index=False)
    log(tbl.to_string(index=False))

    # ---- nature of fraud: interpretable cuts ----
    def cut(col, label, mapper=None, bins=None):
        s = df[col]
        if bins is not None:
            s = pd.cut(pd.to_numeric(s, errors="coerce"), bins)
        g = pd.DataFrame({"g": s, "y": y}).groupby("g", observed=True)["y"]
        out = (g.mean()*100).round(2).astype(str) + "%  (n=" + g.size().astype(str) + ")"
        log(f"\n--- {label} ---")
        for k, v in out.items():
            log(f"  {k}: {v}")

    log("\n=== Природа фроду: інтерпретовані зрізи (база = %.2f%%) ===" % (base*100))
    cut("ProductCD", "Тип продукту (ProductCD)")
    cut("card4", "Платіжна мережа (card4)")
    cut("card6", "Тип картки (card6)")
    cut("D1", "Вік картки D1, днів від першої транзакції",
        bins=[-1, 0, 7, 30, 90, 365, 10000])
    cut("dist1", "Відстань білінг–доставка dist1",
        bins=[-1, 0, 10, 100, 1000, 100000])
    cut("C2", "Лічильник C2 (к-сть зв'язків)",
        bins=[-1, 0, 1, 3, 10, 100000])
    log("\n=== DONE ===")
    _LOG.close()


if __name__ == "__main__":
    main()
