import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import sys
from config import CONFIG

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from text_finder import TextFinder

class Processor:
    COLUMNS_SLASH = ('sniping', 'trading', 'clutching', 'utility', 'firepower', 'opening', 'entrying')
    PERCENT_COLUMNS = ['rounds_with_kill', 'rounds_with_multi_kill', 'traded_death_percentage',
                        'opening_death_traded_percentage', 'support_rounds', 'opening_attempts', 'win_percent_after_open_kill', 'sniping_k_percentage',
                        'rounds_w_sniping_k_percentage', 'trade_kills_percentage', 'assisted_kills_percentage', 'last_alive_percentage',
                        'one_v_one_percentage', 'saved_per_round_loss'
                    ]
    
    TIME_COLUMNS = ['time_alive_pr']
    RECORDS = 350
    IMAGES_DIR = 'images'
    DATA_FILES_DIR = 'csv_data'

    def __init__(self, filter_column= 'sniping'):
        os.makedirs(self.IMAGES_DIR, exist_ok=True)
        os.makedirs(self.DATA_FILES_DIR, exist_ok=True)
        self.config = CONFIG

        self.source_file =  self.config['source_file']
        self.normalized_file = self.config['normalized_file']
        self.upper_limit = self.config['upper_limit']
        self.xlower_limit = self.config['xlower_limit']
        self.ylower_limit = self.config['ylower_limit']
        self.filter_column = filter_column
        self.csv_path = os.path.join(self.DATA_FILES_DIR, self.filter_column + ".csv")
        
    def call(self, x = 'trading', y = 'sniping'):
        self.normalize()
        self.filter(x,y)
        #self.plot_all(x,y)
        self.plot_distribution()

    def time_to_seconds(self, time_str):
        parts = time_str.split()
        total_seconds = 0
        for part in parts:
            if 'm' in part:
                total_seconds += int(part.strip('m')) * 60
            elif 's' in part:
                total_seconds += int(part.strip('s'))
        return total_seconds

    def normalize(self):
        df = pd.read_csv(self.source_file)
        for column in self.COLUMNS_SLASH:
            if column in df:
                df[column] = df[column].str.replace('/', '.').astype(float) / 100
                df[column] = df[column].round(2)

        for column in self.PERCENT_COLUMNS:
            if column in df:
                df[column] = df[column].replace('-', None)  # Або np.nan
                df[column] = df[column].str.strip('%').astype(float) / 100

        for column in self.TIME_COLUMNS:
           if column in df:
                df[column] = df[column].apply(self.time_to_seconds) / 105
                df[column] = df[column].round(2)
        df.to_csv(self.normalized_file, index=False) 

    def filter(self, x,y):
        df = pd.read_csv(self.normalized_file)
        #filtered_df = df[(df[self.filter_column] < self.upper_limit) & (df['country'] == 'Ukraine')]
        filtered_df = df[(df[self.filter_column] < self.upper_limit) & (df[x] > self.xlower_limit) & (df[y] > self.ylower_limit) ]
        sorted_df = filtered_df.sort_values(by=self.filter_column)
        sorted_df = sorted_df.drop_duplicates()
        sorted_df.to_csv(self.csv_path, index=False)

    def plot_distribution(self):
        data = pd.read_csv(self.csv_path)
        column = data[self.filter_column].dropna()
        plt.figure(figsize=(10, 6))
        sns.histplot(column, kde=True, bins=30, color="blue")
        plt.title('Розподіл випадкової величини 230(1000) гравців (>0.15)', fontsize=16)
        plt.xlabel(self.filter_column, fontsize=14)
        plt.ylabel("Частота", fontsize=14)
        plt.grid(True)
        output_path = os.path.join(self.IMAGES_DIR, self.filter_column + '_distribution'+ ".png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        plt.show()

    def plot_all(self, x,y):
        df = pd.read_csv(self.csv_path)   
        subset = df.head(self.RECORDS)[[x, y, 'player', 'country', 'is_igl']]
        sns.scatterplot(data=subset, x=x, y=y)  
        plt.title(self.config['title'], fontsize=self.config['title_fontsize'], fontweight=self.config['title_fontweight'])

        for index, row in subset.iterrows():
            if row['is_igl'] == True:
                name = row['player']
                color = 'red'
            else:
                name = row['player']
                color = 'blue'
                    
            plt.annotate(
                name,  # The name or label for the point
                (row[x], row[y]),  # The x and y coordinates of the point
                textcoords="offset points",  # Position relative to the point
                xytext=(5, 5),  # Offset in pixels
                ha='right',  # Horizontal alignment
                fontsize=14,  # Font size of the annotation
                color=color
            )
        plt.show()

    @classmethod
    def process_all(cls):
        for feature_list in [cls.COLUMNS_SLASH, cls.TIME_COLUMNS, cls.PERCENT_COLUMNS]:
            for feature in feature_list:
                processor = cls(feature)
                processor.call()
        
# Processor.process_all()
Processor().call()
