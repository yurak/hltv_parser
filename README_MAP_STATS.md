# Парсинг статистики по картах

Скрипт `parse_by_maps.py` витягує статистику гравців для кожної карти окремо.

## Карти CS (8 шт)

- de_train
- de_nuke
- de_inferno
- de_mirage
- de_dust2
- de_vertigo
- de_ancient
- de_anubis

## Використання

### Тільки CS2
```bash
python3 parse_by_maps.py cs2
```
Результат: `map_stats_cs2.csv`

### Тільки CS:GO
```bash
python3 parse_by_maps.py csgo
```
Результат: `map_stats_csgo.csv`

### Обидві версії
```bash
python3 parse_by_maps.py both
```
Результат: `map_stats_cs2.csv` + `map_stats_csgo.csv`

## Формат даних

Кожен запис містить:
- Всі стандартні метрики (rating, kills_per_round, etc.)
- **map** - назва карти (de_train, de_nuke, etc.)
- **game_version** - версія гри (cs2/csgo)
- **player_name** - ім'я гравця

Приклад:
```csv
player_name,game_version,map,rating_2.0,kills_per_round,...
s1mple,cs2,de_mirage,1.25,0.85,...
s1mple,cs2,de_nuke,1.18,0.78,...
s1mple,cs2,de_inferno,1.22,0.82,...
```

## Кількість записів

- **Гравців:** 182
- **Карт:** 8
- **CS2:** 182 × 8 = 1,456 записів
- **CS:GO:** 182 × 8 = 1,456 записів
- **Разом:** 2,912 записів

## Час виконання

- ~10-15 хвилин для CS2 (1,456 записів)
- ~10-15 хвилин для CS:GO (1,456 записів)
- ~20-30 хвилин для обох версій

## Запуск в фоні

```bash
# CS2 тільки
python3 parse_by_maps.py cs2 > map_stats_cs2.log 2>&1 &

# Обидві версії
python3 parse_by_maps.py both > map_stats_all.log 2>&1 &

# Перевірити прогрес
tail -f map_stats_cs2.log
```

## Відмінності від основного парсера

| Параметр | hltv_combined_cs2_csgo.csv | map_stats_*.csv |
|----------|---------------------------|-----------------|
| Карта | `all` (всі карти разом) | Окремо для кожної |
| Записів на гравця | 2 (cs2 + csgo) | 16 (8 карт × 2 версії) |
| Розмір даних | 364 записи | 2,912 записів |
