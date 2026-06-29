"""
=============================================================================
SIDE INVARIANCE ANALYSIS - ПОКРОКОВЕ ПОЯСНЕННЯ
=============================================================================

Мета: Перевірити чи ознака залежить від сторони (CT vs T)
Метод: Paired t-test + Cohen's d для парних вибірок

Питання: Чи kills_per_round різний для CT та T сторони?

ВАЖЛИВО: Це ПАРНИЙ тест - порівнюємо того самого гравця на різних сторонах!
"""

import pandas as pd
import numpy as np
from scipy import stats

# Завантажуємо дані
cs2 = pd.read_csv('/Users/yuriikuzhii/projects/hltv_parser/map_stats_cs2.csv')
csgo = pd.read_csv('/Users/yuriikuzhii/projects/hltv_parser/map_stats_csgo.csv')
df = pd.concat([cs2, csgo], ignore_index=True)

print("=" * 70)
print("SIDE INVARIANCE: Чи залежить ознака від сторони (CT vs T)?")
print("=" * 70)

# Вибираємо гравців для прикладу
example_players = ['s1mple', 'ZywOo', 'NiKo', 'device', 'kscerato']

feature = 'kills_per_round'
ct_col = f'ct_{feature}'
t_col = f't_{feature}'

print(f"\nОзнака для аналізу: {feature}")
print(f"CT колонка: {ct_col}")
print(f"T колонка: {t_col}")

# =============================================================================
# КРОК 1: Структура даних (парні спостереження)
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 1: Парні спостереження")
print("=" * 70)

print("""
КЛЮЧОВА ІДЕЯ: Кожен рядок містить дані ОДНОГО гравця на ОДНІЙ карті.
У нас є ct_kills_per_round і t_kills_per_round для того самого гравця.

Це дозволяє використати ПАРНИЙ тест - порівнюємо гравця із самим собою!
Це контролює індивідуальні відмінності між гравцями.
""")

# Показуємо приклад для конкретних гравців
print("Приклад парних даних для гравців:")
print("-" * 60)

for player in example_players[:3]:
    player_data = df[df['player_name'].str.lower() == player.lower()][[ct_col, t_col, 'map']].dropna()
    if len(player_data) > 0:
        print(f"\n{player}:")
        print(f"  {'Map':<15} {'CT':<10} {'T':<10} {'Diff (CT-T)'}")
        for _, row in player_data.head(4).iterrows():
            diff = row[ct_col] - row[t_col]
            print(f"  {str(row['map']):<15} {row[ct_col]:<10.3f} {row[t_col]:<10.3f} {diff:+.3f}")

# =============================================================================
# КРОК 2: Описова статистика
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 2: Описова статистика")
print("=" * 70)

# Беремо тільки рядки де є обидва значення
valid_mask = df[ct_col].notna() & df[t_col].notna()
ct_data = df.loc[valid_mask, ct_col]
t_data = df.loc[valid_mask, t_col]
diff_data = ct_data - t_data

print(f"\nКількість парних спостережень: {len(ct_data)}")

print(f"\nCT сторона:")
print(f"  Mean = {ct_data.mean():.4f}")
print(f"  Std = {ct_data.std():.4f}")

print(f"\nT сторона:")
print(f"  Mean = {t_data.mean():.4f}")
print(f"  Std = {t_data.std():.4f}")

print(f"\nРізниця (CT - T):")
print(f"  Mean = {diff_data.mean():.4f}")
print(f"  Std = {diff_data.std():.4f}")

# =============================================================================
# КРОК 3: Paired t-test
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 3: Paired t-test (парний t-тест)")
print("=" * 70)

print("""
Paired t-test перевіряє чи середня РІЗНИЦЯ відрізняється від нуля.

Гіпотези:
  H0: mean(CT - T) = 0  (немає різниці між сторонами)
  H1: mean(CT - T) ≠ 0  (є різниця)

Формула t-статистики:
  t = mean(differences) / (std(differences) / sqrt(n))
  t = mean(CT - T) / SE

де SE = std(CT - T) / sqrt(n) - стандартна похибка середнього
""")

# Обчислюємо вручну
mean_diff = diff_data.mean()
std_diff = diff_data.std()
n = len(diff_data)
se = std_diff / np.sqrt(n)

print(f"Крок 3.1: Обчислюємо різниці для кожного спостереження")
print(f"  diff_i = CT_i - T_i")
print(f"  Приклад перших 5: {diff_data.head().values.round(3)}")

print(f"\nКрок 3.2: Статистики різниць")
print(f"  mean(diff) = {mean_diff:.4f}")
print(f"  std(diff) = {std_diff:.4f}")
print(f"  n = {n}")

print(f"\nКрок 3.3: Стандартна похибка")
print(f"  SE = std(diff) / sqrt(n) = {std_diff:.4f} / sqrt({n}) = {se:.6f}")

print(f"\nКрок 3.4: t-статистика")
t_manual = mean_diff / se
print(f"  t = mean(diff) / SE = {mean_diff:.4f} / {se:.6f} = {t_manual:.4f}")

# Перевіряємо scipy
t_stat, p_value = stats.ttest_rel(ct_data, t_data)
print(f"\nРезультати scipy.stats.ttest_rel:")
print(f"  t-statistic = {t_stat:.4f}")
print(f"  p-value = {p_value:.2e}")
print(f"  Висновок: {'Значуща різниця (p < 0.05)' if p_value < 0.05 else 'Немає значущої різниці'}")

# =============================================================================
# КРОК 4: Cohen's d для парних вибірок
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 4: Cohen's d для парних вибірок")
print("=" * 70)

print("""
Для ПАРНИХ вибірок Cohen's d обчислюється інакше!

Формула:
  d = |mean(differences)| / std(differences)
  d = |mean(CT - T)| / std(CT - T)

Це показує наскільки велика різниця відносно варіабельності різниць.

Інтерпретація (Cohen, 1988):
  d < 0.2  - немає/мізерний ефект
  d ≈ 0.2  - малий ефект
  d ≈ 0.5  - середній ефект  ← ПОРІГ ІНВАРІАНТНОСТІ
  d ≈ 0.8  - великий ефект
""")

print(f"Крок 4.1: Вже маємо статистики різниць")
print(f"  mean(CT - T) = {mean_diff:.4f}")
print(f"  std(CT - T) = {std_diff:.4f}")

print(f"\nКрок 4.2: Обчислюємо Cohen's d")
cohens_d = abs(mean_diff) / std_diff
print(f"  d = |{mean_diff:.4f}| / {std_diff:.4f}")
print(f"{'=' * 40}")
print(f"  Cohen's d = {cohens_d:.4f}")
print(f"{'=' * 40}")

print(f"\nІнтерпретація:")
if cohens_d < 0.2:
    print(f"  d = {cohens_d:.4f} < 0.2 → МІЗЕРНИЙ ЕФЕКТ (інваріантна)")
elif cohens_d < 0.5:
    print(f"  d = {cohens_d:.4f} < 0.5 → МАЛИЙ ЕФЕКТ (інваріантна)")
elif cohens_d < 0.8:
    print(f"  d = {cohens_d:.4f} < 0.8 → СЕРЕДНІЙ ЕФЕКТ (варіантна)")
else:
    print(f"  d = {cohens_d:.4f} ≥ 0.8 → ВЕЛИКИЙ ЕФЕКТ (варіантна)")

# =============================================================================
# КРОК 5: Порівняння кількох ознак
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 5: Порівняння кількох ознак")
print("=" * 70)

# Базові ознаки (без ct_/t_ префікса)
base_features = ['kills_per_round', 'damage_per_round', 'rating_3.0',
                 'opening_kills_per_round', 'utility_damage_per_round',
                 'assists_per_round', 'sniper_kills_per_round', 'trade_kills_per_round']

results = []
for feat in base_features:
    ct_col = f'ct_{feat}'
    t_col = f't_{feat}'

    if ct_col not in df.columns or t_col not in df.columns:
        continue

    valid = df[[ct_col, t_col]].dropna()
    if len(valid) < 10:
        continue

    ct_vals = valid[ct_col]
    t_vals = valid[t_col]
    diff = ct_vals - t_vals

    t_stat, p_value = stats.ttest_rel(ct_vals, t_vals)
    cohens_d = abs(diff.mean()) / diff.std() if diff.std() > 0 else 0

    results.append({
        'feature': feat,
        'ct_mean': ct_vals.mean(),
        't_mean': t_vals.mean(),
        'diff': diff.mean(),
        'cohens_d': cohens_d,
        'p_value': p_value,
        'invariant': cohens_d < 0.5
    })

print(f"\n{'Feature':<25} {'CT':<8} {'T':<8} {'Diff':<8} {'d':<8} {'Інвар?'}")
print("-" * 70)
for r in sorted(results, key=lambda x: x['cohens_d']):
    status = "✓ ТАК" if r['invariant'] else "✗ НІ"
    print(f"{r['feature']:<25} {r['ct_mean']:<8.3f} {r['t_mean']:<8.3f} "
          f"{r['diff']:<+8.3f} {r['cohens_d']:<8.3f} {status}")

# =============================================================================
# КРОК 6: Інтерпретація результатів
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 6: Інтерпретація")
print("=" * 70)

print("""
ЩО ОЗНАЧАЮТЬ РЕЗУЛЬТАТИ:

ІНВАРІАНТНІ ознаки (d < 0.5):
  - rating_3.0, opening_kills_per_round - приблизно однакові на обох сторонах
  - Це "чисті" показники майстерності гравця

ВАРІАНТНІ ознаки (d ≥ 0.5):
  - kills_per_round: CT вищий (CT більше кілів на раунд)
  - damage_per_round: CT вищий (CT наносить більше damage)
  - utility_damage_per_round: CT набагато вищий
  - sniper_kills_per_round: CT вищий (AWP на захисті ефективніший)
  - trade_kills_per_round: T вищий (T більше трейдить при вході на сайт)

Ці відмінності пояснюються РІЗНИМИ РОЛЯМИ сторін:
  - CT захищає → більше damage, utility, sniper kills
  - T атакує → більше trade kills, opening deaths
""")

print("\n" + "=" * 70)
print("ВИСНОВОК")
print("=" * 70)
print("""
Ознака вважається SIDE-INVARIANT якщо Cohen's d < 0.5 (для парних вибірок)

Це означає, що гравець показує приблизно однакові результати
незалежно від того, на якій стороні він грає.
""")
