# SMICS-2026 — тези доповіді (Track 2)

Тези для міжнародної конференції «Безпека сучасних інформаційних та комунікаційних систем»
(SMICS-2026, ЛНУ ім. Івана Франка + UKEN, Краків, 24–25.09.2026), **секція TRACK 2** — методи протидії
дезінформаційному впливу та соціальній інженерії.

Матеріал побудований на аналізі з `article4_v2/` (стаття для журналу №47, Дніпро), але це **окремий текст**
під англомовний CEURART-формат: інший заголовок, інший фокус (card-testing як атака на платіжні шлюзи),
без дублювання розділів статті.

- **Назва:** Velocity Features as the Structural Invariant of Card-Testing Attacks in Online Payment Systems
- **Автори:** Yurii Kuzhii, Yurii Furgala (ЛНУ ім. Івана Франка)
- **Обсяг:** 5 повних сторінок A4 (вимога — рівно 3–5)

## Структура

```
paper/
  abstract.md                      джерело тексту (front matter + markdown-підмножина)
  figures/F2_family_separability.png  єдина фігура (з article4_v2/outputs/figures_en/)
  Kuzhii_SMICS2026_abstract.odt    ← файл для подання
  Kuzhii_SMICS2026_abstract.pdf    рендер для перевірки обсягу та вигляду
template/
  smics2026_abstract_template.odt  офіційний CEURART ODT-шаблон конференції (не змінювати)
scripts/
  build_odt.py                     abstract.md → ODT на базі шаблону + PDF + контроль сторінок
  check_compliance.py              перевірка вимог конференції (14 перевірок)
review/
  conference_requirements.md       вимоги SMICS-2026, зафіксовані з сайту 23.08.2026
  submission_checklist.md          чекліст подання
```

## Збірка

```bash
python3 scripts/build_odt.py        # ODT + PDF, падає якщо обсяг вийшов за 3–5 сторінок
python3 scripts/check_compliance.py # обсяг, A4, шрифти, мова, розділи, цитування, самоцитування
```

Правити текст **тільки** в `paper/abstract.md` і перезбирати. `build_odt.py` бере з шаблону геометрію
сторінки, стилі абзаців і оголошення шрифтів Libertinus без змін — підмінюється лише вміст
(титул, автори, афіліація, анотація, ключові слова, зноска з e-mail/ORCID/CC, тіло, література).

Локальні залежності (вже встановлені): LibreOffice (`/Applications/LibreOffice.app`), шрифти Libertinus
у `~/Library/Fonts`, `poppler` (`pdfinfo`, `pdftoppm`, `pdffonts`) для перевірок.

### Синтаксис `abstract.md`

- front matter між `---`: `title`, `authors` (`^1` — надрядковий індекс афіліації), `affiliation1`,
  `event`, `corresponding`, `emails`, `orcids`, `abstract`, `keywords`;
- `## Заголовок` → Heading 1 (нумерується автоматично), `### ` → Heading 2;
- `Table [32,14,14,20,20]: підпис` перед markdown-таблицею — числа задають ширини колонок у частках;
- `![підпис](figures/x.png){4.5}` — фігура, `{}` задає ширину в дюймах (за замовчуванням 5.0);
- `**жирний**`, `*курсив*`, `` `код` `` (курсивом), `^-4` — надрядковий; `>=`/`<=` → ≥/≤, `"` → “типографські лапки”.

## Подання

1. Надіслати `paper/Kuzhii_SMICS2026_abstract.odt` (+ PDF) на **smics@lnu.edu.ua**, вказавши TRACK 2.
2. Заповнити реєстраційну форму: https://forms.gle/wxu2zhuXg4vcPUCk8
3. **Дедлайн реєстрації — 1 вересня 2026.** Прийняття — 10.09, запрошення — 15.09.

Воркшопи CEUR-WS (AIC/CDS) не використовуємо: там >9 сторінок і вимога ≥5 праць першого автора в DBLP.
