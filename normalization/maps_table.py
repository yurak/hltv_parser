import pandas as pd
import os
from normaliser import Normaliser
import itertools

class MapsTable:
    def call(self):       
        df = pd.read_csv('top_20_normalized.csv')
        output_dir = "maps_table"
        os.makedirs(output_dir, exist_ok=True)  
        merged_values = [value for key, value in Normaliser.MAIN_COMPONENTS_MAP.items()]
        flat_columns = [item for sublist in merged_values for item in sublist]
     
        for column in flat_columns:
            all_stats = []
            
            for map_name, group in df.groupby("map"):
                filename = os.path.join(output_dir, f"{map_name}.csv")
                
                # group.to_csv(filename, index=False)  # ✅ Now saving each map's data
                # print(f"✅ Saved {filename}")
                std = group[column].std().round(2)
                mean = group[column].mean().round(2)
                divider = (std / mean * 100).round(2) if mean != 0 else 0  # Avoid division by zero
                
                all_stats.append([map_name, mean, std, divider])

            stats_df = pd.DataFrame(all_stats, columns=["Map", "Mean", "Std", "Std/Mean (%)"])
            stats_df.to_csv(os.path.join(output_dir, f"{column}_table.csv"), index=False)
            print(f"📊 Summary saved: {column}_summary_stats.csv")

MapsTable().call()

 
                
                
                
                