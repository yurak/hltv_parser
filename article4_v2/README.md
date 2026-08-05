# Стаття 4 (подання в Дніпро) — Поведінкові шаблони у фінансових онлайн-сервісах (антифрод)

**Четверта стаття** серійної публікаційної лінії «Ідентифікація шаблонів поведінки користувачів
онлайн-сервісів». Відтворюваний робочий процес для статті про ідентифікацію поведінкових шаблонів
карткових транзакцій на основі інженерії ознак та аналізу розділюваності у просторі ознак.

Цільове видання: **№47 «Information Technology: Computer Science, Software Engineering and Cyber
Security» (НТУ «Дніпровська політехніка»)**, категорія «Б», 4 випуски/рік.
**Дедлайн відсутній** — роллінгове приймання через OJS, швидке рецензування (~5 днів до першого
рішення, ~20 днів до фінального). Повні вимоги — `paper/journal_requirements.md`.

> Архітектуру конвеєра описано в `research_article_claude_code_architecture.md`.

## Основні етапи

1. Витяг вимог журналу (`/journal-requirements`) → `paper/journal_requirements.md`
2. Інспекція даних та план аналізу (`/analysis-plan`) → `paper/outline.md`
3. Відтворювані скрипти аналізу (`/analyze-data`) → `scripts/analyze.py`
4. Таблиці та фігури (`/build-figures`) → `outputs/`
5. Чернетка рукопису (`/draft-paper`) → `paper/manuscript.md`
6. Незалежна рецензія (`/reviewer`) → `review/`
7. Ревізії та revision log (`/revise`)
8. Експорт DOCX (`/export-docx`) → `paper/manuscript.docx`

## Дані

- Основа: `data/raw/df.csv` — Predict Chargeback Frauds (Kaggle, dmirandaalves, 2019),
  11 127 транзакцій, травень 2015, частка шахрайства 5,14 %.
- Поля: `Card Number`, `Date`, `Amount`, `CBK` (Yes/No).

## Ключове правило

Не писати результати в рукописі, доки не існує відповідних вихідних артефактів у `outputs/`.
Усі числа статті відтворюються запуском `python scripts/analyze.py`.
