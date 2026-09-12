# LaTeX-пакет для подання у видання №69 (Вісник ЛНУ)

Видання приймає **лише LaTeX**; рисунки — окремими файлами PDF.
Повні вимоги: `../paper/journal_requirements.md`.

## Збирання

```
make          # pdflatex × 2 -> article.pdf
make clean    # прибрати .aux/.log
```

Потрібен pdfLaTeX з кириличними шрифтами T2A (TeX Live). **Не** lualatex — шаблон видання
розрахований на pdfLaTeX-стек, на відміну від `dissertation/`.

## Файли

| Файл | Походження |
|------|------------|
| `VisnykAMI.tex` | шаблон видання, дві задокументовані зміни (нижче) |
| `stdclsdv.sty`, `tocloft.sty` | з шаблону, без змін |
| `article.tex` | рукопис; текст із `../paper/manuscript_revised.md` |
| `figures/*.pdf` | копії з `../outputs/figures/`, генерує `../scripts/build_figures.py` |

Незайманий оригінал шаблону: `../references/journal_guidelines/VISNYK2019_original/`,
архів як завантажено: `../references/journal_guidelines/VISNYK2019.rar`.

## Зміни в шаблоні видання

1. `inputenc`: `cp1251` → `utf8`. Рядок `\usepackage[utf8]{inputenc}` був у шаблоні
   закоментований авторами — це санкціонована ними альтернатива.
2. Виправлено баг в `UdcUkr`: зайвий `\vspace*` без аргументу давав фатальну помилку
   `Missing \endcsname`. В `UdcEng` бага немає, тому в англомовному зразку видання він не
   виявлявся. **Повідомити редакцію при поданні.**

## Обхідні рішення в `article.tex` (шаблон не чіпають)

- `\def\latinencoding{T2A}` — інакше `babel` перемикає англомовний блок на OT1 і кирилиця
  в колонтитулі ламає збирання (`Command \CYRK unavailable in encoding OT1`).
- `\us` = `\_\allowbreak` — довгі імена ознак (`opening_deaths_per_round`) інакше не
  переносяться і лізуть за поле.
- `\raggedright` + `\tabularnewline` у таблиці — пакет `array` у шаблоні не підключено,
  тож `>{\raggedright\arraybackslash}` недоступний.
- Послаблені параметри float (`textfraction` тощо) — 4 великі рисунки й таблиця на 6 сторінок
  тексту інакше відносять таблицю за чотири сторінки від посилання на неї.

## Оновлення рисунків

```
../../.venv/bin/python ../scripts/build_figures.py && cp ../outputs/figures/*.pdf figures/
```

Рисунки будуються в масштабі 1:1 під смугу набору 13,5 см (`PRINT_W` у скрипті), щоб підписи
лишалися читабельними без стиснення.
