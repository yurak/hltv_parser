from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
import time
import os
from selenium_data_builder import SeleniumDataBuiler
import pandas as pd
from clusterization.role_features import CS_MAPS, PLAYERS_TOP20_SOURCE

class SeleniumParser:
    BASE_URL = 'https://www.hltv.org/stats/players/'

    def __init__(self, filename, player_sufix, cs_map):
        self.filename = filename
        self.data_dict = {}
        self.player_sufix = player_sufix
        self.cs_map = cs_map

        if not os.path.exists(self.filename):
            self.create_file()
        if os.path.getsize(self.filename) == 0 or not self.full_url() in self.df()["full_url"].values:
            self.driver = webdriver.Chrome()

    def parse(self, only_headers=False):
        if not self.full_url() in self.df()["full_url"].values:
            self.data_from_response()
            self.write_file(only_headers)
            self.close()

    def write_headers(self):
        if os.path.getsize(self.filename) == 0:
            print('writing heders')
            
            self.data_from_response()
            print('received response')
            self.write_file()
            self.close()

    def create_file(self):
        with open(self.filename, 'w') as f:
            pass
        
    def hltv_response(self):
        """Loads HLTV player stats page using Selenium."""

        self.driver.get(self.full_url())
        # WebDriverWait(self.driver, 10).until(
        #     EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'summaryNickname')]"))
        # )

    def write_file(self, only_headers=True):
        with open(self.filename, 'a+', newline='') as file:
            writer = csv.writer(file)
            if only_headers:
                writer.writerow(self.data_dict.keys())
            else:
                if self.data_dict.values():
                    print(f"Processing  + {self.player_sufix} on {self.cs_map}")

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
            self.data_dict['player_name'] = self.player_sufix.split('/')[1]
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

    @classmethod
    def run_all_maps(cls):
        file_name = 'hltv_attributes_selenium_top20_allmapsv2_hltv3_0.csv'
        cls(file_name, '922/snappi', 'de_nuke').write_headers()
        with open(PLAYERS_TOP20_SOURCE, 'r') as file:
            reader = csv.reader(file)
            rows = [row for row in reader]
            for row in rows:
                time.sleep(0.1)
                cls(file_name, row[0], 'all').parse()

    @classmethod
    def run_competetive_maps(cls):
        file_name = 'hltv_attributes_selenium_top20_competetive_maps_hltv3_0.csv'
        cls(file_name, '922/snappi', 'de_nuke').write_headers()
        with open(PLAYERS_TOP20_SOURCE, 'r') as file:
            reader = csv.reader(file)
            rows = [row for row in reader]
            for row in rows:
                for cs_map in CS_MAPS:
                    time.sleep(0.1)
                    cls(file_name, row[0], cs_map).parse()
            
SeleniumParser.run_all_maps()
#SeleniumParser.run_competetive_maps()