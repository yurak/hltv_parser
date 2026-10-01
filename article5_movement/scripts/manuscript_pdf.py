#!/usr/bin/env python3
"""Рукопис -> PDF для читання: текст + таблиці й рисунки зліпка outputs/paper/.

Не для подання (для ЕлІТ — export_docx.py під шаблон). Тут мета — зручно прочитати
чернетку разом з даними: HTML-коментарі прибрано, позначки [РІШЕННЯ: ...] підсвічено,
таблиці T* і рисунки F* додано після тексту. Рендер — headless Chrome, без мережі.

    /usr/bin/python3 scripts/manuscript_pdf.py [-o paper/manuscript_uk_draft.pdf]
"""
from __future__ import annotations

import argparse, base64, csv, html, re, subprocess, tempfile, time
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "outputs" / "paper"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# назви під нумерацію, на яку посилається текст («табл. N», «рис. N»)
TABLES = [
    ("T1_dataset", 1, "Склад датасету", None),
    ("T2_cohort", 2, "Когорта: гравці з щонайменше трьома серіями (de_mirage)", None),
    ("T3_closed_set", 3, "Закрита множина, протокол (а): точність за родинами ознак", None),
    ("T4_verification", 4, "Верифікація «той самий гравець»", None),
    ("T5_ablation", 5, "Абляція за родинами ознак", None),
    ("T6_degradation", 6, "Деградація при зміні серії та матчу", None),
    ("T7_probe_length", 7, "Точність залежно від кількості раундів проби", None),
    ("T9_temporal", 9, "Верифікація залежно від часового проміжку між серіями", None),
    ("T9_temporal", 9, "Верифікація за проміжком часу між серіями", None),
    ("T10_feature_stability", 10, "Стабільність ознак (ICC), 15 найстабільніших", 15),
    ("T11_channel_ablation", 11, "Канали: чиста локомоція проти бойових ознак", None),
    ("T12_probe_lobby", 12, "Аматори: місце людини серед 10 гравців матчу", None),
    ("T13_probe_hardware", 13, "Аматори: зміна заліза (місце в лобі за каналами)", None),
    ("T14_probe_blind", 14, "Сліпий тест узгодженості акаунта P2", None),
    ("T15_probe_first_bullet", 15, "Точність першої кулі з гвинтівки", None),
    ("T16_outcome_rounds", 16, "Виграний проти програного раунду: 10 найбільших зсувів", 10),
    ("T17_verification_channels", 17, "Верифікація за підмножинами ознак", None),
    ("T18_within_team", 18, "Ідентифікація в межах однієї команди (контроль командного стилю)", None),
    ("T19_groups_summary", 19, "Зведені властивості груп ознак", None),
    ("T17_verification_channels", 17, "Верифікація за наборами ознак; пари партнерів по команді", None),
    ("T18_within_team", 18, "Ідентифікація всередині команди", None),
    ("T19_groups_summary", 19, "Зведення за групами ознак: інформативність і стійкість", None),
]
FIGURES = [
    ("F1_pca_scatter", 1, "Проєкція когорти на дві головні компоненти"),
    ("F2_genuine_impostor", 2, "Розподіли відстаней «свій» / «чужий» і поріг EER"),
    ("F3_roc_det", 3, "ROC- і DET-криві верифікації"),
    ("F4_cmc", 4, "CMC-крива (rank-k) закритої множини"),
    ("F5_probe_length", 5, "Точність залежно від довжини проби"),
    ("F6_families", 6, "Внесок родин ознак"),
    ("F8_degradation", 8, "Деградація при зміні серії та матчу"),
]

CSS = """
@page { size: A4; margin: 22mm 20mm 22mm 22mm;
        @bottom-center { content: counter(page); font-size: 9pt; color: #777; } }
body { font-family: 'Times New Roman', Times, serif; font-size: 11.5pt; line-height: 1.45;
       color: #111; }
h1 { font-size: 17pt; line-height: 1.25; margin: 0.4em 0 0.6em; }
h2 { font-size: 13.5pt; margin: 1.4em 0 0.4em; border-bottom: 1px solid #bbb; padding-bottom: 2px; }
h3 { font-size: 12pt; margin: 1.1em 0 0.3em; }
h4 { font-size: 11.5pt; font-style: italic; margin: 0.9em 0 0.2em; }
p { margin: 0.35em 0; text-align: justify; hyphens: auto; }
li { margin: 0.15em 0; }
hr { border: none; border-top: 1px solid #ddd; margin: 1em 0; }
code { font-family: Menlo, monospace; font-size: 9.5pt; background: #f3f3f3; padding: 0 2px; }
.decision { background: #fff3b0; border-left: 3px solid #e0b000; padding: 1px 4px;
            font-family: Arial, sans-serif; font-size: 9.5pt; color: #5a4500; }
.banner { font-family: Arial, sans-serif; font-size: 9pt; color: #8a1c1c; border: 1px solid #d99;
          background: #fff5f5; padding: 6px 8px; margin-bottom: 1em; }
table { border-collapse: collapse; font-family: Arial, sans-serif; font-size: 8.5pt;
        margin: 0.3em 0 1.1em; width: 100%; page-break-inside: avoid; }
th, td { border: 1px solid #ccc; padding: 2px 4px; text-align: left; vertical-align: top; }
th { background: #f0f0f0; }
.cap { font-family: Arial, sans-serif; font-size: 9.5pt; font-weight: bold; margin-top: 0.8em; }
figure { margin: 0.6em 0 1.2em; page-break-inside: avoid; text-align: center; }
figure img { max-width: 100%; max-height: 105mm; }
figcaption { font-family: Arial, sans-serif; font-size: 9.5pt; margin-top: 3px; }
.pb { page-break-before: always; }
.tbl { page-break-inside: avoid; }
.cap { page-break-after: avoid; }
"""


def mark_decisions(text: str) -> str:
    """[РІШЕННЯ: ...] з вкладеними дужками -> підсвічений span (після рендеру markdown)."""
    out, i, key = [], 0, "[РІШЕННЯ"
    while True:
        j = text.find(key, i)
        if j < 0:
            out.append(text[i:])
            return "".join(out)
        depth, k = 0, j
        while k < len(text):
            depth += text[k] == "["
            depth -= text[k] == "]"
            if depth == 0:
                break
            k += 1
        out += [text[i:j], f'<span class="decision">{text[j:k + 1]}</span>']
        i = k + 1


def fmt(v: str) -> str:
    try:
        f = float(v)
    except ValueError:
        return html.escape(v)
    if f.is_integer() and "." not in v:
        return v
    if f != 0 and abs(f) < 1e-4:
        return "&lt;0.0001"
    return f"{f:.4f}".rstrip("0").rstrip(".")


def table_html(stem: str, n: int, title: str, limit: int | None) -> str:
    p = SNAP / "tables" / f"{stem}.csv"
    if not p.exists():
        return ""
    rows = list(csv.reader(p.open(encoding="utf-8")))
    head, body = rows[0], rows[1:]
    note = ""
    if limit and len(body) > limit:
        note = f" (перші {limit} з {len(body)})"
        body = body[:limit]
    th = "".join(f"<th>{html.escape(h)}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{fmt(c)}</td>" for c in r) + "</tr>" for r in body)
    return (f'<div class="tbl"><div class="cap">Таблиця {n}. {html.escape(title)}{note}</div>'
            f"<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>")


def figure_html(stem: str, n: int, title: str) -> str:
    p = SNAP / "figures" / f"{stem}.png"
    if not p.exists():
        return ""
    b64 = base64.b64encode(p.read_bytes()).decode()
    return (f'<figure><img src="data:image/png;base64,{b64}">'
            f"<figcaption>Рис. {n}. {html.escape(title)}</figcaption></figure>")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", default=str(ROOT / "paper" / "manuscript.md"))
    ap.add_argument("-o", "--output", default=str(ROOT / "paper" / "manuscript_uk_draft.pdf"))
    a = ap.parse_args()

    src = Path(a.input).read_text(encoding="utf-8")
    src = re.sub(r"<!--.*?-->", "", src, flags=re.S)
    body = markdown.markdown(src, extensions=["tables", "sane_lists"])
    body = mark_decisions(body)
    run_id = (SNAP / "run_id.txt").read_text().split()[0] if (SNAP / "run_id.txt").exists() else "?"
    banner = (f'<div class="banner">РОБОЧА ЧЕРНЕТКА — не для подання. Зібрано '
              f'{time.strftime("%d.%m.%Y %H:%M")} з {html.escape(Path(a.input).name)}; числа — '
              f'зліпок {html.escape(run_id)}. Жовтим позначено місця, де потрібне рішення автора. '
              f'Текст підготовлено за участі ШІ-асистента й має бути перевірений і переписаний '
              f'авторами.</div>')
    listed = {t[0] for t in TABLES}
    extra = []
    for p in sorted((SNAP / "tables").glob("T*.csv")):   # нові таблиці — не губити
        if p.stem not in listed:
            m = re.match(r"T(\d+)_", p.stem)
            extra.append((p.stem, int(m.group(1)) if m else 0, p.stem + " (без назви в збирачі)", None))
    tables = "".join(table_html(*t) for t in sorted(TABLES + extra, key=lambda t: t[1]))
    figs = "".join(figure_html(*f) for f in FIGURES)
    doc = (f"<!doctype html><html lang='uk'><head><meta charset='utf-8'><style>{CSS}</style>"
           f"</head><body>{banner}{body}"
           f"<h2 class='pb'>Додаток: таблиці</h2>{tables}"
           f"<h2 class='pb'>Додаток: рисунки</h2>{figs}</body></html>")

    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / "m.html"
        h.write_text(doc, encoding="utf-8")
        out = Path(a.output).resolve()
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={out}", h.as_uri()], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"-> {out} ({out.stat().st_size // 1024} КБ)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
