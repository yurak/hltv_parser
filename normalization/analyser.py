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
        data = pd.read_csv("v4_normalize.csv")  # Замініть на реальний шлях

        # Конвертація tuple у список
        columns = list(Processor.COLUMNS_SLASH)
        columns = [col for col in columns if col in data.columns]  # Фільтрація колонок

        # Обчислення середнього (μ) та стандартного відхилення (σ)
        means = data[columns].mean()
        std_devs = data[columns].std()

        # Створення графіка
        plt.figure(figsize=(12, 6))
        #plt.plot(columns, means, marker='o', color='royalblue', label="Mean", linestyle='-', linewidth=2)

        #plt.errorbar(columns, means, yerr=1.5 * std_devs, fmt='o', color='royalblue', capsize=15, elinewidth=2, label="Mean 3σ", markersize=7, mfc='red')
        
        plt.errorbar(columns, means, yerr=0.5 * std_devs, fmt='-', color='green', capsize=15, elinewidth=20, label="Mean 1σ", mfc='red',  markersize=7)
        # Додаємо легенду
        plt.legend( fontsize=18)
        plt.xlabel("Features", fontsize=14)
        plt.ylabel("Values", fontsize=18)
        plt.title("Mean with 1σ and 3σ", fontsize=18)
        plt.xticks(rotation=45, ha='right', fontsize=10)
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        # Показати графік
        plt.show()

Analyser().call()
