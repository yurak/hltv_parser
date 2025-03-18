import pandas as pd
import os

class MapsFilter:
    def call(self):
        df = pd.read_csv('top_20_normalized.csv')

        # Create output directory if it doesn't exist
        output_dir = "maps"
        os.makedirs(output_dir, exist_ok=True)

        # Group by "map" column and save each group separately
        for map_name, group in df.groupby("map"):
            filename = f"{output_dir}/{map_name}.csv"
            group.to_csv(filename, index=False)
            print(f"✅ Saved {filename}")

        print("✅ All maps processed!")
