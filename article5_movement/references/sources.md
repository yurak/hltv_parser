# Список джерел статті 5 — канонічний, поповнюваний

Єдине місце, де живе бібліографія. Поповнювати тут, не в рукописі.

**Статус перевірки:**
- `V` — бібліографічні дані й числа витягнуті з самого джерела, цитувати можна
- `S` — лише з пошукової видачі, **перед цитуванням звірити**
- `P` — за пейволом, не дістали

Нумерація попередня. ЕлІТ нумерує за порядком згадування — перенумерувати
скриптом після того, як текст буде написаний (`scripts/citation_map.py`).

---

## A. Наші попередні роботи

| # | Статус | Джерело | Чим корисна статті 5 |
|---|---|---|---|
| A1 | V | Кужій Ю. І., Фургала Ю. М. **The Anticheat Development in the Counter-Strike Main Series** // Електроніка та інформаційні технології. 2024. Вип. 26. С. 88–97. DOI: 10.30970/eli.26.8 | Прямий попередник за мотивацією: античіт у CS. Обґрунтовує прикладну рамку статті 5 |
| A2 | V | Kuzhii Yu. I., Furgala Yu. M. **Feature engineering for role assessment in Counter-Strike 2** // Electronics and Information Technologies. 2025. Vol. 32. P. 121–130. DOI: 10.30970/eli.32.8 | Найближча наша робота: ті самі демки CS2, структурування ознак у сімейства. Стаття 5 успадковує підхід і переносить його з ролі на ідентичність |
| A3 | V | Кужій Ю. І., Фургала Ю. М. **Ідентифікація контекстно-інваріантних метрик майстерності гравця у кіберспорті на основі аналізу розмірів ефекту** (стаття 3, Вісник ЛНУ №69, у підготовці) | Інваріантність ознак до контексту — те саме питання, що наша H2 |
| A4 | V | Kuzhii Yu. I., Furgala Yu. M. **Identification of user behavioral patterns in online financial services via feature engineering** (стаття 4, у підготовці) | Нерівномірність розділювальної сили між сімействами ознак як загальна властивість поведінкових даних — наш T5/T11 це підтверджує на третьому домені |

**Важливо для самоцитування:** A2 і A4 разом дають тезу, що розподіл
прогностичної сили між сімействами ознак нерівномірний і доменно-залежний.
Стаття 5 додає третій випадок (локомоція проти бою) і робить із цього
методологічне узагальнення, а не повтор.

---

## B. Прямі попередники — ідентифікація гравців

| # | Статус | Джерело | Ключові числа |
|---|---|---|---|
| B1 | V | Zhang X. **Account Consistency from Gameplay Traces: Same-Player Verification in Counter-Strike 2.** arXiv:2608.24893v2, 27.08.2026 (v1 — «Same-Player Verification for Account Consistency in Counter-Strike 2») | 3570+539+513 демок; AUC 0.926/0.956; приціл −0.087 при вилученні; K=10 → 0.982; про-плече з HLTV |
| B2 | V | Zimmer F., Irvan M., Perera M. N. S., Tamponi R., Kobayashi R., Shigetomi Yamaguchi R. **Player Behavior Analysis for Predicting Player Identity Within Pairs in Esports Tournaments: A Case Study of Counter-Strike Using Binary Random Forest Classifier.** HICSS 2025. DOI: 10.24251/HICSS.2025.513 | 119 матчів CS:GO, точність до 87% на розрізненні в парі |
| B3 | P | Zimmer F. et al. **Fair Play and Identity: In-Game Behavioral Biometrics for Player Identification in Competitive Online Games.** IEEE CoG 2025 | IEEE Xplore 403. Дістати через бібліотеку ЛНУ |
| B4 | V | Singh I., Kaur G., Atwal U. P. S., Singh G., Singh G., Singh M. **BEACON: A Multimodal Dataset for Learning Behavioral Fingerprints from Gameplay Data.** arXiv:2605.10867v2, 2026 | Valorant, 28 гравців, 79 сесій; Var-CNN 70.82%, EER 4.31% при 60 с; миша 63.16% проти клавіатури 36.23% |
| B5 | P | **Sequence Length Aggregation and Behavioral Biometrics: A Case Study in Professional Player Authentication via Tree-Based Classification.** Springer. DOI: 10.1007/978-981-95-4674-9_27 | Пейвол. Близьке до нашої P5 (probe-length) |
| B6 | S | Kaminsky R., Enev M., Andersen E. **Identifying Game Players with Mouse Biometrics** | **Конфлікт авторства** у видачі: подекуди приписують Jorgensen & Yu. Розвʼязати перед цитуванням |
| B7 | P | **User identification based on game-play activity patterns.** ACM SIGCOMM NetGames 2007. DOI: 10.1145/1326257.1326259 | ACM 403 |

---

## C. Ідентифікація за рухом поза іграми — найближчий родич нашої осі

| # | Статус | Джерело | Чому критично |
|---|---|---|---|
| C1 | V | Nair V., Guo W., Mattern J., Wang R., O'Brien J. F., Rosenberg L., Song D. **Unique Identification of 50,000+ Virtual Reality Users from Head & Hand Motion Data.** 32nd USENIX Security Symposium, 2023, pp. 895–910. arXiv:2302.08927 | **Концептуальний прецедент нашої осі:** ідентифікація за чистим рухом (голова + руки), без прицілювання. 55 541 користувач, 94.33% зі 100 с, 73.20% з 10 с |
| C2 | S | **Understanding User Identification in Virtual Reality Through Behavioral Biometrics and the Effect of Body Normalization.** CHI 2021. DOI: 10.1145/3411764.3445528 | Нормалізація тіла — аналог нашої нормалізації в межах лобі |
| C3 | S | **BioMove: Biometric User Identification from Human Kinesiological Movements for Virtual Reality Systems.** Sensors, 2020 | Кінезіологічний рух як біометрія |
| C4 | S | **Emerging trends in gait recognition based on deep learning: a survey** (PMC11323174) | Огляд розпізнавання за ходою. GaitNet 99.7% точності, EER 0.31–0.67%; носимі сенсори EER 0.17–2.27% |

**Що з C4 треба сказати чесно:** розпізнавання за ходою з виділених сенсорів
дає EER 0.2–0.7%, тобто на порядок краще за наші 9.76%. Різниця в каналі:
там спеціалізований сенсор із високою частотою, у нас — серверна демка 64 тіки.
Це не слабкість роботи, а межа носія, і її треба назвати першою.

---

## D. Класика поведінкової біометрії

| # | Статус | Джерело | Роль |
|---|---|---|---|
| D1 | V | Killourhy K. S., Maxion R. A. **Comparing Anomaly-Detection Algorithms for Keystroke Dynamics.** IEEE/IFIP DSN 2009, Lisbon, pp. 125–134 | Еталонний бенчмарк: 51 суб'єкт, 14 алгоритмів, **найкращі EER 9.6–10.2%**. Наш EER 0.0976 лягає рівно в цей діапазон |
| D2 | V | Ahmed A. E., Traore I. **A New Biometric Technology Based on Mouse Dynamics.** IEEE TDSC, 2007, 4(3), 165–179 | Засаднича робота з динаміки миші |
| D3 | S | **Mouse Dynamics Behavioral Biometrics: A Survey.** arXiv:2208.09061 | Оглядове джерело для вступу |

---

## E. Методологія: стабільність ознак і метрики

| # | Статус | Джерело | Що обґрунтовує |
|---|---|---|---|
| E1 | V | Friedman L., Nixon M. S., Komogortsev O. V. **Method to assess the temporal persistence of potential biometric features: Application to oculomotor, gait, face and brain structure databases.** PLOS ONE, 2017, 12(6). DOI: 10.1371/journal.pone.0178501 | **Обґрунтування нашого ICC.** Відбір ознак за високим ICC дав кращий Rank-1 і EER у 12 з 14 баз (p = 0.0065); зростання ICC 0.5→0.75 дає ~28.8 пункту приросту |
| E2 | S | **Why Temporal Persistence of Biometric Features, as Assessed by the ICC, Is So Valuable for Classification Performance.** Sensors, 2020, 20(16), 4555. arXiv:2001.09100 | Продовження E1, механізм ефекту |
| E3 | S | Метрики open-set: DIR@FAR, OSCR. Watchlist Challenge (arXiv:2409.07220); Toward Open-Set Face Recognition (arXiv:1705.01567); VoxWatch (arXiv:2307.00169) | Апарат для нашого P3 (T8/F7) |

---

## F. Античіт і смурфи — для ітерації 2

| # | Статус | Джерело |
|---|---|---|
| F1 | S | **AntiCheatPT: A Transformer-Based Approach to Cheat Detection in Competitive Computer Games.** CS2, точність 89.17%, AUC 93.36% |
| F2 | S | **GUARD: Enabling fair gaming through the gameplay analysis using ML methods and expert knowledge.** Expert Systems with Applications |
| F3 | S | Riot Games. **VALORANT Systems Health Series — Smurf Detection.** Не наукове джерело; показує промислову постановку: смурфа ставлять у правильний рейтинг, а не банять |

---

## G. Українськомовні джерела — для вимог ЕлІТ

| # | Статус | Джерело |
|---|---|---|
| G1 | S | **Ідентифікація користувачів на основі клавіатурного почерку.** КПІ, ela.kpi.ua/handle/123456789/25537 |
| G2 | S | **Сучасні методи біометричної ідентифікації.** КПІ, ela.kpi.ua |
| G3 | S | Захаров В. П., Рудешко В. І. **Біометричні технології.** ЛьвДУВС |
| G4 | S | **Поняття біометричних даних у законодавстві України та іноземних держав** — для розділу про етику й приватність |

Крім A1–A4, українськомовних джерел у списку **чотири, усі неперевірені**.
Якщо ЕлІТ вимагає частку вітчизняних джерел — це найслабше місце списку.

---

## H. Чого ще бракує

1. **Етика й приватність поведінкового трекінгу** — Zhang виносить це в окремий
   розділ обмежень; у нас реальні імена гравців, тож розділ обов'язковий.
   Знайдено лише G4, профільних робіт немає.
2. **Три джерела за пейволом** (B3, B5, B7) — дістати через бібліотеку ЛНУ.
3. **Конфлікт авторства B6** — розвʼязати.
4. **Верифікація 12 джерел зі статусом S.**
5. Gait recognition представлено одним оглядом (C4); якщо вісь статті —
   локомоція, потрібні первинні роботи, а не лише огляд.

---

## Як поповнювати

Додати рядок у відповідний розділ, проставити статус, коротко записати
**чим корисне саме нам**. Після правки рукопису прогнати `scripts/citation_map.py`: з
29.09.2026 він читає список літератури з самого рукопису й перевіряє порядок першої згадки,
синхронізувати нічого не треба.

---

## H. Методи (додано 29.09.2026 за рецензією v0.2)

Метадані звірено з Crossref API 29.09.2026 (`api.crossref.org/works/<DOI>`).

| # | Статус | Джерело | Де в статті |
|---|---|---|---|
| H1 | V | Fisher, R. A. (1936). The use of multiple measurements in taxonomic problems. *Annals of Eugenics, 7*(2), 179–188. DOI: 10.1111/j.1469-1809.1936.tb02137.x | LDA |
| H2 | V | Ledoit, O., & Wolf, M. (2004). A well-conditioned estimator for large-dimensional covariance matrices. *Journal of Multivariate Analysis, 88*(2), 365–411. DOI: 10.1016/S0047-259X(03)00096-4 | стиснення коваріації в LDA (sklearn `shrinkage="auto"`) |
| H3 | V | Breiman, L. (2001). Random forests. *Machine Learning, 45*(1), 5–32. DOI: 10.1023/A:1010933404324 | випадковий ліс |
| H4 | S | ISO/IEC 19795-1:2021. Information technology — Biometric performance testing and reporting — Part 1: Principles and framework. | EER/FAR/FRR. iso.org не відкрився (Cloudflare) — звірити вихідні дані |
| H5 | V | Efron, B. (1979). Bootstrap methods: Another look at the jackknife. *The Annals of Statistics, 7*(1), 1–26. DOI: 10.1214/aos/1176344552 | бутстреп. Crossref не віддає сторінки — 1–26 з пам'яті, звірити |
| H6 | V | Shrout, P. E., & Fleiss, J. L. (1979). Intraclass correlations: Uses in assessing rater reliability. *Psychological Bulletin, 86*(2), 420–428. DOI: 10.1037/0033-2909.86.2.420 | ICC(1) |
| H7 | V | Kruskal, W. H., & Wallis, W. A. (1952). Use of ranks in one-criterion variance analysis. *JASA, 47*(260), 583–621. DOI: 10.1080/01621459.1952.10483441 | критерій Краскела — Уолліса |
| H8 | V | Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: A practical and powerful approach to multiple testing. *JRSS B, 57*(1), 289–300. DOI: 10.1111/j.2517-6161.1995.tb02031.x | поправка БГ |

Також 29.09.2026: DOI D2 (Ahmed & Traore) = 10.1109/TDSC.2007.70207 (Crossref); C1 (Nair)
цитується за сторінкою USENIX https://www.usenix.org/conference/usenixsecurity23/presentation/nair-identification
(перевірено: сторінка існує, назва збігається). У рукопис v0.3 увійшли з розділу V: B3, B7,
C2, C3, D3, E2, E3b, F1, F2.
