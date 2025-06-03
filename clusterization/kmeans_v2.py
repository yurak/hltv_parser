import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score
import seaborn as sns

# 🔹 Завантаження даних
df = pd.read_csv("de_mirage_t_ct.csv", sep=';', decimal=',')
df = df.dropna(subset=['ct_role'])

# 🔹 Вибір ознак
features = df[['ct_utility', 'ct_firepower']]
scaler = StandardScaler()
X_scaled = scaler.fit_transform(features)

# 🔹 Кластеризація
kmeans = KMeans(n_clusters=5, random_state=42)
df['cluster'] = kmeans.fit_predict(X_scaled)

# 🔹 Метрики якості кластеризації
sil_score = silhouette_score(X_scaled, df['cluster'])
db_index = davies_bouldin_score(X_scaled, df['cluster'])

print(f"✅ Silhouette Score: {sil_score:.4f} (ближче до 1 — краще)")
print(f"✅ Davies-Bouldin Index: {db_index:.4f} (менше — краще)")

# 🔹 Перехресна таблиця кластера та реальної ролі
print("\n📊 Перехресна таблиця (Cluster vs CT Role):")
print(pd.crosstab(df['cluster'], df['ct_role']))

# 🔹 Візуалізація
plt.figure(figsize=(10, 6))
roles = df['ct_role'].unique()
colors = plt.cm.get_cmap('tab10', len(roles))
markers = ['o', 's', '^', 'D', 'v', '*', 'P', 'X', 'h', '+']

for i, role in enumerate(roles):
    subset = df[df['ct_role'] == role]
    plt.scatter(subset['ct_utility'], subset['ct_firepower'], 
                label=role, s=60, alpha=0.7, color=colors(i), marker=markers[i % len(markers)])

centroids = scaler.inverse_transform(kmeans.cluster_centers_)
plt.scatter(centroids[:, 0], centroids[:, 1], marker='X', s=200, c='black', label='Centroids')

plt.xlabel("CT Utility")
plt.ylabel("CT Firepower")
plt.title("K-Means Clustering by ct_utility & ct_firepower (colored by ct_role)")
plt.legend()
plt.grid(True)
plt.show()
