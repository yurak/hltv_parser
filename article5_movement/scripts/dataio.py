"""Одне місце, яке знає, як прочитати таблицю датасету.

Датасет переїхав з CSV на parquet: `dataset_events.csv` важив 27.9 МБ уже на
21 демці, а на 108 це шар з 559 тис. подій. Аналітичні скрипти від цього не
мають залежати — вони просто просять таблицю за шляхом.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_table(path, **kw) -> pd.DataFrame:
    p = Path(path)
    if p.suffix in (".parquet", ".pq"):
        return pd.read_parquet(p)
    return pd.read_csv(p, **kw)
