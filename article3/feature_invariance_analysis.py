"""
Feature Invariance Analysis for CS2/CSGO Map Statistics
Analyzes feature space invariance across:
1. Maps
2. Game versions (CS2 vs CSGO)
3. Sides (T vs CT)
"""

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

OUTPUT_DIR = '/Users/yuriikuzhii/projects/hltv_parser/article3/'

def load_data():
    """Load CS2 and CSGO datasets"""
    cs2 = pd.read_csv('/Users/yuriikuzhii/projects/hltv_parser/map_stats_cs2.csv')
    csgo = pd.read_csv('/Users/yuriikuzhii/projects/hltv_parser/map_stats_csgo.csv')

    print(f"CS2 dataset: {cs2.shape[0]} rows, {cs2.shape[1]} columns")
    print(f"CSGO dataset: {csgo.shape[0]} rows, {csgo.shape[1]} columns")

    # Combine datasets
    combined = pd.concat([cs2, csgo], ignore_index=True)

    # Clean map column - keep only valid map names (starting with de_)
    valid_maps = combined['map'].str.startswith('de_', na=False)
    combined = combined[valid_maps].copy()
    combined = combined.dropna(subset=['game_version'])

    print(f"Combined dataset (after cleaning): {combined.shape[0]} rows")
    print(f"Valid maps: {combined['map'].unique()}")

    return cs2, csgo, combined

def get_numeric_features(df):
    """Extract numeric features, excluding metadata columns"""
    exclude_cols = ['full_url', 'player_name', 'game_version', 'map', 'age',
                    'time_alive_per_round', 'ct_time_alive_per_round', 't_time_alive_per_round']

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [c for c in numeric_cols if c not in exclude_cols]

    return feature_cols

def get_base_features(feature_cols):
    """Get base features (without ct_/t_ prefix)"""
    base_features = set()
    for col in feature_cols:
        if col.startswith('ct_'):
            base_features.add(col[3:])
        elif col.startswith('t_'):
            base_features.add(col[2:])
        else:
            base_features.add(col)
    return list(base_features)

def analyze_map_invariance(df, feature_cols):
    """
    Analyze feature invariance across maps using:
    - ANOVA F-test
    - Effect size (eta-squared)
    """
    print("\n" + "="*60)
    print("1. MAP INVARIANCE ANALYSIS")
    print("="*60)

    maps = df['map'].unique()
    print(f"Maps in dataset: {maps}")

    results = []

    for feature in feature_cols:
        if feature.startswith('ct_') or feature.startswith('t_'):
            continue  # Skip side-specific features for map analysis

        groups = [df[df['map'] == m][feature].dropna() for m in maps]
        groups = [g for g in groups if len(g) > 1]

        if len(groups) < 2:
            continue

        try:
            f_stat, p_value = stats.f_oneway(*groups)

            # Calculate eta-squared (effect size)
            all_data = pd.concat([pd.Series(g) for g in groups])
            grand_mean = all_data.mean()
            ss_between = sum(len(g) * (g.mean() - grand_mean)**2 for g in groups)
            ss_total = sum((all_data - grand_mean)**2)
            eta_squared = ss_between / ss_total if ss_total > 0 else 0

            results.append({
                'feature': feature,
                'f_statistic': f_stat,
                'p_value': p_value,
                'eta_squared': eta_squared,
                'invariant': p_value > 0.05  # Not significantly different
            })
        except Exception as e:
            continue

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('eta_squared', ascending=True)

    # Top invariant features (low eta-squared)
    print("\nTOP 15 MAP-INVARIANT FEATURES (low effect size):")
    print(results_df.head(15)[['feature', 'eta_squared', 'p_value', 'invariant']].to_string())

    print("\nTOP 15 MAP-VARIANT FEATURES (high effect size):")
    print(results_df.tail(15)[['feature', 'eta_squared', 'p_value', 'invariant']].to_string())

    return results_df

def analyze_game_version_invariance(df, feature_cols):
    """
    Analyze feature invariance between CS2 and CSGO using:
    - Mann-Whitney U test (non-parametric)
    - Cohen's d effect size
    """
    print("\n" + "="*60)
    print("2. GAME VERSION INVARIANCE ANALYSIS (CS2 vs CSGO)")
    print("="*60)

    cs2_data = df[df['game_version'] == 'cs2']
    csgo_data = df[df['game_version'] == 'csgo']

    print(f"CS2 samples: {len(cs2_data)}, CSGO samples: {len(csgo_data)}")

    results = []

    for feature in feature_cols:
        if feature.startswith('ct_') or feature.startswith('t_'):
            continue

        cs2_vals = cs2_data[feature].dropna()
        csgo_vals = csgo_data[feature].dropna()

        if len(cs2_vals) < 10 or len(csgo_vals) < 10:
            continue

        try:
            # Mann-Whitney U test
            stat, p_value = stats.mannwhitneyu(cs2_vals, csgo_vals, alternative='two-sided')

            # Cohen's d
            pooled_std = np.sqrt((cs2_vals.std()**2 + csgo_vals.std()**2) / 2)
            cohens_d = abs(cs2_vals.mean() - csgo_vals.mean()) / pooled_std if pooled_std > 0 else 0

            results.append({
                'feature': feature,
                'cs2_mean': cs2_vals.mean(),
                'csgo_mean': csgo_vals.mean(),
                'difference': cs2_vals.mean() - csgo_vals.mean(),
                'p_value': p_value,
                'cohens_d': cohens_d,
                'invariant': p_value > 0.05
            })
        except Exception as e:
            continue

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('cohens_d', ascending=True)

    print("\nTOP 15 GAME-INVARIANT FEATURES (low Cohen's d):")
    print(results_df.head(15)[['feature', 'cohens_d', 'p_value', 'invariant']].to_string())

    print("\nTOP 15 GAME-VARIANT FEATURES (high Cohen's d):")
    print(results_df.tail(15)[['feature', 'cohens_d', 'difference', 'invariant']].to_string())

    return results_df

def analyze_side_invariance(df, feature_cols):
    """
    Analyze feature invariance between T and CT sides using:
    - Paired t-test (same player, different sides)
    - Effect size
    """
    print("\n" + "="*60)
    print("3. SIDE INVARIANCE ANALYSIS (T vs CT)")
    print("="*60)

    # Get base features that have both CT and T versions
    base_features = get_base_features(feature_cols)

    results = []

    for base_feat in base_features:
        ct_col = f'ct_{base_feat}'
        t_col = f't_{base_feat}'

        if ct_col not in df.columns or t_col not in df.columns:
            continue

        # Get paired data
        valid_mask = df[ct_col].notna() & df[t_col].notna()
        ct_vals = df.loc[valid_mask, ct_col]
        t_vals = df.loc[valid_mask, t_col]

        if len(ct_vals) < 10:
            continue

        try:
            # Paired t-test
            t_stat, p_value = stats.ttest_rel(ct_vals, t_vals)

            # Effect size (Cohen's d for paired samples)
            diff = ct_vals - t_vals
            cohens_d = abs(diff.mean()) / diff.std() if diff.std() > 0 else 0

            results.append({
                'feature': base_feat,
                'ct_mean': ct_vals.mean(),
                't_mean': t_vals.mean(),
                'difference': ct_vals.mean() - t_vals.mean(),
                't_statistic': t_stat,
                'p_value': p_value,
                'cohens_d': cohens_d,
                'invariant': p_value > 0.05
            })
        except Exception as e:
            continue

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('cohens_d', ascending=True)

    print("\nTOP 15 SIDE-INVARIANT FEATURES (low Cohen's d):")
    print(results_df.head(15)[['feature', 'cohens_d', 'p_value', 'invariant']].to_string())

    print("\nTOP 15 SIDE-VARIANT FEATURES (high Cohen's d):")
    print(results_df.tail(15)[['feature', 'cohens_d', 'difference', 'invariant']].to_string())

    return results_df

def create_visualizations(df, map_results, version_results, side_results, feature_cols):
    """Create comprehensive visualizations"""

    # 1. Summary heatmap of invariance
    fig, axes = plt.subplots(1, 3, figsize=(18, 8))

    # Map invariance bar chart
    ax1 = axes[0]
    top_map = map_results.head(10)
    bottom_map = map_results.tail(10)
    combined_map = pd.concat([top_map, bottom_map])
    colors = ['green' if x else 'red' for x in combined_map['invariant']]
    ax1.barh(range(len(combined_map)), combined_map['eta_squared'], color=colors, alpha=0.7)
    ax1.set_yticks(range(len(combined_map)))
    ax1.set_yticklabels(combined_map['feature'], fontsize=8)
    ax1.set_xlabel('Eta-squared (Effect Size)')
    ax1.set_title('Map Invariance\n(Green=Invariant, Red=Variant)')
    ax1.axvline(x=0.06, color='gray', linestyle='--', label='Medium effect threshold')

    # Game version invariance
    ax2 = axes[1]
    top_ver = version_results.head(10)
    bottom_ver = version_results.tail(10)
    combined_ver = pd.concat([top_ver, bottom_ver])
    colors = ['green' if x else 'red' for x in combined_ver['invariant']]
    ax2.barh(range(len(combined_ver)), combined_ver['cohens_d'], color=colors, alpha=0.7)
    ax2.set_yticks(range(len(combined_ver)))
    ax2.set_yticklabels(combined_ver['feature'], fontsize=8)
    ax2.set_xlabel("Cohen's d (Effect Size)")
    ax2.set_title('Game Version Invariance\n(CS2 vs CSGO)')
    ax2.axvline(x=0.5, color='gray', linestyle='--', label='Medium effect threshold')

    # Side invariance
    ax3 = axes[2]
    top_side = side_results.head(10)
    bottom_side = side_results.tail(10)
    combined_side = pd.concat([top_side, bottom_side])
    colors = ['green' if x else 'red' for x in combined_side['invariant']]
    ax3.barh(range(len(combined_side)), combined_side['cohens_d'], color=colors, alpha=0.7)
    ax3.set_yticks(range(len(combined_side)))
    ax3.set_yticklabels(combined_side['feature'], fontsize=8)
    ax3.set_xlabel("Cohen's d (Effect Size)")
    ax3.set_title('Side Invariance\n(T vs CT)')
    ax3.axvline(x=0.5, color='gray', linestyle='--', label='Medium effect threshold')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR + 'invariance_summary.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 2. PCA visualization by different groupings
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    # Prepare data for PCA
    base_features = [f for f in feature_cols if not f.startswith('ct_') and not f.startswith('t_')]
    X = df[base_features].copy()
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median())

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)

    # By map
    ax1 = axes[0]
    maps = df['map'].dropna().unique()
    for m in maps:
        if pd.isna(m) or not isinstance(m, str):
            continue
        mask = df['map'] == m
        ax1.scatter(X_pca[mask, 0], X_pca[mask, 1], label=str(m).replace('de_', ''), alpha=0.5, s=20)
    ax1.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
    ax1.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
    ax1.set_title('PCA by Map')
    ax1.legend(fontsize=8, ncol=2)

    # By game version
    ax2 = axes[1]
    for version in ['cs2', 'csgo']:
        mask = df['game_version'] == version
        ax2.scatter(X_pca[mask, 0], X_pca[mask, 1], label=version.upper(), alpha=0.5, s=20)
    ax2.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
    ax2.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
    ax2.set_title('PCA by Game Version')
    ax2.legend(fontsize=10)

    # Combined grouping (version + map)
    ax3 = axes[2]
    df['group'] = df['game_version'].astype(str) + '_' + df['map'].astype(str).str.replace('de_', '')
    unique_groups = df['group'].dropna().unique()[:8]  # Limit to 8 groups for visibility
    for g in unique_groups:
        if pd.isna(g):
            continue
        mask = df['group'] == g
        ax3.scatter(X_pca[mask, 0], X_pca[mask, 1], label=str(g), alpha=0.5, s=20)
    ax3.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
    ax3.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
    ax3.set_title('PCA by Game+Map')
    ax3.legend(fontsize=7, ncol=2)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR + 'pca_visualization.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 3. Side comparison heatmap
    fig, ax = plt.subplots(figsize=(10, 12))

    side_pivot = side_results[['feature', 'ct_mean', 't_mean']].copy()
    side_pivot = side_pivot.sort_values('ct_mean', ascending=False).head(25)

    x = np.arange(len(side_pivot))
    width = 0.35

    ax.barh(x - width/2, side_pivot['ct_mean'], width, label='CT', color='blue', alpha=0.7)
    ax.barh(x + width/2, side_pivot['t_mean'], width, label='T', color='orange', alpha=0.7)

    ax.set_yticks(x)
    ax.set_yticklabels(side_pivot['feature'], fontsize=9)
    ax.set_xlabel('Mean Value')
    ax.set_title('CT vs T Side Comparison (Top 25 Features)')
    ax.legend()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR + 'side_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 4. Distribution plots for key features
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    key_features = ['kills_per_round', 'damage_per_round', 'rating_3.0',
                    'opening_kills_per_round', 'utility_damage_per_round', 'sniper_kills_per_round']

    for idx, feat in enumerate(key_features):
        if feat not in df.columns:
            continue
        ax = axes[idx // 3, idx % 3]

        for version in ['cs2', 'csgo']:
            data = df[df['game_version'] == version][feat].dropna()
            ax.hist(data, bins=30, alpha=0.5, label=version.upper(), density=True)

        ax.set_xlabel(feat)
        ax.set_ylabel('Density')
        ax.set_title(f'{feat} Distribution')
        ax.legend()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR + 'feature_distributions.png', dpi=150, bbox_inches='tight')
    plt.close()

    print(f"\nVisualizations saved to {OUTPUT_DIR}")

def find_universal_invariant_features(map_results, version_results, side_results):
    """Find features that are invariant across all dimensions"""

    print("\n" + "="*60)
    print("4. UNIVERSAL INVARIANT FEATURES")
    print("="*60)

    # Merge results
    map_inv = set(map_results[map_results['eta_squared'] < 0.06]['feature'])
    version_inv = set(version_results[version_results['cohens_d'] < 0.5]['feature'])

    # For side results, we need to check if the base feature exists
    side_inv = set(side_results[side_results['cohens_d'] < 0.5]['feature'])

    # Universal invariant (invariant to maps AND game version)
    universal_inv = map_inv & version_inv

    print(f"\nMap-invariant features: {len(map_inv)}")
    print(f"Version-invariant features: {len(version_inv)}")
    print(f"Side-invariant features: {len(side_inv)}")
    print(f"\nUniversal invariant (map + version): {len(universal_inv)}")
    print(list(universal_inv)[:20])

    # Features invariant to all three
    # Note: side features have different names, so we check overlap differently
    base_side_inv = set()
    for f in side_inv:
        base_side_inv.add(f)

    triple_inv = universal_inv & base_side_inv
    print(f"\nTriple invariant (map + version + side): {len(triple_inv)}")
    print(list(triple_inv))

    return {
        'map_invariant': list(map_inv),
        'version_invariant': list(version_inv),
        'side_invariant': list(side_inv),
        'universal_invariant': list(universal_inv),
        'triple_invariant': list(triple_inv)
    }

def main():
    print("="*60)
    print("FEATURE INVARIANCE ANALYSIS FOR CS2/CSGO MAP STATISTICS")
    print("="*60)

    # Load data
    cs2, csgo, combined = load_data()

    # Get feature columns
    feature_cols = get_numeric_features(combined)
    print(f"\nTotal numeric features: {len(feature_cols)}")

    # 1. Map invariance
    map_results = analyze_map_invariance(combined, feature_cols)

    # 2. Game version invariance
    version_results = analyze_game_version_invariance(combined, feature_cols)

    # 3. Side invariance
    side_results = analyze_side_invariance(combined, feature_cols)

    # 4. Find universal invariant features
    invariant_features = find_universal_invariant_features(map_results, version_results, side_results)

    # Create visualizations
    create_visualizations(combined, map_results, version_results, side_results, feature_cols)

    # Save results
    map_results.to_csv(OUTPUT_DIR + 'map_invariance_results.csv', index=False)
    version_results.to_csv(OUTPUT_DIR + 'version_invariance_results.csv', index=False)
    side_results.to_csv(OUTPUT_DIR + 'side_invariance_results.csv', index=False)

    # Save invariant features summary
    with open(OUTPUT_DIR + 'invariant_features_summary.txt', 'w') as f:
        f.write("FEATURE INVARIANCE ANALYSIS SUMMARY\n")
        f.write("="*60 + "\n\n")

        f.write("MAP-INVARIANT FEATURES (eta-squared < 0.06):\n")
        f.write("-"*40 + "\n")
        for feat in sorted(invariant_features['map_invariant']):
            f.write(f"  - {feat}\n")

        f.write(f"\nVERSION-INVARIANT FEATURES (Cohen's d < 0.5):\n")
        f.write("-"*40 + "\n")
        for feat in sorted(invariant_features['version_invariant']):
            f.write(f"  - {feat}\n")

        f.write(f"\nSIDE-INVARIANT FEATURES (Cohen's d < 0.5):\n")
        f.write("-"*40 + "\n")
        for feat in sorted(invariant_features['side_invariant']):
            f.write(f"  - {feat}\n")

        f.write(f"\nUNIVERSAL INVARIANT (map + version):\n")
        f.write("-"*40 + "\n")
        for feat in sorted(invariant_features['universal_invariant']):
            f.write(f"  - {feat}\n")

        f.write(f"\nTRIPLE INVARIANT (map + version + side):\n")
        f.write("-"*40 + "\n")
        for feat in sorted(invariant_features['triple_invariant']):
            f.write(f"  - {feat}\n")

    print(f"\nResults saved to {OUTPUT_DIR}")

    # Summary statistics
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total features analyzed: {len(feature_cols)}")
    print(f"Map-invariant: {len(invariant_features['map_invariant'])} ({len(invariant_features['map_invariant'])/len(map_results)*100:.1f}%)")
    print(f"Version-invariant: {len(invariant_features['version_invariant'])} ({len(invariant_features['version_invariant'])/len(version_results)*100:.1f}%)")
    print(f"Side-invariant: {len(invariant_features['side_invariant'])} ({len(invariant_features['side_invariant'])/len(side_results)*100:.1f}%)")
    print(f"Universal (map+version): {len(invariant_features['universal_invariant'])}")
    print(f"Triple invariant: {len(invariant_features['triple_invariant'])}")

if __name__ == "__main__":
    main()
