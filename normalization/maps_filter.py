import pandas as pd
import os

class MapsFilter:
    TEAM_MAP = {
            'navi': ['b1t', 'iM', 'Aleksib', 'jL', 'w0nderful'],
            'vitality': ['ZyWoo', 'Spinx']
        }
    def call(self):
        df = pd.read_csv('top_20_normalized.csv')

        # Мапа гравців до команд
       

        # Створюємо зворотну мапу: гравець -> команда
        player_to_team = {}
        for team, players in self.TEAM_MAP.items():
            for player in players:
                player_to_team[player] = team

        # Додаємо колонку 'team', значення за замовчуванням — 'other'
        df['team'] = df['player_name'].apply(lambda p: player_to_team.get(p, 'other'))

        # Створюємо директорію, якщо її не існує
        output_dir = "maps"
        os.makedirs(output_dir, exist_ok=True)

        # Групуємо за картою та зберігаємо окремо
        for map_name, group in df.groupby("map"):
            filename = f"{output_dir}/{map_name}.csv"
            group.to_csv(filename, index=False)
            print(f"✅ Saved {filename}")

        print("✅ All maps processed!")
MapsFilter().call()