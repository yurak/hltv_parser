import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from pathlib import Path

from role_features import INTEGRAL,UTILITY,MAIN_COMPONENTS_MAP

class Kmeans:
    BASE_DIR = Path(__file__).resolve()
    IMAGES_DIR = 'results'

    def __init__(self, map_name = 'de_mirage', filter_snipers = True, features = INTEGRAL, image_name ='clusterization'):
        self.filepath = map_name  + '.csv'
        self.map_name = map_name
        self.filter_snipers = filter_snipers
        self.features = features
        self.image_name = image_name
       
    def call(self):
        filepath = self.BASE_DIR.parent.parent/ 'normalization'  / 'maps'/ self.filepath
        results_dir = Path(self.IMAGES_DIR)
        results_dir.mkdir(parents=True, exist_ok=True)
        df = pd.read_csv(filepath)

        # # 2. Фільтрація не-sniper
        if self.filter_snipers:
            df_filtered = df[df['sniping'] < 0.7]
        else:
            df_filtered = df
        
        # 3. Ознаки
        X = df_filtered[self.features]

        # 4. Нормалізація
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # 5. Кластеризація
        kmeans = KMeans(n_clusters=3, random_state=42)
        df_filtered['cluster'] = kmeans.fit_predict(X_scaled)

        # 6. PCA для 2D
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)

        # 7. Малюємо графік
        plt.figure(figsize=(10, 8))
        plt.scatter(X_pca[:, 0], X_pca[:, 1], c=df_filtered['cluster'], s=60, edgecolor='black')

        # 8. Додаємо імена гравців
        for i, player_name in enumerate(df_filtered['player_name']):
            plt.text(X_pca[i, 0] + 0.02, X_pca[i, 1] + 0.02, player_name, fontsize=8)

        plt.title(f'Кластеризація гравців {self.image_name}')
        plt.xlabel('PCA 1')
        plt.ylabel('PCA 2')
        plt.grid(True)
        plt.tight_layout()
        image_wth_ext = self.map_name + self.image_name + 'detailed' + '.png'
        plt.savefig(results_dir / image_wth_ext )


for key,values in MAIN_COMPONENTS_MAP.items():
    filter_snipers = True
    prefix = '_' + key
    image_name = prefix + '_with_sniper_'
  
    if filter_snipers:
        image_name = prefix + '_no_snipers_'
    for map in ['de_mirage', 'de_nuke', 'de_inferno']:
        Kmeans(map_name = map, features = values, image_name = image_name, filter_snipers = filter_snipers).call()
    