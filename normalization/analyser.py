import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import sys
from scipy.stats import f_oneway
import statsmodels.api as sm
from statsmodels.formula.api import ols
from processor import Processor

class Analyser:
    def __init__(self):
        print('init analyser')

    def call(self):
        # Завантаження CSV


        # Завантаження CSV
        data = pd.read_csv("v4_normalize.csv")  # Замініть на шлях до вашого CSV-файлу

        columns = Processor.COLUMNS_SLASH

        # Обчислення статистик
        stats = {}
        for col in columns:
            mean = data[col].mean()
            std_dev = data[col].std()
            sigma_3_upper = mean + 3 * std_dev
            sigma_1_lower = mean - std_dev
            
            stats[col] = {
                'mean': mean,
                'std_dev': std_dev,
                'sigma_3_upper': sigma_3_upper,
                'sigma_1_lower': sigma_1_lower
            }

        # Побудова барчарту
        plt.figure(figsize=(10, 6))
        x = range(len(columns))
        bar_width = 0.4  # Ширина стовпців

        # Горизонтальні лінії для σ і 3σ у вигляді стовпців
        for idx, col in enumerate(columns):
            # 1 Sigma (знизу)
            plt.bar(idx, stats[col]['std_dev'], width=bar_width, bottom=stats[col]['sigma_1_lower'], 
                    color='blue', alpha=0.5, label='1 Sigma' if idx == 0 else "")

            # 3 Sigma (зверху)
            plt.bar(idx, stats[col]['sigma_3_upper'] - stats[col]['mean'], width=bar_width, bottom=stats[col]['mean'], 
                    color='orange', alpha=0.3, label='3 Sigma' if idx == 0 else "")

        # Налаштування графіка
        plt.xticks(x, columns, rotation=45)
        plt.xlabel("Ознаки (Features)")
        plt.ylabel("Значення статистичних параметрів")
        plt.title("Розподіл основних ознак")
        plt.legend(labels=["1 Sigma (синій)", "3 Sigma (помаранчевий)"])
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()

        # Відображення графіка
        plt.show()


Analyser().call()