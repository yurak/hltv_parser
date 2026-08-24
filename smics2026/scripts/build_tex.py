#!/usr/bin/env python3
"""Build a LaTeX (ceurart) version of the abstract from the same paper/abstract.md.

The ODT built by build_odt.py stays the submission format — this script exists so the
same text can be studied and compiled in LaTeX, with one source of truth for the words.

    python3 scripts/build_tex.py            # writes latex/abstract.tex
    python3 scripts/build_tex.py --compile  # ... and compiles it with pdflatex

Output goes to latex/, next to the official ceurart.cls shipped by the conference.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_odt import SOURCE, parse_source  # same parser, same source file

ROOT = Path(__file__).resolve().parent.parent
OUT_TEX = ROOT / "latex" / "abstract.tex"
FIGURE_WIDTH = r"0.85\textwidth"

# Unicode used in abstract.md -> LaTeX, so the file also compiles with plain pdflatex.
UNICODE = {
    "χ²": r"$\chi^2$", "χ": r"$\chi$", "λ": r"$\lambda$", "²": r"$^2$",
    "≥": r"$\ge$", "≤": r"$\le$", "·": r"$\cdot$", "×": r"$\times$", "−": r"$-$",
    "“": "``", "”": "''", "’": "'", "—": "---", "–": "--", "\u00a0": "~",
}
SPECIALS = {"&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_", "$": r"\$",
            "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def esc(text: str) -> str:
    """Escape LaTeX specials in plain text (inline markup is handled before this)."""
    return "".join(SPECIALS.get(ch, ch) for ch in text)


def inline(text: str) -> str:
    """Markdown inline subset -> LaTeX, then citations, superscripts and unicode."""
    out, i = [], 0
    pattern = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|\^(-?[0-9A-Za-z.]+)|\[(\d+)\]")
    for m in pattern.finditer(text):
        out.append(esc(text[i:m.start()]))
        if m.group(1) is not None:
            out.append(r"\textbf{" + esc(m.group(1)) + "}")
        elif m.group(2) is not None:
            out.append(r"\emph{" + esc(m.group(2)) + "}")
        elif m.group(3) is not None:
            out.append(r"\texttt{" + esc(m.group(3)) + "}")
        elif m.group(4) is not None:
            out.append("$^{" + m.group(4) + "}$")
        else:
            out.append(r"\cite{ref" + m.group(5) + "}")
        i = m.end()
    out.append(esc(text[i:]))
    result = "".join(out)
    for src, dst in UNICODE.items():
        result = result.replace(src, dst)
    return result


def front_matter(meta: dict) -> str:
    names = [n.strip() for n in re.split(r",| and ", meta["authors"]) if n.strip()]
    orcids = dict(re.findall(r"(\S+)\s*\(([^)]+)\)", meta["orcids"]))
    emails = dict(re.findall(r"(\S+)\s*\(([^)]+)\)", meta["emails"]))

    authors = []
    for index, raw in enumerate(names):
        name = re.sub(r"\^\d+", "", raw).strip()
        surname = name.split()[-1]
        options = [f"orcid={o}" for o, who in orcids.items() if surname in who]
        options += [f"email={e}" for e, who in emails.items() if surname in who]
        block = f"\\author[1]{{{esc(name)}}}[%\n  " + ",\n  ".join(options) + ",\n]"
        if index == 0:
            block += "\n\\cormark[1]"
        authors.append(block)

    keywords = " \\sep\n  ".join(esc(k.strip()) for k in meta["keywords"].split(","))
    return "\n".join([
        r"\documentclass{ceurart}",
        r"\sloppy",
        "",
        r"\begin{document}",
        r"\copyrightyear{2026}",
        r"\copyrightclause{Copyright for this paper by its authors."
        "\n  Use permitted under Creative Commons License Attribution 4.0"
        "\n  International (CC BY 4.0).}",
        "",
        f"\\conference{{{esc(meta['event'])}}}",
        "",
        f"\\title{{{inline(meta['title'])}}}",
        "",
        "\n\n".join(authors),
        "",
        f"\\address[1]{{{esc(meta['affiliation1'])}}}",
        f"\\cortext[1]{{{esc(meta['corresponding'])}.}}",
        "",
        r"\begin{abstract}",
        "  " + inline(meta["abstract"]),
        r"\end{abstract}",
        "",
        r"\begin{keywords}",
        "  " + keywords,
        r"\end{keywords}",
        "",
        r"\maketitle",
        "",
    ])


def body(blocks: list[dict]) -> str:
    out, refs = [], []
    for block in blocks:
        kind = block["kind"]
        if kind == "h1":
            out.append(f"\\section{{{inline(block['text'])}}}\n")
        elif kind == "h2":
            out.append(f"\\subsection{{{inline(block['text'])}}}\n")
        elif kind == "para":
            out.append(inline(block["text"]) + "\n")
        elif kind == "figure":
            name = Path(block["src"]).name
            out.append("\n".join([
                r"\begin{figure}[htbp]",
                r"  \centering",
                f"  \\includegraphics[width={FIGURE_WIDTH}]{{figures/{name}}}",
                f"  \\caption{{{inline(block['caption'])}}}",
                r"  \label{fig:families}",
                r"\end{figure}",
                "",
            ]))
        elif kind == "table":
            out.append(table(block))
        elif kind == "refhead":
            out.append(r"\begin{thebibliography}{99}")
        elif kind == "ref":
            refs.append(block["text"])
    for number, entry in enumerate(refs, start=1):
        out.append(f"\\bibitem{{ref{number}}}\n  {inline(entry)}\n")
    if refs:
        out.append(r"\end{thebibliography}")
    out.append("")
    out.append(r"\end{document}")
    return "\n".join(out)


def table(block: dict) -> str:
    rows = block["rows"]
    ncols = max(len(r) for r in rows)
    spec = "l" + "c" * (ncols - 1)
    lines = [r"\begin{table}[htbp]", r"  \centering",
             f"  \\caption{{{inline(block['caption'])}}}",
             r"  \label{tab:ablation}",
             f"  \\begin{{tabular}}{{{spec}}}", r"    \toprule"]
    for index, row in enumerate(rows):
        cells = " & ".join(inline(c) for c in row + [""] * (ncols - len(row)))
        lines.append(f"    {cells} \\\\")
        if index == 0:
            lines.append(r"    \midrule")
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


def compile_tex() -> None:
    pdflatex = shutil.which("pdflatex") or "/Library/TeX/texbin/pdflatex"
    if not Path(pdflatex).exists():
        print("pdflatex not found — install MacTeX first (see latex/README.md)", file=sys.stderr)
        sys.exit(2)
    for run in range(2):                      # second pass resolves refs and citations
        result = subprocess.run([pdflatex, "-interaction=nonstopmode", OUT_TEX.name],
                                cwd=OUT_TEX.parent, capture_output=True, text=True)
        if result.returncode != 0:
            tail = "\n".join(l for l in result.stdout.splitlines() if l.startswith("!"))
            print(f"pdflatex failed on pass {run + 1}:\n{tail}", file=sys.stderr)
            sys.exit(1)
    pdf = OUT_TEX.with_suffix(".pdf")
    pages = subprocess.run([shutil.which("pdfinfo") or "pdfinfo", str(pdf)],
                           capture_output=True, text=True).stdout
    print(f"PDF written: {pdf.relative_to(ROOT)} — "
          + (re.search(r"^Pages:\s+\d+$", pages, re.M) or ["pages unknown"])[0])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compile", action="store_true", help="run pdflatex twice afterwards")
    args = parser.parse_args()

    meta, blocks = parse_source(SOURCE)
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_TEX.write_text(front_matter(meta) + body(blocks) + "\n", encoding="utf-8")
    print(f"TeX written: {OUT_TEX.relative_to(ROOT)}")
    if args.compile:
        compile_tex()
