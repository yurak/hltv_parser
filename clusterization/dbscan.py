import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

# 🔹 Завантаження даних
df = pd.read_csv("de_mirage_t_ct.csv", sep=';', decimal=',')
df = df.dropna(subset=['ct_role'])

# 🔹 Масштабування
features = df[['ct_utility', 'ct_firepower']]
scaler = StandardScaler()
X_scaled = scaler.fit_transform(features)

# 🔹 Кластеризація DBSCAN
dbscan = DBSCAN(eps=0.4, min_samples=4)
df['cluster'] = dbscan.fit_predict(X_scaled)

# 🔹 Візуалізація з підписами
plt.figure(figsize=(12, 8))
unique_clusters = sorted(df['cluster'].unique())
colors = plt.cm.get_cmap('tab10', len(unique_clusters))
markers = ['o', 's', '^', 'D', 'v', '*', 'P', 'X', 'h', '+']

for i, cluster_id in enumerate(unique_clusters):
    subset = df[df['cluster'] == cluster_id]
    label = f"Cluster {cluster_id}" if cluster_id != -1 else "Noise"
    color = colors(i)
    marker = markers[i % len(markers)]

    plt.scatter(subset['ct_utility'], subset['ct_firepower'],
                label=label, s=60, alpha=0.7, color=color, marker=marker)

    # 🔹 Додати нікнейми
    for _, row in subset.iterrows():
        plt.text(row['ct_utility'], row['ct_firepower'], row['player_name'],
                 fontsize=8, alpha=0.8)

plt.xlabel("CT Utility")
plt.ylabel("CT Firepower")
plt.title("DBSCAN Clustering with Player Nicknames")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
