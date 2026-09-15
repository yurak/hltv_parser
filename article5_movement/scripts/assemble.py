#!/usr/bin/env python3
"""Стадія 4: гарячий ярус + реєстр -> датасет і когорта.

Заміна `build_dataset.py`. Принципова різниця — жодного звертання до `.dem`:
мапа, контекст, дата й серія беруться з реєстру, а не з заголовка демки. Тому
пайплайн працює, коли сирі демки лежать тільки в S3.

Друга різниця — колонка `series_id`. Спліти в протоколах групуються за нею, а
не за мапою: три мапи одного Bo3 — одна сесія, і genuine-пари всередині неї
брати не можна.

    outputs/dataset/features.parquet         (гравець, сторона, раунд) x 85 ознак
    outputs/dataset/event_features.parquet   агрегати подій на раунд
    outputs/dataset/events.parquet           окремі події
    outputs/dataset/cohort.csv               хто проходить у ядро когорти
    outputs/dataset/coverage.csv             покриття на гравця

    /usr/bin/python3 scripts/assemble.py
    /usr/bin/python3 scripts/assemble.py --min-sessions 3 --min-rounds 24
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEAT = ROOT / "data" / "features"
REG = ROOT / "data" / "registry"
OUT = ROOT / "outputs" / "dataset"

# `event` у реєстрі — назва турніру, а в шарі подій — тип події (стоп/пік).
# Щоб ці два не зіштовхнулись при join, турнір їде як `tournament`.
META_COLS = ["series_id", "date", "event", "team1", "team2", "map", "context",
             "tickrate", "series_source"]


def current_ver() -> str:
    f = FEAT / "CURRENT_VER"
    if f.exists():
        return f.read_text().strip()
    sys.path.insert(0, str(Path(__file__).parent))
    import featurize
    return featurize.feat_ver()


def load_layer(demo_ids: list[str], ver: str, name: str) -> pd.DataFrame:
    parts = []
    for d in demo_ids:
        p = FEAT / d / ver / f"{name}.parquet"
        if p.exists():
            parts.append(pd.read_parquet(p))
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-sessions", type=int, default=3,
                    help="незалежних серій, щоб потрапити в ядро когорти")
    ap.add_argument("--min-rounds", type=int, default=24,
                    help="раундів на сторону в сесії, щоб вона вважалась повною")
    ap.add_argument("--ver", default=None, help="feat_ver (типово поточний)")
    a = ap.parse_args()

    for f in ("demos.csv", "players.csv", "sessions.csv"):
        if not (REG / f).exists():
            print(f"Немає реєстру ({f}). Спершу: run.py registry", file=sys.stderr)
            return 1

    ver = a.ver or current_ver()
    demos = pd.read_csv(REG / "demos.csv", dtype={"series_id": "string", "patch": "string"})
    players = pd.read_csv(REG / "players.csv")
    sessions = pd.read_csv(REG / "sessions.csv", dtype={"series_id": "string"})

    have = [d for d in demos.demo_id if (FEAT / d / ver / "feats.parquet").exists()]
    missing = sorted(set(demos.demo_id) - set(have))
    print(f"feat_ver {ver} | демок з ознаками {len(have)}/{len(demos)}")
    if missing:
        print(f"  без ознак ({len(missing)}): {', '.join(missing[:5])}"
              + (" ..." if len(missing) > 5 else ""))

    meta = (demos.set_index("demo_id")[META_COLS]
            .rename(columns={"event": "tournament"}))
    canon = players.set_index("steamid")["nick_canonical"]

    out = {}
    for name, key in (("feats", "features"), ("evagg", "event_features"),
                      ("events", "events")):
        df = load_layer(have, ver, name)
        if df.empty:
            print(f"  шар {name} порожній", file=sys.stderr)
            continue
        # `demo` лишається як є — на нього спираються аналітичні скрипти;
        # demo_id і match_id додаються поруч як ключі реєстру
        df["demo_id"] = df["demo"]
        df["match_id"] = df["demo"]
        # Метадані чіпляються ЛИШЕ до шару ознак. Аналітичні скрипти вважають
        # ознакою кожну колонку шару подій, якої немає в їхньому списку ключів,
        # тож зайва метаколонка там мовчки поїхала б у модель як предиктор.
        if key == "features":
            df = df.join(meta, on="demo_id")
        df["player"] = df.steamid.map(canon).fillna(df.player)
        out[key] = df

    feats = out["features"]
    OUT.mkdir(parents=True, exist_ok=True)
    for key, df in out.items():
        df.to_parquet(OUT / f"{key}.parquet", index=False)

    # --- когорта ---
    full = sessions[(sessions.rounds_T >= a.min_rounds)
                    & (sessions.rounds_CT >= a.min_rounds)]
    cohort = players.copy()
    cohort["n_sessions_full"] = (cohort.steamid.map(full.groupby("steamid").size())
                                 .fillna(0).astype(int))
    cohort["in_core"] = cohort.n_sessions >= a.min_sessions
    cohort["in_core_strict"] = cohort.n_sessions_full >= a.min_sessions
    cohort["role"] = ""
    roster = ROOT / "data" / "roster.csv"
    if roster.exists():
        r = pd.read_csv(roster)
        sys.path.insert(0, str(Path(__file__).parent))
        from registry import nkey
        rm = {nkey(p): rr for p, rr in zip(r.player, r.role)}
        cohort["role"] = cohort.nick_canonical.map(lambda n: rm.get(nkey(n), ""))
    cohort = cohort.sort_values(["n_sessions", "nick_canonical"], ascending=[False, True])
    cohort.to_csv(OUT / "cohort.csv", index=False)

    cov = (feats.groupby(["player", "side"])
           .agg(rounds=("round", "size"), series=("series_id", "nunique"),
                maps=("map", "nunique"), demos=("demo_id", "nunique"))
           .reset_index()
           .pivot(index="player", columns="side", values=["rounds", "series", "maps", "demos"])
           .fillna(0).astype(int))
    cov.columns = ["_".join(c) for c in cov.columns]
    cov.to_csv(OUT / "coverage.csv")

    core = cohort[cohort.in_core]
    strict = cohort[cohort.in_core_strict]
    summary = {
        "feat_ver": ver, "demos": len(have), "series": int(feats.series_id.nunique()),
        "players": int(feats.player.nunique()), "observations": int(len(feats)),
        "events": int(len(out["events"])), "n_features": int(feats.shape[1]),
        "cohort_core": int(len(core)), "cohort_core_strict": int(len(strict)),
        "min_sessions": a.min_sessions, "min_rounds": a.min_rounds,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print(f"\nдатасет: {summary['observations']} спостережень, "
          f"{summary['players']} гравців, {summary['series']} серій, "
          f"{summary['demos']} демок, {summary['events']} подій")
    print(f"когорта: {summary['cohort_core']} у ядрі (S>={a.min_sessions}), "
          f"{summary['cohort_core_strict']} строго "
          f"(S>={a.min_sessions} повних сесій по >={a.min_rounds} раундів/сторону)")
    print("контекст:", feats.groupby("context")["series_id"].nunique().to_dict())
    print("\nядро когорти:")
    cols = ["nick_canonical", "team", "country", "role", "n_sessions", "n_sessions_full"]
    print(core[cols].head(40).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
