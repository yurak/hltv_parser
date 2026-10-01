#!/usr/bin/env python3
"""Прогін -> таблиці статті (outputs/paper/tables/*.csv) + numbers.json.

Жодне число статті не вписується руками: усе, що з'явиться в тексті, спершу
з'являється тут. Скрипт ідемпотентний і повністю перезбирається після нового
датасету:

    /usr/bin/python3 scripts/build_tables.py --run-id 2026-09-16_mirage_n136

Таблиці, для яких ще немає протоколу (T8 open-set, T9 temporal), пропускаються
з поясненням — це навмисно, щоб було видно, чого бракує.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paperlib as P


def n_features_used(run_id: str, m: dict) -> int:
    ch = P.read_csv(run_id, "channel_ablation.csv")
    if ch is not None and "all" in set(ch["channel"]):
        return int(ch.loc[ch["channel"] == "all", "n_feat"].iloc[0])
    return int(m["n_features"])


def used_demos(m: dict) -> pd.DataFrame:
    """Рядки реєстру лише для демок, що реально увійшли в датасет.

    Реєстр містить усе зібране, разом із демками, де після exclude.csv не
    лишилось жодного гравця; мапи, дати й контекст треба рахувати без них.
    """
    demos = pd.read_csv(P.REG / "demos.csv")
    fp = P.ROOT / "outputs" / "dataset" / "features.parquet"
    summ = P.ROOT / "outputs" / "dataset" / "summary.json"
    if fp.exists() and summ.exists():
        import json
        if json.loads(summ.read_text()).get("feat_ver") == m.get("feat_ver"):
            used = pd.read_parquet(fp, columns=["demo"])["demo"].unique()
            return demos[demos["demo_id"].isin(used)]
    raise SystemExit("T1: датасет outputs/dataset не відповідає feat_ver прогону — "
                     "перезберіть стадію dataset, інакше T1 змішає зібране з використаним")


def t1_dataset(run_id: str, tables: Path, nums: dict) -> str:
    m = P.manifest(run_id)["dataset"]
    demos = used_demos(m)
    m = {**m, "demos": len(demos)}
    rows = [
        ("Демок у датасеті", m["demos"]),
        ("Зібрано демок (до виключення гравців поза когортою)", len(pd.read_csv(P.REG / "demos.csv"))),
        ("Серій (незалежних сесій)", m["series"]),
        ("Гравців у датасеті", m["players"]),
        ("Спостережень (гравець, сторона, раунд)", m["observations"]),
        ("Подій", m["events"]),
        # m["n_features"] — ширина features.parquet разом зі службовими
        # колонками (demo, player, ...), а не кількість ознак; справжню беремо
        # з абляції, де рахується повний набір разом із подієвими
        ("Ознак", n_features_used(run_id, m)),
        ("Мап", demos["map"].nunique()),
        ("Вікно збору", f'{demos["date"].min()} — {demos["date"].max()}'),
        ("Турнірних демок", int((demos.context == "tournament").sum())),
        ("Платформних демок", int((demos.context == "platform").sum())),
        ("Гравців у когорті (S>=%d)" % m["min_sessions"], m["cohort_core"]),
        ("Виключено гравців", m["excluded_players"]),
    ]
    pd.DataFrame(rows, columns=["показник", "значення"]).to_csv(
        tables / "T1_dataset.csv", index=False)
    nums.update({f"dataset_{k}": v for k, v in m.items() if not isinstance(v, dict)})
    nums["dataset_n_features_used"] = n_features_used(run_id, m)
    nums["dataset_demos_collected"] = len(pd.read_csv(P.REG / "demos.csv"))
    nums["dataset_n_maps"] = int(demos["map"].nunique())
    nums["dataset_date_min"] = str(demos["date"].min())
    nums["dataset_date_max"] = str(demos["date"].max())
    return "T1_dataset.csv"


def t2_cohort(run_id: str, tables: Path, nums: dict) -> str | None:
    coh = P.cohort(run_id)
    if coh is None:
        return None
    ses = pd.read_csv(P.REG / "sessions.csv")
    ses["date"] = pd.to_datetime(ses["date"])
    agg = (ses[ses.steamid.isin(coh.steamid)]
           .groupby("steamid")
           .agg(сесій=("series_id", "nunique"),
                раундів=("rounds_CT", "sum"),
                перша=("date", "min"), остання=("date", "max")))
    agg["рознос_міс"] = ((agg["остання"] - agg["перша"]).dt.days / 30.4).round(1)
    out = (coh[["steamid", "nick_canonical", "team", "country", "role"]]
           .merge(agg, on="steamid", how="left")
           .sort_values("сесій", ascending=False)
           .drop(columns=["steamid"]))
    out.to_csv(tables / "T2_cohort.csv", index=False)
    nums["cohort_n_players"] = int(len(out))
    nums["cohort_span_months_max"] = float(agg["рознос_міс"].max())
    nums["cohort_n_span_ge3mo"] = int((agg["рознос_міс"] >= 3).sum())
    return "T2_cohort.csv"


def t3_closed_set(run_id: str, tables: Path, nums: dict) -> str | None:
    r = P.read_json(run_id, "report_both.json")
    if r is None:
        return None
    fams = ["all", "micro", "keydyn", "habit", "event", "macro"]
    rows = []
    for f in fams:
        if f"acc_lda_{f}" not in r:
            continue
        rows.append({"родина": P.FAMILY_UA.get(f, f),
                     "LDA": round(r[f"acc_lda_{f}"], 4),
                     "RF": round(r.get(f"acc_rf_{f}", np.nan), 4)})
    df = pd.DataFrame(rows)
    df["випадковий рівень"] = round(r["chance"], 4)
    df.to_csv(tables / "T3_closed_set.csv", index=False)
    nums.update({
        "p1_n_players": r["n_players"], "p1_n_obs": r["n_obs"],
        "p1_acc_lda_all": round(r["acc_lda_all"], 4),
        "p1_acc_rf_all": round(r["acc_rf_all"], 4),
        "p1_chance": round(r["chance"], 4),
        "p1_permnull_mean": round(r["acc_lda_all_permnull_mean"], 4),
        "p1_permnull_p95": round(r["acc_lda_all_permnull_p95"], 4),
        "p1_n_groups": r["n_groups"], "p1_group_by": r["group_by"],
        "p1_pca_var_2d": round(r["pca_var_2d"], 4),
        "p1_pair_auc_median": round(r["pair_auc_median"], 4),
    })
    return "T3_closed_set.csv"


def t4_verification(run_id: str, tables: Path, nums: dict) -> str | None:
    v = P.read_json(run_id, "verification_both.json")
    if v is None:
        return None
    rows = [("EER", round(v["eer"], 4)), ("AUC", round(v["auc"], 4)),
            ("d'", round(v["dprime"], 3)), ("поріг відстані", round(v["threshold"], 4)),
            ("genuine-пар", v["n_genuine"]), ("impostor-пар", v["n_impostor"]),
            ("ознак у профілі", v["n_features"]), ("профілів", v["n_profiles"])]

    gi = P.genuine_impostor(run_id)
    if gi is not None:
        g, i = gi
        lo, hi = P.bootstrap_eer(g, i)
        rows += [("EER, 95% CI (бутстреп, 2000)", f"[{lo:.4f}; {hi:.4f}]"),
                 ("FAR при FRR=1%", round(P.far_at_frr(g, i, 0.01), 4)),
                 ("FAR при FRR=10%", round(P.far_at_frr(g, i, 0.10), 4)),
                 ("genuine: середня відстань", round(float(g.mean()), 4)),
                 ("genuine: SD", round(float(g.std(ddof=1)), 4)),
                 ("impostor: середня відстань", round(float(i.mean()), 4)),
                 ("impostor: SD", round(float(i.std(ddof=1)), 4))]
        nums.update({"p2_eer_ci_lo": round(lo, 4), "p2_eer_ci_hi": round(hi, 4),
                     "p2_far_at_frr01": round(P.far_at_frr(g, i, 0.01), 4),
                     "p2_far_at_frr10": round(P.far_at_frr(g, i, 0.10), 4),
                     "p2_genuine_mean": round(float(g.mean()), 4),
                     "p2_impostor_mean": round(float(i.mean()), 4)})
    pd.DataFrame(rows, columns=["показник", "значення"]).to_csv(
        tables / "T4_verification.csv", index=False)
    nums.update({"p2_eer": round(v["eer"], 4), "p2_auc": round(v["auc"], 4),
                 "p2_dprime": round(v["dprime"], 3),
                 "p2_n_genuine": v["n_genuine"], "p2_n_impostor": v["n_impostor"],
                 "p2_block_unit": v["block_unit"]})
    return "T4_verification.csv"


def t6_degradation(run_id: str, tables: Path, nums: dict) -> str | None:
    parts = []
    for name, label in [("cross_series_id_both_match.csv", "між серіями"),
                        ("cross_match_id_both_match.csv", "між матчами")]:
        d = P.read_csv(run_id, name)
        if d is None:
            continue
        d = d.copy()
        d["зріз"] = label
        d["родина"] = d["family"].map(lambda f: P.FAMILY_UA.get(f, f))
        parts.append(d[["зріз", "родина", "n_feat", "across_match",
                        "within_match", "degradation"]])
    if not parts:
        return None
    out = pd.concat(parts, ignore_index=True)
    out.to_csv(tables / "T6_degradation.csv", index=False)
    top = out[(out["зріз"] == "між серіями") & (out["родина"] == "усі")]
    if len(top):
        nums.update({"p4_across_series": round(float(top.across_match.iloc[0]), 4),
                     "p4_within_series": round(float(top.within_match.iloc[0]), 4),
                     "p4_degradation": round(float(top.degradation.iloc[0]), 4)})
    return "T6_degradation.csv"


def t5_ablation(run_id: str, tables: Path, nums: dict) -> str | None:
    """Внесок родин: закрита точність поруч із міжматчевою — щоб було видно,
    що добре працює всередині матчу, а що переживає його зміну."""
    d = P.read_csv(run_id, "cross_series_id_both_match.csv")
    r = P.read_json(run_id, "report_both.json")
    if d is None or r is None:
        return None
    rows = []
    for _, x in d.iterrows():
        f = x["family"]
        rows.append({"родина": P.FAMILY_UA.get(f, f), "ознак": int(x["n_feat"]),
                     "closed-set LDA": round(r.get(f"acc_lda_{f}", np.nan), 4)
                     if f != "all" else round(r["acc_lda_all"], 4),
                     "між серіями": round(float(x["across_match"]), 4),
                     "деградація": round(float(x["degradation"]), 4)})
    pd.DataFrame(rows).to_csv(tables / "T5_ablation.csv", index=False)
    best = max((x for x in rows if x["родина"] != "усі"), key=lambda x: x["між серіями"])
    nums["p5_best_family"] = best["родина"]
    nums["p5_best_family_acc"] = best["між серіями"]
    return "T5_ablation.csv"


def t7_probe(run_id: str, tables: Path, nums: dict) -> str | None:
    lc = P.read_csv(run_id, "learning_curve_both.csv")
    if lc is None:
        return None
    lc.to_csv(tables / "T7_probe_length.csv", index=False)
    nums["p7_max_rounds"] = int(lc["rounds"].max())
    nums["p7_acc_at_max"] = round(float(lc.loc[lc["rounds"].idxmax(), "acc_mean"]), 4)
    ss = P.read_csv(run_id, "sample_size_both.csv")
    if ss is not None:
        nums["p7_k_rounds_R80_median"] = round(float(ss["k_rounds_R80"].median()), 2)
    return "T7_probe_length.csv"


def t10_stability(run_id: str, tables: Path, nums: dict) -> str | None:
    fs = P.read_csv(run_id, "feature_stats_both.csv")
    if fs is None:
        return None
    out = (fs.sort_values("icc1", ascending=False)
           .head(25)[["feature", "family", "icc1", "eta2_H", "q_bh"]]
           .round({"icc1": 4, "eta2_H": 4}))
    out.to_csv(tables / "T10_feature_stability.csv", index=False)
    nums["t10_icc_max"] = round(float(fs["icc1"].max()), 4)
    nums["t10_icc_median"] = round(float(fs["icc1"].median()), 4)
    nums["t10_n_icc_ge05"] = int((fs["icc1"] >= 0.5).sum())
    return "T10_feature_stability.csv"


def t11_channel(run_id: str, tables: Path, nums: dict) -> str | None:
    """Чиста локомоція проти повного набору — головна таблиця статті.
    Будується скриптом ablate_channel.py; якщо його не ганяли, таблиці не буде."""
    d = P.read_csv(run_id, "channel_ablation.csv")
    if d is None:
        return None
    out = d.rename(columns={"channel": "канал", "n_feat": "ознак",
                            "across_series": "між серіями", "within_match": "у межах матчу",
                            "degradation": "деградація", "chance": "випадковий рівень",
                            "desc": "опис"})
    out.to_csv(tables / "T11_channel_ablation.csv", index=False)
    r = {x["channel"]: x for _, x in d.iterrows()}
    if "loco" in r and "all" in r:
        nums.update({
            "t11_loco_acc": round(float(r["loco"]["across_series"]), 4),
            "t11_loco_nfeat": int(r["loco"]["n_feat"]),
            "t11_all_acc": round(float(r["all"]["across_series"]), 4),
            "t11_loco_share": round(float(r["loco"]["across_series"]
                                          / r["all"]["across_series"]), 4)})
    if "combat" in r:
        nums["t11_combat_acc"] = round(float(r["combat"]["across_series"]), 4)
        nums["t11_combat_nfeat"] = int(r["combat"]["n_feat"])
    return "T11_channel_ablation.csv"


CHANNEL_UA = {"all": "повний набір", "loco": "керування пересуванням",
              "loco_no_cs": "керування пересуванням без контрстрейфу",
              "keydyn": "клавіатурна динаміка", "combat": "стрільба й прицілювання"}


def review_nums(rc: dict, prefix: str) -> dict:
    """Числа з review_checks.json (scripts/review_checks.py) під префіксом."""
    n = {}
    for ch, v in rc["verification"].items():
        if ch == "verif_default":
            continue
        for k in ("eer", "auc", "dprime", "far_at_frr01", "far_at_frr10", "n_features_icc"):
            n[f"{prefix}ver_{ch}_{k}"] = v[k]
        n[f"{prefix}ver_{ch}_eer_lo"], n[f"{prefix}ver_{ch}_eer_hi"] = v["eer_ci"]
        n[f"{prefix}ver_{ch}_eer_mates"] = v["vs_teammates"]["eer"]
        n[f"{prefix}ver_{ch}_eer_others"] = v["vs_other_teams"]["eer"]
    for ch, v in rc["random_subsets"].items():
        for k, x in v.items():
            n[f"{prefix}rand_{ch}_{k}"] = x
    for ch, v in rc["teammate_errors"].items():
        for k, x in v.items():
            n[f"{prefix}materr_{ch}_{k}"] = x
    for ch, x in rc["closed_set"].items():
        n[f"{prefix}acc_{ch}"] = x
    return n


def t17_review(run_id: str, tables: Path, nums: dict) -> str | None:
    """Верифікація за каналами + партнери по команді (рецензія v0.2, A1/A4/B1)."""
    rc = P.read_json(run_id, "review_checks.json")
    if rc is None:
        return None
    rows = []
    for ch, name in CHANNEL_UA.items():
        v = rc["verification"][ch]
        rows.append({"канал": name, "ознак у профілі": v["n_features_icc"],
                     "EER": v["eer"], "EER 95% CI": f"[{v['eer_ci'][0]}; {v['eer_ci'][1]}]",
                     "AUC": v["auc"], "d'": v["dprime"],
                     "FAR при FRR=1%": v["far_at_frr01"], "FAR при FRR=10%": v["far_at_frr10"],
                     "EER проти партнерів": v["vs_teammates"]["eer"],
                     "EER проти інших команд": v["vs_other_teams"]["eer"]})
    pd.DataFrame(rows).to_csv(tables / "T17_verification_channels.csv", index=False)
    nums.update(review_nums(rc, ""))
    return "T17_verification_channels.csv"


def t18_within_team(run_id: str, tables: Path, nums: dict) -> str | None:
    d = P.read_csv(run_id, "review_within_team.csv")
    if d is None:
        return None
    d["канал"] = d["канал"].map(CHANNEL_UA)
    d.to_csv(tables / "T18_within_team.csv", index=False)
    lo = d[d["канал"] == CHANNEL_UA["loco"]]["між серіями"]
    al = d[d["канал"] == CHANNEL_UA["all"]]["між серіями"]
    nums.update({"t18_loco_min": round(float(lo.min()), 4), "t18_loco_max": round(float(lo.max()), 4),
                 "t18_all_min": round(float(al.min()), 4), "t18_all_max": round(float(al.max()), 4)})
    return "T18_within_team.csv"


def t9_temporal(run_id: str, tables: Path, nums: dict) -> str | None:
    d = P.read_csv(run_id, "review_time_gap.csv")
    if d is None:
        return None
    d["канал"] = d["канал"].map({"verif_default": CHANNEL_UA["all"], "loco": CHANNEL_UA["loco"]})
    d.to_csv(tables / "T9_temporal.csv", index=False)
    for ch, key in ((CHANNEL_UA["all"], "all"), (CHANNEL_UA["loco"], "loco")):
        s = d[d["канал"] == ch].set_index("проміжок_міс")
        nums[f"t9_{key}_eer_lt1"] = float(s.loc["0–1", "EER"])
        nums[f"t9_{key}_eer_ge3"] = float(s.loc["≥3", "EER"])
        nums[f"t9_{key}_n_ge3"] = int(s.loc["≥3", "genuine_пар"])
    return "T9_temporal.csv"


def replica_nums(replica: str | None, nums: dict) -> None:
    """Повторення на другій мапі: ті самі перевірки під префіксом d2_."""
    if not replica:
        return
    rc = P.read_json(replica, "review_checks.json")
    if rc is not None:
        nums.update(review_nums(rc, "d2_"))
    ch = P.read_csv(replica, "channel_ablation.csv")
    if ch is not None:
        r = ch.set_index("channel")["across_series"]
        nums.update({"d2_acc_all": round(float(r["all"]), 4), "d2_acc_loco_ch": round(float(r["loco"]), 4),
                     "d2_acc_combat": round(float(r["combat"]), 4),
                     "d2_loco_share": round(float(r["loco"] / r["all"]), 4)})


def t19_groups(run_id: str, tables: Path, nums: dict) -> str | None:
    """Зведення за групами ознак: інформативність і стійкість до контексту.

    Потрібне за будь-якої рамки статті — це порівняння груп в одному місці.
    Точність і 95 % CI — з acc_ci.py (кластерний бутстреп за серіями),
    деградація — з T6/T11. Стійкість до обладнання є лише для клавіатури й
    мікроруху без бойових ознак (T13 з build_probe_tables.py), тож мікрорух
    має два рядки: повний (26) і без бойових (20), і число про обладнання
    стоїть лише в другому.
    """
    fs = P.read_csv(run_id, "feature_stats_both.csv")
    ci = P.read_csv(run_id, "acc_ci.csv")
    t6, t11 = tables / "T6_degradation.csv", P.read_csv(run_id, "channel_ablation.csv")
    if fs is None or ci is None or t11 is None or not t6.exists():
        return None
    import analyze as A
    from ablate_channel import COMBAT_COUPLED
    deg = pd.read_csv(t6)
    deg = deg[deg["зріз"] == "між серіями"].set_index("родина")["degradation"]
    t11 = t11.set_index("channel")
    ci = ci.set_index("набір")
    icc = fs.set_index("feature")["icc1"]
    fam_icc = fs.groupby("family")["icc1"].median()
    clean = [c for c in A.MICRO if c not in COMBAT_COUPLED and c in icc.index]
    hw_path = tables / "T13_probe_hardware.csv"
    hw = pd.read_csv(hw_path) if hw_path.exists() else None
    spec = [("keydyn", P.FAMILY_UA["keydyn"], "місце_keydyn"),
            ("micro", P.FAMILY_UA["micro"], None),
            ("micro_clean", "мікрорух без ознак стрільби й прицілювання", "місце_micro_clean"),
            ("habit", P.FAMILY_UA["habit"], None), ("event", P.FAMILY_UA["event"], None),
            ("macro", P.FAMILY_UA["macro"], None)]
    rows = []
    for key, ua, hcol in spec:
        d = (float(t11.loc["micro_clean", "degradation"]) if key == "micro_clean"
             else float(deg[ua]))
        ic = float(icc[clean].median()) if key == "micro_clean" else float(fam_icc[key])
        r = {"група": ua, "ознак": int(ci.loc[key, "ознак"]),
             "між серіями": ci.loc[key, "між серіями"],
             "95% CI": f"[{ci.loc[key, 'CI_low']}; {ci.loc[key, 'CI_high']}]",
             "деградація між серіями": round(d, 4), "медіанний ICC(1)": round(ic, 4),
             "перше місце за зміни обладнання":
                 f"{int((hw[hcol] == 1).sum())} з {len(hw)}" if hw is not None and hcol else ""}
        rows.append(r)
        nums[f"t19_{key}_icc_median"] = r["медіанний ICC(1)"]
    pd.DataFrame(rows).to_csv(tables / "T19_groups_summary.csv", index=False)
    for key in ci.index:
        nums[f"ci_{key}_lo"] = float(ci.loc[key, "CI_low"])
        nums[f"ci_{key}_hi"] = float(ci.loc[key, "CI_high"])
    return "T19_groups_summary.csv"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--replica-run", default=None,
                    help="прогін на другій мапі — його числа йдуть із префіксом d2_")
    a = ap.parse_args()

    tables, _, logs = P.out_dirs()
    m = P.manifest(a.run_id)
    nums: dict = {"run_id": a.run_id, "git_sha": m["git_sha"],
                  "feat_ver": m["dataset"]["feat_ver"], "built_at": m["built_at"]}

    made, skipped = [], []
    for fn in (t1_dataset, t2_cohort, t3_closed_set, t4_verification,
               t5_ablation, t6_degradation, t7_probe, t10_stability,
               t11_channel, t17_review, t18_within_team, t9_temporal,
               t19_groups):
        name = fn(a.run_id, tables, nums)
        (made if name else skipped).append(name or fn.__name__)

    replica_nums(a.replica_run, nums)
    skipped += ["T8_open_set (протоколу P3 ще немає)"]

    P.save_numbers(nums)
    (P.PAPER / "run_id.txt").write_text(
        f"{a.run_id}\ngit_sha={m['git_sha']}\nfeat_ver={m['dataset']['feat_ver']}\n"
        f"built_at={m['built_at']}\n")

    log = [f"прогін: {a.run_id}", f"таблиць зібрано: {len(made)}"]
    log += [f"  + {x}" for x in made]
    log += [f"  - пропущено: {x}" for x in skipped]
    log += [f"чисел у numbers.json: {len(nums)}"]
    text = "\n".join(log)
    (logs / "build_tables.log").write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
