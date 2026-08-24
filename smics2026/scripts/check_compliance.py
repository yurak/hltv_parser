#!/usr/bin/env python3
"""Check the built abstract against the SMICS-2026 requirements.

Run after scripts/build_odt.py:
    python3 scripts/check_compliance.py

Checks: page count (3-5), A4 geometry, embedded Libertinus fonts, English-only text, tables
unsplit across pages, mandatory content sections, citation integrity, and the 30 % self-citation limit.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "paper" / "abstract.md"
PDF = ROOT / "paper" / "Kuzhii_SMICS2026_abstract.pdf"
ODT = ROOT / "paper" / "Kuzhii_SMICS2026_abstract.odt"

PAGE_MIN, PAGE_MAX = 3, 5
SELF_CITATION_LIMIT = 0.30
SELF_AUTHORS = ("Kuzhii", "Furgala")
MAX_AUTHORS, MAX_ABSTRACTS_PER_AUTHOR = 5, 2
KEYWORDS_MIN, KEYWORDS_MAX = 3, 8   # conference sets no limit; CEUR practice is 3-8

# The four sections the conference requires the text to contain.
REQUIRED = {
    "problem statement": "Introduction",
    "novelty vs known works": "Novelty",
    "proposed solution": "Feature Space and Methods",
    "conclusions with results": "Conclusions",
}

results: list[tuple[bool, str]] = []


def check(ok: bool, message: str) -> None:
    results.append((ok, message))


def main() -> int:
    if not PDF.exists() or not ODT.exists():
        print("build first: python3 scripts/build_odt.py", file=sys.stderr)
        return 2

    text = SOURCE.read_text(encoding="utf-8")
    body, refs = text.split("## References")

    # --- length and page geometry
    info = subprocess.run([shutil.which("pdfinfo") or "pdfinfo", str(PDF)],
                          check=True, capture_output=True, text=True).stdout
    pages = int(re.search(r"^Pages:\s+(\d+)$", info, re.M).group(1))
    check(PAGE_MIN <= pages <= PAGE_MAX, f"length: {pages} pages (required {PAGE_MIN}-{PAGE_MAX})")
    size = re.search(r"^Page size:\s+(\S+) x (\S+) pts", info, re.M)
    a4 = abs(float(size.group(1)) - 595.276) < 1.5 and abs(float(size.group(2)) - 841.89) < 1.5
    check(a4, f"page size: {size.group(1)} x {size.group(2)} pts (A4 expected)")

    # --- fonts
    fonts = subprocess.run([shutil.which("pdffonts") or "pdffonts", str(PDF)],
                           check=True, capture_output=True, text=True).stdout
    families = sorted({m.group(1) for m in re.finditer(r"\+(\S+)", fonts)})
    non_libertinus = [f for f in families if "Libertinus" not in f]
    check(bool(families) and not non_libertinus,
          f"fonts: {', '.join(families)}" + (f" — non-Libertinus: {non_libertinus}" if non_libertinus else ""))
    check(all("yes" in line.split()[-4:-1] for line in fonts.splitlines()[2:] if line.strip()),
          "fonts embedded in the PDF")

    # --- language
    cyrillic = sorted(set(re.findall(r"[Ѐ-ӿ]+", text)))
    check(not cyrillic, "language: English only" + (f" — found {cyrillic[:3]}" if cyrillic else ""))

    # --- mandatory sections
    headings = re.findall(r"^## (.+)$", body, re.M)
    for label, needle in REQUIRED.items():
        check(any(needle.lower() in h.lower() for h in headings), f"section present: {label}")

    # --- authorship limits
    authors = re.search(r"^authors:\s*(.+)$", text, re.M).group(1)
    n_authors = len(re.split(r",| and ", authors))
    check(n_authors <= MAX_AUTHORS, f"authors: {n_authors} (max {MAX_AUTHORS})")

    # --- citations
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", body)}
    listed = {int(m.group(1)) for m in re.finditer(r"^(\d+)\.\s", refs, re.M)}
    check(not listed - cited, f"no orphan references" + (f" — {sorted(listed - cited)}" if listed - cited else ""))
    check(not cited - listed, f"no dangling citations" + (f" — {sorted(cited - listed)}" if cited - listed else ""))

    own = [n for n in sorted(listed)
           if any(a in re.search(rf"^{n}\..*$", refs, re.M).group(0) for a in SELF_AUTHORS)]
    share = len(own) / len(listed) if listed else 0
    check(share <= SELF_CITATION_LIMIT,
          f"self-citation: {len(own)}/{len(listed)} = {share:.1%} (limit {SELF_CITATION_LIMIT:.0%})")

    # --- keywords: count, how many lines they occupy, and lexical support in the text
    keywords = [k.strip() for k in
                re.search(r"^keywords:\s*(.+)$", text, re.M).group(1).split(",") if k.strip()]
    page1 = subprocess.run([shutil.which("pdftotext") or "pdftotext", "-f", "1", "-l", "1",
                            str(PDF), "-"], check=True, capture_output=True, text=True).stdout
    tail = page1.split("Keywords", 1)[1].strip().split("\n")
    rendered = []
    for line in tail:
        if not line.strip() or re.match(r"^\d+\.\s", line.strip()):
            break
        rendered.append(line.strip())
    check(KEYWORDS_MIN <= len(keywords) <= KEYWORDS_MAX,
          f"keywords: {len(keywords)} items on {len(rendered)} rendered line(s) "
          f"(allowed {KEYWORDS_MIN}-{KEYWORDS_MAX}) — {', '.join(keywords)}")
    lowered = body.lower()
    unsupported = [k for k in keywords
                   if not any(w[:6] in lowered for w in re.findall(r"[a-z]{5,}", k.lower()))]
    check(not unsupported, "keywords backed by the text"
          + (f" — unsupported: {unsupported}" if unsupported else ""))

    # --- every table stays whole on one page, together with its caption
    page_text = [subprocess.run([shutil.which("pdftotext") or "pdftotext", "-f", str(n), "-l", str(n),
                                 str(PDF), "-"], check=True, capture_output=True, text=True).stdout
                 for n in range(1, pages + 1)]
    for number, rows in enumerate(re.findall(r"^Table \[.*?\n((?:\|.*\n)+)", body, re.M), start=1):
        labels = [re.sub(r"\*\*|\*", "", r.strip("|").split("|")[0]).strip()
                  for r in rows.strip().split("\n")]
        labels = [l for l in labels if l and not set(l) <= set("-: ")]
        anchors = [f"Table {number}"] + labels
        located = {a: {n for n, text in enumerate(page_text, start=1) if a in text} for a in anchors}
        missing = [a for a, pgs in located.items() if not pgs]
        shared = set.intersection(*(pgs for pgs in located.values() if pgs)) if not missing else set()
        check(bool(shared),
              f"table {number} unsplit: caption and all {len(labels)} rows on one page"
              + (f" — missing in PDF: {missing}" if missing
                 else "" if shared else f" — spread over {sorted(set().union(*located.values()))}"))

    # --- figures resolve
    for src in re.findall(r"!\[.*?\]\((.+?)\)", body):
        path = (SOURCE.parent / src.split(")")[0]).resolve()
        check(path.exists(), f"figure present: {src}")

    failed = [m for ok, m in results if not ok]
    for ok, message in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {message}")
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    print("Manual checks left to the author: Libertinus installed in LibreOffice on the "
          f"submitting machine; max {MAX_ABSTRACTS_PER_AUTHOR} abstracts per author across the "
          "conference; registration form submitted before September 1, 2026.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
