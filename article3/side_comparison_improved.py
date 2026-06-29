"""
Improved CT vs T side comparison visualization
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.size'] = 11

OUTPUT_DIR = '/Users/yuriikuzhii/projects/hltv_parser/article3/'

# Load data
cs2 = pd.read_csv('/Users/yuriikuzhii/projects/hltv_parser/map_stats_cs2.csv')
csgo = pd.read_csv('/Users/yuriikuzhii/projects/hltv_parser/map_stats_csgo.csv')
df = pd.concat([cs2, csgo], ignore_index=True)

# Load side invariance results for Cohen's d
side_results = pd.read_csv(f'{OUTPUT_DIR}side_invariance_results.csv')

# Colors
CT_COLOR = '#5B89D6'
T_COLOR = '#E8A838'

# Sort by Cohen's d (effect size)
side_results = side_results.sort_values('cohens_d', ascending=True)

# Take top 20 features by effect size (most different between sides)
top_features = side_results.tail(20).copy()

# Create figure with relative difference
fig, ax = plt.subplots(figsize=(12, 10))

# Calculate relative difference: (CT - T) / mean * 100%
top_features['relative_diff'] = (top_features['ct_mean'] - top_features['t_mean']) / \
                                 ((top_features['ct_mean'] + top_features['t_mean']) / 2) * 100

# Sort by relative difference for better visualization
top_features = top_features.sort_values('relative_diff')

# Color based on which side is higher
colors = [CT_COLOR if x > 0 else T_COLOR for x in top_features['relative_diff']]

# Create horizontal bar chart
y_pos = np.arange(len(top_features))
bars = ax.barh(y_pos, top_features['relative_diff'], color=colors, alpha=0.8, height=0.7)

# Formatting
ax.set_yticks(y_pos)
ax.set_yticklabels(top_features['feature'], fontsize=10)
ax.set_xlabel('Relative Difference (%): (CT - T) / Mean', fontsize=12)
ax.set_title('CT vs T Side Comparison\n(Positive = CT higher, Negative = T higher)',
             fontsize=14, fontweight='bold')

# Add vertical line at 0
ax.axvline(x=0, color='black', linewidth=0.8)

# Add value labels on bars
for i, (bar, val) in enumerate(zip(bars, top_features['relative_diff'])):
    if val > 0:
        ax.text(val + 1, i, f'+{val:.1f}%', va='center', fontsize=9, color=CT_COLOR)
    else:
        ax.text(val - 1, i, f'{val:.1f}%', va='center', ha='right', fontsize=9, color=T_COLOR)

# Add legend
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=CT_COLOR, alpha=0.8, label='CT higher'),
                   Patch(facecolor=T_COLOR, alpha=0.8, label='T higher')]
ax.legend(handles=legend_elements, loc='lower right', fontsize=11)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}side_comparison_relative.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: side_comparison_relative.png")


# Version 2: Grouped by scale (small vs large values)
fig, axes = plt.subplots(1, 2, figsize=(14, 8))

# Split features by scale
small_scale = side_results[side_results['ct_mean'] < 1.0].tail(12)
large_scale = side_results[side_results['ct_mean'] >= 1.0].tail(8)

for ax, data, title in [(axes[0], small_scale, 'Per-Round Metrics (0-1 scale)'),
                         (axes[1], large_scale, 'Aggregate Metrics')]:

    y_pos = np.arange(len(data))
    width = 0.35

    ax.barh(y_pos - width/2, data['ct_mean'], width, label='CT', color=CT_COLOR, alpha=0.8)
    ax.barh(y_pos + width/2, data['t_mean'], width, label='T', color=T_COLOR, alpha=0.8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(data['feature'], fontsize=9)
    ax.set_xlabel('Mean Value', fontsize=11)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.legend(fontsize=10)

plt.suptitle('CT vs T Side Comparison (Grouped by Scale)', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}side_comparison_grouped.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: side_comparison_grouped.png")


# Version 3: Normalized (z-score style) comparison
fig, ax = plt.subplots(figsize=(12, 10))

# Normalize: show how many SDs the difference is
top20 = side_results.tail(20).copy()
top20['norm_diff'] = (top20['ct_mean'] - top20['t_mean']) / \
                      np.sqrt((top20['ct_mean']**2 + top20['t_mean']**2) / 2)
top20 = top20.sort_values('norm_diff')

colors = [CT_COLOR if x > 0 else T_COLOR for x in top20['norm_diff']]
y_pos = np.arange(len(top20))

bars = ax.barh(y_pos, top20['norm_diff'], color=colors, alpha=0.8, height=0.7)

ax.set_yticks(y_pos)
ax.set_yticklabels(top20['feature'], fontsize=10)
ax.set_xlabel('Normalized Difference (CT - T) / RMS', fontsize=12)
ax.set_title('CT vs T: Normalized Side Difference\n(Positive = CT higher, Negative = T higher)',
             fontsize=14, fontweight='bold')
ax.axvline(x=0, color='black', linewidth=0.8)

legend_elements = [Patch(facecolor=CT_COLOR, alpha=0.8, label='CT higher'),
                   Patch(facecolor=T_COLOR, alpha=0.8, label='T higher')]
ax.legend(handles=legend_elements, loc='lower right', fontsize=11)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}side_comparison_normalized.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: side_comparison_normalized.png")


# Version 4: Cohen's d effect size visualization
fig, ax = plt.subplots(figsize=(12, 10))

all_features = side_results.copy()
all_features['signed_cohens_d'] = all_features['cohens_d'] * np.sign(all_features['difference'])
all_features = all_features.sort_values('signed_cohens_d')

# Take top and bottom (most different)
top_bottom = pd.concat([all_features.head(10), all_features.tail(10)])

colors = [CT_COLOR if x > 0 else T_COLOR for x in top_bottom['signed_cohens_d']]
y_pos = np.arange(len(top_bottom))

bars = ax.barh(y_pos, top_bottom['signed_cohens_d'], color=colors, alpha=0.8, height=0.7)

ax.set_yticks(y_pos)
ax.set_yticklabels(top_bottom['feature'], fontsize=10)
ax.set_xlabel("Cohen's d (Effect Size)", fontsize=12)
ax.set_title("CT vs T: Effect Size (Cohen's d)\n(Positive = CT higher, Negative = T higher)",
             fontsize=14, fontweight='bold')
ax.axvline(x=0, color='black', linewidth=0.8)

# Add threshold lines
ax.axvline(x=0.5, color='gray', linestyle='--', alpha=0.5, linewidth=1)
ax.axvline(x=-0.5, color='gray', linestyle='--', alpha=0.5, linewidth=1)
ax.axvline(x=0.8, color='gray', linestyle=':', alpha=0.5, linewidth=1)
ax.axvline(x=-0.8, color='gray', linestyle=':', alpha=0.5, linewidth=1)

# Add text for thresholds
ax.text(0.5, len(top_bottom)-0.5, 'medium', fontsize=8, color='gray', ha='center')
ax.text(0.8, len(top_bottom)-0.5, 'large', fontsize=8, color='gray', ha='center')

legend_elements = [Patch(facecolor=CT_COLOR, alpha=0.8, label='CT higher'),
                   Patch(facecolor=T_COLOR, alpha=0.8, label='T higher')]
ax.legend(handles=legend_elements, loc='upper left', fontsize=11)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}side_comparison_cohens_d.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: side_comparison_cohens_d.png")

print("\nDone! Check the article3 folder for new plots.")
