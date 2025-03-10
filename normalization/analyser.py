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
        # Завантаження даних
        dict_maps = {
            'de_train': ['grey', 2,1],
            'de_dust2': ['yellow', 4,2],
            'de_ancient': ['green', 8,3],
            'de_inferno': ['blue', 12,4],
            'de_anubis': ['red', 16,5],
            'de_mirage': ['black', 20,6],
            'de_nuke': ['purple', 14,7],
            'de_vertigo': ['brown', 6,8]        
        }
        plt.figure(figsize=(12, 6))  # Create a single figure for comparison

        for key, value in dict_maps.items():
            map_name = key
            color = value[0]
            width = value[1]
            elinewidth = value[2]

            data = pd.read_csv(f"../maps/{map_name}.csv")  # Replace with actual path

            columns = list(Processor.COLUMNS_SLASH)
            columns = [col for col in columns if col in data.columns]

            means = data[columns].mean()
            std_devs = data[columns].std()

            # Plot error bars for 3σ
            # plt.errorbar(columns, means, yerr=1.5 * std_devs, fmt='o', color=color, capsize=15,
            #             elinewidth=width, label=f"{map_name} Mean 3σ", markersize=7, mfc='red')

            plt.errorbar(columns, means, yerr=0.5 * std_devs, fmt='-', color=color, capsize=width,
                        elinewidth=elinewidth, label=f"{map_name} Mean 1σ", mfc='red', markersize=2)

            plt.errorbar(columns, means, fmt='o', color=color, capsize=width,
                        elinewidth=5, label=f"{map_name} Mean 3σ", markersize=3, mfc=color)

            # Plot error bars for 1σ
            # plt.errorbar(columns, means, fmt='-', color=color, capsize=15,
            #             elinewidth=width, label=f"{map_name} Mean 1σ", mfc=color, markersize=7)
        plt.legend(fontsize=6)
        plt.xlabel("Features", fontsize=14)
        plt.ylabel("Values", fontsize=18)
        plt.title("Comparison of Mean with 1σ and 3σ for de_train and de_dust2", fontsize=18)
        plt.xticks(rotation=45, ha='right', fontsize=10)
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        # Show the final combined graph
        plt.show()
Analyser().call()
