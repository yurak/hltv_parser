import pandas as pd
import os

class PlayersFilter:

    NICKNAMES = (
        'ZywOo',
        'NiKo',
        's1mple',
        'm0NESY',
        'ropz',
        'xertioN',
        'kyxsan',
        'MAJ3R'
    )

    def __init__(self, player_name):
        self.player_name = player_name

    def call(self):
        # Load the CSV file (replace 'hltv_data.csv' with your actual file)
        input_csv = 'hltv_attributes_selenium_top20.csv'
        output_folder = 'players/'

        # Ensure the output folder exists
        os.makedirs(output_folder, exist_ok=True)

        # Read the CSV file
        df = pd.read_csv(input_csv)

        # Filter data where player_name is 'Niko'
        player_df = df[df['player_name'] == self.player_name]
        output_csv = os.path.join(output_folder, f'{self.player_name}.csv')
        player_df.to_csv(output_csv, index=False)

        print(f"Data for {self.player_name} saved to: {output_csv}")

for player_name in PlayersFilter.NICKNAMES:
    PlayersFilter(player_name).call()