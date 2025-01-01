import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from text_finder import TextFinder

class Processor:
    COLUMNS_SLASH = ('sniping', 'trading', 'clutching', 'utility', 'firepower', 'opening', 'entrying')
    PERCENT_COLUMNS = ('rounds_with_kill', 'rounds_with_multi_kill', 'traded_death_percentage',
                        'opening_death_traded_percentage', 'support_rounds', 'opening_attempts', 'win_percent_after_open_kill', 'sniping_k_percentage',
                        'rounds_w_sniping_k_percentage', 'trade_kills_percentage', 'assisted_kills_percentage', 'last_alive_percentage',
                        'one_v_one_percentage', 'saved_per_round_loss'
                    )
    
    TIME_COLUMNS = ['time_alive_pr']

    RECORDS = 200
    DIR = 'images'

    def __init__(self, filter_column= 'firepower'):
        print('init')
        self.source_file = 'v4.csv'
        self.normalized_file = 'v3_normalize.csv'
        self.value = 1
        self.filter_column = filter_column

    def call(self,x = 'sniping',y = 'firepower'):
        self.normalize()
        self.filter()
        # self.plot_all(x,y)
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
            df[column] = df[column].str.replace('/', '.').astype(float) / 100
            df[column] = df[column].round(2)

        for column in self.PERCENT_COLUMNS:
            df[column] = df[column].str.strip('%').astype(float) / 100
            df[column] = df[column].round(2)

        for column in self.TIME_COLUMNS:
            df[column] = df[column].apply(self.time_to_seconds) / 105
            df[column] = df[column].round(2)
        df.to_csv(self.normalized_file, index=False) 

    def filter(self):
        df = pd.read_csv(self.normalized_file)
        filtered_df = df[df[self.filter_column] < self.value]
        sorted_df = filtered_df.sort_values(by=self.filter_column) 
        sorted_df = sorted_df.drop_duplicates()
        sorted_df.to_csv(self.filter_column + '.csv', index=False)

    def plot_distribution(self):
        file_path = self.filter_column + '.csv'
        data = pd.read_csv(file_path)

        # Перевірка наявності колонки 'firepower'
        # Видалення пропусків, якщо вони є
        column = data[self.filter_column].dropna()

        # Побудова гістограми розподілу
        plt.figure(figsize=(10, 6))
        sns.histplot(column, kde=True, bins=30, color="blue")
        plt.title('Розподіл випадкової величини ' + self.filter_column, fontsize=16)
        plt.xlabel(self.filter_column, fontsize=14)
        plt.ylabel("Частота", fontsize=14)
        plt.grid(True)
        os.makedirs(self.DIR, exist_ok=True)
        output_path = os.path.join(self.DIR, self.filter_column + '_distribution'+ ".png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        plt.show()

    def plot_all(self, x,y):
        df = pd.read_csv(self.filter_column + '.csv')   
        subset = df.head(self.RECORDS)[[x, y, 'player']]  # Replace 'Column1' and 'Column2' with your column names

        sns.scatterplot(data=df, x=x, y=y)  
        plt.title("Chart for " + self.filter_column + '=' + str(self.value))

        for _, row in subset.iterrows():
            print(row)
            plt.annotate(
                row['player'],  # The name or label for the point
                (row[x], row[y]),  # The x and y coordinates of the point
                textcoords="offset points",  # Position relative to the point
                xytext=(2, 2),  # Offset in pixels
                ha='right',  # Horizontal alignment
                fontsize=9,  # Font size of the annotation
                color='blue'  # Text color
            )
        plt.show()
        
# for feature in Processor.COLUMNS_SLASH: 
#     processor = Processor(feature)
#     processor.call()

for feature in Processor.COLUMNS_SLASH: 
    processor = Processor(feature)
    processor.call()

for feature in Processor.TIME_COLUMNS: 
    processor = Processor(feature)
    processor.call()

for feature in Processor.PERCENT_COLUMNS: 
    processor = Processor(feature)
    processor.call()