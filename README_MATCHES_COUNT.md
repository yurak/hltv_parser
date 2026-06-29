# Додавання кількості матчів до CSV

Скрипт `add_matches_count.py` додає колонку `matches_played` до існуючого файлу `hltv_combined_cs2_csgo.csv`.

## Як використовувати

```bash
python3 add_matches_count.py
```

Скрипт:
1. Читає `hltv_combined_cs2_csgo.csv`
2. Для кожного запису (гравець + версія гри) парсить HLTV matches page
3. Витягує загальну кількість матчів з патерну "X of Y"
4. Зберігає результат у `hltv_combined_cs2_csgo_with_matches.csv`

## Параметри

Ви можете змінити вхідний та вихідний файли:

```python
from add_matches_count import add_matches_count

add_matches_count(
    csv_file='your_input.csv',
    output_file='your_output.csv'
)
```

## Час виконання

- Для кожного запису потрібно ~10-12 секунд (затримка для Cloudflare)
- Для 364 записів (183 гравців × 2 версії гри) = ~60-70 хвилин
- Можна зупинити і продовжити - скрипт пропускає записи які вже мають `matches_played`

## Формат даних

Додається колонка:
- `matches_played` (int) - загальна кількість матчів для даної версії гри

Приклад:
```
player_name,game_version,matches_played
s1mple,cs2,126
s1mple,csgo,1842
niko,cs2,245
niko,csgo,1523
```

## Примітки

- Скрипт використовує Selenium з headless Chrome
- Потрібна затримка 10 сек для обходу Cloudflare
- Якщо matches count не знайдено, значення залишається None/null
