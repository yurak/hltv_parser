"""
=============================================================================
MAP INVARIANCE ANALYSIS - ПОКРОКОВЕ ПОЯСНЕННЯ
=============================================================================

Мета: Перевірити чи ознака залежить від карти
Метод: ANOVA (Analysis of Variance) + Eta-squared (розмір ефекту)

Питання: Чи kills_per_round різний на різних картах?
"""

import pandas as pd
import numpy as np
from scipy import stats

# Завантажуємо дані
cs2 = pd.read_csv('/Users/yuriikuzhii/projects/hltv_parser/map_stats_cs2.csv')
csgo = pd.read_csv('/Users/yuriikuzhii/projects/hltv_parser/map_stats_csgo.csv')
df = pd.concat([cs2, csgo], ignore_index=True)

# Вибираємо 5 гравців для прикладу
players_cs2 = ['kscerato', 's1mple', 'NiKo', 'ZywOo', 'donk']
players_csgo = ['niko', 'device', 's1mple', 'ZywOo', 'electronic']

print("=" * 70)
print("MAP INVARIANCE: Чи залежить ознака від карти?")
print("=" * 70)

# Беремо одну ознаку для прикладу
feature = 'kills_per_round'

print(f"\nОзнака: {feature}")
print(f"Карти в даних: {df['map'].unique()[:7]}")

# =============================================================================
# КРОК 1: Групуємо дані по картах
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 1: Групування даних по картах")
print("=" * 70)

maps = ['de_mirage', 'de_inferno', 'de_nuke', 'de_dust2', 'de_anubis']
groups = {}

for m in maps:
    map_data = df[df['map'] == m][feature].dropna()
    groups[m] = map_data
    print(f"\n{m}:")
    print(f"  N = {len(map_data)} спостережень")
    print(f"  Mean = {map_data.mean():.4f}")
    print(f"  Std = {map_data.std():.4f}")

# =============================================================================
# КРОК 2: ANOVA F-тест
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 2: ANOVA F-тест")
print("=" * 70)

print("""
ANOVA перевіряє гіпотезу:
  H0: Середні значення однакові для всіх карт (μ1 = μ2 = μ3 = ...)
  H1: Принаймні одне середнє відрізняється

Формула F-статистики:
  F = (Between-group variance) / (Within-group variance)
  F = MSB / MSW

де:
  MSB = SS_between / df_between  (variance між групами)
  MSW = SS_within / df_within    (variance всередині груп)
""")

# Виконуємо ANOVA
group_list = [groups[m] for m in maps if len(groups[m]) > 1]
f_stat, p_value = stats.f_oneway(*group_list)

print(f"Результати ANOVA:")
print(f"  F-statistic = {f_stat:.4f}")
print(f"  p-value = {p_value:.6f}")
print(f"  Висновок: {'Значуща різниця (p < 0.05)' if p_value < 0.05 else 'Немає значущої різниці'}")

# =============================================================================
# КРОК 3: Eta-squared (розмір ефекту)
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 3: Eta-squared (η²) - розмір ефекту")
print("=" * 70)

print("""
Eta-squared показує ЧАСТКУ дисперсії, яку пояснює групування (карта).

Формула:
  η² = SS_between / SS_total

де:
  SS_between = Σ n_i * (mean_i - grand_mean)²  (варіація між групами)
  SS_total = Σ (x_ij - grand_mean)²            (загальна варіація)

Інтерпретація (Cohen, 1988):
  η² < 0.01  - немає ефекту
  η² ≈ 0.01  - малий ефект
  η² ≈ 0.06  - середній ефект
  η² ≈ 0.14  - великий ефект
""")

# Обчислюємо вручну
all_data = pd.concat([groups[m] for m in maps])
grand_mean = all_data.mean()

print(f"Grand mean (загальне середнє) = {grand_mean:.4f}")

# SS_between
ss_between = sum(len(groups[m]) * (groups[m].mean() - grand_mean)**2 for m in maps)
print(f"\nSS_between (варіація між картами):")
for m in maps:
    contribution = len(groups[m]) * (groups[m].mean() - grand_mean)**2
    print(f"  {m}: n={len(groups[m])}, mean={groups[m].mean():.4f}, "
          f"(mean - grand_mean)² * n = {contribution:.4f}")
print(f"  TOTAL SS_between = {ss_between:.4f}")

# SS_total
ss_total = sum((all_data - grand_mean)**2)
print(f"\nSS_total (загальна варіація) = {ss_total:.4f}")

# Eta-squared
eta_squared = ss_between / ss_total
print(f"\n{'=' * 40}")
print(f"η² = SS_between / SS_total = {ss_between:.4f} / {ss_total:.4f} = {eta_squared:.4f}")
print(f"{'=' * 40}")

print(f"\nІнтерпретація:")
if eta_squared < 0.01:
    print(f"  η² = {eta_squared:.4f} < 0.01 → НЕМАЄ ЕФЕКТУ")
    print(f"  Карта пояснює {eta_squared*100:.2f}% варіації")
elif eta_squared < 0.06:
    print(f"  η² = {eta_squared:.4f} < 0.06 → МАЛИЙ ЕФЕКТ (інваріантна)")
    print(f"  Карта пояснює {eta_squared*100:.2f}% варіації")
elif eta_squared < 0.14:
    print(f"  η² = {eta_squared:.4f} < 0.14 → СЕРЕДНІЙ ЕФЕКТ")
    print(f"  Карта пояснює {eta_squared*100:.2f}% варіації")
else:
    print(f"  η² = {eta_squared:.4f} ≥ 0.14 → ВЕЛИКИЙ ЕФЕКТ (варіантна)")
    print(f"  Карта пояснює {eta_squared*100:.2f}% варіації")

# =============================================================================
# КРОК 4: Порівняння кількох ознак
# =============================================================================
print("\n" + "=" * 70)
print("КРОК 4: Порівняння кількох ознак")
print("=" * 70)

features_to_test = ['kills_per_round', 'damage_per_round', 'rating_3.0',
                    'opening_kills_per_round', 'utility_damage_per_round']

results = []
for feat in features_to_test:
    groups_feat = [df[df['map'] == m][feat].dropna() for m in maps]
    groups_feat = [g for g in groups_feat if len(g) > 1]

    if len(groups_feat) < 2:
        continue

    f_stat, p_value = stats.f_oneway(*groups_feat)

    all_data = pd.concat(groups_feat)
    grand_mean = all_data.mean()
    ss_between = sum(len(g) * (g.mean() - grand_mean)**2 for g in groups_feat)
    ss_total = sum((all_data - grand_mean)**2)
    eta_sq = ss_between / ss_total if ss_total > 0 else 0

    results.append({
        'feature': feat,
        'eta_squared': eta_sq,
        'p_value': p_value,
        'invariant': eta_sq < 0.06
    })

print(f"\n{'Feature':<30} {'η²':<10} {'p-value':<12} {'Інваріантна?'}")
print("-" * 65)
for r in results:
    status = "✓ ТАК" if r['invariant'] else "✗ НІ"
    print(f"{r['feature']:<30} {r['eta_squared']:<10.4f} {r['p_value']:<12.6f} {status}")

print("\n" + "=" * 70)
print("ВИСНОВОК")
print("=" * 70)
print("""
Ознака вважається MAP-INVARIANT якщо η² < 0.06

Це означає, що карта пояснює менше 6% варіації ознаки,
тобто значення ознаки приблизно однакові на різних картах.
""")
