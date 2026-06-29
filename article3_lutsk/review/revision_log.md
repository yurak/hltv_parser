# Revision Log

| Дата | Issue | Дія | Файли | Статус |
|------|-------|-----|-------|--------|
| 2026-06-29 | Аудит article3 виявив дефект типу даних і суперечливе визначення інваріантності | Зафіксовано в outputs/logs/article3_audit.md; план v2 враховує фікси | analysis_plan.md, CLAUDE.md | open → буде усунено при перерахунку |
| 2026-06-29 | Проблема 1 (тихе випадання ознак) | Перераховано на _clean.csv + coercion: 46 ознак замість 36 | scripts/clean_data.py, scripts/analyze.py, outputs/tables/* | ✅ closed |
| 2026-06-29 | Проблема 2 (суперечливе визначення інваріантності) | Інваріантність лише за розміром ефекту; фігури кодують тим самим критерієм | scripts/analyze.py, scripts/build_figures.py | ✅ closed |
| 2026-06-29 | Конфаунд версії в map-ANOVA | Додано sensitivity-check по версіях (71.7% cs2 / 76.1% csgo vs 76.1% pooled) | outputs/tables/map_invariance_by_version.csv | ✅ closed |
| 2026-06-29 | Рецензія R1: refs [1][2][3] порожні TODO | Замінено на реальні джерела (Bishop, Guyon&Elisseeff, Quiñonero-Candela); esports-джерело лишено як примітку | manuscript_revised.md | ✅ closed |
| 2026-06-29 | R1: анотації < 200 слів (укр 154 / англ 172) | Розширено до 195 (укр) / 222 (англ) | manuscript_revised.md | ✅ closed |
| 2026-06-29 | R1: причинні речення в Results | Перенесено в Discussion; прибрано інтерпретації з §3.1–3.3 | manuscript_revised.md | ✅ closed |
| 2026-06-29 | R1: Methods не пояснює змінне n | Додано абзац про попарне видалення й залежність n від метрики | manuscript_revised.md | ✅ closed |
| 2026-06-29 | R1: Mann-Whitney + параметричний d; парний d поріг | Додано пояснювальні речення в §2.3 | manuscript_revised.md | ✅ closed |
| 2026-06-29 | R1: стабільність набору в sensitivity | Додано: усі 33 CS2-map-інв. ⊂ CSGO; +2 в CSGO | manuscript_revised.md, обчислено | ✅ closed |
| 2026-06-29 | R1: ORCID плейсхолдер; APC; Word-шаблон | Позначено як невирішене для авторів/редакції | manuscript_revised.md, supervisor_summary.md | ⚠ для користувача |
