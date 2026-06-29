"""
=============================================================================
VERSION INVARIANCE ANALYSIS - ПОКРОКОВЕ ПОЯСНЕННЯ
=============================================================================

Мета: Перевірити чи ознака залежить від версії гри (CS2 vs CSGO)
Метод: Mann-Whitney U тест + Cohen's d (розмір ефекту)

Питання: Чи kills_per_round різний у CS2 та CSGO?
"""

import pandas as pd
import numpy as np
from scipy import stats

# Завантажуємо дані
cs2 = pd.read_csv('/Users/yuriikuzhii/projects/hltv_parser/map_stats_cs2.csv')
csgo = pd.read_csv('/Users/yuriikuzhii/projects/hltv_parser/map_stats_csgo.csv')

print("=" * 70)
print("VERSION INVARIANCE: Чи залежить ознака від версії гри?")
print("=" * 70)

# Вибираємо 5 гравців з кожної версії для прикладу
players_cs2 = ['kscerato', 's1mple', 'NiKo', 'ZywOo', 'donk']
players_csgo = ['niko', 'device', 's1mple', 'ZywOo', 'electronic']

print(f"\nПриклад гравців CS2: {players_cs2}")
print(f"Приклад гравців CSGO: {players_csgo}")

feature = 'kills_per_round'
print(f"\nОзнака для аналізу: {feature}")

# =============================================================================
# КРОК 1: Описова статистика
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 1: Описова статистика по версіях")
print("=" * 70)

cs2_data = cs2[feature].dropna()
csgo_data = csgo[feature].dropna()

print(f"\nCS2:")
print(f"  N = {len(cs2_data)} спостережень")
print(f"  Mean = {cs2_data.mean():.4f}")
print(f"  Std = {cs2_data.std():.4f}")
print(f"  Median = {cs2_data.median():.4f}")

print(f"\nCSGO:")
print(f"  N = {len(csgo_data)} спостережень")
print(f"  Mean = {csgo_data.mean():.4f}")
print(f"  Std = {csgo_data.std():.4f}")
print(f"  Median = {csgo_data.median():.4f}")

print(f"\nРізниця середніх: {cs2_data.mean() - csgo_data.mean():.4f}")

# =============================================================================
# КРОК 2: Mann-Whitney U тест
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 2: Mann-Whitney U тест (непараметричний)")
print("=" * 70)

print("""
Mann-Whitney U тест - непараметрична альтернатива t-тесту.
Не вимагає нормального розподілу даних.

Гіпотези:
  H0: Розподіли CS2 і CSGO однакові
  H1: Розподіли різні

Як працює:
  1. Об'єднуємо всі значення і ранжуємо їх (1, 2, 3, ...)
  2. Рахуємо суму рангів для кожної групи
  3. U-статистика показує скільки разів значення однієї групи
     більше за значення іншої групи
""")

stat, p_value = stats.mannwhitneyu(cs2_data, csgo_data, alternative='two-sided')

print(f"Результати Mann-Whitney U:")
print(f"  U-statistic = {stat:.2f}")
print(f"  p-value = {p_value:.6f}")
print(f"  Висновок: {'Значуща різниця (p < 0.05)' if p_value < 0.05 else 'Немає значущої різниці'}")

# =============================================================================
# КРОК 3: Cohen's d (розмір ефекту)
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 3: Cohen's d - розмір ефекту")
print("=" * 70)

print("""
Cohen's d показує різницю між групами у стандартних відхиленнях.

Формула:
  d = |mean1 - mean2| / pooled_std

де pooled_std = sqrt((std1² + std2²) / 2)

Інтерпретація (Cohen, 1988):
  d < 0.2  - немає/мізерний ефект
  d ≈ 0.2  - малий ефект
  d ≈ 0.5  - середній ефект
  d ≈ 0.8  - великий ефект
  d > 1.0  - дуже великий ефект
""")

# Обчислюємо вручну
mean_cs2 = cs2_data.mean()
mean_csgo = csgo_data.mean()
std_cs2 = cs2_data.std()
std_csgo = csgo_data.std()

print(f"Крок 3.1: Обчислюємо середні")
print(f"  mean_CS2 = {mean_cs2:.4f}")
print(f"  mean_CSGO = {mean_csgo:.4f}")
print(f"  |mean_CS2 - mean_CSGO| = {abs(mean_cs2 - mean_csgo):.4f}")

print(f"\nКрок 3.2: Обчислюємо pooled standard deviation")
print(f"  std_CS2 = {std_cs2:.4f}")
print(f"  std_CSGO = {std_csgo:.4f}")
pooled_std = np.sqrt((std_cs2**2 + std_csgo**2) / 2)
print(f"  pooled_std = sqrt(({std_cs2:.4f}² + {std_csgo:.4f}²) / 2) = {pooled_std:.4f}")

print(f"\nКрок 3.3: Обчислюємо Cohen's d")
cohens_d = abs(mean_cs2 - mean_csgo) / pooled_std
print(f"  d = |{mean_cs2:.4f} - {mean_csgo:.4f}| / {pooled_std:.4f}")
print(f"{'=' * 40}")
print(f"  Cohen's d = {cohens_d:.4f}")
print(f"{'=' * 40}")

print(f"\nІнтерпретація:")
if cohens_d < 0.2:
    print(f"  d = {cohens_d:.4f} < 0.2 → МІЗЕРНИЙ ЕФЕКТ (інваріантна)")
elif cohens_d < 0.5:
    print(f"  d = {cohens_d:.4f} < 0.5 → МАЛИЙ ЕФЕКТ (інваріантна)")
elif cohens_d < 0.8:
    print(f"  d = {cohens_d:.4f} < 0.8 → СЕРЕДНІЙ ЕФЕКТ")
else:
    print(f"  d = {cohens_d:.4f} ≥ 0.8 → ВЕЛИКИЙ ЕФЕКТ (варіантна)")

# =============================================================================
# КРОК 4: Приклад для конкретних гравців
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 4: Приклад для конкретних гравців")
print("=" * 70)

print("\nCS2 гравці - kills_per_round:")
for player in players_cs2:
    player_data = cs2[cs2['player_name'].str.lower() == player.lower()][feature]
    if len(player_data) > 0:
        print(f"  {player}: mean = {player_data.mean():.3f}, n = {len(player_data)}")

print("\nCSGO гравці - kills_per_round:")
for player in players_csgo:
    player_data = csgo[csgo['player_name'].str.lower() == player.lower()][feature]
    if len(player_data) > 0:
        print(f"  {player}: mean = {player_data.mean():.3f}, n = {len(player_data)}")

# =============================================================================
# КРОК 5: Порівняння кількох ознак
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 5: Порівняння кількох ознак")
print("=" * 70)

features_to_test = ['kills_per_round', 'damage_per_round', 'rating_3.0',
                    'opening_kills_per_round', 'utility_damage_per_round',
                    'flashes_thrown_per_round']

results = []
for feat in features_to_test:
    cs2_vals = cs2[feat].dropna()
    csgo_vals = csgo[feat].dropna()

    if len(cs2_vals) < 10 or len(csgo_vals) < 10:
        continue

    stat, p_value = stats.mannwhitneyu(cs2_vals, csgo_vals, alternative='two-sided')

    pooled_std = np.sqrt((cs2_vals.std()**2 + csgo_vals.std()**2) / 2)
    cohens_d = abs(cs2_vals.mean() - csgo_vals.mean()) / pooled_std if pooled_std > 0 else 0

    results.append({
        'feature': feat,
        'cs2_mean': cs2_vals.mean(),
        'csgo_mean': csgo_vals.mean(),
        'cohens_d': cohens_d,
        'p_value': p_value,
        'invariant': cohens_d < 0.5
    })

print(f"\n{'Feature':<28} {'CS2':<8} {'CSGO':<8} {'d':<8} {'Інваріантна?'}")
print("-" * 65)
for r in results:
    status = "✓ ТАК" if r['invariant'] else "✗ НІ"
    print(f"{r['feature']:<28} {r['cs2_mean']:<8.3f} {r['csgo_mean']:<8.3f} {r['cohens_d']:<8.3f} {status}")

print("\n" + "=" * 70)
print("ВИСНОВОК")
print("=" * 70)
print("""
Ознака вважається VERSION-INVARIANT якщо Cohen's d < 0.5

Це означає, що різниця між CS2 та CSGO менше половини
стандартного відхилення - тобто розподіли суттєво перекриваються.
""")
