"""
Normalized Feature Visualizations for CS2/CSGO Analysis
Creates visualizations with standardized features for better comparison
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 10

OUTPUT_DIR = '/Users/yuriikuzhii/projects/hltv_parser/article3/'

def load_and_prepare_data():
    """Load and clean data"""
    cs2 = pd.read_csv('/Users/yuriikuzhii/projects/hltv_parser/map_stats_cs2.csv')
    csgo = pd.read_csv('/Users/yuriikuzhii/projects/hltv_parser/map_stats_csgo.csv')

    combined = pd.concat([cs2, csgo], ignore_index=True)

    # Clean map column
    valid_maps = combined['map'].str.startswith('de_', na=False)
    combined = combined[valid_maps].copy()
    combined = combined.dropna(subset=['game_version'])

    return combined

def get_base_features(df):
    """Get base numeric features (excluding ct_/t_ prefixes and metadata)"""
    exclude_cols = ['full_url', 'player_name', 'game_version', 'map', 'age',
                    'time_alive_per_round', 'ct_time_alive_per_round', 't_time_alive_per_round']

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    base_features = [c for c in numeric_cols
                     if c not in exclude_cols
                     and not c.startswith('ct_')
                     and not c.startswith('t_')]

    return base_features

def normalize_dataframe(df, features, method='zscore'):
    """Normalize features using specified method"""
    X = df[features].copy()
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median())

    if method == 'zscore':
        scaler = StandardScaler()
    elif method == 'minmax':
        scaler = MinMaxScaler()
    elif method == 'robust':
        scaler = RobustScaler()

    X_normalized = pd.DataFrame(
        scaler.fit_transform(X),
        columns=features,
        index=df.index
    )

    return X_normalized, scaler

def plot_normalized_comparison(df, features):
    """Create normalized comparison plots"""

    # Select key features for visualization
    key_features = [
        'kills_per_round', 'damage_per_round', 'rating_3.0',
        'opening_kills_per_round', 'assists_per_round', 'trade_kills_per_round',
        'utility_damage_per_round', 'sniper_kills_per_round', 'clutch_points_per_round',
        'firepower', 'entrying', 'trading'
    ]
    key_features = [f for f in key_features if f in features]

    # Normalize data
    X_zscore, _ = normalize_dataframe(df, key_features, 'zscore')
    X_minmax, _ = normalize_dataframe(df, key_features, 'minmax')

    # Add grouping columns
    X_zscore['game_version'] = df['game_version'].values
    X_zscore['map'] = df['map'].values
    X_minmax['game_version'] = df['game_version'].values
    X_minmax['map'] = df['map'].values

    # 1. Z-score normalized boxplot by game version
    fig, axes = plt.subplots(2, 1, figsize=(16, 12))

    # Melt for seaborn
    zscore_melted = X_zscore.melt(
        id_vars=['game_version'],
        value_vars=key_features,
        var_name='Feature',
        value_name='Z-score'
    )

    ax1 = axes[0]
    sns.boxplot(data=zscore_melted, x='Feature', y='Z-score', hue='game_version',
                ax=ax1, palette=['#3498db', '#e74c3c'])
    ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha='right')
    ax1.set_title('Z-score Normalized Features: CS2 vs CSGO', fontsize=14, fontweight='bold')
    ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax1.legend(title='Game Version')
    ax1.set_ylabel('Z-score (σ від середнього)')

    # 2. Min-Max normalized comparison
    minmax_melted = X_minmax.melt(
        id_vars=['game_version'],
        value_vars=key_features,
        var_name='Feature',
        value_name='Normalized Value'
    )

    ax2 = axes[1]
    sns.boxplot(data=minmax_melted, x='Feature', y='Normalized Value', hue='game_version',
                ax=ax2, palette=['#3498db', '#e74c3c'])
    ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45, ha='right')
    ax2.set_title('Min-Max Normalized Features [0-1]: CS2 vs CSGO', fontsize=14, fontweight='bold')
    ax2.legend(title='Game Version')
    ax2.set_ylabel('Normalized Value [0-1]')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR + 'normalized_version_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: normalized_version_comparison.png")

def plot_normalized_side_comparison(df, features):
    """Create normalized CT vs T comparison"""

    # Get paired features
    base_features = []
    for f in features:
        ct_col = f'ct_{f}'
        t_col = f't_{f}'
        if ct_col in df.columns and t_col in df.columns:
            base_features.append(f)

    # Select key features
    key_features = [
        'kills_per_round', 'damage_per_round', 'rating_3.0',
        'opening_kills_per_round', 'assists_per_round', 'utility_damage_per_round',
        'sniper_kills_per_round', 'firepower', 'saves_per_round_loss',
        'flashes_thrown_per_round', 'trade_kills_per_round', 'support_rounds'
    ]
    key_features = [f for f in key_features if f in base_features]

    # Prepare CT and T data
    ct_data = df[[f'ct_{f}' for f in key_features]].copy()
    ct_data.columns = key_features
    ct_data['Side'] = 'CT'

    t_data = df[[f't_{f}' for f in key_features]].copy()
    t_data.columns = key_features
    t_data['Side'] = 'T'

    combined_sides = pd.concat([ct_data, t_data], ignore_index=True)

    # Normalize together
    X = combined_sides[key_features].replace([np.inf, -np.inf], np.nan).fillna(combined_sides[key_features].median())
    scaler = StandardScaler()
    X_normalized = pd.DataFrame(scaler.fit_transform(X), columns=key_features)
    X_normalized['Side'] = combined_sides['Side'].values

    # Plot
    fig, ax = plt.subplots(figsize=(16, 8))

    melted = X_normalized.melt(
        id_vars=['Side'],
        value_vars=key_features,
        var_name='Feature',
        value_name='Z-score'
    )

    sns.boxplot(data=melted, x='Feature', y='Z-score', hue='Side',
                ax=ax, palette=['#2ecc71', '#f39c12'])
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    ax.set_title('Z-score Normalized Features: CT vs T Side', fontsize=14, fontweight='bold')
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax.legend(title='Side')
    ax.set_ylabel('Z-score (σ від середнього)')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR + 'normalized_side_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: normalized_side_comparison.png")

def plot_normalized_map_heatmap(df, features):
    """Create heatmap of normalized feature means by map"""

    key_features = [
        'kills_per_round', 'damage_per_round', 'rating_3.0',
        'opening_kills_per_round', 'utility_damage_per_round', 'sniper_kills_per_round',
        'firepower', 'entrying', 'clutching', 'trading',
        'flashes_thrown_per_round', 'saves_per_round_loss'
    ]
    key_features = [f for f in key_features if f in features]

    # Calculate mean by map
    map_means = df.groupby('map')[key_features].mean()

    # Z-score normalize across maps (each feature independently)
    map_means_normalized = (map_means - map_means.mean()) / map_means.std()

    # Clean map names
    map_means_normalized.index = map_means_normalized.index.str.replace('de_', '')

    # Plot heatmap
    fig, ax = plt.subplots(figsize=(14, 8))

    sns.heatmap(map_means_normalized,
                annot=True,
                fmt='.2f',
                cmap='RdYlGn',
                center=0,
                ax=ax,
                cbar_kws={'label': 'Z-score (відхилення від середнього по картах)'})

    ax.set_title('Normalized Feature Means by Map\n(Green = Above Average, Red = Below Average)',
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('Features')
    ax.set_ylabel('Maps')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR + 'normalized_map_heatmap.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: normalized_map_heatmap.png")

def plot_radar_chart(df, features):
    """Create radar chart comparing CS2 vs CSGO normalized profiles"""

    key_features = [
        'kills_per_round', 'damage_per_round', 'rating_3.0',
        'opening_kills_per_round', 'utility_damage_per_round',
        'sniper_kills_per_round', 'firepower', 'entrying',
        'clutching', 'trading', 'assists_per_round', 'support_rounds'
    ]
    key_features = [f for f in key_features if f in features]

    # Calculate means by version
    cs2_means = df[df['game_version'] == 'cs2'][key_features].mean()
    csgo_means = df[df['game_version'] == 'csgo'][key_features].mean()

    # Min-Max normalize to [0, 1] for radar
    all_means = pd.concat([cs2_means, csgo_means], axis=1)
    all_means.columns = ['cs2', 'csgo']

    min_vals = all_means.min(axis=1)
    max_vals = all_means.max(axis=1)
    range_vals = max_vals - min_vals
    range_vals[range_vals == 0] = 1  # Avoid division by zero

    cs2_norm = (cs2_means - min_vals) / range_vals
    csgo_norm = (csgo_means - min_vals) / range_vals

    # Radar chart
    angles = np.linspace(0, 2 * np.pi, len(key_features), endpoint=False).tolist()
    angles += angles[:1]  # Complete the loop

    cs2_values = cs2_norm.tolist() + [cs2_norm.tolist()[0]]
    csgo_values = csgo_norm.tolist() + [csgo_norm.tolist()[0]]

    fig, ax = plt.subplots(figsize=(12, 10), subplot_kw=dict(polar=True))

    ax.plot(angles, cs2_values, 'o-', linewidth=2, label='CS2', color='#3498db')
    ax.fill(angles, cs2_values, alpha=0.25, color='#3498db')

    ax.plot(angles, csgo_values, 'o-', linewidth=2, label='CSGO', color='#e74c3c')
    ax.fill(angles, csgo_values, alpha=0.25, color='#e74c3c')

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(key_features, size=10)
    ax.set_title('Normalized Player Profile: CS2 vs CSGO\n(Min-Max scaled per feature)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR + 'normalized_radar_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: normalized_radar_comparison.png")

def plot_effect_sizes_normalized(df):
    """Create normalized effect size comparison chart"""

    # Load results
    map_results = pd.read_csv(OUTPUT_DIR + 'map_invariance_results.csv')
    version_results = pd.read_csv(OUTPUT_DIR + 'version_invariance_results.csv')
    side_results = pd.read_csv(OUTPUT_DIR + 'side_invariance_results.csv')

    # Merge and normalize effect sizes
    # For fair comparison, we'll use percentile ranks

    map_results['map_effect_percentile'] = map_results['eta_squared'].rank(pct=True)
    version_results['version_effect_percentile'] = version_results['cohens_d'].rank(pct=True)
    side_results['side_effect_percentile'] = side_results['cohens_d'].rank(pct=True)

    # Merge on feature name
    merged = map_results[['feature', 'map_effect_percentile', 'eta_squared']].merge(
        version_results[['feature', 'version_effect_percentile', 'cohens_d']],
        on='feature', how='inner'
    )

    # For side, feature names are different (no prefix)
    side_results_renamed = side_results.copy()
    merged2 = merged.merge(
        side_results_renamed[['feature', 'side_effect_percentile']],
        on='feature', how='left'
    )
    merged2 = merged2.dropna()

    # Calculate "invariance score" (lower = more invariant)
    merged2['total_variance'] = (merged2['map_effect_percentile'] +
                                  merged2['version_effect_percentile'] +
                                  merged2['side_effect_percentile']) / 3

    merged2 = merged2.sort_values('total_variance')

    # Plot top 15 most invariant and top 15 most variant
    top_invariant = merged2.head(12)
    top_variant = merged2.tail(12)

    fig, axes = plt.subplots(1, 2, figsize=(16, 10))

    # Most invariant
    ax1 = axes[0]
    x = np.arange(len(top_invariant))
    width = 0.25

    ax1.barh(x - width, top_invariant['map_effect_percentile'], width,
             label='Map Effect', color='#3498db', alpha=0.8)
    ax1.barh(x, top_invariant['version_effect_percentile'], width,
             label='Version Effect', color='#e74c3c', alpha=0.8)
    ax1.barh(x + width, top_invariant['side_effect_percentile'], width,
             label='Side Effect', color='#2ecc71', alpha=0.8)

    ax1.set_yticks(x)
    ax1.set_yticklabels(top_invariant['feature'])
    ax1.set_xlabel('Effect Size Percentile (lower = more invariant)')
    ax1.set_title('Most INVARIANT Features\n(Stable across all dimensions)', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.axvline(x=0.5, color='gray', linestyle='--', alpha=0.5)

    # Most variant
    ax2 = axes[1]
    x = np.arange(len(top_variant))

    ax2.barh(x - width, top_variant['map_effect_percentile'], width,
             label='Map Effect', color='#3498db', alpha=0.8)
    ax2.barh(x, top_variant['version_effect_percentile'], width,
             label='Version Effect', color='#e74c3c', alpha=0.8)
    ax2.barh(x + width, top_variant['side_effect_percentile'], width,
             label='Side Effect', color='#2ecc71', alpha=0.8)

    ax2.set_yticks(x)
    ax2.set_yticklabels(top_variant['feature'])
    ax2.set_xlabel('Effect Size Percentile (higher = more variant)')
    ax2.set_title('Most VARIANT Features\n(Context-dependent)', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.axvline(x=0.5, color='gray', linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR + 'normalized_effect_sizes.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: normalized_effect_sizes.png")

    # Save invariance ranking
    merged2[['feature', 'total_variance', 'map_effect_percentile',
             'version_effect_percentile', 'side_effect_percentile']].to_csv(
        OUTPUT_DIR + 'feature_invariance_ranking.csv', index=False
    )
    print("Saved: feature_invariance_ranking.csv")

def plot_distribution_violin(df, features):
    """Create violin plots for normalized distributions"""

    key_features = [
        'kills_per_round', 'damage_per_round', 'rating_3.0',
        'opening_kills_per_round', 'utility_damage_per_round', 'sniper_kills_per_round'
    ]
    key_features = [f for f in key_features if f in features]

    # Normalize
    X_norm, _ = normalize_dataframe(df, key_features, 'zscore')
    X_norm['game_version'] = df['game_version'].values

    # Melt
    melted = X_norm.melt(
        id_vars=['game_version'],
        value_vars=key_features,
        var_name='Feature',
        value_name='Z-score'
    )

    fig, ax = plt.subplots(figsize=(14, 8))

    sns.violinplot(data=melted, x='Feature', y='Z-score', hue='game_version',
                   split=True, ax=ax, palette=['#3498db', '#e74c3c'], inner='quart')

    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    ax.set_title('Z-score Distribution Comparison: CS2 vs CSGO\n(Violin plots show full distribution shape)',
                 fontsize=14, fontweight='bold')
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax.legend(title='Game Version')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR + 'normalized_violin_distributions.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: normalized_violin_distributions.png")

def main():
    print("="*60)
    print("CREATING NORMALIZED VISUALIZATIONS")
    print("="*60)

    # Load data
    df = load_and_prepare_data()
    features = get_base_features(df)

    print(f"Data loaded: {len(df)} records, {len(features)} features")

    # Create visualizations
    print("\nGenerating normalized plots...")

    plot_normalized_comparison(df, features)
    plot_normalized_side_comparison(df, features)
    plot_normalized_map_heatmap(df, features)
    plot_radar_chart(df, features)
    plot_effect_sizes_normalized(df)
    plot_distribution_violin(df, features)

    print("\n" + "="*60)
    print("All normalized visualizations saved to:", OUTPUT_DIR)
    print("="*60)

if __name__ == "__main__":
    main()
