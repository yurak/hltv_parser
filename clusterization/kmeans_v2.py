import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# 🔹 Завантаження даних
df = pd.read_csv("de_mirage_t_ct.csv", sep=';', decimal=',')  # заміни на свій шлях
df = df.dropna(subset=['ct_role'])
# 🔹 Вибір ознак для кластеризації
features = df[['ct_utility', 'ct_firepower']]

# 🔹 Масштабування (не обов'язково, але рекомендовано)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(features)

# 🔹 Кластеризація KMeans
kmeans = KMeans(n_clusters=5, random_state=42)  # можеш змінити кількість кластерів
df['cluster'] = kmeans.fit_predict(X_scaled)

# 🔹 Візуалізація: кольори — справжня роль (ct_role)
plt.figure(figsize=(10, 6))
roles = df['ct_role'].unique()
breakpoint()
colors = plt.cm.get_cmap('tab10', len(roles))
markers = ['o', 's', '^', 'D', 'v', '*', 'P', 'X', 'h', '+']

for i, role in enumerate(roles):
    subset = df[df['ct_role'] == role]
    plt.scatter(subset['ct_utility'], subset['ct_firepower'], 
                label=role, s=60, alpha=0.7, color=colors(i), marker=markers[i % len(markers)])

# 🔹 Центроїди
centroids = scaler.inverse_transform(kmeans.cluster_centers_)
plt.scatter(centroids[:, 0], centroids[:, 1], marker='X', s=200, c='black', label='Centroids')

plt.xlabel("CT Support")
plt.ylabel("CT Firepower")
plt.title("K-Means Clustering by ct_support & ct_firepower (colored by ct_role)")
plt.legend()
plt.grid(True)
plt.show()
