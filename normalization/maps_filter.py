import pandas as pd
import os
#from role_features import NORMALIZED_SOURCE

class MapsFilter:
    TEAM_MAP = {
            'navi': ['b1t', 'iM', 'Aleksib', 'jL', 'w0nderful'],
            'vitality': ['ZywOo', 'flameZ', 'ropz', 'mezii', 'apEX']
        }
    def call(self):
        df = pd.read_csv('top_20_normalized_competetive_maps.csv')
       
        player_to_team = {}
        for team, players in self.TEAM_MAP.items():
            for player in players:
                player_to_team[player] = team

        df['team'] = df['player_name'].apply(lambda p: player_to_team.get(p, 'other'))
        output_dir = "maps"
        os.makedirs(output_dir, exist_ok=True)

        for map_name, group in df.groupby("map"):
            filename = f"{output_dir}/{map_name}.csv"
            group.to_csv(filename, index=False)
            print(f"✅ Saved {filename}")

        print("✅ All maps processed!")
#MapsFilter().call()