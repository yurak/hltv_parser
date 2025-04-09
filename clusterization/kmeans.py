import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from role_features import ROLE_FEATURES
class RoleAssigner:
    COLOR_MAP = {"AWP": "red", "Anchor": "blue", "Support": "green", "Entry": "purple"}

    def __init__(self, path):
        self.df = pd.read_csv(path)
        self.player_names = self.df["player_name"] if "player_name" in self.df.columns else None
        self.X = self.df.select_dtypes(include=[np.number])
        self.scaled = StandardScaler().fit_transform(self.X)
        self.X_scaled_df = pd.DataFrame(self.scaled, columns=self.X.columns)
        self.pca = PCA(n_components=2).fit_transform(self.scaled)
        self.role_scores = {}
        
    def calculate_scores(self):
        for role, feats in ROLE_FEATURES.items():
            score = np.zeros(len(self.X_scaled_df))
            total_weight = 0
            if role == "AWP":
                s = (
                    self.X["sniping"]
                )
                mask = s > 0.8
            else:
                mask = np.ones(len(self.X_scaled_df), dtype=bool)
            for feat, w in feats.items():
                if feat in self.X_scaled_df.columns:
                    
                    score += self.X_scaled_df[feat] * w
                    total_weight += w
            score[~mask] = -np.inf
            
            self.role_scores[role] = score / total_weight if total_weight > 0 else score

    def assign_roles(self):
        self.calculate_scores()
        self.score_df = pd.DataFrame(self.role_scores)
        self.roles = self.score_df.idxmax(axis=1)

    def cluster(self):
        self.cluster_labels = KMeans(n_clusters=4, random_state=42, n_init=10).fit_predict(self.scaled)
    
    def visualize(self):
        plt.figure(figsize=(14, 10))
        #plt.subplot(1, 2, 1)
        
        for role in ROLE_FEATURES:
            mask = self.roles == role
            plt.scatter(self.pca[mask, 0], self.pca[mask, 1], c = self.COLOR_MAP[role], label = role, s = 30, edgecolor='black')
        if self.player_names is not None:
            for i, name in enumerate(self.player_names):
                plt.text(self.pca[i, 0] + 0.1, self.pca[i, 1], name, fontsize=7)
        plt.title("Рольове призначення")
        plt.xlabel("PCA 1")
        plt.ylabel("PCA 2")
        plt.legend()
        #plt.grid(True)
        # plt.subplot(1, 2, 2)
        # plt.scatter(self.pca[:, 0], self.pca[:, 1], c=self.cluster_labels, cmap="tab10", s=30, edgecolor="black")
        # plt.title("KMeans кластери")
        # plt.xlabel("PCA 1")
        # plt.ylabel("PCA 2")
        #plt.grid(True)
        plt.tight_layout()
        plt.show()

    def export(self):
        self.df["role"] = self.roles
        self.df["cluster_group"] = self.cluster_labels
        self.df.to_csv('de_mirage_wirg_roles.csv', index=False)

if __name__ == "__main__":
    model = RoleAssigner("../normalization/maps/de_mirage.csv")
    model.assign_roles()
    model.cluster()
    model.visualize()
    model.export()