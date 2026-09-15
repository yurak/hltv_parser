"""
Батч-обробка всіх демок з data/raw/ у єдиний датасет.

Для кожної демки: тіки -> ознаки -> події, з міткою match_id (щоб потім робити
міжматчеву валідацію: навчання на одних матчах, перевірка на іншому).
Проміжний parquet кешується — повторний запуск обробляє лише нові демки.

На виході:
    outputs/dataset_features.csv        ознаки на (матч, гравець, сторона, раунд)
    outputs/dataset_events.csv          усі події (стопи, піки)
    outputs/dataset_event_features.csv  агрегати подій на раунд
    outputs/coverage.csv                покриття: скільки раундів на гравця/сторону/матч

Usage:
    /usr/bin/python3 article5_movement/scripts/build_dataset.py
    /usr/bin/python3 article5_movement/scripts/build_dataset.py --map de_mirage --min-rounds 25
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from demoparser2 import DemoParser

import events as EV
import extract_ticks as EX
import features as FT

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
TARGET_ROUNDS_PER_SIDE = 31      # з sample_size.py: надійність профілю 0.9


def process(demo: Path, want_map: str | None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame] | None:
    pq = PROC / f"{demo.stem}_ticks.parquet"
    if not pq.exists():
        ticks, meta = EX.extract(str(demo))
        if want_map and meta["map"] != want_map:
            print(f"  {demo.name}: мапа {meta['map']} != {want_map}, пропуск")
            return None
        if meta["tickrate"] not in (32.0, 64.0, 128.0):
            print(f"  {demo.name}: дивний тікрейт {meta['tickrate']}, пропуск")
            return None
        if meta["tickrate"] != 64.0:
            print(f"  {demo.name}: тікрейт {meta['tickrate']} — вікна детекторів "
                  f"масштабуються автоматично")
        PROC.mkdir(parents=True, exist_ok=True)
        ticks.to_parquet(pq, index=False)
        print(f"  {demo.name}: {meta['map']}, {meta['rounds']} раундів, "
              f"{meta['kept_rows']} тіків -> {pq.name}")
    else:
        print(f"  {demo.name}: кеш {pq.name}")

    feats = FT.build(str(pq))
    ev, agg = EV.build(str(pq))
    hdr = DemoParser(str(demo)).parse_header()
    mp = hdr.get("map_name", "?")
    # Контекст — за назвою файлу, а НЕ за назвою сервера: офіційні турнірні
    # матчі (напр. відкриті кваліфікації EWC) теж хостяться на серверах FACEIT,
    # тому server_name показує провайдера, а не змагальне середовище.
    # "tournament" — офіційний турнірний матч; "platform" — позатурнірна гра на
    # платформі. Демку позатурнірної гри називаємо з токеном "platform".
    ctx = "platform" if "platform" in demo.stem else "tournament"
    for d in (feats, ev, agg):
        d["match_id"] = demo.stem
        d["map"] = mp
        d["context"] = ctx
        d["server"] = str(hdr.get("server_name", "?"))
    return feats, ev, agg


def main(want_map: str | None, min_rounds: int) -> None:
    demos = sorted(RAW.glob("*.dem"))
    if not demos:
        print(f"Немає демок у {RAW}. Поклади .dem файли туди.")
        return
    print(f"Демок знайдено: {len(demos)}")

    F, E, A = [], [], []
    for d in demos:
        r = process(d, want_map)
        if r:
            F.append(r[0]); E.append(r[1]); A.append(r[2])
    if not F:
        print("Нічого не оброблено.")
        return

    feats = pd.concat(F, ignore_index=True)
    ev = pd.concat(E, ignore_index=True)
    agg = pd.concat(A, ignore_index=True)

    # канонізація ніків: одна особа = один steamid, ім'я беремо найчастіше
    canon = (feats.groupby("steamid")["player"]
             .agg(lambda s: s.value_counts().idxmax()).to_dict())
    renamed = {sid: nm for sid, nm in canon.items()
               if feats.loc[feats.steamid == sid, "player"].nunique() > 1}
    for d in (feats, ev, agg):
        d["player"] = d["steamid"].map(canon).fillna(d["player"])
    if renamed:
        print("\nНіки зведені за steamid:", ", ".join(f"{v}" for v in renamed.values()))
    OUT.mkdir(parents=True, exist_ok=True)
    feats.to_csv(OUT / "dataset_features.csv", index=False)
    ev.to_csv(OUT / "dataset_events.csv", index=False)
    agg.to_csv(OUT / "dataset_event_features.csv", index=False)

    # --- покриття: чи вже достатньо даних на гравця ---
    cov = (feats.groupby(["player", "side"])
           .agg(rounds=("round", "size"), matches=("match_id", "nunique"),
                maps=("map", "nunique"))
           .reset_index()
           .pivot(index="player", columns="side", values=["rounds", "matches", "maps"])
           .fillna(0).astype(int))
    cov.columns = ["_".join(c) for c in cov.columns]
    cov["ready"] = ((cov.get("rounds_T", 0) >= min_rounds)
                    & (cov.get("rounds_CT", 0) >= min_rounds)
                    & (cov.filter(like="matches_").min(axis=1) >= 2))
    cov = cov.sort_values("ready", ascending=False)
    cov.to_csv(OUT / "coverage.csv")

    print(f"\nДатасет: {len(feats)} спостережень, {feats.player.nunique()} гравців, "
          f"{feats.match_id.nunique()} матчів, {feats['map'].nunique()} мап, "
          f"{len(ev)} подій")
    print("мапи:", feats.groupby("map")["match_id"].nunique().to_dict())
    print("контексти:", feats.groupby("context")["match_id"].nunique().to_dict())
    if "tickrate" in feats.columns and feats["tickrate"].nunique() > 1:
        print("УВАГА: у датасеті різні тікрейти:",
              feats.groupby("tickrate")["match_id"].nunique().to_dict(),
              "— ознаки нормовані на секунду, але це варто перевірити окремо")
    print(f"\nПокриття (потрібно >={min_rounds} раундів на сторону і >=2 матчі):")
    print(cov.to_string())
    ready = int(cov["ready"].sum())
    print(f"\nГотових до аналізу гравців: {ready}")
    if ready < 4:
        print("Мало. Кожна нова mirage-демка додає ~12 раундів на сторону "
              "одразу 10 гравцям — доливай демки з тими самими складами.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default="de_mirage", help="залишати лише цю мапу ('' = будь-яку)")
    ap.add_argument("--min-rounds", type=int, default=TARGET_ROUNDS_PER_SIDE)
    a = ap.parse_args()
    main(a.map or None, a.min_rounds)
