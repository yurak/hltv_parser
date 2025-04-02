import pandas as pd
import os
from normaliser import Normaliser
class MapsTable:
    def call(self):
        df = pd.read_csv('top_20_normalized.csv')
        output_dir = "maps_table"
        os.makedirs(output_dir, exist_ok=True)

        for key, values in Normaliser.MAIN_COMPONENTS_MAP.items():
            for column in values:
                all_stats = []
                for map_name, group in df.groupby("map"):
                    std = group[column].std().round(2)
                    mean = group[column].mean().round(2)
                    divider = (std / mean * 100).round(2) if mean != 0 else 0  # Avoid division by zero
                    all_stats.append([map_name, mean, std, divider])
                stats_df = pd.DataFrame(all_stats, columns=["Map", "Mean", "Std", "Std/Mean (%)"])
                filename = f"{column}_{key}_table.csv"
                stats_df.to_csv(os.path.join(output_dir,filename), index=False)
                print(f"📊 Summary saved: {filename}")

MapsTable().call()