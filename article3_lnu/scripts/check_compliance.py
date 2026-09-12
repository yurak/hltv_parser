#!/usr/bin/env python3
"""Check a LaTeX manuscript against the journal No. 69 rules and against outputs/.

    python3 scripts/check_compliance.py            # English submission version
    python3 scripts/check_compliance.py uk         # Ukrainian reference version

Four groups of checks:
  BUILD       pdflatex succeeds; no unresolved \\ref/\\cite; no text spilling past the measure; A4.
  JOURNAL     rules of journal No. 69 that can be verified mechanically — LaTeX source, figures as
              separate PDF files, <=7 keywords, both metadata blocks, ORCID (with MOD 11-2 check
              digit), one bibliography, full URLs; plus template integrity — the .sty files
              byte-identical to the journal's own copy, every edit to VisnykAMI.tex annotated, the
              three bugfixes still applied, page geometry untouched, and the shipped figures equal
              to the current output of build_figures.py.
  CONSISTENCY every float referenced, every source cited, no untranslated Cyrillic in the English body.
  PROVENANCE  every share, count and effect size in the text recomputed from outputs/tables/;
              Table 1 rebuilt from the CSVs and compared row by row.

Exit code 0 = all passed, 1 = at least one failure, 2 = cannot run (missing file / no pdflatex).
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LATEX = ROOT / "latex"
TABLES = ROOT / "outputs" / "tables"
ORIGINAL = ROOT / "references" / "journal_guidelines" / "VISNYK2019_original"

LANG = (sys.argv[1] if len(sys.argv) > 1 else "en").lower()
if LANG not in ("uk", "en"):
    raise SystemExit(f"unknown version: {LANG!r} (expected 'en' or 'uk')")
TEX = LATEX / ("article_en.tex" if LANG == "en" else "article.tex")
PDF = TEX.with_suffix(".pdf")
LOG = TEX.with_suffix(".log")

KEYWORDS_MAX = 7          # journal No. 69: "ключові слова (не більше 7)"
OVERFULL_PT = 5.0         # ignore sub-visual overflow; anything larger shows in the margin
CYRILLIC = re.compile(r"[\u0400-\u04FF]")
# \texttt{damage\us{}per\us{}kill} — the body holds balanced {} pairs, so a plain [^}]* fails
TEXTT = r"\\texttt\{((?:[^{}]|\{\})*)\}"

results: list[tuple[bool, str]] = []


def check(ok: bool, message: str) -> None:
    results.append((bool(ok), message))


def feat(s: str) -> str:
    r"""\texttt{opening\us{}deaths\us{}per\us{}round} body -> opening_deaths_per_round."""
    return s.replace(r"\us{}", "_").replace(r"\_", "_").strip()


def num(s: str) -> float:
    """LaTeX decimal, Ukrainian 0{,}06 or English 0.06 -> float."""
    return float(s.replace("{,}", ".").replace(",", "."))


def fmt(x: float) -> list[str]:
    """The ways a one-decimal number may legitimately appear in either language."""
    plain = f"{x:.1f}"
    return [plain, plain.replace(".", "{,}"), plain.replace(".", ",")]


def orcid_valid(orcid: str) -> bool:
    """ISO 7064 MOD 11-2, as printed on orcid.org."""
    digits = orcid.replace("-", "")
    total = 0
    for ch in digits[:-1]:
        total = (total + int(ch)) * 2
    remainder = total % 11
    expected = (12 - remainder) % 11
    return ("X" if expected == 10 else str(expected)) == digits[-1].upper()


def pdf_content(path: Path) -> bytes:
    """PDF bytes without the timestamp and file id — matplotlib stamps a new one on every run,
    so a plain byte comparison would flag every rebuild as a stale copy."""
    raw = path.read_bytes()
    raw = re.sub(rb"/CreationDate \([^)]*\)", b"", raw)
    return re.sub(rb"/ID \[[^\]]*\]", b"", raw)


def load(name: str) -> list[dict]:
    with (TABLES / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    if not TEX.exists():
        print(f"missing manuscript: {TEX}", file=sys.stderr)
        return 2
    if not shutil.which("pdflatex"):
        print("pdflatex not found", file=sys.stderr)
        return 2

    src = TEX.read_text(encoding="utf-8")

    # ------------------------------------------------------------------ BUILD
    build = subprocess.run(["make", "en" if LANG == "en" else "uk"],
                           cwd=LATEX, capture_output=True, text=True)
    check(build.returncode == 0, f"pdflatex builds {TEX.name} without errors")
    if build.returncode != 0:
        tail = (build.stdout or build.stderr).strip().splitlines()[-6:]
        for line in tail:
            print("      " + line)

    log = LOG.read_text(encoding="utf-8", errors="replace") if LOG.exists() else ""
    undefined = re.findall(r"LaTeX Warning: (Reference|Citation) `([^']+)' .*undefined", log)
    check(not undefined,
          "all \\ref/\\cite resolve" + (f" — undefined: {sorted({u[1] for u in undefined})}"
                                        if undefined else ""))
    overfull = [float(m) for m in re.findall(r"Overfull \\hbox \(([\d.]+)pt too wide", log)]
    bad = [m for m in overfull if m > OVERFULL_PT]
    check(not bad, f"no text past the measure by more than {OVERFULL_PT:g}pt"
                   + (f" — worst {max(bad):.1f}pt" if bad else ""))

    if PDF.exists():
        info = subprocess.run([shutil.which("pdfinfo"), str(PDF)],
                              capture_output=True, text=True).stdout
        size = re.search(r"^Page size:\s+([\d.]+) x ([\d.]+) pts", info, re.M)
        pages = re.search(r"^Pages:\s+(\d+)$", info, re.M)
        check(size and abs(float(size.group(1)) - 595.276) < 1.5
              and abs(float(size.group(2)) - 841.89) < 1.5,
              f"A4 page size ({size.group(1)} x {size.group(2)} pts)" if size else "A4 page size")
        check(True, f"length: {pages.group(1)} pages "
                    "(journal No. 69 publishes no limit — confirm with the editors)")

    # ---------------------------------------------------------------- JOURNAL
    for kw_macro, limit_name in ((r"\KeywordsEng", "Key words"), (r"\KeywordsUkr", "Ключові слова")):
        block = re.search(re.escape(kw_macro) + r"(.*?)\\end\{Abstract\}", src, re.S)
        if not block:
            check(False, f"{limit_name} block present")
            continue
        words = [w.strip() for w in block.group(1).replace("\n", " ").strip(" .").split(",")]
        words = [w for w in words if w]
        check(len(words) <= KEYWORDS_MAX,
              f"{limit_name}: {len(words)} keywords (journal limit {KEYWORDS_MAX})")

    for block in ("UdcEng" if LANG == "en" else "UdcUkr", "Title", "Authors",
                  "Organization", "Abstract"):
        want = 1 if block.startswith("Udc") else 2
        got = len(re.findall(r"\\begin\{" + block + r"\}", src))
        check(got >= want, f"template block {block}: {got} (expected {want}) "
                           "— metadata must appear in both languages")

    orcids = re.findall(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", src)
    unique = sorted(set(orcids))
    check(len(unique) == 2, f"ORCID for both authors: found {len(unique)}")
    for o in unique:
        check(orcid_valid(o), f"ORCID {o} passes the MOD 11-2 check digit")
    check("0000-0000-0000-0000" not in src, "no placeholder ORCID left in the text")

    check(len(re.findall(r"\\begin\{thebibliography\}", src)) == 1,
          "exactly one bibliography (the journal template provides one)")

    # figures must be separate PDF files, per the submission rules
    for inc in re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", src):
        path = LATEX / inc
        check(path.exists(), f"figure file present: {inc}")
        check(path.suffix == ".pdf", f"figure is PDF (journal requirement): {inc}")

    # the journal asks for full URLs — check each internet source, not merely that one URL exists
    for m in re.finditer(r"(Access mode:|Режим доступу:)", src):
        tail = src[m.end(): m.end() + 200]
        check(bool(re.search(r"https?://", tail)),
              f"internet source after {m.group(1)!r} carries a full URL")

    # --- template integrity: the editors typeset with their own copy, so ours must not drift
    if ORIGINAL.is_dir():
        for sty in ("stdclsdv.sty", "tocloft.sty"):
            ours, theirs = LATEX / sty, ORIGINAL / sty
            check(ours.exists() and theirs.exists()
                  and hashlib.sha256(ours.read_bytes()).digest()
                  == hashlib.sha256(theirs.read_bytes()).digest(),
                  f"{sty} byte-identical to the journal template")

        orig = (ORIGINAL / "VisnykAMI.tex").read_bytes().decode("cp1251").splitlines()
        mine = (LATEX / "VisnykAMI.tex").read_text(encoding="utf-8").splitlines()
        undocumented = []
        for tag, _, _, j1, j2 in difflib.SequenceMatcher(None, orig, mine).get_opcodes():
            if tag == "equal":
                continue
            hunk = "\n".join(mine[j1:j2])
            if "BUGFIX" not in hunk and "original" not in hunk and "оригінал" not in hunk.lower():
                undocumented.append(mine[j1:j2][:1] or ["<deleted lines>"])
        check(not undocumented,
              "every change to VisnykAMI.tex is annotated (BUGFIX / original)"
              + (f" — undocumented: {undocumented[:3]}" if undocumented else ""))

        # the three fixes must still be there: re-copying the template would reintroduce the crash.
        # Search the ACTIVE code only — the fixes keep the buggy originals as comments beside them.
        tpl = (LATEX / "VisnykAMI.tex").read_text(encoding="utf-8")
        code = "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in tpl.splitlines())
        check(r"\vspace*{0pt}\vspace*\begin{flushleft}" not in code,
              "UdcUkr bugfix still applied (stray \\vspace* removed)")
        check(r"\@plus -1ex" not in code,
              "section spacing bugfix still applied (no negative stretch on a positive beforeskip)")
        check(r"\usepackage[utf8]{inputenc}" in tpl, "inputenc switched to utf8")

        for key in (r"\textwidth = 13.5cm", r"\textheight = 20.4cm",
                    r"\oddsidemargin = 1.96cm", r"\topmargin = 1.42cm",
                    r"\documentclass[10pt,a4paper,twoside,openany]{report}"):
            check(key in tpl, f"page geometry untouched: {key}")

    # --- figures in latex/ must be the current build products, not stale copies
    for inc in re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", src):
        shipped = LATEX / inc
        generated = ROOT / "outputs" / Path(inc).parent.name / Path(inc).name
        if shipped.exists() and generated.exists():
            check(pdf_content(shipped) == pdf_content(generated),
                  f"{inc} matches the current output of build_figures.py (not a stale copy)")
        else:
            check(generated.exists(), f"{inc} has a generated counterpart in outputs/")

    # ------------------------------------------------------------ CONSISTENCY
    labels = set(re.findall(r"\\label\{((?:fig|tab):[^}]+)\}", src))
    refs = set(re.findall(r"\\ref\{((?:fig|tab):[^}]+)\}", src))
    orphan_floats = sorted(labels - refs)
    check(not orphan_floats,
          "every figure and table is referenced in the text"
          + (f" — never referenced: {orphan_floats}" if orphan_floats else ""))

    bibitems = set(re.findall(r"\\bibitem\{([^}]+)\}", src))
    cited = {k.strip() for group in re.findall(r"\\cite\{([^}]+)\}", src) for k in group.split(",")}
    check(not (bibitems - cited),
          "no orphan sources in the bibliography"
          + (f" — never cited: {sorted(bibitems - cited)}" if bibitems - cited else ""))
    check(not (cited - bibitems),
          "every \\cite has a \\bibitem"
          + (f" — missing: {sorted(cited - bibitems)}" if cited - bibitems else ""))

    if LANG == "en":
        # the English body must be Cyrillic-free; the Ukrainian metadata block sits after it
        body_start = src.index(r"\section{Introduction}")
        body_end = src.index(r"\selectlanguage{ukrainian}")
        body = re.sub(r"^\s*%.*$", "", src[body_start:body_end], flags=re.M)
        stray = sorted({m.group(0) for m in CYRILLIC.finditer(body)})
        lines = [n for n, line in enumerate(body.splitlines(), 1) if CYRILLIC.search(line)]
        check(not stray, "English body free of untranslated Cyrillic"
                         + (f" — lines {lines[:5]}" if stray else ""))
        check(r"\begin{Abstract}" in src[body_end:], "Ukrainian metadata block present at the end")

    heads = re.findall(r"\\section\{([^}]+)\}", src)
    imrad = ["Introduction", "Materials", "Results", "Discussion", "Conclusions"] if LANG == "en" \
        else ["Вступ", "Матеріали", "Результати", "Обговорення", "Висновки"]
    missing = [s for s in imrad if not any(s in h for h in heads)]
    check(not missing, "IMRAD structure complete" + (f" — missing: {missing}" if missing else ""))

    # ------------------------------------------------------------- PROVENANCE
    summary = {r["dimension"]: r for r in load("invariant_features_summary.csv")}
    by_version = {r["version"]: r for r in load("map_invariance_by_version.csv")}
    version_rows = load("version_invariance.csv")
    side_rows = load("side_invariance.csv")
    map_rows = load("map_invariance.csv")

    expected_pcts = []
    for dim in ("map", "version", "side"):
        row = summary[dim]
        pct, n_inv = float(row["pct"]), row["n_invariant"]
        expected_pcts.append(pct)
        check(any(f in src for f in fmt(pct)),
              f"{dim} invariance {pct}% present in the text (outputs/invariant_features_summary.csv)")
        check(n_inv in src, f"{dim}: count {n_inv} of {row['n_total']} present in the text")

    for version, row in by_version.items():
        pct = float(row["pct"])
        expected_pcts.append(pct)
        check(any(f in src for f in fmt(pct)),
              f"sensitivity analysis: {version} map-invariance {pct}% present "
              "(outputs/map_invariance_by_version.csv)")

    n_cs2, n_csgo = version_rows[0]["n_cs2"], version_rows[0]["n_csgo"]
    check(n_cs2 in src and n_csgo in src, f"sample sizes {n_cs2} (CS2) / {n_csgo} (CSGO) in the text")
    check(str(int(n_cs2) + int(n_csgo)) in src,
          f"total sample {int(n_cs2) + int(n_csgo)} in the text")

    # universally invariant (map & version) and triple-invariant (map & version & side)
    inv = {dim: {r["feature"] for r in rows if r["invariant"] == "True"}
           for dim, rows in (("map", map_rows), ("version", version_rows), ("side", side_rows))}
    universal = inv["map"] & inv["version"]
    triple = universal & inv["side"]
    check(str(len(universal)) in src, f"universally invariant count {len(universal)} in the text")
    check(str(len(triple)) in src, f"triple-invariant count {len(triple)} in the text")

    table = re.search(r"\\begin\{tabular\}.*?\\end\{tabular\}", src, re.S)
    if table:
        listed = {feat(m) for m in re.findall(TEXTT, table.group(0))}
        listed = {f for f in listed if f}
        check(listed == triple,
              "Table 1 lists exactly the triple-invariant set recomputed from outputs/"
              + (f" — only in table: {sorted(listed - triple)}; missing: {sorted(triple - listed)}"
                 if listed != triple else ""))
    else:
        check(False, "Table 1 found in the source")

    # effect sizes quoted per feature, checked against the CSV of the subsection they sit in
    dim_tables = {"map": ({r["feature"]: float(r["eta_squared"]) for r in map_rows}, r"\eta^2"),
                  "version": ({r["feature"]: float(r["cohens_d"]) for r in version_rows}, "d"),
                  "side": ({r["feature"]: float(r["cohens_d"]) for r in side_rows}, "d")}
    quoted = 0
    for dim, keys in (("map", ("to the map", "до карти")),
                      ("version", ("game version", "версії гри")),
                      ("side", ("to the side", "до сторони"))):
        head = next((m.start() for m in re.finditer(r"\\subsection\{([^}]+)\}", src)
                     if any(k in m.group(1) for k in keys)), None)
        if head is None:
            continue
        nxt = src.find(r"\subsection", head + 1)
        block = src[head: nxt if nxt > 0 else len(src)]
        values, _ = dim_tables[dim]
        pattern = re.compile(TEXTT + r"[^()]{0,80}?\(\$(?:\\eta\^2|d) = ([\d.,{}]+)\$\)")
        for name, value in pattern.findall(block):
            name = feat(name)
            if name not in values:
                check(False, f"{dim}: feature {name!r} quoted in the text is absent from outputs/")
                continue
            quoted += 1
            # the text rounds; compare at the precision it actually prints
            decimals = len(re.sub(r"[^\d]", "", value.split(".")[-1] if "." in value
                                  else value.split("{,}")[-1]))
            check(round(values[name], decimals) == num(value),
                  f"{dim}: {name} = {num(value)} matches outputs/ ({values[name]:.4g})")
    check(quoted > 0, f"per-feature effect sizes cross-checked against outputs/ ({quoted} values)")

    # no invented one-decimal percentage anywhere in the text
    pca = (ROOT / "outputs" / ("figures_en" if LANG == "en" else "figures") / "captions.md")
    allowed = set(expected_pcts)
    if pca.exists():
        pcs = [float(x) for x in re.findall(r"PC[12] ([\d.]+)%", pca.read_text(encoding="utf-8"))]
        allowed |= set(pcs) | {round(sum(pcs), 1)}
    # group means (27.1 % in CS2 against 17.8 % in CSGO) are provenanced too, but only where the
    # same paragraph names the feature they belong to — otherwise any invented value would pass.
    means: dict[str, set[float]] = {}
    for rows, cols in ((version_rows, ("cs2_mean", "csgo_mean")),
                       (side_rows, ("ct_mean", "t_mean"))):
        for r in rows:
            means.setdefault(r["feature"], set()).update(round(float(r[c]), 1) for c in cols)

    pct_re = re.compile(r"(\d+(?:[.,]|\{,\})\d)\\,\\%")
    invented = []
    for para in re.split(r"\n\s*\n", src):
        local = set(allowed)
        for name in (feat(m) for m in re.findall(TEXTT, para)):
            local |= means.get(name, set())
        invented += [num(m) for m in pct_re.findall(para) if num(m) not in local]
    invented = sorted(set(invented))
    check(not invented,
          "no one-decimal percentage without a source in outputs/"
          + (f" — unaccounted: {invented}" if invented else ""))

    # ------------------------------------------------------------------ report
    failed = [m for ok, m in results if not ok]
    for ok, message in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {message}")
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed  [{TEX.name}]")
    print("Not machine-checkable — left to the author: plagiarism report; no other article by the "
          "same author in this issue; article length and submission deadline confirmed with the "
          "editors; the three template bugs reported to them (see latex/README.md).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
