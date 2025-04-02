from normaliser import Normaliser
import pandas as pd

class VarianceTable:
    def __init__(self, source_file):
        self.source_file  = source_file
    
    def call(self):
        df = pd.read_csv(self.source_file)
        normalized_df = df.copy()
        for column in Normaliser.FIREPOWER:
            mean = df[column].mean()
            std = df[column].std()
            normalized_df[column] = (df[column] - mean) / std + 1
        
        normalized_df.to_csv("normalized_data.csv", index=False)
    
VarianceTable('top_20_normalized.csv').call()