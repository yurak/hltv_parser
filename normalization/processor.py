import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

class Processor:

    COLUMNS_SLASH = ('sniping', 'trading', 'clutching', 'utility', 'firepower', 'opening', 'entrying')
    RECORDS = 200

    def __init__(self):
        print('init')
        self.source_file = 'v4.csv'
        self.normalized_file = 'v3_normalize.csv'
        self.value = 1
        self.filter_column = 'firepower'

    def call(self,x,y):
        self.normalize_slash()
        self.filter()
        # self.plot_all(x,y)
        self.plot_distribution()

    def normalize_slash(self):
        df = pd.read_csv(self.source_file)
        # Convert the 'sniping' column to a float
        for column in self.COLUMNS_SLASH:
            df[column] = df[column].str.replace('/', '.').astype(float) / 100
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
        if 'firepower' not in data.columns:
            raise ValueError("Колонка 'firepower' не знайдена у файлі.")

        # Видалення пропусків, якщо вони є
        firepower = data['firepower'].dropna()

        # Побудова гістограми розподілу
        plt.figure(figsize=(10, 6))
        sns.histplot(firepower, kde=True, bins=30, color="blue")
        plt.title("Розподіл випадкової величини 'firepower'", fontsize=16)
        plt.xlabel("Firepower", fontsize=14)
        plt.ylabel("Частота", fontsize=14)
        plt.grid(True)
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

processor = Processor()
processor.call('sniping', 'firepower')