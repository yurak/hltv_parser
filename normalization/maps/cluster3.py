import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
class RoleAssigner:
    def __init__(self, path):
        self.df = pd.read_csv(path)
        self.player_names = self.df["player_name"] if "player_name" in self.df.columns else None
        self.X = self.df.select_dtypes(include=[np.number])
        self.scaled = StandardScaler().fit_transform(self.X)
        self.X_scaled_df = pd.DataFrame(self.scaled, columns=self.X.columns)
        self.pca = PCA(n_components=2).fit_transform(self.scaled)
        self.role_scores = {}
        self.role_features = {
            "AWP": {
                "sniping": 1,
                "sniper_kills_per_round": 1.0,
                "sniper_kills_percentage": 0.9,
                "rounds_with_sniper_kills_percentage": 0.8,
                "sniper_multi_kill_rounds": 0.9,
                "sniper_opening_kills_per_round": 0.9,
                "damage_per_kill": 0.7,
                "kills_per_round": 0.6
            },
            "Anchor": {
                "support_rounds": 0.8,
                "saves_per_round_loss": 1.0,
                "saved_teammate_per_round": 0.9,
                "utility_damage_per_round": 1.0,
                "utility": 0.9,
                "damage_per_round_win": 0.6,
                "time_alive_per_round": 0.7,
                "last_alive_percentage": 0.6,
                "clutch_points_per_round": 0.6
            },
            "Support": {
                "assists_per_round": 1.0,
                "flashes_thrown_per_round": 1.0,
                "flash_assists_per_round": 1.0,
                "time_opponent_flashed_per_round": 0.8,
                "support_rounds": 1.0,
                "saved_teammate_per_round": 0.8,
                "saved_by_teammate_per_round": 0.7,
                "assisted_kills_percentage": 0.8
            },
            "Entry": {
                "entrying": 1.0,
                "opening_kills_per_round": 1.0,
                "opening_attempts": 0.9,
                "opening_success": 1.0,
                "win_after_opening_kill": 0.9,
                "damage_per_round": 1.0,
                "kills_per_round": 0.9,
                "rounds_with_a_kill": 0.8,
                "attacks_per_round": 0.8,
                "time_alive_per_round": 0.5,
                "trading": 0.6
            }
        }
    def calculate_scores(self):
        for role, feats in self.role_features.items():
            score = np.zeros(len(self.X_scaled_df))
            total_weight = 0
            if role == "AWP":
                s = (
                    self.X["sniping"] +
                    self.X["sniper_kills_per_round"] +
                    self.X["sniper_kills_percentage"] +
                    self.X["rounds_with_sniper_kills_percentage"] +
                    self.X["sniper_multi_kill_rounds"] +
                    self.X["sniper_opening_kills_per_round"]
                )
                mask = s > 0.71
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
        plt.figure(figsize=(14, 6))
        plt.subplot(1, 2, 1)
        color_map = {"AWP": "red", "Anchor": "blue", "Support": "green", "Entry": "purple"}
        for role in self.role_features:
            mask = self.roles == role
            plt.scatter(self.pca[mask, 0], self.pca[mask, 1], c=color_map[role], label=role, s=60, edgecolor='black')
        if self.player_names is not None:
            for i, name in enumerate(self.player_names):
                plt.text(self.pca[i, 0] + 0.1, self.pca[i, 1], name, fontsize=7)
        plt.title("Рольове призначення")
        plt.xlabel("PCA 1")
        plt.ylabel("PCA 2")
        plt.legend()
        plt.grid(True)
        plt.subplot(1, 2, 2)
        plt.scatter(self.pca[:, 0], self.pca[:, 1], c=self.cluster_labels, cmap="tab10", s=60, edgecolor="black")
        plt.title("KMeans кластери")
        plt.xlabel("PCA 1")
        plt.ylabel("PCA 2")
        plt.grid(True)
        plt.tight_layout()
        plt.show()
    def export(self, out_path):
        self.df["role"] = self.roles
        self.df["cluster_group"] = self.cluster_labels
        self.df.to_excel(out_path, index=False)
if __name__ == "__main__":
    model = RoleAssigner("de_mirage.csv")
    model.assign_roles()
    model.cluster()
    model.visualize()
    model.export("de_mirage.csv")