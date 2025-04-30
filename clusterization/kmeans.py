import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from pathlib import Path

from role_features import INTEGRAL

class Kmeans:
    BASE_DIR = Path(__file__).resolve()
    IMAGES_DIR = 'results'

    def __init__(self, map_name = 'de_mirage', filter_snipers = True, features = INTEGRAL, image_name ='clusterization', filepath= 'path_to_file'):
        self.map_name = map_name
        self.filter_snipers = filter_snipers
        self.features = features
        self.image_name = image_name
        self.filepath = filepath
       
    def call(self):
        #filepath = self.BASE_DIR.parent.parent/ 'normalization' / 'top_20_normalized_all.csv'
        results_dir = Path(self.IMAGES_DIR)
        results_dir.mkdir(parents=True, exist_ok=True)
        df = pd.read_csv(self.filepath )
        df_filtered = df[df['firepower'] > 0]

        if self.filter_snipers:
            df_filtered = df_filtered[df_filtered['sniping'] < 0.7]
        else:
            df_filtered = df_filtered
        
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
    

    @classmethod
    def run_map_independent_clustering(cls):
        from role_features import MAP_INDEPENDENT
        for bool in [True, False]:  
            prefix = '_map_independent'
            image_name = prefix + ('_no_snipers_' if bool else '_with_sniper_')
            map_name = 'all'
            filepath = Kmeans.BASE_DIR.parent.parent / 'normalization' / 'top_20_normalized_all.csv'

            instance = cls(
                map_name=map_name,
                features=MAP_INDEPENDENT,
                image_name=image_name,
                filter_snipers=bool,
                filepath= filepath
            )
            instance.call()

    @classmethod
    def run_map_clustering(cls):
        from role_features import MAIN_COMPONENTS_MAP, CS_MAPS
        for key,values in MAIN_COMPONENTS_MAP.items():
            filter_snipers = True
            prefix = '_' + key
            image_name = prefix + '_with_sniper_'
        
            if filter_snipers:
                image_name = prefix + '_no_snipers_'
            for map in CS_MAPS:
                filepath = Kmeans.BASE_DIR.parent.parent/ 'normalization'  / 'maps'/ f"{map}.csv"

                instance = cls(
                    map_name=map,
                    features=values,
                    image_name=image_name,
                    filter_snipers=filter_snipers,
                    filepath= filepath
                )
                instance.call()

    

#df_clusters = Kmeans.run_map_independent_clustering()
Kmeans.run_map_clustering()
    