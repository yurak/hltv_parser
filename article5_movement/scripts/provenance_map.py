"""
provenance_map.py — build review/provenance_map.md: every numeric claim of the
manuscript traced back to the artifact it came from.

The journal text must not carry `outputs/...` pointers, but the project rule (CLAUDE.md)
still requires every number in Results to have provenance. This script keeps that audit
trail outside the article: it extracts numbers from the manuscript and searches all
generated artifacts (outputs*/tables/*.csv, outputs*/logs/*.txt) for each of them.

    python scripts/provenance_map.py                 # paper/manuscript_en.md (default)
    python scripts/provenance_map.py manuscript.md   # Ukrainian version

A number is FOUND when it appears in an artifact either literally or as a value rounded
to the precision printed in the text (0.547 matches 0.5470059623503126). Numbers left
UNMATCHED are not proof of an error — they may be derived (a ratio or a percentage change
computed in prose) or come from a cited source — but each one deserves a manual look.
"""
from __future__ import annotations
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "paper" / (sys.argv[1] if len(sys.argv) > 1 else "manuscript.md")
OUT = ROOT / "review" / "provenance_map.md"

# numbers that are structure, not results: section/table/figure refs, years, tiny counts
SKIP_CONTEXT = re.compile(r"(§|Table|Fig\.|Таблиц|Рис\.)\s*$")
YEARS = {str(y) for y in range(1980, 2031)}


def artifacts() -> list[tuple[str, str]]:
    """(label, searchable text) for every generated table and log."""
    items = []
    for d in sorted(ROOT.glob("outputs*")):
        for f in sorted(d.rglob("*.csv")):
            items.append((str(f.relative_to(ROOT)), f.read_text(encoding="utf-8", errors="replace")))
        for ext in ("*.txt", "*.json", "*.log"):
            for f in sorted(d.rglob(ext)):
                items.append((str(f.relative_to(ROOT)), f.read_text(encoding="utf-8", errors="replace")))
    return items


def numeric_tokens(text: str) -> list[float]:
    """All numbers appearing in an artifact, as floats."""
    out = []
    for tok in re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", text):
        try:
            out.append(float(tok))
        except ValueError:
            pass
    return out


# українська версія: розділи без номерів, перевіряються за назвами
UK_SECTIONS = re.compile(r"#+\s*(Анотація|Дані|Матеріали|Результати|Застосування|Перевірка|Загрози|Висновки)")


def results_lines(text: str) -> list[tuple[int, str]]:
    """Body lines of Results/Discussion/Conclusions plus the dataset description —
    the parts whose numbers must be traceable."""
    keep, on = [], False
    for i, line in enumerate(text.split("\n"), 1):
        if line.startswith("<!--") or line.startswith("[РІШЕННЯ"):
            continue
        if line.startswith("## "):
            on = bool(re.match(r"#+\s*(3\.2|4|5)[.\s]", line) or UK_SECTIONS.match(line))
        if line.startswith(("## References", "## Література")):
            break
        if on and line.strip() and not line.startswith(("#", "|", "!")):
            keep.append((i, line))
    return keep


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    uk = bool(UK_SECTIONS.search(text))
    if uk:   # десяткова кома -> крапка; тисяч з комою в українському тексті немає
        text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    arts = artifacts()
    art_values = {label: numeric_tokens(body) for label, body in arts}

    rows, unmatched = [], 0
    seen = set()
    for lineno, line in results_lines(text):
        for m in re.finditer(r"(\d[\d,]*\.?\d*)\s*(%?)", line):
            raw, pct = m.group(1), m.group(2)
            before = line[:m.start()]
            if SKIP_CONTEXT.search(before):
                continue
            clean = raw.replace(",", "")
            if clean in YEARS and not pct:
                continue
            try:
                val = float(clean)
            except ValueError:
                continue
            if val < 10 and "." not in clean and not pct:      # "four families", "(1)"
                continue
            key = (clean, pct, lineno)
            if key in seen:
                continue
            seen.add(key)

            decimals = len(clean.split(".")[1]) if "." in clean else 0
            hits = []
            for label, body in arts:
                if raw in body or clean in body:               # literal match
                    hits.append(label)
                    continue
                for v in art_values[label]:                    # rounded match
                    if round(v, decimals) == val or round(v * 100, decimals) == val:
                        hits.append(label)
                        break
            ctx = re.sub(r"\s+", " ", line[max(0, m.start() - 60):m.end() + 25]).strip()
            if not hits:
                unmatched += 1
            rows.append((lineno, raw + pct, sorted(set(hits)), ctx))

    out = [
        f"# Provenance map — {SRC.name}",
        "",
        "Every number printed in the dataset description, Results, Discussion and Conclusions,",
        "traced to the artifact it came from. The article text itself carries no `outputs/...`",
        "pointers by design — this file is the audit trail.",
        "",
        f"Generated by `scripts/provenance_map.py`; line numbers valid for the current state of {SRC.name}.",
        f"Numbers checked: **{len(rows)}** · traced: **{len(rows) - unmatched}** · unmatched: **{unmatched}**",
        "",
        "| Line | Value | Source artifact(s) | Context |",
        "|---|---|---|---|",
    ]
    for lineno, value, hits, ctx in rows:
        src = "<br>".join(f"`{h}`" for h in hits) if hits else "**— unmatched —**"
        out.append(f"| {lineno} | `{value}` | {src} | …{ctx}… |")

    if unmatched:
        out += ["", "## Unmatched numbers — check each by hand", "",
                "Derived values (ratios, percentage changes, lifts) and figures quoted from cited",
                "literature legitimately have no artifact; anything else is a red flag.", ""]
        out += [f"- line {ln}, `{v}` — …{c}…" for ln, v, h, c in rows if not h]

    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"[saved] {OUT.relative_to(ROOT)}")
    print(f"  numbers: {len(rows)} | traced: {len(rows) - unmatched} | unmatched: {unmatched}")
    print(f"  artifacts scanned: {len(arts)}")


if __name__ == "__main__":
    main()
