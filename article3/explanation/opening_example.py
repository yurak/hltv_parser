"""
ПРОСТИЙ ПРИКЛАД: Аналіз ознаки "opening" на інваріантність
"""

import pandas as pd
import numpy as np
from scipy import stats

# Дані
cs2 = pd.read_csv('/Users/yuriikuzhii/projects/hltv_parser/map_stats_cs2.csv')
csgo = pd.read_csv('/Users/yuriikuzhii/projects/hltv_parser/map_stats_csgo.csv')
df = pd.concat([cs2, csgo], ignore_index=True)

feature = 'opening'

print("=" * 60)
print(f"АНАЛІЗ ОЗНАКИ: {feature}")
print("=" * 60)

# ============================================================
# 1. MAP INVARIANCE (ANOVA + eta-squared)
# ============================================================
print("\n1. MAP INVARIANCE")
print("-" * 40)

maps = ['de_mirage', 'de_inferno', 'de_nuke', 'de_dust2', 'de_anubis']
groups = [df[df['map'] == m][feature].dropna() for m in maps]

# ANOVA
f_stat, p_value = stats.f_oneway(*groups)

# Eta-squared
all_data = pd.concat(groups)
grand_mean = all_data.mean()
ss_between = sum(len(g) * (g.mean() - grand_mean)**2 for g in groups)
ss_total = sum((all_data - grand_mean)**2)
eta_sq = ss_between / ss_total

print(f"eta² = {eta_sq:.4f}")
print(f"Поріг: < 0.06")
print(f"Результат: {'ІНВАРІАНТНА' if eta_sq < 0.06 else 'ВАРІАНТНА'}")

# ============================================================
# 2. VERSION INVARIANCE (Mann-Whitney + Cohen's d)
# ============================================================
print("\n2. VERSION INVARIANCE (CS2 vs CSGO)")
print("-" * 40)

cs2_vals = cs2[feature].dropna()
csgo_vals = csgo[feature].dropna()

# Cohen's d
pooled_std = np.sqrt((cs2_vals.std()**2 + csgo_vals.std()**2) / 2)
cohens_d = abs(cs2_vals.mean() - csgo_vals.mean()) / pooled_std

print(f"CS2 mean = {cs2_vals.mean():.4f}")
print(f"CSGO mean = {csgo_vals.mean():.4f}")
print(f"Cohen's d = {cohens_d:.4f}")
print(f"Поріг: < 0.5")
print(f"Результат: {'ІНВАРІАНТНА' if cohens_d < 0.5 else 'ВАРІАНТНА'}")

# ============================================================
# 3. SIDE INVARIANCE (Paired t-test + Cohen's d)
# ============================================================
print("\n3. SIDE INVARIANCE (CT vs T)")
print("-" * 40)

ct_col = f'ct_{feature}'
t_col = f't_{feature}'

valid = df[[ct_col, t_col]].dropna()
ct_vals = valid[ct_col]
t_vals = valid[t_col]
diff = ct_vals - t_vals

# Cohen's d для парних вибірок
cohens_d_paired = abs(diff.mean()) / diff.std()

print(f"CT mean = {ct_vals.mean():.4f}")
print(f"T mean = {t_vals.mean():.4f}")
print(f"Cohen's d = {cohens_d_paired:.4f}")
print(f"Поріг: < 0.5")
print(f"Результат: {'ІНВАРІАНТНА' if cohens_d_paired < 0.5 else 'ВАРІАНТНА'}")

# ============================================================
# ПІДСУМОК
# ============================================================
print("\n" + "=" * 60)
print("ПІДСУМОК для 'opening'")
print("=" * 60)
print(f"Map-invariant:     {'✓' if eta_sq < 0.06 else '✗'} (η² = {eta_sq:.4f})")
print(f"Version-invariant: {'✓' if cohens_d < 0.5 else '✗'} (d = {cohens_d:.4f})")
print(f"Side-invariant:    {'✓' if cohens_d_paired < 0.5 else '✗'} (d = {cohens_d_paired:.4f})")

if eta_sq < 0.06 and cohens_d < 0.5 and cohens_d_paired < 0.5:
    print("\n→ UNIVERSAL INVARIANT (Triple invariant)")
elif eta_sq < 0.06 and cohens_d < 0.5:
    print("\n→ Universal invariant (map + version)")
else:
    print("\n→ Не є універсально інваріантною")
