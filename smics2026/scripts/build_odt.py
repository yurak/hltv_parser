#!/usr/bin/env python3
"""Build the SMICS-2026 abstract as an ODT from the official CEURART template.

The template (template/smics2026_abstract_template.odt) is never restyled: page geometry,
paragraph/character styles and the Libertinus font declarations are taken from it verbatim,
as the conference requires. Only the *content* of the front matter and the body is replaced,
using the styles already embedded in the template.

Source text: paper/abstract.md (front matter + a small markdown subset).
Output:      paper/Kuzhii_SMICS2026_abstract.odt (+ .pdf when LibreOffice is available).

Usage:
    python3 scripts/build_odt.py [--no-pdf]
"""

from __future__ import annotations

import argparse
import re
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "template" / "smics2026_abstract_template.odt"
SOURCE = ROOT / "paper" / "abstract.md"
OUT_ODT = ROOT / "paper" / "Kuzhii_SMICS2026_abstract.odt"
SOFFICE = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")

PAGE_MIN, PAGE_MAX = 3, 5          # conference requirement: exactly 3-5 full A4 pages
TEXT_WIDTH_IN = 6.2208             # 8.2681 - 1.0634 (left) - 0.9839 (right)
FIGURE_WIDTH_IN = 5.0              # figures are centred and stay inside the text block

# Paragraph/character styles that already exist in the template.
S_TITLE, S_AUTHORS, S_UNIV = "P1", "P2", "University"
S_ABS_TITLE, S_ABS_TEXT = "Abstract_20_Title", "Abstract_20_Text"
S_KW_WORDS = "Keywords_20_words"
S_H1, S_H2 = "P8", "P11"
S_FIRST_PARA, S_PARA = "P9", "Standard"   # P9 = no first-line indent (after a heading)
S_FIG, S_FIG_CAPTION = "Figure", "Figure_20_caption"
S_TBL_NUMBER, S_TBL_CAPTION = "Table_20_number", "Table_20_caption"
S_TBL_CELL_HEAD, S_TBL_CELL_BODY = "Tabelle3.A1", "Tabelle3.A3"
S_TBL_CELL_LAST = "Tabelle3.A5"
S_CELL_PARA, S_CELL_PARA_LEFT = "P21", "P22"   # the template's own cell paragraphs
S_REF_HEAD, S_REF_ITEM = "P32", "P33"
S_SUPER, S_CAPTION_CHAR = "T6", "Figure_20_caption_20_Char"


# --------------------------------------------------------------------------- helpers

def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def typography(text: str) -> str:
    text = text.replace(">=", "≥").replace("<=", "≤").replace("--", "—")
    out, opening = [], True          # straight quotes -> typographic pairs
    for ch in text:
        if ch == '"':
            out.append("\u201c" if opening else "\u201d")
            opening = not opening
        else:
            out.append(ch)
    return "".join(out)


def inline(text: str) -> str:
    """Convert the inline markdown subset to ODF spans.

    **bold** -> bold span, *italic* / `code` -> italic span, ^token -> superscript.
    Bold and italic character styles are added to the document's automatic styles; the
    template's own text styles carry no emphasis, and emphasis changes no page geometry.
    """
    text = typography(text)
    out, i = [], 0
    pattern = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|\^(-?[0-9A-Za-z.]+)")
    for m in pattern.finditer(text):
        out.append(esc(text[i:m.start()]))
        if m.group(1) is not None:
            out.append(f'<text:span text:style-name="SMICSBold">{esc(m.group(1))}</text:span>')
        elif m.group(2) is not None:
            out.append(f'<text:span text:style-name="SMICSItalic">{esc(m.group(2))}</text:span>')
        elif m.group(3) is not None:
            out.append(f'<text:span text:style-name="SMICSItalic">{esc(m.group(3))}</text:span>')
        else:
            out.append(f'<text:span text:style-name="{S_SUPER}">{esc(m.group(4))}</text:span>')
        i = m.end()
    out.append(esc(text[i:]))
    return "".join(out)


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG")
    width, height = struct.unpack(">II", head[16:24])
    return width, height


# --------------------------------------------------------------------------- source parsing

def parse_source(path: Path) -> tuple[dict, list[dict]]:
    lines = path.read_text(encoding="utf-8").split("\n")
    if lines[0].strip() != "---":
        raise SystemExit("abstract.md must start with a '---' front-matter block")
    end = lines.index("---", 1)

    meta, key = {}, None
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue                     # blank line or a "#" comment (e.g. keyword variants)
        m = re.match(r"([A-Za-z0-9_]+):\s*(.*)$", line)
        if m and not line[0].isspace():
            key = m.group(1)
            meta[key] = m.group(2).strip()
        elif key:
            meta[key] += " " + line.strip()

    blocks: list[dict] = []
    buf: list[str] = []
    in_refs = False
    pending_caption: str | None = None
    pending_widths: list[float] | None = None
    table: list[list[str]] | None = None

    def flush_para() -> None:
        nonlocal buf
        if buf:
            blocks.append({"kind": "para", "text": " ".join(buf).strip()})
            buf = []

    def flush_table() -> None:
        nonlocal table, pending_caption, pending_widths
        if table:
            blocks.append({"kind": "table", "rows": table, "caption": pending_caption or "",
                           "widths": pending_widths})
        table, pending_caption, pending_widths = None, None, None

    for raw in lines[end + 1:]:
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue                              # markdown header separator
            flush_para()
            table = (table or []) + [cells]
            continue
        flush_table()

        if not stripped:
            flush_para()
            continue
        m = re.match(r"Table\s*(?:\[([\d,\s.]+)\])?:\s*(.*)$", stripped)
        if m:
            flush_para()
            pending_caption = m.group(2).strip()
            pending_widths = [float(x) for x in m.group(1).split(",")] if m.group(1) else None
            continue
        if stripped.startswith("!["):
            flush_para()
            m = re.match(r"!\[(.*)\]\((.+?)\)(?:\{([\d.]+)\})?$", stripped)
            blocks.append({"kind": "figure", "caption": m.group(1), "src": m.group(2),
                           "width": float(m.group(3)) if m.group(3) else None})
            continue
        if stripped.startswith("### "):
            flush_para()
            blocks.append({"kind": "h2", "text": stripped[4:]})
            continue
        if stripped.startswith("## "):
            flush_para()
            title = stripped[3:]
            in_refs = title.lower() == "references"
            blocks.append({"kind": "refhead" if in_refs else "h1", "text": title})
            continue
        if in_refs and re.match(r"\d+\.\s", stripped):
            flush_para()
            blocks.append({"kind": "ref", "text": re.sub(r"^\d+\.\s+", "", stripped)})
            continue
        buf.append(stripped)

    flush_para()
    flush_table()
    return meta, blocks


# --------------------------------------------------------------------------- front matter

def build_front_matter(front: str, meta: dict) -> str:
    """Replace the demo content of the template's front matter, keeping its markup."""
    # Title.
    front = re.sub(
        r'<text:p text:style-name="P1">.*?</text:p>',
        f'<text:p text:style-name="{S_TITLE}">{inline(meta["title"])}</text:p>',
        front, count=1, flags=re.S)

    # Authors (affiliation marks as superscripts, exactly as in the template).
    authors = re.sub(r"\^(\d+)", lambda m: f'<text:span text:style-name="T3">{m.group(1)}</text:span>',
                     esc(meta["authors"]))
    front = re.sub(r'<text:p text:style-name="P2">.*?</text:p>',
                   f'<text:p text:style-name="{S_AUTHORS}">{authors}</text:p>',
                   front, count=1, flags=re.S)

    # Affiliations: collapse the template's three University paragraphs into ours.
    affiliations = [(k, v) for k, v in sorted(meta.items()) if k.startswith("affiliation")]
    univ = "".join(
        f'<text:p text:style-name="{S_UNIV}">'
        f'<text:span text:style-name="{S_SUPER}">{n}</text:span> {esc(text)}</text:p>'
        for n, (_, text) in enumerate(affiliations, start=1))
    front = re.sub(r'(<text:p text:style-name="University">.*?</text:p>)+', univ,
                   front, count=1, flags=re.S)

    # Abstract text and keywords.
    front = re.sub(r'<text:p text:style-name="Abstract_20_Text">.*?</text:p>',
                   f'<text:p text:style-name="{S_ABS_TEXT}">{inline(meta["abstract"])}</text:p>',
                   front, count=1, flags=re.S)
    front = front.replace("paper template, paper formatting, CEUR-WS", esc(meta["keywords"]), 1)

    # Front-matter footnote: event line, corresponding author, e-mails, ORCIDs.
    front = front.replace(
        '<text:note-body>',
        f'<text:note-body><text:p text:style-name="Footnote">{esc(meta["event"])}</text:p>', 1)
    front = front.replace('Corresponding author<text:span text:style-name="T12">s</text:span>',
                          esc(meta["corresponding"]), 1)
    front = replace_after_frame(front, "P3", meta["emails"])
    front = replace_after_frame(front, "Footnote", meta["orcids"], link_prefix="https://orcid.org/")
    return front


def replace_after_frame(front: str, style: str, payload: str, link_prefix: str = "mailto:") -> str:
    """Keep the icon frame of a front-matter footnote paragraph, replace the text after it."""
    pattern = re.compile(
        r'(<text:p text:style-name="%s">(?:<draw:frame.*?</draw:frame>)?<text:s/>).*?(</text:p>)'
        % re.escape(style), re.S)
    items = []
    for chunk in payload.split(";"):
        chunk = chunk.strip()
        m = re.match(r"(\S+)\s*(\(.*\))?$", chunk)
        target, tail = m.group(1), (m.group(2) or "")
        items.append(
            f'<text:a xlink:type="simple" xlink:href="{link_prefix}{esc(target)}" '
            f'text:style-name="Internet_20_link" text:visited-style-name="Visited_20_Internet_20_Link">'
            f'<text:span text:style-name="Internet_20_link">{esc(target)}</text:span></text:a>'
            + (f" {esc(tail)}" if tail else ""))
    return pattern.sub(lambda m: m.group(1) + "; ".join(items) + m.group(2), front, count=1)


# --------------------------------------------------------------------------- body

def build_body(blocks: list[dict], pictures: dict[str, Path]) -> str:
    out: list[str] = []
    after_heading = True
    fig_no = tbl_no = 0

    for block in blocks:
        kind = block["kind"]
        if kind == "h1":
            out.append(f'<text:h text:style-name="{S_H1}" text:outline-level="1">'
                       f'{inline(block["text"])}</text:h>')
            after_heading = True
        elif kind == "h2":
            out.append(f'<text:h text:style-name="{S_H2}" text:outline-level="2">'
                       f'{inline(block["text"])}</text:h>')
            after_heading = True
        elif kind == "para":
            style = S_FIRST_PARA if after_heading else S_PARA
            out.append(f'<text:p text:style-name="{style}">{inline(block["text"])}</text:p>')
            after_heading = False
        elif kind == "figure":
            fig_no += 1
            out.append(figure_xml(block, fig_no, pictures))
            after_heading = False
        elif kind == "table":
            tbl_no += 1
            out.append(table_xml(block, tbl_no))
            after_heading = False
        elif kind == "refhead":
            out.append(f'<text:h text:style-name="{S_REF_HEAD}" text:outline-level="1">'
                       f'{inline(block["text"])}</text:h><text:list text:style-name="WWNum24">')
        elif kind == "ref":
            out.append(f'<text:list-item><text:p text:style-name="{S_REF_ITEM}">'
                       f'{inline(block["text"])}</text:p></text:list-item>')
    if any(b["kind"] == "ref" for b in blocks):
        out.append("</text:list>")
    return "".join(out)


def figure_xml(block: dict, number: int, pictures: dict[str, Path]) -> str:
    name = pictures[block["src"]].name
    width_px, height_px = png_size(pictures[block["src"]])
    width = min(block.get("width") or FIGURE_WIDTH_IN, TEXT_WIDTH_IN)
    height = width * height_px / width_px
    caption = (f'<text:span text:style-name="{S_CAPTION_CHAR}">Figure {number}: '
               f'</text:span>{inline(block["caption"])}')
    return (
        f'<text:p text:style-name="{S_FIG}">'
        f'<draw:frame draw:style-name="fr1" draw:name="Figure {number}" text:anchor-type="as-char" '
        f'svg:width="{width:.4f}in" svg:height="{height:.4f}in" draw:z-index="0">'
        f'<draw:image xlink:href="Pictures/{name}" xlink:type="simple" xlink:show="embed" '
        f'xlink:actuate="onLoad" draw:mime-type="image/png"/></draw:frame></text:p>'
        f'<text:p text:style-name="{S_FIG_CAPTION}">{caption}</text:p>')


def table_xml(block: dict, number: int) -> str:
    rows = block["rows"]
    ncols = max(len(r) for r in rows)
    weights = block.get("widths") or [1.0] * ncols
    if len(weights) != ncols:
        raise SystemExit(f"table {number}: {len(weights)} widths for {ncols} columns")
    total = sum(weights)
    fractions = [w / total for w in weights]
    name = f"SMICSTable{number}"

    columns = "".join(f'<table:table-column table:style-name="{name}.C{i}"/>' for i in range(ncols))
    body = []
    for idx, row in enumerate(rows):
        cells = []
        for col, cell in enumerate(row + [""] * (ncols - len(row))):
            if idx == 0:
                cell_style = S_TBL_CELL_HEAD
            elif idx == len(rows) - 1:
                cell_style = S_TBL_CELL_LAST
            else:
                cell_style = S_TBL_CELL_BODY
            para = S_CELL_PARA_LEFT if fractions[col] > 0.25 else S_CELL_PARA
            cells.append(f'<table:table-cell table:style-name="{cell_style}" '
                         f'office:value-type="string"><text:p text:style-name="{para}">'
                         f'{inline(cell)}</text:p></table:table-cell>')
        body.append(f'<table:table-row table:style-name="Tabelle3.1">{"".join(cells)}</table:table-row>')

    caption = (f'<text:p text:style-name="{S_TBL_NUMBER}">Table '
               f'<text:sequence text:ref-name="refSMICSTable{number}" text:name="Table" '
               f'text:formula="ooow:Table+1" style:num-format="1">{number}</text:sequence></text:p>'
               f'<text:p text:style-name="{S_TBL_CAPTION}">{inline(block["caption"])}</text:p>')
    return (caption + f'<table:table table:name="{name}" table:style-name="{name}">'
            + columns + "".join(body) + "</table:table>"
            + f'<text:p text:style-name="{S_PARA}"/>')


def extra_styles(blocks: list[dict]) -> str:
    """Emphasis character styles plus one table/column style per table (no geometry changes)."""
    styles = [
        '<style:style style:name="SMICSBold" style:family="text">'
        '<style:text-properties fo:font-weight="bold" style:font-weight-asian="bold"/></style:style>',
        '<style:style style:name="SMICSItalic" style:family="text">'
        '<style:text-properties fo:font-style="italic" style:font-style-asian="italic"/></style:style>',
    ]
    n = 0
    for block in blocks:
        if block["kind"] != "table":
            continue
        n += 1
        ncols = max(len(r) for r in block["rows"])
        weights = block.get("widths") or [1.0] * ncols
        total = sum(weights)
        styles.append(
            f'<style:style style:name="SMICSTable{n}" style:family="table">'
            f'<style:table-properties style:width="{TEXT_WIDTH_IN:.4f}in" fo:margin-top="0in" '
            f'fo:margin-bottom="0in" table:align="center" style:writing-mode="lr-tb" style:may-break-between-rows="false"/></style:style>')
        for i, weight in enumerate(weights):
            styles.append(
                f'<style:style style:name="SMICSTable{n}.C{i}" style:family="table-column">'
                f'<style:table-column-properties style:column-width='
                f'"{TEXT_WIDTH_IN * weight / total:.4f}in"/></style:style>')
    return "".join(styles)


# --------------------------------------------------------------------------- assembly

def build(no_pdf: bool = False) -> None:
    meta, blocks = parse_source(SOURCE)
    with zipfile.ZipFile(TEMPLATE) as zf:
        content = zf.read("content.xml").decode("utf-8")
        manifest = zf.read("META-INF/manifest.xml").decode("utf-8")
        names = zf.namelist()

    pictures: dict[str, Path] = {}
    for block in blocks:
        if block["kind"] == "figure":
            src = (SOURCE.parent / block["src"]).resolve()
            if not src.exists():
                raise SystemExit(f"figure not found: {src}")
            pictures[block["src"]] = src

    start = content.index('<text:p text:style-name="P1">')
    body_start = content.index('<text:h text:style-name="P8" text:outline-level="1">')
    tail_start = content.index("</office:text>")

    front = build_front_matter(content[start:body_start], meta)
    body = build_body(blocks, pictures)
    new_content = (content[:start].replace("</office:automatic-styles>",
                                           extra_styles(blocks) + "</office:automatic-styles>", 1)
                   + front + body + content[tail_start:])

    for src_name, path in pictures.items():
        entry = f'<manifest:file-entry manifest:full-path="Pictures/{path.name}" manifest:media-type="image/png"/>'
        if entry not in manifest:
            manifest = manifest.replace("</manifest:manifest>", " " + entry + "\n</manifest:manifest>")

    OUT_ODT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TEMPLATE) as zf, zipfile.ZipFile(OUT_ODT, "w") as out:
        out.writestr(zipfile.ZipInfo("mimetype"), zf.read("mimetype"), zipfile.ZIP_STORED)
        for name in names:
            if name in ("mimetype", "content.xml", "META-INF/manifest.xml"):
                continue
            out.writestr(name, zf.read(name), zipfile.ZIP_DEFLATED)
        out.writestr("content.xml", new_content.encode("utf-8"), zipfile.ZIP_DEFLATED)
        out.writestr("META-INF/manifest.xml", manifest.encode("utf-8"), zipfile.ZIP_DEFLATED)
        for path in pictures.values():
            out.writestr(f"Pictures/{path.name}", path.read_bytes(), zipfile.ZIP_DEFLATED)

    print(f"ODT written: {OUT_ODT.relative_to(ROOT)}")
    if not no_pdf:
        pages = to_pdf()
        if pages is not None:
            verdict = "OK" if PAGE_MIN <= pages <= PAGE_MAX else "OUT OF RANGE"
            print(f"pages: {pages} (required {PAGE_MIN}-{PAGE_MAX}) -> {verdict}")
            if not PAGE_MIN <= pages <= PAGE_MAX:
                sys.exit(1)


def to_pdf() -> int | None:
    if not SOFFICE.exists():
        print("LibreOffice not found - skipping PDF render and page count", file=sys.stderr)
        return None
    profile = ROOT / ".loprofile"
    subprocess.run(
        [str(SOFFICE), "--headless", f"-env:UserInstallation=file://{profile}",
         "--convert-to", "pdf", "--outdir", str(OUT_ODT.parent), str(OUT_ODT)],
        check=True, capture_output=True)
    pdf = OUT_ODT.with_suffix(".pdf")
    shutil.rmtree(profile, ignore_errors=True)
    print(f"PDF written: {pdf.relative_to(ROOT)}")
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        info = subprocess.run([pdfinfo, str(pdf)], check=True, capture_output=True, text=True).stdout
        return int(re.search(r"^Pages:\s+(\d+)$", info, re.M).group(1))
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-pdf", action="store_true", help="skip the LibreOffice PDF render")
    build(**vars(parser.parse_args()))
