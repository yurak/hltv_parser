from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
import time
import os
from selenium_data_builder import SeleniumDataBuiler
import pandas as pd

class SeleniumParser:
    BASE_URL = 'https://www.hltv.org/stats/players/'

    PLAYERS = (
        '11893/zywoo',
        '3741/niko',
        '7938/xantares',
        '18987/b1t',
        '8738/elige',
        '10394/twistzz'
    )

    CS_MAPS = (
            'de_train', 'de_nuke', 'de_inferno', 'de_mirage', 'de_dust2', 'de_vertigo',
            'de_ancient', 'de_anubis' 
        )

    def __init__(self, filename, player_sufix, cs_map):
        self.filename = filename
        self.data_dict = {}
        self.player_sufix = player_sufix
        self.cs_map = cs_map
       
        if os.path.getsize(self.filename) == 0 or not self.full_url() in self.df()["full_url"].values:
            self.driver = webdriver.Chrome() # Start Selenium Safari WebDriver

    def parse(self, only_headers=False):
        if not self.full_url() in self.df()["full_url"].values:
            self.data_from_response()
            self.write_file(only_headers)
            self.close()

    def write_headers(self):
        if os.path.getsize(self.filename) == 0:
            self.data_from_response()
            self.write_file()
            self.close()
        
    def hltv_response(self):
        """Loads HLTV player stats page using Selenium."""
        self.driver.get(self.full_url())
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'summaryNickname')]"))
        )

    def write_file(self, only_headers=True):
        with open(self.filename, 'a+', newline='') as file:
            writer = csv.writer(file)
            if only_headers:
                writer.writerow(self.data_dict.keys())
            else:
                if self.data_dict.values():
                    print(f"Processing  + {self.player_sufix} on all maps")

                    writer.writerow(self.data_dict.values())
                else:
                    print('Data was not found for: ' + self.player_sufix)

    def full_url(self):
        return self.BASE_URL + self.player_sufix + '?maps='+ self.cs_map

    def data_from_response(self):
        self.data_dict = {}
        self.hltv_response()

        try:
            selenium_data_builder = SeleniumDataBuiler(self.driver, self.cs_map)
            self.data_dict['full_url'] = self.full_url()
            data_from_builder = selenium_data_builder.build()
            self.data_dict.update(data_from_builder)
        except Exception as e:
            print(f"Error parsing {self.full_url()}: {e}")

        return self.data_dict

    def df(self):
        if not os.path.getsize(self.filename) == 0:
            return pd.read_csv(self.filename)

    def close(self):
        """Closes the Selenium driver."""
        self.driver.quit()

# # Run the parser for all players
# SeleniumParser('hltv_attributes_selenium.csv', '922/snappi', 'de_nuke').write_headers()
# for cs_map in SeleniumParser.CS_MAPS:
#     for el in SeleniumParser.PLAYERS:
#         time.sleep(2.5)
#         SeleniumParser('hltv_attributes_selenium.csv', el, cs_map).parse()

SeleniumParser('hltv_attributes_selenium_top20_allmaps.csv', '922/snappi', 'de_nuke').write_headers()

with open('players_top20.csv', 'r') as file:
    reader = csv.reader(file)

    # Convert rows into an array (list of lists)
    rows = [row for row in reader]
    for row in rows:
        time.sleep(0.1)
        
        SeleniumParser('hltv_attributes_selenium_top20_allmaps.csv', row[0], 'all').parse()