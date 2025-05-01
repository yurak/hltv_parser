import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

from role_features import INTEGRAL


class Kmeans:
    BASE_DIR = Path(__file__).resolve()
    IMAGES_DIR = 'results'

    def __init__(self, map_name='de_mirage', filter_snipers=True, features=INTEGRAL,
                 image_name='clusterization', filepath='path_to_file',
                 team_name=None, team_colors=None):
        self.map_name = map_name
        self.filter_snipers = filter_snipers
        self.features = features
        self.image_name = image_name
        self.filepath = filepath
        self.team_name = team_name or ['vitality']
        self.team_colors = team_colors or {}

    def call(self):
        results_dir = Path(self.IMAGES_DIR)
        results_dir.mkdir(parents=True, exist_ok=True)

        df = pd.read_csv(self.filepath)
        df_filtered = df[df['firepower'] > 0]

        if self.filter_snipers:
            df_filtered = df_filtered[df_filtered['sniping'] < 0.7]

        df_filtered['team'] = df_filtered['team'].str.lower()

        X = df_filtered[self.features]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        kmeans = KMeans(n_clusters=3, random_state=42)
        df_filtered['cluster'] = kmeans.fit_predict(X_scaled)

        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)

        plt.figure(figsize=(10, 8))

        # Plot highlighted teams
        highlight_teams = [t.lower() for t in self.team_name]
        for i, team in enumerate(highlight_teams):
            color = self.team_colors.get(team, 'red')  # default color
            mask = df_filtered['team'] == team

            plt.scatter(
                X_pca[mask, 0],
                X_pca[mask, 1],
                color=color,
                s=300,
                marker='*',
                edgecolor='black',
                label=team.title()
            )

        # Plot all other players
        other_mask = ~df_filtered['team'].isin(highlight_teams)
        plt.scatter(
            X_pca[other_mask, 0],
            X_pca[other_mask, 1],
            c=df_filtered.loc[other_mask, 'cluster'],
            s=60,
            marker='o',
            edgecolor='black',
            alpha=0.6,
            label='Other Players'
        )

        # Add player names
        for i, player_name in enumerate(df_filtered['player_name']):
            plt.text(X_pca[i, 0] + 0.02, X_pca[i, 1] + 0.02, player_name, fontsize=8)

        plt.title(f'Кластеризація гравців: {self.image_name}')
        plt.xlabel('PCA 1')
        plt.ylabel('PCA 2')
        plt.grid(True)
        plt.legend()
        plt.tight_layout()

        image_wth_ext = f"{self.map_name}{self.image_name}detailed.png"
        plt.savefig(results_dir / image_wth_ext)

    @classmethod
    def run_map_independent_clustering(cls):
        from role_features import MAP_INDEPENDENT
        team_colors = {'navi': 'gold', 'vitality': 'blue'}
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
                filepath=filepath,
                team_name=['navi', 'vitality'],
                team_colors=team_colors
            )
            instance.call()

    @classmethod
    def run_map_clustering(cls):
        from role_features import MAIN_COMPONENTS_MAP, CS_MAPS
        team_colors = {
            'navi': 'red',
            'vitality': 'blue',
        }

        for bool in [True, False]: 
            for key, values in MAIN_COMPONENTS_MAP.items():
                prefix = '_' + key
                image_name = prefix + ('_no_snipers_' if bool else '_with_sniper_')
                for map in CS_MAPS:
                    filepath = Kmeans.BASE_DIR.parent.parent / 'normalization' / 'maps' / f"{map}.csv"

                    instance = cls(
                        map_name=map,
                        features=values,
                        image_name=image_name,
                        filter_snipers=bool,
                        filepath=filepath,
                        team_name=['navi', 'vitality'],
                        team_colors=team_colors
                    )
                    instance.call()

#Kmeans.run_map_clustering()
Kmeans.run_map_independent_clustering()

